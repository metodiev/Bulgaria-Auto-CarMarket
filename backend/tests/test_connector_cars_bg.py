from __future__ import annotations

from pathlib import Path

from app.connectors.cars_bg import (
    parse_condition,
    parse_listing_cards,
    parse_make_model,
    parse_offer_page,
    parse_price,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_listing_cards() -> None:
    cards = parse_listing_cards((FIXTURES / "cars_bg_list.html").read_text(encoding="utf-8"))
    assert len(cards) == 2
    first = cards[0]
    assert first.url.endswith("/offer/6ad21400a5b417721705d8c2")
    assert first.summary["source_listing_id"] == "6ad21400a5b417721705d8c2"
    assert first.summary["title"] == "VW Tiguan Фейс, Италия"
    assert first.summary["price_text"] == "8,480 EUR"
    assert first.summary["footer"] == "частно лице, Пловдив"
    assert first.summary["image_url"].endswith("6ad212cbae47cf82060b6ba6b.jpg")
    assert cards[1].summary["price_text"] == "цена по договаряне"


def test_parse_offer_page() -> None:
    html = (FIXTURES / "cars_bg_offer.html").read_text(encoding="utf-8")
    summary = {
        "source_listing_id": "6acb2611989e30674702a316",
        "title": "Audi A4 Allroad 3.0D|272HP|8ZF",
        "price_text": "14,999 EUR",
        "secondary": "2017, Дизел, 235000 км, Автоматични скорости",
        "footer": "АУТО ДИЙЛС 2020, Кюстендил",
    }
    listing = parse_offer_page(
        html, "https://www.cars.bg/offer/6acb2611989e30674702a316?utm=1", summary
    )
    assert listing.source_listing_id == "6acb2611989e30674702a316"
    assert listing.canonical_url == "https://www.cars.bg/offer/6acb2611989e30674702a316"
    assert listing.title == "Audi A4 Allroad 3.0D|272HP|8ZF"
    assert listing.make == "Audi"
    assert listing.model == "A4 Allroad 3.0D|272HP|8ZF"
    assert listing.year == 2017
    assert listing.price == 14999
    assert listing.currency == "EUR"
    assert listing.mileage_km == 235000
    assert listing.fuel_type == "diesel"
    assert listing.engine_volume == 3.0
    assert listing.power_hp == 272
    assert listing.power_kw == 200
    assert listing.transmission == "automatic"
    assert listing.body_type == "estate"
    assert listing.condition == "used"
    assert listing.color == "Тъмно сив металик"
    assert listing.city == "Кюстендил"
    assert listing.region == "Кюстендил"
    assert listing.seller_type == "dealer"
    assert listing.description and "AUDI A4 ALLROAD" in listing.description
    assert listing.raw_data["images_count"] == 2


def test_price_and_make_parsing() -> None:
    assert parse_price("14,999 EUR") == (14999.0, "EUR")
    assert parse_price("8 480 лв.") == (8480.0, "BGN")
    assert parse_price("цена по договаряне") == (None, None)
    assert parse_make_model("VW Passat 2.3") == ("Volkswagen", "Passat 2.3")
    assert parse_make_model("Mercedes-Benz C 220") == ("Mercedes-Benz", "C 220")
    assert parse_condition("Употребяван автомобил") == "used"
    assert parse_condition("За части") == "for_parts"
