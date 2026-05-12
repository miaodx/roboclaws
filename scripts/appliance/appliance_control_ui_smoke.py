#!/usr/bin/env python3
"""Smoke-test the appliance Control UI proxy and Gateway websocket auth path."""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import ssl
import struct
import sys
import urllib.request
from urllib.parse import urljoin, urlparse, urlunparse


def _http_get(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "roboclaws-appliance-smoke/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(512).decode("utf-8", errors="replace")
        return resp.status, body


def _ws_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, "/", "", "", ""))


def _origin(base_url: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _read_until(sock: socket.socket, marker: bytes) -> tuple[bytes, bytes]:
    data = bytearray()
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("socket closed while reading headers")
        data.extend(chunk)
    marker_index = data.index(marker) + len(marker)
    return bytes(data[:marker_index]), bytes(data[marker_index:])


def _read_exact(sock: socket.socket, size: int, buffered: bytearray) -> bytes:
    chunks = bytearray()
    if buffered:
        take = min(size, len(buffered))
        chunks.extend(buffered[:take])
        del buffered[:take]
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise RuntimeError("socket closed while reading websocket frame")
        chunks.extend(chunk)
    return bytes(chunks)


def _send_frame(sock: socket.socket, payload: bytes, opcode: int = 1) -> None:
    header = bytearray([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length <= 0xFFFF:
        header.extend([0x80 | 126, *struct.pack("!H", length)])
    else:
        header.extend([0x80 | 127, *struct.pack("!Q", length)])
    mask = os.urandom(4)
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    sock.sendall(bytes(header) + mask + masked)


def _send_text(sock: socket.socket, payload: dict[str, object]) -> None:
    _send_frame(sock, json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def _read_text(sock: socket.socket, buffered: bytearray) -> str:
    while True:
        b1, b2 = _read_exact(sock, 2, buffered)
        opcode = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", _read_exact(sock, 2, buffered))[0]
        elif length == 127:
            length = struct.unpack("!Q", _read_exact(sock, 8, buffered))[0]
        mask = _read_exact(sock, 4, buffered) if masked else b""
        payload = _read_exact(sock, length, buffered) if length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 1:
            return payload.decode("utf-8")
        if opcode == 8:
            raise RuntimeError(f"websocket closed: {payload.decode('utf-8', errors='replace')}")
        if opcode == 9:
            _send_frame(sock, payload, opcode=10)


def _connect_ws(ws_url: str, origin: str, timeout: float) -> tuple[socket.socket, bytearray]:
    parsed = urlparse(ws_url)
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    host = parsed.hostname or ""
    raw = socket.create_connection((host, port), timeout=timeout)
    raw.settimeout(timeout)
    sock: socket.socket
    if parsed.scheme == "wss":
        sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
    else:
        sock = raw
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {parsed.netloc}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        f"Origin: {origin}\r\n"
        "User-Agent: roboclaws-appliance-smoke/1.0\r\n"
        "\r\n"
    )
    sock.sendall(request.encode("ascii"))
    response_bytes, leftover = _read_until(sock, b"\r\n\r\n")
    response = response_bytes.decode("iso-8859-1", errors="replace")
    status_line = response.splitlines()[0] if response else ""
    if " 101 " not in status_line:
        raise RuntimeError(f"websocket upgrade failed: {status_line}")
    return sock, bytearray(leftover)


def smoke(base_url: str, token: str, timeout: float) -> None:
    base_url = base_url.rstrip("/")
    status, body = _http_get(urljoin(base_url + "/", "health"), timeout)
    if status != 200 or "ok" not in body.lower():
        raise RuntimeError(f"/health returned {status}: {body!r}")
    status, body = _http_get(base_url + "/", timeout)
    if status != 200 or "openclaw" not in body.lower():
        raise RuntimeError(f"/ did not look like OpenClaw UI, status={status}")

    ws_url = _ws_url(base_url)
    origin = _origin(base_url)
    sock, buffered = _connect_ws(ws_url, origin, timeout)
    with sock:
        challenge = json.loads(_read_text(sock, buffered))
        if challenge.get("event") != "connect.challenge":
            raise RuntimeError(f"expected connect.challenge, got {challenge!r}")
        nonce = str(challenge.get("payload", {}).get("nonce", ""))
        if not nonce:
            raise RuntimeError(f"connect.challenge missing nonce: {challenge!r}")
        _send_text(
            sock,
            {
                "type": "req",
                "id": "appliance-smoke-connect",
                "method": "connect",
                "params": {
                    "minProtocol": 3,
                    "maxProtocol": 3,
                    "client": {
                        "id": "openclaw-control-ui",
                        "mode": "webchat",
                        "version": "roboclaws-smoke",
                        "displayName": "roboclaws appliance smoke",
                        "platform": sys.platform,
                        "instanceId": "roboclaws-appliance-smoke",
                    },
                    "role": "operator",
                    "scopes": [
                        "operator.approvals",
                        "operator.pairing",
                        "operator.read",
                        "operator.talk.secrets",
                        "operator.write",
                    ],
                    "caps": [],
                    "commands": [],
                    "permissions": {},
                    "auth": {"token": token},
                    "locale": "en-US",
                    "userAgent": "roboclaws-appliance-smoke/1.0",
                },
            },
        )
        response = json.loads(_read_text(sock, buffered))
        if response.get("ok") is not True:
            raise RuntimeError(f"gateway connect failed: {response!r}")
        payload = response.get("payload", {})
        if not isinstance(payload, dict) or payload.get("type") != "hello-ok":
            raise RuntimeError(f"unexpected gateway connect response: {response!r}")
    print(f"OK appliance Control UI websocket auth via {base_url}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url", default=os.environ.get("ROBOCLAWS_PUBLIC_URL", "http://127.0.0.1:8080")
    )
    parser.add_argument(
        "--token", default=os.environ.get("OPENCLAW_TOKEN") or os.environ.get("DEMO_PASSWORD", "")
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    if not args.token:
        raise SystemExit("--token or OPENCLAW_TOKEN/DEMO_PASSWORD is required")
    smoke(args.url, args.token, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
