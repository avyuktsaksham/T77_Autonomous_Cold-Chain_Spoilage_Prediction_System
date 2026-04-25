from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import chromadb
from chromadb.config import Settings


BASE_DIR = Path(__file__).resolve().parent
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
SOP_DOCUMENTS_DIR = BASE_DIR / "sopdocuments"

COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "coldchainsops")
COLLECTION_DESCRIPTION = (
    "Cold-chain SOPs, schema references, routing playbooks, cooling procedures, "
    "notification policies, and cargo handling guidance"
)
COLLECTION_VERSION = "phase5-step5.1-final-aligned-v2"


SUPPORTED_CARGO_TYPES: Sequence[str] = (
    "vaccines",
    "meat",
    "dairy",
    "pharmaceuticals",
    "frozenfood",
    "produce",
    "seafood",
    "icecream",
    "bloodplasma",
    "flowers",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", str(value).strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "document"


def stable_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, bool):
            cleaned[key] = value
        elif isinstance(value, (int, float, str)):
            cleaned[key] = value
        else:
            cleaned[key] = compact_text(json.dumps(value, ensure_ascii=False))
    return cleaned


def ensure_directories() -> None:
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    SOP_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def first_non_empty_line(text: str, fallback: str) -> str:
    for line in str(text).splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:140]
    return fallback


def pretty_cargo_name(cargo_type: str) -> str:
    mapping = {
        "frozenfood": "Frozen Food",
        "bloodplasma": "Blood Plasma",
        "icecream": "Ice Cream",
    }
    return mapping.get(cargo_type, cargo_type.replace("_", " ").title())


@dataclass(frozen=True)
class VectorDocument:
    id: str
    title: str
    content: str
    source: str
    category: str
    document_type: str
    cargo_type: str = "all"
    scenario: str = "all"
    risk_band: str = "all"
    actions: str = ""
    fields: str = ""
    keywords: str = ""
    priority: int = 1

    def to_chroma(self) -> Dict[str, Any]:
        document_text = f"{self.title}\n\n{self.content}".strip()
        metadata = sanitize_metadata(
            {
                "title": self.title,
                "source": self.source,
                "category": self.category,
                "type": self.document_type,
                "cargo_type": self.cargo_type,
                "scenario": self.scenario,
                "risk_band": self.risk_band,
                "actions": self.actions,
                "fields": self.fields,
                "keywords": self.keywords,
                "priority": self.priority,
                "version": COLLECTION_VERSION,
                "ingested_at": now_iso(),
            }
        )
        return {"id": self.id, "document": document_text, "metadata": metadata}


def make_doc(
    *,
    doc_id: str,
    title: str,
    content: str,
    source: str,
    category: str,
    document_type: str,
    cargo_type: str = "all",
    scenario: str = "all",
    risk_band: str = "all",
    actions: str = "",
    fields: str = "",
    keywords: str = "",
    priority: int = 1,
) -> VectorDocument:
    return VectorDocument(
        id=doc_id,
        title=compact_text(title),
        content=content.strip(),
        source=source,
        category=category,
        document_type=document_type,
        cargo_type=cargo_type,
        scenario=scenario,
        risk_band=risk_band,
        actions=actions,
        fields=fields,
        keywords=keywords,
        priority=priority,
    )


def build_builtin_documents() -> List[VectorDocument]:
    docs: List[VectorDocument] = [
        make_doc(
            doc_id="sop-telemetry-schema",
            title="Canonical telemetry payload schema",
            content=(
                "Telemetry payloads must use canonical keys so every downstream component "
                "reads the same shape of data. Required base fields are assetid, timestamp, "
                "temperature, humidity, vibration, dooropen, gpslat, gpslon, and cargotype. "
                "When available, also include scenario, refrigerationfailed, riskproxy, and "
                "cumulativeexposure to support better explanation quality. The RAG layer should "
                "prefer these canonical names over alternative snake_case variants."
            ),
            source="Internal Architecture",
            category="schema",
            document_type="reference",
            fields=(
                "assetid,timestamp,temperature,humidity,vibration,dooropen,"
                "gpslat,gpslon,cargotype,scenario,refrigerationfailed,"
                "riskproxy,cumulativeexposure"
            ),
            keywords=(
                "telemetry mqtt schema assetid dooropen gpslat gpslon cargotype "
                "riskproxy cumulativeexposure"
            ),
            priority=10,
        ),
        make_doc(
            doc_id="sop-prediction-schema",
            title="Canonical prediction payload schema",
            content=(
                "Prediction payloads should contain assetid, timestamp, riskscore, confidence, "
                "timetofailurehours, currenttemp, and currenthumidity. If multiple risk-like "
                "signals exist, use the model riskscore as the primary prediction field and keep "
                "other proxy values clearly named. Explanations should connect riskscore and "
                "timetofailurehours to the latest telemetry context for the same assetid."
            ),
            source="Internal Architecture",
            category="schema",
            document_type="reference",
            fields=(
                "assetid,timestamp,riskscore,confidence,timetofailurehours,"
                "currenttemp,currenthumidity"
            ),
            keywords="prediction schema riskscore confidence timetofailurehours currenttemp currenthumidity",
            priority=10,
        ),
        make_doc(
            doc_id="sop-decision-schema",
            title="Canonical decision payload structure",
            content=(
                "Decision records should include decisionid, assetid, timestamp, analysis, actions, "
                "and executionresults. Analysis should summarize riskscore, risklevel, "
                "contributingfactors, timetofailure, current telemetry context, and any "
                "refrigeration or cumulative exposure concerns. Actions should be explicit, "
                "tool-oriented, and stored as structured items with keys such as type, tool, "
                "priority, description, and action-specific fields like action, targetdc, dcname, "
                "or etahours. Execution results should preserve the tool response for each action "
                "so downstream notification and RAG services can justify what the system chose, "
                "what it executed, and why."
            ),
            source="Internal Architecture",
            category="schema",
            document_type="reference",
            fields=(
                "decisionid,assetid,timestamp,"
                "analysis.riskscore,analysis.risklevel,analysis.contributingfactors,"
                "analysis.timetofailure,analysis.refrigerationfailed,analysis.cumulativeexposure,"
                "actions.type,actions.tool,actions.priority,actions.description,actions.action,"
                "actions.targetdc,actions.dcname,actions.etahours,"
                "executionresults.action,executionresults.result"
            ),
            keywords=(
                "decision schema analysis actions executionresults contributing factors "
                "tool priority reroute cooling notification explainable agent"
            ),
            priority=9,
        ),
        make_doc(
            doc_id="sop-decision-action-taxonomy",
            title="Canonical decision action taxonomy",
            content=(
                "Decision actions should follow a stable taxonomy so tools and explanations stay "
                "aligned. Common action types are monitor, adjustcooling, reroute, "
                "emergencyreroute, notify, and escalate. For adjustcooling actions, the action "
                "field should carry one of hold, ecomode, increasecooling, decreasecooling, "
                "maxcooling, or emergencymode. Routing actions should include targetdc, dcname, "
                "and etahours when available, and notification actions should include "
                "severity-aware descriptions."
            ),
            source="Internal Agent Contract",
            category="decision",
            document_type="reference",
            actions=(
                "monitor,adjustcooling,reroute,emergencyreroute,notify,escalate,"
                "hold,ecomode,increasecooling,decreasecooling,maxcooling,emergencymode"
            ),
            fields=(
                "actions.type,actions.tool,actions.priority,actions.description,"
                "actions.action,actions.targetdc,actions.dcname,actions.etahours"
            ),
            keywords=(
                "decision action taxonomy monitor adjustcooling reroute emergencyreroute "
                "notify escalate cooling modes"
            ),
            priority=10,
        ),
        make_doc(
            doc_id="sop-mqtt-topic-contract",
            title="Canonical MQTT topic contract",
            content=(
                "Slash-separated MQTT topics should be used under the coldchain prefix. "
                "Per-asset telemetry goes to coldchain/telemetry/{assetid}; fleet snapshots go to "
                "coldchain/telemetry/all; predictions go to coldchain/predictions/{assetid}; "
                "decisions go to coldchain/decisions/{assetid}; explanation services may publish "
                "coldchain/explanations/{assetid} and "
                "coldchain/decision-explanations/{assetid}; publisher status uses "
                "coldchain/status/{publisherid}. RAG guidance should prefer these canonical topic "
                "families over legacy flat topic names."
            ),
            source="Internal Messaging Contract",
            category="messaging",
            document_type="reference",
            fields=(
                "topicprefix,telemetry,predictions,decisions,explanations,"
                "decisionexplanations,status,assetid,publisherid"
            ),
            keywords=(
                "mqtt topics coldchain telemetry all predictions decisions explanations "
                "decision explanations status slash topics"
            ),
            priority=9,
        ),
        make_doc(
            doc_id="sop-asset-correlation-contract",
            title="Asset correlation contract across services",
            content=(
                "The assetid is the primary join key across telemetry, predictions, decisions, "
                "notifications, and explanations. Prediction services should relate the latest "
                "sequence to the same assetid, decision services should use the latest telemetry "
                "and prediction for that assetid, and explanation services should ground "
                "explanations in the same correlated asset timeline. If a message cannot be "
                "correlated by assetid, it should not be explained as if it belongs to another shipment."
            ),
            source="Internal Architecture",
            category="correlation",
            document_type="reference",
            fields="assetid,telemetry,prediction,decision,notification,explanation",
            keywords="assetid correlation join telemetry prediction decision explanation",
            priority=10,
        ),
        make_doc(
            doc_id="sop-risk-band-interpretation",
            title="Risk score interpretation and intervention bands",
            content=(
                "When both a model prediction and a telemetry-side proxy are available, use the "
                "higher signal for conservative decision support. Operational interpretation should "
                "mirror the decision workflow: low risk is below 0.30 and generally means continue "
                "monitoring; moderate risk is 0.30 to below 0.70 and should trigger cooling review "
                "and notification; high risk is 0.70 to below 0.85 and should trigger reroute "
                "evaluation plus strong cooling; critical risk is 0.85 or above and requires urgent "
                "intervention, stronger notification, and time-sensitive handling. Scores at or above "
                "0.95 should be treated as immediate escalation conditions inside the critical band. "
                "Any refrigeration failure or time-to-failure at or below 1 hour should be treated "
                "as critical even if the numeric risk score is still catching up."
            ),
            source="Internal Decision Policy",
            category="risk",
            document_type="policy",
            risk_band="low,moderate,high,critical",
            fields="riskscore,riskproxy,timetofailurehours,refrigerationfailed",
            keywords="risk thresholds low moderate high critical escalation time to failure",
            priority=10,
        ),
        make_doc(
            doc_id="sop-cumulative-exposure",
            title="Cumulative exposure handling",
            content=(
                "Cold-chain decisions should not rely only on the latest single reading. Track and "
                "explain cumulative exposure such as tempdegreeminutes, humiditypercentminutes, "
                "dooropenminutes, vibrationwarnminutes, vibrationcriticalminutes, and "
                "outofrangeminutesinhour. A series of short excursions can be operationally more "
                "important than one brief spike, so explanations should highlight sustained and "
                "repeated exposure patterns whenever present."
            ),
            source="Internal Quality SOP",
            category="exposure",
            document_type="protocol",
            fields=(
                "cumulativeexposure,tempdegreeminutes,humiditypercentminutes,"
                "dooropenminutes,vibrationwarnminutes,vibrationcriticalminutes,"
                "outofrangeminutesinhour"
            ),
            keywords="cumulative exposure temp degree minutes humidity door open vibration out of range",
            priority=10,
        ),
        make_doc(
            doc_id="sop-temperature-excursion",
            title="Temperature excursion response",
            content=(
                "Any reading outside the configured cargo target band is a temperature excursion. "
                "If the temperature is modestly above target and the unit is still functioning, "
                "start with controlled cooling adjustment. If the excursion is large, sustained, "
                "or coupled with rising risk and shrinking time-to-failure, escalate to maxcooling "
                "or emergencymode and evaluate rerouting to a compliant facility."
            ),
            source="Internal Quality SOP",
            category="temperature",
            document_type="protocol",
            actions="hold,increasecooling,decreasecooling,maxcooling,emergencymode,reroute",
            fields="temperature,cargotype,riskscore,timetofailurehours,refrigerationfailed",
            keywords="temperature excursion cooling action reroute target band",
            priority=9,
        ),
        make_doc(
            doc_id="sop-humidity-control",
            title="Humidity deviation handling",
            content=(
                "Humidity should be interpreted in the context of cargo sensitivity and cumulative "
                "exposure. High humidity can increase condensation, microbial risk, and packaging "
                "stress, while very low humidity can harm packaging integrity for sensitive loads. "
                "Humidity problems alone may not always require rerouting, but they should contribute "
                "to the explanation when combined with temperature excursions, door events, or long exposure windows."
            ),
            source="Internal Environmental SOP",
            category="humidity",
            document_type="protocol",
            fields="humidity,cargotype,cumulativeexposure",
            keywords="humidity control environmental exposure packaging integrity",
            priority=7,
        ),
        make_doc(
            doc_id="sop-vibration-monitoring",
            title="Vibration monitoring and physical shock response",
            content=(
                "Sustained vibration and physical shock can damage sensitive cargo even when thermal "
                "conditions are acceptable. Rising vibrationwarnminutes or vibrationcriticalminutes "
                "should be explained as physical risk contributors, especially for pharmaceuticals, "
                "blood plasma, flowers, produce, and fragile packaged loads. If extreme vibration "
                "coincides with elevated spoilage risk, include cargo inspection or handling review in the recommendation."
            ),
            source="Internal Handling SOP",
            category="vibration",
            document_type="protocol",
            fields="vibration,cumulativeexposure,vibrationwarnminutes,vibrationcriticalminutes,cargotype",
            keywords="vibration physical shock inspection cargo damage",
            priority=7,
        ),
        make_doc(
            doc_id="sop-door-event-control",
            title="Door opening event control",
            content=(
                "Door opening events should be treated as operationally meaningful because they often "
                "precede temperature and humidity drift. Repeated or prolonged dooropen periods should "
                "increase concern, particularly when they occur during high ambient load, active excursions, "
                "or refrigeration instability. Explanations should explicitly mention dooropen activity when "
                "it contributes to cumulative exposure or when it coincides with a risk increase."
            ),
            source="Internal Handling SOP",
            category="door",
            document_type="protocol",
            fields="dooropen,cumulativeexposure,dooropenminutes,temperature,humidity",
            keywords="door open event temperature spike humidity drift cumulative exposure",
            priority=8,
        ),
        make_doc(
            doc_id="sop-refrigeration-failure",
            title="Refrigeration failure response",
            content=(
                "Refrigeration failure is a high-severity operational event. If refrigerationfailed is true "
                "or the scenario indicates refrigerationfailure, explanations should prioritize active cooling recovery, "
                "rapid ETA assessment, and immediate evaluation of the nearest operational facility that supports the cargo. "
                "If time-to-failure is short, treat the event as critical and pair cooling intervention with notification and escalation."
            ),
            source="Internal Equipment SOP",
            category="equipment",
            document_type="emergency",
            scenario="refrigerationfailure",
            actions="maxcooling,emergencymode,reroute,notify,escalate",
            fields="refrigerationfailed,scenario,timetofailurehours,temperature,riskscore",
            keywords="refrigeration failure emergency cooling reroute escalation",
            priority=10,
        ),
        make_doc(
            doc_id="sop-cooling-action-policy",
            title="Cooling action selection policy",
            content=(
                "Cooling actions must match both severity and direction of deviation. Use hold or ecomode "
                "when the cargo is stable and within band. Use increasecooling when temperature is modestly above "
                "target, use maxcooling when the excursion is large or the risk is already high, use emergencymode "
                "for critical conditions or refrigeration instability, and consider decreasecooling when the load is "
                "below band and over-cooling is the concern. Recommendations should reference the target band and the "
                "current operational urgency rather than using a fixed action for every case."
            ),
            source="Internal Refrigeration SOP",
            category="cooling",
            document_type="decision-policy",
            actions="hold,ecomode,increasecooling,decreasecooling,maxcooling,emergencymode",
            fields="temperature,cargotype,riskscore,refrigerationfailed,scenario",
            keywords="cooling recommendation hold ecomode increasecooling decreasecooling maxcooling emergencymode",
            priority=10,
        ),
        make_doc(
            doc_id="sop-reroute-evaluation",
            title="Reroute evaluation criteria",
            content=(
                "Only recommend rerouting to distribution centers that are operational, have available capacity, "
                "and support the current cargo type. Rank alternatives using distance, ETA, capacity headroom, "
                "refrigeration status, cargo compatibility, and whether the center can be reached before the predicted "
                "failure window closes. A reroute recommendation should be framed as a benefit-based intervention, not "
                "just the nearest geographic stop."
            ),
            source="Internal Routing SOP",
            category="routing",
            document_type="decision-policy",
            actions="reroute",
            fields="gpslat,gpslon,cargotype,riskscore,timetofailurehours,refrigerationfailed",
            keywords="reroute distribution center eta available capacity cargo compatibility benefit score",
            priority=10,
        ),
        make_doc(
            doc_id="sop-route-benefit-score",
            title="Reroute benefit scoring rationale",
            content=(
                "Benefit-based reroute reasoning should explain why one center is better than another. "
                "Important factors include shorter ETA, feasible arrival before failure, operational refrigeration, "
                "capacity availability, cargo support, and urgency bonuses for severe conditions such as refrigeration "
                "failure, high risk, or very short time-to-failure. If no candidate is viable, the explanation should "
                "say that reroute was evaluated but not recommended under current constraints."
            ),
            source="Internal Routing SOP",
            category="routing",
            document_type="reference",
            actions="reroute",
            fields="benefitscore,etahours,distancekm,availablecapacity,timetofailurehours",
            keywords="benefit score reroute eta distance capacity failure window",
            priority=9,
        ),
        make_doc(
            doc_id="sop-notification-policy",
            title="Notification and recipient policy",
            content=(
                "Notifications should be severity-aware and action-aware. Common alert types are spoilagerisk, "
                "reroute, coolingadjustment, coolingfailure, doorevent, escalation, and system. Severity should be "
                "inferred from the worst combination of risk score, telemetry risk proxy, time-to-failure, refrigeration "
                "status, door activity, and decision priority. Critical events should reach leadership roles, while "
                "moderate events should at least reach logistics and quality owners."
            ),
            source="Internal Communication SOP",
            category="notification",
            document_type="policy",
            actions="notify,escalate",
            fields="alerttype,severity,riskscore,riskproxy,timetofailurehours,refrigerationfailed,dooropen",
            keywords="notification severity recipients spoilagerisk reroute coolingfailure escalation",
            priority=9,
        ),
        make_doc(
            doc_id="sop-critical-escalation",
            title="Critical escalation triggers",
            content=(
                "Escalation is required when the event crosses from operational adjustment into business-risk territory. "
                "Typical triggers include critical risk scores, refrigeration instability, inability to arrive at a safe "
                "facility before the failure window, or repeated severe exposure accumulation. Explanations should make it "
                "clear that escalation is not merely a message broadcast; it indicates leadership attention and urgent execution."
            ),
            source="Internal Communication SOP",
            category="notification",
            document_type="emergency",
            risk_band="critical",
            actions="escalate,notify,reroute,emergencymode",
            fields="riskscore,timetofailurehours,refrigerationfailed,cumulativeexposure",
            keywords="critical escalation leadership urgent execution",
            priority=10,
        ),
        make_doc(
            doc_id="sop-scenario-normal",
            title="Normal scenario interpretation",
            content=(
                "In the normal scenario, telemetry should remain close to target conditions with low cumulative exposure "
                "and no sustained operational disturbances. Explanations should emphasize stable temperature control, low "
                "risk, no urgent reroute need, and continued monitoring rather than inventing unnecessary alarm."
            ),
            source="Internal Simulation Guide",
            category="scenario",
            document_type="reference",
            scenario="normal",
            risk_band="low",
            fields="scenario,temperature,humidity,vibration,dooropen,riskscore",
            keywords="normal scenario low risk stable telemetry monitoring",
            priority=6,
        ),
        make_doc(
            doc_id="sop-scenario-micro-excursions",
            title="Micro-excursions scenario interpretation",
            content=(
                "Micro-excursions represent repeated short deviations that may look small individually but become meaningful "
                "through accumulation. Explanations for this scenario should call out cumulative exposure, repeated temperature "
                "or humidity drift, and the possibility that operational handling issues are adding up even before a full failure occurs."
            ),
            source="Internal Simulation Guide",
            category="scenario",
            document_type="reference",
            scenario="microexcursions",
            risk_band="moderate,high",
            fields="scenario,cumulativeexposure,temperature,humidity,riskscore",
            keywords="micro excursions repeated short deviations cumulative exposure",
            priority=8,
        ),
        make_doc(
            doc_id="sop-scenario-refrigeration-failure",
            title="Refrigeration-failure scenario interpretation",
            content=(
                "The refrigerationfailure scenario should be interpreted as a fast-moving incident rather than a routine drift. "
                "Explanations should emphasize rising urgency, higher probability of cargo damage, the need for aggressive cooling action, "
                "facility selection by ETA, and stronger notification or escalation behavior."
            ),
            source="Internal Simulation Guide",
            category="scenario",
            document_type="reference",
            scenario="refrigerationfailure",
            risk_band="high,critical",
            fields="scenario,refrigerationfailed,temperature,riskscore,timetofailurehours",
            keywords="refrigeration failure scenario urgency emergency reroute",
            priority=9,
        ),
        make_doc(
            doc_id="sop-rag-explanation-style",
            title="RAG explanation style guide",
            content=(
                "Generated explanations should be concise, operational, and grounded in retrieved SOPs. They should connect "
                "the current telemetry, the latest prediction, and the selected action path in plain language. Good explanations "
                "name the contributing factors, state the urgency, and cite the relevant SOP identifiers that justify the recommendation."
            ),
            source="Internal GenAI SOP",
            category="rag",
            document_type="style-guide",
            fields="telemetry,prediction,decision",
            keywords="explanation style cited SOP concise operational",
            priority=8,
        ),
    ]

    cargo_specific_notes: Dict[str, str] = {
        "vaccines": (
            "Vaccines should be treated as highly temperature-sensitive cargo. If the load moves above the validated cold range "
            "or is exposed to freezing conditions, explanations should emphasize efficacy risk, cumulative exposure, and time-sensitive handling."
        ),
        "bloodplasma": (
            "Blood plasma should be handled as highly sensitive biological cargo. Explanations should prioritize temperature stability, "
            "minimal delay, and any indication of refrigeration instability or sustained transit risk."
        ),
        "pharmaceuticals": (
            "Pharmaceutical cargo should be handled with close attention to both temperature control and physical shock. "
            "Vibration, packaging stress, and repeated micro-excursions should be included when they contribute to overall risk."
        ),
        "icecream": (
            "Ice cream is highly sensitive to warming and partial thaw-refreeze cycles. Explanations should treat warm excursions, "
            "door activity, and poor cooling response as strong product-quality concerns."
        ),
        "frozenfood": (
            "Frozen food requires stable frozen-chain handling. Explanations should highlight warming drift, repeated door events, "
            "and any scenario that suggests loss of product integrity before delivery."
        ),
        "flowers": (
            "Flowers are sensitive to both temperature stress and physical handling. Explanations should include humidity drift, "
            "vibration, and transit delays when these are likely to reduce freshness."
        ),
        "produce": (
            "Produce should be evaluated using both thermal and environmental stability. Explanations should mention humidity issues, "
            "door events, and cumulative stress that may reduce shelf life."
        ),
        "seafood": (
            "Seafood should be treated as perishable cargo where sustained thermal exposure quickly increases spoilage concern. "
            "Fast intervention, ETA awareness, and strong cooling response should be emphasized when risk rises."
        ),
        "dairy": (
            "Dairy cargo is sensitive to warming and repeated handling instability. Explanations should connect temperature excursions, "
            "door events, and cumulative exposure to quality deterioration risk."
        ),
        "meat": (
            "Meat cargo should be explained with emphasis on sustained cold-chain maintenance, rapid response to warming, "
            "and facility selection if recovery within the current route is doubtful."
        ),
    }

    for cargo_type in SUPPORTED_CARGO_TYPES:
        docs.append(
            make_doc(
                doc_id=f"sop-cargo-{cargo_type}",
                title=f"{pretty_cargo_name(cargo_type)} handling baseline",
                content=(
                    f"{cargo_specific_notes.get(cargo_type, pretty_cargo_name(cargo_type) + ' should remain within its configured cargo profile band.')} "
                    f"Whenever a decision is made for {pretty_cargo_name(cargo_type)}, the explanation should mention cargo compatibility for rerouting, "
                    f"target-band adherence for cooling control, and whether cumulative exposure is building beyond acceptable operating margins."
                ),
                source="Internal Cargo Policy",
                category="cargo",
                document_type="profile",
                cargo_type=cargo_type,
                fields="cargotype,temperature,humidity,vibration,cumulativeexposure,recommendedaction,recommendeddc",
                keywords=f"{cargo_type} cargo profile target band reroute cooling cumulative exposure",
                priority=7,
            )
        )

    return docs


def load_external_sop_documents(directory: Path) -> List[VectorDocument]:
    if not directory.exists():
        return []

    docs: List[VectorDocument] = []
    allowed_suffixes = {".md", ".txt", ".json"}

    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
            continue

        if path.suffix.lower() == ".json":
            docs.extend(_load_external_json_documents(path))
        else:
            docs.extend(_load_external_text_document(path))

    return docs


def _load_external_text_document(path: Path) -> List[VectorDocument]:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []

    title = first_non_empty_line(text, path.stem.replace("-", " ").title())
    rel_source = f"External SOP File: {path.relative_to(BASE_DIR).as_posix()}"
    rel_key = path.relative_to(BASE_DIR).as_posix()
    doc_id = stable_id("external-text", rel_key)

    return [
        make_doc(
            doc_id=doc_id,
            title=title,
            content=text,
            source=rel_source,
            category="external",
            document_type="sop",
            keywords=f"external sop {slugify(path.stem)}",
            priority=5,
        )
    ]


def _load_external_json_documents(path: Path) -> List[VectorDocument]:
    raw = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []

    items = parsed if isinstance(parsed, list) else [parsed]
    docs: List[VectorDocument] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        content = item.get("content") or item.get("document") or item.get("text")
        if not content:
            continue

        title = item.get("title") or first_non_empty_line(content, path.stem.replace("-", " ").title())
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}

        doc_id = str(item.get("id") or stable_id(f"external-{slugify(path.stem)}", f"{title}\n{content}"))
        docs.append(
            make_doc(
                doc_id=doc_id,
                title=title,
                content=str(content),
                source=str(metadata.get("source") or f"External SOP File: {path.relative_to(BASE_DIR).as_posix()}"),
                category=str(metadata.get("category") or "external"),
                document_type=str(metadata.get("type") or "sop"),
                cargo_type=str(metadata.get("cargo_type") or "all"),
                scenario=str(metadata.get("scenario") or "all"),
                risk_band=str(metadata.get("risk_band") or "all"),
                actions=str(metadata.get("actions") or ""),
                fields=str(metadata.get("fields") or ""),
                keywords=str(metadata.get("keywords") or ""),
                priority=int(metadata.get("priority") or 5),
            )
        )

    return docs


def deduplicate_documents(documents: Iterable[VectorDocument]) -> List[VectorDocument]:
    unique: Dict[str, VectorDocument] = {}
    for doc in documents:
        unique[doc.id] = doc
    return list(unique.values())


def create_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=str(VECTORSTORE_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def create_or_replace_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
    reset: bool = True,
):
    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "description": COLLECTION_DESCRIPTION,
            "version": COLLECTION_VERSION,
            "created_at": now_iso(),
        },
    )

    try:
        collection.modify(
            metadata={
                "description": COLLECTION_DESCRIPTION,
                "version": COLLECTION_VERSION,
                "created_at": now_iso(),
            }
        )
    except Exception:
        pass

    return collection


def upsert_documents(collection, documents: Sequence[VectorDocument], batch_size: int = 64) -> int:
    total = 0
    chroma_rows = [doc.to_chroma() for doc in documents]

    for start in range(0, len(chroma_rows), batch_size):
        batch = chroma_rows[start : start + batch_size]
        collection.upsert(
            ids=[row["id"] for row in batch],
            documents=[row["document"] for row in batch],
            metadatas=[row["metadata"] for row in batch],
        )
        total += len(batch)

    return total


def build_summary(documents: Sequence[VectorDocument], collection_name: str, reset: bool) -> Dict[str, Any]:
    by_category: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    by_cargo_type: Dict[str, int] = {}

    for doc in documents:
        by_category[doc.category] = by_category.get(doc.category, 0) + 1
        by_source[doc.source] = by_source.get(doc.source, 0) + 1
        by_cargo_type[doc.cargo_type] = by_cargo_type.get(doc.cargo_type, 0) + 1

    return {
        "collection_name": collection_name,
        "collection_version": COLLECTION_VERSION,
        "vectorstore_path": str(VECTORSTORE_DIR),
        "sop_documents_path": str(SOP_DOCUMENTS_DIR),
        "reset_collection": reset,
        "document_count": len(documents),
        "categories": dict(sorted(by_category.items())),
        "sources": dict(sorted(by_source.items())),
        "cargo_types": dict(sorted(by_cargo_type.items())),
        "document_ids": [doc.id for doc in documents],
        "generated_at": now_iso(),
    }


def write_manifest(summary: Dict[str, Any]) -> Path:
    manifest_path = VECTORSTORE_DIR / "vectorstore_manifest.json"
    manifest_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def main() -> None:
    ensure_directories()

    reset_collection = env_flag("CHROMA_RESET", True)
    client = create_client()

    builtin_docs = build_builtin_documents()
    external_docs = load_external_sop_documents(SOP_DOCUMENTS_DIR)
    all_docs = deduplicate_documents([*builtin_docs, *external_docs])

    collection = create_or_replace_collection(
        client=client,
        collection_name=COLLECTION_NAME,
        reset=reset_collection,
    )

    upserted_count = upsert_documents(collection, all_docs)
    summary = build_summary(all_docs, COLLECTION_NAME, reset_collection)
    manifest_path = write_manifest(summary)

    print("=" * 72)
    print("ChromaDB vector store setup complete")
    print("=" * 72)
    print(f"Collection Name     : {COLLECTION_NAME}")
    print(f"Collection Version  : {COLLECTION_VERSION}")
    print(f"Vector Store Path   : {VECTORSTORE_DIR}")
    print(f"SOP Documents Path  : {SOP_DOCUMENTS_DIR}")
    print(f"Reset Collection    : {reset_collection}")
    print(f"Built-in Documents  : {len(builtin_docs)}")
    print(f"External Documents  : {len(external_docs)}")
    print(f"Upserted Documents  : {upserted_count}")
    print(f"Collection Count    : {collection.count()}")
    print(f"Manifest            : {manifest_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()