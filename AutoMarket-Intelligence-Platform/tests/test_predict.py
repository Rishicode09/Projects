"""Tests for the ML predictor and the /api/predict endpoint.

A small model is trained once (on the in-memory test data written to a
temporary file) so these tests exercise the real train -> save -> load ->
predict path without touching the repository's artifacts.
"""

import pytest
from fastapi.testclient import TestClient

from app.ml import predictor


@pytest.fixture(scope="module")
def trained_model(tmp_path_factory):
    """Train a real (small) model into a temp directory and point the app at it."""
    import pandas as pd

    from app.data_generator import generate_listings
    from app.ml import train as train_module

    tmp = tmp_path_factory.mktemp("model")
    model_path = tmp / "price_model.joblib"
    metrics_path = tmp / "metrics.json"

    # Train on generated data directly (no database needed for this test).
    df = pd.DataFrame(generate_listings(count=500, seed=5))
    df["age"] = 2026 - df["year"]

    original_loader = train_module.load_training_data
    train_module.load_training_data = lambda: df
    try:
        train_module.train(model_path=model_path, metrics_path=metrics_path)
    finally:
        train_module.load_training_data = original_loader

    # Point the predictor at the temp artifacts and clear its caches.
    original_paths = (predictor.MODEL_PATH, predictor.METRICS_PATH)
    predictor.MODEL_PATH, predictor.METRICS_PATH = model_path, metrics_path
    predictor.get_model.cache_clear()
    predictor.get_metrics.cache_clear()
    yield
    predictor.MODEL_PATH, predictor.METRICS_PATH = original_paths
    predictor.get_model.cache_clear()
    predictor.get_metrics.cache_clear()


def test_predicts_a_plausible_price(trained_model) -> None:
    price = predictor.predict_price(
        make="Volkswagen",
        model="Golf",
        year=2021,
        mileage=40_000,
        fuel_type="Petrol",
        transmission="Manual",
        engine_size=1.5,
    )
    assert 3_000 < price < 40_000


def test_newer_car_costs_more_than_older_one(trained_model) -> None:
    def golf(year: int, mileage: int) -> int:
        return predictor.predict_price(
            make="Volkswagen",
            model="Golf",
            year=year,
            mileage=mileage,
            fuel_type="Petrol",
            transmission="Manual",
            engine_size=1.5,
        )

    assert golf(year=2024, mileage=15_000) > golf(year=2012, mileage=110_000)


def test_predict_endpoint(trained_model, client: TestClient) -> None:
    response = client.post(
        "/api/predict",
        json={
            "make": "BMW",
            "model": "3 Series",
            "year": 2020,
            "mileage": 45_000,
            "fuel_type": "Petrol",
            "transmission": "Automatic",
            "engine_size": 2.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["estimated_price"] > 0
    assert body["currency"] == "GBP"
    assert body["model_mae"] > 0


def test_predict_endpoint_validates_input(client: TestClient) -> None:
    response = client.post("/api/predict", json={"make": "BMW"})  # missing fields
    assert response.status_code == 422
