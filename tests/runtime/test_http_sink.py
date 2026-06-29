import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from eventweave.core.event import Event
from eventweave.runtime.sinks.http import HTTPSink


def _event(event_id: str = "e1") -> Event:
    return Event(
        event_id=event_id,
        scenario_id="sc1",
        source_id="src1",
        event_type="login",
        event_time="2024-01-01T00:00:00Z",
    )


class _OKHandler(BaseHTTPRequestHandler):
    received: list[bytes] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        _OKHandler.received.append(body)
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


class _FailHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        self.send_response(500)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


def _start_server(handler: type[BaseHTTPRequestHandler]) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_http_sink_posts_events():
    _OKHandler.received = []
    server = _start_server(_OKHandler)
    try:
        url = f"http://127.0.0.1:{server.server_port}/events"
        sink = HTTPSink(url, allow_internal=True)
        sink.open()
        sink.write(_event("e1"))
        sink.write(_event("e2"))
        sink.close()

        assert sink.count() == 2
        assert sink.failed() == 0
        assert len(_OKHandler.received) == 2
        assert json.loads(_OKHandler.received[0])["event_id"] == "e1"
    finally:
        server.shutdown()
        server.server_close()


def test_http_sink_counts_failures():
    server = _start_server(_FailHandler)
    try:
        url = f"http://127.0.0.1:{server.server_port}/events"
        sink = HTTPSink(url, allow_internal=True)
        sink.open()
        sink.write(_event())
        sink.close()

        assert sink.count() == 0
        assert sink.failed() == 1
    finally:
        server.shutdown()
        server.server_close()


def test_http_sink_retry_on_server_error():
    class _OnceHandler(BaseHTTPRequestHandler):
        requests = 0

        def do_POST(self) -> None:  # noqa: N802
            _OnceHandler.requests += 1
            if _OnceHandler.requests == 1:
                self.send_response(503)
            else:
                self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = _start_server(_OnceHandler)
    try:
        url = f"http://127.0.0.1:{server.server_port}/events"
        sink = HTTPSink(url, retries=1, allow_internal=True)
        sink.open()
        sink.write(_event())
        sink.close()

        assert sink.count() == 1
        assert sink.failed() == 0
        assert _OnceHandler.requests == 2
    finally:
        server.shutdown()
        server.server_close()


def test_http_sink_no_retry_on_4xx():
    class _NotFoundHandler(BaseHTTPRequestHandler):
        requests = 0

        def do_POST(self) -> None:  # noqa: N802
            _NotFoundHandler.requests += 1
            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = _start_server(_NotFoundHandler)
    try:
        url = f"http://127.0.0.1:{server.server_port}/events"
        sink = HTTPSink(url, retries=2, allow_internal=True)
        sink.open()
        sink.write(_event())
        sink.close()

        assert sink.count() == 0
        assert sink.failed() == 1
        assert _NotFoundHandler.requests == 1
    finally:
        server.shutdown()
        server.server_close()


def test_http_sink_retry_on_429():
    class _RateLimitHandler(BaseHTTPRequestHandler):
        requests = 0

        def do_POST(self) -> None:  # noqa: N802
            _RateLimitHandler.requests += 1
            if _RateLimitHandler.requests == 1:
                self.send_response(429)
            else:
                self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = _start_server(_RateLimitHandler)
    try:
        url = f"http://127.0.0.1:{server.server_port}/events"
        sink = HTTPSink(url, retries=2, backoff_factor=0.01, allow_internal=True)
        sink.open()
        sink.write(_event())
        sink.close()

        assert sink.count() == 1
        assert sink.failed() == 0
        assert _RateLimitHandler.requests == 2
    finally:
        server.shutdown()
        server.server_close()


def test_http_sink_respects_max_retry_duration():
    class _SlowFailHandler(BaseHTTPRequestHandler):
        requests = 0

        def do_POST(self) -> None:  # noqa: N802
            _SlowFailHandler.requests += 1
            self.send_response(503)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = _start_server(_SlowFailHandler)
    try:
        url = f"http://127.0.0.1:{server.server_port}/events"
        sink = HTTPSink(
            url,
            retries=100,
            max_retry_duration=0.05,
            backoff_factor=0.01,
            allow_internal=True,
        )
        sink.open()
        sink.write(_event())
        sink.close()

        assert sink.count() == 0
        assert sink.failed() == 1
        # Should give up well before exhausting all retries.
        assert _SlowFailHandler.requests < 100
    finally:
        server.shutdown()
        server.server_close()
