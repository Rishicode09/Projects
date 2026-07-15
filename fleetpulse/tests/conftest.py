"""Shared fixtures.

Training even a small model takes a couple of seconds, so the dataset,
trained model, and API client are built once per session and reused.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from fleetpulse.api import create_app
from fleetpulse.config import GeneratorConfig, TrainingConfig
from fleetpulse.data import generate_fleet_telemetry
from fleetpulse.models.anomaly import AnomalyDetector
from fleetpulse.models.train import TrainedModel, train_model

SMALL_CONFIG = GeneratorConfig(n_vehicles=18, n_days=150, seed=7)


@pytest.fixture(scope="session")
def telemetry() -> pd.DataFrame:
    return generate_fleet_telemetry(SMALL_CONFIG)


@pytest.fixture(scope="session")
def trained_model(telemetry: pd.DataFrame) -> TrainedModel:
    return train_model(telemetry, TrainingConfig(seed=7, generator=SMALL_CONFIG))


@pytest.fixture(scope="session")
def artifact_dir(
    telemetry: pd.DataFrame,
    trained_model: TrainedModel,
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    path = tmp_path_factory.mktemp("artifacts")
    trained_model.save(path)
    AnomalyDetector(seed=7).fit(telemetry).save(path)
    return path


@pytest.fixture(scope="session")
def client(artifact_dir: Path):
    with TestClient(create_app(artifact_dir)) as test_client:
        yield test_client
