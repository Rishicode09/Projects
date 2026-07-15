import pandas as pd

from fleetpulse.features import FEATURE_COLUMNS, build_features
from fleetpulse.models.evaluate import compute_metrics, select_threshold
from fleetpulse.models.train import TrainedModel, load_model


def test_model_beats_random_ranking(trained_model: TrainedModel):
    metrics = trained_model.card["metrics"]
    # PR-AUC of a random ranker equals the positive rate; require a clear margin.
    assert metrics["pr_auc"] > 2 * metrics["positive_rate"]
    assert metrics["roc_auc"] > 0.7


def test_model_card_is_complete(trained_model: TrainedModel):
    card = trained_model.card
    for key in ("model_name", "threshold", "metrics", "feature_columns", "trained_at"):
        assert key in card
    assert card["feature_columns"] == list(FEATURE_COLUMNS)
    assert set(card["candidate_metrics"]) == {"logistic_regression", "hist_gradient_boosting"}


def test_test_split_never_overlaps_training_vehicles(trained_model: TrainedModel, telemetry):
    test_vehicles = set(trained_model.card["test_vehicles"])
    all_vehicles = set(telemetry["vehicle_id"].unique())
    assert test_vehicles and test_vehicles < all_vehicles


def test_persistence_round_trip(trained_model: TrainedModel, telemetry, tmp_path):
    trained_model.save(tmp_path)
    restored = load_model(tmp_path)
    features = build_features(telemetry).head(50)
    original = trained_model.predict_proba(features)
    reloaded = restored.predict_proba(features)
    pd.testing.assert_series_equal(original, reloaded)
    assert restored.card == trained_model.card


def test_compute_metrics_perfect_classifier():
    import numpy as np

    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9])
    metrics = compute_metrics(y_true, y_prob, threshold=0.5)
    assert metrics["pr_auc"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["f1"] == 1.0


def test_select_threshold_separates_classes():
    import numpy as np

    y_true = np.array([0] * 90 + [1] * 10)
    y_prob = np.concatenate([np.linspace(0.0, 0.3, 90), np.linspace(0.7, 1.0, 10)])
    threshold = select_threshold(y_true, y_prob)
    assert 0.3 < threshold <= 0.7
