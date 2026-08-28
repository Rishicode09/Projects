"""Evaluation metrics for binary functional/cracked classification.

Accuracy is a poor summary on ELPV: at the default threshold roughly 69% of
cells are functional, so predicting "functional" for everything scores 69% and
finds nothing. The metrics below are chosen to be hard to fool that way, and to
expose the precision/recall trade-off explicitly — because where you sit on that
curve is an operational decision (a missed severe cell costs energy; a false
alarm costs a technician's morning), not something to bury in an argmax.
"""

from __future__ import annotations

import numpy as np
import torch
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    roc_auc_score,
)

from .data.elpv import CLASS_NAMES
from .models.classifier import DEFAULT_THRESHOLD


@torch.no_grad()
def collect_predictions(model, loader, device: torch.device) -> dict[str, np.ndarray]:
    """Run the model over a loader and return raw arrays for metric computation."""
    model.eval()
    logits_all, labels_all, modules_all, probabilities_all = [], [], [], []

    for batch in loader:
        images = batch["image"].to(device, non_blocking=True)
        logits = model(images)
        logits_all.append(logits.detach().float().cpu())
        labels_all.append(batch["label"])
        modules_all.append(batch["module_id"])
        probabilities_all.append(batch["probability"])

    logits = torch.cat(logits_all)
    return {
        "logits": logits.numpy(),
        "probability": torch.sigmoid(logits).numpy(),
        "labels": torch.cat(labels_all).numpy().astype(int),
        "modules": torch.cat(modules_all).numpy(),
        "graded_severity": torch.cat(probabilities_all).numpy(),
    }


def compute_metrics(
    predictions: dict[str, np.ndarray], threshold: float = DEFAULT_THRESHOLD
) -> dict[str, float]:
    """Threshold-dependent and threshold-free metrics.

    ``roc_auc`` and ``average_precision`` are the ones to compare models on:
    they integrate over all thresholds, so they do not reward a model that
    happens to suit the arbitrary 0.5 cut. ``mcc`` is the best single-number
    summary at a fixed threshold on imbalanced data — unlike F1 it accounts for
    true negatives, so it cannot be inflated by predicting the majority class.
    """
    labels = predictions["labels"]
    probability = predictions["probability"]
    predicted = (probability >= threshold).astype(int)

    metrics: dict[str, float] = {
        "accuracy": float((predicted == labels).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
        "f1": float(f1_score(labels, predicted, zero_division=0)),
        "mcc": float(matthews_corrcoef(labels, predicted)) if len(set(labels)) > 1 else 0.0,
    }

    true_positive = int(((predicted == 1) & (labels == 1)).sum())
    metrics["recall"] = float(true_positive / max(int((labels == 1).sum()), 1))
    metrics["precision"] = float(true_positive / max(int((predicted == 1).sum()), 1))
    # False-alarm rate: the number a plant operator budgets against.
    false_positive = int(((predicted == 1) & (labels == 0)).sum())
    metrics["false_positive_rate"] = float(false_positive / max(int((labels == 0).sum()), 1))

    if len(set(labels)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(labels, probability))
        metrics["average_precision"] = float(average_precision_score(labels, probability))

    return metrics


def best_threshold(
    predictions: dict[str, np.ndarray], target_recall: float = 0.90
) -> dict[str, float]:
    """Lowest-false-alarm threshold that still reaches ``target_recall``.

    Reporting a single 0.5-threshold number hides the actual deployment choice.
    A plant that must catch 90% of cracked cells needs to know what that costs
    in false alarms, and this returns exactly that operating point.
    """
    labels = predictions["labels"]
    probability = predictions["probability"]
    if len(set(labels)) < 2:
        return {"threshold": DEFAULT_THRESHOLD, "recall": 0.0, "precision": 0.0}

    precision, recall, thresholds = precision_recall_curve(labels, probability)
    # precision_recall_curve returns one more point than thresholds.
    precision, recall = precision[:-1], recall[:-1]

    feasible = recall >= target_recall
    if not feasible.any():
        best = int(np.argmax(recall))
    else:
        # Among thresholds meeting the recall target, take the most precise.
        candidates = np.flatnonzero(feasible)
        best = int(candidates[np.argmax(precision[candidates])])

    return {
        "threshold": float(thresholds[best]),
        "recall": float(recall[best]),
        "precision": float(precision[best]),
    }


def confusion(
    predictions: dict[str, np.ndarray], threshold: float = DEFAULT_THRESHOLD
) -> np.ndarray:
    predicted = (predictions["probability"] >= threshold).astype(int)
    return confusion_matrix(predictions["labels"], predicted, labels=[0, 1])


def format_report(
    predictions: dict[str, np.ndarray], threshold: float = DEFAULT_THRESHOLD
) -> str:
    """Human-readable metric block, confusion matrix and operating point."""
    metrics = compute_metrics(predictions, threshold)
    matrix = confusion(predictions, threshold)

    lines = [f"Metrics (threshold = {threshold:.2f})", "-" * 34]
    lines += [f"  {name:<22s} {value:.4f}" for name, value in metrics.items()]

    lines += ["", "Confusion matrix (rows = true, cols = predicted)", "-" * 48]
    lines.append(" " * 14 + "".join(f"{name:>13s}" for name in CLASS_NAMES))
    for index, row in enumerate(matrix):
        lines.append(f"{CLASS_NAMES[index]:>12s}  " + "".join(f"{int(v):>13d}" for v in row))

    operating_point = best_threshold(predictions, target_recall=0.90)
    lines += [
        "",
        "Operating point for 90% recall",
        "-" * 34,
        f"  threshold  {operating_point['threshold']:.4f}",
        f"  recall     {operating_point['recall']:.4f}",
        f"  precision  {operating_point['precision']:.4f}",
    ]
    return "\n".join(lines)


def aggregate_to_modules(predictions: dict[str, np.ndarray]) -> dict[int, np.ndarray]:
    """Group per-cell crack probabilities by module, for the physics model.

    The physics needs a whole module's cells at once, because mismatch is a
    property of the series string rather than of any individual cell.
    """
    modules = predictions["modules"]
    probability = predictions["probability"]
    return {int(m): probability[modules == m] for m in np.unique(modules) if m >= 0}
