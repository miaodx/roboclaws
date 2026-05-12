#!/usr/bin/env python3
"""Print a usable TCP port, preferring a requested port when it is free."""

from __future__ import annotations

import argparse
import socket


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("preferred_port", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host = _probe_host(args.host)
    if not _port_accepting(host, args.preferred_port):
        print(args.preferred_port)
        return 0

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        print(sock.getsockname()[1])
    return 0


def _probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
