"""Training pipeline: candidate models, grouped splitting, and persistence.

Two design decisions here matter more than the choice of algorithm:

1. **Grouped train/test split.** Rows from one vehicle are highly
   autocorrelated — day 100 and day 101 are nearly identical. A random row
   split would put both sides of that pair in train and test and inflate
   every metric. ``GroupShuffleSplit`` on ``vehicle_id`` guarantees the
   model is evaluated on vehicles it has never seen.

2. **Model selection against a baseline.** A logistic regression and a
   gradient-boosted tree ensemble are trained side by side and the winner
   is chosen by held-out PR-AUC. Keeping the linear baseline in the run
   makes the value of the more complex model measurable rather than assumed.

The trained artifact is a directory containing the fitted pipeline and a
JSON *model card* (metrics, threshold, feature list, library versions) so
the API can report exactly what it is serving.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from fleetpulse import __version__
from fleetpulse.config import CATEGORICAL_COLUMNS, LABEL_COLUMN, TrainingConfig
from fleetpulse.features import FEATURE_COLUMNS, build_features
from fleetpulse.models.evaluate import compute_metrics, select_threshold

_MODEL_FILE = "model.joblib"
_CARD_FILE = "model_card.json"


@dataclass(frozen=True)
class TrainedModel:
    """A fitted pipeline plus the metadata needed to serve it responsibly."""

    pipeline: Pipeline
    card: dict

    @property
    def threshold(self) -> float:
        return float(self.card["threshold"])

    def predict_proba(self, features: pd.DataFrame) -> pd.Series:
        columns = list(FEATURE_COLUMNS)
        probs = self.pipeline.predict_proba(features[columns])[:, 1]
        return pd.Series(probs, index=features.index, name="failure_probability")

    def save(self, artifact_dir: Path) -> None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, artifact_dir / _MODEL_FILE)
        (artifact_dir / _CARD_FILE).write_text(json.dumps(self.card, indent=2))


def load_model(artifact_dir: Path) -> TrainedModel:
    pipeline = joblib.load(artifact_dir / _MODEL_FILE)
    card = json.loads((artifact_dir / _CARD_FILE).read_text())
    return TrainedModel(pipeline=pipeline, card=card)


def _candidate_pipelines(seed: int) -> dict[str, Pipeline]:
    numeric = [c for c in FEATURE_COLUMNS if c not in CATEGORICAL_COLUMNS]
    categorical = list(CATEGORICAL_COLUMNS)

    linear_prep = ColumnTransformer(
        [
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ]
    )
    # Trees are scale-invariant, so the boosted model only needs encoding.
    tree_prep = ColumnTransformer(
        [
            ("num", "passthrough", numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ]
    )
    return {
        "logistic_regression": Pipeline(
            [
                ("prep", linear_prep),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("prep", tree_prep),
                ("clf", HistGradientBoostingClassifier(random_state=seed)),
            ]
        ),
    }


def train_model(telemetry: pd.DataFrame, config: TrainingConfig | None = None) -> TrainedModel:
    """Train candidate models on telemetry and return the best one.

    ``telemetry`` is raw generator output; feature engineering happens here
    so training and any offline evaluation share one code path.
    """
    config = config or TrainingConfig()
    features = build_features(telemetry)

    splitter = GroupShuffleSplit(
        n_splits=1, test_size=config.test_fraction, random_state=config.seed
    )
    train_idx, test_idx = next(splitter.split(features, groups=features["vehicle_id"]))
    train, test = features.iloc[train_idx], features.iloc[test_idx]

    x_train, y_train = train[list(FEATURE_COLUMNS)], train[LABEL_COLUMN]
    x_test, y_test = test[list(FEATURE_COLUMNS)], test[LABEL_COLUMN]

    results: dict[str, dict] = {}
    fitted: dict[str, Pipeline] = {}
    for name, pipeline in _candidate_pipelines(config.seed).items():
        pipeline.fit(x_train, y_train)
        probs = pipeline.predict_proba(x_test)[:, 1]
        threshold = select_threshold(y_test.to_numpy(), probs)
        results[name] = compute_metrics(y_test.to_numpy(), probs, threshold)
        fitted[name] = pipeline

    best_name = max(results, key=lambda name: results[name]["pr_auc"])

    card = {
        "model_name": best_name,
        "fleetpulse_version": __version__,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "threshold": results[best_name]["threshold"],
        "metrics": results[best_name],
        "candidate_metrics": results,
        "feature_columns": list(FEATURE_COLUMNS),
        "training_rows": int(len(train)),
        "test_rows": int(len(test)),
        "test_vehicles": sorted(test["vehicle_id"].unique().tolist()),
    }
    return TrainedModel(pipeline=fitted[best_name], card=card)
