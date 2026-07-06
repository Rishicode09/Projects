"""Fill the database with synthetic listings.

Usage:
    python scripts/seed_data.py            # seed 5000 listings (skips if data exists)
    python scripts/seed_data.py --force    # wipe and reseed
"""

import argparse

from sqlalchemy import delete, func, select

from app.data_generator import generate_listings
from app.database import SessionLocal, init_db
from app.models import Listing


def seed(count: int = 5000, force: bool = False) -> int:
    """Insert `count` listings. Returns how many rows were inserted."""
    init_db()
    with SessionLocal() as db:
        existing = db.scalar(select(func.count()).select_from(Listing))
        if existing and not force:
            print(f"Database already has {existing} listings. Use --force to reseed.")
            return 0
        if existing:
            db.execute(delete(Listing))

        db.add_all(Listing(**row) for row in generate_listings(count))
        db.commit()
        print(f"Inserted {count} listings.")
        return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    seed(count=args.count, force=args.force)
