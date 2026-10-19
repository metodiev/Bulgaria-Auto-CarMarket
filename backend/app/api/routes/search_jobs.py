from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import require_admin
from app.db.session import get_db
from app.models.common import utcnow
from app.models.source import SearchJob
from app.schemas.ops import SearchJobOut, SearchJobUpdate

router = APIRouter(prefix="/search-jobs", tags=["search-jobs"])


@router.get("", response_model=list[SearchJobOut])
def list_search_jobs(db: Session = Depends(get_db)) -> list[SearchJobOut]:
    rows = db.scalars(
        select(SearchJob)
        .options(selectinload(SearchJob.source))
        .order_by(SearchJob.name)
    ).all()
    return [SearchJobOut.model_validate(row) for row in rows]


@router.put(
    "/{job_id}",
    response_model=SearchJobOut,
    dependencies=[Depends(require_admin)],
)
def update_search_job(
    job_id: str, payload: SearchJobUpdate, db: Session = Depends(get_db)
) -> SearchJobOut:
    job = db.scalar(
        select(SearchJob)
        .where(SearchJob.id == job_id)
        .options(selectinload(SearchJob.source))
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Search job не е намерен.")
    if payload.enabled and (
        job.source is None or not job.source.enabled or job.source.status != "verified"
    ):
        raise HTTPException(
            status_code=409,
            detail="Периодичният scraping е разрешен само за включен проверен източник.",
        )
    if payload.enabled is not None:
        job.enabled = payload.enabled
        if payload.enabled and job.next_run_at is None:
            job.next_run_at = utcnow()
    if payload.interval_minutes is not None:
        job.interval_minutes = payload.interval_minutes
    if payload.filters is not None:
        job.filters = payload.filters
    db.commit()
    db.refresh(job)
    return SearchJobOut.model_validate(job)
