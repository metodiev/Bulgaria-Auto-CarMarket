from __future__ import annotations

from app.connectors.base import (
    BaseConnector,
    DiscoveredListing,
    NormalizedListing,
    SourceAccessDenied,
)


class GatedConnector(BaseConnector):
    """Connector that must not make requests until access is explicitly confirmed."""

    access_status: str = "needs_permission"
    access_reason: str = "Access has not been confirmed for automated collection."

    async def health_check(self) -> dict:
        return {
            "ok": False,
            "status": self.access_status,
            "message": self.access_reason,
        }

    async def discover_listings(self, page: int = 1) -> list[DiscoveredListing]:
        raise SourceAccessDenied(self.access_reason)

    async def fetch_listing(self, url: str) -> str:
        raise SourceAccessDenied(self.access_reason)

    def normalize_listing(
        self, html: str, url: str, summary: dict | None = None
    ) -> NormalizedListing:
        raise SourceAccessDenied(self.access_reason)

    def fetch_images(self, listing: NormalizedListing, html: str) -> list[str]:
        raise SourceAccessDenied(self.access_reason)

    def get_source_capabilities(self) -> dict:
        return {
            "scraping": False,
            "images": False,
            "archives": False,
            "status": self.access_status,
            "reason": self.access_reason,
        }
