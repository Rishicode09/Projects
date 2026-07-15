"""FastAPI application factory.

Artifacts are loaded once at startup via the lifespan hook (not per
request), and ``create_app`` takes the artifact directory as a parameter so
tests can point it at a temporary model without touching environment state.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from fleetpulse import __version__
from fleetpulse.api.schemas import (
    AnomalyCheckRequest,
    AnomalyCheckResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthResponse,
    ModelInfo,
    Prediction,
    VehicleHistory,
)
from fleetpulse.api.service import PredictionService
from fleetpulse.config import default_artifact_dir


def create_app(artifact_dir: Path | None = None) -> FastAPI:
    artifacts = artifact_dir or default_artifact_dir()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = PredictionService.from_artifacts(artifacts)
        yield

    app = FastAPI(
        title="FleetPulse",
        version=__version__,
        description="Predictive maintenance API for vehicle fleets.",
        lifespan=lifespan,
    )

    def service(app: FastAPI = app) -> PredictionService:
        svc = getattr(app.state, "service", None)
        if svc is None:  # pragma: no cover - only reachable if lifespan skipped
            raise HTTPException(status_code=503, detail="Model not loaded")
        return svc

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", model_loaded=hasattr(app.state, "service"))

    @app.get("/model/info", response_model=ModelInfo, tags=["ops"])
    def model_info() -> ModelInfo:
        return service().info()

    @app.post("/predict", response_model=Prediction, tags=["inference"])
    def predict(history: VehicleHistory) -> Prediction:
        return service().predict(history)

    @app.post("/predict/batch", response_model=BatchPredictionResponse, tags=["inference"])
    def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
        return BatchPredictionResponse(predictions=service().predict_batch(request.vehicles))

    @app.post("/anomaly/check", response_model=AnomalyCheckResponse, tags=["inference"])
    def anomaly_check(request: AnomalyCheckRequest) -> AnomalyCheckResponse:
        return service().check_anomaly(request.reading)

    return app
