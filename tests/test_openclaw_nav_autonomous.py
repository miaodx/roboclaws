# ruff: noqa: I001

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from openclaw_nav_autonomous import _kickoff_prompt, _parse_args, run_autonomous_navigation  # noqa: E402
from roboclaws.openclaw.bridge import OpenClawUnavailable, RunResult  # noqa: E402


def test_parse_args_defaults() -> None:
    args = _parse_args([])
    assert args.scene == "FloorPlan201"
    assert args.max_moves == 200
    assert args.wall_budget == 600.0
    assert args.output_dir is None
    assert args.skip_bootstrap is False


def test_kickoff_prompt_describes_exec_http_flow() -> None:
    prompt = _kickoff_prompt(50)
    assert "use the read tool to read skills/ai2thor-navigator/SKILL.md" in prompt
    assert "Do not claim that paired nodes" in prompt
    assert "curl -sS http://host.docker.internal:18788/observe" in prompt
    assert "target budget is 50 physical moves" in prompt
    assert "Default behavior is observe -> think -> move" in prompt
    assert '"direction":"MoveAhead","reason":"clear hallway continues"' in prompt
    assert "Be agentic" in prompt
    assert "explicitly mention the human_message" in prompt


def test_run_autonomous_navigation_offline_happy_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "autonomous"
    bridge_result = RunResult(
        final_message="done exploring",
        wallclock_s=12.5,
        terminated_by="done",
    )
    subprocess_calls: list[list[str]] = []

    def _subprocess_run(*args, **kwargs):
        cmd = list(args[0])
        subprocess_calls.append(cmd)
        if cmd == ["./scripts/openclaw-bootstrap.sh"]:
            env = kwargs["env"]
            assert env["TIMEOUT_SECONDS"] == "360"
            assert env["SIM_SERVER_URL"] == "http://host.docker.internal:18788"
            return SimpleNamespace(stdout="token-123\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    with (
        patch("openclaw_nav_autonomous.MultiAgentEngine") as engine_cls,
        patch("openclaw_nav_autonomous.SimHTTPServer") as server_cls,
        patch("openclaw_nav_autonomous.OpenClawBridge") as bridge_cls,
        patch("openclaw_nav_autonomous.subprocess.run", side_effect=_subprocess_run),
        patch("openclaw_nav_autonomous.sys.stdin.isatty", return_value=False),
    ):
        server = server_cls.return_value
        server.port = 18788
        server.done_event = MagicMock()
        bridge = bridge_cls.return_value
        bridge.start_run.return_value = bridge_result

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
    bridge_cls.assert_called_once_with(gateway_url="http://127.0.0.1:18789", token="token-123")
    bridge.start_run.assert_called_once()
    assert ["./scripts/openclaw-bootstrap.sh"] in subprocess_calls
    assert [
        sys.executable,
        "scripts/render_autonomous_replay.py",
        "--run-dir",
        str(output_dir),
    ] in subprocess_calls
    assert ["docker", "rm", "-f", "openclaw-gateway"] in subprocess_calls
    engine_cls.return_value.close.assert_called_once()
    server.close.assert_called_once()
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

    with (
        patch("openclaw_nav_autonomous.MultiAgentEngine") as engine_cls,
        patch("openclaw_nav_autonomous.SimHTTPServer") as server_cls,
        patch("openclaw_nav_autonomous.OpenClawBridge") as bridge_cls,
        patch("openclaw_nav_autonomous.subprocess.run", side_effect=_subprocess_run),
        patch("openclaw_nav_autonomous.sys.stdin.isatty", return_value=False),
        patch.dict("openclaw_nav_autonomous.os.environ", {"OPENCLAW_GATEWAY_TOKEN": "token-xyz"}),
    ):
        server = server_cls.return_value
        server.port = 18788
        server.done_event = MagicMock()
        bridge = bridge_cls.return_value
        bridge.start_run.return_value = bridge_result

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
    server.close.assert_called_once()
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

    with (
        patch("openclaw_nav_autonomous.MultiAgentEngine") as engine_cls,
        patch("openclaw_nav_autonomous.SimHTTPServer") as server_cls,
        patch("openclaw_nav_autonomous.OpenClawBridge") as bridge_cls,
        patch("openclaw_nav_autonomous.subprocess.run", side_effect=_subprocess_run),
        patch("openclaw_nav_autonomous.sys.stdin.isatty", return_value=False),
    ):
        server = server_cls.return_value
        server.port = 18788
        server.done_event = MagicMock()
        bridge = bridge_cls.return_value
        bridge.start_run.side_effect = OpenClawUnavailable("Gateway protocol error: boom")

        result = run_autonomous_navigation(
            scene="FloorPlan201",
            max_moves=50,
            wall_budget=300.0,
            output_dir=output_dir,
            skip_bootstrap=False,
        )

    assert result["terminated_by"] == "error"
    assert "Gateway protocol error: boom" in result["final_message"]
    assert ["docker", "rm", "-f", "openclaw-gateway"] in subprocess_calls
    engine_cls.return_value.close.assert_called_once()
    server.close.assert_called_once()
    bridge.close.assert_called_once()
