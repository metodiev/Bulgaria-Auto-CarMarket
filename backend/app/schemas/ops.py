from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.source import SourceBrief


class SearchJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    source: SourceBrief
    name: str
    filters: dict
    enabled: bool
    interval_minutes: int
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SearchJobUpdate(BaseModel):
    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    filters: dict | None = None


class ScrapeRunCreate(BaseModel):
    source_id: str
    search_job_id: str | None = None
    max_pages: int | None = Field(default=None, ge=1, le=20)
    max_listings: int | None = Field(default=None, ge=1, le=100)


class ScraperErrorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    source_id: str
    url: str | None = None
    error_type: str
    message: str
    occurred_at: datetime


class ScrapeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    search_job_id: str | None = None
    status: str
    triggered_by: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    pages_fetched: int
    listings_found: int
    listings_created: int
    listings_updated: int
    listings_unchanged: int
    errors_count: int
    error_message: str | None = None
    stats: dict
    created_at: datetime


class ScrapeRunDetailOut(ScrapeRunOut):
    errors: list[ScraperErrorOut] = []


class DedupListingBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    price: float | None = None
    currency: str | None = None
    year: int | None = None
    mileage_km: int | None = None
    canonical_url: str
    source: dict


class DedupCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    score: float
    reasons: dict
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
    listing_a: DedupListingBrief
    listing_b: DedupListingBrief


class DedupResolve(BaseModel):
    action: Literal["duplicate", "ignore"]
