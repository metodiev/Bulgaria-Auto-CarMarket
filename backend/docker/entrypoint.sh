#!/usr/bin/env sh
set -eu

if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
    python - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
last_error = None
for attempt in range(1, 61):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("database is ready", flush=True)
        break
    except Exception as exc:  # pragma: no cover - startup-only path
        last_error = exc
        print(f"database not ready ({attempt}/60): {exc}", flush=True)
        time.sleep(2)
else:
    raise SystemExit(f"database did not become ready: {last_error}")
PY
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    alembic upgrade head
    python -m app.seed
fi

exec "$@"
