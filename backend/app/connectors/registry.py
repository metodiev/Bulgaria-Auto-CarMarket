from __future__ import annotations

from app.connectors.auto_bg import AutoBgConnector
from app.connectors.base import BaseConnector
from app.connectors.bazar_bg import BazarBgConnector
from app.connectors.carmarket_bg import CarMarketBgConnector
from app.connectors.cars_bg import CarsBgConnector
from app.connectors.mobile_bg import MobileBgConnector
from app.connectors.olx_bg import OlxBgConnector
from app.models.source import Source

CONNECTORS: dict[str, type[BaseConnector]] = {
    "cars-bg": CarsBgConnector,
    "mobile-bg": MobileBgConnector,
    "auto-bg": AutoBgConnector,
    "olx-bg": OlxBgConnector,
    "bazar-bg": BazarBgConnector,
    "carmarket-bg": CarMarketBgConnector,
}


def get_connector(source: Source) -> BaseConnector:
    connector_class = CONNECTORS.get(source.slug)
    if connector_class is None:
        raise ValueError(f"No connector registered for source {source.slug!r}.")
    return connector_class(source)
