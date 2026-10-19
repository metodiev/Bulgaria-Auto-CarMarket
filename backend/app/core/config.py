from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Bulgaria Auto CarMarket"
    app_version: str = "1.0.0"
    app_env: str = "production"
    log_level: str = "INFO"

    admin_api_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    database_url: str = (
        "postgresql+psycopg://carmarket:carmarket@localhost:5432/carmarket"
    )
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str | None = None
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "carmarket"
    s3_secure: bool = False

    scrape_user_agent: str = (
        "BulgariaAutoCarMarket/1.0 (self-hosted; respectful crawler; "
        "contact: admin@example.invalid)"
    )
    request_timeout_seconds: float = 30.0
    scraper_retry_limit: int = 3
    scraper_backoff_seconds: float = 2.0
    image_download_enabled: bool = False
    image_max_bytes: int = 8_000_000
    image_max_per_listing: int = 10
    archive_enabled: bool = False
    archive_max_bytes: int = 8_000_000
    stale_listing_days: int = 14

    ai_enabled: bool = False
    ai_auto_analyze: bool = False
    ai_analyze_images: bool = False
    ai_include_descriptions: bool = True
    ai_default_task: str = "best_deals"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ai_max_concurrency: int = 1
    ai_timeout_seconds: float = 180.0
    ai_max_attempts: int = 3
    ai_candidate_limit: int = 40

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
