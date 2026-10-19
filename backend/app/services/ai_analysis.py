from __future__ import annotations

import asyncio
import logging
import random
import statistics
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings as env_settings
from app.db.session import SessionLocal
from app.models.ai import AIAnalysisRun, AISettings
from app.models.common import ensure_utc, utcnow
from app.models.listing import Listing
from app.models.source import Source
from app.schemas.ai import AIAnalyzeRequest, AISettingsUpdate
from app.services.ai_gateway import (
    AIValidationError,
    CandidateContext,
    InvalidAIResponse,
    OllamaClient,
    OllamaModelMissing,
    OllamaUnavailable,
    build_messages,
    extract_json,
    validate_ai_output,
)

logger = logging.getLogger(__name__)

PROMPT_VERSION = "2026-10-19-v1"
TASK_TYPES = {"best_deals", "price_anomalies", "market_overview"}


class AIDisabled(Exception):
    pass


class AIQueueError(Exception):
    pass


def get_ai_settings(db: Session) -> AISettings:
    row = db.get(AISettings, 1)
    if row is None:
        row = AISettings(
            id=1,
            enabled=env_settings.ai_enabled,
            base_url=env_settings.ollama_base_url.rstrip("/"),
            model_name=env_settings.ollama_model,
            default_task=env_settings.ai_default_task,
            auto_analyze=env_settings.ai_auto_analyze,
            include_descriptions=env_settings.ai_include_descriptions,
            analyze_images=False,
            max_concurrency=env_settings.ai_max_concurrency,
            timeout_seconds=env_settings.ai_timeout_seconds,
            max_attempts=env_settings.ai_max_attempts,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def update_ai_settings(db: Session, payload: AISettingsUpdate) -> AISettings:
    row = get_ai_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(row, field, value)
    if payload.analyze_images:
        # qwen3:4b is a text model. Keep the capability off unless a vision model
        # is explicitly configured and verified in a later release.
        row.analyze_images = False
    db.commit()
    db.refresh(row)
    return row


def create_analysis_run(
    db: Session, request: AIAnalyzeRequest, *, triggered_by: str = "manual"
) -> AIAnalysisRun:
    ai_settings = get_ai_settings(db)
    if not ai_settings.enabled:
        raise AIDisabled("AI модулът е изключен. Включете го от AI настройките.")
    if request.task_type not in TASK_TYPES:
        raise ValueError(f"Unsupported AI task type: {request.task_type}")

    filters = dict(request.filters or {})
    if request.candidate_limit is not None:
        filters["candidate_limit"] = request.candidate_limit
    filters["max_attempts"] = ai_settings.max_attempts

    run = AIAnalysisRun(
        task_type=request.task_type,
        status="pending",
        model_name=ai_settings.model_name,
        prompt_version=PROMPT_VERSION,
        filter_config=filters,
        progress=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    from app.tasks.celery_app import celery_app

    try:
        result = celery_app.send_task(
            "app.tasks.ai.run_analysis", args=[run.id], queue="ai"
        )
        run.celery_task_id = result.id
        db.commit()
    except Exception as exc:
        logger.error("AI queue unavailable: %s", type(exc).__name__)
        run.status = "failed"
        run.error_message = "AI queue is unavailable. Check Redis/Celery."
        run.completed_at = utcnow()
        db.commit()
        raise AIQueueError("AI queue is unavailable. Check Redis/Celery.") from exc
    return run


def maybe_create_auto_analysis(db: Session) -> AIAnalysisRun | None:
    ai_settings = get_ai_settings(db)
    if not ai_settings.enabled or not ai_settings.auto_analyze:
        return None
    request = AIAnalyzeRequest(
        task_type=ai_settings.default_task,  # type: ignore[arg-type]
        filters={},
    )
    try:
        return create_analysis_run(db, request, triggered_by="scrape")
    except (AIDisabled, AIQueueError) as exc:
        logger.warning("Automatic AI analysis not queued: %s", exc)
        return None


def _apply_filters(stmt, filters: dict[str, Any], db: Session):
    conditions = [Listing.status == "active", Listing.price.is_not(None)]
    make = filters.get("make")
    if make:
        conditions.append(func.lower(Listing.make) == str(make).lower())
    model = filters.get("model")
    if model:
        conditions.append(Listing.model.ilike(f"%{model}%"))
    for key, column in (
        ("year_from", Listing.year),
        ("year_to", Listing.year),
        ("price_from", Listing.price),
        ("price_to", Listing.price),
        ("mileage_from", Listing.mileage_km),
        ("mileage_to", Listing.mileage_km),
    ):
        value = filters.get(key)
        if value is None or value == "":
            continue
        if key.endswith("_from"):
            conditions.append(column >= value)
        else:
            conditions.append(column <= value)
    for key, column in (
        ("region", Listing.region),
        ("fuel_type", Listing.fuel_type),
        ("transmission", Listing.transmission),
    ):
        value = filters.get(key)
        if value:
            conditions.append(func.lower(column) == str(value).lower())
    source_slug = filters.get("source")
    if source_slug:
        source = db.scalar(select(Source).where(Source.slug == source_slug))
        conditions.append(Listing.source_id == (source.id if source else "__missing__"))
    days = filters.get("days")
    if days:
        conditions.append(Listing.last_seen_at >= utcnow() - timedelta(days=int(days)))
    return stmt.where(*conditions)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _recency_score(listing: Listing) -> float:
    if listing.last_seen_at is None:
        return 40.0
    age = utcnow() - ensure_utc(listing.last_seen_at)
    if age <= timedelta(days=7):
        return 100.0
    if age <= timedelta(days=30):
        return 70.0
    return 40.0


def select_candidates(
    db: Session, filters: dict[str, Any], default_limit: int = 40
) -> tuple[list[CandidateContext], dict]:
    stmt = _apply_filters(select(Listing), filters, db).order_by(
        Listing.last_seen_at.desc()
    ).limit(1000)
    listings = db.scalars(stmt).all()
    if not listings:
        return [], {
            "matched_listings": 0,
            "analyzed_listings": 0,
            "filters": filters,
            "generated_at": utcnow().isoformat(),
        }

    groups: dict[tuple[str, str], list[Listing]] = {}
    make_groups: dict[str, list[Listing]] = {}
    for listing in listings:
        make_key = (listing.make or "").lower()
        model_key = (listing.model or "").lower()
        groups.setdefault((make_key, model_key), []).append(listing)
        make_groups.setdefault(make_key, []).append(listing)

    all_prices = [float(item.price) for item in listings if item.price is not None]
    all_mileages = [
        float(item.mileage_km) for item in listings if item.mileage_km is not None
    ]

    scored: list[CandidateContext] = []
    for listing in listings:
        make_key = (listing.make or "").lower()
        model_key = (listing.model or "").lower()
        peers = [item for item in groups[(make_key, model_key)] if item.id != listing.id]
        if len(peers) < 2 and make_key:
            peers = [
                item
                for item in make_groups.get(make_key, [])
                if item.id != listing.id
            ]

        peer_prices = [float(item.price) for item in peers if item.price is not None]
        peer_mileages = [
            float(item.mileage_km) for item in peers if item.mileage_km is not None
        ]
        price_median = (
            statistics.median(peer_prices) if peer_prices else statistics.median(all_prices)
        )
        mileage_median = (
            statistics.median(peer_mileages)
            if peer_mileages
            else (statistics.median(all_mileages) if all_mileages else None)
        )
        price = float(listing.price) if listing.price is not None else None
        mileage = float(listing.mileage_km) if listing.mileage_km is not None else None
        price_advantage = (
            (price_median - price) / price_median * 100.0
            if price is not None and price_median
            else None
        )
        mileage_advantage = (
            (mileage_median - mileage) / mileage_median * 100.0
            if mileage is not None and mileage_median
            else None
        )

        completeness_values = [
            listing.make,
            listing.model,
            listing.year,
            listing.price,
            listing.mileage_km,
            listing.fuel_type,
            listing.transmission,
            listing.power_hp,
        ]
        completeness = sum(value is not None for value in completeness_values) / len(
            completeness_values
        ) * 100.0

        score = (
            0.50 * _clamp(50.0 + (price_advantage or 0.0) * 2.0)
            + 0.25 * _clamp(50.0 + (mileage_advantage or 0.0) * 1.5)
            + 0.15 * completeness
            + 0.10 * _recency_score(listing)
        )
        scored.append(
            CandidateContext(
                listing=listing,
                score=score,
                price_advantage_pct=round(price_advantage, 2)
                if price_advantage is not None
                else None,
                mileage_advantage_pct=round(mileage_advantage, 2)
                if mileage_advantage is not None
                else None,
                peer_count=len(peers),
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    limit = int(filters.get("candidate_limit") or default_limit)
    limit = max(5, min(limit, 100))
    selected = scored[:limit]
    stats = {
        "matched_listings": len(listings),
        "analyzed_listings": len(selected),
        "median_price": round(statistics.median(all_prices), 2) if all_prices else None,
        "median_mileage": round(statistics.median(all_mileages), 2)
        if all_mileages
        else None,
        "filters": filters,
        "generated_at": utcnow().isoformat(),
    }
    return selected, stats


def recover_interrupted_runs(db: Session, older_than_minutes: int = 10) -> int:
    cutoff = utcnow() - timedelta(minutes=older_than_minutes)
    runs = db.scalars(
        select(AIAnalysisRun).where(
            AIAnalysisRun.status == "running",
            AIAnalysisRun.started_at.is_not(None),
            AIAnalysisRun.started_at < cutoff,
        )
    ).all()
    for run in runs:
        run.status = "failed"
        run.error_message = (
            "AI задачата беше прекъсната (worker restart или изтекъл timeout). "
            "Стартирайте анализа отново."
        )
        run.completed_at = utcnow()
        run.progress = 100
    if runs:
        db.commit()
    return len(runs)


def _empty_result(message: str) -> dict:
    return {
        "summary": message,
        "methodology": "Няма налични кандидати за анализ.",
        "candidate_listing_ids": [],
        "ranking": [],
        "pros": [],
        "cons": [],
        "price_comparison": "",
        "confidence": 0,
        "limitations": [message],
        "original_urls": [],
        "_validation": {"warnings": []},
    }


def run_analysis(run_id: str) -> None:
    asyncio.run(_run_analysis(run_id))


async def _run_analysis(run_id: str) -> None:
    db = SessionLocal()
    run = db.get(AIAnalysisRun, run_id)
    if run is None:
        db.close()
        return
    if run.cancel_requested:
        _cancel_run(db, run, "Cancelled before start.")
        db.close()
        return

    ai_settings = get_ai_settings(db)
    if not ai_settings.enabled:
        _fail_run(db, run, "AI модулът е изключен.")
        db.close()
        return

    started = utcnow()
    run.status = "running"
    run.started_at = started
    run.progress = 5
    run.attempt = 0
    db.commit()

    try:
        candidates, stats = select_candidates(
            db, dict(run.filter_config or {}), env_settings.ai_candidate_limit
        )
        run.input_count = len(candidates)
        run.progress = 20
        db.commit()

        if not candidates:
            run.output_json = _empty_result(
                "Не са намерени обяви, отговарящи на филтрите."
            )
            _complete_run(db, run, started)
            return

        messages = build_messages(
            task_type=run.task_type,
            candidates=candidates,
            stats=stats,
            include_descriptions=ai_settings.include_descriptions,
        )
        client = OllamaClient(
            ai_settings.base_url, ai_settings.model_name, ai_settings.timeout_seconds
        )
        candidate_map = {item.listing.id: item.listing for item in candidates}
        max_attempts = max(
            1,
            min(
                int((run.filter_config or {}).get("max_attempts") or ai_settings.max_attempts),
                5,
            ),
        )

        for attempt in range(1, max_attempts + 1):
            db.refresh(run)
            if run.cancel_requested:
                _cancel_run(db, run, "Cancelled by the user.")
                return
            run.attempt = attempt
            run.progress = 35
            run.error_message = None
            db.commit()
            try:
                content = await client.chat(messages)
                run.progress = 70
                db.commit()
                raw = extract_json(content)
                result = validate_ai_output(raw, candidate_map, run.task_type)
                if run.cancel_requested:
                    _cancel_run(db, run, "Cancelled by the user.")
                    return
                run.output_json = result
                _complete_run(db, run, started)
                return
            except OllamaModelMissing as exc:
                _fail_run(db, run, str(exc), started=started)
                return
            except (OllamaUnavailable, InvalidAIResponse, AIValidationError) as exc:
                run.error_message = str(exc)
                run.progress = 50
                db.commit()
                if attempt >= max_attempts:
                    _fail_run(
                        db,
                        run,
                        f"Analysis failed after {attempt} attempts: {exc}",
                        started=started,
                    )
                    return
                delay = min(30.0, 2.0 ** (attempt - 1)) + random.uniform(0, 0.75)
                logger.warning(
                    "AI attempt %s failed, retrying in %.1fs: %s",
                    attempt,
                    delay,
                    exc,
                    extra={"analysis_id": run.id, "error_type": type(exc).__name__},
                )
                await asyncio.sleep(delay)
            except Exception as exc:
                logger.exception(
                    "AI analysis failed",
                    extra={"analysis_id": run.id, "error_type": type(exc).__name__},
                )
                _fail_run(db, run, f"{type(exc).__name__}: {exc}", started=started)
                return
    except Exception as exc:
        logger.exception(
            "AI analysis crashed",
            extra={"analysis_id": run.id, "error_type": type(exc).__name__},
        )
        _fail_run(db, run, f"{type(exc).__name__}: {exc}", started=started)
    finally:
        db.close()


def _complete_run(db: Session, run: AIAnalysisRun, started) -> None:
    run.status = "completed"
    run.completed_at = utcnow()
    run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
    run.progress = 100
    run.error_message = None
    db.commit()


def _fail_run(db: Session, run: AIAnalysisRun, message: str, started=None) -> None:
    run.status = "failed"
    run.error_message = message[:4000]
    run.completed_at = utcnow()
    if started is not None:
        run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
    run.progress = 100
    db.commit()


def _cancel_run(db: Session, run: AIAnalysisRun, message: str) -> None:
    run.status = "cancelled"
    run.error_message = message
    run.completed_at = utcnow()
    run.progress = 100
    db.commit()
