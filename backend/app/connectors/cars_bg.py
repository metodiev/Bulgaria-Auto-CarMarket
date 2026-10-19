from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.connectors.base import (
    BaseConnector,
    ConnectorError,
    DiscoveredListing,
    NormalizedListing,
)
from app.services.http import fetch_text
from app.services.rate_limit import RateLimiter

BASE_URL = "https://www.cars.bg"
OFFER_HOSTS = {"cars.bg", "www.cars.bg"}

MAKE_ALIASES = {
    "vw": "Volkswagen",
    "mercedes": "Mercedes-Benz",
    "citroen": "Citroen",
    "skoda": "Skoda",
    "seat": "Seat",
    "mini": "MINI",
    "mg": "MG",
    "ds": "DS",
}

MAKES = [
    "Abarth",
    "Alfa Romeo",
    "Alpine",
    "Aston Martin",
    "Audi",
    "Bentley",
    "BMW",
    "BYD",
    "Cadillac",
    "Chery",
    "Chevrolet",
    "Chrysler",
    "Citroen",
    "Cupra",
    "Dacia",
    "Daewoo",
    "Dodge",
    "DS",
    "Fiat",
    "Ford",
    "Geely",
    "Genesis",
    "GMC",
    "Honda",
    "Hummer",
    "Hyundai",
    "Infiniti",
    "Isuzu",
    "Iveco",
    "Jaguar",
    "Jeep",
    "Kia",
    "Lada",
    "Lamborghini",
    "Lancia",
    "Land Rover",
    "Lexus",
    "Lincoln",
    "Lotus",
    "Maserati",
    "Mazda",
    "McLaren",
    "Mercedes-Benz",
    "MG",
    "MINI",
    "Mitsubishi",
    "Nissan",
    "Opel",
    "Peugeot",
    "Polestar",
    "Porsche",
    "RAM",
    "Renault",
    "Rolls-Royce",
    "Rover",
    "Saab",
    "Seat",
    "Skoda",
    "Smart",
    "SsangYong",
    "Subaru",
    "Suzuki",
    "Tesla",
    "Toyota",
    "Volkswagen",
    "Volvo",
    "VW",
    "Mercedes",
]

CITY_TO_REGION = {
    "София": "София-град",
    "Пловдив": "Пловдив",
    "Варна": "Варна",
    "Бургас": "Бургас",
    "Русе": "Русе",
    "Стара Загора": "Стара Загора",
    "Плевен": "Плевен",
    "Добрич": "Добрич",
    "Сливен": "Сливен",
    "Шумен": "Шумен",
    "Перник": "Перник",
    "Хасково": "Хасково",
    "Пазарджик": "Пазарджик",
    "Ямбол": "Ямбол",
    "Благоевград": "Благоевград",
    "Велико Търново": "Велико Търново",
    "Враца": "Враца",
    "Габрово": "Габрово",
    "Видин": "Видин",
    "Кърджали": "Кърджали",
    "Кюстендил": "Кюстендил",
    "Ловеч": "Ловеч",
    "Монтана": "Монтана",
    "Разград": "Разград",
    "Силистра": "Силистра",
    "Смолян": "Смолян",
    "Търговище": "Търговище",
}

BODY_TYPES = {
    "комби": "estate",
    "седан": "sedan",
    "хечбек": "hatchback",
    "джип": "suv",
    "suv": "suv",
    "купе": "coupe",
    "кабриолет": "convertible",
    "ван": "van",
    "пикап": "pickup",
    "миниван": "minivan",
}

FUEL_TYPES = {
    "дизел": "diesel",
    "бензин": "petrol",
    "газ/бензин": "lpg_petrol",
    "газ": "lpg",
    "метан": "cng",
    "електрически": "electric",
    "електро": "electric",
    "хибрид": "hybrid",
    "плъгин": "plug_in_hybrid",
}

TRANSMISSIONS = {
    "автоматични": "automatic",
    "автоматик": "automatic",
    "ръчни": "manual",
    "полуавтоматични": "semi_automatic",
    "вариатор": "cvt",
}


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _decimal_from_text(value: str) -> float | None:
    raw = _clean(value).replace("\u00a0", "").replace(" ", "")
    raw = re.sub(r"[^\d.,-]", "", raw)
    if not raw or raw in {"-", ".", ","}:
        return None
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts[-1]) == 3 and len(parts) > 1:
            raw = raw.replace(",", "")
        else:
            raw = raw.replace(",", ".")
    try:
        return float(Decimal(raw))
    except (InvalidOperation, ValueError):
        return None


def parse_price(text: str | None) -> tuple[float | None, str | None]:
    value = _clean(text)
    if not value or "договаряне" in value.lower():
        return None, None
    currency = "EUR" if "EUR" in value.upper() else ("BGN" if "BGN" in value.upper() or "ЛВ" in value.upper() else None)
    return _decimal_from_text(value), currency


def parse_mileage(text: str | None) -> int | None:
    match = re.search(r"([\d\s.,]+)\s*км", _clean(text), re.IGNORECASE)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def parse_year(text: str | None) -> int | None:
    matches = re.findall(r"\b(19\d{2}|20\d{2})\b", _clean(text))
    if not matches:
        return None
    return int(matches[0])


def parse_power_hp(text: str | None) -> int | None:
    match = re.search(r"(\d{2,4})\s*к\.?\s*с\.?", _clean(text), re.IGNORECASE)
    return int(match.group(1)) if match else None


def parse_engine_volume(text: str | None) -> float | None:
    value = _clean(text)
    match = re.search(r"(\d{3,4})\s*см", value, re.IGNORECASE)
    if match:
        return round(int(match.group(1)) / 1000.0, 1)
    match = re.search(r"\b([0-8]\.\d)\b", value)
    if match:
        return float(match.group(1))
    return None


def parse_body_type(text: str | None) -> str | None:
    lowered = _clean(text).lower()
    for needle, value in BODY_TYPES.items():
        if needle in lowered:
            return value
    return None


def parse_fuel_type(text: str | None) -> str | None:
    lowered = _clean(text).lower()
    for needle, value in FUEL_TYPES.items():
        if needle in lowered:
            return value
    return None


def parse_transmission(text: str | None) -> str | None:
    lowered = _clean(text).lower()
    for needle, value in TRANSMISSIONS.items():
        if needle in lowered:
            return value
    return None


def parse_drivetrain(text: str | None) -> str | None:
    lowered = _clean(text).lower()
    if "4x4" in lowered or "4х4" in lowered or "quattro" in lowered:
        return "awd"
    if "задно" in lowered:
        return "rwd"
    if "предно" in lowered:
        return "fwd"
    return None


def parse_condition(text: str | None) -> str | None:
    lowered = _clean(text).lower()
    if "употребяван" in lowered:
        return "used"
    if "за части" in lowered:
        return "for_parts"
    if re.search(r"\bнов\b", lowered):
        return "new"
    return None


def parse_make_model(title: str) -> tuple[str | None, str | None]:
    cleaned = _clean(title)
    lowered = cleaned.lower()
    for candidate in sorted(MAKES, key=len, reverse=True):
        needle = candidate.lower()
        if lowered == needle or lowered.startswith(f"{needle} "):
            display = MAKE_ALIASES.get(needle, candidate)
            return display, cleaned[len(candidate) :].strip() or None
    return None, cleaned or None


def parse_location(footer: str | None) -> tuple[str | None, str | None, str | None]:
    value = _clean(footer)
    seller_type = "private" if "частно лице" in value.lower() else ("dealer" if value else None)
    if not value:
        return None, None, seller_type
    parts = [part.strip() for part in value.split(",") if part.strip()]
    city = parts[-1] if parts else None
    if city and city.lower() in {"частно лице", "дилър", "автокъща"}:
        city = None
    region = CITY_TO_REGION.get(city or "", city)
    return city, region, seller_type


def parse_listing_cards(html: str) -> list[DiscoveredListing]:
    soup = BeautifulSoup(html, "lxml")
    results: list[DiscoveredListing] = []
    seen: set[str] = set()
    for card in soup.select("div.offer"):
        link = card.select_one('a[href*="/offer/"]')
        if link is None:
            continue
        url = urljoin(BASE_URL, link.get("href", ""))
        if url in seen:
            continue
        seen.add(url)
        reference_el = card.select_one("[data-reference]")
        source_listing_id = (
            reference_el.get("data-reference") if reference_el is not None else None
        ) or url.rstrip("/").split("/")[-1]
        title = _clean(card.get("title") or "")
        if not title:
            title_el = card.select_one("h5.observable")
            title = _clean(title_el.get_text(" ", strip=True) if title_el else "")
        price_el = card.select_one(".price")
        price_text = _clean(price_el.get_text(" ", strip=True) if price_el else "")
        secondary = " ".join(
            _clean(el.get_text(" ", strip=True)) for el in card.select(".card__secondary")
        )
        footer_el = card.select_one(".card__footer")
        footer = _clean(footer_el.get_text(" ", strip=True) if footer_el else "")
        subtitle_el = card.select_one(".card__subtitle")
        subtitle = _clean(subtitle_el.get_text(" ", strip=True) if subtitle_el else "")
        media = card.select_one(".mdc-card__media")
        image_url = None
        if media is not None:
            style = media.get("style", "")
            match = re.search(r'url\("?([^")]+)"?\)', style)
            if match:
                image_url = match.group(1)
        results.append(
            DiscoveredListing(
                url=url,
                summary={
                    "source_listing_id": source_listing_id,
                    "title": title,
                    "price_text": price_text,
                    "secondary": secondary,
                    "footer": footer,
                    "subtitle": subtitle,
                    "image_url": image_url,
                },
            )
        )
    return results


def parse_image_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    seen: set[str] = set()
    for image in soup.find_all("img", src=True):
        src = image.get("src", "")
        if not src.startswith("https://g1-bg.cars.bg/"):
            continue
        if not re.search(r"/20\d{2}-\d{2}-\d{2}[^/]*/", src):
            continue
        if not re.search(r"\.(?:jpe?g|png|webp)$", src, re.IGNORECASE):
            continue
        if src.endswith("o.jpg") or src.endswith("b.jpg"):
            # Prefer the standard "b" variant over the original "o" variant.
            if src.endswith("o.jpg"):
                candidate = src[:-5] + "b.jpg"
                if candidate not in seen:
                    seen.add(candidate)
                    urls.append(candidate)
                continue
        if src not in seen:
            seen.add(src)
            urls.append(src)
    return urls


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def parse_offer_page(
    html: str, url: str, summary: dict | None = None
) -> NormalizedListing:
    summary = summary or {}
    soup = BeautifulSoup(html, "lxml")
    outer = soup.select_one("div.text-copy")
    title_el = outer.select_one("h2") if outer is not None else soup.find("h2")
    title = _clean(title_el.get_text(" ", strip=True) if title_el else "")
    if not title:
        title = _clean(summary.get("title"))

    price_el = soup.select_one(".offer-price")
    price_text = _clean(price_el.get_text(" ", strip=True) if price_el else "")
    if not price_text:
        price_text = _clean(summary.get("price_text"))
    price, currency = parse_price(price_text)

    params_text = _clean(outer.get_text(" ", strip=True) if outer is not None else "")
    if title and params_text:
        params_text = params_text.replace(title, " ", 1)
    if price_text:
        params_text = params_text.replace(price_text, " ", 1)

    description_el = soup.select_one(".offer-notes")
    description = _clean(description_el.get_text(" ", strip=True) if description_el else None)
    features_el = soup.select_one(".description.text-copy")
    features = _clean(features_el.get_text(" ", strip=True) if features_el else None)

    make, model = parse_make_model(title or summary.get("title", ""))
    mobile_text = " ".join(
        filter(
            None,
            [
                params_text,
                _clean(summary.get("secondary")),
                _clean(summary.get("footer")),
            ],
        )
    )
    city, region, seller_type = parse_location(summary.get("footer"))
    if city is None:
        address_match = re.search(
            r"\d{4}\s+([^,]+),\s*([^,]+)", soup.get_text(" ", strip=True)
        )
        if address_match:
            city = _clean(address_match.group(1))
            region = CITY_TO_REGION.get(city, _clean(address_match.group(2)))

    power_hp = parse_power_hp(mobile_text) or parse_power_hp(title)
    power_kw = round(power_hp * 0.7355) if power_hp else None
    images = parse_image_urls(html)
    if not images:
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            images = [og_image["content"]]

    source_listing_id = (
        _clean(summary.get("source_listing_id"))
        or _canonical_url(url).rstrip("/").split("/")[-1]
    )

    return NormalizedListing(
        source_listing_id=source_listing_id,
        canonical_url=_canonical_url(url),
        title=title or _clean(summary.get("title")) or source_listing_id,
        make=make,
        model=model,
        year=parse_year(params_text) or parse_year(summary.get("secondary")),
        price=price,
        currency=currency,
        mileage_km=parse_mileage(mobile_text),
        fuel_type=parse_fuel_type(mobile_text),
        engine_volume=parse_engine_volume(mobile_text) or parse_engine_volume(title),
        power_kw=power_kw,
        power_hp=power_hp,
        transmission=parse_transmission(mobile_text),
        body_type=parse_body_type(mobile_text),
        drivetrain=parse_drivetrain(mobile_text),
        condition=parse_condition(mobile_text),
        color=_color_from_summary(params_text),
        city=city,
        region=region,
        seller_type=seller_type,
        description=description or features,
        raw_data={
            "card": summary,
            "price_text": price_text,
            "params_text": params_text,
            "features": features,
            "description": description,
            "images_count": len(images),
        },
    )


def _color_from_summary(params_text: str) -> str | None:
    parts = [part.strip() for part in params_text.split(",") if part.strip()]
    if len(parts) < 2:
        return None
    candidate = parts[-1]
    if len(candidate) <= 50 and not re.search(r"\d", candidate):
        return candidate
    return None


class CarsBgConnector(BaseConnector):
    slug = "cars-bg"
    base_url = BASE_URL
    allowed_hosts = OFFER_HOSTS
    capabilities = {
        "scraping": True,
        "images": True,
        "archives": True,
        "verified": True,
        "robots": "User-agent: * / Disallow: (empty)",
    }

    def __init__(self, source, settings=None) -> None:
        super().__init__(source, settings)
        config = source.config or {}
        self.rate_limiter = RateLimiter(
            float(config.get("requests_per_second", 0.5))
        )
        self.retry_limit = int(
            config.get("retry_limit", self.settings.scraper_retry_limit)
        )
        self.backoff_seconds = float(
            config.get("backoff_seconds", self.settings.scraper_backoff_seconds)
        )
        self.timeout = float(
            config.get("timeout_seconds", self.settings.request_timeout_seconds)
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.7",
            },
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=False,
        )

    def search_url(self, page: int) -> str:
        return f"{self.base_url}/carslist.php?page={page}"

    async def discover_listings(self, page: int = 1) -> list[DiscoveredListing]:
        if page < 1:
            raise ConnectorError("Page number must be positive.")
        url = self.search_url(page)
        async with self._client() as client:
            result = await fetch_text(
                client,
                url,
                allowed_hosts=self.allowed_hosts,
                max_bytes=6_000_000,
                retry_limit=self.retry_limit,
                backoff_seconds=self.backoff_seconds,
                rate_limiter=self.rate_limiter,
            )
        return parse_listing_cards(result.text)

    async def fetch_listing(self, url: str) -> str:
        async with self._client() as client:
            result = await fetch_text(
                client,
                url,
                allowed_hosts=self.allowed_hosts,
                max_bytes=6_000_000,
                retry_limit=self.retry_limit,
                backoff_seconds=self.backoff_seconds,
                rate_limiter=self.rate_limiter,
            )
        return result.text

    def normalize_listing(
        self, html: str, url: str, summary: dict | None = None
    ) -> NormalizedListing:
        return parse_offer_page(html, url, summary)

    def fetch_images(self, listing: NormalizedListing, html: str) -> list[str]:
        return parse_image_urls(html)

    async def health_check(self) -> dict:
        async with self._client() as client:
            try:
                response = await client.get(self.base_url, timeout=self.timeout)
            except httpx.HTTPError as exc:
                return {"ok": False, "message": str(exc)}
        return {
            "ok": response.status_code < 500,
            "status_code": response.status_code,
            "message": "Cars.bg responded.",
        }
