#!/usr/bin/env python3
"""End-to-end: a directory of EL cell crops -> annual energy loss for that module.

    python scripts/analyse_module.py --images path/to/module_cells/ \
        --checkpoint artifacts/model.pt

This is the script that closes the loop the rest of the repo is built around.
Everything before it produces a severity per cell; everything after it turns
those severities into a number a maintenance planner can act on.

Cell ordering matters: the files are sorted by name and assigned to string
positions in that order, so name them in the module's physical series order
(``cell_01.png`` … ``cell_60.png``). Getting the order wrong changes which
cells share a bypass diode, and therefore changes the answer.

Without ``--checkpoint`` the script falls back to the image-only inactive-area
estimator, which is much weaker but needs no trained model.
"""

from __future__ import annotations

import argparse
import json
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

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def load_cells(directory: Path) -> tuple[list[Path], list[np.ndarray]]:
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    if not paths:
        raise SystemExit(f"No images found in {directory}")

    images = []
    for path in paths:
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise SystemExit(f"Could not decode {path}")
        images.append(image)
    return paths, images


def predict_severities(images: list[np.ndarray], checkpoint: Path | None) -> np.ndarray:
    """Severity per cell, from the CNN if available or the dark-area proxy if not."""
    if checkpoint is None or not checkpoint.exists():
        print("No checkpoint supplied — falling back to the image-only area estimator.")
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
        prediction = model.predict(torch.from_numpy(batch).float())
    return prediction["severity"].numpy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True, help="directory of cell crops")
    parser.add_argument("--checkpoint", type=Path, default=Path("artifacts/model.pt"))
    parser.add_argument("--latitude", type=float, default=49.60)
    parser.add_argument("--longitude", type=float, default=11.01)
    parser.add_argument("--timezone", type=str, default="Europe/Berlin")
    parser.add_argument("--tilt", type=float, default=30.0)
    parser.add_argument("--azimuth", type=float, default=180.0)
    parser.add_argument("--tariff", type=float, default=0.12, help="currency per kWh")
    parser.add_argument("--modules", type=int, default=1, help="how many identical modules")
    parser.add_argument("--offline", action="store_true", help="skip PVGIS, use clear-sky")
    parser.add_argument("--damage-scaling", type=float, default=1.0,
                        help="degradation model severity; sweep 0.5-1.5 to bracket")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    paths, images = load_cells(args.images)
    severities = predict_severities(images, args.checkpoint)

    print(f"Analysed {len(paths)} cells from {args.images}")
    worst = np.argsort(severities)[::-1][:5]
    print("\nWorst cells:")
    for rank, index in enumerate(worst, start=1):
        print(f"  {rank}. {paths[index].name:<24s} severity {severities[index]:.3f}")

    site = SiteSpec(
        latitude=args.latitude, longitude=args.longitude, timezone=args.timezone,
        surface_tilt=args.tilt, surface_azimuth=args.azimuth,
    )
    poa = plane_of_array(site, typical_meteorological_year(site, use_network=not args.offline))

    module = ModuleSpec.default()
    degradation = DegradationModel().with_uncertainty(args.damage_scaling)
    result = simulate_annual_energy(severities, poa, module, degradation)

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
        "Note: the severity->damage mapping is uncalibrated. Re-run with "
        "--damage-scaling 0.5 and 1.5 to see the spread before acting on the figure."
    )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(
                {
                    "cells": [
                        {"file": p.name, "severity": float(s)}
                        for p, s in zip(paths, severities)
                    ],
                    "stc_power_loss_fraction": result.stc_power_loss_fraction,
                    "annual_energy_loss_fraction": result.annual_energy_loss_fraction,
                    "annual_energy_loss_kwh": result.annual_energy_loss_kwh,
                    "annual_energy_healthy_kwh": result.annual_energy_healthy_kwh,
                    "weather_source": result.weather_source,
                    "damage_scaling": args.damage_scaling,
                    **impact,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
