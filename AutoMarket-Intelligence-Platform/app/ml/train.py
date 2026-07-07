"""Train the price prediction model.

Usage (after seeding the database):

    python -m app.ml.train

Loads all listings, tries three regression algorithms, evaluates each on a
held-out test set, and saves the best one (plus its metrics) to app/ml/artifacts/.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import select

from app.database import engine
from app.models import Listing

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "price_model.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

CATEGORICAL = ["make", "model", "fuel_type", "transmission", "seller_type"]
NUMERIC = ["age", "mileage", "engine_size"]
TARGET = "price"


def load_training_data() -> pd.DataFrame:
    """Read all listings from the database and derive the `age` feature."""
    df = pd.read_sql(select(Listing), engine)
    # Age is what actually drives depreciation; the model learns it far more
    # easily than a raw year value like 2019.
    df["age"] = datetime.now(UTC).year - df["year"]
    return df


def build_pipeline(regressor) -> Pipeline:
    """Preprocessing + model in one object, so 'the model' includes its encoding.

    One-hot encoding turns text columns (make, fuel type...) into the 0/1
    columns that regression algorithms require. Bundling it into the pipeline
    means training and prediction can never encode the data differently.
    """
    preprocessing = ColumnTransformer(
        # sparse_output=False: HistGradientBoosting requires a dense array.
        [("categories", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL)],
        remainder="passthrough",  # numeric columns pass straight through
    )
    return Pipeline([("preprocess", preprocessing), ("regressor", regressor)])


def train(model_path: Path = MODEL_PATH, metrics_path: Path = METRICS_PATH) -> dict:
    """Train, compare and save the best model. Returns the saved metrics."""
    df = load_training_data()
    if len(df) < 100:
        raise RuntimeError(
            f"Only {len(df)} listings in the database - seed it first: "
            "python scripts/seed_data.py"
        )

    X = df[CATEGORICAL + NUMERIC]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    candidates = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42),
        "HistGradientBoosting": HistGradientBoostingRegressor(random_state=42),
    }

    results = {}
    fitted = {}
    for name, regressor in candidates.items():
        pipeline = build_pipeline(regressor)
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)
        results[name] = {
            "mae": float(mean_absolute_error(y_test, predictions)),
            "rmse": float(root_mean_squared_error(y_test, predictions)),
            "r2": float(r2_score(y_test, predictions)),
        }
        fitted[name] = pipeline
        print(
            f"{name:22s} MAE £{results[name]['mae']:,.0f}   "
            f"RMSE £{results[name]['rmse']:,.0f}   R² {results[name]['r2']:.3f}"
        )

    best_name = min(results, key=lambda name: results[name]["mae"])
    print(f"\nBest model: {best_name}")

    metrics = {
        "best_model": best_name,
        "trained_at": datetime.now(UTC).isoformat(),
        "training_rows": len(df),
        "test_mae": results[best_name]["mae"],
        "test_rmse": results[best_name]["rmse"],
        "test_r2": results[best_name]["r2"],
        "all_results": results,
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted[best_name], model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"Saved model to {model_path}")
    return metrics


if __name__ == "__main__":
    train()
