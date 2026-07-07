"""Tests for the listings endpoints."""

from fastapi.testclient import TestClient


def test_returns_a_page_of_listings(client: TestClient) -> None:
    response = client.get("/api/listings")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 200
    assert len(body["items"]) == body["page_size"] == 20
    assert body["pages"] == 10


def test_filters_by_make(client: TestClient) -> None:
    response = client.get("/api/listings", params={"make": "Ford"})
    body = response.json()
    assert body["total"] > 0
    assert all(item["make"] == "Ford" for item in body["items"])


def test_filters_by_price_range(client: TestClient) -> None:
    params = {"price_min": 5000, "price_max": 10000}
    body = client.get("/api/listings", params=params).json()
    assert all(5000 <= item["price"] <= 10000 for item in body["items"])


def test_sorts_by_price_ascending(client: TestClient) -> None:
    body = client.get("/api/listings", params={"sort_by": "price", "order": "asc"}).json()
    prices = [item["price"] for item in body["items"]]
    assert prices == sorted(prices)


def test_pagination_returns_different_items(client: TestClient) -> None:
    page1 = client.get("/api/listings", params={"page": 1}).json()
    page2 = client.get("/api/listings", params={"page": 2}).json()
    ids_on_page1 = {item["id"] for item in page1["items"]}
    ids_on_page2 = {item["id"] for item in page2["items"]}
    assert ids_on_page1.isdisjoint(ids_on_page2)


def test_rejects_invalid_sort_column(client: TestClient) -> None:
    response = client.get("/api/listings", params={"sort_by": "id; DROP TABLE"})
    assert response.status_code == 422  # validation error, not a crash


def test_get_single_listing(client: TestClient) -> None:
    listing_id = client.get("/api/listings").json()["items"][0]["id"]
    response = client.get(f"/api/listings/{listing_id}")
    assert response.status_code == 200
    assert response.json()["id"] == listing_id


def test_get_missing_listing_returns_404(client: TestClient) -> None:
    response = client.get("/api/listings/999999")
    assert response.status_code == 404
