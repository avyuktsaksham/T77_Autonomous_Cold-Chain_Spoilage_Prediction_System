from __future__ import annotations

import os
import json
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional
from collections import deque

import numpy as np
import torch
import joblib
from pymongo import MongoClient, UpdateOne
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from models.lstm_model import create_model

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("edge-ai-predict")


def env_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return default if v is None else str(v).strip()


def env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return int(v)


def env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or not str(v).strip():
        return default
    return float(v)


def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class PredictConfig:
    mongodb_uri: str
    mongodb_db: str
    testing_collection: str
    mongodb_uri_2: str
    predictions_collection: str

    model_path: str
    meta_path: str
    poll_interval_sec: float
    batch_limit: int

    mqtt_enabled: bool
    mqtt_host: str
    mqtt_port: int
    mqtt_topic_prefix: str
    mqtt_qos: int

    state_path: str


def load_config() -> PredictConfig:
    return PredictConfig(
        mongodb_uri=env_str("MONGODB_URI", ""),
        mongodb_db=env_str("MONGODB_DB", "cold_chain_database"),
        testing_collection=env_str("MONGODB_COLLECTION", "sensors_data"),
        mongodb_uri_2=env_str("MONGODB_URI_PREDICTIONS", ""),
        predictions_collection=env_str("MONGODB_COLLECTION_PREDICTIONS", "predictions_on_real_time_data"),

        model_path=env_str("MODEL_PATH", os.path.join("models", "best_model.pth")),
        meta_path=env_str("META_PATH", os.path.join("models", "model_meta.json")),

        poll_interval_sec=env_float("POLL_INTERVAL_SEC", 1.0),
        batch_limit=env_int("BATCH_LIMIT", 15000),

        mqtt_enabled=env_bool("MQTT_ENABLED", True),
        mqtt_host=env_str("MQTT_HOST", "localhost"),
        mqtt_port=env_int("MQTT_PORT", 1881),
        mqtt_topic_prefix=env_str("MQTT_TOPIC_PREFIX", "coldchain").strip("/"),
        mqtt_qos=env_int("MQTT_QOS", 1),

        state_path=env_str("PREDICTOR_STATE_PATH", os.path.join("models", ".predictor_state.json")),
    )


def _get_nested(d: Dict[str, Any], path: str) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _to_float(x: Any, default: float = 0.0) -> float:
    if x is None:
        return float(default)
    if isinstance(x, bool):
        return float(int(x))
    try:
        return float(x)
    except Exception:
        return float(default)


def _to_int01(x: Any) -> int:
    if isinstance(x, bool):
        return int(x)
    if x is None:
        return 0
    s = str(x).strip().lower()
    return 1 if s in {"1", "true", "yes", "y", "on"} else 0


def load_meta(meta_path: str) -> Dict[str, Any]:
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"last_timestamp": None}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


class MQTTOut:
    def __init__(self, enabled: bool, host: str, port: int, topic_prefix: str, qos: int) -> None:
        self.enabled = enabled
        self.host = host
        self.port = int(port)
        self.topic_prefix = topic_prefix
        self.qos = int(qos)
        self.client: Optional[mqtt.Client] = None

    def connect(self) -> None:
        if not self.enabled:
            logger.info("MQTT disabled (MQTT_ENABLED=0).")
            return
        c = mqtt.Client(client_id=f"edge-ai-predictor-{os.getpid()}", clean_session=True)
        c.connect(self.host, self.port, keepalive=60)
        c.loop_start()
        self.client = c
        logger.info(f"MQTT connected: {self.host}:{self.port} prefix={self.topic_prefix}")

    def close(self) -> None:
        if not self.client:
            return
        try:
            self.client.loop_stop()
        finally:
            try:
                self.client.disconnect()
            except Exception:
                pass

    def publish_prediction(self, asset_id: str, payload: Dict[str, Any]) -> None:
        if not self.client:
            return
        topic = f"{self.topic_prefix}/predictions/{asset_id}"
        self.client.publish(topic, json.dumps(payload, ensure_ascii=False, default=str), qos=self.qos, retain=False)


class PreprocessorRuntime:
    def __init__(self, bundle: Dict[str, Any]) -> None:
        self.numeric_cols: List[str] = list(bundle["numeric_cols"])
        self.categorical_cols: List[str] = list(bundle["categorical_cols"])
        self.scaler = bundle["scaler"]
        self.ohe = bundle["ohe"]

    def transform_one(self, d: Dict[str, Any]) -> np.ndarray:
        num_vals: List[float] = []
        for c in self.numeric_cols:
            if c.startswith("cumulative_exposure."):
                num_vals.append(_to_float(_get_nested(d, c), 0.0))
            elif c == "door_open":
                num_vals.append(float(_to_int01(d.get("door_open"))))
            elif c == "refrigeration_failed":
                num_vals.append(float(_to_int01(d.get("refrigeration_failed"))))
            else:
                num_vals.append(_to_float(d.get(c), 0.0))

        cat_vals: List[str] = []
        for c in self.categorical_cols:
            cat_vals.append(str(d.get(c) or "unknown"))

        X_num = np.array(num_vals, dtype=np.float32).reshape(1, -1)
        X_cat = np.array(cat_vals, dtype=object).reshape(1, -1)

        X_num_s = self.scaler.transform(X_num).astype(np.float32)
        X_cat_o = self.ohe.transform(X_cat).astype(np.float32)

        x = np.concatenate([X_num_s, X_cat_o], axis=1).reshape(-1).astype(np.float32)
        return x


class PredictorService:
    def __init__(self, cfg: PredictConfig) -> None:
        self.cfg = cfg
        if not cfg.mongodb_uri:
            raise ValueError("MONGODB_URI is required (MongoDB Atlas connection string)")

        self.meta = load_meta(cfg.meta_path)
        self.seq_len = int(self.meta["seq_len"])

        preproc_path = self.meta["artifacts"]["preprocessor_path"]
        bundle = joblib.load(preproc_path)
        self.preproc = PreprocessorRuntime(bundle)

        self.feature_dim = int(self.meta["input_schema"]["feature_dim"])
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = create_model(
            num_features=self.feature_dim,
            hidden_size=int(self.meta["model"]["hidden_size"]),
            num_layers=int(self.meta["model"]["num_layers"]),
            dropout=float(self.meta["model"]["dropout"]),
            output_activation=str(self.meta["model"]["output_activation"]),
        ).to(self.device)

        state = torch.load(cfg.model_path, map_location="cpu")
        self.model.load_state_dict(state)
        self.model.eval()

        self.buffers: Dict[str, Deque[np.ndarray]] = {}
        self.mqtt_out = MQTTOut(cfg.mqtt_enabled, cfg.mqtt_host, cfg.mqtt_port, cfg.mqtt_topic_prefix, cfg.mqtt_qos)

        logger.info("Connecting to MongoDB...")
        self.mongo = MongoClient(cfg.mongodb_uri)
        self.test_coll = self.mongo[cfg.mongodb_db][cfg.testing_collection]
        self.mongo_pred = MongoClient(cfg.mongodb_uri_2)
        self.pred_coll = self.mongo_pred[cfg.mongodb_db][cfg.predictions_collection]

        self._ensure_indexes()

        logger.info("=== Predictor Initialized ===")
        logger.info(f"TEST DB={cfg.mongodb_db}.{cfg.testing_collection} | "f"PRED DB={cfg.mongodb_db}.{cfg.predictions_collection}")
        logger.info(f"SEQ_LEN={self.seq_len} feature_dim={self.feature_dim} device={self.device}")
        logger.info(f"Poll every {cfg.poll_interval_sec}s | batch_limit={cfg.batch_limit}")

    def _ensure_indexes(self) -> None:
        try:
            self.pred_coll.create_index([("asset_id", 1), ("timestamp", 1)], unique=True)
            self.test_coll.create_index([("timestamp", 1)])
        except Exception:
            pass

    def close(self) -> None:
        try:
            self.mqtt_out.close()
        finally:
            try:
                self.mongo.close()
            except Exception:
                pass
            try:
                self.mongo_pred.close()
            except Exception:
                pass

    def _get_buffer(self, asset_id: str) -> Deque[np.ndarray]:
        if asset_id not in self.buffers:
            self.buffers[asset_id] = deque(maxlen=self.seq_len)
        return self.buffers[asset_id]

    @torch.no_grad()
    def _predict_from_buffer(self, buf: Deque[np.ndarray]) -> float:
        X = np.stack(list(buf), axis=0).astype(np.float32)
        Xt = torch.from_numpy(X).float().unsqueeze(0).to(self.device)
        y = float(self.model(Xt).detach().cpu().numpy().reshape(-1)[0])
        return y

    @staticmethod
    def _estimate_time_to_failure_hours(pred_risk: float) -> float:
        """
        Convert normalized risk score (0..1) to estimated time-to-failure hours.
        Higher predicted risk => lower remaining safe time.
        """
        risk = max(0.0, min(1.0, float(pred_risk)))
        min_hours = 6.0
        max_hours = 72.0
        estimated = max_hours - (risk * (max_hours - min_hours))
        return round(max(min_hours, min(max_hours, estimated)), 1)

    def poll_and_predict_forever(self) -> None:
        self.mqtt_out.connect()

        state = load_state(self.cfg.state_path)
        last_ts = state.get("last_timestamp")
        logger.info(f"Starting polling loop | last_timestamp={last_ts}")

        while True:
            query: Dict[str, Any] = {}
            if last_ts:
                query["timestamp"] = {"$gt": last_ts}

            cursor = (
                self.test_coll.find(
                    query,
                    projection={
                        "_id": 1,
                        "asset_id": 1,
                        "timestamp": 1,
                        "cargo_type": 1,
                        "scenario": 1,
                        "temperature": 1,
                        "humidity": 1,
                        "vibration": 1,
                        "door_open": 1,
                        "gps_lat": 1,
                        "gps_lon": 1,
                        "refrigeration_failed": 1,
                        "cumulative_exposure": 1,
                        "risk_proxy": 1,
                    },
                )
                .sort("timestamp", 1)
                .limit(self.cfg.batch_limit)
            )

            docs = list(cursor)
            if not docs:
                logger.info("No new testing docs. Sleeping...")
                time.sleep(self.cfg.poll_interval_sec)
                continue

            logger.info(f"Fetched {len(docs)} new testing docs...")
            ops: List[UpdateOne] = []
            predicted_count = 0

            for d in docs:
                asset_id = d.get("asset_id")
                ts = d.get("timestamp")
                if not asset_id or not ts:
                    continue

                asset_id = str(asset_id)
                x_vec = self.preproc.transform_one(d)

                buf = self._get_buffer(asset_id)
                buf.append(x_vec)

                if len(buf) < self.seq_len:
                    last_ts = ts
                    continue

                pred_risk = self._predict_from_buffer(buf)
                actual_risk = _to_float(d.get("risk_proxy"), 0.0)
                time_to_failure_hours = self._estimate_time_to_failure_hours(pred_risk)

                pred_doc = {
                    "asset_id": asset_id,
                    "timestamp": ts,
                    "predicted_risk_proxy": float(pred_risk),
                    "actual_risk_proxy": float(actual_risk),
                    "time_to_failure_hours": float(time_to_failure_hours),
                    "source_doc_id": d.get("_id"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "model_meta_path": self.cfg.meta_path,
                    "model_path": self.cfg.model_path,
                }

                ops.append(
                    UpdateOne(
                        {"asset_id": asset_id, "timestamp": ts},
                        {"$set": pred_doc},
                        upsert=True,
                    )
                )

                self.mqtt_out.publish_prediction(
                    asset_id,
                    {
                        "asset_id": asset_id,
                        "timestamp": ts,
                        "predicted_risk_proxy": float(pred_risk),
                        "time_to_failure_hours": float(time_to_failure_hours),
                    },
                )

                predicted_count += 1
                last_ts = ts

            if ops:
                try:
                    self.pred_coll.bulk_write(ops, ordered=False)
                    logger.info(f"Wrote {len(ops)} predictions to MongoDB (upsert).")
                except Exception as e:
                    logger.warning(f"Mongo bulk_write failed: {e}")

            state["last_timestamp"] = last_ts
            save_state(self.cfg.state_path, state)

            logger.info(
                f"Cycle done | predicted={predicted_count} assets_cached={len(self.buffers)} last_ts={last_ts}"
            )
            time.sleep(self.cfg.poll_interval_sec)


def main() -> None:
    load_dotenv()
    cfg = load_config()
    service = PredictorService(cfg)
    try:
        service.poll_and_predict_forever()
    finally:
        service.close()


if __name__ == "__main__":
    main()