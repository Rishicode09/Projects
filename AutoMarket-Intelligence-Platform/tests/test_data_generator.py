"""Tests for the synthetic data generator."""

from datetime import date

from app.data_generator import generate_listings


def test_generates_requested_count() -> None:
    assert len(generate_listings(count=50, seed=1)) == 50


def test_same_seed_gives_same_data() -> None:
    assert generate_listings(count=20, seed=7) == generate_listings(count=20, seed=7)


def test_prices_fall_with_age() -> None:
    """Older cars should be cheaper on average - the core market fact."""
    listings = generate_listings(count=2000, seed=3)
    current_year = date.today().year
    new = [x["price"] for x in listings if current_year - x["year"] <= 2]
    old = [x["price"] for x in listings if current_year - x["year"] >= 10]
    assert sum(new) / len(new) > sum(old) / len(old)


def test_values_are_sane() -> None:
    for row in generate_listings(count=500, seed=2):
        assert row["price"] >= 500
        assert row["mileage"] >= 0
        assert 0.0 <= row["engine_size"] <= 8.0
        assert row["fuel_type"] in {"Petrol", "Diesel", "Hybrid", "Electric"}
