"""Minimal HTTP receiver for EventWeave http sink demos.

Run with:

    python examples/receivers/http_receiver.py

Then in another terminal:

    eventweave run dist/ecommerce_refund_flow_semantic \
      --sink http --url http://127.0.0.1:8080/events --no-wait
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    received = 0

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        event = json.loads(body.decode("utf-8"))
        _Handler.received += 1
        print(json.dumps(event, ensure_ascii=False))
        self.send_response(200)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        # Suppress default request logging.
        pass


def main() -> int:
    host = "127.0.0.1"
    port = 8080
    server = HTTPServer((host, port), _Handler)
    print(f"Listening on http://{host}:{port}/events", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\nReceived {_Handler.received} events", file=sys.stderr)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
