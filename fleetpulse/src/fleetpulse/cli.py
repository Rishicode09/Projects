"""Command-line interface: the full workflow without leaving the terminal.

    fleetpulse generate --out data/telemetry.csv
    fleetpulse train    --data data/telemetry.csv --out artifacts
    fleetpulse drift    --data data/telemetry.csv
    fleetpulse serve    --artifacts artifacts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from fleetpulse.config import GeneratorConfig, TrainingConfig, default_artifact_dir
from fleetpulse.data import generate_fleet_telemetry
from fleetpulse.models.anomaly import AnomalyDetector
from fleetpulse.models.train import train_model
from fleetpulse.monitoring import drift_report


def _cmd_generate(args: argparse.Namespace) -> None:
    config = GeneratorConfig(n_vehicles=args.vehicles, n_days=args.days, seed=args.seed)
    telemetry = generate_fleet_telemetry(config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    telemetry.to_csv(args.out, index=False)
    rate = telemetry["failure_within_horizon"].mean()
    print(f"Wrote {len(telemetry):,} rows for {args.vehicles} vehicles to {args.out}")
    print(f"Positive label rate: {rate:.1%}")


def _cmd_train(args: argparse.Namespace) -> None:
    telemetry = pd.read_csv(args.data)
    model = train_model(telemetry, TrainingConfig(seed=args.seed))
    model.save(args.out)
    AnomalyDetector(seed=args.seed).fit(telemetry).save(args.out)
    print(f"Selected model: {model.card['model_name']}")
    print(json.dumps(model.card["metrics"], indent=2))
    print(f"Artifacts written to {args.out}/")


def _cmd_drift(args: argparse.Namespace) -> None:
    telemetry = pd.read_csv(args.data)
    midpoint = telemetry["day"].median()
    report = drift_report(
        telemetry[telemetry["day"] <= midpoint], telemetry[telemetry["day"] > midpoint]
    )
    print(report.to_string(index=False))


def _cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    from fleetpulse.api import create_app

    uvicorn.run(create_app(args.artifacts), host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fleetpulse", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate synthetic fleet telemetry")
    gen.add_argument("--out", type=Path, default=Path("data/telemetry.csv"))
    gen.add_argument("--vehicles", type=int, default=60)
    gen.add_argument("--days", type=int, default=365)
    gen.add_argument("--seed", type=int, default=42)
    gen.set_defaults(func=_cmd_generate)

    train = sub.add_parser("train", help="Train and persist the failure model")
    train.add_argument("--data", type=Path, default=Path("data/telemetry.csv"))
    train.add_argument("--out", type=Path, default=default_artifact_dir())
    train.add_argument("--seed", type=int, default=42)
    train.set_defaults(func=_cmd_train)

    drift = sub.add_parser("drift", help="PSI drift report: first vs second half of the data")
    drift.add_argument("--data", type=Path, default=Path("data/telemetry.csv"))
    drift.set_defaults(func=_cmd_drift)

    serve = sub.add_parser("serve", help="Run the inference API")
    serve.add_argument("--artifacts", type=Path, default=default_artifact_dir())
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
