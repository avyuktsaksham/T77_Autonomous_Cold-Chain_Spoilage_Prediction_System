from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
import random
import math
import time


@dataclass(frozen=True)
class CargoProfile:
    name: str
    temp_min_c: float
    temp_max_c: float
    humidity_min_pct: float
    humidity_max_pct: float
    max_door_open_per_hour: int
    vibration_warn_g: float
    vibration_critical_g: float
    allowed_out_of_range_minutes_per_hour: float
    hard_temp_low_c: float
    hard_temp_high_c: float
    freeze_sensitive: bool = False
    freeze_temp_c: float = 0.0


CARGO_PROFILES: Dict[str, CargoProfile] = {
    "vaccines": CargoProfile(
        name="vaccines",
        temp_min_c=2.0, temp_max_c=8.0,
        humidity_min_pct=30.0, humidity_max_pct=60.0,
        max_door_open_per_hour=3,
        vibration_warn_g=2.5, vibration_critical_g=5.0,
        allowed_out_of_range_minutes_per_hour=10.0,
        hard_temp_low_c=0.0, hard_temp_high_c=12.0,
        freeze_sensitive=True, freeze_temp_c=0.0
    ),
    "meat": CargoProfile(
        name="meat",
        temp_min_c=-1.0, temp_max_c=4.0,
        humidity_min_pct=85.0, humidity_max_pct=95.0,
        max_door_open_per_hour=2,
        vibration_warn_g=3.0, vibration_critical_g=6.0,
        allowed_out_of_range_minutes_per_hour=12.0,
        hard_temp_low_c=-5.0, hard_temp_high_c=8.0,
    ),
    "dairy": CargoProfile(
        name="dairy",
        temp_min_c=1.0, temp_max_c=7.0,
        humidity_min_pct=70.0, humidity_max_pct=85.0,
        max_door_open_per_hour=3,
        vibration_warn_g=3.0, vibration_critical_g=6.5,
        allowed_out_of_range_minutes_per_hour=12.0,
        hard_temp_low_c=-1.0, hard_temp_high_c=12.0,
    ),
    "pharmaceuticals": CargoProfile(
        name="pharmaceuticals",
        temp_min_c=15.0, temp_max_c=25.0,
        humidity_min_pct=40.0, humidity_max_pct=60.0,
        max_door_open_per_hour=4,
        vibration_warn_g=2.0, vibration_critical_g=4.5,
        allowed_out_of_range_minutes_per_hour=15.0,
        hard_temp_low_c=10.0, hard_temp_high_c=35.0,
    ),
    "frozen_food": CargoProfile(
        name="frozen_food",
        temp_min_c=-25.0, temp_max_c=-15.0,
        humidity_min_pct=60.0, humidity_max_pct=95.0,
        max_door_open_per_hour=2,
        vibration_warn_g=3.5, vibration_critical_g=7.0,
        allowed_out_of_range_minutes_per_hour=8.0,
        hard_temp_low_c=-35.0, hard_temp_high_c=-5.0,
    ),
    "produce": CargoProfile(
        name="produce",
        temp_min_c=2.0, temp_max_c=10.0,
        humidity_min_pct=80.0, humidity_max_pct=95.0,
        max_door_open_per_hour=4,
        vibration_warn_g=3.0, vibration_critical_g=6.0,
        allowed_out_of_range_minutes_per_hour=15.0,
        hard_temp_low_c=0.0, hard_temp_high_c=18.0,
    ),
    "seafood": CargoProfile(
        name="seafood",
        temp_min_c=-2.0, temp_max_c=2.0,
        humidity_min_pct=85.0, humidity_max_pct=95.0,
        max_door_open_per_hour=2,
        vibration_warn_g=3.0, vibration_critical_g=6.0,
        allowed_out_of_range_minutes_per_hour=10.0,
        hard_temp_low_c=-6.0, hard_temp_high_c=6.0,
    ),
    "ice_cream": CargoProfile(
        name="ice_cream",
        temp_min_c=-30.0, temp_max_c=-18.0,
        humidity_min_pct=50.0, humidity_max_pct=90.0,
        max_door_open_per_hour=2,
        vibration_warn_g=3.5, vibration_critical_g=7.0,
        allowed_out_of_range_minutes_per_hour=6.0,
        hard_temp_low_c=-40.0, hard_temp_high_c=-10.0,
    ),
    "blood_plasma": CargoProfile(
        name="blood_plasma",
        temp_min_c=2.0, temp_max_c=6.0,
        humidity_min_pct=30.0, humidity_max_pct=60.0,
        max_door_open_per_hour=2,
        vibration_warn_g=2.0, vibration_critical_g=4.0,
        allowed_out_of_range_minutes_per_hour=8.0,
        hard_temp_low_c=0.0, hard_temp_high_c=10.0,
        freeze_sensitive=True, freeze_temp_c=0.0
    ),
    "flowers": CargoProfile(
        name="flowers",
        temp_min_c=2.0, temp_max_c=8.0,
        humidity_min_pct=85.0, humidity_max_pct=95.0,
        max_door_open_per_hour=4,
        vibration_warn_g=3.0, vibration_critical_g=6.0,
        allowed_out_of_range_minutes_per_hour=15.0,
        hard_temp_low_c=0.0, hard_temp_high_c=14.0,
    ),
}


@dataclass(frozen=True)
class ShipmentScenario:
    name: str
    micro_excursion_rate_per_min: float = 0.01
    micro_excursion_duration_min: Tuple[int, int] = (2, 8)
    micro_excursion_temp_delta_c: Tuple[float, float] = (1.5, 5.0)
    door_event_rate_per_min: float = 0.005
    vibration_spike_rate_per_min: float = 0.02
    refrigeration_failure_at_min: Optional[int] = None
    refrigeration_temp_rise_c_per_min: float = 0.10
    speed_kmph: float = 45.0

    @staticmethod
    def normal() -> "ShipmentScenario":
        return ShipmentScenario(
            name="normal",
            micro_excursion_rate_per_min=0.003,
            door_event_rate_per_min=0.003,
            vibration_spike_rate_per_min=0.01,
            refrigeration_failure_at_min=None,
            refrigeration_temp_rise_c_per_min=0.10,
            speed_kmph=45.0
        )

    @staticmethod
    def micro_excursions() -> "ShipmentScenario":
        return ShipmentScenario(
            name="micro_excursions",
            micro_excursion_rate_per_min=0.02,
            door_event_rate_per_min=0.006,
            vibration_spike_rate_per_min=0.02,
            refrigeration_failure_at_min=None,
            refrigeration_temp_rise_c_per_min=0.10,
            speed_kmph=45.0
        )

    @staticmethod
    def refrigeration_failure(fail_at_min: int = 45) -> "ShipmentScenario":
        return ShipmentScenario(
            name="refrigeration_failure",
            micro_excursion_rate_per_min=0.01,
            door_event_rate_per_min=0.006,
            vibration_spike_rate_per_min=0.02,
            refrigeration_failure_at_min=fail_at_min,
            refrigeration_temp_rise_c_per_min=0.18,
            speed_kmph=40.0
        )


@dataclass(frozen=True)
class Route:
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    waypoints: Optional[List[Tuple[float, float]]] = None

    def path_points(self) -> List[Tuple[float, float]]:
        pts = [self.origin]
        if self.waypoints:
            pts.extend(self.waypoints)
        pts.append(self.destination)
        return pts


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


class RouteFollower:
    def __init__(self, route: Route):
        self.points = route.path_points()
        self.seg = 0
        self.t = 0.0

    def step(self, distance_km: float) -> Tuple[float, float]:
        while distance_km > 0 and self.seg < len(self.points) - 1:
            (lat1, lon1) = self.points[self.seg]
            (lat2, lon2) = self.points[self.seg + 1]
            seg_len = max(0.001, _haversine_km(lat1, lon1, lat2, lon2))
            remaining = seg_len * (1.0 - self.t)
            if distance_km >= remaining:
                self.seg += 1
                self.t = 0.0
                distance_km -= remaining
            else:
                self.t += distance_km / seg_len
                distance_km = 0.0

        if self.seg >= len(self.points) - 1:
            return self.points[-1]

        (lat1, lon1) = self.points[self.seg]
        (lat2, lon2) = self.points[self.seg + 1]
        return (_lerp(lat1, lat2, self.t), _lerp(lon1, lon2, self.t))

    def arrived(self) -> bool:
        return self.seg >= len(self.points) - 1


@dataclass
class ExposureState:
    total_minutes: float = 0.0
    temp_degree_minutes: float = 0.0
    humidity_percent_minutes: float = 0.0
    door_open_minutes: float = 0.0
    vibration_warn_minutes: float = 0.0
    vibration_critical_minutes: float = 0.0
    out_of_range_minutes_in_hour: float = 0.0
    hour_elapsed: float = 0.0


def _band_excess(value: float, low: float, high: float) -> float:
    if value < low:
        return low - value
    if value > high:
        return value - high
    return 0.0


def _risk_proxy(profile: CargoProfile, exp: ExposureState, current_temp: float) -> float:
    temp_score = 1.0 - math.exp(-exp.temp_degree_minutes / 120.0)
    hum_score = 1.0 - math.exp(-exp.humidity_percent_minutes / 600.0)
    door_score = 1.0 - math.exp(-exp.door_open_minutes / 20.0)
    vib_score = 1.0 - math.exp(-(exp.vibration_warn_minutes + 2.0 * exp.vibration_critical_minutes) / 30.0)

    base = 0.55 * temp_score + 0.15 * hum_score + 0.15 * door_score + 0.15 * vib_score

    penalty = 0.0
    if current_temp < profile.hard_temp_low_c:
        penalty += min(0.25, (profile.hard_temp_low_c - current_temp) / 10.0)
    if current_temp > profile.hard_temp_high_c:
        penalty += min(0.25, (current_temp - profile.hard_temp_high_c) / 10.0)
    if profile.freeze_sensitive and current_temp <= profile.freeze_temp_c:
        penalty += 0.30
    if exp.out_of_range_minutes_in_hour > profile.allowed_out_of_range_minutes_per_hour:
        over = exp.out_of_range_minutes_in_hour - profile.allowed_out_of_range_minutes_per_hour
        penalty += min(0.20, over / 60.0)

    r = base + penalty
    return max(0.0, min(1.0, r))


class ColdChainSensorSimulator:
    def __init__(
        self,
        asset_id: str,
        cargo_type: str = "vaccines",
        scenario: Optional[ShipmentScenario] = None,
        route: Optional[Route] = None,
        publish_interval_sec: int = 5,
        seed: Optional[int] = None,
    ):
        self.asset_id = asset_id
        self.cargo_type = cargo_type.strip().lower()
        if self.cargo_type not in CARGO_PROFILES:
            raise ValueError(f"Unknown cargo_type '{cargo_type}'. Supported: {list(CARGO_PROFILES.keys())}")

        self.profile = CARGO_PROFILES[self.cargo_type]
        self.scenario = scenario or ShipmentScenario.normal()
        self.publish_interval_sec = int(publish_interval_sec)

        if seed is not None:
            random.seed(seed)

        if route is None:
            route = Route(
                origin=(27.1767, 78.0081),
                destination=(28.7041, 77.1025),
                waypoints=[(27.4924, 77.6737)]
            )
        self.route_follower = RouteFollower(route)

        self.current_temp = (self.profile.temp_min_c + self.profile.temp_max_c) / 2.0
        self.current_humidity = (self.profile.humidity_min_pct + self.profile.humidity_max_pct) / 2.0
        self.door_open = False

        self.excursion_remaining_min = 0.0
        self.excursion_delta_c = 0.0

        self.refrigeration_failed = False
        self.elapsed_min = 0.0

        self.door_events_in_hour = 0
        self.door_hour_elapsed = 0.0

        self.exposure = ExposureState()
        self.base_vibration_g = 1.2

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _reset_hour_windows_if_needed(self, dt_min: float):
        self.exposure.hour_elapsed += dt_min
        if self.exposure.hour_elapsed >= 60.0:
            self.exposure.hour_elapsed = 0.0
            self.exposure.out_of_range_minutes_in_hour = 0.0

        self.door_hour_elapsed += dt_min
        if self.door_hour_elapsed >= 60.0:
            self.door_hour_elapsed = 0.0
            self.door_events_in_hour = 0

    def _maybe_toggle_door(self):
        if (not self.door_open) and (self.door_events_in_hour >= self.profile.max_door_open_per_hour):
            return
        if random.random() < self.scenario.door_event_rate_per_min:
            new_state = not self.door_open
            if (not self.door_open) and new_state:
                self.door_events_in_hour += 1
            self.door_open = new_state

    def _maybe_start_excursion(self):
        if self.excursion_remaining_min > 0:
            return
        if random.random() < self.scenario.micro_excursion_rate_per_min:
            dur = random.randint(*self.scenario.micro_excursion_duration_min)
            self.excursion_remaining_min = float(dur)
            self.excursion_delta_c = random.uniform(*self.scenario.micro_excursion_temp_delta_c)

    def _maybe_fail_refrigeration(self):
        if self.scenario.refrigeration_failure_at_min is None:
            return
        if (not self.refrigeration_failed) and (self.elapsed_min >= self.scenario.refrigeration_failure_at_min):
            self.refrigeration_failed = True

    def _temperature_step(self, dt_min: float):
        setpoint = (self.profile.temp_min_c + self.profile.temp_max_c) / 2.0
        k = 0.12
        noise = random.gauss(0.0, 0.12)
        self.current_temp += (setpoint - self.current_temp) * k * dt_min + noise

        if self.door_open:
            self.current_temp += random.uniform(0.03, 0.10) * dt_min

        self._maybe_start_excursion()
        if self.excursion_remaining_min > 0:
            self.current_temp += (self.excursion_delta_c / max(1.0, self.excursion_remaining_min)) * dt_min
            self.excursion_remaining_min = max(0.0, self.excursion_remaining_min - dt_min)

        self._maybe_fail_refrigeration()
        if self.refrigeration_failed:
            self.current_temp += self.scenario.refrigeration_temp_rise_c_per_min * dt_min

    def _humidity_step(self, dt_min: float):
        target = (self.profile.humidity_min_pct + self.profile.humidity_max_pct) / 2.0
        k = 0.08
        noise = random.gauss(0.0, 0.8)
        self.current_humidity += (target - self.current_humidity) * k * dt_min + noise

        if self.door_open:
            ambient = 55.0
            self.current_humidity += (ambient - self.current_humidity) * 0.05 * dt_min

        self.current_humidity = max(5.0, min(99.0, self.current_humidity))

    def _vibration_reading(self) -> float:
        vib = max(0.0, random.gauss(self.base_vibration_g, 0.35))
        if random.random() < self.scenario.vibration_spike_rate_per_min:
            vib += random.uniform(2.0, 6.0)
        if self.door_open and random.random() < 0.15:
            vib += random.uniform(0.5, 2.0)
        return float(min(10.0, vib))

    def _gps_step(self, dt_min: float) -> Tuple[float, float]:
        distance_km = (self.scenario.speed_kmph * dt_min) / 60.0
        lat, lon = self.route_follower.step(distance_km)
        return (float(round(lat, 6)), float(round(lon, 6)))

    def _update_exposure(self, dt_min: float, vibration_g: float):
        exp = self.exposure
        exp.total_minutes += dt_min

        t_ex = _band_excess(self.current_temp, self.profile.temp_min_c, self.profile.temp_max_c)
        h_ex = _band_excess(self.current_humidity, self.profile.humidity_min_pct, self.profile.humidity_max_pct)

        if t_ex > 0:
            exp.temp_degree_minutes += t_ex * dt_min
            exp.out_of_range_minutes_in_hour += dt_min

        if h_ex > 0:
            exp.humidity_percent_minutes += h_ex * dt_min
            exp.out_of_range_minutes_in_hour += dt_min * 0.25

        if self.door_open:
            exp.door_open_minutes += dt_min
            exp.out_of_range_minutes_in_hour += dt_min * 0.2

        if vibration_g >= self.profile.vibration_warn_g:
            exp.vibration_warn_minutes += dt_min
        if vibration_g >= self.profile.vibration_critical_g:
            exp.vibration_critical_minutes += dt_min

    def get_telemetry(self) -> Dict[str, Any]:
        dt_min = self.publish_interval_sec / 60.0
        self.elapsed_min += dt_min

        self._reset_hour_windows_if_needed(dt_min)
        self._maybe_toggle_door()

        self._temperature_step(dt_min)
        self._humidity_step(dt_min)

        vibration_g = self._vibration_reading()
        gps_lat, gps_lon = self._gps_step(dt_min)

        self._update_exposure(dt_min, vibration_g)
        r = _risk_proxy(self.profile, self.exposure, self.current_temp)

        return {
            "asset_id": self.asset_id,
            "timestamp": self._now_iso(),
            "cargo_type": self.cargo_type,
            "temperature": round(self.current_temp, 2),
            "humidity": round(self.current_humidity, 2),
            "vibration": round(vibration_g, 2),
            "door_open": bool(self.door_open),
            "gps_lat": gps_lat,
            "gps_lon": gps_lon,
            "scenario": self.scenario.name,
            "refrigeration_failed": bool(self.refrigeration_failed),
            "cumulative_exposure": {
                "total_minutes": round(self.exposure.total_minutes, 2),
                "temp_degree_minutes": round(self.exposure.temp_degree_minutes, 2),
                "humidity_percent_minutes": round(self.exposure.humidity_percent_minutes, 2),
                "door_open_minutes": round(self.exposure.door_open_minutes, 2),
                "vibration_warn_minutes": round(self.exposure.vibration_warn_minutes, 2),
                "vibration_critical_minutes": round(self.exposure.vibration_critical_minutes, 2),
                "out_of_range_minutes_in_hour": round(self.exposure.out_of_range_minutes_in_hour, 2),
            },
            "risk_proxy": round(float(r), 3),
        }


@dataclass(frozen=True)
class TruckConfig:
    asset_id: str
    cargo_type: str
    scenario: ShipmentScenario
    route: Route
    seed: Optional[int] = None


class FleetSimulator:
    def __init__(self, trucks: List[TruckConfig], publish_interval_sec: int = 5):
        self.publish_interval_sec = int(publish_interval_sec)
        self.simulators: List[ColdChainSensorSimulator] = []
        for cfg in trucks:
            self.simulators.append(
                ColdChainSensorSimulator(
                    asset_id=cfg.asset_id,
                    cargo_type=cfg.cargo_type,
                    scenario=cfg.scenario,
                    route=cfg.route,
                    publish_interval_sec=self.publish_interval_sec,
                    seed=cfg.seed,
                )
            )

    def tick_all(self) -> List[Dict[str, Any]]:
        return [sim.get_telemetry() for sim in self.simulators]

    def sleep_interval(self):
        time.sleep(self.publish_interval_sec)


def create_default_fleet(publish_interval_sec: int = 2, fleet_size: int = 50) -> FleetSimulator:
    route_agra_delhi = Route(
        origin=(27.1767, 78.0081), destination=(28.7041, 77.1025), waypoints=[(27.4924, 77.6737)]
    )
    route_mathura_noida = Route(
        origin=(27.4924, 77.6737), destination=(28.5355, 77.3910), waypoints=None
    )
    route_agra_kanpur = Route(
        origin=(27.1767, 78.0081), destination=(26.4499, 80.3319), waypoints=[(27.8974, 78.0880)]
    )
    route_delhi_gurgaon = Route(
        origin=(28.7041, 77.1025), destination=(28.4595, 77.0266), waypoints=None
    )

    routes = [route_agra_delhi, route_mathura_noida, route_agra_kanpur, route_delhi_gurgaon]
    cargo_types = list(CARGO_PROFILES.keys())

    trucks: List[TruckConfig] = []
    for i in range(int(fleet_size)):
        asset_id = f"TRUCK_{i+1:03d}"
        cargo_type = cargo_types[i % len(cargo_types)]
        route = routes[i % len(routes)]

        if i % 10 == 4:
            scenario = ShipmentScenario.refrigeration_failure(fail_at_min=25)
        elif i % 3 == 0:
            scenario = ShipmentScenario.micro_excursions()
        else:
            scenario = ShipmentScenario.normal()

        trucks.append(
            TruckConfig(
                asset_id=asset_id,
                cargo_type=cargo_type,
                scenario=scenario,
                route=route,
                seed=i + 1,
            )
        )

    return FleetSimulator(trucks=trucks, publish_interval_sec=int(publish_interval_sec))

if __name__ == "__main__":
    print("Supported cargo types:", ", ".join(CARGO_PROFILES.keys()))
    fleet = create_default_fleet(publish_interval_sec=2, fleet_size=50)

    try:
        while True:
            messages = fleet.tick_all()
            for t in messages:
                print(
                    f"[{t['timestamp']}] {t['asset_id']} {t['cargo_type']} | "
                    f"T={t['temperature']}C H={t['humidity']}% Vib={t['vibration']}g "
                    f"Door={'OPEN' if t['door_open'] else 'CLOSED'} Risk={t['risk_proxy']} "
                    f"Scenario={t['scenario']} Fail={t['refrigeration_failed']}"
                )
            print("-" * 120)
            fleet.sleep_interval()
    except KeyboardInterrupt:
        print("\nStopped fleet simulation.")