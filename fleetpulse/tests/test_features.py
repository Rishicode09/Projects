import pandas as pd

from fleetpulse.config import ROLLING_WINDOW_DAYS
from fleetpulse.data import generate_fleet_telemetry
from fleetpulse.features import FEATURE_COLUMNS, build_features

from .conftest import SMALL_CONFIG


def test_output_has_all_feature_columns_and_no_nans(telemetry: pd.DataFrame):
    features = build_features(telemetry)
    missing = set(FEATURE_COLUMNS) - set(features.columns)
    assert not missing
    assert not features[list(FEATURE_COLUMNS)].isna().any().any()


def test_only_warmup_rows_dropped(telemetry: pd.DataFrame):
    features = build_features(telemetry)
    # The delta feature needs a reading from `window` days ago, so each
    # vehicle's first `window` rows are warm-up and get dropped.
    dropped_per_vehicle = ROLLING_WINDOW_DAYS
    expected = len(telemetry) - SMALL_CONFIG.n_vehicles * dropped_per_vehicle
    assert len(features) == expected
    assert features["day"].min() == dropped_per_vehicle


def test_no_lookahead_leakage():
    """Features at day t must be unaffected by changes to data after day t."""
    telemetry = generate_fleet_telemetry(SMALL_CONFIG)
    cutoff_day = 100

    baseline = build_features(telemetry)
    corrupted = telemetry.copy()
    corrupted.loc[corrupted["day"] > cutoff_day, "engine_temp_c"] = 999.0
    recomputed = build_features(corrupted)

    past_a = baseline[baseline["day"] <= cutoff_day].reset_index(drop=True)
    past_b = recomputed[recomputed["day"] <= cutoff_day].reset_index(drop=True)
    pd.testing.assert_frame_equal(past_a, past_b)


def test_rolling_windows_do_not_cross_vehicles(telemetry: pd.DataFrame):
    """Vehicle B's first window must not include vehicle A's last readings."""
    features = build_features(telemetry)
    one_vehicle = telemetry[telemetry["vehicle_id"] == "VH-0001"]
    alone = build_features(one_vehicle)
    together = features[features["vehicle_id"] == "VH-0001"].reset_index(drop=True)
    pd.testing.assert_frame_equal(alone, together)
