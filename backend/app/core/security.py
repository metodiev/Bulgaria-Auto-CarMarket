from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_admin_key(x_admin_key: str | None) -> None:
    if not x_admin_key or not secrets.compare_digest(
        x_admin_key, settings.admin_api_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалиден администраторски ключ.",
        )


def require_admin(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    verify_admin_key(x_admin_key)
