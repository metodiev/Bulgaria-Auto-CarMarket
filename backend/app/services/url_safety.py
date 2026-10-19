from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    pass


def _is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def validate_http_url(
    url: str,
    *,
    allowed_hosts: set[str] | None = None,
    resolve_dns: bool = True,
) -> str:
    if not url or len(url) > 2000:
        raise UnsafeUrlError("URL is empty or too long.")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Only http and https URLs are allowed.")
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no hostname.")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("URLs with embedded credentials are not allowed.")

    host = parsed.hostname.lower().rstrip(".")
    if allowed_hosts:
        allowed = {item.lower().rstrip(".") for item in allowed_hosts}
        if not any(host == candidate or host.endswith(f".{candidate}") for candidate in allowed):
            raise UnsafeUrlError(f"Host {host!r} is not allowed for this source.")

    if resolve_dns:
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
            }
        except socket.gaierror as exc:
            raise UnsafeUrlError(f"Could not resolve host {host!r}.") from exc
        if not addresses:
            raise UnsafeUrlError(f"Host {host!r} did not resolve.")
        if any(not _is_public_ip(address) for address in addresses):
            raise UnsafeUrlError(f"Host {host!r} resolves to a non-public address.")

    return url
