"""Minimal SSE consumer for the EventWeave HTTP serve endpoint.

Run inside the demo stack container or locally against a serve endpoint:

    python examples/demo-stack/receivers/http_sse_consumer.py http://127.0.0.1:8081/events
"""

from __future__ import annotations

import sys
import urllib.request


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8081/events"
    print(f"Connecting to {url}", file=sys.stderr)

    req = urllib.request.Request(url, method="GET", headers={"Accept": "text/event-stream"})
    with urllib.request.urlopen(req) as resp:
        for raw in resp:
            line = raw.decode("utf-8").rstrip()
            if line.startswith("data: "):
                print(line[6:])
            elif line.startswith("data:"):
                print(line[5:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
