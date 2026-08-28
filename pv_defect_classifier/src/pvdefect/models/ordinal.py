"""Ordinal (CORN) head and loss for graded defect severity.

ELPV's four labels are ordered: confusing "none" with "severe" is a worse error
than confusing "moderate" with "severe", and a plain softmax cross-entropy
treats both identically. It also gives you no monotonicity guarantee, so a
softmax model can output P(severe) > P(moderate) in ways that make the
downstream physics model behave erratically.

We use CORN (Conditional Ordinal Regression for Neural networks, Shi et al.
2021): K-1 binary heads where head *k* predicts P(y > k | y > k-1). The
cumulative probabilities are products of these conditionals, so they are
monotonically non-increasing *by construction*, which is exactly the property
the power-loss model needs to stay well behaved.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class CornLoss(nn.Module):
    """Conditional ordinal loss over ``num_classes - 1`` binary tasks.

    Each head *k* is trained only on the subset of samples with ``y >= k``,
    which is what makes the outputs conditional probabilities rather than
    unconditional ones (the difference between CORN and the earlier CORAL).
    """

    def __init__(self, num_classes: int, class_weights: torch.Tensor | None = None) -> None:
        super().__init__()
        self.num_classes = num_classes
        if class_weights is not None:
            self.register_buffer("class_weights", class_weights.float())
        else:
            self.class_weights = None

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if logits.shape[1] != self.num_classes - 1:
            raise ValueError(
                f"CORN expects {self.num_classes - 1} logits, got {logits.shape[1]}"
            )

        total = logits.new_zeros(())
        contributing = 0

        for k in range(self.num_classes - 1):
            # Head k is only defined for samples that reached level k.
            subset = targets >= k
            if not torch.any(subset):
                continue

            head_logits = logits[subset, k]
            head_targets = (targets[subset] > k).float()

            if self.class_weights is not None:
                # Weight each sample by the class it actually belongs to, so
                # the rare middle levels keep their influence on every head.
                weights = self.class_weights[targets[subset]]
                loss = F.binary_cross_entropy_with_logits(
                    head_logits, head_targets, weight=weights, reduction="mean"
                )
            else:
                loss = F.binary_cross_entropy_with_logits(
                    head_logits, head_targets, reduction="mean"
                )

            total = total + loss
            contributing += 1

        return total / max(contributing, 1)


def corn_cumulative_probabilities(logits: torch.Tensor) -> torch.Tensor:
    """Convert CORN logits to P(y > k) for each k, as a cumulative product.

    Shape ``(N, K-1)``. Monotonically non-increasing along dim 1 by
    construction, since each factor lies in (0, 1).
    """
    conditionals = torch.sigmoid(logits)
    return torch.cumprod(conditionals, dim=1)


def corn_class_probabilities(logits: torch.Tensor) -> torch.Tensor:
    """Per-class probabilities ``P(y = k)``, shape ``(N, K)``.

    P(y=0)   = 1 - P(y>0)
    P(y=k)   = P(y>k-1) - P(y>k)
    P(y=K-1) = P(y>K-2)
    """
    cumulative = corn_cumulative_probabilities(logits)
    ones = cumulative.new_ones((cumulative.shape[0], 1))
    zeros = cumulative.new_zeros((cumulative.shape[0], 1))
    upper = torch.cat([ones, cumulative], dim=1)     # P(y > k-1), k = 0..K-1
    lower = torch.cat([cumulative, zeros], dim=1)    # P(y > k),   k = 0..K-1
    # Clamp guards against tiny negatives from floating point subtraction.
    return torch.clamp(upper - lower, min=0.0)


def corn_predict_label(logits: torch.Tensor, threshold: float = 0.5) -> torch.Tensor:
    """Predicted ordinal level: how many cumulative probabilities clear ``threshold``.

    Raising ``threshold`` makes the model more conservative about calling a
    cell defective, which is the knob a plant operator tunes against their
    false-alarm budget.
    """
    cumulative = corn_cumulative_probabilities(logits)
    return (cumulative > threshold).sum(dim=1)


def expected_severity(logits: torch.Tensor, num_classes: int = 4) -> torch.Tensor:
    """Expected severity in [0, 1] under the predicted distribution.

    This is the number handed to the physics model. A continuous expectation
    beats a hard argmax there: a cell the model reads as a coin flip between
    "none" and "severe" should propagate as genuine uncertainty in the power
    estimate, not as a confident middle answer.
    """
    probabilities = corn_class_probabilities(logits)
    levels = torch.linspace(0.0, 1.0, num_classes, device=logits.device, dtype=probabilities.dtype)
    return (probabilities * levels).sum(dim=1)
