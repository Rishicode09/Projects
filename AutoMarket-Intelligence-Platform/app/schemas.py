"""Pydantic schemas: the shapes of API requests and responses.

Keeping these separate from the database models means we choose exactly what
the API exposes, and FastAPI uses them to validate input and document the API.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ListingOut(BaseModel):
    """A single listing as returned by the API."""

    model_config = ConfigDict(from_attributes=True)  # allows building from ORM objects

    id: int
    make: str
    model: str
    year: int
    mileage: int
    fuel_type: str
    transmission: str
    engine_size: float
    price: int
    region: str
    seller_type: str
    listed_date: date


class ListingPage(BaseModel):
    """One page of listings plus the info needed to paginate."""

    items: list[ListingOut]
    total: int
    page: int
    page_size: int
    pages: int


class MakeStat(BaseModel):
    make: str
    listings: int
    average_price: int


class YearStat(BaseModel):
    year: int
    listings: int
    average_price: int


class StatsOverview(BaseModel):
    total_listings: int
    average_price: int
    median_price: int
    average_mileage: int
    popular_makes: list[MakeStat]
    price_by_year: list[YearStat]


class PredictionRequest(BaseModel):
    """The car details a user submits to get a price estimate."""

    make: str
    model: str
    year: int = Field(ge=1990, le=2030)
    mileage: int = Field(ge=0, le=500_000)
    fuel_type: str
    transmission: str
    engine_size: float = Field(ge=0.0, le=8.0)


class PredictionResponse(BaseModel):
    estimated_price: int
    currency: str = "GBP"
    model_name: str
    model_mae: int = Field(description="Mean absolute error of the model on unseen test data")
