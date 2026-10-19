from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.base import NormalizedListing
from app.models.common import utcnow
from app.models.listing import Listing, PriceHistory
from app.models.source import Source
from app.services.dedup import detect_candidates

UPDATABLE_FIELDS = (
    "canonical_url",
    "title",
    "make",
    "model",
    "generation",
    "year",
    "price",
    "currency",
    "mileage_km",
    "fuel_type",
    "engine_volume",
    "power_kw",
    "power_hp",
    "transmission",
    "body_type",
    "drivetrain",
    "condition",
    "color",
    "city",
    "region",
    "seller_type",
    "description",
)


def upsert_listing(
    db: Session,
    source: Source,
    payload: NormalizedListing,
    *,
    observed_at: datetime | None = None,
) -> tuple[Listing, str]:
    now = observed_at or utcnow()
    data = asdict(payload)
    existing = db.scalar(
        select(Listing).where(
            Listing.source_id == source.id,
            Listing.source_listing_id == payload.source_listing_id,
        )
    )

    if existing is None:
        listing = Listing(
            source_id=source.id,
            source_listing_id=payload.source_listing_id,
            first_seen_at=now,
            last_seen_at=now,
            last_checked_at=now,
            status="active",
            raw_data=data.get("raw_data") or {},
        )
        for field in UPDATABLE_FIELDS:
            value = data.get(field)
            if field == "price" and value is not None:
                value = Decimal(str(value))
            if field == "engine_volume" and value is not None:
                value = Decimal(str(value))
            setattr(listing, field, value)
        db.add(listing)
        db.flush()
        if listing.price is not None:
            db.add(
                PriceHistory(
                    listing_id=listing.id,
                    price=listing.price,
                    currency=listing.currency or "EUR",
                    observed_at=now,
                    source="scrape",
                )
            )
        detect_candidates(db, listing)
        return listing, "created"

    changed = False
    old_price = existing.price
    for field in UPDATABLE_FIELDS:
        value = data.get(field)
        if value is None:
            continue
        if field in {"price", "engine_volume"}:
            value = Decimal(str(value))
        if getattr(existing, field) != value:
            setattr(existing, field, value)
            changed = True

    new_price = Decimal(str(payload.price)) if payload.price is not None else None
    if new_price is not None and (old_price is None or old_price != new_price):
        db.add(
            PriceHistory(
                listing_id=existing.id,
                price=new_price,
                currency=payload.currency or existing.currency or "EUR",
                observed_at=now,
                source="scrape",
            )
        )
        existing.price = new_price
        changed = True
    if payload.currency and existing.currency != payload.currency:
        existing.currency = payload.currency
        changed = True

    existing.last_seen_at = now
    existing.last_checked_at = now
    if existing.status != "duplicate":
        existing.status = "active"
    if payload.raw_data:
        merged = dict(existing.raw_data or {})
        merged.update(payload.raw_data)
        existing.raw_data = merged
    db.flush()
    detect_candidates(db, existing)
    return existing, "updated" if changed else "unchanged"


def mark_stale_listings(db: Session, days: int) -> int:
    cutoff = utcnow().replace(microsecond=0)
    from datetime import timedelta

    cutoff = cutoff - timedelta(days=days)
    stale = db.scalars(
        select(Listing).where(
            Listing.status == "active",
            Listing.last_seen_at < cutoff,
        )
    ).all()
    for listing in stale:
        listing.status = "inactive"
    return len(stale)
