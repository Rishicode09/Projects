"""Database tables, defined as SQLAlchemy ORM models."""

from datetime import date

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Listing(Base):
    """One used-car listing on the market."""

    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str] = mapped_column(String(50), index=True)
    model: Mapped[str] = mapped_column(String(50), index=True)
    year: Mapped[int] = mapped_column(index=True)
    mileage: Mapped[int]
    fuel_type: Mapped[str] = mapped_column(String(20))
    transmission: Mapped[str] = mapped_column(String(20))
    engine_size: Mapped[float]
    price: Mapped[int] = mapped_column(index=True)
    region: Mapped[str] = mapped_column(String(50))
    seller_type: Mapped[str] = mapped_column(String(20))
    listed_date: Mapped[date]

    def __repr__(self) -> str:
        return f"<Listing {self.year} {self.make} {self.model} £{self.price}>"
