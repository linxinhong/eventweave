"""HTTP sink that POSTs events as JSON."""

from __future__ import annotations

import ipaddress
import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from eventweave.core.event import Event
from eventweave.encoders.base import Encoder
from eventweave.runtime.sink import Sink

_FORBIDDEN_HOSTS = frozenset(
    {
        "localhost",
        "metadata",
        "metadata.google.internal",
        "metadata.google.internal.",
    }
)

_FORBIDDEN_SUFFIXES = (".local", ".internal", ".localhost")

_FORBIDDEN_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "100.64.0.0/10",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "233.252.0.0/24",
        "198.18.0.0/15",
        "240.0.0.0/4",
        "255.255.255.255/32",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Raise on HTTP redirects to prevent SSRF pivoting."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> urllib.request.Request | None:
        raise urllib.error.HTTPError(
            req.get_full_url(),
            code,
            "HTTP redirects are disabled for the http sink",
            headers,  # type: ignore[arg-type]
            fp,  # type: ignore[arg-type]
        )


def _is_forbidden_host(host: str) -> bool:
    lower = host.lower().rstrip(".")
    if lower in _FORBIDDEN_HOSTS:
        return True
    return any(lower.endswith(suffix) for suffix in _FORBIDDEN_SUFFIXES)


def _is_forbidden_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        address.is_loopback
        or address.is_link_local
        or address.is_private
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return True
    return any(address in network for network in _FORBIDDEN_NETWORKS)


def _validate_http_url(url: str, allow_internal: bool = False) -> None:
    """Validate that *url* is a safe HTTP(S) endpoint.

    Raises *ValueError* when the URL uses a forbidden scheme, host, or IP range.
    Internal/private endpoints are rejected unless *allow_internal* is true.
    """
    if allow_internal:
        return

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"http sink only supports http/https URLs, got {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise ValueError("http sink URL is missing a host")

    if _is_forbidden_host(host):
        raise ValueError(f"http sink URL points to forbidden host: {host}")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Hostname that is not an IP address: rely on host/suffix checks above.
        return

    if _is_forbidden_ip(ip):
        raise ValueError(f"http sink URL points to forbidden IP address: {host}")


class HTTPSink(Sink):
    """POST each event as JSON to a remote endpoint."""

    def __init__(
        self,
        url: str,
        timeout: float = 5.0,
        retries: int = 0,
        max_retry_duration: float = 30.0,
        backoff_factor: float = 1.0,
        allow_internal: bool = False,
        encoder: Encoder | None = None,
    ) -> None:
        _validate_http_url(url, allow_internal=allow_internal)
        self.url = url
        self.timeout = timeout
        self.retries = retries
        self.max_retry_duration = max_retry_duration
        self.backoff_factor = backoff_factor
        self.encoder = encoder
        self._success = 0
        self._failed = 0
        self._opener = urllib.request.build_opener(_NoRedirectHandler())

    def open(self) -> None:
        pass

    @staticmethod
    def _backoff(attempt: int, backoff_factor: float) -> float:
        """Exponential backoff capped at 30 seconds."""
        return float(min(backoff_factor * (2**attempt), 30.0))

    def _should_retry(self, attempt: int, start_time: float) -> bool:
        """Check whether another retry is allowed by count and total duration."""
        if attempt >= self.retries:
            return False
        if self.max_retry_duration is not None:
            elapsed = time.monotonic() - start_time
            if elapsed >= self.max_retry_duration:
                return False
        return True

    def write(self, event: Event) -> None:
        if self.encoder is not None:
            result = self.encoder.encode(event)
            if not result.success:
                self._failed += 1
                return
            payload = result.output.encode("utf-8")
            content_type = self.encoder.content_type
        else:
            payload = (
                json.dumps(event.model_dump(), default=str, ensure_ascii=False).encode("utf-8")
            )
            content_type = "application/json"
        headers = {"Content-Type": content_type}
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers=headers,
            method="POST",
        )

        start_time = time.monotonic()
        attempt = 0
        while True:
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    status = response.getcode()
                    if 200 <= status < 300:
                        self._success += 1
                        return
                    # Retry on 429 and 5xx server errors.
                    if (status == 429 or 500 <= status < 600) and self._should_retry(
                        attempt, start_time
                    ):
                        time.sleep(self._backoff(attempt, self.backoff_factor))
                        attempt += 1
                        continue
                    self._failed += 1
                    return
            except urllib.error.HTTPError as exc:
                if (exc.code == 429 or 500 <= exc.code < 600) and self._should_retry(
                    attempt, start_time
                ):
                    time.sleep(self._backoff(attempt, self.backoff_factor))
                    attempt += 1
                    continue
                self._failed += 1
                return
            except (urllib.error.URLError, TimeoutError, OSError):
                if self._should_retry(attempt, start_time):
                    time.sleep(self._backoff(attempt, self.backoff_factor))
                    attempt += 1
                    continue
                self._failed += 1
                return

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    def count(self) -> int:
        return self._success

    def failed(self) -> int:
        return self._failed
