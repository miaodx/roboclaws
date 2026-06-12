from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from aiohttp import ClientSession, web

from roboclaws.agents.provider_timing_proxy import (
    ProviderTimingProxyConfig,
    free_local_port,
    replace_base_url_origin,
    serve_provider_timing_proxy,
)
from roboclaws.reports.live_performance import privacy_findings_for_run_dir


def test_replace_base_url_origin_preserves_upstream_path() -> None:
    assert (
        replace_base_url_origin(
            "https://provider.example.test/v1",
            bind_url="http://127.0.0.1:18888",
        )
        == "http://127.0.0.1:18888/v1"
    )


def test_provider_timing_proxy_streams_counts_bytes_and_redacts(tmp_path: Path) -> None:
    asyncio.run(_proxy_streaming_case(tmp_path))


async def _proxy_streaming_case(tmp_path: Path) -> None:
    upstream_stop = asyncio.Event()
    proxy_stop = asyncio.Event()
    upstream_port = free_local_port()
    proxy_port = free_local_port()
    received: dict[str, object] = {}

    async def handle(request: web.Request) -> web.StreamResponse:
        body = await request.read()
        received["body"] = body.decode("utf-8")
        received["authorization"] = request.headers.get("authorization")
        response = web.StreamResponse(
            status=200,
            headers={
                "content-type": "text/event-stream",
                "x-request-id": "safe-upstream-id",
            },
        )
        await response.prepare(request)
        await response.write(b"data: first\n\n")
        await asyncio.sleep(0.05)
        await response.write(b"data: second\n\n")
        await response.write_eof()
        return response

    upstream_runner = web.AppRunner(web.Application())
    upstream_runner.app.router.add_post("/v1/responses", handle)
    upstream_runner.app.router.add_post("/v1/v1/responses", _unexpected_upstream_path)
    await upstream_runner.setup()
    upstream_site = web.TCPSite(upstream_runner, "127.0.0.1", upstream_port)
    await upstream_site.start()

    proxy_task = asyncio.create_task(
        serve_provider_timing_proxy(
            ProviderTimingProxyConfig(
                upstream_base_url=f"http://127.0.0.1:{upstream_port}/v1",
                metrics_path=tmp_path / "run" / "provider_request_metrics.jsonl",
                bind_port=proxy_port,
                agent_engine="codex-cli",
                provider_profile="codex-env",
                model="gpt-5.5",
            ),
            stop_event=proxy_stop,
        )
    )
    await _wait_for_port(proxy_port)

    first_chunk_at: float | None = None
    chunks: list[bytes] = []
    async with ClientSession() as session:
        async with session.post(
            f"http://127.0.0.1:{proxy_port}/v1/responses",
            data=b"secret prompt text",
            headers={"authorization": "Bearer sk-test-secret"},
        ) as response:
            async for chunk in response.content.iter_chunked(64):
                if first_chunk_at is None:
                    first_chunk_at = time.monotonic()
                chunks.append(chunk)

    proxy_stop.set()
    upstream_stop.set()
    await proxy_task
    await upstream_runner.cleanup()

    assert b"".join(chunks) == b"data: first\n\ndata: second\n\n"
    assert first_chunk_at is not None
    assert received["body"] == "secret prompt text"
    assert received["authorization"] == "Bearer sk-test-secret"

    metrics_path = tmp_path / "run" / "provider_request_metrics.jsonl"
    rows = [json.loads(line) for line in metrics_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["schema"] == "roboclaws_provider_request_metric_v1"
    assert row["agent_engine"] == "codex-cli"
    assert row["provider_profile"] == "codex-env"
    assert row["method"] == "POST"
    assert row["path"] == "/v1/responses"
    assert row["status_code"] == 200
    assert row["request_body_bytes"] == len(b"secret prompt text")
    assert row["response_body_bytes"] == len(b"data: first\n\ndata: second\n\n")
    assert row["streaming"] is True
    assert row["provider_request_id"] == "safe-upstream-id"
    assert row["duration_s"] >= row["time_to_first_byte_s"] >= 0
    assert row["stream_duration_s"] >= 0
    assert "secret prompt text" not in metrics_path.read_text(encoding="utf-8")
    assert "sk-test-secret" not in metrics_path.read_text(encoding="utf-8")
    assert "data: first" not in metrics_path.read_text(encoding="utf-8")
    assert privacy_findings_for_run_dir(tmp_path / "run") == []


async def _wait_for_port(port: int) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
        except OSError:
            await asyncio.sleep(0.02)
            continue
        writer.close()
        await writer.wait_closed()
        reader.feed_eof()
        return
    raise AssertionError(f"port {port} did not open")


async def _unexpected_upstream_path(_request: web.Request) -> web.Response:
    return web.Response(status=599, text="unexpected duplicated upstream path")
