"""Evaluation metrics for ordinal defect classification.

Accuracy is close to useless on ELPV: 57% of cells are class 0, so a model that
predicts "no defect" for everything scores 57% and finds nothing. The metrics
here are chosen to be hard to fool that way.
"""

from __future__ import annotations

import numpy as np
import torch
from sklearn.metrics import (
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    roc_auc_score,
)

from .data.elpv import CLASS_NAMES, NUM_CLASSES
from .models.ordinal import corn_cumulative_probabilities, corn_predict_label, expected_severity


@torch.no_grad()
def collect_predictions(model, loader, device: torch.device) -> dict[str, np.ndarray]:
    """Run the model over a loader and return raw arrays for metric computation."""
    model.eval()
    logits_all, labels_all, modules_all = [], [], []

    for batch in loader:
        images = batch["image"].to(device, non_blocking=True)
        logits = model(images)
        logits_all.append(logits.detach().float().cpu())
        labels_all.append(batch["label"])
        modules_all.append(batch["module_id"])

    logits = torch.cat(logits_all)
    labels = torch.cat(labels_all)

    return {
        "logits": logits.numpy(),
        "labels": labels.numpy(),
        "modules": torch.cat(modules_all).numpy(),
        "predictions": corn_predict_label(logits).numpy(),
        "severity": expected_severity(logits, NUM_CLASSES).numpy(),
        "cumulative": corn_cumulative_probabilities(logits).numpy(),
    }


def compute_metrics(predictions: dict[str, np.ndarray]) -> dict[str, float]:
    """Metrics that respect the ordinal structure and the class imbalance.

    ``quadratic_kappa`` is the headline number: it penalises a none->severe
    error nine times as hard as a none->mild one, which matches the operational
    cost of the mistake. ``defect_auc`` measures the binary "is this cell worth
    a technician's time" decision independently of any threshold choice.
    ``mae_severity`` is in units of severity levels, so 0.3 means the average
    prediction is a third of a level off.
    """
    labels = predictions["labels"]
    predicted = predictions["predictions"]
    severity = predictions["severity"]

    metrics: dict[str, float] = {
        "accuracy": float((predicted == labels).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
        "macro_f1": float(f1_score(labels, predicted, average="macro", zero_division=0)),
        "quadratic_kappa": float(
            cohen_kappa_score(labels, predicted, weights="quadratic", labels=list(range(NUM_CLASSES)))
        ),
        "mae_levels": float(mean_absolute_error(labels, predicted)),
        "mae_severity": float(np.mean(np.abs(severity - labels / (NUM_CLASSES - 1)))),
    }

    # Binary defect detection: class 0 vs everything else.
    binary_labels = (labels > 0).astype(int)
    if 0 < binary_labels.sum() < len(binary_labels):
        # P(y > 0) is the first cumulative probability.
        metrics["defect_auc"] = float(roc_auc_score(binary_labels, predictions["cumulative"][:, 0]))
        binary_predicted = (predicted > 0).astype(int)
        metrics["defect_f1"] = float(f1_score(binary_labels, binary_predicted, zero_division=0))
        true_positive = int(((binary_predicted == 1) & (binary_labels == 1)).sum())
        metrics["defect_recall"] = float(true_positive / max(binary_labels.sum(), 1))
        metrics["defect_precision"] = float(true_positive / max(binary_predicted.sum(), 1))

    # Severe-only recall: missing a class-3 cell is the expensive failure.
    severe_mask = labels == NUM_CLASSES - 1
    if severe_mask.any():
        metrics["severe_recall"] = float((predicted[severe_mask] == NUM_CLASSES - 1).mean())

    return metrics


def confusion(predictions: dict[str, np.ndarray]) -> np.ndarray:
    return confusion_matrix(
        predictions["labels"], predictions["predictions"], labels=list(range(NUM_CLASSES))
    )


def format_report(predictions: dict[str, np.ndarray]) -> str:
    """Human-readable metric block plus confusion matrix."""
    metrics = compute_metrics(predictions)
    matrix = confusion(predictions)

    lines = ["Metrics", "-------"]
    lines += [f"  {name:<20s} {value:.4f}" for name, value in metrics.items()]

    lines += ["", "Confusion matrix (rows = true, cols = predicted)", "-" * 48]
    header = " " * 12 + "".join(f"{name:>9s}" for name in CLASS_NAMES)
    lines.append(header)
    for i, row in enumerate(matrix):
        lines.append(f"{CLASS_NAMES[i]:>10s}  " + "".join(f"{int(v):>9d}" for v in row))

    return "\n".join(lines)


def aggregate_to_modules(predictions: dict[str, np.ndarray]) -> dict[int, np.ndarray]:
    """Group per-cell severities by module, for feeding the physics model.

    The physics model needs a full module's cells at once, because mismatch is
    a property of the string rather than of any individual cell.
    """
    modules = predictions["modules"]
    severity = predictions["severity"]
    return {int(m): severity[modules == m] for m in np.unique(modules) if m >= 0}
