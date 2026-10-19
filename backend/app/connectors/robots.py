from __future__ import annotations

import logging
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class RobotsGate:
    """Conservative robots.txt gate. Fails closed when robots cannot be checked."""

    def __init__(self, base_url: str, user_agent: str, timeout: float = 15.0) -> None:
        self.base_url = base_url
        self.user_agent = user_agent
        self.timeout = timeout
        self._parser: RobotFileParser | None = None
        self._allowed_when_missing = False
        self._loaded = False
        self._error: str | None = None

    async def load(self, client: httpx.AsyncClient) -> None:
        if self._loaded:
            return
        robots_url = urljoin(self.base_url, "/robots.txt")
        try:
            response = await client.get(
                robots_url,
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            self._error = str(exc)
            logger.warning("Could not fetch robots.txt: %s", exc)
            self._loaded = True
            return

        if response.status_code in {401, 403} or response.status_code >= 500:
            self._error = f"robots.txt returned HTTP {response.status_code}"
            logger.warning("robots.txt denied or unavailable: %s", self._error)
            self._loaded = True
            return

        if response.status_code == 404:
            self._allowed_when_missing = True
            self._loaded = True
            return

        if response.status_code != 200:
            self._error = f"robots.txt returned HTTP {response.status_code}"
            self._loaded = True
            return

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        self._parser = parser
        self._loaded = True

    def can_fetch(self, url: str) -> bool:
        if not self._loaded:
            return False
        if self._parser is None:
            return self._allowed_when_missing
        return self._parser.can_fetch(self.user_agent, url)

    def crawl_delay(self) -> float | None:
        if self._parser is None:
            return None
        value = self._parser.crawl_delay(self.user_agent)
        return float(value) if value is not None else None

    @property
    def error(self) -> str | None:
        return self._error
