from __future__ import annotations

import logging

from app.services.scraping import execute_scrape_run
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.scrape.execute_scrape_run", max_retries=0)
def execute_scrape_run_task(self, run_id: str) -> None:
    logger.info("Starting scrape run %s", run_id)
    execute_scrape_run(run_id)
