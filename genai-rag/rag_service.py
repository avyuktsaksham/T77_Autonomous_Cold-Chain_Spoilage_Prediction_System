from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import chromadb
from chromadb.config import Settings

try:
    from openai import OpenAI  # openai>=1.x
except Exception:  # pragma: no cover
    OpenAI = None

try:
    import openai as openai_legacy  # fallback for older SDKs
except Exception:  # pragma: no cover
    openai_legacy = None


LOGLEVEL = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOGLEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("rag-service")


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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    if isinstance(value, bool):
        return float(int(value))
    try:
        return float(value)
    except Exception:
        return float(default)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clamp01(value: Any) -> float:
    return clamp(safe_float(value, 0.0), 0.0, 1.0)


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def deepcopy_dict(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    copied: Dict[str, Any] = {}
    for k, v in value.items():
        if isinstance(v, dict):
            copied[k] = deepcopy_dict(v)
        elif isinstance(v, list):
            copied[k] = list(v)
        else:
            copied[k] = v
    return copied


def get_first(data: Optional[Dict[str, Any]], keys: Sequence[str], default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


@dataclass
class RAGServiceConfig:
    vectorstore_path: str
    collection_name: str
    openai_api_key: str
    openai_model: str
    openai_temperature: float
    max_sop_results: int
    max_explanation_tokens: int
    max_decision_tokens: int


def load_config() -> RAGServiceConfig:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return RAGServiceConfig(
        vectorstore_path=envstr("VECTORSTORE_PATH", os.path.join(base_dir, "vectorstore")),
        collection_name=envstr("CHROMA_COLLECTION_NAME", "coldchainsops"),
        openai_api_key=envstr("OPENAI_API_KEY", envstr("OPENAIAPIKEY", "")),
        openai_model=envstr("OPENAI_MODEL", "gpt-4o-mini"),
        openai_temperature=envfloat("OPENAI_TEMPERATURE", 0.2),
        max_sop_results=max(1, envint("RAG_MAX_SOP_RESULTS", 4)),
        max_explanation_tokens=max(128, envint("RAG_MAX_EXPLANATION_TOKENS", 350)),
        max_decision_tokens=max(96, envint("RAG_MAX_DECISION_TOKENS", 220)),
    )


class RAGExplanationService:
    """
    RAG service for risk and decision explanations.

    Aligns with:
    - telemetry payloads from iot-simulator/mqtt_publisher.py
    - prediction payloads from edge-ai/predict.py
    - decision payloads from agentic-ai/decision_engine.py and decision_agent.py
    - SOP retrieval from genai-rag/setup_vectorstore.py
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        vectorstore_path: Optional[str] = None,
        collection_name: Optional[str] = None,
        openai_model: Optional[str] = None,
        config: Optional[RAGServiceConfig] = None,
    ) -> None:
        self.config = config or load_config()

        if openai_api_key is not None:
            self.config.openai_api_key = str(openai_api_key).strip()
        if vectorstore_path is not None:
            self.config.vectorstore_path = str(vectorstore_path).strip()
        if collection_name is not None:
            self.config.collection_name = str(collection_name).strip()
        if openai_model is not None:
            self.config.openai_model = str(openai_model).strip()

        self.client = chromadb.PersistentClient(
            path=self.config.vectorstore_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self._resolve_collection()

        self.openai_client = None
        if self.config.openai_api_key:
            self.openai_client = self._build_openai_client(self.config.openai_api_key)

        logger.info(
            "RAG service initialized | vectorstore=%s | collection=%s | model=%s",
            self.config.vectorstore_path,
            self.collection.name,
            self.config.openai_model,
        )

    # -------------------------------------------------------------------------
    # Initialization helpers
    # -------------------------------------------------------------------------

    def _resolve_collection(self):
        candidate_names = [
            self.config.collection_name,
            "coldchainsops",
            "cold_chain_sops",
            "cold-chain-sops",
        ]

        seen = set()
        for name in candidate_names:
            name = safe_str(name)
            if not name or name in seen:
                continue
            seen.add(name)
            try:
                return self.client.get_collection(name=name)
            except Exception:
                continue

        try:
            collections = self.client.list_collections()
        except Exception as exc:
            raise RuntimeError(
                f"Unable to find Chroma collection. Checked {candidate_names} in {self.config.vectorstore_path}"
            ) from exc

        if collections:
            first = collections[0]
            first_name = getattr(first, "name", None) or str(first)
            return self.client.get_collection(name=first_name)

        raise RuntimeError(
            f"No Chroma collection found in {self.config.vectorstore_path}. "
            f"Run setup_vectorstore.py first."
        )

    def _build_openai_client(self, api_key: str):
        if OpenAI is not None:
            return OpenAI(api_key=api_key)

        if openai_legacy is not None:
            openai_legacy.api_key = api_key
            return None

        raise RuntimeError("OpenAI SDK is not installed.")

    # -------------------------------------------------------------------------
    # Normalization
    # -------------------------------------------------------------------------

    def normalize_telemetry(self, telemetry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        base = deepcopy_dict(telemetry)
        exposure = get_first(base, ["cumulativeexposure", "cumulative_exposure"], {})
        if not isinstance(exposure, dict):
            exposure = {}

        normalized = {
            "assetid": safe_str(get_first(base, ["assetid", "asset_id"], "UNKNOWNASSET"), "UNKNOWNASSET"),
            "timestamp": safe_str(get_first(base, ["timestamp", "ts"], now_iso()), now_iso()),
            "temperature": safe_float(get_first(base, ["temperature", "currenttemp", "temp"], 0.0), 0.0),
            "humidity": safe_float(get_first(base, ["humidity", "currenthumidity"], 0.0), 0.0),
            "vibration": safe_float(get_first(base, ["vibration"], 0.0), 0.0),
            "dooropen": to_bool(get_first(base, ["dooropen", "door_open"], False)),
            "gpslat": safe_float(get_first(base, ["gpslat", "gps_lat", "latitude"], 0.0), 0.0),
            "gpslon": safe_float(get_first(base, ["gpslon", "gps_lon", "longitude"], 0.0), 0.0),
            "cargotype": safe_str(get_first(base, ["cargotype", "cargo_type"], "unknown"), "unknown").lower(),
            "scenario": safe_str(get_first(base, ["scenario"], "unknown"), "unknown").lower(),
            "refrigerationfailed": to_bool(
                get_first(base, ["refrigerationfailed", "refrigeration_failed"], False)
            ),
            "riskproxy": clamp01(get_first(base, ["riskproxy", "risk_proxy", "telemetryriskproxy"], 0.0)),
            "cumulativeexposure": {
                "tempdegreeminutes": safe_float(
                    get_first(exposure, ["tempdegreeminutes", "temp_degree_minutes"], 0.0), 0.0
                ),
                "humiditypercentminutes": safe_float(
                    get_first(exposure, ["humiditypercentminutes", "humidity_percent_minutes"], 0.0), 0.0
                ),
                "dooropenminutes": safe_float(
                    get_first(exposure, ["dooropenminutes", "door_open_minutes"], 0.0), 0.0
                ),
                "vibrationwarnminutes": safe_float(
                    get_first(exposure, ["vibrationwarnminutes", "vibration_warn_minutes"], 0.0), 0.0
                ),
                "vibrationcriticalminutes": safe_float(
                    get_first(exposure, ["vibrationcriticalminutes", "vibration_critical_minutes"], 0.0), 0.0
                ),
                "outofrangeminutesinhour": safe_float(
                    get_first(exposure, ["outofrangeminutesinhour", "out_of_range_minutes_in_hour"], 0.0), 0.0
                ),
            },
            "raw": base,
        }
        return normalized

    def normalize_prediction(self, prediction: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        base = deepcopy_dict(prediction)

        predicted_risk = clamp01(
            get_first(
                base,
                [
                    "predictedriskproxy",
                    "predicted_risk_proxy",
                    "riskscore",
                    "risk_score",
                    "riskproxy",
                    "actualriskproxy",
                ],
                0.0,
            )
        )

        actual_risk = clamp01(
            get_first(base, ["actualriskproxy", "actual_risk_proxy", "riskproxy"], 0.0)
        )

        timetofailurehours = self._extract_ttf(base)

        normalized = {
            "assetid": safe_str(get_first(base, ["assetid", "asset_id"], "UNKNOWNASSET"), "UNKNOWNASSET"),
            "timestamp": safe_str(get_first(base, ["timestamp", "ts"], now_iso()), now_iso()),
            "predictedriskproxy": predicted_risk,
            "actualriskproxy": actual_risk,
            "riskscore": predicted_risk if predicted_risk > 0 else actual_risk,
            "confidence": clamp01(get_first(base, ["confidence", "predictionconfidence"], 0.0)),
            "timetofailurehours": timetofailurehours,
            "currenttemp": safe_float(get_first(base, ["currenttemp", "temperature"], 0.0), 0.0),
            "currenthumidity": safe_float(get_first(base, ["currenthumidity", "humidity"], 0.0), 0.0),
            "raw": base,
        }
        return normalized

    def normalize_decision(self, decision: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        base = deepcopy_dict(decision)
        analysis = get_first(base, ["analysis"], {})
        if not isinstance(analysis, dict):
            analysis = {}

        actions = get_first(base, ["actions"], [])
        if not isinstance(actions, list):
            actions = []

        executionresults = get_first(base, ["executionresults", "execution_results"], [])
        if not isinstance(executionresults, list):
            executionresults = []

        normalized_actions = [self._normalize_action(a) for a in actions if isinstance(a, dict)]
        normalized_analysis = {
            "riskscore": clamp01(
                get_first(analysis, ["riskscore", "risk_score", "predictedriskproxy", "riskproxy"], 0.0)
            ),
            "risklevel": safe_str(get_first(analysis, ["risklevel", "risk_level"], ""), "").lower(),
            "contributingfactors": [
                str(x).strip()
                for x in get_first(analysis, ["contributingfactors", "contributing_factors"], [])
                if str(x).strip()
            ],
            "timetofailurehours": self._extract_ttf(analysis) or self._extract_ttf(base),
            "requiresaction": bool(get_first(analysis, ["requiresaction", "requires_action"], False)),
            "temperaturestatus": safe_str(
                get_first(analysis, ["temperaturestatus", "temperature_status"], ""), ""
            ).lower(),
        }

        normalized = {
            "decisionid": safe_str(get_first(base, ["decisionid", "decision_id"], ""), ""),
            "timestamp": safe_str(get_first(base, ["timestamp", "ts"], now_iso()), now_iso()),
            "assetid": safe_str(get_first(base, ["assetid", "asset_id"], "UNKNOWNASSET"), "UNKNOWNASSET"),
            "analysis": normalized_analysis,
            "actions": normalized_actions,
            "executionresults": executionresults,
            "telemetry": deepcopy_dict(get_first(base, ["telemetry"], {})),
            "prediction": deepcopy_dict(get_first(base, ["prediction"], {})),
            "raw": base,
        }
        return normalized

    def _normalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": safe_str(get_first(action, ["type", "actiontype"], "unknown"), "unknown").lower(),
            "description": safe_str(get_first(action, ["description"], ""), ""),
            "priority": safe_str(get_first(action, ["priority"], "medium"), "medium").lower(),
            "tool": safe_str(get_first(action, ["tool"], ""), ""),
            "action": safe_str(get_first(action, ["action", "recommendedaction"], ""), ""),
            "targetdc": safe_str(get_first(action, ["targetdc"], ""), ""),
            "dcname": safe_str(get_first(action, ["dcname"], ""), ""),
            "etahours": safe_float(get_first(action, ["etahours"], 0.0), 0.0),
            "benefitscore": safe_float(get_first(action, ["benefitscore"], 0.0), 0.0),
            "raw": deepcopy_dict(action),
        }

    # -------------------------------------------------------------------------
    # Extraction helpers
    # -------------------------------------------------------------------------

    def _extract_ttf(self, data: Optional[Dict[str, Any]]) -> Optional[float]:
        if not isinstance(data, dict):
            return None
        for key in [
            "timetofailurehours",
            "time_to_failure_hours",
            "timetofailure",
            "eta_to_failure_hours",
            "etatofailurehours",
        ]:
            if key in data and data[key] is not None:
                value = safe_float(data[key], -1.0)
                return None if value < 0 else value
        return None

    def _merge_asset_identity(
        self,
        telemetry: Dict[str, Any],
        prediction: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ) -> None:
        asset = telemetry.get("assetid") or prediction.get("assetid") or (
            decision.get("assetid") if isinstance(decision, dict) else None
        )
        asset = safe_str(asset, "UNKNOWNASSET")

        if telemetry.get("assetid") in {"", "UNKNOWNASSET"}:
            telemetry["assetid"] = asset
        if prediction.get("assetid") in {"", "UNKNOWNASSET"}:
            prediction["assetid"] = asset
        if isinstance(decision, dict) and decision.get("assetid") in {"", "UNKNOWNASSET"}:
            decision["assetid"] = asset

    def extract_risk_score(
        self,
        prediction: Optional[Dict[str, Any]],
        telemetry: Optional[Dict[str, Any]],
        decision: Optional[Dict[str, Any]] = None,
    ) -> float:
        scores = []

        if isinstance(prediction, dict):
            scores.append(clamp01(get_first(prediction, ["predictedriskproxy", "riskscore"], 0.0)))
        if isinstance(telemetry, dict):
            scores.append(clamp01(get_first(telemetry, ["riskproxy"], 0.0)))
        if isinstance(decision, dict):
            analysis = get_first(decision, ["analysis"], {})
            if isinstance(analysis, dict):
                scores.append(clamp01(get_first(analysis, ["riskscore"], 0.0)))

        return max(scores) if scores else 0.0

    def derive_urgency(
        self,
        riskscore: float,
        telemetry: Optional[Dict[str, Any]] = None,
        prediction: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
    ) -> str:
        telemetry = telemetry or {}
        prediction = prediction or {}
        decision = decision or {}

        ttf = self._extract_ttf(prediction)
        if ttf is None:
            analysis = get_first(decision, ["analysis"], {})
            ttf = self._extract_ttf(analysis if isinstance(analysis, dict) else None)

        refrigeration_failed = to_bool(get_first(telemetry, ["refrigerationfailed"], False))
        door_open = to_bool(get_first(telemetry, ["dooropen"], False))

        if riskscore >= 0.95:
            urgency = "critical"
        elif riskscore >= 0.75:
            urgency = "high"
        elif riskscore >= 0.40:
            urgency = "moderate"
        else:
            urgency = "low"

        if refrigeration_failed:
            if urgency == "low":
                urgency = "moderate"
            elif urgency == "moderate":
                urgency = "high"

        if ttf is not None:
            if ttf <= 1.0:
                urgency = "critical"
            elif ttf <= 3.0 and urgency in {"low", "moderate"}:
                urgency = "high"

        if door_open and riskscore >= 0.70 and urgency == "moderate":
            urgency = "high"

        return urgency

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------

    def build_retrieval_query(
        self,
        prediction: Dict[str, Any],
        telemetry: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ) -> str:
        decision = decision or {}
        analysis = get_first(decision, ["analysis"], {})
        actions = get_first(decision, ["actions"], [])
        action_types = [
            safe_str(get_first(a, ["type"], ""), "").lower()
            for a in actions
            if isinstance(a, dict)
        ]

        riskscore = self.extract_risk_score(prediction, telemetry, decision)
        urgency = self.derive_urgency(riskscore, telemetry, prediction, decision)

        query_parts = [
            f"cargo {telemetry.get('cargotype', 'unknown')}",
            f"scenario {telemetry.get('scenario', 'unknown')}",
            f"temperature {telemetry.get('temperature', 0.0):.2f}C",
            f"humidity {telemetry.get('humidity', 0.0):.2f}",
            f"vibration {telemetry.get('vibration', 0.0):.2f}g",
            f"risk {riskscore:.3f}",
            f"urgency {urgency}",
            "temperature monitoring protocol",
            "spoilage assessment guideline",
        ]

        if telemetry.get("dooropen"):
            query_parts.append("door opening protocol")
        if telemetry.get("refrigerationfailed") or telemetry.get("scenario") == "refrigerationfailure":
            query_parts.append("refrigeration failure response backup cooling")
        if telemetry.get("humidity", 0.0) >= 70.0 or telemetry.get("humidity", 0.0) <= 20.0:
            query_parts.append("humidity control guidelines")
        if telemetry.get("vibration", 0.0) >= 5.0:
            query_parts.append("vibration exposure limits inspection")
        if "reroute" in action_types or "emergencyreroute" in action_types:
            query_parts.append("emergency rerouting nearest distribution center")
        if "adjustcooling" in action_types:
            query_parts.append("cooling adjustment response")
        if isinstance(analysis, dict):
            for factor in get_first(analysis, ["contributingfactors"], []):
                factor_text = safe_str(factor, "")
                if factor_text:
                    query_parts.append(factor_text)

        exposure = telemetry.get("cumulativeexposure", {})
        if isinstance(exposure, dict):
            if safe_float(exposure.get("tempdegreeminutes"), 0.0) > 0:
                query_parts.append("cumulative temperature exposure")
            if safe_float(exposure.get("dooropenminutes"), 0.0) > 0:
                query_parts.append("cumulative door opening")
            if safe_float(exposure.get("vibrationcriticalminutes"), 0.0) > 0:
                query_parts.append("critical vibration exposure")

        ttf = prediction.get("timetofailurehours")
        if ttf is not None:
            query_parts.append(f"time to failure {safe_float(ttf, 0.0):.2f} hours")

        return " | ".join(query_parts)

    def retrieve_relevant_sops(self, query: str, n_results: Optional[int] = None) -> List[Dict[str, Any]]:
        n = max(1, int(n_results or self.config.max_sop_results))
        results = self.collection.query(query_texts=[query], n_results=n)

        ids = results.get("ids", [[]])
        docs = results.get("documents", [[]])
        metas = results.get("metadatas", [[]])
        distances = results.get("distances", [[]])

        out: List[Dict[str, Any]] = []
        seen = set()

        first_ids = ids[0] if ids else []
        first_docs = docs[0] if docs else []
        first_metas = metas[0] if metas else []
        first_distances = distances[0] if distances else []

        for i in range(len(first_ids)):
            sop_id = safe_str(first_ids[i], f"SOP{i+1}")
            if sop_id in seen:
                continue
            seen.add(sop_id)
            out.append(
                {
                    "id": sop_id,
                    "content": first_docs[i] if i < len(first_docs) else "",
                    "metadata": first_metas[i] if i < len(first_metas) and isinstance(first_metas[i], dict) else {},
                    "distance": safe_float(first_distances[i], 0.0) if i < len(first_distances) else 0.0,
                }
            )

        return out

    def _format_sop_context(self, sop_docs: List[Dict[str, Any]]) -> str:
        blocks = []
        for doc in sop_docs:
            metadata = doc.get("metadata", {}) or {}
            meta_parts = []
            for key in ["source", "category", "type"]:
                value = metadata.get(key)
                if value is not None:
                    meta_parts.append(f"{key}={value}")
            meta_text = f" ({', '.join(meta_parts)})" if meta_parts else ""
            blocks.append(f"[{doc.get('id', 'SOP')}] {doc.get('content', '').strip()}{meta_text}")
        return "\n".join(blocks).strip()

    # -------------------------------------------------------------------------
    # LLM
    # -------------------------------------------------------------------------

    def _call_llm(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        if not self.config.openai_api_key:
            raise RuntimeError("OpenAI API key not configured.")

        if self.openai_client is not None:
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=messages,
                temperature=self.config.openai_temperature,
                max_tokens=max_tokens,
            )
            return (response.choices[0].message.content or "").strip()

        if openai_legacy is not None:
            openai_legacy.api_key = self.config.openai_api_key
            response = openai_legacy.ChatCompletion.create(
                model=self.config.openai_model,
                messages=messages,
                temperature=self.config.openai_temperature,
                max_tokens=max_tokens,
            )
            return (response["choices"][0]["message"]["content"] or "").strip()

        raise RuntimeError("OpenAI SDK is unavailable.")

    # -------------------------------------------------------------------------
    # Prompt builders
    # -------------------------------------------------------------------------

    def _build_risk_prompt(
        self,
        telemetry: Dict[str, Any],
        prediction: Dict[str, Any],
        decision: Optional[Dict[str, Any]],
        sop_docs: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        decision = decision or {}
        riskscore = self.extract_risk_score(prediction, telemetry, decision)
        urgency = self.derive_urgency(riskscore, telemetry, prediction, decision)

        compact_telemetry = {
            "assetid": telemetry.get("assetid"),
            "timestamp": telemetry.get("timestamp"),
            "cargotype": telemetry.get("cargotype"),
            "scenario": telemetry.get("scenario"),
            "temperature": telemetry.get("temperature"),
            "humidity": telemetry.get("humidity"),
            "vibration": telemetry.get("vibration"),
            "dooropen": telemetry.get("dooropen"),
            "gpslat": telemetry.get("gpslat"),
            "gpslon": telemetry.get("gpslon"),
            "refrigerationfailed": telemetry.get("refrigerationfailed"),
            "riskproxy": telemetry.get("riskproxy"),
            "cumulativeexposure": telemetry.get("cumulativeexposure"),
        }

        compact_prediction = {
            "assetid": prediction.get("assetid"),
            "timestamp": prediction.get("timestamp"),
            "predictedriskproxy": prediction.get("predictedriskproxy"),
            "actualriskproxy": prediction.get("actualriskproxy"),
            "riskscore": riskscore,
            "confidence": prediction.get("confidence"),
            "timetofailurehours": prediction.get("timetofailurehours"),
        }

        compact_decision = {}
        if decision:
            compact_decision = {
                "decisionid": decision.get("decisionid"),
                "timestamp": decision.get("timestamp"),
                "analysis": decision.get("analysis"),
                "actions": [
                    {
                        "type": a.get("type"),
                        "description": a.get("description"),
                        "priority": a.get("priority"),
                    }
                    for a in decision.get("actions", [])
                ],
            }

        system_prompt = (
            "You are a cold-chain operations explainability assistant. "
            "Use only the supplied telemetry, prediction, decision context, and SOP snippets. "
            "Explain the main risk drivers clearly, reference SOP IDs exactly as given, "
            "and keep the answer concise, operational, and factual."
        )

        user_prompt = f"""
Current risk context:
- Asset ID: {telemetry.get('assetid')}
- Combined Risk Score: {riskscore:.3f}
- Urgency: {urgency}
- Estimated Time to Failure (hours): {prediction.get('timetofailurehours')}

Telemetry:
{json.dumps(compact_telemetry, indent=2, ensure_ascii=False)}

Prediction:
{json.dumps(compact_prediction, indent=2, ensure_ascii=False)}

Decision:
{json.dumps(compact_decision, indent=2, ensure_ascii=False)}

Relevant SOPs:
{self._format_sop_context(sop_docs)}

Write a single explanation in under 180 words that:
1. Explains why the risk is at this level.
2. Mentions the most relevant contributing factors.
3. Mentions the most relevant action or next step.
4. References SOP IDs directly in the text.
Return plain text only.
""".strip()

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_decision_prompt(
        self,
        decision: Dict[str, Any],
        telemetry: Dict[str, Any],
        prediction: Dict[str, Any],
        sop_docs: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        riskscore = self.extract_risk_score(prediction, telemetry, decision)
        urgency = self.derive_urgency(riskscore, telemetry, prediction, decision)

        action_lines = []
        for action in decision.get("actions", []):
            desc = action.get("description") or action.get("type") or "unknown action"
            prio = action.get("priority") or "unknown"
            action_lines.append(f"- {desc} (priority={prio})")

        actions_block = "\n".join(action_lines) if action_lines else "- No actions listed"

        system_prompt = (
            "You are a cold-chain operations assistant explaining autonomous decisions. "
            "Justify the actions using the supplied decision data and SOPs only. "
            "Keep the explanation short, direct, and operational."
        )

        user_prompt = f"""
Decision context:
- Asset ID: {decision.get('assetid')}
- Decision ID: {decision.get('decisionid')}
- Risk Score: {riskscore:.3f}
- Urgency: {urgency}
- Time to Failure (hours): {prediction.get('timetofailurehours')}

Decision Analysis:
{json.dumps(decision.get('analysis', {}), indent=2, ensure_ascii=False)}

Actions:
{actions_block}

Telemetry:
{json.dumps({
    "temperature": telemetry.get("temperature"),
    "humidity": telemetry.get("humidity"),
    "vibration": telemetry.get("vibration"),
    "dooropen": telemetry.get("dooropen"),
    "scenario": telemetry.get("scenario"),
    "refrigerationfailed": telemetry.get("refrigerationfailed"),
    "riskproxy": telemetry.get("riskproxy"),
}, indent=2, ensure_ascii=False)}

Relevant SOPs:
{self._format_sop_context(sop_docs)}

Write a brief explanation in under 120 words that:
1. Explains why these actions are justified.
2. Mentions urgency.
3. References SOP IDs directly in the text.
Return plain text only.
""".strip()

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    # -------------------------------------------------------------------------
    # Fallbacks
    # -------------------------------------------------------------------------

    def _fallback_risk_explanation(
        self,
        telemetry: Dict[str, Any],
        prediction: Dict[str, Any],
        decision: Optional[Dict[str, Any]],
        sop_docs: List[Dict[str, Any]],
    ) -> str:
        decision = decision or {}
        riskscore = self.extract_risk_score(prediction, telemetry, decision)
        urgency = self.derive_urgency(riskscore, telemetry, prediction, decision)
        ttf = prediction.get("timetofailurehours")

        factors: List[str] = []

        if telemetry.get("refrigerationfailed"):
            factors.append("refrigeration failure is active")
        if telemetry.get("dooropen"):
            factors.append("a door-open event is present")
        if telemetry.get("temperature", 0.0) > 8.0:
            factors.append(f"temperature is elevated at {telemetry.get('temperature'):.2f}C")
        if telemetry.get("humidity", 0.0) >= 70.0:
            factors.append(f"humidity is high at {telemetry.get('humidity'):.2f}%")
        if telemetry.get("vibration", 0.0) >= 5.0:
            factors.append(f"vibration is elevated at {telemetry.get('vibration'):.2f}g")

        exposure = telemetry.get("cumulativeexposure", {})
        if isinstance(exposure, dict):
            if safe_float(exposure.get("tempdegreeminutes"), 0.0) > 0:
                factors.append("cumulative temperature exposure has built up")
            if safe_float(exposure.get("dooropenminutes"), 0.0) > 0:
                factors.append("door-open exposure has accumulated")

        if not factors:
            factors.append("the current telemetry and model output indicate developing spoilage risk")

        action_text = ""
        if decision.get("actions"):
            action_descriptions = [
                a.get("description") or a.get("type") or "intervention"
                for a in decision.get("actions", [])[:3]
            ]
            action_text = " Recommended actions: " + "; ".join(action_descriptions) + "."

        sop_text = ""
        if sop_docs:
            sop_text = " Relevant SOPs: " + ", ".join(doc["id"] for doc in sop_docs) + "."

        ttf_text = ""
        if ttf is not None:
            ttf_text = f" Estimated time to failure is about {safe_float(ttf, 0.0):.2f} hours."

        return (
            f"Risk is {urgency} for asset {telemetry.get('assetid')} because "
            + "; ".join(factors)
            + f". Combined risk score is {riskscore:.3f}."
            + ttf_text
            + action_text
            + sop_text
        ).strip()

    def _fallback_decision_explanation(
        self,
        decision: Dict[str, Any],
        telemetry: Dict[str, Any],
        prediction: Dict[str, Any],
        sop_docs: List[Dict[str, Any]],
    ) -> str:
        analysis = decision.get("analysis", {})
        risklevel = safe_str(get_first(analysis, ["risklevel"], ""), "").lower() or "unknown"
        action_descriptions = [
            a.get("description") or a.get("type") or "intervention"
            for a in decision.get("actions", [])[:3]
        ]
        actions_text = "; ".join(action_descriptions) if action_descriptions else "no listed interventions"
        sop_text = ", ".join(doc["id"] for doc in sop_docs) if sop_docs else "no matched SOP IDs"

        return (
            f"The autonomous system treated this case as {risklevel} risk and selected {actions_text} "
            f"based on the current telemetry, predicted spoilage trend, and operating scenario. "
            f"These actions align with the retrieved SOP guidance, especially {sop_text}."
        ).strip()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def generate_explanation(
        self,
        prediction: Dict[str, Any],
        telemetry: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_prediction = self.normalize_prediction(prediction)
        normalized_telemetry = self.normalize_telemetry(telemetry)
        normalized_decision = self.normalize_decision(decision) if decision else None

        self._merge_asset_identity(
            normalized_telemetry,
            normalized_prediction,
            normalized_decision,
        )

        if normalized_decision and not normalized_decision.get("actions"):
            normalized_decision = None

        riskscore = self.extract_risk_score(
            normalized_prediction,
            normalized_telemetry,
            normalized_decision,
        )
        urgency = self.derive_urgency(
            riskscore,
            normalized_telemetry,
            normalized_prediction,
            normalized_decision,
        )

        query = self.build_retrieval_query(
            normalized_prediction,
            normalized_telemetry,
            normalized_decision,
        )
        sop_docs = self.retrieve_relevant_sops(query, n_results=self.config.max_sop_results)

        try:
            messages = self._build_risk_prompt(
                normalized_telemetry,
                normalized_prediction,
                normalized_decision,
                sop_docs,
            )
            explanation_text = self._call_llm(messages, self.config.max_explanation_tokens)
            if not explanation_text:
                raise RuntimeError("Empty explanation returned by LLM.")
        except Exception as exc:
            logger.warning("LLM explanation failed, using fallback: %s", exc)
            explanation_text = self._fallback_risk_explanation(
                normalized_telemetry,
                normalized_prediction,
                normalized_decision,
                sop_docs,
            )

        return {
            "explanationid": f"EXP-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            "timestamp": now_iso(),
            "assetid": normalized_telemetry.get("assetid"),
            "riskscore": round(riskscore, 3),
            "urgency": urgency,
            "predictiontimestamp": normalized_prediction.get("timestamp"),
            "telemetrytimestamp": normalized_telemetry.get("timestamp"),
            "decisionid": normalized_decision.get("decisionid") if normalized_decision else None,
            "explanationtext": explanation_text,
            "referencedsops": [doc["id"] for doc in sop_docs],
            "sopdetails": sop_docs,
            "telemetrysnapshot": normalized_telemetry,
            "predictionsnapshot": normalized_prediction,
            "decisionsnapshot": normalized_decision,
            "retrievalquery": query,
        }

    def explain_decision(
        self,
        decision: Dict[str, Any],
        telemetry: Optional[Dict[str, Any]] = None,
        prediction: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_decision = self.normalize_decision(decision)
        telemetry_input = telemetry if telemetry is not None else normalized_decision.get("telemetry", {})
        prediction_input = prediction if prediction is not None else normalized_decision.get("prediction", {})

        normalized_telemetry = self.normalize_telemetry(telemetry_input)
        normalized_prediction = self.normalize_prediction(prediction_input)

        self._merge_asset_identity(
            normalized_telemetry,
            normalized_prediction,
            normalized_decision,
        )

        riskscore = self.extract_risk_score(
            normalized_prediction,
            normalized_telemetry,
            normalized_decision,
        )
        urgency = self.derive_urgency(
            riskscore,
            normalized_telemetry,
            normalized_prediction,
            normalized_decision,
        )

        query = self.build_retrieval_query(
            normalized_prediction,
            normalized_telemetry,
            normalized_decision,
        )
        sop_docs = self.retrieve_relevant_sops(query, n_results=max(2, self.config.max_sop_results - 1))

        try:
            messages = self._build_decision_prompt(
                normalized_decision,
                normalized_telemetry,
                normalized_prediction,
                sop_docs,
            )
            explanation_text = self._call_llm(messages, self.config.max_decision_tokens)
            if not explanation_text:
                raise RuntimeError("Empty decision explanation returned by LLM.")
        except Exception as exc:
            logger.warning("LLM decision explanation failed, using fallback: %s", exc)
            explanation_text = self._fallback_decision_explanation(
                normalized_decision,
                normalized_telemetry,
                normalized_prediction,
                sop_docs,
            )

        return {
            "decisionid": normalized_decision.get("decisionid"),
            "timestamp": now_iso(),
            "assetid": normalized_decision.get("assetid"),
            "riskscore": round(riskscore, 3),
            "urgency": urgency,
            "explanationtext": explanation_text,
            "referencedsops": [doc["id"] for doc in sop_docs],
            "sopdetails": sop_docs,
            "telemetrysnapshot": normalized_telemetry,
            "predictionsnapshot": normalized_prediction,
            "decisionsnapshot": normalized_decision,
            "retrievalquery": query,
        }

    # Optional alias for compatibility
    def generate_decision_explanation(
        self,
        decision: Dict[str, Any],
        telemetry: Optional[Dict[str, Any]] = None,
        prediction: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.explain_decision(decision, telemetry=telemetry, prediction=prediction)