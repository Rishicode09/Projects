"""Build an Ultralytics-format dataset directory from ELPV cells.

YOLO expects a rigid layout:

    root/
      images/train/xxx.png     labels/train/xxx.txt
      images/val/yyy.png       labels/val/yyy.txt
      data.yaml

Two details that are easy to get wrong and expensive to debug:

1. **Every image needs a label file**, including negatives. A cell with no
   defects gets an *empty* ``.txt``, not a missing one — missing files are
   treated as unlabelled and silently skipped, so your background class
   disappears and the detector over-fires.

2. **The split must stay module-aware**, exactly as for the classifier. The
   same leakage argument applies with more force here: two crops of the same
   crack in adjacent cells landing on opposite sides of the split is close to
   testing on training data.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import cv2
import pandas as pd
import yaml

from ..preprocess.cell_prep import to_grayscale_float
from .pseudo_label import CLASS_NAMES, propose_regions, proposals_to_yolo_lines

logger = logging.getLogger(__name__)


def write_data_yaml(root: Path, class_names: tuple[str, ...] = CLASS_NAMES) -> Path:
    """Write the ``data.yaml`` that Ultralytics reads."""
    root = Path(root).resolve()
    payload = {
        "path": str(root),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {index: name for index, name in enumerate(class_names)},
    }
    destination = root / "data.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
    return destination


def build_yolo_dataset(
    splits: dict[str, pd.DataFrame],
    root: Path,
    generate_proposals: bool = True,
    only_label_defective: bool = True,
    overwrite: bool = False,
) -> Path:
    """Materialise a YOLO dataset from ELPV splits.

    Parameters
    ----------
    splits:
        ``{"train": frame, "val": frame, ...}`` from :mod:`data.splits`.
    generate_proposals:
        Write bootstrap boxes from the classical detector. With ``False`` you
        get images plus empty label files — the right choice if you are
        annotating from scratch in an external tool.
    only_label_defective:
        Propose boxes only on cells the annotation calls cracked. Strongly
        recommended: running the proposal generator on functional cells is how
        you teach a detector that grain boundaries are defects.

    Returns the path to ``data.yaml``.
    """
    root = Path(root)
    if root.exists() and overwrite:
        shutil.rmtree(root)

    statistics = {"images": 0, "boxes": 0, "empty": 0}

    for split_name, frame in splits.items():
        image_dir = root / "images" / split_name
        label_dir = root / "labels" / split_name
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)

        for _, row in frame.iterrows():
            source = Path(row["path"])
            image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
            if image is None:
                logger.warning("Skipping undecodable %s", source)
                continue

            # YOLO backbones expect 3-channel input; write the grayscale cell
            # replicated rather than the preprocessed stack, so a human
            # reviewer sees what the camera saw.
            gray = (to_grayscale_float(image) * 255).astype("uint8")
            colour = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            stem = source.stem
            cv2.imwrite(str(image_dir / f"{stem}.png"), colour)
            statistics["images"] += 1

            lines: list[str] = []
            is_defective = int(row["label"]) == 1
            if generate_proposals and (is_defective or not only_label_defective):
                regions = propose_regions(image)
                lines = proposals_to_yolo_lines(regions, gray.shape[1], gray.shape[0])
                statistics["boxes"] += len(lines)

            # Always write the file, even when empty — see module docstring.
            (label_dir / f"{stem}.txt").write_text("\n".join(lines), encoding="utf-8")
            if not lines:
                statistics["empty"] += 1

    data_yaml = write_data_yaml(root)
    logger.info(
        "Wrote %d images, %d proposed boxes, %d empty labels to %s",
        statistics["images"], statistics["boxes"], statistics["empty"], root,
    )
    if statistics["boxes"]:
        logger.warning(
            "Boxes are UNREVIEWED proposals from a classical detector. Review them in a "
            "labelling tool before training, or the detector will learn its mistakes."
        )
    return data_yaml
