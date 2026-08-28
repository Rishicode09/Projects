"""Tests for the detection stack.

These deliberately do not train a YOLO model — that needs reviewed annotations
and minutes of compute. They cover the parts this repo actually owns: proposal
generation, YOLO dataset layout, and the area-to-physics coupling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pvdefect.detection.dataset import build_yolo_dataset, write_data_yaml
from pvdefect.detection.detector import (
    Detection,
    defect_area_fraction,
    summarise_module,
)
from pvdefect.detection.pseudo_label import (
    CLASS_NAMES,
    CRACK,
    INACTIVE_AREA,
    Region,
    classify_region,
    draw_proposals,
    is_grid_structure,
    propose_regions,
    proposals_to_yolo_lines,
)


def cell_with_crack(size: int = 300) -> np.ndarray:
    rng = np.random.default_rng(2)
    image = np.full((size, size), 190, dtype=np.uint8)
    image = (image + rng.normal(0, 4, image.shape)).clip(0, 255).astype(np.uint8)
    for i in range(40, size - 40):
        j = int(0.8 * i)
        if 0 <= j < size:
            image[i, max(0, j - 2) : j + 3] = 15
    return image


def cell_with_dead_region(size: int = 300) -> np.ndarray:
    rng = np.random.default_rng(3)
    image = np.full((size, size), 190, dtype=np.uint8)
    image = (image + rng.normal(0, 4, image.shape)).clip(0, 255).astype(np.uint8)
    image[40:180, 40:180] = 12
    return image


def clean_cell(size: int = 300) -> np.ndarray:
    rng = np.random.default_rng(4)
    image = np.full((size, size), 190, dtype=np.uint8)
    return (image + rng.normal(0, 4, image.shape)).clip(0, 255).astype(np.uint8)


def cell_with_busbars(size: int = 300) -> np.ndarray:
    image = clean_cell(size)
    for x in (size // 4, size // 2, 3 * size // 4):
        image[:, x - 3 : x + 3] = 40
    return image


def cell_with_busbars_and_crack(size: int = 300) -> np.ndarray:
    image = cell_with_busbars(size)
    for i in range(60, size - 60):
        j = int(30 + 0.7 * i)
        if 0 <= j < size:
            image[i, max(0, j - 2) : j + 3] = 15
    return image


# ------------------------------------------------------------- proposals

def test_classify_region_separates_lines_from_blobs():
    assert classify_region(width=100, height=8, area=500) == CRACK      # elongated
    assert classify_region(width=100, height=100, area=9000) == INACTIVE_AREA  # filled blob


def test_proposals_found_on_a_cracked_cell():
    regions = propose_regions(cell_with_crack())
    assert len(regions) >= 1


def test_dead_region_is_proposed_and_classified_as_area():
    regions = propose_regions(cell_with_dead_region())
    assert regions
    assert any(r.class_id == INACTIVE_AREA for r in regions)
    # The dead square is ~21% of the cell; the biggest box should be substantial.
    assert max(r.width * r.height for r in regions) > 0.05 * 300 * 300


def test_clean_cell_yields_no_proposals():
    """Guards the Otsu trap: an always-splitting threshold floods clean cells."""
    assert propose_regions(clean_cell()) == []


def test_busbars_are_not_proposed_as_defects():
    """Every cell has busbars, so boxing them means a false positive everywhere."""
    assert propose_regions(cell_with_busbars()) == []


def test_a_crack_is_still_found_among_busbars():
    """Busbar suppression must not swallow real defects on the same cell."""
    regions = propose_regions(cell_with_busbars_and_crack())
    assert len(regions) >= 1
    assert any(r.class_id == CRACK for r in regions)


def test_is_grid_structure_geometry():
    # Full-height thin line through a 300x300 cell: a busbar.
    assert is_grid_structure(width=6, height=300, image_width=300, image_height=300)
    assert is_grid_structure(width=300, height=5, image_width=300, image_height=300)
    # A compact blob is not.
    assert not is_grid_structure(width=140, height=140, image_width=300, image_height=300)
    # A full-height but wide region is a dead column, not a busbar.
    assert not is_grid_structure(width=129, height=300, image_width=300, image_height=300)


def test_proposal_count_is_capped():
    regions = propose_regions(cell_with_crack(), max_regions=2)
    assert len(regions) <= 2


def test_yolo_lines_are_normalised_and_well_formed():
    regions = [Region(x=10, y=20, width=30, height=40, class_id=CRACK, score=0.5)]
    lines = proposals_to_yolo_lines(regions, 300, 300)
    assert len(lines) == 1

    parts = lines[0].split()
    assert len(parts) == 5
    assert int(parts[0]) == CRACK
    values = [float(v) for v in parts[1:]]
    assert all(0.0 <= v <= 1.0 for v in values)
    # centre-x = (10 + 15) / 300
    assert values[0] == pytest.approx(25 / 300, abs=1e-4)
    assert values[2] == pytest.approx(30 / 300, abs=1e-4)


def test_draw_proposals_returns_a_colour_image():
    image = cell_with_crack()
    drawn = draw_proposals(image, propose_regions(image))
    assert drawn.ndim == 3 and drawn.shape[2] == 3
    assert drawn.dtype == np.uint8


# --------------------------------------------------------------- dataset

def test_write_data_yaml_has_the_keys_ultralytics_needs(tmp_path):
    import yaml

    path = write_data_yaml(tmp_path)
    payload = yaml.safe_load(path.read_text())
    assert {"path", "train", "val", "names"} <= set(payload)
    assert payload["names"][0] == CLASS_NAMES[0]


def test_build_yolo_dataset_writes_a_label_for_every_image(tmp_path):
    """Missing label files are silently skipped by YOLO, killing the negatives."""
    import cv2

    image_dir = tmp_path / "cells"
    image_dir.mkdir()
    rows = []
    for index, (image, label) in enumerate(
        [(cell_with_crack(), 1), (clean_cell(), 0), (cell_with_dead_region(), 1)]
    ):
        path = image_dir / f"cell{index:03d}.png"
        cv2.imwrite(str(path), image)
        rows.append({"path": path, "probability": float(label), "wafer_type": "mono",
                     "label": label, "module_id": 0})

    frame = pd.DataFrame(rows)
    root = tmp_path / "yolo"
    build_yolo_dataset({"train": frame}, root)

    images = sorted((root / "images" / "train").glob("*.png"))
    labels = sorted((root / "labels" / "train").glob("*.txt"))
    assert len(images) == 3
    assert len(labels) == 3          # including the functional cell's empty file

    functional_label = (root / "labels" / "train" / "cell001.txt").read_text().strip()
    assert functional_label == ""


def test_only_label_defective_leaves_functional_cells_empty(tmp_path):
    import cv2

    path = tmp_path / "clean.png"
    cv2.imwrite(str(path), clean_cell())
    frame = pd.DataFrame(
        [{"path": path, "probability": 0.0, "wafer_type": "mono", "label": 0, "module_id": 0}]
    )

    root = tmp_path / "yolo"
    build_yolo_dataset({"train": frame}, root, only_label_defective=True)
    assert (root / "labels" / "train" / "clean.txt").read_text().strip() == ""


# ------------------------------------------------- area -> physics coupling

def test_inactive_area_counts_fully_and_cracks_are_discounted():
    """The physics distinction: a dead region is lost area, a crack line is not."""
    shape = (100, 100)
    inactive = [Detection(0, 0, 50, 50, INACTIVE_AREA, 0.9)]     # 25% of the cell
    crack = [Detection(0, 0, 50, 50, CRACK, 0.9)]                # same box, a crack

    assert defect_area_fraction(inactive, shape) == pytest.approx(0.25, abs=1e-6)
    assert defect_area_fraction(crack, shape, crack_area_weight=0.25) == pytest.approx(
        0.0625, abs=1e-6
    )


def test_overlapping_detections_are_not_double_counted():
    shape = (100, 100)
    overlapping = [
        Detection(0, 0, 50, 50, INACTIVE_AREA, 0.9),
        Detection(25, 25, 75, 75, INACTIVE_AREA, 0.8),
    ]
    # Union is 2*2500 - 625 = 4375 px of 10000, not 5000.
    assert defect_area_fraction(overlapping, shape) == pytest.approx(0.4375, abs=1e-6)


def test_crack_box_inside_an_inactive_box_adds_nothing():
    shape = (100, 100)
    detections = [
        Detection(0, 0, 50, 50, INACTIVE_AREA, 0.9),
        Detection(10, 10, 40, 40, CRACK, 0.9),
    ]
    assert defect_area_fraction(detections, shape) == pytest.approx(0.25, abs=1e-6)


def test_no_detections_means_no_area():
    assert defect_area_fraction([], (100, 100)) == 0.0


def test_area_fraction_is_bounded():
    huge = [Detection(-50, -50, 500, 500, INACTIVE_AREA, 0.9)]
    assert 0.0 <= defect_area_fraction(huge, (100, 100)) <= 0.95


def test_summarise_module_reports_the_worst_cell():
    cells = [
        [],
        [Detection(0, 0, 30, 30, INACTIVE_AREA, 0.9)],
        [Detection(0, 0, 80, 80, INACTIVE_AREA, 0.9)],
    ]
    summary = summarise_module(cells, image_shape=(100, 100))
    assert summary["cells_with_defects"] == 2
    assert summary["total_detections"] == 2
    assert summary["worst_cell_index"] == 2
    assert summary["worst_cell_area"] == pytest.approx(0.64, abs=1e-6)


def test_detected_area_overrides_the_severity_lookup_table():
    """The point of detection: replace an inferred area with a measured one."""
    from pvdefect.physics.degradation import DegradationModel

    model = DegradationModel()
    severity = np.array([1.0])

    from_table = model.inactive_area(severity)
    from_detection = model.inactive_area(severity, detected_area=np.array([0.60]))

    # Detection is weighted at 0.8, so the result must move most of the way
    # from the table value toward the measurement.
    assert from_detection > from_table
    assert from_detection > 0.4


def test_detection_is_gated_by_classifier_confidence():
    """A detector firing on a cell the classifier calls clean is likely wrong."""
    from pvdefect.physics.degradation import DegradationModel

    model = DegradationModel()
    confident = model.inactive_area(np.array([1.0]), detected_area=np.array([0.6]))
    unsure = model.inactive_area(np.array([0.0]), detected_area=np.array([0.6]))
    assert confident > unsure
