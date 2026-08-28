#!/usr/bin/env python3
"""Build a YOLO dataset from ELPV, with bootstrap box proposals.

    python scripts/build_detection_dataset.py --dest data/yolo --preview 24

**Read this before training on the output.** ELPV has no bounding boxes. This
script proposes them from the classical crack response in
``preprocess.cell_prep``, on cells the annotation already calls cracked. The
proposals are a labelling *accelerator*, not ground truth — the generator has no
concept of a crack and will happily box grain boundaries and busbar shadows.

The intended workflow:

1. Run this to get images, proposed labels, and a preview grid.
2. Look at the preview. If the proposals are mostly junk on your imagery, run
   again with ``--no-proposals`` and annotate from scratch instead.
3. Correct the labels in a tool that reads YOLO format (Label Studio, CVAT,
   labelImg all do).
4. Train: ``python scripts/train_detector.py --data data/yolo/data.yaml``

Skipping step 3 gives you a detector that has learned to imitate a threshold.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pvdefect.data.elpv import load_index  # noqa: E402
from pvdefect.data.splits import assign_pseudo_modules, split_by_module  # noqa: E402
from pvdefect.detection.dataset import build_yolo_dataset  # noqa: E402
from pvdefect.detection.pseudo_label import draw_proposals, propose_regions  # noqa: E402


def write_preview(frame, destination: Path, count: int, columns: int = 6) -> None:
    """Grid of proposals on defective cells, so you can judge quality at a glance."""
    defective = frame[frame["label"] == 1].head(count)
    if defective.empty:
        print("No defective cells to preview.")
        return

    tiles = []
    for _, row in defective.iterrows():
        image = cv2.imread(str(row["path"]), cv2.IMREAD_UNCHANGED)
        if image is None:
            continue
        drawn = draw_proposals(image, propose_regions(image))
        tiles.append(cv2.resize(drawn, (200, 200)))

    if not tiles:
        return

    rows = []
    for start in range(0, len(tiles), columns):
        chunk = tiles[start : start + columns]
        while len(chunk) < columns:
            chunk.append(np.zeros_like(tiles[0]))
        rows.append(np.hstack(chunk))

    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), np.vstack(rows))
    print(f"Wrote proposal preview to {destination}  <- inspect this before training")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, default=Path("data/elpv-dataset"))
    parser.add_argument("--dest", type=Path, default=Path("data/yolo"))
    parser.add_argument("--defect-threshold", type=float, default=0.5)
    parser.add_argument("--no-proposals", action="store_true",
                        help="write empty label files for annotation from scratch")
    parser.add_argument("--label-all", action="store_true",
                        help="also propose boxes on functional cells (not recommended)")
    parser.add_argument("--preview", type=int, default=24,
                        help="how many cells to render in the preview grid (0 to skip)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    frame = assign_pseudo_modules(load_index(args.data_root, args.defect_threshold))
    splits = split_by_module(frame, seed=args.seed)

    data_yaml = build_yolo_dataset(
        splits,
        args.dest,
        generate_proposals=not args.no_proposals,
        only_label_defective=not args.label_all,
        overwrite=args.overwrite,
    )
    print(f"\nWrote {data_yaml}")

    if args.preview and not args.no_proposals:
        write_preview(splits["train"], args.dest / "proposal_preview.png", args.preview)

    print("\nNext: review the labels in a YOLO-format annotation tool, then")
    print(f"  python scripts/train_detector.py --data {data_yaml}")


if __name__ == "__main__":
    main()
