from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.config import Settings, settings as default_settings
from app.models.source import Source


@dataclass(slots=True)
class DiscoveredListing:
    url: str
    summary: dict = field(default_factory=dict)


@dataclass(slots=True)
class NormalizedListing:
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
    raw_data: dict = field(default_factory=dict)


class ConnectorError(Exception):
    """Base connector failure."""


class SourceAccessDenied(ConnectorError):
    """The source is blocked or needs explicit permission."""


class BaseConnector(ABC):
    slug: str
    base_url: str
    allowed_hosts: set[str] = set()
    capabilities: dict = {
        "scraping": False,
        "images": False,
        "archives": False,
    }

    def __init__(self, source: Source, settings: Settings | None = None) -> None:
        self.source = source
        self.settings = settings or default_settings

    @property
    def user_agent(self) -> str:
        return self.settings.scrape_user_agent

    async def health_check(self) -> dict:
        return {"ok": True, "message": "Connector is implemented."}

    def search_url(self, page: int) -> str:
        return self.base_url

    @abstractmethod
    async def discover_listings(self, page: int = 1) -> list[DiscoveredListing]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_listing(self, url: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def normalize_listing(
        self, html: str, url: str, summary: dict | None = None
    ) -> NormalizedListing:
        raise NotImplementedError

    @abstractmethod
    def fetch_images(self, listing: NormalizedListing, html: str) -> list[str]:
        raise NotImplementedError

    def get_source_capabilities(self) -> dict:
        return dict(self.capabilities)
