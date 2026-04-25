from __future__ import annotations

import json
import logging
import os
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from rag_service import RAGExplanationService


def envstr(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None else str(value).strip()


def envint(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return int(default)
    return int(value)


def envfloat(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return float(default)
    return float(value)


def envbool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class RAGMQTTConfig:
    mqtthost: str
    mqttport: int
    mqtttopicprefix: str
    mqttqos: int
    mqttkeepalive: int
    mqttusername: str
    mqttpassword: str
    mqtttls: bool
    mqttcacert: str
    mqttclientcert: str
    mqttclientkey: str
    mqtttlsinsecure: bool
    connectretrydelaysec: float
    telemetrycachettlsec: float
    predictioncachettlsec: float
    decisioncachettlsec: float
    publishdecisionexplanations: bool
    serviceid: str
    vectorstorepath: str
    chromacollectionname: str
    openaiapikey: str
    openaimodel: str


def load_config() -> RAGMQTTConfig:
    return RAGMQTTConfig(
        mqtthost=envstr("MQTT_HOST", envstr("MQTTHOST", "localhost")),
        mqttport=envint("MQTT_PORT", envint("MQTTPORT", 1881)),
        mqtttopicprefix=envstr("MQTT_TOPIC_PREFIX", envstr("MQTTTOPICPREFIX", "coldchain")).strip("/"),
        mqttqos=envint("MQTT_QOS", envint("MQTTQOS", 1)),
        mqttkeepalive=envint("MQTT_KEEPALIVE", envint("MQTTKEEPALIVE", 60)),
        mqttusername=envstr("MQTT_USERNAME", envstr("MQTTUSERNAME", "")),
        mqttpassword=envstr("MQTT_PASSWORD", envstr("MQTTPASSWORD", "")),
        mqtttls=envbool("MQTT_TLS", envbool("MQTTTLS", False)),
        mqttcacert=envstr("MQTT_CA_CERT", envstr("MQTTCACERT", "")),
        mqttclientcert=envstr("MQTT_CLIENT_CERT", envstr("MQTTCLIENTCERT", "")),
        mqttclientkey=envstr("MQTT_CLIENT_KEY", envstr("MQTTCLIENTKEY", "")),
        mqtttlsinsecure=envbool("MQTT_TLS_INSECURE", envbool("MQTTTLSINSECURE", False)),
        connectretrydelaysec=envfloat("RAG_MQTT_CONNECT_RETRY_DELAY_SEC", 5.0),
        telemetrycachettlsec=envfloat("RAG_TELEMETRY_CACHE_TTL_SEC", 1800.0),
        predictioncachettlsec=envfloat("RAG_PREDICTION_CACHE_TTL_SEC", 1800.0),
        decisioncachettlsec=envfloat("RAG_DECISION_CACHE_TTL_SEC", 1800.0),
        publishdecisionexplanations=envbool("RAG_PUBLISH_DECISION_EXPLANATIONS", True),
        serviceid=envstr("RAG_SERVICE_ID", f"rag-service-{os.getpid()}"),
        vectorstorepath=envstr("VECTORSTORE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "vectorstore")),
        chromacollectionname=envstr("CHROMA_COLLECTION_NAME", "coldchainsops"),
        openaiapikey=envstr("OPENAI_API_KEY", envstr("OPENAIAPIKEY", "")),
        openaimodel=envstr("OPENAI_MODEL", "gpt-4o-mini"),
    )


LOGLEVEL = envstr("LOGLEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOGLEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("rag-mqtt-service")


class RAGMQTTService:
    def __init__(self, config: RAGMQTTConfig) -> None:
        self.config = config
        self.ragservice = RAGExplanationService(
            openai_api_key=config.openaiapikey,
            vectorstore_path=config.vectorstorepath,
            collection_name=config.chromacollectionname,
            openai_model=config.openaimodel,
        )

        self.latesttelemetry: Dict[str, Dict[str, Any]] = {}
        self.latestpredictions: Dict[str, Dict[str, Any]] = {}
        self.latestdecisions: Dict[str, Dict[str, Any]] = {}

        self.lastprocessedpredictionts: Dict[str, str] = {}
        self.lastprocesseddecisionts: Dict[str, str] = {}

        self.connected = False
        self.client = mqtt.Client(
            client_id=self.config.serviceid,
            protocol=mqtt.MQTTv311,
            clean_session=True,
        )
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        if self.config.mqttusername:
            self.client.username_pw_set(self.config.mqttusername, self.config.mqttpassword)

        if self.config.mqtttls:
            tls_kwargs: Dict[str, Any] = {}
            if self.config.mqttcacert:
                tls_kwargs["ca_certs"] = self.config.mqttcacert
            if self.config.mqttclientcert:
                tls_kwargs["certfile"] = self.config.mqttclientcert
            if self.config.mqttclientkey:
                tls_kwargs["keyfile"] = self.config.mqttclientkey
            self.client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT, **tls_kwargs)
            self.client.tls_insecure_set(bool(self.config.mqtttlsinsecure))

        self.client.will_set(
            self.status_topic(),
            payload=safe_json(
                {
                    "serviceid": self.config.serviceid,
                    "status": "offline",
                    "timestamp": now_iso(),
                }
            ),
            qos=1,
            retain=True,
        )

    # ------------------------------------------------------------------
    # Topic helpers
    # ------------------------------------------------------------------

    def telemetry_topic(self) -> str:
        return f"{self.config.mqtttopicprefix}/telemetry/#"

    def prediction_topic(self) -> str:
        return f"{self.config.mqtttopicprefix}/predictions/#"

    def decision_topic(self) -> str:
        return f"{self.config.mqtttopicprefix}/decisions/#"

    def explanation_topic(self, assetid: str) -> str:
        return f"{self.config.mqtttopicprefix}/explanations/{assetid}"

    def decision_explanation_topic(self, assetid: str) -> str:
        return f"{self.config.mqtttopicprefix}/decisionexplanations/{assetid}"

    def status_topic(self) -> str:
        return f"{self.config.mqtttopicprefix}/status/{self.config.serviceid}"

    # ------------------------------------------------------------------
    # MQTT lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self.client.connect(
            self.config.mqtthost,
            self.config.mqttport,
            keepalive=self.config.mqttkeepalive,
        )
        self.client.loop_start()

    def close(self) -> None:
        try:
            self.publish_status("offline")
        except Exception:
            pass
        try:
            self.client.loop_stop()
        except Exception:
            pass
        try:
            self.client.disconnect()
        except Exception:
            pass

    def publish_status(self, status: str) -> None:
        self.client.publish(
            self.status_topic(),
            payload=safe_json(
                {
                    "serviceid": self.config.serviceid,
                    "status": status,
                    "timestamp": now_iso(),
                }
            ),
            qos=1,
            retain=True,
        )

    def on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
        self.connected = rc == 0
        if not self.connected:
            logger.error("MQTT connection failed with rc=%s", rc)
            return

        subscriptions = [
            (self.telemetry_topic(), self.config.mqttqos),
            (self.prediction_topic(), self.config.mqttqos),
            (self.decision_topic(), self.config.mqttqos),
        ]
        for topic, qos in subscriptions:
            client.subscribe(topic, qos=qos)

        self.publish_status("online")
        logger.info(
            "MQTT connected | host=%s | port=%s | prefix=%s",
            self.config.mqtthost,
            self.config.mqttport,
            self.config.mqtttopicprefix,
        )
        logger.info(
            "Subscribed to topics | telemetry=%s | predictions=%s | decisions=%s",
            self.telemetry_topic(),
            self.prediction_topic(),
            self.decision_topic(),
        )

    def on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        self.connected = False
        if rc == 0:
            logger.info("MQTT disconnected cleanly")
        else:
            logger.warning("Unexpected MQTT disconnect rc=%s", rc)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def cache_payload(self, cache: Dict[str, Dict[str, Any]], assetid: str, payload: Dict[str, Any]) -> None:
        cache[assetid] = {
            "payload": dict(payload),
            "cachedat": time.time(),
        }

    def prune_cache(self) -> None:
        now = time.time()

        stale_telemetry = [
            assetid
            for assetid, item in self.latesttelemetry.items()
            if now - float(item.get("cachedat", now)) > self.config.telemetrycachettlsec
        ]
        for assetid in stale_telemetry:
            self.latesttelemetry.pop(assetid, None)

        stale_predictions = [
            assetid
            for assetid, item in self.latestpredictions.items()
            if now - float(item.get("cachedat", now)) > self.config.predictioncachettlsec
        ]
        for assetid in stale_predictions:
            self.latestpredictions.pop(assetid, None)

        stale_decisions = [
            assetid
            for assetid, item in self.latestdecisions.items()
            if now - float(item.get("cachedat", now)) > self.config.decisioncachettlsec
        ]
        for assetid in stale_decisions:
            self.latestdecisions.pop(assetid, None)

    # ------------------------------------------------------------------
    # Payload helpers
    # ------------------------------------------------------------------

    def extract_assetid(self, payload: Dict[str, Any], topic: str = "") -> Optional[str]:
        for key in ("assetid", "asset_id"):
            assetid = safe_str(payload.get(key))
            if assetid and assetid.lower() != "all":
                return assetid

        parts = topic.strip("/").split("/")
        if parts:
            last = safe_str(parts[-1])
            if last and last.lower() != "all" and "#" not in last and "+" not in last:
                return last

        return None

    def build_publish_metadata(self, kind: str, assetid: str) -> Dict[str, Any]:
        return {
            "kind": kind,
            "serviceid": self.config.serviceid,
            "timestamp": now_iso(),
            "assetid": assetid,
            "mqttprefix": self.config.mqtttopicprefix,
        }

    def publish_explanation(self, assetid: str, explanation: Dict[str, Any]) -> None:
        payload = dict(explanation)
        payload["ragservicemetadata"] = self.build_publish_metadata("prediction-explanation", assetid)
        self.client.publish(
            self.explanation_topic(assetid),
            payload=safe_json(payload),
            qos=self.config.mqttqos,
            retain=False,
        )
        logger.info("Published prediction explanation for assetid=%s", assetid)

    def publish_decision_explanation(self, assetid: str, explanation: Dict[str, Any]) -> None:
        payload = dict(explanation)
        payload["ragservicemetadata"] = self.build_publish_metadata("decision-explanation", assetid)
        self.client.publish(
            self.decision_explanation_topic(assetid),
            payload=safe_json(payload),
            qos=self.config.mqttqos,
            retain=False,
        )
        logger.info("Published decision explanation for assetid=%s", assetid)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process_prediction_if_ready(self, assetid: str) -> None:
        prediction_item = self.latestpredictions.get(assetid)
        telemetry_item = self.latesttelemetry.get(assetid)

        if not prediction_item or not telemetry_item:
            return

        prediction = dict(prediction_item.get("payload") or {})
        telemetry = dict(telemetry_item.get("payload") or {})
        decision = dict((self.latestdecisions.get(assetid) or {}).get("payload") or {})

        prediction_ts = safe_str(prediction.get("timestamp"))
        if prediction_ts and self.lastprocessedpredictionts.get(assetid) == prediction_ts:
            return

        try:
            explanation = self.ragservice.generate_explanation(
                prediction=prediction,
                telemetry=telemetry,
                decision=decision or None,
            )
            self.publish_explanation(assetid, explanation)
            self.display_explanation(explanation)
            self.lastprocessedpredictionts[assetid] = prediction_ts or now_iso()
        except Exception as exc:
            logger.exception("Failed to generate prediction explanation for assetid=%s | %s", assetid, exc)

    def process_decision_if_ready(self, assetid: str) -> None:
        decision_item = self.latestdecisions.get(assetid)
        if not decision_item:
            return

        decision = dict(decision_item.get("payload") or {})
        telemetry = dict((self.latesttelemetry.get(assetid) or {}).get("payload") or {})
        prediction = dict((self.latestpredictions.get(assetid) or {}).get("payload") or {})

        decision_ts = safe_str(decision.get("timestamp"))
        if decision_ts and self.lastprocesseddecisionts.get(assetid) == decision_ts:
            return

        embedded_telemetry = decision.get("telemetry")
        embedded_prediction = decision.get("prediction")

        if not telemetry and isinstance(embedded_telemetry, dict):
            telemetry = dict(embedded_telemetry)

        if not prediction and isinstance(embedded_prediction, dict):
            prediction = dict(embedded_prediction)

        if not telemetry and not embedded_telemetry:
            return

        try:
            explanation = self.ragservice.explain_decision(
                decision=decision,
                telemetry=telemetry or None,
                prediction=prediction or None,
            )
            if self.config.publishdecisionexplanations:
                self.publish_decision_explanation(assetid, explanation)
            self.display_decision_explanation(explanation)
            self.lastprocesseddecisionts[assetid] = decision_ts or now_iso()
        except Exception as exc:
            logger.exception("Failed to generate decision explanation for assetid=%s | %s", assetid, exc)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    def handle_telemetry(self, topic: str, payload: Dict[str, Any]) -> None:
        assetid = self.extract_assetid(payload, topic)
        if not assetid:
            logger.warning("Ignoring telemetry without assetid")
            return

        payload["assetid"] = assetid
        self.cache_payload(self.latesttelemetry, assetid, payload)
        logger.debug("Cached telemetry for assetid=%s", assetid)

        self.process_prediction_if_ready(assetid)
        self.process_decision_if_ready(assetid)

    def handle_telemetry_batch(self, payload: Dict[str, Any]) -> None:
        batch = payload.get("batch")
        if not isinstance(batch, list):
            logger.warning("Ignoring telemetry batch without list 'batch'")
            return

        for item in batch:
            if not isinstance(item, dict):
                continue
            assetid = self.extract_assetid(item)
            if not assetid:
                continue
            item["assetid"] = assetid
            self.cache_payload(self.latesttelemetry, assetid, item)
            logger.debug("Cached batched telemetry for assetid=%s", assetid)

            self.process_prediction_if_ready(assetid)
            self.process_decision_if_ready(assetid)

    def handle_prediction(self, topic: str, payload: Dict[str, Any]) -> None:
        assetid = self.extract_assetid(payload, topic)
        if not assetid:
            logger.warning("Ignoring prediction without assetid")
            return

        payload["assetid"] = assetid
        self.cache_payload(self.latestpredictions, assetid, payload)
        logger.debug("Cached prediction for assetid=%s", assetid)

        self.process_prediction_if_ready(assetid)
        self.process_decision_if_ready(assetid)

    def handle_decision(self, topic: str, payload: Dict[str, Any]) -> None:
        assetid = self.extract_assetid(payload, topic)
        if not assetid:
            logger.warning("Ignoring decision without assetid")
            return

        payload["assetid"] = assetid
        self.cache_payload(self.latestdecisions, assetid, payload)
        logger.debug("Cached decision for assetid=%s", assetid)

        self.process_decision_if_ready(assetid)

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        self.prune_cache()

        try:
            rawpayload = msg.payload.decode("utf-8")
            data = json.loads(rawpayload)
            if not isinstance(data, dict):
                logger.warning("Ignoring non-dict payload on topic=%s", msg.topic)
                return

            topic = msg.topic.strip()
            prefix = self.config.mqtttopicprefix

            if topic == f"{prefix}/telemetry/all":
                self.handle_telemetry_batch(data)
            elif topic.startswith(f"{prefix}/telemetry/"):
                self.handle_telemetry(topic, data)
            elif topic.startswith(f"{prefix}/predictions/"):
                self.handle_prediction(topic, data)
            elif topic.startswith(f"{prefix}/decisions/"):
                self.handle_decision(topic, data)
            else:
                logger.debug("Ignoring unmatched topic=%s", topic)

        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON on topic=%s | %s", msg.topic, exc)
        except Exception as exc:
            logger.exception("Error processing topic=%s | %s", msg.topic, exc)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def display_explanation(self, explanation: Dict[str, Any]) -> None:
        print("=" * 80)
        print("RISK EXPLANATION GENERATED")
        print("=" * 80)
        print(f"Asset ID: {explanation.get('assetid')}")
        print(f"Risk Score: {explanation.get('riskscore')}")
        print(f"Urgency: {explanation.get('urgency')}")
        print(f"Timestamp: {explanation.get('timestamp')}")
        print("-" * 80)
        print(explanation.get("explanationtext", ""))
        print("-" * 80)
        refs = explanation.get("referencedsops") or []
        print(f"Referenced SOPs: {', '.join(refs) if refs else 'None'}")
        print("=" * 80)

    def display_decision_explanation(self, explanation: Dict[str, Any]) -> None:
        print("=" * 80)
        print("DECISION EXPLANATION GENERATED")
        print("=" * 80)
        print(f"Asset ID: {explanation.get('assetid')}")
        print(f"Decision ID: {explanation.get('decisionid')}")
        print(f"Risk Score: {explanation.get('riskscore')}")
        print(f"Urgency: {explanation.get('urgency')}")
        print(f"Timestamp: {explanation.get('timestamp')}")
        print("-" * 80)
        print(explanation.get("explanationtext", ""))
        print("-" * 80)
        refs = explanation.get("referencedsops") or []
        print(f"Referenced SOPs: {', '.join(refs) if refs else 'None'}")
        print("=" * 80)

    # ------------------------------------------------------------------
    # Service loop
    # ------------------------------------------------------------------

    def start(self) -> None:
        while True:
            try:
                logger.info(
                    "Starting RAG MQTT service | host=%s | port=%s | prefix=%s",
                    self.config.mqtthost,
                    self.config.mqttport,
                    self.config.mqtttopicprefix,
                )
                self.connect()
                while not self.connected:
                    time.sleep(0.1)
                self.client.loop_forever()
            except KeyboardInterrupt:
                logger.info("RAG MQTT service stopped by user")
                self.close()
                break
            except Exception as exc:
                logger.exception("RAG MQTT service crashed | %s", exc)
                try:
                    self.close()
                except Exception:
                    pass
                time.sleep(self.config.connectretrydelaysec)


def main() -> None:
    load_dotenv()
    config = load_config()
    service = RAGMQTTService(config)
    service.start()


if __name__ == "__main__":
    main()