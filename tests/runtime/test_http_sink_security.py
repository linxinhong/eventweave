import urllib.error
import urllib.request

import pytest

from eventweave.core.event import Event
from eventweave.runtime.sinks.http import HTTPSink


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/events",
        "http://10.0.0.1/events",
        "http://192.168.1.1/events",
        "http://172.16.0.1/events",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/events",
        "http://localhost/events",
        "http://metadata/events",
        "http://metadata.google.internal/",
        "http://my-service.local/events",
        "http://my-service.internal/events",
        "file:///etc/passwd",
        "ftp://example.com/events",
    ],
)
def test_http_sink_rejects_internal_url(url: str) -> None:
    with pytest.raises(ValueError):
        HTTPSink(url)


def test_http_sink_accepts_internal_url_when_allowed() -> None:
    # Construction should succeed when explicitly allowed.
    sink = HTTPSink("http://127.0.0.1/events", allow_internal=True)
    assert sink.url == "http://127.0.0.1/events"


def test_http_sink_rejects_missing_scheme() -> None:
    with pytest.raises(ValueError):
        HTTPSink("example.com/events")


def test_http_sink_blocks_redirect(monkeypatch) -> None:
    """Redirects are disabled so a public URL cannot pivot to an internal host."""
    sink = HTTPSink("http://example.com/events")

    def _fake_open(request: urllib.request.Request, timeout: float | None = None) -> object:
        raise urllib.error.HTTPError(
            request.get_full_url(),
            302,
            "Found",
            {"Location": "http://127.0.0.1/secret"},
            None,
        )

    monkeypatch.setattr(sink._opener, "open", _fake_open)

    event = Event(
        event_id="e1",
        scenario_id="sc1",
        source_id="src1",
        event_type="login",
        event_time="2024-01-01T00:00:00Z",
    )
    sink.write(event)
    # The redirect is treated as a failed write, not followed.
    assert sink.failed() == 1
    assert sink.count() == 0
