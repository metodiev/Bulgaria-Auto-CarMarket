from __future__ import annotations

import hashlib
import logging
import mimetypes
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.listing import Listing, ListingImage
from app.services.storage import ObjectStorage, StorageError
from app.services.url_safety import UnsafeUrlError, validate_http_url

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}


class ImageError(Exception):
    pass


async def download_image(
    url: str,
    *,
    max_bytes: int,
    timeout: float = 20.0,
) -> tuple[bytes, str, str]:
    headers = {
        "User-Agent": "BulgariaAutoCarMarket/1.0 (self-hosted; image cache)",
        "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8",
    }
    current_url = url
    async with httpx.AsyncClient(
        headers=headers, timeout=httpx.Timeout(timeout), follow_redirects=False
    ) as client:
        for _ in range(4):
            validate_http_url(current_url)
            async with client.stream("GET", current_url) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ImageError("Redirect without Location header.")
                    current_url = urljoin(current_url, location)
                    continue
                if response.status_code != 200:
                    raise ImageError(f"Image request returned HTTP {response.status_code}.")
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type not in ALLOWED_IMAGE_TYPES:
                    raise ImageError(f"Unexpected image MIME type: {content_type!r}.")
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    raise ImageError("Image is larger than the configured limit.")
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ImageError("Image exceeded the configured limit.")
                    chunks.append(chunk)
                data = b"".join(chunks)
                checksum = hashlib.sha256(data).hexdigest()
                return data, content_type, checksum
    raise ImageError("Too many image redirects.")


def _extension(content_type: str, url: str) -> str:
    return ALLOWED_IMAGE_TYPES.get(content_type) or mimetypes.guess_extension(content_type) or ".bin"


async def save_listing_images(
    db: Session,
    listing: Listing,
    urls: list[str],
    *,
    source_slug: str,
    enabled: bool,
    settings: Settings,
    storage: ObjectStorage | None = None,
) -> list[ListingImage]:
    storage = storage or ObjectStorage(settings)
    images: list[ListingImage] = []
    for url in urls[: settings.image_max_per_listing]:
        image = db.scalar(
            select(ListingImage).where(
                ListingImage.listing_id == listing.id,
                ListingImage.original_url == url,
            )
        )
        if image is None:
            image = ListingImage(
                listing_id=listing.id,
                original_url=url,
                download_status="pending",
            )
            db.add(image)
            db.flush()
        images.append(image)

        if image.download_status == "downloaded" and image.storage_key:
            continue
        if not enabled:
            image.download_status = "skipped"
            continue

        try:
            data, content_type, checksum = await download_image(
                url, max_bytes=settings.image_max_bytes
            )
            extension = _extension(content_type, url)
            key = f"listings/{source_slug}/{listing.id}/{checksum[:2]}/{checksum}{extension}"
            storage.put_bytes(key, data, content_type)
            image.storage_key = key
            image.checksum_sha256 = checksum
            image.mime_type = content_type
            image.size_bytes = len(data)
            image.download_status = "downloaded"
            image.downloaded_at = datetime.now(timezone.utc)
            image.error_message = None
        except (ImageError, UnsafeUrlError, StorageError, httpx.HTTPError) as exc:
            image.download_status = "failed"
            image.error_message = str(exc)[:1000]
            logger.warning(
                "Image download failed: %s",
                exc,
                extra={"listing_id": listing.id, "url": url, "error_type": "image"},
            )
    return images
