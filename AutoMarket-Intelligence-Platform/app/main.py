"""FastAPI application entrypoint.

Run locally with:

    uvicorn app.main:app --reload

Interactive API docs are served at http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI

from app.config import get_settings
from app.database import init_db
from app.routes import health, listings, predict, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

settings = get_settings()

init_db()  # create database tables on startup if they don't exist

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Used-car market analytics: browse listings, market statistics "
    "and ML price estimates.",
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(listings.router, prefix="/api", tags=["listings"])
app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(predict.router, prefix="/api", tags=["prediction"])
