from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _deep_copy_dict(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    copied: Dict[str, Any] = {}
    for k, v in value.items():
        if isinstance(v, dict):
            copied[k] = _deep_copy_dict(v)
        elif isinstance(v, list):
            copied[k] = list(v)
        else:
            copied[k] = v
    return copied


@dataclass(frozen=True)
class NotificationRecord:
    id: str
    timestamp: str
    asset_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    recipients: List[str]
    channels: List[str]
    status: str
    metadata: Dict[str, Any]


class NotificationTool:
    def __init__(self) -> None:
        self.notification_history: List[Dict[str, Any]] = []
        self._counter: int = 0

        self.default_recipients_by_severity: Dict[str, List[str]] = {
            "low": ["logistics_manager"],
            "medium": ["logistics_manager", "quality_officer"],
            "high": ["logistics_manager", "quality_officer", "fleet_supervisor"],
            "critical": [
                "logistics_manager",
                "quality_officer",
                "fleet_supervisor",
                "operations_director",
            ],
        }

        self.alert_type_recipients: Dict[str, List[str]] = {
            "spoilage_risk": ["logistics_manager", "quality_officer"],
            "reroute": ["logistics_manager", "fleet_supervisor"],
            "cooling_adjustment": ["fleet_supervisor", "maintenance_team"],
            "cooling_failure": ["maintenance_team", "operations_director", "quality_officer"],
            "door_event": ["fleet_supervisor"],
            "escalation": [
                "senior_logistics_manager",
                "operations_director",
                "quality_director",
            ],
            "system": ["operations_director"],
        }

        self.default_channels_by_severity: Dict[str, List[str]] = {
            "low": ["dashboard", "audit_log"],
            "medium": ["dashboard", "audit_log", "email"],
            "high": ["dashboard", "audit_log", "email", "sms"],
            "critical": ["dashboard", "audit_log", "email", "sms", "phone_call"],
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _next_id(self) -> str:
        self._counter += 1
        return f"ALERT_{self._counter:06d}"

    def _normalize_severity(self, severity: Optional[str]) -> str:
        if severity is None:
            return "medium"

        value = str(severity).strip().lower()
        mapping = {
            "low": "low",
            "info": "low",
            "informational": "low",
            "medium": "medium",
            "moderate": "medium",
            "warning": "medium",
            "high": "high",
            "urgent": "high",
            "critical": "critical",
            "severe": "critical",
            "emergency": "critical",
        }
        return mapping.get(value, "medium")

    def _severity_rank(self, severity: str) -> int:
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return order.get(self._normalize_severity(severity), 2)

    def _max_severity(self, a: str, b: str) -> str:
        sa = self._normalize_severity(a)
        sb = self._normalize_severity(b)
        return sa if self._severity_rank(sa) >= self._severity_rank(sb) else sb

    def _extract_risk_score(self, prediction: Optional[Dict[str, Any]]) -> float:
        if not prediction:
            return 0.0

        for key in (
            "predicted_risk_proxy",
            "risk_score",
            "riskscore",
            "risk_proxy",
            "actual_risk_proxy",
        ):
            if key in prediction and prediction[key] is not None:
                return _clamp(_safe_float(prediction[key], 0.0), 0.0, 1.0)

        return 0.0
    
    def _extract_telemetry_risk_score(self, telemetry: Optional[Dict[str, Any]]) -> float:
        if not telemetry:
            return 0.0
        return _clamp(_safe_float(telemetry.get("risk_proxy"), 0.0), 0.0, 1.0)

    def _extract_time_to_failure_hours(self, prediction: Optional[Dict[str, Any]]) -> Optional[float]:
        if not prediction:
            return None

        for key in (
            "time_to_failure_hours",
            "time_to_failure",
            "timetofailurehours",
            "timetofailure",
            "eta_to_failure_hours",
        ):
            if key in prediction and prediction[key] is not None:
                value = _safe_float(prediction[key], -1.0)
                return None if value < 0 else value

        return None

    def _derive_alert_type(
        self,
        telemetry: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
    ) -> str:
        telemetry = telemetry or {}
        decision = decision or {}

        decision_type = str(
            decision.get("type")
            or decision.get("action_type")
            or decision.get("alert_type")
            or ""
        ).strip().lower()

        if decision_type in {"reroute", "route_change"}:
            return "reroute"
        if decision_type in {"adjust_cooling", "cooling_adjustment"}:
            return "cooling_adjustment"
        if decision_type in {"cooling_failure", "refrigeration_failure"}:
            return "cooling_failure"
        if decision_type in {"door_event"}:
            return "door_event"
        if decision_type in {"escalation", "escalate"}:
            return "escalation"

        # Align with routing_tool.py outputs
        if (
            "recommended_dc" in decision
            or "alternatives" in decision
            or "reroute_recommended" in decision
        ):
            return "reroute"

        # Align with refrigeration_tool.py outputs
        if "recommended_action" in decision or "command_preview" in decision:
            if _to_bool(telemetry.get("refrigeration_failed")) or str(
                telemetry.get("scenario") or ""
            ).strip().lower() == "refrigeration_failure":
                return "cooling_failure"
            return "cooling_adjustment"

        if _to_bool(telemetry.get("refrigeration_failed")):
            return "cooling_failure"
        if _to_bool(telemetry.get("door_open")):
            return "door_event"

        return "spoilage_risk"

    def _infer_severity(
        self,
        telemetry: Optional[Dict[str, Any]] = None,
        prediction: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
        alert_type: Optional[str] = None,
    ) -> str:
        telemetry = telemetry or {}
        prediction = prediction or {}
        decision = decision or {}

        predicted_risk_score = self._extract_risk_score(prediction)
        telemetry_risk_score = self._extract_telemetry_risk_score(telemetry)
        risk_score = max(predicted_risk_score, telemetry_risk_score)

        time_to_failure_hours = self._extract_time_to_failure_hours(prediction)
        refrigeration_failed = _to_bool(telemetry.get("refrigeration_failed"))
        door_open = _to_bool(telemetry.get("door_open"))
        temperature = _safe_float(telemetry.get("temperature"), 0.0)
        scenario = str(telemetry.get("scenario") or "").strip().lower()
        priority = str(decision.get("priority") or "").strip().lower()

        recommended_action = str(decision.get("recommended_action") or "").strip().lower()
        reroute_recommended = _to_bool(decision.get("reroute_recommended"))

        severity = "low"

        if risk_score >= 0.95:
            severity = "critical"
        elif risk_score >= 0.85:
            severity = "high"
        elif risk_score >= 0.40:
            severity = "medium"

        if time_to_failure_hours is not None:
            if time_to_failure_hours <= 1.0:
                severity = self._max_severity(severity, "critical")
            elif time_to_failure_hours <= 3.0:
                severity = self._max_severity(severity, "high")
            elif time_to_failure_hours <= 6.0:
                severity = self._max_severity(severity, "medium")

        if refrigeration_failed or scenario == "refrigeration_failure":
            severity = self._max_severity(severity, "high")

        if door_open and risk_score >= 0.70:
            severity = self._max_severity(severity, "high")

        if temperature >= 30.0:
            severity = self._max_severity(severity, "critical")

        # Align with refrigeration_tool.py outputs
        if recommended_action == "emergency_mode":
            severity = self._max_severity(severity, "critical")
        elif recommended_action == "max_cooling":
            severity = self._max_severity(severity, "high")
        elif recommended_action == "increase_cooling":
            severity = self._max_severity(severity, "medium")

        # Align with routing_tool.py outputs
        if alert_type == "reroute" and reroute_recommended:
            if risk_score >= 0.70 or (
                time_to_failure_hours is not None and time_to_failure_hours <= 3.0
            ):
                severity = self._max_severity(severity, "high")
            else:
                severity = self._max_severity(severity, "medium")

        if priority:
            severity = self._max_severity(severity, self._normalize_severity(priority))

        if alert_type == "escalation":
            severity = "critical"

        return severity

    def _build_recipients(
        self,
        alert_type: str,
        severity: str,
        recipients: Optional[Sequence[str]] = None,
    ) -> List[str]:
        if recipients:
            return [str(x) for x in recipients if str(x).strip()]

        merged: List[str] = []
        for item in self.default_recipients_by_severity.get(severity, []):
            if item not in merged:
                merged.append(item)

        for item in self.alert_type_recipients.get(alert_type, []):
            if item not in merged:
                merged.append(item)

        if not merged:
            merged = ["logistics_manager"]

        return merged

    def _build_channels(
        self,
        severity: str,
        channels: Optional[Sequence[str]] = None,
    ) -> List[str]:
        if channels:
            return [str(x) for x in channels if str(x).strip()]
        return list(self.default_channels_by_severity.get(severity, ["dashboard", "audit_log"]))

    def _build_title(self, asset_id: str, alert_type: str, severity: str) -> str:
        label_map = {
            "spoilage_risk": "Spoilage Risk Alert",
            "reroute": "Reroute Recommendation",
            "cooling_adjustment": "Cooling Adjustment Alert",
            "cooling_failure": "Cooling Failure Alert",
            "door_event": "Door Event Alert",
            "escalation": "Escalation Required",
            "system": "System Notification",
        }
        label = label_map.get(alert_type, "Cold-Chain Alert")
        return f"[{severity.upper()}] {label} - {asset_id}"

    def _build_message(
        self,
        asset_id: str,
        alert_type: str,
        severity: str,
        telemetry: Optional[Dict[str, Any]] = None,
        prediction: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> str:
        telemetry = telemetry or {}
        prediction = prediction or {}
        decision = decision or {}

        cargo_type = str(telemetry.get("cargo_type") or "unknown")
        temperature = telemetry.get("temperature")
        humidity = telemetry.get("humidity")
        vibration = telemetry.get("vibration")
        scenario = str(telemetry.get("scenario") or "unknown")
        refrigeration_failed = _to_bool(telemetry.get("refrigeration_failed"))
        door_open = _to_bool(telemetry.get("door_open"))

        predicted_risk_score = self._extract_risk_score(prediction)
        telemetry_risk_score = self._extract_telemetry_risk_score(telemetry)
        risk_score = max(predicted_risk_score, telemetry_risk_score)
        time_to_failure_hours = self._extract_time_to_failure_hours(prediction)

        parts: List[str] = [
            f"Asset {asset_id}",
            f"cargo={cargo_type}",
            f"severity={severity}",
            f"alert_type={alert_type}",
        ]

        if temperature is not None:
            parts.append(f"temperature={round(_safe_float(temperature), 2)}C")
        if humidity is not None:
            parts.append(f"humidity={round(_safe_float(humidity), 2)}%")
        if vibration is not None:
            parts.append(f"vibration={round(_safe_float(vibration), 2)}g")

        parts.append(f"scenario={scenario}")
        parts.append(f"door_open={'yes' if door_open else 'no'}")
        parts.append(f"refrigeration_failed={'yes' if refrigeration_failed else 'no'}")
        parts.append(f"telemetry_risk_proxy={round(telemetry_risk_score, 3)}")
        parts.append(f"predicted_risk={round(predicted_risk_score, 3)}")
        parts.append(f"risk_score={round(risk_score, 3)}")

        if time_to_failure_hours is not None:
            parts.append(f"time_to_failure_hours={round(time_to_failure_hours, 2)}")

        if reason:
            parts.append(f"reason={reason}")

        decision_type = str(decision.get("type") or "").strip().lower()
        if not decision_type:
            if (
                "recommended_dc" in decision
                or "alternatives" in decision
                or "reroute_recommended" in decision
            ):
                decision_type = "reroute"
            elif "recommended_action" in decision or "command_preview" in decision:
                decision_type = "cooling_adjustment"

        if decision_type:
            parts.append(f"decision={decision_type}")

        recommended_action = decision.get("action") or decision.get("recommended_action")
        if recommended_action:
            parts.append(f"recommended_action={recommended_action}")

        command_preview = decision.get("command_preview")
        if isinstance(command_preview, dict):
            if command_preview.get("target_temp") is not None:
                parts.append(
                    f"target_temp={round(_safe_float(command_preview.get('target_temp')), 2)}C"
                )
            if command_preview.get("power_change_pct") is not None:
                parts.append(
                    f"power_change_pct={round(_safe_float(command_preview.get('power_change_pct')), 2)}"
                )

        recommended_dc = decision.get("recommended_dc")
        if isinstance(recommended_dc, dict):
            dc_name = recommended_dc.get("name") or recommended_dc.get("id")
            if dc_name:
                parts.append(f"target_dc={dc_name}")
            if recommended_dc.get("eta_hours") is not None:
                parts.append(
                    f"eta_hours={round(_safe_float(recommended_dc.get('eta_hours')), 2)}"
                )
            if recommended_dc.get("distance_km") is not None:
                parts.append(
                    f"distance_km={round(_safe_float(recommended_dc.get('distance_km')), 2)}"
                )
            if recommended_dc.get("benefit_score") is not None:
                parts.append(
                    f"benefit_score={round(_safe_float(recommended_dc.get('benefit_score')), 2)}"
                )
        else:
            dc_name = decision.get("dc_name") or decision.get("target_dc_name") or decision.get("target_name")
            if dc_name:
                parts.append(f"target_dc={dc_name}")

            target_dc = decision.get("target_dc")
            if target_dc and not dc_name:
                parts.append(f"target_dc={target_dc}")

            eta_hours = decision.get("eta_hours")
            if eta_hours is not None:
                parts.append(f"eta_hours={round(_safe_float(eta_hours), 2)}")

        exposure = telemetry.get("cumulative_exposure") or {}
        temp_degree_minutes = exposure.get("temp_degree_minutes")
        if temp_degree_minutes is not None:
            parts.append(f"temp_degree_minutes={round(_safe_float(temp_degree_minutes), 2)}")

        return " | ".join(parts)

    def send_alert(
        self,
        asset_id: str,
        alert_type: str,
        severity: str,
        message: str,
        recipients: Optional[Sequence[str]] = None,
        title: Optional[str] = None,
        channels: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_severity = self._normalize_severity(severity)
        normalized_alert_type = str(alert_type or "system").strip().lower() or "system"
        asset_id = str(asset_id or "UNKNOWN_ASSET")

        final_recipients = self._build_recipients(
            alert_type=normalized_alert_type,
            severity=normalized_severity,
            recipients=recipients,
        )
        final_channels = self._build_channels(
            severity=normalized_severity,
            channels=channels,
        )
        title = title or self._build_title(asset_id, normalized_alert_type, normalized_severity)

        record = NotificationRecord(
            id=self._next_id(),
            timestamp=self._now_iso(),
            asset_id=asset_id,
            alert_type=normalized_alert_type,
            severity=normalized_severity,
            title=title,
            message=str(message),
            recipients=list(final_recipients),
            channels=list(final_channels),
            status="sent",
            metadata=_deep_copy_dict(metadata),
        )

        record_dict = asdict(record)
        self.notification_history.append(record_dict)

        return {
            "success": True,
            "notification_id": record.id,
            "asset_id": asset_id,
            "alert_type": normalized_alert_type,
            "severity": normalized_severity,
            "title": title,
            "message": str(message),
            "recipients": list(final_recipients),
            "sent_to": len(final_recipients),
            "channels": list(final_channels),
            "status": "sent",
            "timestamp": record.timestamp,
            "metadata": _deep_copy_dict(metadata),
        }

    def escalate(
        self,
        asset_id: str,
        reason: str,
        priority: str = "high",
        telemetry: Optional[Dict[str, Any]] = None,
        prediction: Optional[Dict[str, Any]] = None,
        recipients: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        telemetry = telemetry or {}
        prediction = prediction or {}

        severity = "critical"
        escalation_recipients = list(recipients) if recipients else [
            "senior_logistics_manager",
            "operations_director",
            "quality_director",
        ]

        message = self._build_message(
            asset_id=str(asset_id),
            alert_type="escalation",
            severity=severity,
            telemetry=telemetry,
            prediction=prediction,
            decision={"type": "escalation", "priority": priority},
            reason=reason,
        )

        final_metadata = _deep_copy_dict(metadata)
        final_metadata.update(
            {
                "requested_priority": str(priority),
                "reason": str(reason),
                "telemetry": _deep_copy_dict(telemetry),
                "prediction": _deep_copy_dict(prediction),
            }
        )

        return self.send_alert(
            asset_id=str(asset_id),
            alert_type="escalation",
            severity=severity,
            title=self._build_title(str(asset_id), "escalation", severity),
            message=message,
            recipients=escalation_recipients,
            channels=self.default_channels_by_severity["critical"],
            metadata=final_metadata,
        )

    def notify_decision(
        self,
        telemetry: Dict[str, Any],
        prediction: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
        recipients: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        telemetry = telemetry or {}
        prediction = prediction or {}
        decision = decision or {}

        asset_id = str(telemetry.get("asset_id") or decision.get("asset_id") or "UNKNOWN_ASSET")
        alert_type = self._derive_alert_type(telemetry=telemetry, decision=decision)
        severity = self._infer_severity(
            telemetry=telemetry,
            prediction=prediction,
            decision=decision,
            alert_type=alert_type,
        )

        message = self._build_message(
            asset_id=asset_id,
            alert_type=alert_type,
            severity=severity,
            telemetry=telemetry,
            prediction=prediction,
            decision=decision,
            reason=str(decision.get("reason") or "").strip() or None,
        )

        metadata = {
            "telemetry": _deep_copy_dict(telemetry),
            "prediction": _deep_copy_dict(prediction),
            "decision": _deep_copy_dict(decision),
        }

        return self.send_alert(
            asset_id=asset_id,
            alert_type=alert_type,
            severity=severity,
            title=self._build_title(asset_id, alert_type, severity),
            message=message,
            recipients=recipients,
            metadata=metadata,
        )

    def get_notification_history(
        self,
        asset_id: Optional[str] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        records = list(self.notification_history)

        if asset_id is not None:
            asset_id = str(asset_id)
            records = [r for r in records if str(r.get("asset_id")) == asset_id]

        if severity is not None:
            sev = self._normalize_severity(severity)
            records = [r for r in records if self._normalize_severity(r.get("severity")) == sev]

        if alert_type is not None:
            typ = str(alert_type).strip().lower()
            records = [r for r in records if str(r.get("alert_type")).strip().lower() == typ]

        return records

    def get_latest_notification(self, asset_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        records = self.get_notification_history(asset_id=asset_id)
        if not records:
            return None
        return records[-1]

    def summarize_asset_alerts(self, asset_id: str) -> Dict[str, Any]:
        records = self.get_notification_history(asset_id=asset_id)

        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        alert_type_counts: Dict[str, int] = {}

        for record in records:
            sev = self._normalize_severity(record.get("severity"))
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            typ = str(record.get("alert_type") or "unknown")
            alert_type_counts[typ] = alert_type_counts.get(typ, 0) + 1

        return {
            "asset_id": str(asset_id),
            "total_notifications": len(records),
            "severity_counts": severity_counts,
            "alert_type_counts": alert_type_counts,
            "latest_notification": records[-1] if records else None,
        }