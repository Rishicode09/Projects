"""Tests for preprocessing, the ordinal head, and the split logic."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from pvdefect.data.elpv import NUM_CLASSES, _probability_to_label, class_weights
from pvdefect.data.splits import assign_pseudo_modules, split_by_module
from pvdefect.models.classifier import DefectClassifier
from pvdefect.models.ordinal import (
    CornLoss,
    corn_class_probabilities,
    corn_cumulative_probabilities,
    corn_predict_label,
    expected_severity,
)
from pvdefect.preprocess.cell_prep import (
    estimate_inactive_area_fraction,
    preprocess_cell,
)


# --------------------------------------------------------------------- data

def synthetic_frame(n: int = 600) -> pd.DataFrame:
    """An ELPV-shaped index: contiguous modules, alternating wafer types."""
    rng = np.random.default_rng(0)
    wafer = np.repeat(["mono", "poly"], n // 2)
    labels = rng.integers(0, NUM_CLASSES, size=n)
    return pd.DataFrame(
        {
            "path": [f"cell{i:04d}.png" for i in range(n)],
            "probability": labels / (NUM_CLASSES - 1),
            "wafer_type": wafer,
            "label": labels,
        }
    )


def test_probability_snaps_to_nearest_level():
    assert _probability_to_label(0.0) == 0
    assert _probability_to_label(0.3333333333333333) == 1
    assert _probability_to_label(0.6666666666666666) == 2
    assert _probability_to_label(1.0) == 3


def test_pseudo_modules_never_span_wafer_types():
    frame = assign_pseudo_modules(synthetic_frame(), cells_per_module=60)
    per_module_types = frame.groupby("module_id")["wafer_type"].nunique()
    assert (per_module_types == 1).all()


def test_module_split_shares_no_module_between_subsets():
    frame = assign_pseudo_modules(synthetic_frame(1200), cells_per_module=60)
    splits = split_by_module(frame, seed=0)

    ids = {name: set(subset["module_id"]) for name, subset in splits.items()}
    assert not ids["train"] & ids["val"]
    assert not ids["train"] & ids["test"]
    assert not ids["val"] & ids["test"]

    total = sum(len(subset) for subset in splits.values())
    assert total == len(frame)
    assert all(len(subset) > 0 for subset in splits.values())


def test_class_weights_favour_rare_classes():
    frame = synthetic_frame()
    frame.loc[: len(frame) - 10, "label"] = 0     # make class 0 dominant
    weights = class_weights(frame)
    assert weights[0] < weights[1:].max()
    assert np.all(np.isfinite(weights))


# -------------------------------------------------------------- preprocess

def synthetic_cell(size: int = 300, with_crack: bool = False) -> np.ndarray:
    """A fake EL cell: bright wafer, dark busbars, optional crack."""
    rng = np.random.default_rng(1)
    image = np.full((size, size), 180, dtype=np.uint8)
    image = (image + rng.normal(0, 5, image.shape)).clip(0, 255).astype(np.uint8)
    for x in (size // 4, size // 2, 3 * size // 4):    # busbars
        image[:, x - 3 : x + 3] = 40
    if with_crack:
        for i in range(size):
            j = int(0.6 * i)
            if 0 <= j < size:
                image[i, max(0, j - 2) : j + 2] = 20
    return image


def test_preprocess_shape_and_range():
    processed = preprocess_cell(synthetic_cell(), size=224)
    assert processed.shape == (224, 224, 3)
    assert processed.dtype == np.float32
    assert 0.0 <= processed.min() and processed.max() <= 1.0


def test_single_channel_mode_replicates():
    processed = preprocess_cell(synthetic_cell(), size=128, build_channels=False)
    assert processed.shape == (128, 128, 3)
    assert np.allclose(processed[..., 0], processed[..., 1])


def test_preprocessing_is_invariant_to_exposure():
    """Two exposures of the same cell must preprocess to nearly the same thing.

    This is the property that stops the network from learning per-module camera
    settings instead of defects.
    """
    cell = synthetic_cell()
    dim = (cell.astype(np.float32) * 0.55).astype(np.uint8)

    bright_processed = preprocess_cell(cell, size=128)[..., 0]
    dim_processed = preprocess_cell(dim, size=128)[..., 0]

    assert np.mean(np.abs(bright_processed - dim_processed)) < 0.06


def test_inactive_area_responds_to_dark_regions():
    healthy = synthetic_cell()
    damaged = synthetic_cell()
    damaged[:150, :150] = 10                          # a quarter of the cell dead

    assert estimate_inactive_area_fraction(healthy) < 0.10
    assert estimate_inactive_area_fraction(damaged) > 0.15


# ----------------------------------------------------------------- ordinal

def test_cumulative_probabilities_are_monotone():
    """The property that makes CORN safe to feed into the physics model."""
    logits = torch.randn(64, NUM_CLASSES - 1)
    cumulative = corn_cumulative_probabilities(logits)
    assert torch.all(cumulative[:, :-1] >= cumulative[:, 1:] - 1e-6)
    assert torch.all((cumulative >= 0) & (cumulative <= 1))


def test_class_probabilities_sum_to_one():
    logits = torch.randn(32, NUM_CLASSES - 1)
    probabilities = corn_class_probabilities(logits)
    assert probabilities.shape == (32, NUM_CLASSES)
    assert torch.allclose(probabilities.sum(dim=1), torch.ones(32), atol=1e-5)
    assert torch.all(probabilities >= -1e-6)


def test_expected_severity_spans_the_unit_interval():
    very_negative = torch.full((1, NUM_CLASSES - 1), -20.0)
    very_positive = torch.full((1, NUM_CLASSES - 1), 20.0)
    assert float(expected_severity(very_negative)) == pytest.approx(0.0, abs=1e-4)
    assert float(expected_severity(very_positive)) == pytest.approx(1.0, abs=1e-4)


def test_predicted_label_matches_thresholds():
    # P(y>0) high, P(y>1) high, P(y>2) low  -> class 2
    logits = torch.tensor([[5.0, 5.0, -5.0]])
    assert int(corn_predict_label(logits)[0]) == 2


def test_corn_loss_decreases_when_predictions_improve():
    criterion = CornLoss(NUM_CLASSES)
    targets = torch.tensor([0, 1, 2, 3])

    wrong = torch.tensor(
        [[6.0, 6.0, 6.0], [-6.0, -6.0, -6.0], [-6.0, -6.0, -6.0], [-6.0, -6.0, -6.0]]
    )
    right = torch.tensor(
        [[-6.0, -6.0, -6.0], [6.0, -6.0, -6.0], [6.0, 6.0, -6.0], [6.0, 6.0, 6.0]]
    )
    assert float(criterion(right, targets)) < float(criterion(wrong, targets))


def test_corn_loss_is_finite_when_a_class_is_absent():
    """Rare classes genuinely vanish from small ELPV batches."""
    criterion = CornLoss(NUM_CLASSES)
    loss = criterion(torch.randn(8, NUM_CLASSES - 1), torch.zeros(8, dtype=torch.long))
    assert torch.isfinite(loss)


# ------------------------------------------------------------------- model

def test_model_forward_and_predict_shapes():
    model = DefectClassifier(backbone="resnet18", pretrained=False)
    images = torch.randn(2, 3, 224, 224)

    logits = model(images)
    assert logits.shape == (2, NUM_CLASSES - 1)

    prediction = model.predict(images)
    assert prediction["label"].shape == (2,)
    assert prediction["probabilities"].shape == (2, NUM_CLASSES)
    assert torch.all((prediction["severity"] >= 0) & (prediction["severity"] <= 1))


def test_model_trains_a_step():
    model = DefectClassifier(backbone="resnet18", pretrained=False)
    criterion = CornLoss(NUM_CLASSES)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    images = torch.randn(4, 3, 224, 224)
    targets = torch.tensor([0, 1, 2, 3])

    with torch.no_grad():
        before = float(criterion(model(images), targets))
    for _ in range(5):
        optimizer.zero_grad()
        loss = criterion(model(images), targets)
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        assert float(criterion(model(images), targets)) < before


def test_gradcam_produces_a_normalised_map():
    from pvdefect.explain import GradCam, overlay_heatmap

    model = DefectClassifier(backbone="resnet18", pretrained=False)
    image = torch.randn(1, 3, 224, 224)

    with GradCam(model) as cam:
        heatmap = cam(image, level=0)

    assert heatmap.shape == (224, 224)
    assert 0.0 <= heatmap.min() and heatmap.max() <= 1.0 + 1e-6

    overlay = overlay_heatmap(image[0].permute(1, 2, 0).numpy(), heatmap)
    assert overlay.shape == (224, 224, 3)
    assert overlay.dtype == np.uint8
