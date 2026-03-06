from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tools.routing_tool import RoutingTool
from tools.refrigeration_tool import RefrigerationTool
from tools.notification_tool import NotificationTool


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


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


class ColdChainDecisionAgent:
    def __init__(self) -> None:
        self.routing_tool = RoutingTool()
        self.refrigeration_tool = RefrigerationTool()
        self.notification_tool = NotificationTool()

        self.decision_history: List[Dict[str, Any]] = []

        self.RISK_THRESHOLDS: Dict[str, float] = {
            "low": 0.30,
            "moderate": 0.70,
            "high": 0.85,
            "critical": 0.95,
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

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
                return max(0.0, min(1.0, _safe_float(prediction[key], 0.0)))

        return 0.0

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

    def _normalize_prediction(self, prediction: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        base = _deep_copy_dict(prediction)
        risk_score = self._extract_risk_score(base)
        time_to_failure_hours = self._extract_time_to_failure_hours(base)

        if "risk_score" not in base:
            base["risk_score"] = risk_score
        if "predicted_risk_proxy" not in base:
            base["predicted_risk_proxy"] = risk_score
        if time_to_failure_hours is not None and "time_to_failure_hours" not in base:
            base["time_to_failure_hours"] = time_to_failure_hours

        return base

    def _get_risk_level(
        self,
        risk_score: float,
        refrigeration_failed: bool = False,
        time_to_failure_hours: Optional[float] = None,
    ) -> str:
        if risk_score < self.RISK_THRESHOLDS["low"]:
            level = "low"
        elif risk_score < self.RISK_THRESHOLDS["moderate"]:
            level = "moderate"
        elif risk_score < self.RISK_THRESHOLDS["high"]:
            level = "high"
        else:
            level = "critical"

        if refrigeration_failed:
            if level == "low":
                level = "moderate"
            elif level == "moderate":
                level = "high"

        if time_to_failure_hours is not None:
            if time_to_failure_hours <= 1.0:
                level = "critical"
            elif time_to_failure_hours <= 3.0 and level in {"low", "moderate"}:
                level = "high"

        return level

    def analyze_situation(self, prediction: Dict[str, Any], telemetry: Dict[str, Any]) -> Dict[str, Any]:
        normalized_prediction = self._normalize_prediction(prediction)

        risk_score = self._extract_risk_score(normalized_prediction)
        time_to_failure_hours = self._extract_time_to_failure_hours(normalized_prediction)

        cargo_type = str(telemetry.get("cargo_type") or "").strip().lower() or None
        current_temp = _safe_float(telemetry.get("temperature"), 0.0)
        current_humidity = _safe_float(telemetry.get("humidity"), 0.0)
        current_vibration = _safe_float(telemetry.get("vibration"), 0.0)
        door_open = _to_bool(telemetry.get("door_open"))
        refrigeration_failed = _to_bool(telemetry.get("refrigeration_failed"))
        scenario = str(telemetry.get("scenario") or "").strip().lower()

        temp_band_min, temp_band_max = self.refrigeration_tool.get_target_band(cargo_type)
        ideal_temp = self.refrigeration_tool.get_ideal_temp(cargo_type)

        contributing_factors: List[str] = []

        if current_temp < temp_band_min or current_temp > temp_band_max:
            contributing_factors.append("temperature_excursion")

        if refrigeration_failed:
            contributing_factors.append("refrigeration_failure")

        if scenario == "refrigeration_failure":
            contributing_factors.append("refrigeration_failure_scenario")
        elif scenario and scenario != "normal":
            contributing_factors.append(f"scenario_{scenario}")

        if current_humidity > 85.0:
            contributing_factors.append("high_humidity")
        elif current_humidity < 20.0:
            contributing_factors.append("low_humidity")

        if current_vibration > 5.0:
            contributing_factors.append("excessive_vibration")

        if door_open:
            contributing_factors.append("door_open_event")

        exposure = telemetry.get("cumulative_exposure") or {}
        temp_degree_minutes = _safe_float(exposure.get("temp_degree_minutes"), 0.0)
        humidity_percent_minutes = _safe_float(exposure.get("humidity_percent_minutes"), 0.0)
        door_open_minutes = _safe_float(exposure.get("door_open_minutes"), 0.0)
        out_of_range_minutes = _safe_float(exposure.get("out_of_range_minutes_in_hour"), 0.0)

        if temp_degree_minutes > 0:
            contributing_factors.append("cumulative_temperature_exposure")
        if humidity_percent_minutes > 0:
            contributing_factors.append("cumulative_humidity_exposure")
        if door_open_minutes > 0:
            contributing_factors.append("cumulative_door_open_exposure")
        if out_of_range_minutes > 10.0:
            contributing_factors.append("sustained_out_of_range_exposure")

        if time_to_failure_hours is not None and time_to_failure_hours <= 6.0:
            contributing_factors.append("short_time_to_failure")

        risk_level = self._get_risk_level(
            risk_score=risk_score,
            refrigeration_failed=refrigeration_failed,
            time_to_failure_hours=time_to_failure_hours,
        )

        requires_action = (
            risk_score >= self.RISK_THRESHOLDS["moderate"]
            or refrigeration_failed
            or current_temp < temp_band_min
            or current_temp > temp_band_max
            or (time_to_failure_hours is not None and time_to_failure_hours <= 6.0)
        )

        if current_temp < temp_band_min:
            temperature_status = "below_range"
        elif current_temp > temp_band_max:
            temperature_status = "above_range"
        else:
            temperature_status = "within_range"

        return {
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "contributing_factors": contributing_factors,
            "time_to_failure_hours": time_to_failure_hours,
            "requires_action": bool(requires_action),
            "temperature_status": temperature_status,
            "temperature_band": {
                "min_c": round(temp_band_min, 2),
                "max_c": round(temp_band_max, 2),
                "ideal_c": round(ideal_temp, 2),
            },
            "exposure_summary": {
                "temp_degree_minutes": round(temp_degree_minutes, 2),
                "humidity_percent_minutes": round(humidity_percent_minutes, 2),
                "door_open_minutes": round(door_open_minutes, 2),
                "out_of_range_minutes_in_hour": round(out_of_range_minutes, 2),
            },
        }

    def _build_monitor_action(self, analysis: Dict[str, Any], telemetry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "monitor",
            "description": "Continue normal monitoring",
            "priority": "low",
            "tool": "none",
            "asset_id": telemetry.get("asset_id"),
            "risk_level": analysis.get("risk_level"),
        }

    def _build_cooling_action(
        self,
        telemetry: Dict[str, Any],
        prediction: Dict[str, Any],
        priority: str,
    ) -> Dict[str, Any]:
        cooling_plan = self.refrigeration_tool.recommend_action(telemetry, prediction)
        command_preview = cooling_plan.get("command_preview") or {}

        return {
            "type": "adjust_cooling",
            "action": cooling_plan.get("recommended_action", "hold"),
            "description": f"Adjust refrigeration: {cooling_plan.get('recommended_action', 'hold')}",
            "priority": priority,
            "tool": "refrigeration",
            "asset_id": telemetry.get("asset_id"),
            "cargo_type": telemetry.get("cargo_type"),
            "current_temp": telemetry.get("temperature"),
            "target_band": cooling_plan.get("target_band"),
            "command_preview": command_preview,
            "rationale": list(cooling_plan.get("rationale", [])),
        }

    def _build_reroute_action(
        self,
        telemetry: Dict[str, Any],
        prediction: Dict[str, Any],
        priority: str,
        max_results: int = 2,
    ) -> Optional[Dict[str, Any]]:
        route_plan = self.routing_tool.recommend_reroute(
            telemetry=telemetry,
            prediction=prediction,
            max_results=max_results,
        )

        recommended_dc = route_plan.get("recommended_dc")
        if not recommended_dc:
            return None

        return {
            "type": "reroute",
            "description": (
                f"Reroute to {recommended_dc.get('name')} "
                f"(ETA: {recommended_dc.get('eta_hours')}h)"
            ),
            "priority": priority,
            "tool": "routing",
            "asset_id": telemetry.get("asset_id"),
            "target_dc": recommended_dc.get("id"),
            "dc_name": recommended_dc.get("name"),
            "eta_hours": recommended_dc.get("eta_hours"),
            "distance_km": recommended_dc.get("distance_km"),
            "benefit_score": recommended_dc.get("benefit_score"),
            "recommended_dc": recommended_dc,
            "alternatives": route_plan.get("alternatives", []),
        }

    def _build_notify_action(
        self,
        telemetry: Dict[str, Any],
        priority: str,
        alert_type: str,
        description: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "type": "notify",
            "alert_type": alert_type,
            "description": description,
            "priority": priority,
            "tool": "notification",
            "asset_id": telemetry.get("asset_id"),
            "reason": reason or description,
        }

    def _build_escalate_action(
        self,
        telemetry: Dict[str, Any],
        reason: str,
        priority: str = "critical",
    ) -> Dict[str, Any]:
        return {
            "type": "escalate",
            "description": f"Escalate issue: {reason}",
            "priority": priority,
            "tool": "notification",
            "asset_id": telemetry.get("asset_id"),
            "reason": reason,
        }

    def decide_action(
        self,
        analysis: Dict[str, Any],
        telemetry: Dict[str, Any],
        prediction: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        prediction = self._normalize_prediction(prediction)
        actions: List[Dict[str, Any]] = []

        risk_level = str(analysis.get("risk_level") or "low").strip().lower()
        refrigeration_failed = _to_bool(telemetry.get("refrigeration_failed"))
        temperature_status = str(analysis.get("temperature_status") or "within_range").strip().lower()

        if risk_level == "low" and not analysis.get("requires_action", False):
            actions.append(self._build_monitor_action(analysis, telemetry))
            return actions

        if risk_level == "moderate":
            actions.append(
                self._build_cooling_action(
                    telemetry=telemetry,
                    prediction=prediction,
                    priority="medium",
                )
            )
            actions.append(
                self._build_notify_action(
                    telemetry=telemetry,
                    priority="medium",
                    alert_type="spoilage_risk",
                    description="Alert logistics team of moderate spoilage risk",
                    reason="Moderate spoilage risk detected",
                )
            )
            return actions

        if risk_level == "high":
            reroute_action = self._build_reroute_action(
                telemetry=telemetry,
                prediction=prediction,
                priority="high",
                max_results=2,
            )
            if reroute_action is not None:
                actions.append(reroute_action)

            actions.append(
                self._build_cooling_action(
                    telemetry=telemetry,
                    prediction=prediction,
                    priority="high",
                )
            )

            actions.append(
                self._build_notify_action(
                    telemetry=telemetry,
                    priority="high",
                    alert_type="spoilage_risk" if reroute_action is None else "reroute",
                    description="High-priority alert for logistics and quality teams",
                    reason="High spoilage risk requires immediate intervention",
                )
            )
            return actions

        if risk_level == "critical":
            reroute_action = self._build_reroute_action(
                telemetry=telemetry,
                prediction=prediction,
                priority="critical",
                max_results=3,
            )
            if reroute_action is not None:
                actions.append(reroute_action)

            cooling_action = self._build_cooling_action(
                telemetry=telemetry,
                prediction=prediction,
                priority="critical",
            )

            if refrigeration_failed and cooling_action.get("action") in {"hold", "eco_mode"}:
                cooling_action["action"] = "emergency_mode"
                cooling_action["description"] = "Adjust refrigeration: emergency_mode"

            if temperature_status == "above_range" and cooling_action.get("action") == "hold":
                cooling_action["action"] = "max_cooling"
                cooling_action["description"] = "Adjust refrigeration: max_cooling"

            actions.append(cooling_action)

            actions.append(
                self._build_notify_action(
                    telemetry=telemetry,
                    priority="critical",
                    alert_type="cooling_failure" if refrigeration_failed else "spoilage_risk",
                    description="Critical alert issued to operations leadership",
                    reason="Critical spoilage risk detected",
                )
            )

            actions.append(
                self._build_escalate_action(
                    telemetry=telemetry,
                    reason="Critical spoilage risk or refrigeration instability requires escalation",
                    priority="critical",
                )
            )
            return actions

        actions.append(self._build_monitor_action(analysis, telemetry))
        return actions

    def execute_actions(
        self,
        actions: List[Dict[str, Any]],
        telemetry: Dict[str, Any],
        prediction: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        prediction = self._normalize_prediction(prediction)
        results: List[Dict[str, Any]] = []

        asset_id = str(telemetry.get("asset_id") or "UNKNOWN_ASSET")
        cargo_type = telemetry.get("cargo_type")
        current_temp = _safe_float(telemetry.get("temperature"), 0.0)
        scenario = telemetry.get("scenario")
        refrigeration_failed = _to_bool(telemetry.get("refrigeration_failed"))

        for action in actions:
            action_type = str(action.get("type") or "").strip().lower()

            if action_type == "monitor":
                result = {
                    "success": True,
                    "type": "monitor",
                    "asset_id": asset_id,
                    "status": "monitoring",
                    "message": action.get("description", "Continue monitoring"),
                }

            elif action_type == "adjust_cooling":
                result = self.refrigeration_tool.adjust_cooling(
                    asset_id=asset_id,
                    action=str(action.get("action") or "hold"),
                    current_temp=current_temp,
                    cargo_type=cargo_type,
                    refrigeration_failed=refrigeration_failed,
                    scenario=scenario,
                )
                result["type"] = "adjust_cooling"

            elif action_type == "reroute":
                result = {
                    "success": True,
                    "type": "reroute",
                    "asset_id": asset_id,
                    "status": "recommended",
                    "target_dc": action.get("target_dc"),
                    "dc_name": action.get("dc_name"),
                    "eta_hours": action.get("eta_hours"),
                    "distance_km": action.get("distance_km"),
                    "benefit_score": action.get("benefit_score"),
                    "recommended_dc": _deep_copy_dict(action.get("recommended_dc")),
                    "alternatives": list(action.get("alternatives", [])),
                }

            elif action_type == "notify":
                notify_payload = _deep_copy_dict(action)
                notify_payload["type"] = action.get("alert_type") or "spoilage_risk"

                result = self.notification_tool.notify_decision(
                    telemetry=telemetry,
                    prediction=prediction,
                    decision=notify_payload,
                    recipients=action.get("recipients"),
                )
                result["type"] = "notify"

            elif action_type == "escalate":
                result = self.notification_tool.escalate(
                    asset_id=asset_id,
                    reason=str(action.get("reason") or action.get("description") or "Escalation required"),
                    priority=str(action.get("priority") or "critical"),
                    telemetry=telemetry,
                    prediction=prediction,
                    recipients=action.get("recipients"),
                )
                result["type"] = "escalate"

            else:
                result = {
                    "success": False,
                    "type": action_type or "unknown",
                    "asset_id": asset_id,
                    "error": f"Unknown action type: {action_type}",
                }

            results.append(
                {
                    "action": _deep_copy_dict(action),
                    "result": result,
                }
            )

        return results

    def process_decision(
        self,
        prediction: Dict[str, Any],
        telemetry: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized_prediction = self._normalize_prediction(prediction)
        analysis = self.analyze_situation(normalized_prediction, telemetry)
        actions = self.decide_action(analysis, telemetry, normalized_prediction)
        execution_results = self.execute_actions(actions, telemetry, normalized_prediction)

        record = {
            "decision_id": f"DECISION_{len(self.decision_history) + 1:06d}",
            "timestamp": self._now_iso(),
            "asset_id": telemetry.get("asset_id"),
            "telemetry": _deep_copy_dict(telemetry),
            "prediction": _deep_copy_dict(normalized_prediction),
            "analysis": analysis,
            "actions": actions,
            "execution_results": execution_results,
        }

        self.decision_history.append(record)
        return record

    def evaluate_and_act(
        self,
        prediction: Dict[str, Any],
        telemetry: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.process_decision(prediction=prediction, telemetry=telemetry)

    def get_decision_history(self, asset_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if asset_id is None:
            return list(self.decision_history)

        asset_id = str(asset_id)
        return [d for d in self.decision_history if str(d.get("asset_id")) == asset_id]

    def get_latest_decision(self, asset_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        history = self.get_decision_history(asset_id=asset_id)
        if not history:
            return None
        return history[-1]