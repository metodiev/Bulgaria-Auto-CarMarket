from __future__ import annotations

from tests.conftest import make_listing

ADMIN = {"X-Admin-Key": "test-admin-key"}


def test_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] is True
    assert body["status"] in {"ok", "degraded"}


def test_mobile_cors_origins(client) -> None:
    for origin in ("capacitor://localhost", "http://localhost", "https://localhost"):
        response = client.options(
            "/api/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Admin-Key",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin


def test_sources_and_admin_guards(client, sources) -> None:
    response = client.get("/api/sources")
    assert response.status_code == 200
    by_slug = {item["slug"]: item for item in response.json()}
    assert by_slug["cars-bg"]["status"] == "verified"
    assert by_slug["mobile-bg"]["enabled"] is False

    blocked = client.put(
        f"/api/sources/{by_slug['mobile-bg']['id']}",
        json={"enabled": True},
        headers=ADMIN,
    )
    assert blocked.status_code == 409

    unauthorized = client.put(
        f"/api/sources/{by_slug['cars-bg']['id']}", json={"enabled": True}
    )
    assert unauthorized.status_code == 401

    updated = client.put(
        f"/api/sources/{by_slug['cars-bg']['id']}",
        json={"config": {"max_pages_per_run": 1}},
        headers=ADMIN,
    )
    assert updated.status_code == 200
    assert updated.json()["config"]["max_pages_per_run"] == 1
    assert updated.json()["config"]["max_listings_per_run"] == 20


def test_listings_api(client, sources, db) -> None:
    listing = make_listing(db, sources["cars-bg"])
    db.commit()

    response = client.get("/api/listings?make=Audi")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["source"]["slug"] == "cars-bg"
    assert body["items"][0]["id"] == listing.id

    detail = client.get(f"/api/listings/{listing.id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Audi A4 2.0 TDI"

    history = client.get(f"/api/listings/{listing.id}/price-history")
    assert history.status_code == 200
    assert history.json() == []

    options = client.get("/api/listings/filters")
    assert options.status_code == 200
    assert "Audi" in options.json()["makes"]

    stats = client.get("/api/statistics/market")
    assert stats.status_code == 200
    assert stats.json()["total_active"] == 1
    assert stats.json()["avg_price"] == 15000
    assert stats.json()["by_model"][0]["key"] == "A4"


def test_missing_listing(client) -> None:
    assert client.get("/api/listings/does-not-exist").status_code == 404


def test_source_health_check_for_gated_connector(client, sources) -> None:
    mobile = sources["mobile-bg"]
    response = client.post(
        f"/api/sources/{mobile.id}/health", headers=ADMIN
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["status"] == "needs_permission"
    refreshed = next(
        item for item in client.get("/api/sources").json() if item["id"] == mobile.id
    )
    assert refreshed["last_health_status"] == "needs_permission"
    assert refreshed["last_health_checked_at"] is not None


def test_search_job_scheduler_toggle(client, sources) -> None:
    response = client.get("/api/search-jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 1
    job = jobs[0]
    assert job["source"]["slug"] == "cars-bg"
    assert job["enabled"] is False

    unauthorized = client.put(
        f"/api/search-jobs/{job['id']}", json={"enabled": True}
    )
    assert unauthorized.status_code == 401

    updated = client.put(
        f"/api/search-jobs/{job['id']}",
        json={"enabled": True, "interval_minutes": 60},
        headers=ADMIN,
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    assert updated.json()["interval_minutes"] == 60
    assert updated.json()["next_run_at"] is not None


def test_ai_disabled_analysis(client, sources) -> None:
    settings = client.get("/api/ai/settings")
    assert settings.status_code == 200
    assert settings.json()["enabled"] is False

    response = client.post(
        "/api/ai/analyze",
        json={"task_type": "best_deals", "filters": {}},
        headers=ADMIN,
    )
    assert response.status_code == 409


def test_ai_health_is_available_without_ollama(client, sources) -> None:
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["model"] == "qwen3:4b"


def test_scrape_run_admin_and_permission_guards(client, sources) -> None:
    unauthorized = client.post(
        "/api/scrape-runs",
        json={"source_id": sources["cars-bg"].id, "max_pages": 1, "max_listings": 1},
    )
    assert unauthorized.status_code == 401

    mobile = sources["mobile-bg"]
    blocked = client.post(
        "/api/scrape-runs",
        json={"source_id": mobile.id, "max_pages": 1, "max_listings": 1},
        headers=ADMIN,
    )
    assert blocked.status_code == 409


def test_empty_collections(client, sources) -> None:
    for path in ("/api/errors", "/api/ai/results", "/api/dedup/candidates"):
        response = client.get(path)
        assert response.status_code == 200
