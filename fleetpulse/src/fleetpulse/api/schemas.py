"""Request/response contracts for the inference API.

Validation limits are physical plausibility bounds, not statistical ones:
a 300 °C engine coolant reading is a data fault and should be rejected at
the boundary with a 422 rather than silently scored. Statistical oddities
*within* plausible bounds are the anomaly detector's job.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from fleetpulse.config import ROLLING_WINDOW_DAYS

# A prediction needs a full rolling window plus the day being scored.
MIN_HISTORY_DAYS = ROLLING_WINDOW_DAYS + 1
MAX_BATCH_SIZE = 100


class SensorReading(BaseModel):
    """One day of telemetry for one vehicle."""

    day: int = Field(ge=0, description="Day index; must increase across the history")
    engine_temp_c: float = Field(ge=-40, le=150)
    oil_pressure_kpa: float = Field(ge=0, le=700)
    vibration_rms: float = Field(ge=0, le=25)
    battery_voltage_v: float = Field(ge=6, le=16)
    coolant_level_pct: float = Field(ge=0, le=100)
    brake_pad_mm: float = Field(ge=0, le=20)
    mileage_km: float = Field(ge=0)


class VehicleHistory(BaseModel):
    """A vehicle's recent telemetry; the latest reading is the one scored."""

    vehicle_id: str = Field(min_length=1, max_length=32)
    vehicle_type: Literal["city_car", "delivery_van", "hgv"]
    vehicle_age_years: float = Field(ge=0, le=40)
    readings: list[SensorReading] = Field(min_length=MIN_HISTORY_DAYS, max_length=730)

    @model_validator(mode="after")
    def _days_strictly_increasing(self) -> VehicleHistory:
        days = [r.day for r in self.readings]
        if any(later <= earlier for earlier, later in zip(days, days[1:], strict=False)):
            raise ValueError("readings must be ordered by strictly increasing day")
        return self


class Prediction(BaseModel):
    vehicle_id: str
    failure_probability: float = Field(ge=0, le=1)
    maintenance_recommended: bool
    risk_band: Literal["low", "medium", "high"]
    threshold: float


class BatchPredictionRequest(BaseModel):
    vehicles: list[VehicleHistory] = Field(min_length=1, max_length=MAX_BATCH_SIZE)


class BatchPredictionResponse(BaseModel):
    predictions: list[Prediction]


class AnomalyCheckRequest(BaseModel):
    reading: SensorReading


class AnomalyCheckResponse(BaseModel):
    anomaly_score: float
    is_anomaly: bool


class ModelInfo(BaseModel):
    model_name: str
    fleetpulse_version: str
    trained_at: str
    threshold: float
    metrics: dict[str, float]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_loaded: bool
