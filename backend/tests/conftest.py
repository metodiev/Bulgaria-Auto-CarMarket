from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / f"carmarket_test_{os.getpid()}.db"

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB.as_posix()}"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["AI_ENABLED"] = "false"
os.environ["AI_AUTO_ANALYZE"] = "false"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/14"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/13"
os.environ["S3_ENDPOINT"] = "http://localhost:9000"
os.environ["LOG_LEVEL"] = "ERROR"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db
from app.models.source import Source


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()
    try:
        TEST_DB.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture(autouse=True)
def clean_database(database_schema):
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    yield


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db: Session):
    from app.main import app

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sources(db: Session) -> dict[str, Source]:
    from app.seed import seed_sources

    seed_sources(db)
    rows = db.query(Source).all()
    return {source.slug: source for source in rows}


def make_source(
    db: Session,
    *,
    slug: str = "cars-bg",
    name: str = "Cars.bg",
    status: str = "verified",
    enabled: bool = True,
) -> Source:
    source = Source(
        slug=slug,
        name=name,
        base_url=f"https://{slug}.example/",
        status=status,
        enabled=enabled,
        notes="test",
        capabilities={"scraping": True, "images": True, "archives": True},
        config={
            "max_concurrency": 1,
            "requests_per_second": 0.5,
            "timeout_seconds": 25,
            "retry_limit": 0,
            "backoff_seconds": 1,
            "crawl_interval_minutes": 360,
            "max_pages_per_run": 1,
            "max_listings_per_run": 5,
            "download_images": False,
            "archive_html": False,
        },
    )
    db.add(source)
    db.flush()
    return source


def make_listing(
    db: Session,
    source: Source,
    *,
    ref: str = "listing-1",
    title: str = "Audi A4 2.0 TDI",
    make: str = "Audi",
    model: str = "A4",
    year: int = 2018,
    price: float = 15000,
    mileage: int = 150000,
    city: str = "София",
    description: str = "Добре поддържан автомобил.",
):
    from app.models.listing import Listing

    listing = Listing(
        source_id=source.id,
        source_listing_id=ref,
        canonical_url=f"https://{source.slug}.example/offer/{ref}",
        title=title,
        make=make,
        model=model,
        year=year,
        price=price,
        currency="EUR",
        mileage_km=mileage,
        fuel_type="diesel",
        transmission="automatic",
        city=city,
        region=city,
        description=description,
        status="active",
        raw_data={},
    )
    db.add(listing)
    db.flush()
    return listing
