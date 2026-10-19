from __future__ import annotations

import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings

BACKEND = Path(__file__).resolve().parents[1]


def test_alembic_initial_migration() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        db_path = Path(handle.name)
    url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    previous = settings.database_url
    settings.database_url = url
    try:
        config = Config(str(BACKEND / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND / "alembic"))
        command.upgrade(config, "head")

        engine = create_engine(url)
        tables = set(inspect(engine).get_table_names())
        assert {
            "sources",
            "search_jobs",
            "listings",
            "listing_images",
            "price_history",
            "listing_snapshots",
            "scrape_runs",
            "scraper_errors",
            "deduplication_candidates",
            "ai_analysis_runs",
            "ai_settings",
        }.issubset(tables)
        engine.dispose()
    finally:
        settings.database_url = previous
        db_path.unlink(missing_ok=True)
