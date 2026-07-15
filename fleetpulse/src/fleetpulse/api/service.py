"""Translation layer between API schemas and the ML pipeline.

The service owns the loaded artifacts and reuses the *same*
``build_features`` function as training, so a request is guaranteed to be
transformed exactly the way training data was — the classic source of
train/serve skew is a second, hand-rolled feature implementation in the
serving path.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fleetpulse.api.schemas import (
    AnomalyCheckResponse,
    ModelInfo,
    Prediction,
    SensorReading,
    VehicleHistory,
)
from fleetpulse.features import build_features
from fleetpulse.models.anomaly import AnomalyDetector
from fleetpulse.models.train import TrainedModel, load_model


def _history_to_frame(history: VehicleHistory) -> pd.DataFrame:
    frame = pd.DataFrame([reading.model_dump() for reading in history.readings])
    frame["vehicle_id"] = history.vehicle_id
    frame["vehicle_type"] = history.vehicle_type
    frame["vehicle_age_years"] = history.vehicle_age_years
    return frame


def _risk_band(probability: float, threshold: float) -> str:
    if probability >= threshold:
        return "high"
    if probability >= threshold / 2:
        return "medium"
    return "low"


class PredictionService:
    def __init__(self, model: TrainedModel, detector: AnomalyDetector) -> None:
        self._model = model
        self._detector = detector

    @classmethod
    def from_artifacts(cls, artifact_dir: Path) -> PredictionService:
        return cls(model=load_model(artifact_dir), detector=AnomalyDetector.load(artifact_dir))

    def predict(self, history: VehicleHistory) -> Prediction:
        features = build_features(_history_to_frame(history))
        latest = features.iloc[[-1]]  # score the most recent day
        probability = float(self._model.predict_proba(latest).iloc[0])
        threshold = self._model.threshold
        return Prediction(
            vehicle_id=history.vehicle_id,
            failure_probability=round(probability, 4),
            maintenance_recommended=probability >= threshold,
            risk_band=_risk_band(probability, threshold),
            threshold=threshold,
        )

    def predict_batch(self, histories: list[VehicleHistory]) -> list[Prediction]:
        return [self.predict(history) for history in histories]

    def check_anomaly(self, reading: SensorReading) -> AnomalyCheckResponse:
        result = self._detector.score(pd.DataFrame([reading.model_dump()])).iloc[0]
        return AnomalyCheckResponse(
            anomaly_score=round(float(result["anomaly_score"]), 4),
            is_anomaly=bool(result["is_anomaly"]),
        )

    def info(self) -> ModelInfo:
        card = self._model.card
        return ModelInfo(
            model_name=card["model_name"],
            fleetpulse_version=card["fleetpulse_version"],
            trained_at=card["trained_at"],
            threshold=card["threshold"],
            metrics=card["metrics"],
        )
