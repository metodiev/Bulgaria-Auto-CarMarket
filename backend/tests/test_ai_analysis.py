from __future__ import annotations

from datetime import timedelta

from app.models.ai import AIAnalysisRun
from app.models.common import utcnow
from app.services.ai_analysis import recover_interrupted_runs, select_candidates
from tests.conftest import make_listing, make_source


def test_select_candidates_prefers_below_market_price(db) -> None:
    source = make_source(db)
    cheap = make_listing(db, source, ref="cheap", price=10000, mileage=150000)
    make_listing(db, source, ref="market-1", price=15000, mileage=150000)
    make_listing(db, source, ref="market-2", price=15000, mileage=150000)
    db.commit()

    candidates, stats = select_candidates(db, {}, default_limit=10)
    assert stats["matched_listings"] == 3
    assert len(candidates) == 3
    assert candidates[0].listing.id == cheap.id
    assert candidates[0].price_advantage_pct == 33.33
    assert candidates[0].score > candidates[1].score


def test_select_candidates_respects_filters(db) -> None:
    source = make_source(db)
    make_listing(db, source, ref="a4", make="Audi", model="A4", price=10000)
    make_listing(db, source, ref="x5", make="BMW", model="X5", price=20000)
    db.commit()

    candidates, stats = select_candidates(db, {"make": "Audi"}, default_limit=10)
    assert stats["matched_listings"] == 1
    assert candidates[0].listing.model == "A4"


def test_recover_interrupted_ai_run(db) -> None:
    run = AIAnalysisRun(
        task_type="best_deals",
        status="running",
        model_name="qwen3:4b",
        prompt_version="test",
        filter_config={},
        started_at=utcnow() - timedelta(minutes=30),
        progress=35,
    )
    db.add(run)
    db.commit()

    assert recover_interrupted_runs(db, older_than_minutes=10) == 1
    db.refresh(run)
    assert run.status == "failed"
    assert "прекъсната" in (run.error_message or "")
    assert run.progress == 100
