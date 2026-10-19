from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceConfig(BaseModel):
    max_concurrency: int = Field(default=1, ge=1, le=4)
    requests_per_second: float = Field(default=0.5, gt=0, le=5)
    timeout_seconds: float = Field(default=25, ge=5, le=120)
    retry_limit: int = Field(default=3, ge=0, le=10)
    backoff_seconds: float = Field(default=2, ge=0.5, le=60)
    crawl_interval_minutes: int = Field(default=360, ge=5, le=10080)
    max_pages_per_run: int = Field(default=2, ge=1, le=50)
    max_listings_per_run: int = Field(default=20, ge=1, le=200)
    download_images: bool = False
    archive_html: bool = False


class SourceUpdate(BaseModel):
    enabled: bool | None = None
    config: SourceConfig | None = None
    notes: str | None = Field(default=None, max_length=2000)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    base_url: str
    robots_url: str | None = None
    terms_url: str | None = None
    status: str
    enabled: bool
    notes: str | None = None
    capabilities: dict
    config: dict
    last_health_status: str | None = None
    last_health_checked_at: datetime | None = None
    listing_count: int = 0
    created_at: datetime
    updated_at: datetime


class SourceBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
