from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "bulgaria_auto_carmarket",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=[
        "app.tasks.scrape",
        "app.tasks.ai",
        "app.tasks.scheduler",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_default_queue="scrape",
    task_routes={
        "app.tasks.scrape.*": {"queue": "scrape"},
        "app.tasks.ai.*": {"queue": "ai"},
        "app.tasks.scheduler.*": {"queue": "scrape"},
    },
    beat_schedule={
        "dispatch-due-scrapes": {
            "task": "app.tasks.scheduler.dispatch_due_scrapes",
            "schedule": 60.0,
        },
        "mark-stale-listings": {
            "task": "app.tasks.scheduler.mark_stale_listings",
            "schedule": crontab(hour=3, minute=15),
        },
        "recover-interrupted-ai-runs": {
            "task": "app.tasks.scheduler.recover_interrupted_ai_runs",
            "schedule": 300.0,
        },
        "recover-interrupted-scrape-runs": {
            "task": "app.tasks.scheduler.recover_interrupted_scrape_runs",
            "schedule": 900.0,
        },
    },
)
