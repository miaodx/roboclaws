"""Redacted provider HTTP timing proxy for live coding-agent runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from aiohttp import ClientError, ClientSession, ClientTimeout, web

from roboclaws.agents.provider_timing_contract import (
    PROVIDER_REQUEST_METRIC_SCHEMA,
    PROVIDER_REQUEST_METRICS_FILENAME,
)

PROVIDER_TIMING_PROXY_ENV = "ROBOCLAWS_PROVIDER_TIMING_PROXY"
PROVIDER_TIMING_PROXY_UPSTREAM_ENV = "ROBOCLAWS_TIMING_PROXY_UPSTREAM_BASE_URL"
PROVIDER_TIMING_PROXY_BIND_HOST_ENV = "ROBOCLAWS_TIMING_PROXY_BIND_HOST"
PROVIDER_TIMING_PROXY_BIND_PORT_ENV = "ROBOCLAWS_TIMING_PROXY_BIND_PORT"
PROVIDER_TIMING_PROXY_READY_ENV = "ROBOCLAWS_TIMING_PROXY_READY_PATH"

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
SAFE_PROVIDER_REQUEST_ID_HEADERS = (
    "x-request-id",
    "request-id",
    "x-amzn-requestid",
    "cf-ray",
)


@dataclass(frozen=True)
class ProviderTimingProxyConfig:
    upstream_base_url: str
    metrics_path: Path
    bind_host: str = "127.0.0.1"
    bind_port: int = 0
    agent_engine: str = ""
    provider_profile: str = ""
    model: str = ""

    def normalized_upstream(self) -> str:
        return self.upstream_base_url.rstrip("/") + "/"


CONFIG_APP_KEY = web.AppKey("provider_timing_proxy_config", ProviderTimingProxyConfig)
CLIENT_SESSION_APP_KEY = web.AppKey("provider_timing_proxy_client_session", ClientSession)


@dataclass(frozen=True)
class ProviderTimingProxyHandle:
    process: subprocess.Popen[bytes]
    bind_url: str
    upstream_base_url: str
    metrics_path: Path
    ready_path: Path


def provider_timing_proxy_enabled(env: Mapping[str, str] | None = None) -> bool:
    value = (env or os.environ).get(PROVIDER_TIMING_PROXY_ENV, "")
    return value.lower() in {"1", "true", "yes", "on"}


def free_local_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def replace_base_url_origin(base_url: str, *, bind_url: str) -> str:
    """Return a client base URL that keeps the original path under the proxy origin."""

    original = urlsplit(base_url)
    proxy = urlsplit(bind_url)
    return urlunsplit((proxy.scheme, proxy.netloc, original.path.rstrip("/"), "", ""))


async def start_provider_timing_proxy(
    *,
    repo_root: Path,
    run_dir: Path,
    upstream_base_url: str,
    agent_engine: str,
    provider_profile: str,
    model: str = "",
    bind_host: str | None = None,
    bind_port: int | None = None,
    startup_timeout_s: float = 10.0,
) -> ProviderTimingProxyHandle:
    """Start the proxy as a subprocess and wait for its ready artifact."""

    if not upstream_base_url:
        raise RuntimeError("provider timing proxy requires an upstream base URL")
    bind_host = bind_host or os.environ.get(PROVIDER_TIMING_PROXY_BIND_HOST_ENV) or "127.0.0.1"
    bind_port = (
        bind_port or _int_env(PROVIDER_TIMING_PROXY_BIND_PORT_ENV) or free_local_port(bind_host)
    )
    metrics_path = run_dir / PROVIDER_REQUEST_METRICS_FILENAME
    ready_path = run_dir / "provider_timing_proxy.ready.json"
    ready_path.unlink(missing_ok=True)
    metrics_path.unlink(missing_ok=True)

    command = [
        str(repo_root / ".venv/bin/python"),
        "-m",
        "roboclaws.agents.provider_timing_proxy",
        "--upstream-base-url",
        upstream_base_url,
        "--metrics-path",
        str(metrics_path),
        "--bind-host",
        bind_host,
        "--bind-port",
        str(bind_port),
        "--agent-engine",
        agent_engine,
        "--provider-profile",
        provider_profile,
        "--model",
        model,
        "--ready-path",
        str(ready_path),
    ]
    env = os.environ.copy()
    proc = subprocess.Popen(
        command,
        cwd=repo_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + startup_timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        if ready_path.is_file():
            payload = _read_ready_payload(ready_path)
            return ProviderTimingProxyHandle(
                process=proc,
                bind_url=str(payload.get("bind_url") or f"http://{bind_host}:{bind_port}"),
                upstream_base_url=upstream_base_url,
                metrics_path=metrics_path,
                ready_path=ready_path,
            )
        if proc.poll() is not None:
            last_error = _read_stderr_tail(proc)
            break
        await asyncio.sleep(0.05)
        if proc.poll() is not None:
            last_error = _read_stderr_tail(proc)
            break
    await stop_provider_timing_proxy(proc)
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(
        "provider timing proxy did not become ready "
        f"at {bind_host}:{bind_port} within {startup_timeout_s:g}s{detail}"
    )


async def stop_provider_timing_proxy(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        await asyncio.to_thread(process.wait, timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        await asyncio.to_thread(process.wait, timeout=5)


async def serve_provider_timing_proxy(
    config: ProviderTimingProxyConfig,
    *,
    ready_path: Path | None = None,
    stop_event: asyncio.Event | None = None,
) -> None:
    upstream = urlsplit(config.normalized_upstream())
    if upstream.scheme not in {"http", "https"} or not upstream.netloc:
        raise RuntimeError(f"invalid upstream base URL: {config.upstream_base_url!r}")
    if config.bind_host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("provider timing proxy v1 only supports loopback bind hosts")

    app = web.Application()
    app[CONFIG_APP_KEY] = config
    app[CLIENT_SESSION_APP_KEY] = ClientSession(timeout=ClientTimeout(total=None))
    app.router.add_route("*", "/{tail:.*}", _proxy_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.bind_host, config.bind_port)
    await site.start()
    bind_port = _site_port(site)
    bind_url = f"http://{config.bind_host}:{bind_port}"
    if ready_path is not None:
        ready_path.parent.mkdir(parents=True, exist_ok=True)
        ready_path.write_text(
            json.dumps(
                {
                    "schema": "roboclaws_provider_timing_proxy_ready_v1",
                    "bind_url": bind_url,
                    "upstream_base_url": config.upstream_base_url,
                    "metrics_path": str(config.metrics_path),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    stop_event = stop_event or asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        await app[CLIENT_SESSION_APP_KEY].close()
        await runner.cleanup()


async def _proxy_handler(request: web.Request) -> web.StreamResponse:
    config = request.app[CONFIG_APP_KEY]
    session = request.app[CLIENT_SESSION_APP_KEY]
    request_id = uuid.uuid4().hex[:12]
    if request.raw_path.startswith(("http://", "https://")):
        _write_metric_line(
            config.metrics_path,
            {
                "schema": PROVIDER_REQUEST_METRIC_SCHEMA,
                "proxy_request_id": request_id,
                "agent_engine": config.agent_engine,
                "provider_profile": config.provider_profile,
                "method": request.method,
                "path": request.rel_url.raw_path,
                "started_at_epoch": _round_epoch(time.time()),
                "upstream_headers_received_at_epoch": None,
                "first_response_byte_at_epoch": None,
                "finished_at_epoch": _round_epoch(time.time()),
                "duration_s": 0.0,
                "time_to_headers_s": None,
                "time_to_first_byte_s": None,
                "stream_duration_s": None,
                "request_body_bytes": 0,
                "response_body_bytes": 0,
                "status_code": 400,
                "streaming": False,
                "provider_request_id": "",
                "model": config.model,
                "limitations": ["absolute_upstream_host_rejected"],
            },
        )
        return web.json_response({"error": "absolute_upstream_host_rejected"}, status=400)
    started = time.time()
    upstream_url = _upstream_url(config.normalized_upstream(), request)
    request_body_bytes = 0
    response_body_bytes = 0
    upstream_headers_received: float | None = None
    first_response_byte: float | None = None
    finished: float | None = None
    status_code: int | None = None
    streaming = False
    provider_request_id = ""
    limitations: list[str] = []

    async def request_body() -> AsyncIterator[bytes]:
        nonlocal request_body_bytes
        async for chunk in request.content.iter_chunked(64 * 1024):
            request_body_bytes += len(chunk)
            yield chunk

    headers = _forward_request_headers(request.headers)
    try:
        async with session.request(
            request.method,
            upstream_url,
            headers=headers,
            data=request_body(),
            allow_redirects=False,
        ) as upstream_response:
            upstream_headers_received = time.time()
            status_code = upstream_response.status
            provider_request_id = _safe_provider_request_id(upstream_response.headers)
            response = web.StreamResponse(
                status=upstream_response.status,
                reason=upstream_response.reason,
                headers=_forward_response_headers(upstream_response.headers),
            )
            await response.prepare(request)
            async for chunk in upstream_response.content.iter_chunked(64 * 1024):
                if not chunk:
                    continue
                if first_response_byte is None:
                    first_response_byte = time.time()
                response_body_bytes += len(chunk)
                streaming = True
                await response.write(chunk)
            await response.write_eof()
            return response
    except ClientError:
        status_code = 502
        limitations.append("upstream_client_error")
        return web.json_response({"error": "upstream_client_error"}, status=502)
    finally:
        finished = time.time()
        _write_metric_line(
            config.metrics_path,
            {
                "schema": PROVIDER_REQUEST_METRIC_SCHEMA,
                "proxy_request_id": request_id,
                "agent_engine": config.agent_engine,
                "provider_profile": config.provider_profile,
                "method": request.method,
                "path": request.rel_url.raw_path,
                "started_at_epoch": _round_epoch(started),
                "upstream_headers_received_at_epoch": _round_epoch(upstream_headers_received),
                "first_response_byte_at_epoch": _round_epoch(first_response_byte),
                "finished_at_epoch": _round_epoch(finished),
                "duration_s": _round_duration(_elapsed(started, finished)),
                "time_to_headers_s": _round_duration(_elapsed(started, upstream_headers_received)),
                "time_to_first_byte_s": _round_duration(_elapsed(started, first_response_byte)),
                "stream_duration_s": _round_duration(_elapsed(first_response_byte, finished)),
                "request_body_bytes": request_body_bytes,
                "response_body_bytes": response_body_bytes,
                "status_code": status_code,
                "streaming": streaming,
                "provider_request_id": provider_request_id,
                "model": config.model,
                "limitations": limitations,
            },
        )


def _upstream_url(upstream_base_url: str, request: web.Request) -> str:
    upstream = urlsplit(upstream_base_url)
    return urlunsplit((upstream.scheme, upstream.netloc, request.rel_url.raw_path_qs, "", ""))


def _forward_request_headers(headers: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        lowered = key.lower()
        if lowered in HOP_BY_HOP_HEADERS or lowered == "host":
            continue
        result[key] = value
    return result


def _forward_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        lowered = key.lower()
        if lowered in HOP_BY_HOP_HEADERS:
            continue
        result[key] = value
    return result


def _safe_provider_request_id(headers: Mapping[str, str]) -> str:
    for key in SAFE_PROVIDER_REQUEST_ID_HEADERS:
        value = headers.get(key)
        if value:
            return str(value)[:128]
    return ""


def _write_metric_line(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, sort_keys=True) + "\n")


def _site_port(site: web.TCPSite) -> int:
    sockets = getattr(site, "_server", None).sockets
    if not sockets:
        raise RuntimeError("provider timing proxy did not expose a listening socket")
    return int(sockets[0].getsockname()[1])


def _elapsed(started: float | None, finished: float | None) -> float | None:
    if started is None or finished is None:
        return None
    return max(0.0, finished - started)


def _round_duration(value: float | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, value), 3)


def _round_epoch(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def _int_env(name: str) -> int | None:
    value = os.environ.get(name)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _read_ready_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_stderr_tail(proc: subprocess.Popen[bytes]) -> str:
    if proc.stderr is None:
        return ""
    data = proc.stderr.read()
    return data.decode("utf-8", errors="replace")[-2000:].strip()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-base-url", required=True)
    parser.add_argument("--metrics-path", type=Path, required=True)
    parser.add_argument("--bind-host", default="127.0.0.1")
    parser.add_argument("--bind-port", type=int, default=0)
    parser.add_argument("--agent-engine", default="")
    parser.add_argument("--provider-profile", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--ready-path", type=Path)
    return parser.parse_args(argv)


async def async_main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass
    config = ProviderTimingProxyConfig(
        upstream_base_url=args.upstream_base_url,
        metrics_path=args.metrics_path,
        bind_host=args.bind_host,
        bind_port=args.bind_port,
        agent_engine=args.agent_engine,
        provider_profile=args.provider_profile,
        model=args.model,
    )
    await serve_provider_timing_proxy(config, ready_path=args.ready_path, stop_event=stop_event)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
