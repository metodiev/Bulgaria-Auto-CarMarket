from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import or_, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.common import utcnow
from app.models.ops import ScrapeRun
from app.models.source import SearchJob
from app.services.ai_analysis import recover_interrupted_runs as recover_ai_runs
from app.services.listings import mark_stale_listings as mark_stale
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.scheduler.dispatch_due_scrapes")
def dispatch_due_scrapes() -> None:
    db = SessionLocal()
    try:
        now = utcnow()
        jobs = db.scalars(
            select(SearchJob)
            .where(
                SearchJob.enabled.is_(True),
                or_(SearchJob.next_run_at.is_(None), SearchJob.next_run_at <= now),
            )
            .order_by(SearchJob.next_run_at.asc().nullsfirst())
            .limit(20)
        ).all()

        for job in jobs:
            source = job.source
            interval = timedelta(minutes=max(5, job.interval_minutes))
            job.last_run_at = now
            job.next_run_at = now + interval
            db.commit()

            if source is None or not source.enabled or source.status != "verified":
                logger.warning(
                    "Skipping due search job for non-scrapable source",
                    extra={"source": source.slug if source else None},
                )
                continue

            active_run = db.scalar(
                select(ScrapeRun.id).where(
                    ScrapeRun.source_id == source.id,
                    ScrapeRun.status.in_(["pending", "running"]),
                )
            )
            if active_run:
                continue

            config = dict(source.config or {})
            run = ScrapeRun(
                source_id=source.id,
                search_job_id=job.id,
                status="pending",
                triggered_by="scheduler",
                stats={
                    "max_pages": config.get("max_pages_per_run", 2),
                    "max_listings": config.get("max_listings_per_run", 20),
                },
            )
            db.add(run)
            db.commit()
            db.refresh(run)

            try:
                result = celery_app.send_task(
                    "app.tasks.scrape.execute_scrape_run",
                    args=[run.id],
                    queue="scrape",
                )
                run.celery_task_id = result.id
                db.commit()
                logger.info(
                    "Queued scheduled scrape run",
                    extra={"source": source.slug, "run_id": run.id},
                )
            except Exception as exc:
                run.status = "failed"
                run.error_message = "Scraping queue is unavailable. Check Redis/Celery."
                run.completed_at = utcnow()
                db.commit()
                logger.error(
                    "Could not queue scheduled scrape run: %s", type(exc).__name__
                )
    finally:
        db.close()


@celery_app.task(name="app.tasks.scheduler.mark_stale_listings")
def mark_stale_listings() -> None:
    db = SessionLocal()
    try:
        count = mark_stale(db, settings.stale_listing_days)
        db.commit()
        logger.info("Marked %s listings as inactive", count)
    finally:
        db.close()


@celery_app.task(name="app.tasks.scheduler.recover_interrupted_ai_runs")
def recover_interrupted_ai_runs() -> None:
    db = SessionLocal()
    try:
        count = recover_ai_runs(db, older_than_minutes=10)
        logger.info("Recovered %s interrupted AI runs", count)
    finally:
        db.close()


@celery_app.task(name="app.tasks.scheduler.recover_interrupted_scrape_runs")
def recover_interrupted_scrape_runs() -> None:
    db = SessionLocal()
    try:
        cutoff = utcnow() - timedelta(minutes=60)
        runs = db.scalars(
            select(ScrapeRun).where(
                ScrapeRun.status == "running",
                ScrapeRun.started_at.is_not(None),
                ScrapeRun.started_at < cutoff,
            )
        ).all()
        for run in runs:
            run.status = "failed"
            run.error_message = (
                "Scrape run-ът беше прекъснат (worker restart или изтекъл timeout)."
            )
            run.completed_at = utcnow()
        if runs:
            db.commit()
        logger.info("Recovered %s interrupted scrape runs", len(runs))
    finally:
        db.close()
