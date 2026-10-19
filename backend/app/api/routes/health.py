from __future__ import annotations

import logging

import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    database_ok = True
    database_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        database_ok = False
        database_error = str(exc)

    redis_ok = True
    redis_error = None
    try:
        client = redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        client.close()
    except Exception as exc:
        redis_ok = False
        redis_error = str(exc)

    if not database_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": False,
                "redis": redis_ok,
                "error": database_error,
            },
        )

    return {
        "status": "ok" if redis_ok else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": database_ok,
        "redis": redis_ok,
        "redis_error": redis_error,
        "ai_enabled_default": settings.ai_enabled,
    }
