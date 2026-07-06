"""FastAPI application factory and entrypoint.

Run locally with:

    uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

_ERROR_STATUS_CODES: dict[type[AppError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    UnauthorizedError: 401,
    ForbiddenError: 403,
}


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a FastAPI application instance.

    A factory (rather than a module-level app built at import time) lets tests
    inject their own ``Settings`` and keeps import side effects to a minimum.
    """
    injected = settings
    settings = settings or get_settings()
    setup_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    if injected is not None:
        # Endpoints resolve settings via Depends(get_settings); when an explicit
        # Settings object is injected (tests), route that dependency to it too.
        app.dependency_overrides[get_settings] = lambda: injected

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        status_code = _ERROR_STATUS_CODES.get(type(exc), 400)
        return JSONResponse(status_code=status_code, content={"detail": exc.message})

    logger.info("Application configured (environment=%s)", settings.environment)
    return app


app = create_app()
