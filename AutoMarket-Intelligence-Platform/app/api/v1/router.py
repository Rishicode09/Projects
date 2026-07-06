"""Aggregates all v1 endpoint routers into a single router.

New feature routers (auth, listings, analytics, predictions...) get included
here so ``app.main`` only ever mounts one object per API version.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
