"""HTTP sink that POSTs events as JSON."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from eventweave.core.event import Event
from eventweave.runtime.sink import Sink


class HTTPSink(Sink):
    """POST each event as JSON to a remote endpoint."""

    def __init__(
        self,
        url: str,
        timeout: float = 5.0,
        retries: int = 0,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.retries = retries
        self._success = 0
        self._failed = 0

    def open(self) -> None:
        pass

    def write(self, event: Event) -> None:
        payload = json.dumps(event.model_dump(), default=str, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers=headers,
            method="POST",
        )

        attempt = 0
        while True:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    status = response.getcode()
                    if 200 <= status < 300:
                        self._success += 1
                        return
                    # Non-2xx response: treat as failure.
                    self._failed += 1
                    return
            except urllib.error.HTTPError as exc:
                # Retry only on 5xx server errors.
                if 500 <= exc.code < 600 and attempt < self.retries:
                    attempt += 1
                    continue
                self._failed += 1
                return
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < self.retries:
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
