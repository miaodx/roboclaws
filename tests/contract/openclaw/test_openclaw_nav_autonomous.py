# ruff: noqa: I001

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "examples"))

import subprocess  # noqa: E402

from openclaw_nav_autonomous import (  # noqa: E402
    _kickoff_prompt,
    _parse_args,
    _run_capture,
    run_autonomous_navigation,
)
from roboclaws.openclaw.bridge import (  # noqa: E402
    OpenClawUnavailable,
    RunResult,
    TranscriptMessage,
)


def _make_fake_mcp_server(snapshot_metrics: dict | None = None) -> MagicMock:
    """Build a MagicMock shaped like a RoboclawsMCPServer.

    Covers the five methods + attributes the example relies on
    (see roboclaws/mcp/server.py public surface). `done_event`
    is a real threading.Event so tests can set() it if needed.
    """
    fake = MagicMock(
        spec_set=[
            "done_event",
            "host",
            "port",
            "run_in_thread",
            "close",
            "enqueue_human_message",
            "snapshot_metrics",
            "write_runtime_event",
            "write_trace_event",
        ]
    )
    fake.done_event = threading.Event()
    fake.host = "127.0.0.1"
    fake.port = 18788
    fake.run_in_thread = MagicMock()
    fake.close = MagicMock()
    fake.enqueue_human_message = MagicMock()
    fake.write_runtime_event = MagicMock()
    fake.write_trace_event = MagicMock()
    fake.snapshot_metrics = MagicMock(
        return_value=snapshot_metrics
        if snapshot_metrics is not None
        else {
            "runtime_s": 0.0,
            "last_trace_age_s": 0.0,
            "queued_human_messages": 0,
            "observed_once": True,
            "moves_since_observe": 0,
            "done_event_set": False,
            "done_reason": None,
            "tool_event_counts": {},
        }
    )
    return fake


def test_parse_args_defaults() -> None:
    args = _parse_args([])
    assert args.scene == "FloorPlan201"
    assert args.max_moves == 200
    assert args.wall_budget == 600.0
    assert args.output_dir is None
    assert args.skip_bootstrap is False


def test_kickoff_prompt_is_mcp_era_and_short() -> None:
    """The kickoff prompt targets the MCP tool surface (plan 02.6-04 D-07).

    <= 10 non-empty lines, mentions the three roboclaws__ tools, preserves
    the observe-before-act + human_message behaviors called out in CONTEXT.md,
    and contains zero references to the Phase-2.5 curl/exec/image/tmp escape
    hatches.
    """
    prompt = _kickoff_prompt(50)

    # Budget: <= 10 non-empty lines.
    non_empty = [line for line in prompt.splitlines() if line.strip()]
    assert len(non_empty) <= 10, f"prompt has {len(non_empty)} non-empty lines: {non_empty!r}"

    # Forbidden substrings — none of the Phase-2.5 escape hatches may appear.
    forbidden = [
        "curl",
        "exec",
        "/tmp",
        "image tool",
        "data:image",
        "base64",
        "host.docker.internal",
        "18788",
        "HTTP",
    ]
    hits = [f for f in forbidden if f in prompt]
    assert hits == [], f"forbidden substrings in kickoff prompt: {hits}"

    # Required content.
    assert "roboclaws" in prompt, "prompt must name the roboclaws MCP server namespace"
    assert "observe" in prompt
    assert "move" in prompt
    assert "done" in prompt
    # Budget interpolation must happen.
    assert "50" in prompt, "max_moves budget must be interpolated into prompt"
    # Preserve the human_message ack behavior (D-10, plan must-have).
    assert "human_message" in prompt
    assert "observe_delivery" in prompt
    assert "view_variant" in prompt
    assert "image_labels" in prompt
    assert "bridge_model" in prompt
    # Delegate to the skill, don't duplicate it.
    assert "SKILL.md" in prompt or "skill" in prompt.lower()


def test_run_autonomous_navigation_offline_happy_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "autonomous"
    bridge_result = RunResult(
        final_message="done exploring",
        wallclock_s=12.5,
        terminated_by="done",
        transcript_source="terminal-body",
        transcript_messages=[
            TranscriptMessage(
                wallclock_s=1.2,
                source="terminal-body",
                content="Checking session",
                message_index=0,
                chunk_index=0,
            ),
            TranscriptMessage(
                wallclock_s=1.5,
                source="terminal-body",
                content=" status.",
                message_index=0,
                chunk_index=1,
            ),
        ],
        debug={"prompt_chars": 123, "gateway_request_seconds": 12.5},
    )
    subprocess_calls: list[list[str]] = []

    def _subprocess_run(*args, **kwargs):
        cmd = list(args[0])
        subprocess_calls.append(cmd)
        if cmd == ["./scripts/openclaw-bootstrap.sh"]:
            env = kwargs["env"]
            assert env["TIMEOUT_SECONDS"] == "360"
            assert env["READY_TIMEOUT"] == "180"
            # Example must pass ROBOCLAWS_MCP_URL; SIM_SERVER_URL stays out
            # of the example entirely in phase 02.6-04 (bootstrap still
            # accepts it from operators one more wave).
            assert env["ROBOCLAWS_MCP_URL"] == "http://host.docker.internal:18788/mcp"
            assert "SIM_SERVER_URL" not in env
            return SimpleNamespace(stdout="token-123\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    fake_server = _make_fake_mcp_server(
        snapshot_metrics={"observed_once": True, "moves_since_observe": 0}
    )

    with (
        patch("openclaw_nav_autonomous.MultiAgentEngine") as engine_cls,
        patch(
            "openclaw_nav_autonomous.make_roboclaws_mcp",
            return_value=fake_server,
        ) as mcp_factory,
        patch("openclaw_nav_autonomous.OpenClawBridge") as bridge_cls,
        patch("openclaw_nav_autonomous.subprocess.run", side_effect=_subprocess_run),
        patch("openclaw_nav_autonomous.sys.stdin.isatty", return_value=False),
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
        bridge = bridge_cls.return_value
        bridge.start_run.return_value = bridge_result
        bridge.get_last_run_metrics.return_value = {
            "prompt_chars": 123,
            "gateway_request_seconds": 12.5,
        }

        result = run_autonomous_navigation(
            scene="FloorPlan201",
            max_moves=50,
            wall_budget=300.0,
            output_dir=output_dir,
            skip_bootstrap=False,
        )

    assert result["terminated_by"] == "done"
    assert result["final_message"] == "done exploring"
    assert (output_dir / "run_result.json").exists()
    assert (output_dir / "start_run_metrics.json").exists()
    run_result_json = json.loads((output_dir / "run_result.json").read_text(encoding="utf-8"))
    assert run_result_json["view_variant"] == "map-v2+chase"
    assert run_result_json["bridge_metrics"]["prompt_chars"] == 123
    assert run_result_json["transcript_source"] == "terminal-body"
    assert run_result_json["transcript_messages"][0] == {
        "wallclock_s": 1.2,
        "source": "terminal-body",
        "content": "Checking session",
        "message_index": 0,
        "chunk_index": 0,
        "is_final": False,
    }
    # Key name 'sim_server_metrics' is frozen for report.html compat even
    # though the backing server is now MCP.
    assert run_result_json["sim_server_metrics"]["observed_once"] is True
    bridge_cls.assert_called_once_with(gateway_url="http://127.0.0.1:18789", token="token-123")
    bridge.start_run.assert_called_once()
    # MCP factory was called and the server was started in a thread.
    mcp_factory.assert_called_once()
    # WR-03 regression guard: the example must override host to 0.0.0.0
    # on Linux (spike 02.6-06). 127.0.0.1 is unreachable from Docker's
    # default bridge on 6.x kernels + Docker 29.x. If someone "fixes" the
    # module-docstring contradiction by reverting the override, Linux
    # local-dev breaks silently — this test flips the regression visibly.
    _, mcp_kwargs = mcp_factory.call_args
    assert mcp_kwargs.get("host") == "0.0.0.0", (
        "example must override host to 0.0.0.0 on Linux (spike 02.6-06); "
        "127.0.0.1 is unreachable from Docker's default bridge on 6.x kernels"
    )
    assert mcp_kwargs.get("model_name") == "mimo_openai/mimo-v2.5-pro"
    assert mcp_kwargs.get("image_model") == "mimo_openai/mimo-v2-omni"
    assert mcp_kwargs.get("observe_mode") == "text-bridge"
    fake_server.run_in_thread.assert_called_once()
    assert fake_server.write_trace_event.call_count == 2
    first_trace = fake_server.write_trace_event.call_args_list[0].kwargs
    assert first_trace["tool"] == "assistant"
    assert first_trace["event"] == "assistant_transcript"
    assert first_trace["content"] == "Checking session"
    assert first_trace["wallclock_elapsed"] == 1.2
    assert ["./scripts/openclaw-bootstrap.sh"] in subprocess_calls
    assert [
        sys.executable,
        "scripts/render_autonomous_replay.py",
        "--run-dir",
        str(output_dir),
    ] in subprocess_calls
    assert ["docker", "rm", "-f", "openclaw-gateway"] in subprocess_calls
    engine_cls.return_value.close.assert_called_once()
    fake_server.close.assert_called_once()
    bridge.close.assert_called_once()


def test_run_autonomous_navigation_skip_bootstrap_reuses_token(tmp_path: Path) -> None:
    output_dir = tmp_path / "autonomous"
    bridge_result = RunResult(
        final_message="done exploring",
        wallclock_s=9.5,
        terminated_by="done",
    )
    subprocess_calls: list[list[str]] = []

    def _subprocess_run(*args, **kwargs):
        cmd = list(args[0])
        subprocess_calls.append(cmd)
        return SimpleNamespace(stdout="", returncode=0)

    fake_server = _make_fake_mcp_server(snapshot_metrics={})

    with (
        patch("openclaw_nav_autonomous.MultiAgentEngine") as engine_cls,
        patch(
            "openclaw_nav_autonomous.make_roboclaws_mcp",
            return_value=fake_server,
        ),
        patch("openclaw_nav_autonomous.OpenClawBridge") as bridge_cls,
        patch("openclaw_nav_autonomous.subprocess.run", side_effect=_subprocess_run),
        patch("openclaw_nav_autonomous.sys.stdin.isatty", return_value=False),
        patch.dict("openclaw_nav_autonomous.os.environ", {"OPENCLAW_GATEWAY_TOKEN": "token-xyz"}),
    ):
        bridge = bridge_cls.return_value
        bridge.start_run.return_value = bridge_result
        bridge.get_last_run_metrics.return_value = {}

        result = run_autonomous_navigation(
            scene="FloorPlan201",
            max_moves=50,
            wall_budget=300.0,
            output_dir=output_dir,
            skip_bootstrap=True,
        )

    assert result["terminated_by"] == "done"
    bridge_cls.assert_called_once_with(gateway_url="http://127.0.0.1:18789", token="token-xyz")
    assert ["./scripts/openclaw-bootstrap.sh"] not in subprocess_calls
    assert ["docker", "rm", "-f", "openclaw-gateway"] not in subprocess_calls
    engine_cls.return_value.close.assert_called_once()
    fake_server.close.assert_called_once()
    bridge.close.assert_called_once()


def test_run_autonomous_navigation_records_gateway_error(tmp_path: Path) -> None:
    output_dir = tmp_path / "autonomous"
    subprocess_calls: list[list[str]] = []

    def _subprocess_run(*args, **kwargs):
        cmd = list(args[0])
        subprocess_calls.append(cmd)
        if cmd == ["./scripts/openclaw-bootstrap.sh"]:
            env = kwargs["env"]
            assert env["TIMEOUT_SECONDS"] == "360"
            return SimpleNamespace(stdout="token-123\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    fake_server = _make_fake_mcp_server(snapshot_metrics={"observed_once": True})

    with (
        patch("openclaw_nav_autonomous.MultiAgentEngine") as engine_cls,
        patch(
            "openclaw_nav_autonomous.make_roboclaws_mcp",
            return_value=fake_server,
        ),
        patch("openclaw_nav_autonomous.OpenClawBridge") as bridge_cls,
        patch("openclaw_nav_autonomous.subprocess.run", side_effect=_subprocess_run),
        patch("openclaw_nav_autonomous.sys.stdin.isatty", return_value=False),
    ):
        bridge = bridge_cls.return_value
        bridge.start_run.side_effect = OpenClawUnavailable("Gateway protocol error: boom")
        bridge.get_last_run_metrics.return_value = {"gateway_error": "remote_protocol_error"}

        result = run_autonomous_navigation(
            scene="FloorPlan201",
            max_moves=50,
            wall_budget=300.0,
            output_dir=output_dir,
            skip_bootstrap=False,
        )

    assert result["terminated_by"] == "error"
    assert "Gateway protocol error: boom" in result["final_message"]
    diagnostics_dir = output_dir / "diagnostics"
    assert diagnostics_dir.exists()
    assert (diagnostics_dir / "gateway.inspect.json").exists()
    assert (diagnostics_dir / "gateway.docker.log").exists()
    assert (diagnostics_dir / "gateway.inner.log").exists()
    assert (diagnostics_dir / "gateway.workspace-state.txt").exists()
    assert ["docker", "rm", "-f", "openclaw-gateway"] in subprocess_calls
    engine_cls.return_value.close.assert_called_once()
    fake_server.close.assert_called_once()
    bridge.close.assert_called_once()


def test_roboclaws_mcp_url_env_override_is_honored(tmp_path: Path) -> None:
    """Operator-supplied ROBOCLAWS_MCP_URL wins over the loopback default.

    Regression guard for threat T-02.6-23: a future edit using `env[...] = "..."`
    instead of `env.setdefault(...)` for ROBOCLAWS_MCP_URL would silently
    override a value the operator set (e.g. for the local-probe gate).
    """
    output_dir = tmp_path / "autonomous"
    bridge_result = RunResult(
        final_message="done",
        wallclock_s=1.0,
        terminated_by="done",
    )
    captured_env: dict[str, str] = {}

    def _subprocess_run(*args, **kwargs):
        cmd = list(args[0])
        if cmd == ["./scripts/openclaw-bootstrap.sh"]:
            captured_env.update(kwargs["env"])
            return SimpleNamespace(stdout="token-override\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    override_url = "http://override.test:9999/mcp"
    fake_server = _make_fake_mcp_server()

    with (
        patch("openclaw_nav_autonomous.MultiAgentEngine"),
        patch(
            "openclaw_nav_autonomous.make_roboclaws_mcp",
            return_value=fake_server,
        ),
        patch("openclaw_nav_autonomous.OpenClawBridge") as bridge_cls,
        patch("openclaw_nav_autonomous.subprocess.run", side_effect=_subprocess_run),
        patch("openclaw_nav_autonomous.sys.stdin.isatty", return_value=False),
        patch.dict(
            "openclaw_nav_autonomous.os.environ",
            {"ROBOCLAWS_MCP_URL": override_url},
        ),
    ):
        bridge = bridge_cls.return_value
        bridge.start_run.return_value = bridge_result
        bridge.get_last_run_metrics.return_value = {}

        run_autonomous_navigation(
            scene="FloorPlan201",
            max_moves=10,
            wall_budget=30.0,
            output_dir=output_dir,
            skip_bootstrap=False,
        )

    # Operator-supplied value was preserved (setdefault, not assignment).
    assert captured_env.get("ROBOCLAWS_MCP_URL") == override_url
    # The example no longer sets SIM_SERVER_URL itself. A pre-existing value
    # in os.environ (inherited) is acceptable, but the example is not the
    # source of the legacy URL anymore.
    assert captured_env.get("SIM_SERVER_URL") != "http://host.docker.internal:18788"


def test_run_capture_applies_timeout_and_surfaces_timeout_exit_code() -> None:
    """WR-02: diagnostic subprocesses must not hang indefinitely.

    Pre-fix `_run_capture` called `subprocess.run(..., timeout=?)` with no
    timeout kwarg, so a wedged `docker exec` during teardown could stall
    the process forever. Post-fix it passes `timeout=`, and on
    `TimeoutExpired` returns (124, stdout, stderr+"timed out after …").
    """
    calls: list[dict] = []

    def _fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        # Simulate a hung process by raising TimeoutExpired — this is what
        # subprocess.run does internally when the wall-clock cap elapses.
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs["timeout"])

    with patch("openclaw_nav_autonomous.subprocess.run", side_effect=_fake_run):
        rc, stdout, stderr = _run_capture(["docker", "inspect", "wedged"], timeout=0.5)

    assert len(calls) == 1
    # The timeout kwarg was forwarded to subprocess.run — this is the core fix.
    assert calls[0]["kwargs"].get("timeout") == 0.5
    # 124 matches coreutils `timeout(1)` so log grep keeps working.
    assert rc == 124
    assert "timed out after" in stderr
    assert isinstance(stdout, str)


def test_run_capture_has_default_timeout() -> None:
    """_run_capture must pass a non-None default timeout when caller omits one."""
    captured: dict = {}

    def _fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    with patch("openclaw_nav_autonomous.subprocess.run", side_effect=_fake_run):
        _run_capture(["docker", "inspect", "foo"])

    assert captured.get("timeout") is not None
    assert captured["timeout"] > 0
