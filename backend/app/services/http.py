from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import httpx

from app.services.rate_limit import RateLimiter
from app.services.url_safety import UnsafeUrlError, validate_http_url

logger = logging.getLogger(__name__)


class ResponseTooLarge(Exception):
    pass


class RetryableHttpError(Exception):
    def __init__(self, status_code: int, retry_after: float | None = None) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        self.retry_after = retry_after


@dataclass(slots=True)
class FetchResult:
    url: str
    status_code: int
    text: str
    headers: dict[str, str]


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            from datetime import datetime, timezone

            return max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
        except Exception:
            return None


async def _request_once(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_bytes: int,
    rate_limiter: RateLimiter | None,
) -> tuple[int, dict[str, str], bytes, str | None]:
    if rate_limiter is not None:
        await rate_limiter.wait()

    async with client.stream("GET", url) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        location = headers.get("location")
        if response.status_code in {301, 302, 303, 307, 308}:
            return response.status_code, headers, b"", location

        if response.status_code in {429, 500, 502, 503, 504}:
            retry_after = _retry_after_seconds(headers.get("retry-after"))
            raise RetryableHttpError(response.status_code, retry_after)

        response.raise_for_status()
        content_length = headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            raise ResponseTooLarge(
                f"Response is larger than the configured limit ({max_bytes} bytes)."
            )

        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise ResponseTooLarge(
                    f"Response exceeded the configured limit ({max_bytes} bytes)."
                )
            chunks.append(chunk)
        return response.status_code, headers, b"".join(chunks), None


async def fetch_text(
    client: httpx.AsyncClient,
    url: str,
    *,
    allowed_hosts: set[str] | None = None,
    max_bytes: int = 5_000_000,
    max_redirects: int = 3,
    retry_limit: int = 3,
    backoff_seconds: float = 2.0,
    rate_limiter: RateLimiter | None = None,
) -> FetchResult:
    current_url = url
    for redirect_index in range(max_redirects + 1):
        validate_http_url(current_url, allowed_hosts=allowed_hosts)

        for attempt in range(retry_limit + 1):
            try:
                status, headers, content, location = await _request_once(
                    client,
                    current_url,
                    max_bytes=max_bytes,
                    rate_limiter=rate_limiter,
                )
                if status in {301, 302, 303, 307, 308}:
                    if not location:
                        raise httpx.HTTPStatusError(
                            "Redirect without Location header",
                            request=httpx.Request("GET", current_url),
                            response=httpx.Response(status),
                        )
                    if redirect_index >= max_redirects:
                        raise httpx.TooManyRedirects("Too many redirects.")
                    current_url = urljoin(current_url, location)
                    break

                encoding = headers.get("content-encoding", "")
                if encoding:
                    # httpx already decompresses the streamed body.
                    pass
                charset = _charset_from_headers(headers)
                text = content.decode(charset, errors="replace")
                return FetchResult(
                    url=str(current_url),
                    status_code=status,
                    text=text,
                    headers=headers,
                )
            except RetryableHttpError as exc:
                if attempt >= retry_limit:
                    raise
                delay = exc.retry_after if exc.retry_after is not None else backoff_seconds * (2**attempt)
                delay = min(delay, 60.0) + random.uniform(0, 0.5)
                logger.warning(
                    "Retrying request after HTTP error",
                    extra={"url": current_url, "error_type": "http_retry"},
                )
                await asyncio.sleep(delay)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt >= retry_limit:
                    raise
                delay = backoff_seconds * (2**attempt) + random.uniform(0, 0.5)
                logger.warning(
                    "Retrying request after transport error: %s",
                    exc,
                    extra={"url": current_url, "error_type": "transport_retry"},
                )
                await asyncio.sleep(delay)
        else:
            raise UnsafeUrlError("Request failed after all retries.")
    raise UnsafeUrlError("Too many redirects.")


def _charset_from_headers(headers: dict[str, str]) -> str:
    content_type = headers.get("content-type", "")
    for part in content_type.split(";")[1:]:
        part = part.strip()
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip().strip('"')
    return "utf-8"
