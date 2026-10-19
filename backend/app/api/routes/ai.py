from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.models.ai import AIAnalysisRun
from app.models.common import utcnow
from app.schemas.ai import (
    AIAnalysisOutput,
    AIAnalysisResultOut,
    AIAnalysisRunOut,
    AIAnalyzeRequest,
    AIHealthOut,
    AIModelInfo,
    AIModelsOut,
    AISettingsOut,
    AISettingsUpdate,
)
from app.schemas.common import Page
from app.services.ai_analysis import (
    AIDisabled,
    AIQueueError,
    create_analysis_run,
    get_ai_settings,
    update_ai_settings,
)
from app.services.ai_gateway import OllamaClient, OllamaError

router = APIRouter(prefix="/ai", tags=["ai"])


def _settings_row(db: Session):
    return get_ai_settings(db)


@router.get("/settings", response_model=AISettingsOut)
def read_settings(db: Session = Depends(get_db)) -> AISettingsOut:
    return AISettingsOut.model_validate(_settings_row(db))


@router.put(
    "/settings",
    response_model=AISettingsOut,
    dependencies=[Depends(require_admin)],
)
def write_settings(
    payload: AISettingsUpdate, db: Session = Depends(get_db)
) -> AISettingsOut:
    row = update_ai_settings(db, payload)
    return AISettingsOut.model_validate(row)


@router.get("/models", response_model=AIModelsOut)
async def list_models(db: Session = Depends(get_db)) -> AIModelsOut:
    row = _settings_row(db)
    client = OllamaClient(row.base_url, row.model_name, row.timeout_seconds)
    try:
        models = await client.list_models()
    except OllamaError as exc:
        return AIModelsOut(reachable=False, models=[], error=str(exc))
    return AIModelsOut(
        reachable=True,
        models=[
            AIModelInfo(
                name=str(item.get("name") or item.get("model") or ""),
                size=item.get("size"),
                modified_at=item.get("modified_at"),
            )
            for item in models
            if item.get("name") or item.get("model")
        ],
    )


@router.get("/health", response_model=AIHealthOut)
async def ai_health(db: Session = Depends(get_db)) -> AIHealthOut:
    row = _settings_row(db)
    configured = bool(row.base_url and row.model_name)
    if not configured:
        return AIHealthOut(
            configured=False,
            enabled=row.enabled,
            reachable=False,
            model=row.model_name,
            model_available=False,
            message="Ollama URL или модел не са конфигурирани.",
        )
    client = OllamaClient(row.base_url, row.model_name, row.timeout_seconds)
    try:
        models = await client.list_models()
    except OllamaError as exc:
        return AIHealthOut(
            configured=True,
            enabled=row.enabled,
            reachable=False,
            model=row.model_name,
            model_available=False,
            message=str(exc),
        )
    names = {
        str(item.get("name") or item.get("model") or "").lower()
        for item in models
    }
    model_available = any(
        name == row.model_name.lower()
        or name.startswith(f"{row.model_name.lower()}:")
        for name in names
    )
    message = (
        "Ollama е достъпен и моделът е инсталиран."
        if model_available
        else (
            f"Ollama е достъпен, но моделът {row.model_name!r} липсва. "
            f"Изпълнете: docker compose exec ollama ollama pull {row.model_name}"
        )
    )
    return AIHealthOut(
        configured=True,
        enabled=row.enabled,
        reachable=True,
        model=row.model_name,
        model_available=model_available,
        message=message,
    )


@router.post(
    "/analyze",
    response_model=AIAnalysisRunOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def analyze(
    payload: AIAnalyzeRequest, db: Session = Depends(get_db)
) -> AIAnalysisRunOut:
    try:
        run = create_analysis_run(db, payload)
    except AIDisabled as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AIQueueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AIAnalysisRunOut.model_validate(run)


@router.get("/results", response_model=Page[AIAnalysisRunOut])
def list_results(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    task_type: str | None = None,
    db: Session = Depends(get_db),
) -> Page[AIAnalysisRunOut]:
    conditions = []
    if status:
        conditions.append(AIAnalysisRun.status == status)
    if task_type:
        conditions.append(AIAnalysisRun.task_type == task_type)
    total = db.scalar(select(func.count(AIAnalysisRun.id)).where(*conditions)) or 0
    rows = db.scalars(
        select(AIAnalysisRun)
        .where(*conditions)
        .order_by(AIAnalysisRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for row in rows:
        item = AIAnalysisRunOut.model_validate(row)
        item.output_json = None
        items.append(item)
    return Page[AIAnalysisRunOut](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/jobs/{run_id}", response_model=AIAnalysisRunOut)
def get_job(run_id: str, db: Session = Depends(get_db)) -> AIAnalysisRunOut:
    run = db.get(AIAnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI задачата не е намерена.")
    return AIAnalysisRunOut.model_validate(run)


@router.get("/results/{run_id}", response_model=AIAnalysisResultOut)
def get_result(run_id: str, db: Session = Depends(get_db)) -> AIAnalysisResultOut:
    run = db.get(AIAnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI резултатът не е намерен.")
    result = AIAnalysisResultOut.model_validate(run)
    if run.output_json:
        try:
            result.output = AIAnalysisOutput.model_validate(run.output_json)
        except Exception:
            result.output = None
    return result


@router.post(
    "/jobs/{run_id}/retry",
    response_model=AIAnalysisRunOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def retry_job(run_id: str, db: Session = Depends(get_db)) -> AIAnalysisRunOut:
    old = db.get(AIAnalysisRun, run_id)
    if old is None:
        raise HTTPException(status_code=404, detail="AI задачата не е намерена.")
    request = AIAnalyzeRequest(
        task_type=old.task_type,  # type: ignore[arg-type]
        filters=dict(old.filter_config or {}),
    )
    try:
        run = create_analysis_run(db, request, triggered_by="retry")
    except AIDisabled as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AIQueueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AIAnalysisRunOut.model_validate(run)


@router.post(
    "/jobs/{run_id}/cancel",
    response_model=AIAnalysisRunOut,
    dependencies=[Depends(require_admin)],
)
def cancel_job(run_id: str, db: Session = Depends(get_db)) -> AIAnalysisRunOut:
    run = db.get(AIAnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI задачата не е намерена.")
    if run.status in {"completed", "failed", "cancelled"}:
        return AIAnalysisRunOut.model_validate(run)
    run.cancel_requested = True
    if run.status == "pending":
        run.status = "cancelled"
        run.completed_at = utcnow()
        run.progress = 100
    db.commit()
    db.refresh(run)
    return AIAnalysisRunOut.model_validate(run)
