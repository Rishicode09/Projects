"""Tests for preprocessing, module cropping, augmentation, and the classifier."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch

from pvdefect.data.elpv import CLASS_NAMES, NUM_CLASSES, positive_weight, snap_to_level
from pvdefect.data.splits import assign_pseudo_modules, split_by_module
from pvdefect.data.transforms import build_eval_transform, build_train_transform
from pvdefect.models.classifier import DefectClassifier
from pvdefect.preprocess.cell_prep import (
    estimate_inactive_area_fraction,
    preprocess_cell,
)
from pvdefect.preprocess.module_crop import (
    crop_module,
    find_module_corners,
    rectify_module,
    split_into_cells,
)


# --------------------------------------------------------------------- data

def synthetic_frame(n: int = 600) -> pd.DataFrame:
    """An ELPV-shaped index: contiguous modules, alternating wafer types."""
    rng = np.random.default_rng(0)
    wafer = np.repeat(["mono", "poly"], n // 2)
    probability = rng.choice([0.0, 1 / 3, 2 / 3, 1.0], size=n)
    return pd.DataFrame(
        {
            "path": [f"cell{i:04d}.png" for i in range(n)],
            "probability": probability,
            "wafer_type": wafer,
            "label": (probability >= 0.5).astype(int),
        }
    )


def test_binary_labels_have_two_classes():
    assert NUM_CLASSES == 2
    assert CLASS_NAMES == ("functional", "cracked")


def test_snap_to_level():
    assert snap_to_level(0.0) == 0.0
    assert snap_to_level(0.34) == pytest.approx(1 / 3)
    assert snap_to_level(0.9) == 1.0


def test_defect_threshold_changes_the_split_point():
    """The threshold is a real operating choice, so it must actually move."""
    frame = synthetic_frame()
    strict = (frame["probability"] >= 0.5).sum()
    lenient = (frame["probability"] >= 0.1).sum()
    assert lenient > strict


def test_pseudo_modules_never_span_wafer_types():
    frame = assign_pseudo_modules(synthetic_frame(), cells_per_module=60)
    assert (frame.groupby("module_id")["wafer_type"].nunique() == 1).all()


def test_module_split_shares_no_module_between_subsets():
    frame = assign_pseudo_modules(synthetic_frame(1200), cells_per_module=60)
    splits = split_by_module(frame, seed=0)

    ids = {name: set(subset["module_id"]) for name, subset in splits.items()}
    assert not ids["train"] & ids["val"]
    assert not ids["train"] & ids["test"]
    assert not ids["val"] & ids["test"]
    assert sum(len(s) for s in splits.values()) == len(frame)
    assert all(len(subset) > 0 for subset in splits.values())


def test_positive_weight_exceeds_one_when_cracked_is_minority():
    frame = synthetic_frame()
    frame.loc[: len(frame) - 50, "label"] = 0
    assert positive_weight(frame) > 1.0


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


def synthetic_module(rows: int = 6, columns: int = 10, cell: int = 60) -> np.ndarray:
    """A grid of bright cells separated by dark gaps, on a dark background."""
    gap = 6
    height = rows * cell + (rows + 1) * gap
    width = columns * cell + (columns + 1) * gap
    module = np.full((height, width), 20, dtype=np.uint8)

    for r in range(rows):
        for c in range(columns):
            y = gap + r * (cell + gap)
            x = gap + c * (cell + gap)
            module[y : y + cell, x : x + cell] = 200

    # Dark margin so the laminate is a findable bright blob on dark ground.
    canvas = np.full((height + 60, width + 60), 5, dtype=np.uint8)
    canvas[30 : 30 + height, 30 : 30 + width] = module
    return canvas


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

    This is the property that stops the network learning per-module camera
    settings instead of defects.
    """
    cell = synthetic_cell()
    dim = (cell.astype(np.float32) * 0.55).astype(np.uint8)

    bright = preprocess_cell(cell, size=128)[..., 0]
    dark = preprocess_cell(dim, size=128)[..., 0]
    assert np.mean(np.abs(bright - dark)) < 0.06


def test_inactive_area_responds_to_dark_regions():
    healthy = synthetic_cell()
    damaged = synthetic_cell()
    damaged[:150, :150] = 10                          # a quarter of the cell dead

    assert estimate_inactive_area_fraction(healthy) < 0.10
    assert estimate_inactive_area_fraction(damaged) > 0.15


# ----------------------------------------------------------- module crop

def test_find_module_corners_on_synthetic_module():
    corners = find_module_corners(synthetic_module())
    assert corners is not None
    assert corners.shape == (4, 2)
    # Ordered top-left, top-right, bottom-right, bottom-left.
    assert corners[0][0] < corners[1][0]      # TL left of TR
    assert corners[0][1] < corners[3][1]      # TL above BL


def test_find_module_corners_returns_none_when_no_module_fills_the_frame():
    """A wrong rectification silently ruins every crop, so refusing is correct.

    Here the bright region is far too small to be the laminate, which is the
    realistic failure: a photo where the module is a distant object in frame.
    """
    image = np.full((300, 300), 5, dtype=np.uint8)
    image[140:160, 140:160] = 220          # ~0.4% of the frame
    assert find_module_corners(image, min_area_fraction=0.15) is None


def test_split_into_cells_returns_the_right_count_and_shape():
    cells = split_into_cells(synthetic_module(), rows=6, columns=10, cell_size=64)
    assert len(cells) == 60
    assert all(cell.shape[:2] == (64, 64) for cell in cells)


def test_crop_module_end_to_end():
    grid = crop_module(synthetic_module(), rows=6, columns=10, cell_size=64)
    assert len(grid) == 60
    assert grid.rows == 6 and grid.columns == 10
    assert grid.cell_at(0, 0).shape[:2] == (64, 64)


def test_cropped_cells_are_mostly_wafer_not_gap():
    """If the cuts land on the gaps, the crops come out dark — the classic failure."""
    grid = crop_module(synthetic_module(), rows=6, columns=10, cell_size=64)
    means = np.array([cell.mean() for cell in grid.cells])
    # Wafer is 200, gaps are 20; a correctly placed crop is much closer to 200.
    assert means.min() > 120


def realistic_module(rows: int = 3, columns: int = 5, cell: int = 300,
                     dark_edge: bool = True) -> tuple[np.ndarray, list[np.ndarray]]:
    """A full-scale module image plus the ground-truth cells it was built from.

    Two properties that the small synthetic module does not have, both of which
    hid real bugs:

    * **Realistic pixel scale.** Morphological kernels sized in absolute pixels
      behave completely differently at 300-pixel cells than at 60-pixel ones.
    * **Dark cells along an edge.** Brightness-based outline detection finds the
      module several hundred pixels inside the laminate when the border cells
      are dead, and every crop then straddles two cells — while still having
      entirely plausible mean and variance.
    """
    rng = np.random.default_rng(7)
    gap = 8
    cells = []
    for index in range(rows * columns):
        base = 40 if (dark_edge and index < columns) else 190
        image = np.full((cell, cell), base, dtype=np.uint8)
        image = (image + rng.normal(0, 4, image.shape)).clip(0, 255).astype(np.uint8)
        for x in (cell // 4, cell // 2, 3 * cell // 4):     # busbars: present even when dark
            image[:, x - 3 : x + 3] = max(10, base - 60)
        for y in range(0, cell, cell // 8):                 # fingers
            image[y : y + 2, :] = max(8, base - 50)
        cells.append(image)

    height = rows * cell + (rows + 1) * gap
    width = columns * cell + (columns + 1) * gap
    module = np.full((height, width), 18, dtype=np.uint8)
    for r in range(rows):
        for c in range(columns):
            y, x = gap + r * (cell + gap), gap + c * (cell + gap)
            module[y : y + cell, x : x + cell] = cells[r * columns + c]

    canvas = np.full((height + 120, width + 120), 6, dtype=np.uint8)
    canvas[60 : 60 + height, 60 : 60 + width] = module
    return canvas, cells


def test_cropping_recovers_the_true_cells_at_realistic_scale():
    """Regression: crops must actually align, not merely look statistically sane."""
    module, truth = realistic_module()
    grid = crop_module(module, rows=3, columns=5, cell_size=300)

    assert len(grid) == len(truth)
    errors = [
        float(np.mean(np.abs(crop.astype(float) - true.astype(float))))
        for crop, true in zip(grid.cells, truth)
    ]
    # A misaligned crop straddling two cells scores ~40 on this scale.
    assert np.mean(errors) < 25.0, f"crops look misaligned (mean abs error {np.mean(errors):.1f})"


def test_dark_edge_cells_do_not_shift_the_detected_outline():
    """A module with dead cells on one edge must still be found in full.

    Brightness thresholding fails here; texture segmentation is what makes it
    work, because a dead cell still shows its metallisation.
    """
    module, _ = realistic_module(dark_edge=True)
    corners = find_module_corners(module)
    assert corners is not None

    # The laminate starts at (60, 60) by construction; allow a modest margin.
    assert corners[:, 0].min() < 140, "outline shifted right, missing the dark cells"
    assert corners[:, 1].min() < 140, "outline shifted down, missing the dark cells"


def test_module_corners_are_four_distinct_points():
    """Guards the degenerate-quad bug: duplicated corners smear the whole warp."""
    module, _ = realistic_module()
    corners = find_module_corners(module)
    assert corners is not None
    for i in range(4):
        for j in range(i + 1, 4):
            assert np.linalg.norm(corners[i] - corners[j]) > 1.0


def test_rectify_is_a_noop_without_corners():
    image = synthetic_cell()
    rectified, corners = rectify_module(image, corners=None)
    assert rectified.shape[:2] == image.shape[:2] or corners is not None


# ------------------------------------------------------------ transforms

def test_train_transform_preserves_shape_and_dtype():
    transform = build_train_transform(224)
    image = (np.random.rand(300, 300, 3) * 255).astype(np.uint8)
    for _ in range(10):
        out = transform(image=image)["image"]
        assert out.shape == (224, 224, 3)
        assert out.dtype == np.uint8


def test_eval_transform_is_deterministic():
    transform = build_eval_transform(224)
    image = (np.random.rand(300, 300, 3) * 255).astype(np.uint8)
    first = transform(image=image)["image"]
    second = transform(image=image)["image"]
    assert np.array_equal(first, second)


def test_train_transform_actually_changes_the_image():
    transform = build_train_transform(224)
    image = (np.random.rand(300, 300, 3) * 255).astype(np.uint8)
    outputs = [transform(image=image)["image"] for _ in range(6)]
    assert any(not np.array_equal(outputs[0], other) for other in outputs[1:])


def test_augmentation_does_not_introduce_black_borders():
    """Reflective padding matters: a black wedge reads as a dead region."""
    transform = build_train_transform(224)
    image = np.full((300, 300, 3), 200, dtype=np.uint8)
    for _ in range(15):
        out = transform(image=image)["image"]
        # A rotated image with constant padding would show near-zero corners.
        assert out.min() > 30


# ------------------------------------------------------------------- model

@pytest.mark.parametrize("backbone", ["resnet50", "efficientnet_b0"])
def test_model_forward_and_predict_shapes(backbone):
    model = DefectClassifier(backbone=backbone, pretrained=False)
    images = torch.randn(2, 3, 224, 224)

    logits = model(images)
    assert logits.shape == (2,)      # single logit per image

    prediction = model.predict(images)
    assert prediction["label"].shape == (2,)
    assert prediction["probability"].shape == (2,)
    assert torch.all((prediction["probability"] >= 0) & (prediction["probability"] <= 1))
    # severity is what the physics model consumes
    assert torch.allclose(prediction["severity"], prediction["probability"])


def test_threshold_shifts_the_decision():
    model = DefectClassifier(backbone="resnet18", pretrained=False)
    images = torch.randn(8, 3, 224, 224)
    permissive = model.predict(images, threshold=0.01)["label"].sum()
    strict = model.predict(images, threshold=0.99)["label"].sum()
    assert permissive >= strict


def test_model_trains_a_step():
    model = DefectClassifier(backbone="resnet18", pretrained=False)
    criterion = torch.nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    images = torch.randn(4, 3, 224, 224)
    targets = torch.tensor([0.0, 1.0, 1.0, 0.0])

    with torch.no_grad():
        before = float(criterion(model(images), targets))
    for _ in range(5):
        optimizer.zero_grad()
        loss = criterion(model(images), targets)
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        assert float(criterion(model(images), targets)) < before


def test_pos_weight_penalises_missed_cracks_more():
    """The mechanism that stops the model defaulting to 'functional'."""
    weighted = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor([4.0]))
    plain = torch.nn.BCEWithLogitsLoss()

    logits = torch.tensor([-3.0])            # confident "functional"
    cracked = torch.tensor([1.0])            # ...but it is cracked
    assert float(weighted(logits, cracked)) > float(plain(logits, cracked))


def test_gradcam_produces_a_normalised_map():
    from pvdefect.explain import GradCam, overlay_heatmap

    model = DefectClassifier(backbone="resnet18", pretrained=False)
    image = torch.randn(1, 3, 224, 224)

    with GradCam(model) as cam:
        heatmap = cam(image)

    assert heatmap.shape == (224, 224)
    assert 0.0 <= heatmap.min() and heatmap.max() <= 1.0 + 1e-6

    overlay = overlay_heatmap(image[0].permute(1, 2, 0).numpy(), heatmap)
    assert overlay.shape == (224, 224, 3)
    assert overlay.dtype == np.uint8
