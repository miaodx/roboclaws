"""Tests for the appliance ``/reset`` endpoint and its plumbing.

Engine-level ``MultiAgentEngine.reset`` is exercised by the live AI2-THOR
smoke (``just appliance::smoke`` against a running container) — those calls
require the Unity build and X server, which aren't available in the cloud
sandbox. Here we cover everything that lives upstream of AI2-THOR:

* ``RoboclawsMCPServer.reset_world`` — locks, calls ``engine.reset``,
  wipes the snapshots dir, returns a summary, writes a trace event.
* ``ResetServer`` — HTTP layer around ``reset_world`` returning HTML.
* ``deploy/railway/nginx.conf.template`` — has the ``/reset`` route.
"""

from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from roboclaws.openclaw.reset_server import ResetServer

ROOT = Path(__file__).resolve().parents[3]


class _FakeEngine:
    """Engine stub that records reset calls without touching AI2-THOR."""

    def __init__(self) -> None:
        self.reset_calls = 0

    def reset(self) -> None:
        self.reset_calls += 1


def _make_stub_mcp(snapshots_dir: Path) -> SimpleNamespace:
    """Build the minimum MCP server surface that ``reset_world`` reads."""
    from roboclaws.mcp.server import RoboclawsMCPServer

    # Drive the real bound method so we exercise the lock + trace path,
    # but on a hand-rolled object so we don't have to spin AI2-THOR.
    stub = SimpleNamespace(
        engine=_FakeEngine(),
        snapshots_dir=snapshots_dir,
        _controller_lock=threading.Lock(),
        write_runtime_event=mock.Mock(),
    )
    stub.reset_world = RoboclawsMCPServer.reset_world.__get__(stub)
    return stub


def test_reset_world_resets_engine_and_wipes_snapshots(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots" / "agent-0"
    snapshots.mkdir(parents=True)
    (snapshots / "latest.fpv.png").write_bytes(b"fake-fpv")
    (snapshots / "latest.map.png").write_bytes(b"fake-map")
    (snapshots / "stale-001.png").write_bytes(b"fake")

    mcp = _make_stub_mcp(snapshots)
    summary = mcp.reset_world()

    assert mcp.engine.reset_calls == 1
    assert list(snapshots.iterdir()) == [], "snapshots dir must be empty after reset"
    assert summary["snapshots_removed"] == 3
    assert summary["elapsed_ms"] >= 0
    mcp.write_runtime_event.assert_called_once()
    event_name, kwargs = mcp.write_runtime_event.call_args[0], mcp.write_runtime_event.call_args[1]
    assert event_name == ("world_reset",)
    assert kwargs["snapshots_removed"] == 3


def test_reset_world_skips_missing_snapshots_dir(tmp_path: Path) -> None:
    mcp = _make_stub_mcp(tmp_path / "does-not-exist")
    summary = mcp.reset_world()

    assert mcp.engine.reset_calls == 1
    assert summary["snapshots_removed"] == 0


def test_reset_world_leaves_snapshots_when_engine_raises(tmp_path: Path) -> None:
    """If AI2-THOR throws, the on-disk frames stay so an operator can debug."""
    snapshots = tmp_path / "snapshots" / "agent-0"
    snapshots.mkdir(parents=True)
    (snapshots / "latest.fpv.png").write_bytes(b"fake")

    mcp = _make_stub_mcp(snapshots)
    mcp.engine.reset = mock.Mock(side_effect=RuntimeError("ai2thor crashed"))  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="ai2thor crashed"):
        mcp.reset_world()

    assert (snapshots / "latest.fpv.png").exists(), "must not wipe on engine failure"
    mcp.write_runtime_event.assert_not_called()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_reset_server_serves_html_on_success(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots" / "agent-0"
    snapshots.mkdir(parents=True)
    (snapshots / "latest.fpv.png").write_bytes(b"fake")

    mcp = _make_stub_mcp(snapshots)
    server = ResetServer(mcp, port=_free_port())  # type: ignore[arg-type]
    server.run_in_thread()
    try:
        url = f"http://{server.host}:{server.port}/reset"
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8")
        assert "Reset complete" in body
        assert resp.headers["Content-Type"].startswith("text/html")
    finally:
        server.shutdown()

    assert mcp.engine.reset_calls == 1
    assert list(snapshots.iterdir()) == []


def test_reset_server_returns_500_when_engine_raises(tmp_path: Path) -> None:
    mcp = _make_stub_mcp(tmp_path)
    mcp.engine.reset = mock.Mock(side_effect=RuntimeError("ai2thor crashed"))  # type: ignore[method-assign]

    server = ResetServer(mcp, port=_free_port())  # type: ignore[arg-type]
    server.run_in_thread()
    try:
        url = f"http://{server.host}:{server.port}/reset"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url, timeout=2.0)
        assert exc_info.value.code == 500
        body = exc_info.value.read().decode("utf-8")
        assert "Reset failed" in body
        assert "ai2thor crashed" in body
    finally:
        server.shutdown()


def test_reset_server_returns_404_for_other_paths(tmp_path: Path) -> None:
    mcp = _make_stub_mcp(tmp_path)
    server = ResetServer(mcp, port=_free_port())  # type: ignore[arg-type]
    server.run_in_thread()
    try:
        url = f"http://{server.host}:{server.port}/something-else"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url, timeout=2.0)
        assert exc_info.value.code == 404
    finally:
        server.shutdown()
    assert mcp.engine.reset_calls == 0


def test_nginx_template_has_reset_route() -> None:
    nginx = (ROOT / "deploy" / "railway" / "nginx.conf.template").read_text(encoding="utf-8")
    assert "location = /reset" in nginx
    assert "proxy_pass http://127.0.0.1:18790/reset" in nginx
    # /reset must NOT be inside an auth_basic block (matches /views/ stance).
    assert "auth_basic" not in nginx


def test_reset_summary_is_json_serializable(tmp_path: Path) -> None:
    """Sanity check: the dict reset_world returns is round-trippable."""
    mcp = _make_stub_mcp(tmp_path)
    summary = mcp.reset_world()
    json.dumps(summary)
