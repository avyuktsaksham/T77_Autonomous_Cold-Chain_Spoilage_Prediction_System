from __future__ import annotations
import random
import os
import json
import time
import argparse
import socket
import ssl
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from pymongo import MongoClient

import paho.mqtt.client as mqtt

from sensors import (
    ColdChainSensorSimulator,
    FleetSimulator,
    create_default_fleet,
    ShipmentScenario,
    Route,
    CARGO_PROFILES,
)


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return int(v)


def _env_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v is None:
        return default
    return v


def _safe_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)

def init_mongo():
    uri = os.getenv("MONGODB_URI", "").strip()
    db_name = os.getenv("MONGODB_DB", "cold_chain_database").strip()
    train_collname = os.getenv("MONGODB_COLLECTION_TRAINING", "sensors_data_training").strip()
    test_collname  = os.getenv("MONGODB_COLLECTION_TESTING",  "sensors_data_testing").strip()

    if not uri:
        return None, None, None

    client = MongoClient(uri)
    db = client[db_name]
    train_coll = db[train_collname]
    test_coll = db[test_collname]
    return client, train_coll, test_coll

def fancy_print_telemetry(t: Dict[str, Any]):
    ts = t.get("timestamp", "")
    asset = t.get("asset_id", "UNKNOWN")
    cargo = t.get("cargo_type", "UNKNOWN")

    temp = t.get("temperature")
    hum = t.get("humidity")
    vib = t.get("vibration")
    door_open = bool(t.get("door_open", False))
    lat = t.get("gps_lat")
    lon = t.get("gps_lon")

    scenario = t.get("scenario", "")
    failed = bool(t.get("refrigeration_failed", False))
    risk = t.get("risk_proxy")

    door_txt = "OPEN ❌" if door_open else "CLOSED ✅"
    fail_txt = "YES ❌" if failed else "NO ✅"

    print(f"\n[{ts}]")
    print(f"  🚚 Truck: {asset} | 🧊 Cargo: {cargo} | 🎛️ Scenario: {scenario} | ❄️ Fail: {fail_txt}")
    print(f"  🌡️  Temp: {temp}°C")
    print(f"  💧 Humidity: {hum}%")
    print(f"  📳 Vibration: {vib}")
    print(f"  🚪 Door: {door_txt}")
    print(f"  📍 GPS: ({lat}, {lon})")
    print(f"  ⚠️  Risk: {risk}")
    print("-" * 60)

class MQTTPublisher:
    def __init__(
        self,
        host: str,
        port: int,
        topic_prefix: str = "coldchain",
        username: str = "",
        password: str = "",
        qos: int = 1,
        keepalive: int = 60,
        publisher_id: str = "iot-sim-publisher",
        tls_enabled: bool = False,
        ca_cert: str = "",
        client_cert: str = "",
        client_key: str = "",
        tls_insecure: bool = False,
        client_id: Optional[str] = None,
    ):
        self.host = host
        self.port = int(port)
        self.topic_prefix = topic_prefix.strip().strip("/")
        self.username = username
        self.password = password
        self.qos = int(qos)
        self.keepalive = int(keepalive)
        self.publisher_id = publisher_id

        self.tls_enabled = tls_enabled
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self.tls_insecure = tls_insecure

        if client_id is None:
            client_id = f"{publisher_id}-{socket.gethostname()}-{os.getpid()}"

        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311, clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        if self.username:
            self.client.username_pw_set(self.username, self.password)

        self.status_topic = f"{self.topic_prefix}/status/{self.publisher_id}"
        self.client.will_set(
            topic=self.status_topic,
            payload=_safe_json({"publisher_id": self.publisher_id, "status": "offline"}),
            qos=1,
            retain=True,
        )

        if self.tls_enabled:
            tls_kwargs = {}
            if self.ca_cert:
                tls_kwargs["ca_certs"] = self.ca_cert
            if self.client_cert:
                tls_kwargs["certfile"] = self.client_cert
            if self.client_key:
                tls_kwargs["keyfile"] = self.client_key
            self.client.tls_set(**tls_kwargs, tls_version=ssl.PROTOCOL_TLS_CLIENT)
            self.client.tls_insecure_set(bool(self.tls_insecure))

        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = (rc == 0)
        if self.connected:
            client.publish(
                self.status_topic,
                payload=_safe_json({"publisher_id": self.publisher_id, "status": "online"}),
                qos=1,
                retain=True,
            )

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False

    def connect(self):
        self.client.connect(self.host, self.port, keepalive=self.keepalive)
        self.client.loop_start()

        t0 = time.time()
        while not self.connected and (time.time() - t0) < 5:
            time.sleep(0.05)

    def close(self):
        try:
            self.client.publish(
                self.status_topic,
                payload=_safe_json({"publisher_id": self.publisher_id, "status": "offline"}),
                qos=1,
                retain=True,
            )
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

    def topic_telemetry_asset(self, asset_id: str) -> str:
        return f"{self.topic_prefix}/telemetry/{asset_id}"

    def topic_telemetry_all(self) -> str:
        return f"{self.topic_prefix}/telemetry/all"

    def publish_asset_telemetry(self, telemetry: Dict[str, Any]):
        asset_id = telemetry.get("asset_id", "UNKNOWN")
        topic = self.topic_telemetry_asset(str(asset_id))
        payload = _safe_json(telemetry)
        self.client.publish(topic, payload=payload, qos=self.qos, retain=False)

    def publish_batch_all(self, telemetry_list: List[Dict[str, Any]]):
        payload = _safe_json({"publisher_id": self.publisher_id, "batch": telemetry_list})
        self.client.publish(self.topic_telemetry_all(), payload=payload, qos=self.qos, retain=False)


def run_fleet_mode(pub: MQTTPublisher, interval_sec: int, fleet_size: int, fancy: bool = True):
    fleet: FleetSimulator = create_default_fleet(publish_interval_sec=interval_sec, fleet_size=fleet_size)
    mongoclient, train_coll, test_coll = init_mongo()
    split = float(os.getenv("TRAIN_SPLIT", "0.8"))
    while True:
        batch = fleet.tick_all()
        if train_coll is not None and test_coll is not None:
            train_docs = []
            test_docs = []
            for doc in batch:
                if random.random() < split:
                    train_docs.append(doc)
                else:
                    test_docs.append(doc)
            if train_docs:
                train_coll.insert_many(train_docs)
            if test_docs:
                test_coll.insert_many(test_docs)
        for t in batch:
            pub.publish_asset_telemetry(t)
            fancy_print_telemetry(t)

        pub.publish_batch_all(batch)
        time.sleep(interval_sec)


def run_single_mode(
    pub: MQTTPublisher,
    interval_sec: int,
    asset_id: str,
    cargo_type: str,
    scenario_name: str,
):
    cargo_type = cargo_type.strip().lower()
    if cargo_type not in CARGO_PROFILES:
        raise ValueError(f"Unknown cargo_type '{cargo_type}'. Supported: {list(CARGO_PROFILES.keys())}")

    if scenario_name == "normal":
        scenario = ShipmentScenario.normal()
    elif scenario_name == "micro_excursions":
        scenario = ShipmentScenario.micro_excursions()
    elif scenario_name == "refrigeration_failure":
        scenario = ShipmentScenario.refrigeration_failure(fail_at_min=25)
    else:
        raise ValueError("scenario must be one of: normal, micro_excursions, refrigeration_failure")

    route = Route(
        origin=(27.1767, 78.0081),
        destination=(28.7041, 77.1025),
        waypoints=[(27.4924, 77.6737)]
    )

    sim = ColdChainSensorSimulator(
        asset_id=asset_id,
        cargo_type=cargo_type,
        scenario=scenario,
        route=route,
        publish_interval_sec=interval_sec,
        seed=7
    )
    mongoclient, train_coll, test_coll = init_mongo()
    split = float(os.getenv("TRAIN_SPLIT", "0.8"))
    while True:
        t = sim.get_telemetry()
        if train_coll is not None and test_coll is not None:
            if random.random() < split:
                train_coll.insert_one(t)
            else:
                test_coll.insert_one(t)
        pub.publish_asset_telemetry(t)
        fancy_print_telemetry(t)
        time.sleep(interval_sec)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cold-chain telemetry MQTT publisher (single or fleet).")

    p.add_argument("--mode", choices=["fleet", "single"], default="fleet")

    p.add_argument("--host", default=_env_str("MQTT_HOST", "localhost"))
    p.add_argument("--port", type=int, default=_env_int("MQTT_PORT", 1882))
    p.add_argument("--username", default=_env_str("MQTT_USERNAME", ""))
    p.add_argument("--password", default=_env_str("MQTT_PASSWORD", ""))

    p.add_argument("--topic-prefix", default=_env_str("MQTT_TOPIC_PREFIX", "coldchain"))
    p.add_argument("--qos", type=int, default=_env_int("MQTT_QOS", 1))
    p.add_argument("--keepalive", type=int, default=_env_int("MQTT_KEEPALIVE", 60))
    p.add_argument("--publisher-id", default=_env_str("MQTT_PUBLISHER_ID", "iot-sim-publisher"))

    p.add_argument("--tls", action="store_true", default=_env_bool("MQTT_TLS", False))
    p.add_argument("--ca-cert", default=_env_str("MQTT_CA_CERT", ""))
    p.add_argument("--client-cert", default=_env_str("MQTT_CLIENT_CERT", ""))
    p.add_argument("--client-key", default=_env_str("MQTT_CLIENT_KEY", ""))
    p.add_argument("--tls-insecure", action="store_true", default=_env_bool("MQTT_TLS_INSECURE", False))

    p.add_argument("--interval", type=int, default=_env_int("PUBLISH_INTERVAL_SEC", 2))
    p.add_argument("--fleet-size", type=int, default=_env_int("FLEET_SIZE", 50))

    p.add_argument("--asset-id", default="TRUCK_001")
    p.add_argument("--cargo-type", default="vaccines")
    p.add_argument("--scenario", choices=["normal", "micro_excursions", "refrigeration_failure"], default="micro_excursions")

    return p


def main():
    load_dotenv()
    args = build_arg_parser().parse_args()

    pub = MQTTPublisher(
        host=args.host,
        port=args.port,
        topic_prefix=args.topic_prefix,
        username=args.username,
        password=args.password,
        qos=args.qos,
        keepalive=args.keepalive,
        publisher_id=args.publisher_id,
        tls_enabled=bool(args.tls),
        ca_cert=args.ca_cert,
        client_cert=args.client_cert,
        client_key=args.client_key,
        tls_insecure=bool(args.tls_insecure),
    )

    pub.connect()

    print(f"✅ Connected to MQTT Broker at {args.host}:{args.port}")
    print("🚚 Cold-Chain IoT Telemetry Publisher Started")
    print("=" * 60)
    print(f"📡 Publishing to: mqtt://{args.host}:{args.port}")
    print(f"🔄 Interval: {args.interval}s")
    if args.mode == "single":
        print(f"📦 Asset ID: {args.asset_id}")
        print(f"🧊 Cargo Type: {args.cargo_type}")
    else:
        print("📦 Mode: fleet (multi-truck)")
        print("=" * 60)


    try:
        if args.mode == "fleet":
            run_fleet_mode(pub, interval_sec=args.interval, fleet_size=args.fleet_size, fancy=True)
        else:
            run_single_mode(
                pub,
                interval_sec=args.interval,
                asset_id=args.asset_id,
                cargo_type=args.cargo_type,
                scenario_name=args.scenario,
            )
    except KeyboardInterrupt:
        pass
    finally:
        pub.close()


if __name__ == "__main__":
    main()