from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.listing import Listing
from app.services.ai_gateway import AIValidationError, validate_ai_output


def listing(listing_id: str, url: str) -> Listing:
    return Listing(
        id=listing_id,
        canonical_url=url,
        title="Audi A4 2.0 TDI",
        make="Audi",
        model="A4",
        year=2018,
        price=Decimal("15000"),
        currency="EUR",
        mileage_km=150000,
        status="active",
    )


def base_output() -> dict:
    return {
        "summary": "Тестово резюме",
        "methodology": "Сравнение с подобни обяви",
        "candidate_listing_ids": ["valid-1", "ghost"],
        "ranking": [
            {
                "listing_id": "ghost",
                "rank": 1,
                "score": 95,
                "reasoning": "измислена обява",
                "pros": [],
                "cons": [],
                "price_comparison": "",
                "confidence": 9,
            },
            {
                "listing_id": "valid-1",
                "rank": 2,
                "score": 80,
                "reasoning": "добра цена",
                "pros": ["нисък пробег"],
                "cons": ["липсва сервизна история"],
                "price_comparison": "под пазарната",
                "confidence": 7,
            },
        ],
        "pros": [],
        "cons": [],
        "price_comparison": "",
        "confidence": 7,
        "limitations": ["липсват данни"],
        "original_urls": ["https://evil.example/ghost"],
    }


def test_validation_drops_hallucinated_listing() -> None:
    valid = listing("valid-1", "https://cars.example/offer/1")
    result = validate_ai_output(base_output(), {"valid-1": valid}, "best_deals")
    assert result["candidate_listing_ids"] == ["valid-1"]
    assert [item["listing_id"] for item in result["ranking"]] == ["valid-1"]
    assert result["original_urls"] == ["https://cars.example/offer/1"]
    assert result["candidate_details"]["valid-1"]["title"] == "Audi A4 2.0 TDI"
    assert result["_validation"]["warnings"]


def test_validation_rejects_empty_ranking() -> None:
    output = base_output()
    output["ranking"] = []
    output["candidate_listing_ids"] = []
    with pytest.raises(AIValidationError):
        validate_ai_output(output, {}, "best_deals")


def test_validation_rejects_invalid_schema() -> None:
    output = base_output()
    output.pop("summary")
    with pytest.raises(AIValidationError):
        validate_ai_output(output, {}, "best_deals")
