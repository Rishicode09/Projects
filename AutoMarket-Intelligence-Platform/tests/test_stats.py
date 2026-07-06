"""Tests for the market statistics endpoint."""

from fastapi.testclient import TestClient


def test_overview_returns_market_statistics(client: TestClient) -> None:
    response = client.get("/api/stats/overview")
    assert response.status_code == 200
    body = response.json()

    assert body["total_listings"] == 200
    assert body["average_price"] > 0
    assert body["median_price"] > 0

    assert 0 < len(body["popular_makes"]) <= 10
    top = body["popular_makes"][0]
    assert top["listings"] >= body["popular_makes"][-1]["listings"]

    years = [entry["year"] for entry in body["price_by_year"]]
    assert years == sorted(years)
