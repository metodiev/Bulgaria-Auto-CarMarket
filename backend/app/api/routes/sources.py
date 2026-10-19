from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.core.security import require_admin
from app.db.session import get_db
from app.models.common import utcnow
from app.models.listing import Listing
from app.models.source import Source
from app.schemas.source import SourceOut, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


def _source_out(source: Source, listing_count: int = 0) -> SourceOut:
    return SourceOut.model_validate(source).model_copy(
        update={"listing_count": listing_count}
    )


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)) -> list[SourceOut]:
    rows = db.execute(
        select(Source, func.count(Listing.id))
        .outerjoin(Listing, Listing.source_id == Source.id)
        .group_by(Source.id)
        .order_by(Source.name)
    ).all()
    return [_source_out(source, int(count)) for source, count in rows]


@router.put(
    "/{source_id}",
    response_model=SourceOut,
    dependencies=[Depends(require_admin)],
)
def update_source(
    source_id: str, payload: SourceUpdate, db: Session = Depends(get_db)
) -> SourceOut:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Източникът не е намерен.")
    if payload.enabled is True and source.status != "verified":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Източникът е със статус {source.status}. "
                "Включването е блокирано до потвърждение на разрешен достъп."
            ),
        )
    if payload.enabled is not None:
        source.enabled = payload.enabled
    if payload.config is not None:
        merged = dict(source.config or {})
        merged.update(payload.config.model_dump(exclude_unset=True))
        source.config = merged
    if payload.notes is not None:
        source.notes = payload.notes
    db.commit()
    db.refresh(source)
    count = db.scalar(
        select(func.count(Listing.id)).where(Listing.source_id == source.id)
    ) or 0
    return _source_out(source, int(count))


@router.post(
    "/{source_id}/health",
    dependencies=[Depends(require_admin)],
)
async def check_source_health(
    source_id: str, db: Session = Depends(get_db)
) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Източникът не е намерен.")
    connector = get_connector(source)
    try:
        result = await connector.health_check()
    except Exception as exc:
        result = {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
    source.last_health_status = (
        "ok" if result.get("ok") else str(result.get("status") or "error")
    )
    source.last_health_checked_at = utcnow()
    db.commit()
    return result
