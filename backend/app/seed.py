from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.source import SearchJob, Source
from app.services.ai_analysis import get_ai_settings

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "max_concurrency": 1,
    "requests_per_second": 0.5,
    "timeout_seconds": 25,
    "retry_limit": 3,
    "backoff_seconds": 2,
    "crawl_interval_minutes": 360,
    "max_pages_per_run": 2,
    "max_listings_per_run": 20,
    "download_images": False,
    "archive_html": False,
}

SOURCES = [
    {
        "slug": "cars-bg",
        "name": "Cars.bg",
        "base_url": "https://www.cars.bg/",
        "robots_url": "https://www.cars.bg/robots.txt",
        "terms_url": None,
        "status": "verified",
        "enabled": True,
        "notes": (
            "robots.txt позволява достъп (Disallow е празен). Живите HTML селектори са "
            "проверени на 2026-10-19. Пази се консервативно темпо (0.5 заявки/сек) и "
            "ограничение на страниците. Общи условия не бяха намерени на сайта; при "
            "промяна на условията източникът трябва да се преоцени."
        ),
        "capabilities": {
            "scraping": True,
            "images": True,
            "archives": True,
            "verified": True,
        },
        "config": {**DEFAULT_CONFIG, "max_pages_per_run": 2, "max_listings_per_run": 20},
    },
    {
        "slug": "mobile-bg",
        "name": "Mobile.bg",
        "base_url": "https://www.mobile.bg/",
        "robots_url": "https://www.mobile.bg/robots.txt",
        "terms_url": "https://www.mobile.bg/obshti-uslovia",
        "status": "needs_permission",
        "enabled": False,
        "notes": (
            "robots.txt позволява достъп, но Общите условия (чл. 4) определят данните "
            "като собственост на „Резон“ ООД и допускат търговско ползване само от "
            "упълномощени лица срещу заплащане. Нужно е изрично разрешение."
        ),
        "capabilities": {"scraping": False, "images": False, "archives": False},
        "config": dict(DEFAULT_CONFIG),
    },
    {
        "slug": "auto-bg",
        "name": "Auto.bg",
        "base_url": "https://www.auto.bg/",
        "robots_url": "https://www.auto.bg/robots.txt",
        "terms_url": "https://www.auto.bg/gc",
        "status": "needs_permission",
        "enabled": False,
        "notes": (
            "robots.txt позволява достъп, но Общите условия (чл. 5) определят данните "
            "като собственост на „Булинфо“ ООД и допускат търговско ползване само от "
            "упълномощени лица срещу заплащане. Нужно е изрично разрешение."
        ),
        "capabilities": {"scraping": False, "images": False, "archives": False},
        "config": dict(DEFAULT_CONFIG),
    },
    {
        "slug": "olx-bg",
        "name": "OLX.bg",
        "base_url": "https://www.olx.bg/",
        "robots_url": "https://www.olx.bg/robots.txt",
        "terms_url": None,
        "status": "blocked",
        "enabled": False,
        "notes": (
            "Заявката към robots.txt връща HTTP 403 от CloudFront. Автоматизираният "
            "достъп е блокиран и не се заобикаля."
        ),
        "capabilities": {"scraping": False, "images": False, "archives": False},
        "config": dict(DEFAULT_CONFIG),
    },
    {
        "slug": "bazar-bg",
        "name": "Bazar.bg",
        "base_url": "https://www.bazar.bg/",
        "robots_url": "https://www.bazar.bg/robots.txt",
        "terms_url": None,
        "status": "needs_permission",
        "enabled": False,
        "notes": (
            "robots.txt забранява /обяви/ и редица region-specific пътища за обяви. "
            "Условията не бяха намерени на началната страница. Нужен е ръчен преглед "
            "и потвърждение на разрешения достъп преди включване."
        ),
        "capabilities": {"scraping": False, "images": False, "archives": False},
        "config": dict(DEFAULT_CONFIG),
    },
    {
        "slug": "carmarket-bg",
        "name": "CarMarket.bg",
        "base_url": "https://carmarket.bg/",
        "robots_url": "https://carmarket.bg/robots.txt",
        "terms_url": "https://carmarket.bg/terms.pdf",
        "status": "needs_permission",
        "enabled": False,
        "notes": (
            "robots.txt позволява достъп, но Общите условия (т. 7.5 и т. 10.1) "
            "забраняват копиране и разпространение на съдържание за търговски цели "
            "без писмено съгласие. Нужно е изрично разрешение."
        ),
        "capabilities": {"scraping": False, "images": False, "archives": False},
        "config": dict(DEFAULT_CONFIG),
    },
]


def seed_sources(db: Session) -> int:
    created = 0
    for item in SOURCES:
        source = db.scalar(select(Source).where(Source.slug == item["slug"]))
        if source is None:
            source = Source(**item)
            db.add(source)
            created += 1
        else:
            source.name = item["name"]
            source.base_url = item["base_url"]
            source.robots_url = item["robots_url"]
            source.terms_url = item["terms_url"]
            source.notes = item["notes"]
            source.capabilities = item["capabilities"]
    db.commit()

    cars_bg = db.scalar(select(Source).where(Source.slug == "cars-bg"))
    if cars_bg is not None:
        job = db.scalar(
            select(SearchJob).where(
                SearchJob.source_id == cars_bg.id,
                SearchJob.name == "Cars.bg — основно търсене",
            )
        )
        if job is None:
            db.add(
                SearchJob(
                    source_id=cars_bg.id,
                    name="Cars.bg — основно търсене",
                    filters={},
                    enabled=False,
                    interval_minutes=360,
                    next_run_at=None,
                )
            )
    db.commit()
    get_ai_settings(db)
    return created


def seed_all() -> None:
    db = SessionLocal()
    try:
        created = seed_sources(db)
        logger.info("Seeded %s new sources", created)
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
