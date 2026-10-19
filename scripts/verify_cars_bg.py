"""Conservative live smoke test for the verified Cars.bg connector.

Usage (from the repository root, with backend dependencies installed):

    python scripts/verify_cars_bg.py

The script fetches robots.txt, one search page and one offer page only. It does not
bypass any protection and does not download images.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.connectors.cars_bg import CarsBgConnector, parse_listing_cards, parse_offer_page
from app.connectors.robots import RobotsGate
from app.core.config import settings
from app.models.source import Source


async def main() -> int:
    source = Source(
        slug="cars-bg",
        name="Cars.bg",
        base_url="https://www.cars.bg/",
        status="verified",
        enabled=True,
        capabilities={},
        config={
            "requests_per_second": 0.5,
            "retry_limit": 2,
            "backoff_seconds": 1,
            "timeout_seconds": 25,
        },
    )
    connector = CarsBgConnector(source, settings)
    async with httpx.AsyncClient(
        headers={"User-Agent": connector.user_agent},
        timeout=httpx.Timeout(25),
        follow_redirects=False,
    ) as client:
        robots = RobotsGate(connector.base_url, connector.user_agent)
        await robots.load(client)
        print(f"robots.txt error: {robots.error or 'none'}")
        print(f"search page allowed: {robots.can_fetch(connector.search_url(1))}")
        search = await client.get(connector.search_url(1), timeout=25)
        print(f"search HTTP: {search.status_code}, bytes: {len(search.content)}")
        cards = parse_listing_cards(search.text)
        print(f"cards parsed: {len(cards)}")
        if not cards:
            return 1
        first = cards[0]
        print(f"first card: {first.summary['title']} | {first.summary['price_text']}")
        print(f"allowed offer page: {robots.can_fetch(first.url)}")
        detail = await client.get(first.url, timeout=25)
        print(f"offer HTTP: {detail.status_code}, bytes: {len(detail.content)}")
        normalized = parse_offer_page(detail.text, first.url, first.summary)
        for key, value in asdict(normalized).items():
            if key != "raw_data":
                print(f"  {key}: {value}")
        print(f"  images: {normalized.raw_data.get('images_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
