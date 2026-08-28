"""Loading and indexing of the ELPV electroluminescence dataset.

The dataset (zae-bayern/elpv-dataset) contains 2,624 grayscale 300x300 cell
crops extracted from 44 modules, each annotated with a defect *probability* in
{0, 1/3, 2/3, 1} and the wafer type ("mono" or "poly").

**Binary framing.** The raw annotation is the fraction of expert annotators who
marked the cell defective, i.e. four graded levels. This project collapses it to
a binary decision — *functional* vs *cracked* — which is the call a maintenance
workflow actually makes. The threshold is configurable because it is a real
choice, not a detail:

* ``threshold=0.5`` (default) puts the ambiguous 1/3 level on the functional
  side. It trains a model that fires when a clear majority of experts saw a
  defect, so precision is high and hairline cracks are missed.
* ``threshold=0.1`` counts *any* annotator disagreement as cracked. Recall goes
  up, and so do false alarms on cells that three of four experts called clean.

The graded probability is kept in the frame regardless, under ``probability``,
because the physics model consumes a continuous severity and throwing the
gradation away at load time would make that impossible.

One more thing that drives the design: ``labels.csv`` does not expose which
module a cell came from, but rows are ordered module by module. Cells from one
module share a wafer batch, a camera exposure and often the same crack
propagating across neighbours, so a random split leaks. See ``splits.py``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# The four raw annotation levels, in ascending severity.
SEVERITY_LEVELS = (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0)

# Binary task.
NUM_CLASSES = 2
CLASS_NAMES = ("functional", "cracked")

# Any annotator agreement at or above this counts as cracked.
DEFAULT_DEFECT_THRESHOLD = 0.5


@dataclass(frozen=True)
class ElpvSample:
    """One annotated cell crop."""

    path: Path
    probability: float      # raw graded annotation, retained for the physics model
    wafer_type: str
    label: int              # 0 = functional, 1 = cracked
    module_id: int          # pseudo-module, see splits.assign_pseudo_modules


def snap_to_level(probability: float) -> float:
    """Snap a raw annotation onto its nearest of the four canonical levels."""
    return float(min(SEVERITY_LEVELS, key=lambda level: abs(probability - level)))


def find_labels_csv(root: Path) -> Path:
    """Locate ``labels.csv`` inside an elpv-dataset checkout.

    The upstream repository moved the data under ``src/elpv_dataset/data`` in
    2024; older clones and the PyPI package keep it at the top level. We accept
    either, plus a direct path to the file itself.
    """
    root = Path(root)
    if root.is_file() and root.suffix == ".csv":
        return root

    candidates = [
        root / "labels.csv",
        root / "src" / "elpv_dataset" / "data" / "labels.csv",
        root / "elpv_dataset" / "data" / "labels.csv",
        root / "data" / "labels.csv",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    # Last resort: search, but bound the depth so we do not walk a home dir.
    for depth in range(1, 5):
        pattern = "/".join(["*"] * depth) + "/labels.csv"
        for hit in sorted(root.glob(pattern)):
            return hit

    raise FileNotFoundError(
        f"Could not find labels.csv under {root}. Run "
        "`python scripts/download_data.py` to fetch the ELPV dataset."
    )


def load_index(
    root: Path, defect_threshold: float = DEFAULT_DEFECT_THRESHOLD
) -> pd.DataFrame:
    """Read the ELPV annotations into a dataframe of absolute image paths.

    Returns columns ``path``, ``probability`` (graded, 0-1), ``wafer_type`` and
    ``label`` (binary). ``module_id`` is added separately by
    :func:`splits.assign_pseudo_modules` so the raw index stays a faithful
    mirror of the upstream file.
    """
    labels_csv = find_labels_csv(Path(root))
    base_dir = labels_csv.parent

    # Upstream file is whitespace-separated: "images/cell0001.png  1.0  mono"
    frame = pd.read_csv(
        labels_csv,
        sep=r"\s+",
        header=None,
        names=["rel_path", "probability", "wafer_type"],
    )

    frame["path"] = [base_dir / rel for rel in frame["rel_path"]]
    frame["label"] = (frame["probability"] >= defect_threshold).astype(int)
    frame = frame.drop(columns=["rel_path"])

    missing = [p for p in frame["path"] if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} image(s) referenced by {labels_csv} are missing, "
            f"e.g. {missing[0]}. The clone may be incomplete."
        )

    logger.info(
        "Loaded %d ELPV cells from %s at threshold %.2f (functional=%d, cracked=%d)",
        len(frame), labels_csv, defect_threshold,
        int((frame["label"] == 0).sum()), int((frame["label"] == 1).sum()),
    )
    return frame


def class_distribution(frame: pd.DataFrame) -> pd.Series:
    """Counts per binary class, reindexed so an empty class still shows up."""
    return (
        frame["label"]
        .value_counts()
        .reindex(range(NUM_CLASSES), fill_value=0)
        .rename(index=lambda i: CLASS_NAMES[i])
    )


def positive_weight(frame: pd.DataFrame) -> float:
    """``pos_weight`` for ``BCEWithLogitsLoss``: negatives divided by positives.

    At the default threshold ELPV is roughly 1803 functional / 821 cracked, so
    this lands near 2.2 — enough to stop the model defaulting to "functional"
    without the instability that a large weight causes on a small dataset.
    """
    positives = int((frame["label"] == 1).sum())
    negatives = int((frame["label"] == 0).sum())
    if positives == 0:
        logger.warning("No positive samples in this split; pos_weight defaults to 1.")
        return 1.0
    return negatives / positives


def graded_severity(frame: pd.DataFrame) -> np.ndarray:
    """The raw graded annotation, for feeding the physics model directly.

    Use this when you want ground-truth severity rather than a prediction — for
    example when validating the power-loss model against annotated modules.
    """
    return frame["probability"].to_numpy(dtype=float)
