from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_compose_services_and_profiles() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    for name in (
        "frontend",
        "backend",
        "scraper-worker",
        "ai-worker",
        "scheduler",
        "postgres",
        "redis",
        "ollama",
        "minio",
    ):
        assert name in services
    assert services["ai-worker"]["profiles"] == ["ai"]
    assert services["ollama"]["profiles"] == ["ai"]
    assert "minio-init" in services
    assert (
        services["minio"]["depends_on"]["minio-init"]["condition"]
        == "service_completed_successfully"
    )
    assert "healthcheck" in services["backend"]
    assert "healthcheck" in services["postgres"]
    assert "healthcheck" in services["redis"]
    assert services["backend"]["environment"]["RUN_MIGRATIONS"] == "1"


def test_non_root_container_users() -> None:
    backend = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    worker = (ROOT / "backend" / "Dockerfile.worker").read_text(encoding="utf-8")
    frontend = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    assert "USER app" in backend
    assert "USER pwuser" in worker
    assert "nginx-unprivileged" in frontend


def test_ai_defaults_are_qwen3_4b_and_disabled() -> None:
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OLLAMA_MODEL=qwen3:4b" in env
    assert "AI_ENABLED=false" in env
    assert "AI_AUTO_ANALYZE=false" in env
    assert "AI_ANALYZE_IMAGES=false" in env
