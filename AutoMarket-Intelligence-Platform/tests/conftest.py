"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture()
def settings() -> Settings:
    """Isolated settings for tests -- never reads the developer's .env file."""
    return Settings(_env_file=None, environment="testing")


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    """HTTP client against a fresh app instance built from test settings."""
    return TestClient(create_app(settings))
