from __future__ import annotations

from pydantic import BaseModel


class StatBucket(BaseModel):
    key: str
    count: int
    avg_price: float | None = None


class MarketStatsOut(BaseModel):
    total_active: int
    new_last_7_days: int
    price_changes_30d: int
    avg_price: float | None
    median_price: float | None
    by_source: list[StatBucket]
    by_make: list[StatBucket]
    by_model: list[StatBucket]
    by_region: list[StatBucket]
    by_fuel: list[StatBucket]
    by_year: list[StatBucket]
