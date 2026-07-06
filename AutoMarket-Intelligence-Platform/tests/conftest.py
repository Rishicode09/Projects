"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """HTTP client that calls the API in-process (no server needed)."""
    return TestClient(app)
