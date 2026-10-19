from __future__ import annotations

from sqlalchemy import select

from app.connectors.base import NormalizedListing
from app.models.listing import PriceHistory
from app.services.listings import upsert_listing
from tests.conftest import make_source


def payload(price: float) -> NormalizedListing:
    return NormalizedListing(
        source_listing_id="offer-1",
        canonical_url="https://cars-bg.example/offer/1",
        title="Audi A4 2.0 TDI",
        make="Audi",
        model="A4",
        year=2018,
        price=price,
        currency="EUR",
        mileage_km=150000,
        fuel_type="diesel",
        power_hp=190,
        transmission="automatic",
        description="test",
        raw_data={"price_text": str(price)},
    )


def test_upsert_tracks_price_history(db) -> None:
    source = make_source(db)
    listing, action = upsert_listing(db, source, payload(15000))
    db.commit()
    assert action == "created"

    listing, action = upsert_listing(db, source, payload(14000))
    db.commit()
    assert action == "updated"
    assert float(listing.price) == 14000

    history = db.scalars(
        select(PriceHistory)
        .where(PriceHistory.listing_id == listing.id)
        .order_by(PriceHistory.observed_at.asc())
    ).all()
    assert [float(item.price) for item in history] == [15000, 14000]


def test_upsert_is_idempotent_for_same_price(db) -> None:
    source = make_source(db)
    listing, _ = upsert_listing(db, source, payload(15000))
    db.commit()
    _, action = upsert_listing(db, source, payload(15000))
    db.commit()
    assert action == "unchanged"
    history = db.scalars(
        select(PriceHistory).where(PriceHistory.listing_id == listing.id)
    ).all()
    assert len(history) == 1
