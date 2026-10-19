from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.connectors.base import SourceAccessDenied
from app.connectors.registry import get_connector
from app.connectors.robots import RobotsGate
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.common import utcnow
from app.models.ops import ScrapeRun, ScraperError
from app.models.source import Source
from app.services.archive import archive_and_store
from app.services.images import save_listing_images
from app.services.listings import upsert_listing
from app.services.storage import ObjectStorage

logger = logging.getLogger(__name__)


def execute_scrape_run(run_id: str) -> None:
    asyncio.run(_execute_scrape_run(run_id))


async def _execute_scrape_run(run_id: str) -> None:
    db = SessionLocal()
    run = db.get(ScrapeRun, run_id)
    if run is None:
        db.close()
        return
    source = db.get(Source, run.source_id)
    if source is None:
        _fail_run(db, run, "Source not found.")
        db.close()
        return

    if not source.enabled or source.status != "verified":
        _fail_run(
            db,
            run,
            f"Source {source.slug!r} is not verified/enabled (status={source.status}).",
        )
        db.close()
        return

    started = time.monotonic()
    run.status = "running"
    run.started_at = utcnow()
    db.commit()

    config = dict(source.config or {})
    stats = dict(run.stats or {})
    max_pages = int(stats.get("max_pages") or config.get("max_pages_per_run", 2))
    max_pages = max(1, min(max_pages, 50))
    max_listings = int(stats.get("max_listings") or config.get("max_listings_per_run", 20))
    max_listings = max(1, min(max_listings, 200))
    download_images = bool(config.get("download_images", settings.image_download_enabled))
    archive_html = bool(config.get("archive_html", settings.archive_enabled))
    max_concurrency = max(1, min(int(config.get("max_concurrency", 1)), 4))

    connector = None
    try:
        connector = get_connector(source)
        robots = RobotsGate(
            source.base_url,
            connector.user_agent,
            timeout=float(config.get("timeout_seconds", settings.request_timeout_seconds)),
        )
        async with httpx.AsyncClient(
            headers={"User-Agent": connector.user_agent},
            timeout=httpx.Timeout(
                float(config.get("timeout_seconds", settings.request_timeout_seconds))
            ),
            follow_redirects=False,
        ) as robot_client:
            await robots.load(robot_client)

        if robots.error:
            logger.warning(
                "robots.txt check failed: %s", robots.error, extra={"source": source.slug}
            )

        total_found = 0
        created = 0
        updated = 0
        unchanged = 0
        errors = 0
        requests_count = 0
        storage = ObjectStorage(settings)
        fetch_semaphore = asyncio.Semaphore(max_concurrency)

        for page in range(1, max_pages + 1):
            search_url = connector.search_url(page)
            if not robots.can_fetch(search_url):
                raise SourceAccessDenied(
                    f"robots.txt does not allow the search page: {search_url}"
                )

            discovered = await connector.discover_listings(page)
            requests_count += 1
            run.pages_fetched += 1
            total_found += len(discovered)
            run.listings_found = total_found
            db.commit()

            remaining = max_listings - (created + updated + unchanged)
            if remaining <= 0:
                break
            batch = []
            for item in discovered:
                if len(batch) >= remaining:
                    break
                if not robots.can_fetch(item.url):
                    _add_error(
                        db,
                        run,
                        source,
                        item.url,
                        "robots_denied",
                        "robots.txt does not allow this listing page.",
                    )
                    errors += 1
                    continue
                batch.append(item)
            if not batch:
                continue

            async def fetch_one(item):
                async with fetch_semaphore:
                    try:
                        return item, await connector.fetch_listing(item.url), None
                    except Exception as exc:
                        return item, None, exc

            requests_count += len(batch)
            fetched = await asyncio.gather(*(fetch_one(item) for item in batch))
            for item, html, fetch_error in fetched:
                if fetch_error is not None:
                    if isinstance(fetch_error, SourceAccessDenied):
                        raise fetch_error
                    _add_error(
                        db,
                        run,
                        source,
                        item.url,
                        type(fetch_error).__name__,
                        str(fetch_error),
                    )
                    errors += 1
                    logger.warning(
                        "Listing fetch failed: %s",
                        fetch_error,
                        extra={
                            "source": source.slug,
                            "run_id": run.id,
                            "url": item.url,
                            "error_type": type(fetch_error).__name__,
                        },
                    )
                    continue

                try:
                    normalized = connector.normalize_listing(html, item.url, item.summary)
                    listing, action = upsert_listing(db, source, normalized)

                    image_urls = connector.fetch_images(normalized, html)
                    if image_urls:
                        await save_listing_images(
                            db,
                            listing,
                            image_urls,
                            source_slug=source.slug,
                            enabled=download_images,
                            settings=settings,
                            storage=storage,
                        )

                    if archive_html:
                        await archive_and_store(
                            db,
                            listing,
                            source_slug=source.slug,
                            settings=settings,
                            storage=storage,
                            allowed_hosts=connector.allowed_hosts,
                        )
                    db.commit()
                    if action == "created":
                        created += 1
                    elif action == "updated":
                        updated += 1
                    else:
                        unchanged += 1
                    logger.info(
                        "Listing processed",
                        extra={
                            "source": source.slug,
                            "run_id": run.id,
                            "listing_id": listing.id,
                            "url": item.url,
                        },
                    )
                except SourceAccessDenied:
                    raise
                except Exception as exc:
                    db.rollback()
                    _add_error(
                        db,
                        run,
                        source,
                        item.url,
                        type(exc).__name__,
                        str(exc),
                    )
                    errors += 1
                    logger.warning(
                        "Listing scrape failed: %s",
                        exc,
                        extra={
                            "source": source.slug,
                            "run_id": run.id,
                            "url": item.url,
                            "error_type": type(exc).__name__,
                        },
                    )

            if created + updated + unchanged >= max_listings:
                break

        run.listings_found = total_found
        run.listings_created = created
        run.listings_updated = updated
        run.listings_unchanged = unchanged
        run.errors_count = errors
        run.status = "completed"
        run.completed_at = utcnow()
        run.stats = {
            **stats,
            "max_pages": max_pages,
            "max_listings": max_listings,
            "requests": requests_count,
            "duration_seconds": round(time.monotonic() - started, 2),
            "robots_error": robots.error,
        }
        db.commit()
        logger.info(
            "Scrape run completed",
            extra={"source": source.slug, "run_id": run.id},
        )
        _maybe_auto_analyze(db)
    except SourceAccessDenied as exc:
        db.rollback()
        _fail_run(db, run, str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Scrape run failed",
            extra={"source": source.slug, "run_id": run.id, "error_type": type(exc).__name__},
        )
        _fail_run(db, run, f"{type(exc).__name__}: {exc}")
    finally:
        db.close()


def _fail_run(db: Session, run: ScrapeRun, message: str) -> None:
    run.status = "failed"
    run.error_message = message[:4000]
    run.completed_at = utcnow()
    db.commit()


def _add_error(
    db: Session,
    run: ScrapeRun,
    source: Source,
    url: str | None,
    error_type: str,
    message: str,
) -> None:
    run.errors_count += 1
    db.add(
        ScraperError(
            run_id=run.id,
            source_id=source.id,
            url=url,
            error_type=error_type,
            message=message[:4000],
            occurred_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def _maybe_auto_analyze(db: Session) -> None:
    try:
        from app.services.ai_analysis import maybe_create_auto_analysis

        maybe_create_auto_analysis(db)
    except Exception as exc:
        logger.warning("Auto AI analysis could not be queued: %s", exc)
