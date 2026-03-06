from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
import math

Location = Tuple[float, float]

SUPPORTED_CARGO_TYPES: Tuple[str, ...] = (
    "vaccines",
    "meat",
    "dairy",
    "pharmaceuticals",
    "frozen_food",
    "produce",
    "seafood",
    "ice_cream",
    "blood_plasma",
    "flowers",
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class DistributionCenter:
    id: str
    name: str
    location: Location
    capacity: int
    current_load: int
    refrigeration_status: str = "operational"
    supported_cargo_types: Tuple[str, ...] = SUPPORTED_CARGO_TYPES
    priority_rank: int = 1

    @property
    def available_capacity(self) -> int:
        return max(0, int(self.capacity) - int(self.current_load))

    @property
    def has_capacity(self) -> bool:
        return self.available_capacity > 0


class RoutingTool:
    def __init__(
        self,
        average_speed_kmph: float = 45.0,
        max_service_radius_km: float = 350.0,
    ) -> None:
        self.average_speed_kmph = float(max(1.0, average_speed_kmph))
        self.max_service_radius_km = float(max(10.0, max_service_radius_km))
        self.distribution_centers: List[DistributionCenter] = self._build_default_centers()

    def _build_default_centers(self) -> List[DistributionCenter]:
        return [
            DistributionCenter(
                id="DC_AGRA",
                name="Agra Distribution Center",
                location=(27.1767, 78.0081),
                capacity=80,
                current_load=38,
                refrigeration_status="operational",
                supported_cargo_types=SUPPORTED_CARGO_TYPES,
                priority_rank=1,
            ),
            DistributionCenter(
                id="DC_MATHURA",
                name="Mathura Cold Hub",
                location=(27.4924, 77.6737),
                capacity=60,
                current_load=21,
                refrigeration_status="operational",
                supported_cargo_types=(
                    "vaccines",
                    "dairy",
                    "produce",
                    "flowers",
                    "blood_plasma",
                    "pharmaceuticals",
                ),
                priority_rank=1,
            ),
            DistributionCenter(
                id="DC_FIROZABAD",
                name="Firozabad Transit Facility",
                location=(27.1591, 78.3957),
                capacity=45,
                current_load=17,
                refrigeration_status="operational",
                supported_cargo_types=(
                    "vaccines",
                    "dairy",
                    "produce",
                    "pharmaceuticals",
                    "flowers",
                ),
                priority_rank=2,
            ),
            DistributionCenter(
                id="DC_DELHI",
                name="Delhi Compliance Center",
                location=(28.7041, 77.1025),
                capacity=120,
                current_load=66,
                refrigeration_status="operational",
                supported_cargo_types=SUPPORTED_CARGO_TYPES,
                priority_rank=1,
            ),
            DistributionCenter(
                id="DC_NOIDA",
                name="Noida Pharma and Foods Hub",
                location=(28.5355, 77.3910),
                capacity=90,
                current_load=44,
                refrigeration_status="operational",
                supported_cargo_types=(
                    "vaccines",
                    "dairy",
                    "pharmaceuticals",
                    "produce",
                    "blood_plasma",
                    "flowers",
                    "seafood",
                ),
                priority_rank=1,
            ),
            DistributionCenter(
                id="DC_KANPUR",
                name="Kanpur Refrigerated Logistics Hub",
                location=(26.4499, 80.3319),
                capacity=85,
                current_load=49,
                refrigeration_status="operational",
                supported_cargo_types=(
                    "meat",
                    "dairy",
                    "frozen_food",
                    "produce",
                    "seafood",
                    "ice_cream",
                    "pharmaceuticals",
                ),
                priority_rank=1,
            ),
            DistributionCenter(
                id="DC_GURUGRAM",
                name="Gurugram Rapid Response Center",
                location=(28.4595, 77.0266),
                capacity=70,
                current_load=28,
                refrigeration_status="operational",
                supported_cargo_types=(
                    "vaccines",
                    "dairy",
                    "pharmaceuticals",
                    "blood_plasma",
                    "produce",
                    "flowers",
                ),
                priority_rank=1,
            ),
        ]

    def _supports_cargo(self, center: DistributionCenter, cargo_type: Optional[str]) -> bool:
        if not cargo_type:
            return True
        return str(cargo_type).strip().lower() in set(center.supported_cargo_types)

    def _is_operational(self, center: DistributionCenter) -> bool:
        return str(center.refrigeration_status).strip().lower() == "operational"

    def _eta_hours(self, distance_km: float) -> float:
        return round(distance_km / self.average_speed_kmph, 2)

    def _center_to_dict(self, center: DistributionCenter, distance_km: float) -> Dict[str, Any]:
        return {
            "id": center.id,
            "name": center.name,
            "location": {
                "lat": round(center.location[0], 6),
                "lon": round(center.location[1], 6),
            },
            "distance_km": round(distance_km, 2),
            "eta_hours": self._eta_hours(distance_km),
            "capacity": int(center.capacity),
            "current_load": int(center.current_load),
            "available_capacity": int(center.available_capacity),
            "refrigeration_status": center.refrigeration_status,
            "supported_cargo_types": list(center.supported_cargo_types),
            "priority_rank": int(center.priority_rank),
        }

    def get_center_by_id(self, center_id: str) -> Optional[DistributionCenter]:
        center_id = str(center_id).strip().upper()
        for center in self.distribution_centers:
            if center.id.upper() == center_id:
                return center
        return None

    def find_nearest_centers(
        self,
        current_location: Location,
        max_results: int = 3,
        cargo_type: Optional[str] = None,
        exclude_ids: Optional[Sequence[str]] = None,
        min_available_capacity: int = 1,
        require_operational: bool = True,
    ) -> List[Dict[str, Any]]:
        if (
            not isinstance(current_location, (tuple, list))
            or len(current_location) != 2
        ):
            raise ValueError("current_location must be a (lat, lon) tuple")

        lat, lon = _safe_float(current_location[0]), _safe_float(current_location[1])
        cargo_type = (cargo_type or "").strip().lower() or None
        exclude = {str(x).strip().upper() for x in (exclude_ids or [])}

        centers_with_distance: List[Dict[str, Any]] = []

        for center in self.distribution_centers:
            if center.id.upper() in exclude:
                continue
            if center.available_capacity < int(min_available_capacity):
                continue
            if require_operational and not self._is_operational(center):
                continue
            if not self._supports_cargo(center, cargo_type):
                continue

            distance_km = _haversine_km(lat, lon, center.location[0], center.location[1])
            centers_with_distance.append(self._center_to_dict(center, distance_km))

        centers_with_distance.sort(
            key=lambda x: (
                x["distance_km"],
                -x["available_capacity"],
                x["priority_rank"],
            )
        )
        return centers_with_distance[: max(1, int(max_results))]

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
            "timetofailurehours",
            "time_to_failure",
            "timetofailure",
            "eta_to_failure_hours",
        ):
            if key in prediction and prediction[key] is not None:
                val = _safe_float(prediction[key], -1.0)
                return None if val < 0 else val
        return None

    def _normalize_center_input(
        self,
        alternative_dc: Any,
        current_location: Optional[Location] = None,
    ) -> Dict[str, Any]:
        if isinstance(alternative_dc, DistributionCenter):
            distance_km = 0.0
            if current_location is not None:
                distance_km = _haversine_km(
                    _safe_float(current_location[0]),
                    _safe_float(current_location[1]),
                    alternative_dc.location[0],
                    alternative_dc.location[1],
                )
            return self._center_to_dict(alternative_dc, distance_km)

        if isinstance(alternative_dc, str):
            center = self.get_center_by_id(alternative_dc)
            if center is None:
                raise ValueError(f"Unknown distribution center ID: {alternative_dc}")
            distance_km = 0.0
            if current_location is not None:
                distance_km = _haversine_km(
                    _safe_float(current_location[0]),
                    _safe_float(current_location[1]),
                    center.location[0],
                    center.location[1],
                )
            return self._center_to_dict(center, distance_km)

        if isinstance(alternative_dc, dict):
            if "id" in alternative_dc:
                center = self.get_center_by_id(str(alternative_dc["id"]))
                if center is not None:
                    distance_km = _safe_float(alternative_dc.get("distance_km"), -1.0)
                    if distance_km < 0 and current_location is not None:
                        distance_km = _haversine_km(
                            _safe_float(current_location[0]),
                            _safe_float(current_location[1]),
                            center.location[0],
                            center.location[1],
                        )
                    if distance_km < 0:
                        distance_km = 0.0
                    return self._center_to_dict(center, distance_km)

            if "location" in alternative_dc and isinstance(alternative_dc["location"], dict):
                lat = _safe_float(alternative_dc["location"].get("lat"))
                lon = _safe_float(alternative_dc["location"].get("lon"))
            else:
                lat = _safe_float(alternative_dc.get("lat"))
                lon = _safe_float(alternative_dc.get("lon"))

            distance_km = _safe_float(alternative_dc.get("distance_km"), 0.0)
            eta_hours = _safe_float(alternative_dc.get("eta_hours"), self._eta_hours(distance_km))

            return {
                "id": str(alternative_dc.get("id", "UNKNOWN_DC")),
                "name": str(alternative_dc.get("name", "Unknown Center")),
                "location": {"lat": round(lat, 6), "lon": round(lon, 6)},
                "distance_km": round(distance_km, 2),
                "eta_hours": round(eta_hours, 2),
                "capacity": int(_safe_float(alternative_dc.get("capacity"), 0)),
                "current_load": int(_safe_float(alternative_dc.get("current_load"), 0)),
                "available_capacity": int(_safe_float(alternative_dc.get("available_capacity"), 0)),
                "refrigeration_status": str(alternative_dc.get("refrigeration_status", "unknown")),
                "supported_cargo_types": list(alternative_dc.get("supported_cargo_types", [])),
                "priority_rank": int(_safe_float(alternative_dc.get("priority_rank"), 99)),
            }

        raise ValueError("alternative_dc must be a DistributionCenter, center ID, or dict")

    def calculate_reroute_benefit(
        self,
        current_location: Location,
        alternative_dc: Any,
        risk_score: float,
        time_to_failure_hours: Optional[float] = None,
        cargo_type: Optional[str] = None,
        refrigeration_failed: bool = False,
        scenario: Optional[str] = None,
        current_temp: Optional[float] = None,
    ) -> Dict[str, Any]:
        dc = self._normalize_center_input(alternative_dc, current_location=current_location)
        cargo_type = (cargo_type or "").strip().lower() or None
        risk_score = _clamp(_safe_float(risk_score, 0.0), 0.0, 1.0)
        scenario = (scenario or "").strip().lower()

        distance_km = _safe_float(dc.get("distance_km"), 0.0)
        eta_hours = _safe_float(dc.get("eta_hours"), self._eta_hours(distance_km))
        capacity = max(0, int(_safe_float(dc.get("capacity"), 0)))
        available_capacity = max(0, int(_safe_float(dc.get("available_capacity"), 0)))
        refrigeration_status = str(dc.get("refrigeration_status", "unknown")).strip().lower()
        supported = {str(x).strip().lower() for x in dc.get("supported_cargo_types", [])}

        compatible = True if not cargo_type else cargo_type in supported
        operational = refrigeration_status == "operational"
        capacity_ratio = 0.0 if capacity <= 0 else available_capacity / capacity

        distance_score = 1.0 - _clamp(distance_km / self.max_service_radius_km, 0.0, 1.0)
        refrigeration_score = 1.0 if operational else 0.0
        compatibility_score = 1.0 if compatible else 0.0

        can_arrive_before_failure: Optional[bool] = None
        eta_buffer_hours: Optional[float] = None
        viability_score = 0.5

        if time_to_failure_hours is not None:
            time_to_failure_hours = max(0.0, _safe_float(time_to_failure_hours, 0.0))
            eta_buffer_hours = round(time_to_failure_hours - eta_hours, 2)
            can_arrive_before_failure = eta_hours <= time_to_failure_hours
            viability_score = _clamp((eta_buffer_hours + 2.0) / 4.0, 0.0, 1.0)

        urgency_bonus = 0.0
        if refrigeration_failed:
            urgency_bonus += 0.10
        if scenario == "refrigeration_failure":
            urgency_bonus += 0.08
        if risk_score >= 0.80 and distance_km <= 60.0:
            urgency_bonus += 0.05
        if current_temp is not None and risk_score >= 0.70:
            urgency_bonus += 0.03

        if not compatible or not operational or available_capacity <= 0:
            benefit_score = 0.0
        else:
            benefit_score = 100.0 * (
                0.30 * viability_score
                + 0.25 * distance_score
                + 0.20 * capacity_ratio
                + 0.15 * refrigeration_score
                + 0.10 * compatibility_score
                + urgency_bonus
            )
            benefit_score = _clamp(benefit_score, 0.0, 100.0)

        rationale: List[str] = []
        if compatible:
            rationale.append("Center supports this cargo type")
        else:
            rationale.append("Center does not support this cargo type")

        if operational:
            rationale.append("Refrigeration is operational")
        else:
            rationale.append("Refrigeration is not operational")

        if available_capacity > 0:
            rationale.append(f"Available capacity: {available_capacity}/{capacity}")
        else:
            rationale.append("No available capacity")

        rationale.append(f"ETA to center: {round(eta_hours, 2)} hours")
        rationale.append(f"Distance to center: {round(distance_km, 2)} km")

        if eta_buffer_hours is not None:
            if can_arrive_before_failure:
                rationale.append(f"Arrival is ahead of failure window by {eta_buffer_hours} hours")
            else:
                rationale.append(f"ETA exceeds failure window by {abs(eta_buffer_hours)} hours")

        return {
            "id": dc["id"],
            "name": dc["name"],
            "location": dc["location"],
            "distance_km": round(distance_km, 2),
            "eta_hours": round(eta_hours, 2),
            "available_capacity": available_capacity,
            "capacity": capacity,
            "refrigeration_status": dc["refrigeration_status"],
            "supported_cargo_types": dc["supported_cargo_types"],
            "compatible_for_cargo": compatible,
            "can_arrive_before_failure": can_arrive_before_failure,
            "eta_buffer_hours": eta_buffer_hours,
            "benefit_score": round(float(benefit_score), 2),
            "rationale": rationale,
        }

    def recommend_reroute(
        self,
        telemetry: Dict[str, Any],
        prediction: Optional[Dict[str, Any]] = None,
        max_results: int = 3,
        exclude_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        lat = _safe_float(telemetry.get("gps_lat"), None)
        lon = _safe_float(telemetry.get("gps_lon"), None)

        if lat is None or lon is None:
            raise ValueError("telemetry must include gps_lat and gps_lon")

        current_location: Location = (lat, lon)
        cargo_type = str(telemetry.get("cargo_type") or "").strip().lower() or None
        risk_score = self._extract_risk_score(prediction)
        time_to_failure_hours = self._extract_time_to_failure_hours(prediction)

        nearest = self.find_nearest_centers(
            current_location=current_location,
            max_results=max(3, int(max_results) * 2),
            cargo_type=cargo_type,
            exclude_ids=exclude_ids,
            min_available_capacity=1,
            require_operational=True,
        )

        scored: List[Dict[str, Any]] = []
        for center in nearest:
            scored.append(
                self.calculate_reroute_benefit(
                    current_location=current_location,
                    alternative_dc=center,
                    risk_score=risk_score,
                    time_to_failure_hours=time_to_failure_hours,
                    cargo_type=cargo_type,
                    refrigeration_failed=bool(telemetry.get("refrigeration_failed", False)),
                    scenario=str(telemetry.get("scenario") or "").strip().lower(),
                    current_temp=_safe_float(telemetry.get("temperature"), 0.0),
                )
            )

        scored.sort(
            key=lambda x: (
                -x["benefit_score"],
                x["distance_km"],
                -x["available_capacity"],
            )
        )

        alternatives = scored[: max(1, int(max_results))]
        recommended_dc = alternatives[0] if alternatives else None

        return {
            "asset_id": telemetry.get("asset_id"),
            "cargo_type": cargo_type,
            "current_location": {
                "lat": round(current_location[0], 6),
                "lon": round(current_location[1], 6),
            },
            "risk_score": round(float(risk_score), 3),
            "time_to_failure_hours": time_to_failure_hours,
            "recommended_dc": recommended_dc,
            "alternatives": alternatives,
        }