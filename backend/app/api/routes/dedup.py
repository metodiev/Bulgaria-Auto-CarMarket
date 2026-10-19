from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import require_admin
from app.db.session import get_db
from app.models.common import utcnow
from app.models.listing import Listing
from app.models.ops import DeduplicationCandidate
from app.schemas.ops import DedupCandidateOut, DedupListingBrief, DedupResolve

router = APIRouter(prefix="/dedup", tags=["deduplication"])


def _brief(listing: Listing) -> DedupListingBrief:
    return DedupListingBrief(
        id=listing.id,
        title=listing.title,
        price=float(listing.price) if listing.price is not None else None,
        currency=listing.currency,
        year=listing.year,
        mileage_km=listing.mileage_km,
        canonical_url=listing.canonical_url,
        source={
            "id": listing.source.id,
            "slug": listing.source.slug,
            "name": listing.source.name,
            "status": listing.source.status,
        },
    )


def _out(candidate: DeduplicationCandidate) -> DedupCandidateOut:
    return DedupCandidateOut(
        id=candidate.id,
        score=candidate.score,
        reasons=candidate.reasons,
        status=candidate.status,
        created_at=candidate.created_at,
        resolved_at=candidate.resolved_at,
        listing_a=_brief(candidate.listing_a),
        listing_b=_brief(candidate.listing_b),
    )


@router.get("/candidates", response_model=list[DedupCandidateOut])
def list_candidates(
    status: str = "pending",
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[DedupCandidateOut]:
    rows = db.scalars(
        select(DeduplicationCandidate)
        .where(DeduplicationCandidate.status == status)
        .options(
            selectinload(DeduplicationCandidate.listing_a).selectinload(Listing.source),
            selectinload(DeduplicationCandidate.listing_b).selectinload(Listing.source),
        )
        .order_by(DeduplicationCandidate.score.desc())
        .limit(limit)
    ).all()
    return [_out(row) for row in rows]


@router.post(
    "/candidates/{candidate_id}/resolve",
    response_model=DedupCandidateOut,
    dependencies=[Depends(require_admin)],
)
def resolve_candidate(
    candidate_id: str, payload: DedupResolve, db: Session = Depends(get_db)
) -> DedupCandidateOut:
    candidate = db.scalar(
        select(DeduplicationCandidate)
        .where(DeduplicationCandidate.id == candidate_id)
        .options(
            selectinload(DeduplicationCandidate.listing_a).selectinload(Listing.source),
            selectinload(DeduplicationCandidate.listing_b).selectinload(Listing.source),
        )
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Кандидатът не е намерен.")
    if payload.action == "duplicate":
        a = candidate.listing_a
        b = candidate.listing_b
        canonical, duplicate = (a, b) if a.source.status == "verified" else (b, a)
        duplicate.status = "duplicate"
        duplicate.duplicate_of_id = canonical.id
        candidate.status = "resolved"
    else:
        candidate.status = "ignored"
    candidate.resolved_at = utcnow()
    db.commit()
    db.refresh(candidate)
    return _out(candidate)
