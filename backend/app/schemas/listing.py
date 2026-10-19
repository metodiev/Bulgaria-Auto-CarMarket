from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.source import SourceBrief


class ListingImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_url: str
    storage_key: str | None = None
    checksum_sha256: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    download_status: str
    downloaded_at: datetime | None = None


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    source: SourceBrief
    source_listing_id: str
    canonical_url: str
    title: str
    make: str | None = None
    model: str | None = None
    generation: str | None = None
    year: int | None = None
    price: float | None = None
    currency: str | None = None
    mileage_km: int | None = None
    fuel_type: str | None = None
    engine_volume: float | None = None
    power_kw: int | None = None
    power_hp: int | None = None
    transmission: str | None = None
    body_type: str | None = None
    drivetrain: str | None = None
    condition: str | None = None
    color: str | None = None
    city: str | None = None
    region: str | None = None
    seller_type: str | None = None
    description: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    last_checked_at: datetime | None = None
    status: str
    primary_image_url: str | None = None


class ListingDetailOut(ListingOut):
    images: list[ListingImageOut] = []
    duplicate_of_id: str | None = None


class PricePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: float
    currency: str
    observed_at: datetime
    source: str


class ListingFilterOptions(BaseModel):
    makes: list[str]
    models: list[str]
    regions: list[str]
    fuel_types: list[str]
    transmissions: list[str]
    sources: list[SourceBrief]
    years: list[int]
