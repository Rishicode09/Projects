import numpy as np
import pandas as pd

from fleetpulse.config import LABEL_COLUMN, SENSOR_COLUMNS, GeneratorConfig
from fleetpulse.data import generate_fleet_telemetry

from .conftest import SMALL_CONFIG


def test_shape_and_columns(telemetry: pd.DataFrame):
    assert len(telemetry) == SMALL_CONFIG.n_vehicles * SMALL_CONFIG.n_days
    for col in ("vehicle_id", "day", LABEL_COLUMN, *SENSOR_COLUMNS):
        assert col in telemetry.columns


def test_deterministic_for_seed():
    a = generate_fleet_telemetry(GeneratorConfig(n_vehicles=4, n_days=60, seed=123))
    b = generate_fleet_telemetry(GeneratorConfig(n_vehicles=4, n_days=60, seed=123))
    pd.testing.assert_frame_equal(a, b)


def test_different_seeds_differ():
    a = generate_fleet_telemetry(GeneratorConfig(n_vehicles=4, n_days=60, seed=1))
    b = generate_fleet_telemetry(GeneratorConfig(n_vehicles=4, n_days=60, seed=2))
    assert not a[list(SENSOR_COLUMNS)].equals(b[list(SENSOR_COLUMNS)])


def test_both_classes_present(telemetry: pd.DataFrame):
    rate = telemetry[LABEL_COLUMN].mean()
    assert 0.0 < rate < 0.5, "failure labels should be present but a minority class"


def test_sensor_values_physically_plausible(telemetry: pd.DataFrame):
    assert telemetry["engine_temp_c"].between(60, 150).all()
    assert telemetry["oil_pressure_kpa"].between(0, 600).all()
    assert telemetry["coolant_level_pct"].between(0, 100).all()
    assert telemetry["brake_pad_mm"].between(0, 15).all()
    assert (np.diff(telemetry.groupby("vehicle_id")["mileage_km"].last()) != 0).any()


def test_mileage_monotonic_per_vehicle(telemetry: pd.DataFrame):
    for _, group in telemetry.groupby("vehicle_id"):
        assert group.sort_values("day")["mileage_km"].is_monotonic_increasing
