#!/usr/bin/env python3
"""Fetch the ELPV dataset into ``data/elpv-dataset``.

    python scripts/download_data.py [--dest data/elpv-dataset]

Licence note, because this matters for publication: the ELPV **images** are
CC BY-NC-SA 4.0 (non-commercial, share-alike) while the accompanying code is
Apache-2.0. Cite Buerhop-Lutz et al. 2018, Deitsch et al. 2019 and Deitsch
et al. 2021 in any paper that uses them — the citations are in the upstream
README and in this repo's own README.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY = "https://github.com/zae-bayern/elpv-dataset.git"
EXPECTED_CELL_COUNT = 2624


def clone(dest: Path, depth: int = 1) -> None:
    if shutil.which("git") is None:
        raise SystemExit("git is not installed; install it or download the dataset manually.")

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning {REPOSITORY} -> {dest}")
    subprocess.run(
        ["git", "clone", "--depth", str(depth), REPOSITORY, str(dest)],
        check=True,
    )


def verify(dest: Path) -> int:
    """Confirm the checkout is complete and return the cell count."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from pvdefect.data.elpv import class_distribution, load_index

    frame = load_index(dest)
    print(f"\nFound {len(frame)} annotated cells at {dest}")
    print("\nClass distribution:")
    print(class_distribution(frame).to_string())
    print("\nWafer types:")
    print(frame["wafer_type"].value_counts().to_string())

    if len(frame) != EXPECTED_CELL_COUNT:
        print(
            f"\nWarning: expected {EXPECTED_CELL_COUNT} cells but found {len(frame)}. "
            "Upstream may have changed; check before publishing numbers."
        )
    return len(frame)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path("data/elpv-dataset"))
    parser.add_argument("--force", action="store_true", help="re-clone over an existing checkout")
    args = parser.parse_args()

    dest: Path = args.dest
    if dest.exists() and args.force:
        print(f"Removing existing {dest}")
        shutil.rmtree(dest)

    if not dest.exists():
        clone(dest)
    else:
        print(f"{dest} already exists; verifying (use --force to re-clone)")

    verify(dest)
    print("\nReady. Train with:  python -m pvdefect.train --config configs/default.yaml")


if __name__ == "__main__":
    main()
