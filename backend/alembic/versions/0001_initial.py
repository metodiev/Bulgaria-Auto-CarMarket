"""Initial schema for Bulgaria Auto CarMarket.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.common import JSONType

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("robots_url", sa.String(500), nullable=True),
        sa.Column("terms_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("capabilities", JSONType, nullable=False),
        sa.Column("config", JSONType, nullable=False),
        sa.Column("last_health_status", sa.String(32), nullable=True),
        sa.Column("last_health_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sources_slug", "sources", ["slug"], unique=True)
    op.create_index("ix_sources_status", "sources", ["status"])
    op.create_index("ix_sources_enabled", "sources", ["enabled"])

    op.create_table(
        "search_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("filters", JSONType, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_jobs_source_id", "search_jobs", ["source_id"])
    op.create_index("ix_search_jobs_enabled", "search_jobs", ["enabled"])
    op.create_index("ix_search_jobs_next_run_at", "search_jobs", ["next_run_at"])

    op.create_table(
        "listings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_listing_id", sa.String(120), nullable=False),
        sa.Column("canonical_url", sa.String(500), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("make", sa.String(80), nullable=True),
        sa.Column("model", sa.String(160), nullable=True),
        sa.Column("generation", sa.String(80), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("mileage_km", sa.Integer(), nullable=True),
        sa.Column("fuel_type", sa.String(40), nullable=True),
        sa.Column("engine_volume", sa.Numeric(4, 1), nullable=True),
        sa.Column("power_kw", sa.Integer(), nullable=True),
        sa.Column("power_hp", sa.Integer(), nullable=True),
        sa.Column("transmission", sa.String(40), nullable=True),
        sa.Column("body_type", sa.String(40), nullable=True),
        sa.Column("drivetrain", sa.String(40), nullable=True),
        sa.Column("condition", sa.String(40), nullable=True),
        sa.Column("color", sa.String(80), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("region", sa.String(120), nullable=True),
        sa.Column("seller_type", sa.String(40), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "duplicate_of_id",
            sa.String(36),
            sa.ForeignKey("listings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("raw_data", JSONType, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_id", "source_listing_id", name="uq_listings_source_reference"
        ),
    )
    op.create_index("ix_listings_source_id", "listings", ["source_id"])
    op.create_index("ix_listings_canonical_url", "listings", ["canonical_url"])
    op.create_index("ix_listings_make", "listings", ["make"])
    op.create_index("ix_listings_model", "listings", ["model"])
    op.create_index("ix_listings_year", "listings", ["year"])
    op.create_index("ix_listings_fuel_type", "listings", ["fuel_type"])
    op.create_index("ix_listings_transmission", "listings", ["transmission"])
    op.create_index("ix_listings_city", "listings", ["city"])
    op.create_index("ix_listings_region", "listings", ["region"])
    op.create_index("ix_listings_first_seen_at", "listings", ["first_seen_at"])
    op.create_index("ix_listings_last_seen_at", "listings", ["last_seen_at"])
    op.create_index("ix_listings_status", "listings", ["status"])
    op.create_index("ix_listings_make_model_year", "listings", ["make", "model", "year"])
    op.create_index(
        "ix_listings_status_last_seen", "listings", ["status", "last_seen_at"]
    )
    op.create_index("ix_listings_price", "listings", ["price"])
    op.create_index("ix_listings_mileage_km", "listings", ["mileage_km"])

    op.create_table(
        "listing_images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "listing_id",
            sa.String(36),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_url", sa.String(1000), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("download_status", sa.String(20), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("listing_id", "original_url", name="uq_listing_images_url"),
    )
    op.create_index("ix_listing_images_listing_id", "listing_images", ["listing_id"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "listing_id",
            sa.String(36),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_price_history_listing_id", "price_history", ["listing_id"])
    op.create_index(
        "ix_price_history_listing_observed",
        "price_history",
        ["listing_id", "observed_at"],
    )

    op.create_table(
        "listing_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "listing_id",
            sa.String(36),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("html_storage_key", sa.String(500), nullable=True),
        sa.Column("screenshot_storage_key", sa.String(500), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_listing_snapshots_listing_id", "listing_snapshots", ["listing_id"])

    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "search_job_id",
            sa.String(36),
            sa.ForeignKey("search_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("triggered_by", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pages_fetched", sa.Integer(), nullable=False),
        sa.Column("listings_found", sa.Integer(), nullable=False),
        sa.Column("listings_created", sa.Integer(), nullable=False),
        sa.Column("listings_updated", sa.Integer(), nullable=False),
        sa.Column("listings_unchanged", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stats", JSONType, nullable=False),
        sa.Column("celery_task_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scrape_runs_source_id", "scrape_runs", ["source_id"])
    op.create_index("ix_scrape_runs_search_job_id", "scrape_runs", ["search_job_id"])
    op.create_index("ix_scrape_runs_status", "scrape_runs", ["status"])
    op.create_index(
        "ix_scrape_runs_source_created", "scrape_runs", ["source_id", "created_at"]
    )

    op.create_table(
        "scraper_errors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("scrape_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("error_type", sa.String(80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scraper_errors_run_id", "scraper_errors", ["run_id"])
    op.create_index("ix_scraper_errors_source_id", "scraper_errors", ["source_id"])
    op.create_index("ix_scraper_errors_occurred_at", "scraper_errors", ["occurred_at"])

    op.create_table(
        "deduplication_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "listing_a_id",
            sa.String(36),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "listing_b_id",
            sa.String(36),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", JSONType, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("listing_a_id", "listing_b_id", name="uq_dedup_pair"),
    )
    op.create_index(
        "ix_deduplication_candidates_listing_a_id",
        "deduplication_candidates",
        ["listing_a_id"],
    )
    op.create_index(
        "ix_deduplication_candidates_listing_b_id",
        "deduplication_candidates",
        ["listing_b_id"],
    )
    op.create_index(
        "ix_deduplication_candidates_status",
        "deduplication_candidates",
        ["status"],
    )
    op.create_index("ix_dedup_status_score", "deduplication_candidates", ["status", "score"])

    op.create_table(
        "ai_analysis_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("filter_config", JSONType, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_count", sa.Integer(), nullable=False),
        sa.Column("output_json", JSONType, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("celery_task_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_analysis_runs_task_type", "ai_analysis_runs", ["task_type"])
    op.create_index("ix_ai_analysis_runs_status", "ai_analysis_runs", ["status"])
    op.create_index("ix_ai_analysis_runs_created_at", "ai_analysis_runs", ["created_at"])

    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("default_task", sa.String(40), nullable=False),
        sa.Column("auto_analyze", sa.Boolean(), nullable=False),
        sa.Column("include_descriptions", sa.Boolean(), nullable=False),
        sa.Column("analyze_images", sa.Boolean(), nullable=False),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_settings")
    op.drop_table("ai_analysis_runs")
    op.drop_table("deduplication_candidates")
    op.drop_table("scraper_errors")
    op.drop_table("scrape_runs")
    op.drop_table("listing_snapshots")
    op.drop_table("price_history")
    op.drop_table("listing_images")
    op.drop_table("listings")
    op.drop_table("search_jobs")
    op.drop_table("sources")
