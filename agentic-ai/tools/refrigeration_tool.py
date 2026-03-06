from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


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


@dataclass(frozen=True)
class CargoCoolingProfile:
    name: str
    temp_min_c: float
    temp_max_c: float
    hard_temp_low_c: float
    hard_temp_high_c: float
    freeze_sensitive: bool = False
    freeze_temp_c: float = 0.0


class RefrigerationTool:
    def __init__(self) -> None:
        self.cargo_profiles: Dict[str, CargoCoolingProfile] = {
            "vaccines": CargoCoolingProfile(
                name="vaccines",
                temp_min_c=2.0,
                temp_max_c=8.0,
                hard_temp_low_c=0.0,
                hard_temp_high_c=12.0,
                freeze_sensitive=True,
                freeze_temp_c=0.0,
            ),
            "meat": CargoCoolingProfile(
                name="meat",
                temp_min_c=-1.0,
                temp_max_c=4.0,
                hard_temp_low_c=-5.0,
                hard_temp_high_c=8.0,
            ),
            "dairy": CargoCoolingProfile(
                name="dairy",
                temp_min_c=1.0,
                temp_max_c=7.0,
                hard_temp_low_c=-1.0,
                hard_temp_high_c=12.0,
            ),
            "pharmaceuticals": CargoCoolingProfile(
                name="pharmaceuticals",
                temp_min_c=15.0,
                temp_max_c=25.0,
                hard_temp_low_c=10.0,
                hard_temp_high_c=35.0,
            ),
            "frozen_food": CargoCoolingProfile(
                name="frozen_food",
                temp_min_c=-25.0,
                temp_max_c=-15.0,
                hard_temp_low_c=-35.0,
                hard_temp_high_c=-5.0,
            ),
            "produce": CargoCoolingProfile(
                name="produce",
                temp_min_c=2.0,
                temp_max_c=10.0,
                hard_temp_low_c=0.0,
                hard_temp_high_c=18.0,
            ),
            "seafood": CargoCoolingProfile(
                name="seafood",
                temp_min_c=-2.0,
                temp_max_c=2.0,
                hard_temp_low_c=-6.0,
                hard_temp_high_c=6.0,
            ),
            "ice_cream": CargoCoolingProfile(
                name="ice_cream",
                temp_min_c=-30.0,
                temp_max_c=-18.0,
                hard_temp_low_c=-40.0,
                hard_temp_high_c=-10.0,
            ),
            "blood_plasma": CargoCoolingProfile(
                name="blood_plasma",
                temp_min_c=2.0,
                temp_max_c=6.0,
                hard_temp_low_c=0.0,
                hard_temp_high_c=10.0,
                freeze_sensitive=True,
                freeze_temp_c=0.0,
            ),
            "flowers": CargoCoolingProfile(
                name="flowers",
                temp_min_c=2.0,
                temp_max_c=8.0,
                hard_temp_low_c=0.0,
                hard_temp_high_c=14.0,
            ),
        }

        self.action_aliases: Dict[str, str] = {
            "increase_cooling": "increase_cooling",
            "increasecooling": "increase_cooling",
            "decrease_cooling": "decrease_cooling",
            "decreasecooling": "decrease_cooling",
            "max_cooling": "max_cooling",
            "maxcooling": "max_cooling",
            "eco_mode": "eco_mode",
            "ecomode": "eco_mode",
            "emergency_mode": "emergency_mode",
            "emergencymode": "emergency_mode",
            "hold": "hold",
            "monitor": "hold",
            "normal": "hold",
        }

        self.action_effects: Dict[str, Dict[str, float]] = {
            "increase_cooling": {"delta_temp_c": -2.0, "power_change_pct": 20.0},
            "decrease_cooling": {"delta_temp_c": 1.0, "power_change_pct": -10.0},
            "max_cooling": {"delta_temp_c": -5.0, "power_change_pct": 50.0},
            "eco_mode": {"delta_temp_c": 0.5, "power_change_pct": -30.0},
            "emergency_mode": {"delta_temp_c": -8.0, "power_change_pct": 100.0},
            "hold": {"delta_temp_c": 0.0, "power_change_pct": 0.0},
        }

    def normalize_cargo_type(self, cargo_type: Optional[str]) -> Optional[str]:
        if cargo_type is None:
            return None
        cargo = str(cargo_type).strip().lower()
        return cargo if cargo in self.cargo_profiles else None

    def normalize_action(self, action: str) -> Optional[str]:
        if action is None:
            return None
        return self.action_aliases.get(str(action).strip().lower())

    def get_cargo_profile(self, cargo_type: Optional[str]) -> Optional[CargoCoolingProfile]:
        cargo = self.normalize_cargo_type(cargo_type)
        if cargo is None:
            return None
        return self.cargo_profiles[cargo]

    def get_target_band(self, cargo_type: Optional[str]) -> Tuple[float, float]:
        profile = self.get_cargo_profile(cargo_type)
        if profile is None:
            return (2.0, 8.0)
        return (profile.temp_min_c, profile.temp_max_c)

    def get_ideal_temp(self, cargo_type: Optional[str]) -> float:
        low, high = self.get_target_band(cargo_type)
        return (low + high) / 2.0

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

    def _extract_time_to_failure_hours(self, prediction: Optional[Dict[str, Any]]) -> Optional[float]:
        if not prediction:
            return None

        for key in (
            "time_to_failure_hours",
            "time_to_failure",
            "timetofailurehours",
            "timetofailure",
        ):
            if key in prediction and prediction[key] is not None:
                val = _safe_float(prediction[key], -1.0)
                return None if val < 0 else val

        return None

    def get_cooling_recommendation(
        self,
        current_temp: float,
        ideal_temp: Optional[float] = None,
        risk_score: float = 0.0,
        cargo_type: Optional[str] = None,
        refrigeration_failed: bool = False,
        scenario: Optional[str] = None,
        temp_rate_c_per_hour: Optional[float] = None,
    ) -> str:
        current_temp = _safe_float(current_temp, 0.0)
        risk_score = _clamp(_safe_float(risk_score, 0.0), 0.0, 1.0)
        cargo = self.normalize_cargo_type(cargo_type)
        profile = self.get_cargo_profile(cargo)
        scenario_name = str(scenario or "").strip().lower()

        if ideal_temp is None:
            ideal_temp = self.get_ideal_temp(cargo)
        else:
            ideal_temp = _safe_float(ideal_temp, self.get_ideal_temp(cargo))

        if profile is None:
            temp_diff = current_temp - ideal_temp

            if refrigeration_failed and (risk_score >= 0.40 or temp_diff > 1.0):
                return "emergency_mode"
            if risk_score >= 0.85:
                return "emergency_mode"
            if risk_score >= 0.65 or temp_diff >= 5.0:
                return "max_cooling"
            if risk_score >= 0.40 or temp_diff >= 2.0:
                return "increase_cooling"
            if temp_diff <= -1.0:
                return "decrease_cooling"
            if abs(temp_diff) <= 0.5 and risk_score < 0.20:
                return "eco_mode"
            return "hold"

        low = profile.temp_min_c
        high = profile.temp_max_c
        hard_low = profile.hard_temp_low_c
        hard_high = profile.hard_temp_high_c

        if profile.freeze_sensitive and current_temp <= profile.freeze_temp_c:
            return "decrease_cooling"

        if refrigeration_failed or scenario_name == "refrigeration_failure":
            if current_temp >= high or risk_score >= 0.40:
                return "emergency_mode"

        if current_temp >= hard_high or risk_score >= 0.90:
            return "emergency_mode"

        if temp_rate_c_per_hour is not None and _safe_float(temp_rate_c_per_hour, 0.0) >= 2.0:
            return "max_cooling"

        if current_temp >= high + 4.0 or risk_score >= 0.75:
            return "max_cooling"

        if current_temp > high or risk_score >= 0.40:
            return "increase_cooling"

        if profile.freeze_sensitive and current_temp <= profile.freeze_temp_c + 0.5:
            return "decrease_cooling"

        if current_temp < low - 1.5:
            return "decrease_cooling"

        if low <= current_temp <= high and risk_score < 0.20:
            return "eco_mode"

        if abs(current_temp - ideal_temp) <= 0.5:
            return "hold"

        return "hold"

    def _compute_safe_target_temp(
        self,
        current_temp: float,
        delta_temp_c: float,
        profile: Optional[CargoCoolingProfile],
    ) -> float:
        target_temp = current_temp + delta_temp_c

        if profile is None:
            return round(target_temp, 2)

        target_temp = _clamp(target_temp, profile.hard_temp_low_c, profile.hard_temp_high_c)

        if profile.freeze_sensitive and target_temp <= profile.freeze_temp_c:
            target_temp = max(profile.freeze_temp_c + 0.5, profile.hard_temp_low_c)

        return round(target_temp, 2)

    def adjust_cooling(
        self,
        asset_id: str,
        action: str,
        current_temp: float,
        cargo_type: Optional[str] = None,
        refrigeration_failed: bool = False,
        scenario: Optional[str] = None,
    ) -> Dict[str, Any]:
        canonical_action = self.normalize_action(action)
        if canonical_action is None or canonical_action not in self.action_effects:
            return {
                "success": False,
                "asset_id": asset_id,
                "error": f"Unsupported action: {action}",
            }

        current_temp = _safe_float(current_temp, 0.0)
        cargo = self.normalize_cargo_type(cargo_type)
        profile = self.get_cargo_profile(cargo)
        effect = self.action_effects[canonical_action]

        target_temp = self._compute_safe_target_temp(
            current_temp=current_temp,
            delta_temp_c=effect["delta_temp_c"],
            profile=profile,
        )

        estimated_time_minutes = round(abs(target_temp - current_temp) * 15.0, 2)
        recommended_low, recommended_high = self.get_target_band(cargo)

        notes: List[str] = []

        if canonical_action == "emergency_mode":
            notes.append("Emergency cooling requested")
        if refrigeration_failed:
            notes.append("Refrigeration failure context detected; backup or manual intervention may be required")
        if profile and profile.freeze_sensitive and target_temp <= profile.freeze_temp_c + 0.5:
            notes.append("Freeze-sensitive cargo protection applied")
        if profile and target_temp < profile.temp_min_c:
            notes.append("Target remains below preferred cargo band; monitor for overcooling")
        if profile and target_temp > profile.temp_max_c:
            notes.append("Target remains above preferred cargo band; continued intervention may be needed")

        return {
            "success": True,
            "asset_id": asset_id,
            "action": canonical_action,
            "requested_action": action,
            "cargo_type": cargo or "unknown",
            "current_temp": round(current_temp, 2),
            "target_temp": round(target_temp, 2),
            "power_change_pct": round(effect["power_change_pct"], 2),
            "estimated_time_minutes": estimated_time_minutes,
            "recommended_range": {
                "min_c": round(recommended_low, 2),
                "max_c": round(recommended_high, 2),
            },
            "refrigeration_failed": bool(refrigeration_failed),
            "scenario": str(scenario or ""),
            "notes": notes,
        }

    def recommend_action(
        self,
        telemetry: Dict[str, Any],
        prediction: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        asset_id = str(telemetry.get("asset_id") or "UNKNOWN_ASSET")
        cargo_type = self.normalize_cargo_type(telemetry.get("cargo_type"))
        current_temp = _safe_float(telemetry.get("temperature"), 0.0)
        scenario = str(telemetry.get("scenario") or "").strip().lower()
        refrigeration_failed = _to_bool(telemetry.get("refrigeration_failed"))

        risk_score = self._extract_risk_score(prediction)
        time_to_failure_hours = self._extract_time_to_failure_hours(prediction)

        temp_degree_minutes = _safe_float(
            (telemetry.get("cumulative_exposure") or {}).get("temp_degree_minutes"),
            0.0,
        )
        door_open = _to_bool(telemetry.get("door_open"))

        action = self.get_cooling_recommendation(
            current_temp=current_temp,
            cargo_type=cargo_type,
            risk_score=risk_score,
            refrigeration_failed=refrigeration_failed,
            scenario=scenario,
        )

        command = self.adjust_cooling(
            asset_id=asset_id,
            action=action,
            current_temp=current_temp,
            cargo_type=cargo_type,
            refrigeration_failed=refrigeration_failed,
            scenario=scenario,
        )

        low, high = self.get_target_band(cargo_type)
        rationale: List[str] = []

        if current_temp > high:
            rationale.append("Temperature is above the preferred cargo range")
        elif current_temp < low:
            rationale.append("Temperature is below the preferred cargo range")
        else:
            rationale.append("Temperature is within the preferred cargo range")

        if risk_score >= 0.75:
            rationale.append("Predicted spoilage risk is high")
        elif risk_score >= 0.40:
            rationale.append("Predicted spoilage risk is moderate")

        if refrigeration_failed:
            rationale.append("Refrigeration failure flag is active")

        if scenario == "refrigeration_failure":
            rationale.append("Shipment is in refrigeration-failure scenario")

        if temp_degree_minutes > 0:
            rationale.append(f"Cumulative temperature exposure detected: {round(temp_degree_minutes, 2)} degree-minutes")

        if door_open:
            rationale.append("Door is currently open, which may worsen thermal drift")

        if time_to_failure_hours is not None:
            rationale.append(f"Estimated time to failure: {round(time_to_failure_hours, 2)} hours")

        return {
            "asset_id": asset_id,
            "cargo_type": cargo_type or "unknown",
            "current_temp": round(current_temp, 2),
            "recommended_action": action,
            "risk_score": round(risk_score, 3),
            "time_to_failure_hours": time_to_failure_hours,
            "target_band": {
                "min_c": round(low, 2),
                "max_c": round(high, 2),
            },
            "command_preview": command,
            "rationale": rationale,
        }