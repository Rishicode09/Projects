"""Health check and app info endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


class VersionResponse(BaseModel):
    version: str
    app_name: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", app=settings.app_name, version=settings.app_version)


@router.get("/version", response_model=VersionResponse)
def version_info() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(version=settings.app_version, app_name=settings.app_name)
