"""Liveness endpoint used by Docker healthchecks, load balancers and uptime monitors."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Shape of the health-check payload."""

    status: str
    app: str
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse)
def health_check(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Report that the API process is up and which build/environment it is running."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
