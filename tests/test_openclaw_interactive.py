# ruff: noqa: I001

from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

import openclaw_interactive  # noqa: E402
from openclaw_interactive import (  # noqa: E402
    _bootstrap_gateway,
    _default_output_dir,
    _existing_gateway_token,
    _parse_args,
    main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_mcp_server(*, pre_done: bool = True) -> MagicMock:
    """MagicMock shaped like RoboclawsMCPServer.

    `done_event` is a real threading.Event so main()'s wait loop can observe
    the flip synchronously; default pre_done=True makes main() exit on the
    first poll (with a 2s post-done sleep that tests patch out).
    """
    fake = MagicMock(
        spec_set=[
            "done_event",
            "host",
            "port",
            "run_in_thread",
            "close",
            "enqueue_human_message",
            "write_runtime_event",
            "write_trace_event",
        ]
    )
    fake.done_event = threading.Event()
    if pre_done:
        fake.done_event.set()
    fake.host = "0.0.0.0"
    fake.port = 18788
    return fake


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults() -> None:
    args = _parse_args([])
    assert args.scene == "FloorPlan201"
    assert args.views == "map-v2+chase"
    assert args.agent_id == 0
    assert args.output_dir is None
    assert args.skip_bootstrap is False
    assert args.keep_gateway is False


def test_parse_args_accepts_skip_and_keep_flags() -> None:
    args = _parse_args(["--skip-bootstrap", "--keep-gateway", "--agent-id", "2"])
    assert args.skip_bootstrap is True
    assert args.keep_gateway is True
    assert args.agent_id == 2


def test_parse_args_rejects_invalid_view() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--views", "not-a-variant"])


# ---------------------------------------------------------------------------
# _default_output_dir
# ---------------------------------------------------------------------------


def test_default_output_dir_is_timestamped_under_output_tree() -> None:
    path = _default_output_dir()
    parts = path.parts
    assert parts[0] == "output"
    assert parts[1] == "openclaw-interactive"
    # Timestamp segment looks like YYYYMMDDHHMM (12 chars).
    assert len(parts[2]) == 12 and parts[2].isdigit()


# ---------------------------------------------------------------------------
# _bootstrap_gateway
# ---------------------------------------------------------------------------


def test_bootstrap_gateway_invokes_script_with_expected_env() -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs):
        captured["cmd"] = list(args[0])
        captured["env"] = kwargs["env"]
        assert kwargs["check"] is True
        return SimpleNamespace(stdout="token-xyz\n", returncode=0)

    with (
        patch("openclaw_interactive.subprocess.run", side_effect=_fake_run),
        # Do not leak the harness's real OPENCLAW_* env vars into the call.
        patch.dict("os.environ", {}, clear=False),
    ):
        token = _bootstrap_gateway(agent_id=1)

    assert token == "token-xyz"
    assert captured["cmd"] == ["./scripts/openclaw-bootstrap.sh"]
    env = captured["env"]
    # agent_id=1 → at least 2 agents (0 and 1).
    assert env["AGENTS"] == "2"
    assert env["ROBOCLAWS_MCP_URL"] == "http://host.docker.internal:18788/mcp"
    assert env["TIMEOUT_SECONDS"] == "600"


def test_bootstrap_gateway_preserves_caller_overrides() -> None:
    """setdefault semantics: caller env wins over our defaults."""

    def _fake_run(*args, **kwargs):
        return SimpleNamespace(stdout="tok\n", returncode=0)

    with (
        patch("openclaw_interactive.subprocess.run", side_effect=_fake_run) as run_mock,
        patch.dict(
            "os.environ",
            {"AGENTS": "4", "TIMEOUT_SECONDS": "900"},
            clear=False,
        ),
    ):
        _bootstrap_gateway(agent_id=0)
        env = run_mock.call_args.kwargs["env"]
        assert env["AGENTS"] == "4"
        assert env["TIMEOUT_SECONDS"] == "900"


# ---------------------------------------------------------------------------
# _existing_gateway_token
# ---------------------------------------------------------------------------


def test_existing_gateway_token_parses_docker_exec_output() -> None:
    fake = SimpleNamespace(stdout="deadbeefcafef00d\n", returncode=0, stderr="")
    with patch("openclaw_interactive.subprocess.run", return_value=fake):
        token = _existing_gateway_token("openclaw-gateway")
    assert token == "deadbeefcafef00d"


def test_existing_gateway_token_returns_none_on_empty_stdout() -> None:
    fake = SimpleNamespace(stdout="\n", returncode=1, stderr="boom")
    with patch("openclaw_interactive.subprocess.run", return_value=fake):
        assert _existing_gateway_token("openclaw-gateway") is None


def test_existing_gateway_token_returns_none_when_docker_missing() -> None:
    with patch(
        "openclaw_interactive.subprocess.run",
        side_effect=FileNotFoundError("docker"),
    ):
        assert _existing_gateway_token("openclaw-gateway") is None


# ---------------------------------------------------------------------------
# main() — end-to-end patched runs
# ---------------------------------------------------------------------------


@pytest.fixture
def _patched_main_deps(tmp_path: Path):
    """Common patches so main() runs fully offline + exits immediately.

    - Engine is a MagicMock (no Unity boot).
    - make_roboclaws_mcp returns a fake whose done_event is pre-set so the
      wait loop exits on the first poll.
    - time.sleep is a no-op (skips the 2s post-done hold).
    - signal.signal is a no-op (tests may run off the main thread).
    - stdin.isatty() → False so the stdin pump is skipped.
    - subprocess.run is captured and driven per-test.
    """
    fake_server = _make_fake_mcp_server(pre_done=True)
    engine_cls = MagicMock()
    with (
        patch("openclaw_interactive.MultiAgentEngine", engine_cls),
        patch("openclaw_interactive.make_roboclaws_mcp", return_value=fake_server),
        patch("openclaw_interactive.time.sleep"),
        patch("openclaw_interactive.signal.signal"),
        patch("openclaw_interactive.sys.stdin.isatty", return_value=False),
    ):
        yield SimpleNamespace(
            tmp_path=tmp_path,
            fake_server=fake_server,
            engine_cls=engine_cls,
        )


def test_main_bootstraps_and_prints_banner_with_token(_patched_main_deps, capsys) -> None:
    ctx = _patched_main_deps
    subprocess_calls: list[list[str]] = []

    def _fake_run(*args, **kwargs):
        cmd = list(args[0])
        subprocess_calls.append(cmd)
        if cmd[0] == "./scripts/openclaw-bootstrap.sh":
            return SimpleNamespace(stdout="tok-fresh\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    with (
        patch("openclaw_interactive.subprocess.run", side_effect=_fake_run),
        patch.dict(
            "os.environ",
            {
                "MODEL": "mimo_openai/mimo-v2.5-pro",
                "IMAGE_MODEL": "mimo_openai/mimo-v2-omni",
                "ROBOCLAWS_OBSERVE_MODE": "text-bridge",
            },
            clear=False,
        ),
    ):
        rc = main(["--output-dir", str(ctx.tmp_path / "run")])

    assert rc == 0
    # Bootstrap was invoked exactly once and Gateway was torn down at exit.
    assert ["./scripts/openclaw-bootstrap.sh"] in subprocess_calls
    assert ["docker", "rm", "-f", "openclaw-gateway"] in subprocess_calls

    # MCP bound to 0.0.0.0:18788 (Linux host.docker.internal route).
    mcp_kwargs = openclaw_interactive.make_roboclaws_mcp.call_args.kwargs
    assert mcp_kwargs["host"] == "0.0.0.0"
    assert mcp_kwargs["port"] == 18788
    assert mcp_kwargs["agent_id"] == 0
    assert mcp_kwargs["view_variant"] == "map-v2+chase"
    ctx.fake_server.run_in_thread.assert_called_once()
    ctx.fake_server.close.assert_called_once()
    ctx.engine_cls.return_value.close.assert_called_once()

    # Banner reaches stdout with URL + token + agent-0.
    out = capsys.readouterr().out
    assert "http://127.0.0.1:18789" in out
    assert "tok-fresh" in out
    assert "agent-0" in out
    assert "mimo-v2.5-pro" in out
    assert "mimo-v2-omni" in out
    assert "text-bridge" in out


def test_main_skip_bootstrap_uses_env_token(_patched_main_deps) -> None:
    ctx = _patched_main_deps
    subprocess_calls: list[list[str]] = []

    def _fake_run(*args, **kwargs):
        subprocess_calls.append(list(args[0]))
        return SimpleNamespace(stdout="", returncode=0)

    with (
        patch("openclaw_interactive.subprocess.run", side_effect=_fake_run),
        patch.dict("os.environ", {"OPENCLAW_GATEWAY_TOKEN": "env-token"}, clear=False),
    ):
        rc = main(
            [
                "--skip-bootstrap",
                "--output-dir",
                str(ctx.tmp_path / "reuse"),
            ]
        )

    assert rc == 0
    # No bootstrap, no teardown — we attached to an existing Gateway.
    assert ["./scripts/openclaw-bootstrap.sh"] not in subprocess_calls
    assert all(cmd[:3] != ["docker", "rm", "-f"] for cmd in subprocess_calls), (
        f"should not tear down a Gateway we didn't start: {subprocess_calls}"
    )


def test_main_skip_bootstrap_falls_back_to_container_token(
    _patched_main_deps,
) -> None:
    ctx = _patched_main_deps

    def _fake_run(*args, **kwargs):
        cmd = list(args[0])
        # Only docker-exec calls happen in this path — return the container token.
        if cmd[:2] == ["docker", "exec"]:
            return SimpleNamespace(stdout="container-token\n", returncode=0, stderr="")
        return SimpleNamespace(stdout="", returncode=0)

    with (
        patch("openclaw_interactive.subprocess.run", side_effect=_fake_run),
        patch.dict("os.environ", {}, clear=False),
    ):
        # Ensure the env var is not inherited from the host.
        import os as _os

        _os.environ.pop("OPENCLAW_GATEWAY_TOKEN", None)
        rc = main(
            [
                "--skip-bootstrap",
                "--output-dir",
                str(ctx.tmp_path / "fallback"),
            ]
        )

    assert rc == 0


def test_main_skip_bootstrap_raises_without_any_token(
    _patched_main_deps,
) -> None:
    ctx = _patched_main_deps

    def _fake_run(*args, **kwargs):
        # docker exec returns empty → no container token.
        return SimpleNamespace(stdout="", returncode=1, stderr="no container")

    with (
        patch("openclaw_interactive.subprocess.run", side_effect=_fake_run),
        patch.dict("os.environ", {}, clear=False),
    ):
        import os as _os

        _os.environ.pop("OPENCLAW_GATEWAY_TOKEN", None)
        rc = main(
            [
                "--skip-bootstrap",
                "--output-dir",
                str(ctx.tmp_path / "missing"),
            ]
        )

    # Missing token is a fatal error inside main()'s try block → returns 1.
    assert rc == 1


def test_main_keep_gateway_suppresses_teardown(_patched_main_deps) -> None:
    ctx = _patched_main_deps
    subprocess_calls: list[list[str]] = []

    def _fake_run(*args, **kwargs):
        cmd = list(args[0])
        subprocess_calls.append(cmd)
        if cmd[0] == "./scripts/openclaw-bootstrap.sh":
            return SimpleNamespace(stdout="tok-keep\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    with patch("openclaw_interactive.subprocess.run", side_effect=_fake_run):
        rc = main(
            [
                "--keep-gateway",
                "--output-dir",
                str(ctx.tmp_path / "keep"),
            ]
        )

    assert rc == 0
    assert ["./scripts/openclaw-bootstrap.sh"] in subprocess_calls
    # With --keep-gateway, the Gateway we bootstrapped stays up.
    assert all(cmd[:3] != ["docker", "rm", "-f"] for cmd in subprocess_calls), (
        f"--keep-gateway must suppress teardown; saw: {subprocess_calls}"
    )
