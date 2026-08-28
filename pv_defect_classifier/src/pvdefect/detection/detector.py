"""Ultralytics YOLO training and inference for EL defect localisation.

**Why detection earns its place here.** The physics model's dominant input is
*inactive area* — what fraction of the cell stopped contributing photocurrent.
A classifier cannot supply that; it emits a probability that has to be mapped
to an area through the uncalibrated table in ``physics.degradation``. A detector
measures the geometry directly, so :func:`defect_area_fraction` closes the
largest calibration gap in the project by replacing a guess with a measurement.

That is the argument for spending annotation effort on boxes: not better
accuracy on a benchmark, but a physically meaningful number where there was
previously a lookup table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .pseudo_label import CLASS_NAMES, INACTIVE_AREA

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "yolo11n.pt"   # nano: 2,624 cells does not support anything larger
DEFAULT_IMAGE_SIZE = 320       # ELPV cells are 300x300; 320 is the nearest /32 multiple


@dataclass(frozen=True)
class Detection:
    """One detected defect on one cell."""

    x1: float
    y1: float
    x2: float
    y2: float
    class_id: int
    confidence: float

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)

    @property
    def class_name(self) -> str:
        return CLASS_NAMES[self.class_id] if self.class_id < len(CLASS_NAMES) else "unknown"


def train_detector(
    data_yaml: Path,
    model_name: str = DEFAULT_MODEL,
    epochs: int = 100,
    image_size: int = DEFAULT_IMAGE_SIZE,
    batch: int = 16,
    project: str = "artifacts/detection",
    name: str = "elpv",
    device: str | int | None = None,
    **kwargs,
):
    """Fine-tune a YOLO detector on the EL dataset.

    Ultralytics runs its own augmentation (mosaic, HSV, flips) internally. Two
    of its defaults are wrong for EL imagery and are overridden here:

    * ``hsv_s`` / ``hsv_v`` — the input is single-channel near-infrared
      replicated to 3 channels, so saturation jitter is meaningless. Value
      jitter is kept, as a stand-in for exposure variation.
    * ``degrees`` — enabled, unlike the default of 0. Solar cells have no
      canonical orientation, so rotation is free label-preserving data.

    ``mosaic`` is left on: it fabricates composite scenes that never occur in a
    real cell crop, but on a dataset this small the regularisation is worth
    more than the realism it costs.
    """
    from ultralytics import YOLO

    model = YOLO(model_name)
    return model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=image_size,
        batch=batch,
        project=project,
        name=name,
        device=device,
        hsv_h=0.0,
        hsv_s=0.0,
        hsv_v=0.25,
        degrees=180.0,
        fliplr=0.5,
        flipud=0.5,
        **kwargs,
    )


def load_detector(weights: Path | str):
    """Load trained weights, or fall back to the pretrained checkpoint."""
    from ultralytics import YOLO

    path = Path(weights)
    if not path.exists():
        logger.warning(
            "No detector weights at %s; loading %s, which is COCO-pretrained and "
            "knows nothing about solar cells. Train one before trusting output.",
            path, DEFAULT_MODEL,
        )
        return YOLO(DEFAULT_MODEL)
    return YOLO(str(path))


def detect_cells(
    model,
    images: list[np.ndarray],
    confidence: float = 0.25,
    image_size: int = DEFAULT_IMAGE_SIZE,
) -> list[list[Detection]]:
    """Run the detector over a list of cell crops.

    Returns one list of detections per input image, in the same order.
    """
    if not images:
        return []

    # Ultralytics wants HWC uint8 BGR.
    prepared = []
    for image in images:
        array = image
        if array.dtype != np.uint8:
            array = np.clip(array * 255 if array.max() <= 1.5 else array, 0, 255).astype(np.uint8)
        if array.ndim == 2:
            array = np.stack([array] * 3, axis=-1)
        prepared.append(array)

    results = model.predict(prepared, conf=confidence, imgsz=image_size, verbose=False)

    per_image: list[list[Detection]] = []
    for result in results:
        detections: list[Detection] = []
        boxes = getattr(result, "boxes", None)
        if boxes is not None and len(boxes):
            coordinates = boxes.xyxy.cpu().numpy()
            classes = boxes.cls.cpu().numpy().astype(int)
            confidences = boxes.conf.cpu().numpy()
            for (x1, y1, x2, y2), class_id, score in zip(coordinates, classes, confidences):
                detections.append(
                    Detection(float(x1), float(y1), float(x2), float(y2),
                              int(class_id), float(score))
                )
        per_image.append(detections)
    return per_image


def defect_area_fraction(
    detections: list[Detection],
    image_shape: tuple[int, int],
    inactive_classes: tuple[int, ...] = (INACTIVE_AREA,),
    crack_area_weight: float = 0.25,
) -> float:
    """Fraction of the cell that is electrically inactive, from detections.

    This is the function that feeds ``physics.degradation``, and it encodes one
    genuine piece of physics rather than just summing boxes:

    A detected **inactive area** counts at its full box area — the region is
    dark because it is not collecting, and the box approximates its extent.
    A detected **crack** does not. A crack is a line; its bounding box is mostly
    intact silicon, and more importantly a crack only costs power once it
    *isolates* material. Counting crack boxes at face value is exactly the
    over-prediction that the IEA-PVPS T13 review warns about, so cracks are
    down-weighted by ``crack_area_weight``.

    That weight is the one number here worth calibrating against flash-test
    data; 0.25 is a placeholder, not a measurement.

    Boxes are unioned on a mask rather than summed, so overlapping detections
    of the same defect do not double-count.
    """
    height, width = image_shape[:2]
    total = float(height * width)
    if total <= 0:
        return 0.0

    inactive_mask = np.zeros((height, width), dtype=bool)
    crack_mask = np.zeros((height, width), dtype=bool)

    for detection in detections:
        x1 = int(np.clip(detection.x1, 0, width))
        x2 = int(np.clip(detection.x2, 0, width))
        y1 = int(np.clip(detection.y1, 0, height))
        y2 = int(np.clip(detection.y2, 0, height))
        if x2 <= x1 or y2 <= y1:
            continue

        if detection.class_id in inactive_classes:
            inactive_mask[y1:y2, x1:x2] = True
        else:
            crack_mask[y1:y2, x1:x2] = True

    # Do not let a crack box add area already claimed as inactive.
    crack_only = crack_mask & ~inactive_mask

    fraction = (inactive_mask.sum() + crack_area_weight * crack_only.sum()) / total
    return float(np.clip(fraction, 0.0, 0.95))


def summarise_module(
    detections_per_cell: list[list[Detection]],
    image_shape: tuple[int, int] = (300, 300),
) -> dict[str, object]:
    """Per-cell area fractions plus module-level counts, for reporting."""
    areas = np.array(
        [defect_area_fraction(cell, image_shape) for cell in detections_per_cell]
    )
    counts: dict[str, int] = {name: 0 for name in CLASS_NAMES}
    for cell in detections_per_cell:
        for detection in cell:
            counts[detection.class_name] = counts.get(detection.class_name, 0) + 1

    return {
        "area_fraction_per_cell": areas,
        "cells_with_defects": int(sum(1 for cell in detections_per_cell if cell)),
        "total_detections": int(sum(len(cell) for cell in detections_per_cell)),
        "detections_by_class": counts,
        "worst_cell_index": int(np.argmax(areas)) if len(areas) else -1,
        "worst_cell_area": float(areas.max()) if len(areas) else 0.0,
    }
