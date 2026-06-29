"""Minimal Syslog TCP consumer for the EventWeave syslog_tcp serve endpoint.

Run inside the demo stack container or locally:

    python examples/demo-stack/receivers/syslog_tcp_receiver.py 127.0.0.1 5515
"""

from __future__ import annotations

import socket
import sys


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5515

    print(f"Connecting to {host}:{port}", file=sys.stderr)
    with socket.create_connection((host, port)) as sock:
        sock.settimeout(None)
        buffer = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                print(line.decode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
