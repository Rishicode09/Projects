"""Unsupervised anomaly detection over raw sensor snapshots.

The supervised failure model answers "is this vehicle degrading towards a
known failure mode?". The anomaly detector answers a complementary
question: "does this reading look like anything we saw during training?"
It catches faulty sensors and novel failure modes that the classifier was
never taught, which is why real condition-monitoring systems run both.

An ``IsolationForest`` is fitted on *healthy* training rows only, so its
notion of "normal" is not contaminated by pre-failure telemetry.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from fleetpulse.config import LABEL_COLUMN, SENSOR_COLUMNS

_ANOMALY_FILE = "anomaly.joblib"


class AnomalyDetector:
    """Thin wrapper that fixes the feature contract around IsolationForest."""

    def __init__(self, contamination: float = 0.02, seed: int = 42) -> None:
        self._forest = IsolationForest(
            n_estimators=200, contamination=contamination, random_state=seed
        )

    def fit(self, telemetry: pd.DataFrame) -> AnomalyDetector:
        healthy = telemetry
        if LABEL_COLUMN in telemetry.columns:
            healthy = telemetry[telemetry[LABEL_COLUMN] == 0]
        self._forest.fit(healthy[list(SENSOR_COLUMNS)])
        return self

    def score(self, readings: pd.DataFrame) -> pd.DataFrame:
        """Return per-row anomaly scores; higher means more anomalous."""
        x = readings[list(SENSOR_COLUMNS)]
        # decision_function is positive for inliers; negate so "bigger = worse".
        scores = -self._forest.decision_function(x)
        flags = self._forest.predict(x) == -1
        return pd.DataFrame({"anomaly_score": scores, "is_anomaly": flags}, index=readings.index)

    def save(self, artifact_dir: Path) -> None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._forest, artifact_dir / _ANOMALY_FILE)

    @classmethod
    def load(cls, artifact_dir: Path) -> AnomalyDetector:
        detector = cls()
        detector._forest = joblib.load(artifact_dir / _ANOMALY_FILE)
        return detector
