from __future__ import annotations

from datetime import timedelta
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.common import utcnow
from app.models.listing import Listing, PriceHistory
from app.models.source import Source
from app.schemas.stats import MarketStatsOut, StatBucket


def _buckets(
    db: Session,
    column,
    *,
    conditions: list,
    limit: int = 12,
    order_by_count: bool = True,
) -> list[StatBucket]:
    stmt = (
        select(column, func.count(Listing.id), func.avg(Listing.price))
        .where(*conditions, column.is_not(None))
        .group_by(column)
    )
    if order_by_count:
        stmt = stmt.order_by(func.count(Listing.id).desc())
    else:
        stmt = stmt.order_by(column.desc())
    stmt = stmt.limit(limit)
    rows = db.execute(stmt).all()
    return [
        StatBucket(
            key=str(row[0]),
            count=int(row[1]),
            avg_price=round(float(row[2]), 2) if row[2] is not None else None,
        )
        for row in rows
    ]


def get_market_stats(
    db: Session, *, source_slug: str | None = None, days: int = 30
) -> MarketStatsOut:
    conditions = [Listing.status == "active"]
    if source_slug:
        source = db.scalar(select(Source).where(Source.slug == source_slug))
        conditions.append(Listing.source_id == (source.id if source else "__missing__"))

    total_active = db.scalar(
        select(func.count(Listing.id)).where(*conditions)
    ) or 0
    cutoff = utcnow() - timedelta(days=7)
    new_last_7_days = db.scalar(
        select(func.count(Listing.id)).where(*conditions, Listing.first_seen_at >= cutoff)
    ) or 0
    price_cutoff = utcnow() - timedelta(days=days)
    price_changes_30d = db.scalar(
        select(func.count(PriceHistory.id)).where(PriceHistory.observed_at >= price_cutoff)
    ) or 0

    prices = [
        float(value)
        for value in db.scalars(
            select(Listing.price).where(*conditions, Listing.price.is_not(None))
        ).all()
    ]
    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    median_price = round(median(prices), 2) if prices else None

    source_conditions = [Listing.status == "active"]
    if source_slug:
        source = db.scalar(select(Source).where(Source.slug == source_slug))
        source_conditions.append(Listing.source_id == (source.id if source else "__missing__"))
    source_rows = db.execute(
        select(Source.name, func.count(Listing.id), func.avg(Listing.price))
        .join(Listing, Listing.source_id == Source.id)
        .where(*source_conditions)
        .group_by(Source.name)
        .order_by(func.count(Listing.id).desc())
        .limit(12)
    ).all()
    by_source = [
        StatBucket(
            key=str(row[0]),
            count=int(row[1]),
            avg_price=round(float(row[2]), 2) if row[2] is not None else None,
        )
        for row in source_rows
    ]

    return MarketStatsOut(
        total_active=total_active,
        new_last_7_days=new_last_7_days,
        price_changes_30d=price_changes_30d,
        avg_price=avg_price,
        median_price=median_price,
        by_source=by_source,
        by_make=_buckets(db, Listing.make, conditions=conditions),
        by_model=_buckets(db, Listing.model, conditions=conditions),
        by_region=_buckets(db, Listing.region, conditions=conditions),
        by_fuel=_buckets(db, Listing.fuel_type, conditions=conditions),
        by_year=_buckets(db, Listing.year, conditions=conditions, limit=10, order_by_count=False),
    )
