"""PyTorch dataset for ELPV cells, augmented with Albumentations."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from ..preprocess.cell_prep import DEFAULT_SIZE, preprocess_cell
from .transforms import build_eval_transform, build_train_transform

logger = logging.getLogger(__name__)


class ElpvCellDataset(Dataset):
    """Cell crops with binary functional/cracked labels.

    ``frame`` is a slice of the index built by :func:`elpv.load_index`, so a
    dataset always knows which pseudo-module each sample came from — needed when
    aggregating predictions back to module level for the physics simulation.

    Note the ordering: OpenCV preprocessing runs first and produces the
    3-channel stack, then Albumentations augments that stack. Augmenting the raw
    image first would let brightness jitter feed into CLAHE, which
    re-normalises it straight back out and defeats the point.
    """

    def __init__(
        self,
        frame: pd.DataFrame,
        train: bool = False,
        size: int = DEFAULT_SIZE,
        build_channels: bool = True,
        augmentation_strength: float = 1.0,
        cache_images: bool = True,
    ) -> None:
        self.frame = frame.reset_index(drop=True)
        self.train = train
        self.size = size
        self.build_channels = build_channels
        self.transform = (
            build_train_transform(size, augmentation_strength)
            if train
            else build_eval_transform(size)
        )
        # 2624 cells at 224x224x3 float32 is ~1.5 GB, so cache the decoded
        # grayscale source (300x300 uint8, ~236 MB) and redo the cheap
        # preprocessing per epoch. Keeps augmentation downstream of it.
        self._cache: dict[int, np.ndarray] | None = {} if cache_images else None

    def __len__(self) -> int:
        return len(self.frame)

    def _read_source(self, index: int) -> np.ndarray:
        if self._cache is not None and index in self._cache:
            return self._cache[index]

        path = Path(self.frame.at[index, "path"])
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise FileNotFoundError(f"OpenCV could not decode {path}")

        if self._cache is not None:
            self._cache[index] = image
        return image

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        source = self._read_source(index)
        image = preprocess_cell(source, size=self.size, build_channels=self.build_channels)

        # Albumentations wants uint8 for its photometric ops to behave as
        # documented; convert back to float afterwards.
        augmented = self.transform(image=(image * 255).astype(np.uint8))["image"]
        image = augmented.astype(np.float32) / 255.0

        tensor = torch.from_numpy(np.ascontiguousarray(image.transpose(2, 0, 1)))
        row = self.frame.iloc[index]
        return {
            "image": tensor,
            # float for BCEWithLogitsLoss
            "label": torch.tensor(float(row["label"]), dtype=torch.float32),
            "probability": torch.tensor(float(row["probability"]), dtype=torch.float32),
            "module_id": torch.tensor(int(row.get("module_id", -1)), dtype=torch.long),
            "index": torch.tensor(index, dtype=torch.long),
        }


def build_sampler(frame: pd.DataFrame, cap: float = 4.0) -> WeightedRandomSampler:
    """Oversample the cracked class, with the boost capped.

    Capping matters on a dataset this small: uncapped inverse-frequency
    sampling repeats the minority images often enough that the model memorises
    them instead of generalising. With ``pos_weight`` already in the loss, the
    sampler only needs to close part of the gap.
    """
    counts = frame["label"].value_counts()
    frequency = np.array([counts.get(0, 0), counts.get(1, 0)], dtype=float)
    frequency[frequency == 0] = np.inf

    weights = 1.0 / frequency
    weights = np.minimum(weights / weights[weights > 0].min(), cap)

    sample_weights = weights[frame["label"].to_numpy().astype(int)]
    return WeightedRandomSampler(
        weights=torch.as_tensor(sample_weights, dtype=torch.double),
        num_samples=len(frame),
        replacement=True,
    )


def build_dataloaders(
    splits: dict[str, pd.DataFrame],
    batch_size: int = 32,
    num_workers: int = 4,
    size: int = DEFAULT_SIZE,
    build_channels: bool = True,
    balanced_sampling: bool = True,
    augmentation_strength: float = 1.0,
) -> dict[str, DataLoader]:
    """Wrap each split in a DataLoader; only ``train`` is shuffled and augmented."""
    loaders: dict[str, DataLoader] = {}
    for name, frame in splits.items():
        if len(frame) == 0:
            logger.warning("split %r is empty, skipping", name)
            continue

        is_train = name == "train"
        dataset = ElpvCellDataset(
            frame,
            train=is_train,
            size=size,
            build_channels=build_channels,
            augmentation_strength=augmentation_strength,
        )

        sampler = build_sampler(frame) if (is_train and balanced_sampling) else None
        loaders[name] = DataLoader(
            dataset,
            batch_size=batch_size,
            sampler=sampler,
            shuffle=is_train and sampler is None,
            num_workers=num_workers,
            pin_memory=torch.cuda.is_available(),
            drop_last=is_train and len(frame) > batch_size,
            persistent_workers=num_workers > 0,
        )
    return loaders
