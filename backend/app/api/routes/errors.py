from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ops import ScraperError
from app.schemas.common import Page
from app.schemas.ops import ScraperErrorOut

router = APIRouter(prefix="/errors", tags=["errors"])


@router.get("", response_model=Page[ScraperErrorOut])
def list_errors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    source_id: str | None = None,
    run_id: str | None = None,
    db: Session = Depends(get_db),
) -> Page[ScraperErrorOut]:
    conditions = []
    if source_id:
        conditions.append(ScraperError.source_id == source_id)
    if run_id:
        conditions.append(ScraperError.run_id == run_id)
    total = db.scalar(select(func.count(ScraperError.id)).where(*conditions)) or 0
    rows = db.scalars(
        select(ScraperError)
        .where(*conditions)
        .order_by(ScraperError.occurred_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[ScraperErrorOut](
        items=[ScraperErrorOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )
