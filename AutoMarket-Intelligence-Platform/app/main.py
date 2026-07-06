"""FastAPI application entrypoint.

Run locally with:

    uvicorn app.main:app --reload

Interactive API docs are served at http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI

from app.config import get_settings
from app.routes import health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(health.router, prefix="/api", tags=["health"])
