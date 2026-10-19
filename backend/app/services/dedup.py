from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.ops import DeduplicationCandidate


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-zа-я0-9]+", " ", value.lower()).strip()


def _ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _price_similarity(left: float | None, right: float | None) -> float:
    if left is None or right is None or left <= 0 or right <= 0:
        return 0.5
    return max(0.0, 1.0 - abs(left - right) / max(left, right))


def _mileage_similarity(left: int | None, right: int | None) -> float:
    if left is None or right is None:
        return 0.5
    return max(0.0, 1.0 - abs(left - right) / 50_000.0)


def similarity_score(left: Listing, right: Listing) -> tuple[float, dict]:
    title_score = _ratio(_normalize(left.title), _normalize(right.title))
    price_score = _price_similarity(
        float(left.price) if left.price is not None else None,
        float(right.price) if right.price is not None else None,
    )
    mileage_score = _mileage_similarity(left.mileage_km, right.mileage_km)
    year_score = 1.0 if left.year == right.year else 0.7
    if left.city and right.city:
        city_score = 1.0 if left.city.lower() == right.city.lower() else 0.0
    else:
        city_score = 0.6

    score = (
        0.25 * title_score
        + 0.25 * price_score
        + 0.20 * mileage_score
        + 0.15 * year_score
        + 0.15 * city_score
    )
    return round(score, 4), {
        "title_similarity": round(title_score, 3),
        "price_similarity": round(price_score, 3),
        "mileage_similarity": round(mileage_score, 3),
        "year_score": year_score,
        "city_score": city_score,
    }


def detect_candidates(
    db: Session, listing: Listing, threshold: float = 0.75
) -> list[DeduplicationCandidate]:
    if not listing.make or not listing.model or listing.year is None:
        return []

    candidates = db.scalars(
        select(Listing)
        .where(
            Listing.id != listing.id,
            Listing.status == "active",
            Listing.make == listing.make,
            Listing.model == listing.model,
            Listing.year.between(listing.year - 1, listing.year + 1),
        )
        .limit(100)
    ).all()

    created: list[DeduplicationCandidate] = []
    for other in candidates:
        if other.source_id == listing.source_id and other.source_listing_id == listing.source_listing_id:
            continue
        score, reasons = similarity_score(listing, other)
        if score < threshold:
            continue
        a_id, b_id = sorted((listing.id, other.id))
        exists = db.scalar(
            select(DeduplicationCandidate.id).where(
                DeduplicationCandidate.listing_a_id == a_id,
                DeduplicationCandidate.listing_b_id == b_id,
            )
        )
        if exists:
            continue
        candidate = DeduplicationCandidate(
            listing_a_id=a_id,
            listing_b_id=b_id,
            score=score,
            reasons=reasons,
            status="pending",
        )
        db.add(candidate)
        created.append(candidate)
    return created
