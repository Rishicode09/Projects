import numpy as np
import pandas as pd

from fleetpulse.config import SENSOR_COLUMNS
from fleetpulse.monitoring import drift_report, population_stability_index


def test_psi_near_zero_for_same_distribution():
    rng = np.random.default_rng(0)
    a = rng.normal(90, 5, 5000)
    b = rng.normal(90, 5, 5000)
    assert population_stability_index(a, b) < 0.02


def test_psi_large_for_shifted_distribution():
    rng = np.random.default_rng(0)
    a = rng.normal(90, 5, 5000)
    b = rng.normal(110, 5, 5000)
    assert population_stability_index(a, b) > 0.25


def test_drift_report_flags_shifted_sensor(telemetry: pd.DataFrame):
    reference = telemetry.copy()
    current = telemetry.copy()
    current["engine_temp_c"] += 15.0  # simulate a firmware calibration change

    report = drift_report(reference, current)
    assert set(report["feature"]) == set(SENSOR_COLUMNS)
    row = report.set_index("feature").loc["engine_temp_c"]
    assert row["severity"] == "significant_shift"
    stable = report.set_index("feature").drop("engine_temp_c")
    assert (stable["severity"] == "stable").all()
