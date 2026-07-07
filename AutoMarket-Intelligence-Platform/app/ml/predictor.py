"""Load the trained model and make price predictions."""

import json
from datetime import UTC, datetime
from functools import lru_cache

import joblib
import pandas as pd

from app.ml.train import METRICS_PATH, MODEL_PATH


class ModelNotTrainedError(Exception):
    """Raised when a prediction is requested before the model has been trained."""


@lru_cache
def get_model():
    """Load the model from disk once and reuse it for every request."""
    if not MODEL_PATH.exists():
        raise ModelNotTrainedError("No trained model found. Run: python -m app.ml.train")
    return joblib.load(MODEL_PATH)


@lru_cache
def get_metrics() -> dict:
    """Load the saved evaluation metrics for the current model."""
    if not METRICS_PATH.exists():
        raise ModelNotTrainedError("No model metrics found. Run: python -m app.ml.train")
    return json.loads(METRICS_PATH.read_text())


def predict_price(
    make: str,
    model: str,
    year: int,
    mileage: int,
    fuel_type: str,
    transmission: str,
    engine_size: float,
    seller_type: str = "Dealer",
) -> int:
    """Estimate the fair price (GBP) for a car with these details."""
    features = pd.DataFrame(
        [
            {
                "make": make,
                "model": model,
                "age": datetime.now(UTC).year - year,
                "mileage": mileage,
                "fuel_type": fuel_type,
                "transmission": transmission,
                "engine_size": engine_size,
                "seller_type": seller_type,
            }
        ]
    )
    estimate = get_model().predict(features)[0]
    return max(0, int(round(estimate, -1)))
