"""Albumentations pipelines for EL cell images.

Augmentation choices here are constrained by EL physics rather than by what
looks reasonable on natural photographs:

* **Rotation and flips are free.** A cell has no canonical orientation and a
  module can be imaged from either side, so all eight dihedral symmetries are
  label-preserving. Rotation by arbitrary angles is fine too, with reflective
  border padding so no black wedge appears at the corners (a black wedge reads
  as an inactive region to both the classifier and the area estimator).

* **Contrast and brightness jitter is the important one.** EL intensity depends
  on injection current and camera integration time, both set per module. Two
  photographs of the same module at different exposures must map to the same
  label, and jittering them during training is what enforces that.

* **Blur is capped hard.** The difference between a healthy cell and a mildly
  cracked one is a hairline feature a few pixels wide. Aggressive blur destroys
  exactly the signal we are trying to learn, so it is limited to a 3-pixel
  kernel and a low probability.

* **No colour ops.** Single-channel near-infrared sensor; hue and saturation
  are meaningless.

* **No large translations or crops.** ELPV crops are already cell-aligned, and
  edge cracks live at the cell border — shifting them out of frame teaches the
  model to ignore the region where a third of the defects are.
"""

from __future__ import annotations

import albumentations as A

from ..preprocess.cell_prep import DEFAULT_SIZE


def build_train_transform(size: int = DEFAULT_SIZE, strength: float = 1.0) -> A.Compose:
    """Training augmentation.

    ``strength`` scales the aggressiveness of the photometric ops; use <1 if you
    see the model underfitting the rare defect classes.
    """
    return A.Compose(
        [
            A.Resize(size, size, interpolation=1),
            # Dihedral symmetries: label-preserving for a solar cell.
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.RandomRotate90(p=0.5),
            # Small free rotation for residual misalignment after cell cropping.
            A.Affine(
                rotate=(-12, 12),
                scale=(0.95, 1.05),
                translate_percent=(-0.02, 0.02),
                border_mode=4,  # BORDER_REFLECT_101: no black corners
                p=0.5,
            ),
            # The exposure-invariance driver.
            A.RandomBrightnessContrast(
                brightness_limit=0.25 * strength,
                contrast_limit=0.30 * strength,
                p=0.8,
            ),
            A.RandomGamma(gamma_limit=(80, 120), p=0.3),
            # Sensor read noise: EL cameras run at high gain.
            A.GaussNoise(std_range=(0.02, 0.08), p=0.3),
            # Capped: anything stronger erases hairline cracks.
            A.OneOf([A.GaussianBlur(blur_limit=(3, 3)), A.MotionBlur(blur_limit=3)], p=0.15),
        ]
    )


def build_eval_transform(size: int = DEFAULT_SIZE) -> A.Compose:
    """Deterministic resize for validation, test and inference."""
    return A.Compose([A.Resize(size, size, interpolation=1)])


def build_detection_train_transform(size: int = 640) -> A.Compose:
    """Augmentation for the detector, with bounding boxes carried along.

    Ultralytics applies its own augmentation during training, so this exists for
    offline dataset expansion — generating extra annotated frames *before*
    handing the directory to YOLO — rather than as an inline replacement.
    Geometric ops are restricted to the ones that keep axis-aligned boxes
    axis-aligned; a free rotation would need box re-fitting and inflates every
    box around a diagonal crack.
    """
    return A.Compose(
        [
            A.LongestMaxSize(max_size=size),
            A.PadIfNeeded(size, size, border_mode=4),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.RandomRotate90(p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.25, contrast_limit=0.30, p=0.8),
            A.GaussNoise(std_range=(0.02, 0.08), p=0.3),
        ],
        bbox_params=A.BboxParams(
            format="yolo",
            label_fields=["class_labels"],
            # Drop boxes that augmentation pushed mostly out of frame.
            min_visibility=0.4,
        ),
    )
