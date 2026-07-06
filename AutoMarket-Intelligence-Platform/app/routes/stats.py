"""Market statistics, computed with Pandas."""

from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Listing
from app.schemas import MakeStat, StatsOverview, YearStat

router = APIRouter()


@router.get("/stats/overview", response_model=StatsOverview)
def stats_overview(db: Annotated[Session, Depends(get_db)]) -> StatsOverview:
    """Headline market statistics across all listings."""
    df = pd.read_sql(select(Listing), db.connection())
    if df.empty:
        raise HTTPException(status_code=404, detail="No listings in the database yet")

    by_make = (
        df.groupby("make")["price"]
        .agg(listings="count", average_price="mean")
        .sort_values("listings", ascending=False)
        .head(10)
        .reset_index()
    )
    by_year = (
        df.groupby("year")["price"]
        .agg(listings="count", average_price="mean")
        .sort_index()
        .reset_index()
    )

    return StatsOverview(
        total_listings=len(df),
        average_price=int(df["price"].mean()),
        median_price=int(df["price"].median()),
        average_mileage=int(df["mileage"].mean()),
        popular_makes=[
            MakeStat(
                make=row.make,
                listings=int(row.listings),
                average_price=int(row.average_price),
            )
            for row in by_make.itertuples()
        ],
        price_by_year=[
            YearStat(
                year=int(row.year),
                listings=int(row.listings),
                average_price=int(row.average_price),
            )
            for row in by_year.itertuples()
        ],
    )
