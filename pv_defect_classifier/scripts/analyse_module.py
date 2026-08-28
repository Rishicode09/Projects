#!/usr/bin/env python3
"""End-to-end: EL images of a module -> annual energy loss.

Two input modes:

    # a directory of pre-cropped cells (ELPV-style)
    python scripts/analyse_module.py --cells path/to/module_cells/

    # one photograph of a whole module, cropped here with OpenCV
    python scripts/analyse_module.py --module-image module_01.png --rows 6 --columns 10

This is the script that closes the loop the rest of the repo is built around.
Everything before it produces a per-cell defect estimate; everything after it
turns those into a number a maintenance planner can act on.

Cell ordering matters. Cells are taken in reading order (or filename order) and
assigned to string positions in that order, so a serpentine-wired module needs
reordering first — it changes which cells share a bypass diode, and therefore
changes the answer.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pvdefect.physics.cell_model import ModuleSpec  # noqa: E402
from pvdefect.physics.degradation import DegradationModel  # noqa: E402
from pvdefect.physics.energy import revenue_impact, simulate_annual_energy  # noqa: E402
from pvdefect.physics.weather import (  # noqa: E402
    SiteSpec,
    plane_of_array,
    typical_meteorological_year,
)
from pvdefect.preprocess.cell_prep import (  # noqa: E402
    estimate_inactive_area_fraction,
    preprocess_cell,
)
from pvdefect.preprocess.module_crop import crop_module  # noqa: E402

logger = logging.getLogger(__name__)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def load_cells_from_directory(directory: Path) -> tuple[list[str], list[np.ndarray]]:
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    if not paths:
        raise SystemExit(f"No images found in {directory}")

    images = []
    for path in paths:
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise SystemExit(f"Could not decode {path}")
        images.append(image)
    return [p.name for p in paths], images


def load_cells_from_module(path: Path, rows: int, columns: int) -> tuple[list[str], list[np.ndarray]]:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise SystemExit(f"Could not decode {path}")

    grid = crop_module(image, rows=rows, columns=columns)
    names = [f"r{r}c{c}" for r in range(grid.rows) for c in range(grid.columns)]
    if grid.corners is None:
        logger.warning(
            "Perspective correction was skipped (module outline not found confidently). "
            "Cell crops may be misaligned; check with --save-crops."
        )
    return names, grid.cells


def classify(images: list[np.ndarray], checkpoint: Path | None, threshold: float) -> np.ndarray:
    """Crack probability per cell, from the CNN if available."""
    if checkpoint is None or not checkpoint.exists():
        print("No classifier checkpoint — falling back to the image-only area estimator.")
        print("This is a weak proxy; train a model for anything you intend to publish.\n")
        return np.array([estimate_inactive_area_fraction(image) for image in images])

    import torch

    from pvdefect.config import Config
    from pvdefect.models.classifier import build_model

    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    config = Config.from_dict(payload["config"])
    model = build_model(config.model)
    model.load_state_dict(payload["model_state"])
    model.eval()

    batch = np.stack(
        [
            preprocess_cell(
                image, size=config.data.image_size, build_channels=config.data.build_channels
            ).transpose(2, 0, 1)
            for image in images
        ]
    )
    with torch.no_grad():
        prediction = model.predict(torch.from_numpy(batch).float(), threshold=threshold)
    return prediction["probability"].numpy()


def detect(images: list[np.ndarray], weights: Path | None, confidence: float,
           crack_weight: float) -> np.ndarray | None:
    """Measured defect area fraction per cell, or ``None`` if no detector."""
    if weights is None or not Path(weights).exists():
        return None

    from pvdefect.detection.detector import defect_area_fraction, detect_cells, load_detector

    model = load_detector(weights)
    per_cell = detect_cells(model, images, confidence=confidence)
    return np.array(
        [
            defect_area_fraction(dets, image.shape[:2], crack_area_weight=crack_weight)
            for dets, image in zip(per_cell, images)
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--cells", type=Path, help="directory of pre-cropped cell images")
    source.add_argument("--module-image", type=Path, help="one photograph of a whole module")

    parser.add_argument("--rows", type=int, default=6, help="cell rows (module-image mode)")
    parser.add_argument("--columns", type=int, default=10, help="cell columns (module-image mode)")
    parser.add_argument("--checkpoint", type=Path, default=Path("artifacts/model.pt"))
    parser.add_argument("--detector", type=Path, default=None,
                        help="YOLO weights; enables measured defect area")
    parser.add_argument("--threshold", type=float, default=0.5, help="crack decision threshold")
    parser.add_argument("--detector-confidence", type=float, default=0.25)
    parser.add_argument("--crack-area-weight", type=float, default=0.25)
    parser.add_argument("--latitude", type=float, default=49.60)
    parser.add_argument("--longitude", type=float, default=11.01)
    parser.add_argument("--timezone", type=str, default="Europe/Berlin")
    parser.add_argument("--tilt", type=float, default=30.0)
    parser.add_argument("--azimuth", type=float, default=180.0)
    parser.add_argument("--tariff", type=float, default=0.12, help="currency per kWh")
    parser.add_argument("--modules", type=int, default=1, help="how many identical modules")
    parser.add_argument("--offline", action="store_true", help="skip PVGIS, use clear-sky")
    parser.add_argument("--damage-scaling", type=float, default=1.0,
                        help="degradation severity; sweep 0.5-1.5 to bracket the answer")
    parser.add_argument("--save-crops", type=Path, default=None,
                        help="write the cell crops here, to check the cropping visually")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    if args.cells:
        names, images = load_cells_from_directory(args.cells)
    else:
        names, images = load_cells_from_module(args.module_image, args.rows, args.columns)

    if args.save_crops:
        args.save_crops.mkdir(parents=True, exist_ok=True)
        for name, image in zip(names, images):
            cv2.imwrite(str(args.save_crops / f"{name}.png"), image)
        print(f"Wrote {len(images)} crops to {args.save_crops}")

    probabilities = classify(images, args.checkpoint, args.threshold)
    detected_areas = detect(images, args.detector, args.detector_confidence,
                            args.crack_area_weight)

    print(f"\nAnalysed {len(images)} cells")
    print(f"Cells above threshold {args.threshold:.2f}: "
          f"{int((probabilities >= args.threshold).sum())}")

    order = np.argsort(probabilities)[::-1][:5]
    print("\nWorst cells:")
    for rank, index in enumerate(order, start=1):
        area = f"  measured area {detected_areas[index]:.1%}" if detected_areas is not None else ""
        print(f"  {rank}. {names[index]:<20s} P(cracked) {probabilities[index]:.3f}{area}")

    if detected_areas is None:
        print("\nNo detector weights supplied — defect area comes from the severity lookup")
        print("table rather than a measurement. Pass --detector to improve this.")

    site = SiteSpec(
        latitude=args.latitude, longitude=args.longitude, timezone=args.timezone,
        surface_tilt=args.tilt, surface_azimuth=args.azimuth,
    )
    poa = plane_of_array(site, typical_meteorological_year(site, use_network=not args.offline))

    module = ModuleSpec.default()
    degradation = DegradationModel().with_uncertainty(args.damage_scaling)
    result = simulate_annual_energy(
        probabilities, poa, module, degradation, detected_areas=detected_areas
    )

    print("\n" + result.summary())

    impact = revenue_impact(result, args.modules, args.tariff, years=10)
    print(
        f"\nAcross {args.modules} module(s): "
        f"{impact['annual_energy_loss_kwh']:.0f} kWh/yr "
        f"= {impact['annual_revenue_loss']:.0f}/yr "
        f"({impact['cumulative_revenue_loss']:.0f} over 10 years)"
    )

    if poa.attrs.get("synthetic", True):
        print(
            "\nNote: synthetic clear-sky weather. Relative losses are meaningful; "
            "absolute yield is over-stated because there are no clouds."
        )
    print(
        "Note: the defect->damage mapping is uncalibrated. Re-run with "
        "--damage-scaling 0.5 and 1.5 to see the spread before acting on the figure."
    )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(
                {
                    "cells": [
                        {
                            "name": name,
                            "crack_probability": float(probability),
                            "detected_area": (
                                float(detected_areas[i]) if detected_areas is not None else None
                            ),
                        }
                        for i, (name, probability) in enumerate(zip(names, probabilities))
                    ],
                    "stc_power_loss_fraction": result.stc_power_loss_fraction,
                    "annual_energy_loss_fraction": result.annual_energy_loss_fraction,
                    "annual_energy_loss_kwh": result.annual_energy_loss_kwh,
                    "annual_energy_healthy_kwh": result.annual_energy_healthy_kwh,
                    "weather_source": result.weather_source,
                    "damage_scaling": args.damage_scaling,
                    "used_detector": detected_areas is not None,
                    **impact,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
