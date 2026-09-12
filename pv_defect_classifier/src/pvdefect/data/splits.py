"""Leakage-aware train/val/test splitting for ELPV.

Why this file exists at all: the headline accuracies you see quoted for ELPV
vary by more than 10 points depending on how the split was made, and most of
that gap is leakage rather than modelling. Cells cropped from the same module
share a wafer batch, an EL exposure, a busbar layout, and frequently the same
crack running across neighbouring cells. Put one half of a cracked cell pair in
train and the other in test and you are measuring memorisation.

The upstream ``labels.csv`` does not publish module IDs, so we cannot do a
perfect module-wise split. What we can do is exploit the fact that rows are
ordered module by module, and cut the sequence into contiguous pseudo-modules.
This is an approximation: it removes the dominant "same module, adjacent cell"
leak, but a pseudo-module boundary that lands mid-module still lets two cells
of one real module fall on opposite sides of the split.

Report which split policy you used whenever you quote a number from this repo.
"""

from __future__ import annotations

import logging
from typing import Iterator

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold

logger = logging.getLogger(__name__)

# Most modules in the ELPV set are 60-cell (6x10) laminates; a few are 72-cell.
# 60 is the safest chunk size: it under-segments 72-cell modules rather than
# splitting a 60-cell one across two pseudo-modules.
DEFAULT_CELLS_PER_MODULE = 60


def assign_pseudo_modules(
    frame: pd.DataFrame,
    cells_per_module: int = DEFAULT_CELLS_PER_MODULE,
) -> pd.DataFrame:
    """Add a ``module_id`` column by chunking contiguous same-wafer-type runs.

    Wafer type ("mono"/"poly") changes only at real module boundaries, so every
    type transition is a guaranteed cut. Within a run of one type we cut every
    ``cells_per_module`` rows.
    """
    frame = frame.copy()
    wafer = frame["wafer_type"].to_numpy()

    # A new run starts wherever the wafer type differs from the previous row.
    run_starts = np.flatnonzero(wafer[1:] != wafer[:-1]) + 1
    run_id = np.zeros(len(frame), dtype=int)
    run_id[run_starts] = 1
    run_id = np.cumsum(run_id)

    module_id = np.empty(len(frame), dtype=int)
    next_id = 0
    for run in np.unique(run_id):
        (positions,) = np.nonzero(run_id == run)
        # Chunk this run into ceil(len/cells_per_module) pseudo-modules of
        # near-equal size, so a 70-cell run becomes 35+35 rather than 60+10.
        n_chunks = max(1, int(np.ceil(len(positions) / cells_per_module)))
        for chunk, chunk_positions in enumerate(np.array_split(positions, n_chunks)):
            module_id[chunk_positions] = next_id + chunk
        next_id += n_chunks

    frame["module_id"] = module_id
    logger.info(
        "Assigned %d pseudo-modules over %d cells (median size %.0f)",
        frame["module_id"].nunique(),
        len(frame),
        frame.groupby("module_id").size().median(),
    )
    return frame


def split_by_module(
    frame: pd.DataFrame,
    val_fraction: float = 0.15,
    test_fraction: float = 0.15,
    seed: int = 0,
) -> dict[str, pd.DataFrame]:
    """Split into train/val/test with no pseudo-module spanning two subsets.

    Stratification is best-effort: whole modules move together, so the class
    balance of each subset can only approximate the global one.
    """
    if not 0 < val_fraction + test_fraction < 1:
        raise ValueError("val_fraction + test_fraction must lie in (0, 1)")

    frame = frame if "module_id" in frame.columns else assign_pseudo_modules(frame)
    rng = np.random.default_rng(seed)

    # Rank modules by mean severity, then deal them round-robin into buckets.
    # This spreads the rare severe-defect modules across all three subsets far
    # more evenly than a random shuffle of module IDs does.
    module_severity = frame.groupby("module_id")["label"].mean().sort_values()
    modules = module_severity.index.to_numpy()
    # Break ties randomly so the ordering is not an artefact of module ID.
    jitter = rng.permutation(len(modules))
    order = np.lexsort((jitter, module_severity.to_numpy()))
    modules = modules[order]

    n_modules = len(modules)
    n_test = max(1, int(round(test_fraction * n_modules)))
    n_val = max(1, int(round(val_fraction * n_modules)))
    if n_test + n_val >= n_modules:
        raise ValueError(
            f"Only {n_modules} pseudo-modules available; reduce the val/test "
            "fractions or the cells_per_module chunk size."
        )

    # Deal every k-th module to val/test so both stay severity-balanced.
    test_stride = n_modules / n_test
    val_stride = n_modules / n_val
    test_ids = {modules[min(int(i * test_stride), n_modules - 1)] for i in range(n_test)}
    val_ids = set()
    for i in range(n_val):
        # Offset by half a stride to avoid colliding with the test picks.
        idx = min(int((i + 0.5) * val_stride), n_modules - 1)
        candidate = modules[idx]
        step = 0
        while candidate in test_ids or candidate in val_ids:
            step += 1
            idx = (idx + step) % n_modules
            candidate = modules[idx]
        val_ids.add(candidate)

    subsets = {
        "test": frame[frame["module_id"].isin(test_ids)],
        "val": frame[frame["module_id"].isin(val_ids)],
        "train": frame[~frame["module_id"].isin(test_ids | val_ids)],
    }
    for name, subset in subsets.items():
        logger.info(
            "split %-5s: %4d cells / %2d modules / mean severity %.2f",
            name,
            len(subset),
            subset["module_id"].nunique(),
            subset["label"].mean(),
        )
    return {k: subsets[k] for k in ("train", "val", "test")}


def split_random(
    frame: pd.DataFrame,
    val_fraction: float = 0.15,
    test_fraction: float = 0.15,
    seed: int = 0,
) -> dict[str, pd.DataFrame]:
    """Stratified split that ignores module membership.

    Provided *only* so you can measure the leakage gap against
    :func:`split_by_module`. Do not report numbers from this split as if they
    were generalisation estimates.
    """
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(frame))
    shuffled = frame.iloc[indices].reset_index(drop=True)

    n_test = int(round(test_fraction * len(shuffled)))
    n_val = int(round(val_fraction * len(shuffled)))
    return {
        "train": shuffled.iloc[n_test + n_val :],
        "val": shuffled.iloc[n_test : n_test + n_val],
        "test": shuffled.iloc[:n_test],
    }


def cross_validation_folds(
    frame: pd.DataFrame,
    n_splits: int = 5,
    group_aware: bool = True,
    seed: int = 0,
) -> Iterator[tuple[pd.DataFrame, pd.DataFrame]]:
    """Yield ``(train, val)`` folds for repeated-measurement error bars.

    With ~44 real modules, single-split numbers on ELPV carry several points of
    noise. Cross-validate before claiming one architecture beats another.
    """
    frame = frame if "module_id" in frame.columns else assign_pseudo_modules(frame)
    labels = frame["label"].to_numpy()

    if group_aware:
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        iterator = splitter.split(frame, labels, groups=frame["module_id"].to_numpy())
    else:
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        iterator = splitter.split(frame, labels)

    for train_idx, val_idx in iterator:
        yield frame.iloc[train_idx], frame.iloc[val_idx]
