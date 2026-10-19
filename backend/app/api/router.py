from fastapi import APIRouter

from app.api.routes import (
    ai,
    dedup,
    errors,
    health,
    listings,
    scrape_runs,
    search_jobs,
    sources,
    statistics,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(listings.router)
api_router.include_router(statistics.router)
api_router.include_router(sources.router)
api_router.include_router(scrape_runs.router)
api_router.include_router(search_jobs.router)
api_router.include_router(errors.router)
api_router.include_router(ai.router)
api_router.include_router(dedup.router)
