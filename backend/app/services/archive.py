from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.listing import Listing, ListingSnapshot
from app.services.storage import ObjectStorage, StorageError
from app.services.url_safety import validate_http_url

logger = logging.getLogger(__name__)


class ArchiveError(Exception):
    pass


async def capture_page(url: str, *, max_bytes: int) -> tuple[bytes, bytes]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ArchiveError("Playwright is not installed in this worker.") from exc

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            page = await browser.new_page(
                viewport={"width": 1366, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (compatible; BulgariaAutoCarMarket/1.0; "
                    "self-hosted archive)"
                ),
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            html = (await page.content()).encode("utf-8")
            screenshot = await page.screenshot(full_page=True, type="png")
        finally:
            await browser.close()

    if len(html) > max_bytes or len(screenshot) > max_bytes:
        raise ArchiveError("Archived page exceeded the configured size limit.")
    return html, screenshot


async def archive_and_store(
    db: Session,
    listing: Listing,
    *,
    source_slug: str,
    settings: Settings,
    storage: ObjectStorage,
    allowed_hosts: set[str] | None = None,
) -> ListingSnapshot | None:
    try:
        validate_http_url(listing.canonical_url, allowed_hosts=allowed_hosts)
        html, screenshot = await capture_page(
            listing.canonical_url, max_bytes=settings.archive_max_bytes
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        html_key = f"archives/{source_slug}/{listing.id}/{stamp}.html"
        screenshot_key = f"archives/{source_slug}/{listing.id}/{stamp}.png"
        storage.put_bytes(html_key, html, "text/html; charset=utf-8")
        storage.put_bytes(screenshot_key, screenshot, "image/png")
        snapshot = ListingSnapshot(
            listing_id=listing.id,
            html_storage_key=html_key,
            screenshot_storage_key=screenshot_key,
            status="completed",
        )
        db.add(snapshot)
        return snapshot
    except Exception as exc:
        logger.warning(
            "Archive failed: %s",
            exc,
            extra={"listing_id": listing.id, "url": listing.canonical_url, "error_type": "archive"},
        )
        snapshot = ListingSnapshot(
            listing_id=listing.id,
            status="failed",
            error_message=str(exc)[:1000],
        )
        db.add(snapshot)
        return snapshot
