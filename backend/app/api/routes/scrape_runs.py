from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import require_admin
from app.db.session import get_db
from app.models.ops import ScrapeRun, ScraperError
from app.models.source import Source
from app.schemas.common import Page
from app.schemas.ops import (
    ScrapeRunCreate,
    ScrapeRunDetailOut,
    ScrapeRunOut,
    ScraperErrorOut,
)
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/scrape-runs", tags=["scrape-runs"])


def _page(items, total: int, page: int, page_size: int):
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.get("", response_model=Page[ScrapeRunOut])
def list_scrape_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> Page[ScrapeRunOut]:
    conditions = []
    if source_id:
        conditions.append(ScrapeRun.source_id == source_id)
    if status:
        conditions.append(ScrapeRun.status == status)
    total = db.scalar(select(func.count(ScrapeRun.id)).where(*conditions)) or 0
    rows = db.scalars(
        select(ScrapeRun)
        .where(*conditions)
        .order_by(ScrapeRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[ScrapeRunOut](
        **_page(
            [ScrapeRunOut.model_validate(row) for row in rows],
            total,
            page,
            page_size,
        )
    )


@router.post(
    "",
    response_model=ScrapeRunOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_scrape_run(
    payload: ScrapeRunCreate, db: Session = Depends(get_db)
) -> ScrapeRunOut:
    source = db.get(Source, payload.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Източникът не е намерен.")
    if not source.enabled or source.status != "verified":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Източникът е със статус {source.status} и не може да бъде стартиран."
            ),
        )
    active = db.scalar(
        select(ScrapeRun.id).where(
            ScrapeRun.source_id == source.id,
            ScrapeRun.status.in_(["pending", "running"]),
        )
    )
    if active:
        raise HTTPException(
            status_code=409, detail="Вече има активен scrape run за този източник."
        )

    config = dict(source.config or {})
    run = ScrapeRun(
        source_id=source.id,
        search_job_id=payload.search_job_id,
        status="pending",
        triggered_by="manual",
        stats={
            "max_pages": payload.max_pages or config.get("max_pages_per_run", 2),
            "max_listings": payload.max_listings
            or config.get("max_listings_per_run", 20),
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        result = celery_app.send_task(
            "app.tasks.scrape.execute_scrape_run", args=[run.id], queue="scrape"
        )
        run.celery_task_id = result.id
        db.commit()
    except Exception as exc:
        run.status = "failed"
        run.error_message = "Scraping queue is unavailable. Check Redis/Celery."
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Опашката за scraping не е достъпна. Проверете Redis/Celery.",
        ) from exc
    return ScrapeRunOut.model_validate(run)


@router.get("/{run_id}", response_model=ScrapeRunDetailOut)
def get_scrape_run(run_id: str, db: Session = Depends(get_db)) -> ScrapeRunDetailOut:
    run = db.scalar(
        select(ScrapeRun)
        .where(ScrapeRun.id == run_id)
        .options(selectinload(ScrapeRun.errors))
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Scrape run не е намерен.")
    return ScrapeRunDetailOut.model_validate(run)


@router.get("/{run_id}/errors", response_model=list[ScraperErrorOut])
def get_run_errors(
    run_id: str, db: Session = Depends(get_db)
) -> list[ScraperErrorOut]:
    rows = db.scalars(
        select(ScraperError)
        .where(ScraperError.run_id == run_id)
        .order_by(ScraperError.occurred_at.desc())
    ).all()
    return [ScraperErrorOut.model_validate(row) for row in rows]


@router.post(
    "/{run_id}/retry",
    response_model=ScrapeRunOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def retry_scrape_run(run_id: str, db: Session = Depends(get_db)) -> ScrapeRunOut:
    old = db.get(ScrapeRun, run_id)
    if old is None:
        raise HTTPException(status_code=404, detail="Scrape run не е намерен.")
    source = db.get(Source, old.source_id)
    if source is None or not source.enabled or source.status != "verified":
        raise HTTPException(status_code=409, detail="Източникът не е активен.")
    run = ScrapeRun(
        source_id=old.source_id,
        search_job_id=old.search_job_id,
        status="pending",
        triggered_by="retry",
        stats=dict(old.stats or {}),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        result = celery_app.send_task(
            "app.tasks.scrape.execute_scrape_run", args=[run.id], queue="scrape"
        )
        run.celery_task_id = result.id
        db.commit()
    except Exception as exc:
        run.status = "failed"
        run.error_message = "Scraping queue is unavailable. Check Redis/Celery."
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Опашката за scraping не е достъпна. Проверете Redis/Celery.",
        ) from exc
    return ScrapeRunOut.model_validate(run)
