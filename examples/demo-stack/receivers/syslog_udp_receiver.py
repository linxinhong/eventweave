"""Minimal Syslog UDP consumer for the EventWeave syslog_udp serve endpoint.

The server learns client addresses from the first datagram. This script sends a
registration datagram, then prints all forwarded messages.

Run inside the demo stack container or locally:

    python examples/demo-stack/receivers/syslog_udp_receiver.py 127.0.0.1 5514
"""

from __future__ import annotations

import socket
import sys


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5514

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(None)
        # Sending a registration datagram lets the server learn our address.
        sock.sendto(b"register\n", (host, port))
        print(f"Registered with {host}:{port}", file=sys.stderr)
        while True:
            data, addr = sock.recvfrom(4096)
            print(data.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    raise SystemExit(main())
