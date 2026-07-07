"""Shared pytest fixtures.

Tests run against their own in-memory SQLite database, seeded with a small
generated dataset -- they never touch the real automarket.db file.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.data_generator import generate_listings
from app.database import Base, get_db
from app.main import app
from app.models import Listing


@pytest.fixture(scope="session")
def test_engine():
    """One in-memory database for the whole test run, pre-seeded with 200 listings."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keeps the same in-memory DB across connections
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(Listing(**row) for row in generate_listings(count=200, seed=1))
        session.commit()
    return engine


@pytest.fixture()
def db(test_engine) -> Session:
    session = sessionmaker(bind=test_engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(test_engine) -> TestClient:
    """HTTP client whose requests use the test database instead of the real one."""
    TestSession = sessionmaker(bind=test_engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
