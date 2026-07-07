"""Browse and filter car listings."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Listing
from app.schemas import ListingOut, ListingPage

router = APIRouter()


@router.get("/listings", response_model=ListingPage)
def list_listings(
    db: Annotated[Session, Depends(get_db)],
    make: str | None = None,
    model: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    sort_by: str = Query("listed_date", pattern="^(price|year|mileage|listed_date)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ListingPage:
    """Return a page of listings, with optional filters and sorting."""
    query = select(Listing)
    if make:
        query = query.where(Listing.make == make)
    if model:
        query = query.where(Listing.model == model)
    if year_min is not None:
        query = query.where(Listing.year >= year_min)
    if year_max is not None:
        query = query.where(Listing.year <= year_max)
    if price_min is not None:
        query = query.where(Listing.price >= price_min)
    if price_max is not None:
        query = query.where(Listing.price <= price_max)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    sort_column = getattr(Listing, sort_by)
    query = query.order_by(sort_column.desc() if order == "desc" else sort_column.asc())
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    return ListingPage(
        items=[ListingOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Annotated[Session, Depends(get_db)]) -> ListingOut:
    """Return one listing by its id, or 404 if it doesn't exist."""
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
    return ListingOut.model_validate(listing)
