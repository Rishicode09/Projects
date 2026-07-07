"""Database connection setup.

One engine (the connection pool) and one session factory for the whole app.
Routes get a database session through the `get_db` dependency, which
guarantees the session is closed after every request.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# SQLite refuses cross-thread use by default; FastAPI handles requests in a
# thread pool, so we must allow it. Harmless for other databases.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class that all ORM models inherit from."""


def init_db() -> None:
    """Create all tables that don't exist yet."""
    # Imported here so the models are registered with Base before create_all runs.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: hand a session to the route, always close it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
