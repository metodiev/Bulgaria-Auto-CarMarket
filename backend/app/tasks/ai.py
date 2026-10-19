from __future__ import annotations

import logging

from celery.signals import worker_ready

from app.db.session import SessionLocal
from app.services.ai_analysis import recover_interrupted_runs, run_analysis
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.ai.run_analysis", max_retries=0)
def run_analysis_task(self, run_id: str) -> None:
    logger.info("Starting AI analysis %s", run_id)
    run_analysis(run_id)


@worker_ready.connect
def recover_orphaned_runs_on_start(sender=None, **kwargs) -> None:
    hostname = getattr(sender, "hostname", "") or ""
    if not hostname.startswith("ai@"):
        return
    db = SessionLocal()
    try:
        count = recover_interrupted_runs(db, older_than_minutes=1)
        if count:
            logger.warning("Recovered %s orphaned AI runs after worker start", count)
    finally:
        db.close()
