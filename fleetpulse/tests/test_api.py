import pandas as pd
import pytest

from fleetpulse.api.schemas import MIN_HISTORY_DAYS
from fleetpulse.config import SENSOR_COLUMNS


def _history_payload(telemetry: pd.DataFrame, vehicle_id: str, n_days: int = 20) -> dict:
    """Build a /predict payload from the last n_days of a simulated vehicle."""
    rows = telemetry[telemetry["vehicle_id"] == vehicle_id].sort_values("day").tail(n_days)
    readings = [
        {"day": int(r["day"]), "mileage_km": float(r["mileage_km"])}
        | {col: float(r[col]) for col in SENSOR_COLUMNS}
        for _, r in rows.iterrows()
    ]
    first = rows.iloc[0]
    return {
        "vehicle_id": vehicle_id,
        "vehicle_type": str(first["vehicle_type"]),
        "vehicle_age_years": float(first["vehicle_age_years"]),
        "readings": readings,
    }


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_loaded": True}


def test_model_info(client):
    body = client.get("/model/info").json()
    assert body["model_name"] in {"logistic_regression", "hist_gradient_boosting"}
    assert 0 <= body["threshold"] <= 1
    assert "pr_auc" in body["metrics"]


def test_predict_returns_valid_prediction(client, telemetry):
    payload = _history_payload(telemetry, "VH-0002")
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["vehicle_id"] == "VH-0002"
    assert 0 <= body["failure_probability"] <= 1
    assert body["risk_band"] in {"low", "medium", "high"}
    assert body["maintenance_recommended"] == (
        body["failure_probability"] >= body["threshold"]
    )


def test_predict_batch(client, telemetry):
    payload = {
        "vehicles": [
            _history_payload(telemetry, "VH-0000"),
            _history_payload(telemetry, "VH-0001"),
        ]
    }
    response = client.post("/predict/batch", json=payload)
    assert response.status_code == 200
    predictions = response.json()["predictions"]
    assert [p["vehicle_id"] for p in predictions] == ["VH-0000", "VH-0001"]


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("engine_temp_c", 300.0),  # physically implausible
        ("battery_voltage_v", -1.0),
        ("coolant_level_pct", 150.0),
    ],
)
def test_predict_rejects_implausible_sensor_values(client, telemetry, field, bad_value):
    payload = _history_payload(telemetry, "VH-0002")
    payload["readings"][-1][field] = bad_value
    assert client.post("/predict", json=payload).status_code == 422


def test_predict_rejects_short_history(client, telemetry):
    payload = _history_payload(telemetry, "VH-0002", n_days=MIN_HISTORY_DAYS - 1)
    assert client.post("/predict", json=payload).status_code == 422


def test_predict_rejects_unordered_days(client, telemetry):
    payload = _history_payload(telemetry, "VH-0002")
    payload["readings"][0]["day"], payload["readings"][1]["day"] = (
        payload["readings"][1]["day"],
        payload["readings"][0]["day"],
    )
    assert client.post("/predict", json=payload).status_code == 422


def test_anomaly_check_normal_reading(client, telemetry):
    row = telemetry[telemetry["failure_within_horizon"] == 0].iloc[10]
    reading = {"day": int(row["day"]), "mileage_km": float(row["mileage_km"])} | {
        col: float(row[col]) for col in SENSOR_COLUMNS
    }
    response = client.post("/anomaly/check", json={"reading": reading})
    assert response.status_code == 200
    assert response.json()["is_anomaly"] is False


def test_anomaly_check_flags_extreme_reading(client):
    reading = {
        "day": 100,
        "engine_temp_c": 149.0,
        "oil_pressure_kpa": 5.0,
        "vibration_rms": 24.0,
        "battery_voltage_v": 6.5,
        "coolant_level_pct": 1.0,
        "brake_pad_mm": 0.2,
        "mileage_km": 50000.0,
    }
    response = client.post("/anomaly/check", json={"reading": reading})
    assert response.status_code == 200
    assert response.json()["is_anomaly"] is True
