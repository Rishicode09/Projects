"""Tests for the health endpoint and app factory wiring."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "testing"
    assert body["version"] == "0.1.0"


def test_openapi_docs_are_exposed(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200
