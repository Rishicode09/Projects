"""Central configuration shared by the data, training, and serving layers.

Keeping column names and defaults in one module means the feature pipeline,
the API schemas, and the tests can never silently disagree about what a
telemetry record looks like.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Raw sensor channels emitted by the (simulated) telematics unit.
SENSOR_COLUMNS: tuple[str, ...] = (
    "engine_temp_c",
    "oil_pressure_kpa",
    "vibration_rms",
    "battery_voltage_v",
    "coolant_level_pct",
    "brake_pad_mm",
)

# Static per-vehicle attributes.
STATIC_COLUMNS: tuple[str, ...] = ("vehicle_type", "vehicle_age_years")

CATEGORICAL_COLUMNS: tuple[str, ...] = ("vehicle_type",)

LABEL_COLUMN = "failure_within_horizon"

VEHICLE_TYPES: tuple[str, ...] = ("city_car", "delivery_van", "hgv")

# Rolling window (days) used by the feature pipeline. The API requires at
# least this much history per vehicle before it can score a prediction.
ROLLING_WINDOW_DAYS = 7


@dataclass(frozen=True)
class GeneratorConfig:
    """Parameters for the synthetic telemetry generator."""

    n_vehicles: int = 60
    n_days: int = 365
    horizon_days: int = 30
    seed: int = 42


@dataclass(frozen=True)
class TrainingConfig:
    """Parameters for model training and selection."""

    test_fraction: float = 0.25
    seed: int = 42
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)


def default_artifact_dir() -> Path:
    """Directory where trained model artifacts are stored.

    Overridable via ``FLEETPULSE_MODEL_DIR`` so the Docker image and tests
    can point the API at a different artifact location.
    """
    return Path(os.environ.get("FLEETPULSE_MODEL_DIR", "artifacts"))
