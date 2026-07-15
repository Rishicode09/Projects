"""Feature engineering for degradation modelling.

The raw sensor snapshot at a single point in time is a weak signal — a hot
engine on one afternoon means little. Degradation shows up in *trends*, so
every sensor channel gets:

* a trailing rolling mean and standard deviation (``ROLLING_WINDOW_DAYS``), and
* a delta against the reading ``ROLLING_WINDOW_DAYS`` ago (trend direction).

All windows are strictly trailing (pandas ``rolling`` over past rows only),
so no feature at day *t* can see data after day *t*. ``tests/test_features.py``
asserts this property directly — leakage through rolling windows is the most
common silent failure in time-series ML.
"""

from __future__ import annotations

import pandas as pd

from fleetpulse.config import ROLLING_WINDOW_DAYS, SENSOR_COLUMNS, STATIC_COLUMNS

# Feature names are derived from config so the API and model card stay in sync.
_TREND_SUFFIXES = ("roll_mean", "roll_std", "delta")

FEATURE_COLUMNS: tuple[str, ...] = tuple(
    [*SENSOR_COLUMNS]
    + [f"{col}_{suffix}" for col in SENSOR_COLUMNS for suffix in _TREND_SUFFIXES]
    + [*STATIC_COLUMNS]
)


def build_features(telemetry: pd.DataFrame, window: int = ROLLING_WINDOW_DAYS) -> pd.DataFrame:
    """Return a feature frame aligned row-for-row with ``telemetry``.

    Rows that lack a full trailing window of history are dropped (they occur
    only in each vehicle's first ``window`` days), so the returned frame has
    no NaNs and every row is scoreable.

    The input must contain ``vehicle_id``, ``day``, all sensor columns and
    static columns; a label column is carried through if present.
    """
    frame = telemetry.sort_values(["vehicle_id", "day"]).reset_index(drop=True)
    grouped = frame.groupby("vehicle_id", sort=False)

    for col in SENSOR_COLUMNS:
        rolling = grouped[col].rolling(window=window, min_periods=window)
        frame[f"{col}_roll_mean"] = rolling.mean().reset_index(level=0, drop=True)
        frame[f"{col}_roll_std"] = rolling.std().reset_index(level=0, drop=True)
        frame[f"{col}_delta"] = grouped[col].transform(lambda s: s - s.shift(window))

    engineered = [c for c in frame.columns if c.endswith(_TREND_SUFFIXES)]
    return frame.dropna(subset=engineered).reset_index(drop=True)
