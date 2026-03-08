from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

try:
    from agents.decision_agent import ColdChainDecisionAgent
except ImportError:
    from .agents.decision_agent import ColdChainDecisionAgent


def env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None else str(value).strip()


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return int(default)
    return int(value)


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return float(default)
    return float(value)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


@dataclass(frozen=True)
class DecisionEngineConfig:
    mqtt_enabled: bool
    mqtt_host: str
    mqtt_port: int
    mqtt_topic_prefix: str
    mqtt_qos: int
    telemetry_cache_ttl_sec: float
    prediction_cache_ttl_sec: float
    connect_retry_delay_sec: float


def load_config() -> DecisionEngineConfig:
    return DecisionEngineConfig(
        mqtt_enabled=env_bool("MQTT_ENABLED", True),
        mqtt_host=env_str("MQTT_HOST", "localhost"),
        mqtt_port=env_int("MQTT_PORT", 1884),
        mqtt_topic_prefix=env_str("MQTT_TOPIC_PREFIX", "coldchain").strip("/"),
        mqtt_qos=env_int("MQTT_QOS", 1),
        telemetry_cache_ttl_sec=env_float("DECISION_ENGINE_TELEMETRY_CACHE_TTL_SEC", 1800.0),
        prediction_cache_ttl_sec=env_float("DECISION_ENGINE_PREDICTION_CACHE_TTL_SEC", 900.0),
        connect_retry_delay_sec=env_float("DECISION_ENGINE_CONNECT_RETRY_DELAY_SEC", 5.0),
    )


LOG_LEVEL = env_str("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("decision-engine")


class DecisionEngineService:
    def __init__(self, config: DecisionEngineConfig) -> None:
        self.config = config
        self.agent = ColdChainDecisionAgent()

        self.latest_telemetry: Dict[str, Dict[str, Any]] = {}
        self.pending_predictions: Dict[str, Dict[str, Any]] = {}
        self.last_processed_prediction_ts: Dict[str, str] = {}

        self.client = mqtt.Client(
            client_id=f"decision-engine-{os.getpid()}",
            clean_session=True,
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _telemetry_topic(self) -> str:
        return f"{self.config.mqtt_topic_prefix}/telemetry/#"

    def _prediction_topic(self) -> str:
        return f"{self.config.mqtt_topic_prefix}/predictions/#"

    def _decision_topic(self, asset_id: str) -> str:
        return f"{self.config.mqtt_topic_prefix}/decisions/{asset_id}"

    def _extract_asset_id(self, payload: Dict[str, Any], topic: str) -> Optional[str]:
        asset_id = _safe_str(payload.get("asset_id"))
        if asset_id:
            return asset_id

        parts = topic.strip("/").split("/")
        if len(parts) >= 3:
            return _safe_str(parts[-1]) or None
        return None

    def _cache_payload(
        self,
        cache: Dict[str, Dict[str, Any]],
        asset_id: str,
        payload: Dict[str, Any],
    ) -> None:
        cache[asset_id] = {
            "payload": dict(payload),
            "cached_at": time.time(),
        }

    def _prune_cache(self) -> None:
        now = time.time()

        stale_telemetry = [
            asset_id
            for asset_id, item in self.latest_telemetry.items()
            if (now - float(item.get("cached_at", now))) > self.config.telemetry_cache_ttl_sec
        ]
        for asset_id in stale_telemetry:
            self.latest_telemetry.pop(asset_id, None)

        stale_predictions = [
            asset_id
            for asset_id, item in self.pending_predictions.items()
            if (now - float(item.get("cached_at", now))) > self.config.prediction_cache_ttl_sec
        ]
        for asset_id in stale_predictions:
            self.pending_predictions.pop(asset_id, None)

    def _publish_decision(self, asset_id: str, decision: Dict[str, Any]) -> None:
        topic = self._decision_topic(asset_id)
        payload = json.dumps(decision, ensure_ascii=False, default=str)
        self.client.publish(topic, payload, qos=self.config.mqtt_qos, retain=False)
        logger.info(f"Published decision for asset_id={asset_id} to topic={topic}")

    def _build_engine_metadata(
        self,
        asset_id: str,
        prediction: Dict[str, Any],
        telemetry: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "engine_timestamp": _now_iso(),
            "engine_name": "decision_engine",
            "asset_id": asset_id,
            "prediction_timestamp": prediction.get("timestamp"),
            "telemetry_timestamp": telemetry.get("timestamp"),
            "mqtt_prefix": self.config.mqtt_topic_prefix,
        }

    def _process_asset_if_ready(self, asset_id: str) -> None:
        telemetry_item = self.latest_telemetry.get(asset_id)
        prediction_item = self.pending_predictions.get(asset_id)

        if not telemetry_item or not prediction_item:
            return

        telemetry = dict(telemetry_item.get("payload") or {})
        prediction = dict(prediction_item.get("payload") or {})

        prediction_ts = _safe_str(prediction.get("timestamp"))
        if prediction_ts and self.last_processed_prediction_ts.get(asset_id) == prediction_ts:
            logger.debug(f"Skipping duplicate prediction for asset_id={asset_id} timestamp={prediction_ts}")
            self.pending_predictions.pop(asset_id, None)
            return

        decision = self.agent.process_decision(prediction=prediction, telemetry=telemetry)
        decision["engine_metadata"] = self._build_engine_metadata(
            asset_id=asset_id,
            prediction=prediction,
            telemetry=telemetry,
        )

        self._publish_decision(asset_id, decision)

        self.last_processed_prediction_ts[asset_id] = prediction_ts or _safe_str(decision.get("timestamp"), _now_iso())
        self.pending_predictions.pop(asset_id, None)

        analysis = decision.get("analysis") or {}
        logger.info(
            "Decision completed | asset_id=%s risk_level=%s risk_score=%s actions=%s",
            asset_id,
            analysis.get("risk_level"),
            analysis.get("risk_score"),
            len(decision.get("actions") or []),
        )

    def _handle_telemetry(self, topic: str, payload: Dict[str, Any]) -> None:
        asset_id = self._extract_asset_id(payload, topic)
        if not asset_id:
            logger.warning("Ignoring telemetry without asset_id")
            return

        payload["asset_id"] = asset_id
        self._cache_payload(self.latest_telemetry, asset_id, payload)
        logger.debug(f"Cached telemetry for asset_id={asset_id}")
        self._process_asset_if_ready(asset_id)

    def _handle_prediction(self, topic: str, payload: Dict[str, Any]) -> None:
        asset_id = self._extract_asset_id(payload, topic)
        if not asset_id:
            logger.warning("Ignoring prediction without asset_id")
            return

        payload["asset_id"] = asset_id
        self._cache_payload(self.pending_predictions, asset_id, payload)
        logger.debug(f"Cached prediction for asset_id={asset_id}")
        self._process_asset_if_ready(asset_id)

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
        if rc != 0:
            logger.error(f"MQTT connection failed with rc={rc}")
            return

        subscriptions = [
            (self._telemetry_topic(), self.config.mqtt_qos),
            (self._prediction_topic(), self.config.mqtt_qos),
        ]
        for topic, qos in subscriptions:
            client.subscribe(topic, qos=qos)

        logger.info(
            "MQTT connected | host=%s port=%s prefix=%s",
            self.config.mqtt_host,
            self.config.mqtt_port,
            self.config.mqtt_topic_prefix,
        )
        logger.info(
            "Subscribed to topics | telemetry=%s predictions=%s",
            self._telemetry_topic(),
            self._prediction_topic(),
        )

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        if rc == 0:
            logger.info("MQTT disconnected cleanly")
        else:
            logger.warning(f"Unexpected MQTT disconnect rc={rc}")

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        self._prune_cache()

        try:
            raw_payload = msg.payload.decode("utf-8")
            data = json.loads(raw_payload)
            if not isinstance(data, dict):
                logger.warning(f"Ignoring non-dict payload on topic={msg.topic}")
                return

            topic = msg.topic.strip()
            prefix = self.config.mqtt_topic_prefix.strip("/")

            if topic.startswith(f"{prefix}/telemetry/"):
                self._handle_telemetry(topic, data)
            elif topic.startswith(f"{prefix}/predictions/"):
                self._handle_prediction(topic, data)
            else:
                logger.debug(f"Ignoring topic={topic}")

        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON received on topic={msg.topic}: {exc}")
        except Exception as exc:
            logger.exception(f"Error processing MQTT message on topic={msg.topic}: {exc}")

    def start(self) -> None:
        if not self.config.mqtt_enabled:
            logger.warning("Decision engine not started because MQTT_ENABLED=0")
            return

        while True:
            try:
                logger.info(
                    "Starting decision engine | mqtt=%s:%s prefix=%s",
                    self.config.mqtt_host,
                    self.config.mqtt_port,
                    self.config.mqtt_topic_prefix,
                )
                self.client.connect(self.config.mqtt_host, self.config.mqtt_port, keepalive=60)
                self.client.loop_forever()
            except KeyboardInterrupt:
                logger.info("Decision engine stopped by user")
                self.close()
                break
            except Exception as exc:
                logger.exception(f"Decision engine crashed: {exc}")
                try:
                    self.client.disconnect()
                except Exception:
                    pass
                time.sleep(self.config.connect_retry_delay_sec)

    def close(self) -> None:
        try:
            self.client.loop_stop()
        except Exception:
            pass

        try:
            self.client.disconnect()
        except Exception:
            pass


def main() -> None:
    load_dotenv()
    config = load_config()
    service = DecisionEngineService(config)
    service.start()


if __name__ == "__main__":
    main()