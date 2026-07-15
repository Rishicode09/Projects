"""Physics-informed synthetic telemetry for a vehicle fleet.

Real fleet telemetry is proprietary, so this module simulates it in a way
that preserves the properties that make predictive maintenance hard:

* Each vehicle carries a hidden, monotonically increasing *wear* state.
* Sensor channels are noisy functions of wear (temperature rises, oil
  pressure falls, vibration grows super-linearly as bearings degrade).
* When wear crosses 1.0 the vehicle "fails" and is repaired imperfectly
  (wear resets to a small random value, not zero).
* The supervised label is whether a failure occurs within the next
  ``horizon_days`` — the quantity a maintenance planner actually needs.

Because labels are derived from the *future* of the wear trajectory, a
model can only score well by reading degradation signatures out of the
sensor history, exactly as it would on real data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fleetpulse.config import VEHICLE_TYPES, GeneratorConfig

# Per-type daily wear rate (mean of the gamma-distributed daily increment)
# and typical daily mileage. HGVs work harder and degrade faster.
_TYPE_PROFILES: dict[str, tuple[float, float]] = {
    "city_car": (0.006, 45.0),
    "delivery_van": (0.010, 140.0),
    "hgv": (0.014, 420.0),
}

_FAILURE_THRESHOLD = 1.0


def _simulate_wear(rng: np.random.Generator, rate: float, n_days: int) -> np.ndarray:
    """Simulate a wear trajectory with imperfect repairs after each failure."""
    wear = np.empty(n_days)
    level = rng.uniform(0.0, 0.3)
    for day in range(n_days):
        level += rng.gamma(shape=2.0, scale=rate / 2.0)
        wear[day] = level
        if level >= _FAILURE_THRESHOLD:
            level = rng.uniform(0.05, 0.15)  # repaired, but not to new condition
    return wear


def _sensor_readings(rng: np.random.Generator, wear: np.ndarray) -> dict[str, np.ndarray]:
    """Map the hidden wear state to noisy sensor channels."""
    n = wear.shape[0]
    return {
        "engine_temp_c": 88.0 + 14.0 * wear + rng.normal(0.0, 1.6, n),
        "oil_pressure_kpa": 320.0 - 90.0 * wear + rng.normal(0.0, 7.0, n),
        "vibration_rms": 0.5 + 2.2 * wear**1.5 + rng.normal(0.0, 0.12, n),
        "battery_voltage_v": 12.7 - 0.5 * wear + rng.normal(0.0, 0.06, n),
        "coolant_level_pct": np.clip(98.0 - 25.0 * wear + rng.normal(0.0, 1.2, n), 0.0, 100.0),
        "brake_pad_mm": np.clip(12.0 - 9.0 * wear + rng.normal(0.0, 0.25, n), 0.5, 14.0),
    }


def _label_failures(wear: np.ndarray, horizon_days: int) -> np.ndarray:
    """1 if a failure (wear crossing the threshold) occurs within the horizon."""
    failure_days = np.flatnonzero(wear >= _FAILURE_THRESHOLD)
    labels = np.zeros(wear.shape[0], dtype=np.int8)
    for day in range(wear.shape[0]):
        upcoming = failure_days[(failure_days > day) & (failure_days <= day + horizon_days)]
        labels[day] = 1 if upcoming.size else 0
    return labels


def generate_fleet_telemetry(config: GeneratorConfig | None = None) -> pd.DataFrame:
    """Generate one row per vehicle per day of labelled telemetry.

    The output is deterministic for a given ``config.seed``, which the test
    suite relies on for reproducibility.
    """
    config = config or GeneratorConfig()
    rng = np.random.default_rng(config.seed)
    frames: list[pd.DataFrame] = []

    for vehicle_idx in range(config.n_vehicles):
        vehicle_type = VEHICLE_TYPES[vehicle_idx % len(VEHICLE_TYPES)]
        wear_rate, daily_km = _TYPE_PROFILES[vehicle_type]
        age_years = float(rng.uniform(0.5, 9.0))
        # Older vehicles degrade slightly faster.
        wear = _simulate_wear(rng, wear_rate * (1.0 + 0.05 * age_years), config.n_days)

        frame = pd.DataFrame(_sensor_readings(rng, wear))
        frame.insert(0, "vehicle_id", f"VH-{vehicle_idx:04d}")
        frame.insert(1, "day", np.arange(config.n_days))
        frame["vehicle_type"] = vehicle_type
        frame["vehicle_age_years"] = round(age_years, 1)
        frame["mileage_km"] = np.cumsum(rng.normal(daily_km, daily_km * 0.15, config.n_days))
        frame["failure_within_horizon"] = _label_failures(wear, config.horizon_days)
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)
