"""Price prediction endpoint."""

from fastapi import APIRouter, HTTPException

from app.ml.predictor import ModelNotTrainedError, get_metrics, predict_price
from app.schemas import PredictionRequest, PredictionResponse

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    """Estimate a fair market price for the given car."""
    try:
        estimate = predict_price(
            make=request.make,
            model=request.model,
            year=request.year,
            mileage=request.mileage,
            fuel_type=request.fuel_type,
            transmission=request.transmission,
            engine_size=request.engine_size,
        )
        metrics = get_metrics()
    except ModelNotTrainedError as exc:
        # 503 = service (temporarily) unavailable: the API works, the model is missing.
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return PredictionResponse(
        estimated_price=estimate,
        model_name=metrics["best_model"],
        model_mae=int(metrics["test_mae"]),
    )
