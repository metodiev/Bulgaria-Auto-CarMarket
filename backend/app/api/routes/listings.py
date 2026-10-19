from __future__ import annotations

import math
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.listing import Listing, PriceHistory
from app.models.source import Source
from app.schemas.common import Page
from app.schemas.listing import (
    ListingDetailOut,
    ListingFilterOptions,
    ListingOut,
    PricePointOut,
)
from app.schemas.source import SourceBrief

router = APIRouter(prefix="/listings", tags=["listings"])

SORTABLE = {
    "price": Listing.price,
    "mileage_km": Listing.mileage_km,
    "year": Listing.year,
    "first_seen_at": Listing.first_seen_at,
    "last_seen_at": Listing.last_seen_at,
    "title": Listing.title,
    "make": Listing.make,
}


def _conditions(
    *,
    make: str | None,
    model: str | None,
    year_from: int | None,
    year_to: int | None,
    price_from: float | None,
    price_to: float | None,
    mileage_from: int | None,
    mileage_to: int | None,
    region: str | None,
    fuel_type: str | None,
    transmission: str | None,
    power_from: int | None,
    power_to: int | None,
    source: str | None,
    status: str,
    q: str | None,
) -> list:
    conditions: list = []
    if status != "all":
        statuses = [item.strip() for item in status.split(",") if item.strip()]
        conditions.append(Listing.status.in_(statuses))
    if make:
        conditions.append(func.lower(Listing.make) == make.lower())
    if model:
        conditions.append(Listing.model.ilike(f"%{model}%"))
    if year_from is not None:
        conditions.append(Listing.year >= year_from)
    if year_to is not None:
        conditions.append(Listing.year <= year_to)
    if price_from is not None:
        conditions.append(Listing.price >= Decimal(str(price_from)))
    if price_to is not None:
        conditions.append(Listing.price <= Decimal(str(price_to)))
    if mileage_from is not None:
        conditions.append(Listing.mileage_km >= mileage_from)
    if mileage_to is not None:
        conditions.append(Listing.mileage_km <= mileage_to)
    if region:
        conditions.append(func.lower(Listing.region) == region.lower())
    if fuel_type:
        conditions.append(func.lower(Listing.fuel_type) == fuel_type.lower())
    if transmission:
        conditions.append(func.lower(Listing.transmission) == transmission.lower())
    if power_from is not None:
        conditions.append(Listing.power_hp >= power_from)
    if power_to is not None:
        conditions.append(Listing.power_hp <= power_to)
    if source:
        conditions.append(Source.slug == source)
    if q:
        needle = q.lower()
        conditions.append(
            or_(
                func.lower(Listing.title).contains(needle, autoescape=True),
                func.lower(Listing.description).contains(needle, autoescape=True),
                func.lower(Listing.make).contains(needle, autoescape=True),
                func.lower(Listing.model).contains(needle, autoescape=True),
            )
        )
    return conditions


@router.get("/filters", response_model=ListingFilterOptions)
def filter_options(db: Session = Depends(get_db)) -> ListingFilterOptions:
    def distinct(column) -> list[str]:
        values = db.scalars(
            select(column).where(column.is_not(None)).distinct().order_by(column)
        ).all()
        return [str(value) for value in values if value]

    sources = db.scalars(select(Source).order_by(Source.name)).all()
    years = [
        int(value)
        for value in db.scalars(
            select(Listing.year).where(Listing.year.is_not(None)).distinct().order_by(Listing.year.desc())
        ).all()
    ]
    return ListingFilterOptions(
        makes=distinct(Listing.make),
        models=distinct(Listing.model),
        regions=distinct(Listing.region),
        fuel_types=distinct(Listing.fuel_type),
        transmissions=distinct(Listing.transmission),
        sources=[SourceBrief.model_validate(source) for source in sources],
        years=years,
    )


@router.get("", response_model=Page[ListingOut])
def list_listings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    make: str | None = None,
    model: str | None = None,
    year_from: int | None = Query(default=None, ge=1900, le=2100),
    year_to: int | None = Query(default=None, ge=1900, le=2100),
    price_from: float | None = Query(default=None, ge=0),
    price_to: float | None = Query(default=None, ge=0),
    mileage_from: int | None = Query(default=None, ge=0),
    mileage_to: int | None = Query(default=None, ge=0),
    region: str | None = None,
    fuel_type: str | None = None,
    transmission: str | None = None,
    power_from: int | None = Query(default=None, ge=0),
    power_to: int | None = Query(default=None, ge=0),
    source: str | None = None,
    status: str = "active",
    q: str | None = Query(default=None, max_length=200),
    sort_by: str = "last_seen_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
) -> Page[ListingOut]:
    conditions = _conditions(
        make=make,
        model=model,
        year_from=year_from,
        year_to=year_to,
        price_from=price_from,
        price_to=price_to,
        mileage_from=mileage_from,
        mileage_to=mileage_to,
        region=region,
        fuel_type=fuel_type,
        transmission=transmission,
        power_from=power_from,
        power_to=power_to,
        source=source,
        status=status,
        q=q,
    )
    sort_column = SORTABLE.get(sort_by, Listing.last_seen_at)
    order = sort_column.desc() if sort_order != "asc" else sort_column.asc()

    base: Select = select(Listing).join(Source, Listing.source_id == Source.id)
    if conditions:
        base = base.where(*conditions)
    total = db.scalar(
        select(func.count(Listing.id))
        .join(Source, Listing.source_id == Source.id)
        .where(*conditions)
    ) or 0
    items = db.scalars(
        base.options(selectinload(Listing.source), selectinload(Listing.images))
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[ListingOut](
        items=[ListingOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{listing_id}", response_model=ListingDetailOut)
def get_listing(listing_id: str, db: Session = Depends(get_db)) -> ListingDetailOut:
    listing = db.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.source), selectinload(Listing.images))
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Обявата не е намерена.")
    return ListingDetailOut.model_validate(listing)


@router.get("/{listing_id}/price-history", response_model=list[PricePointOut])
def get_price_history(
    listing_id: str, db: Session = Depends(get_db)
) -> list[PricePointOut]:
    exists = db.scalar(select(Listing.id).where(Listing.id == listing_id))
    if exists is None:
        raise HTTPException(status_code=404, detail="Обявата не е намерена.")
    rows = db.scalars(
        select(PriceHistory)
        .where(PriceHistory.listing_id == listing_id)
        .order_by(PriceHistory.observed_at.asc())
    ).all()
    return [PricePointOut.model_validate(row) for row in rows]
