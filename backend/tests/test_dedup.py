from __future__ import annotations

from sqlalchemy import select

from app.models.ops import DeduplicationCandidate
from app.services.dedup import detect_candidates
from tests.conftest import make_listing, make_source


def test_detects_cross_source_duplicate(db) -> None:
    source_a = make_source(db, slug="source-a", name="Source A")
    source_b = make_source(db, slug="source-b", name="Source B")
    listing_a = make_listing(db, source_a, ref="a-1", title="Audi A4 2.0 TDI", price=15000)
    listing_b = make_listing(db, source_b, ref="b-1", title="Audi A4 2.0 TDI", price=15200)

    created = detect_candidates(db, listing_a)
    db.commit()

    assert len(created) == 1
    stored = db.scalars(select(DeduplicationCandidate)).all()
    assert len(stored) == 1
    assert stored[0].score >= 0.75
    assert {stored[0].listing_a_id, stored[0].listing_b_id} == {listing_a.id, listing_b.id}
    assert detect_candidates(db, listing_a) == []


def test_ignores_different_listing(db) -> None:
    source_a = make_source(db, slug="source-a", name="Source A")
    source_b = make_source(db, slug="source-b", name="Source B")
    listing_a = make_listing(db, source_a, ref="a-1", title="Audi A4 2.0 TDI", price=15000)
    make_listing(db, source_b, ref="b-1", title="BMW X5 3.0d", make="BMW", model="X5", price=30000)

    assert detect_candidates(db, listing_a) == []
