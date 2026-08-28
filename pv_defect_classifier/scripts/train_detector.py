#!/usr/bin/env python3
"""Fine-tune an Ultralytics YOLO detector on EL defect boxes.

    python scripts/train_detector.py --data data/yolo/data.yaml --epochs 100

Build the dataset first with ``scripts/build_detection_dataset.py``, and review
the labels before running this — see that script's docstring for why.

Model size: ``yolo11n`` (nano) is the default and is the right choice here.
ELPV is 2,624 cells with at most a few thousand boxes after annotation; a
larger backbone has more parameters than there are labelled objects and will
memorise the training modules rather than generalise to new ones.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pvdefect.detection.detector import DEFAULT_IMAGE_SIZE, DEFAULT_MODEL, train_detector  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=Path("data/yolo/data.yaml"))
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--image-size", type=int, default=DEFAULT_IMAGE_SIZE)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=str, default=None, help="e.g. 0, cpu, mps")
    parser.add_argument("--project", type=str, default="artifacts/detection")
    parser.add_argument("--name", type=str, default="elpv")
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(
            f"{args.data} not found. Build it first:\n"
            "  python scripts/build_detection_dataset.py"
        )

    results = train_detector(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        image_size=args.image_size,
        batch=args.batch,
        project=args.project,
        name=args.name,
        device=args.device,
    )

    weights = Path(args.project) / args.name / "weights" / "best.pt"
    print(f"\nBest weights: {weights}")
    print("Use them with:")
    print(f"  python scripts/analyse_module.py --cells <dir> --detector {weights}")
    return results


if __name__ == "__main__":
    main()
