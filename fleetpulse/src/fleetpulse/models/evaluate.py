"""Model evaluation utilities.

Failure labels are imbalanced (most fleet-days are healthy), so accuracy
is a misleading headline metric here. The primary selection metric is average
precision (PR-AUC), which reflects how well the model ranks the rare
positive class; ROC-AUC and the Brier score are reported alongside for
ranking quality and probability calibration respectively.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict[str, float]:
    """Compute ranking, thresholded, and calibration metrics."""
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "positive_rate": float(np.mean(y_true)),
        "threshold": float(threshold),
    }


def select_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Pick the operating threshold that maximises F1 on validation data.

    In production this would be a business decision balancing the cost of an
    unnecessary workshop visit against the cost of a roadside breakdown; F1
    is a reasonable neutral default and the choice is recorded in the model
    card so it can be revisited.
    """
    candidates = np.unique(np.round(y_prob, 3))
    if candidates.size == 0:
        return 0.5
    scores = [f1_score(y_true, y_prob >= t, zero_division=0) for t in candidates]
    return float(candidates[int(np.argmax(scores))])
