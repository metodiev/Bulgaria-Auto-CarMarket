from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stats import MarketStatsOut
from app.services.statistics import get_market_stats

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/market", response_model=MarketStatsOut)
def market_statistics(
    source: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> MarketStatsOut:
    return get_market_stats(db, source_slug=source, days=days)
