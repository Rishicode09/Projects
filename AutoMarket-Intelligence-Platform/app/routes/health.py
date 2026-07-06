"""Health check endpoint.

Used to confirm the API is up -- by humans, by tests, and later by any
hosting platform that pings the service to check it is alive.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", app=settings.app_name, version=settings.app_version)
