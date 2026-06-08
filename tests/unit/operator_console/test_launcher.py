from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from unittest.mock import patch

from roboclaws.operator_console.launcher import (
    LaunchRequest,
    build_launch_argv,
    load_repo_dotenv,
    route_readiness,
    start_console_run,
    stop_console_run,
)
from roboclaws.operator_console.locks import ResourceLock
from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import get_route

CODEX_ENV = {
    "CODEX_BASE_URL": "https://codex.example.test/v1",
    "CODEX_API_KEY": "key",
}


def test_launcher_readiness_validates_isaac_and_agibot_gates(tmp_path: Path) -> None:
    isaac = route_readiness(tmp_path, get_route("codex-isaac-cleanup"), env=CODEX_ENV)
    assert not isaac["can_start"]
    assert "Isaac preflight" in isaac["blocker"]

    agibot = route_readiness(
        tmp_path,
        get_route("codex-agibot-g2-map-build"),
        overrides={"context_json": str(tmp_path / "context.json")},
        gates={"localization_ready": True, "run_enabled": False, "estop_ready": True},
        env=CODEX_ENV,
    )
    assert not agibot["can_start"]
    assert "Agibot operator gates" in agibot["blocker"]


def test_launcher_builds_route_specific_overrides(tmp_path: Path) -> None:
    route = get_route("codex-agibot-g2-map-build")
    argv = build_launch_argv(
        route,
        root=tmp_path,
        run_id="run-1",
        overrides={
            "context_json": str(tmp_path / "context.json"),
            "visual_grounding": "grounding-dino",
            "real_movement_enabled": "true",
        },
    )
    assert f"output_dir={tmp_path / 'output' / 'operator-console' / 'runs' / 'run-1'}" in argv
    assert f"context_json={tmp_path / 'context.json'}" in argv
    assert "real_movement_enabled=true" in argv


def test_launcher_replaces_route_default_overrides(tmp_path: Path) -> None:
    route = get_route("codex-mujoco-cleanup")
    argv = build_launch_argv(
        route,
        root=tmp_path,
        run_id="run-1",
        overrides={"seed": "9", "generated_mess_count": "2"},
    )

    assert "seed=7" not in argv
    assert "generated_mess_count=5" not in argv
    assert "seed=9" in argv
    assert "generated_mess_count=2" in argv


def test_launcher_holds_lock_before_spawning_process(tmp_path: Path) -> None:
    route = get_route("codex-mujoco-cleanup")
    seen_lock_owner = ""
    seen_env: dict[str, str] = {}

    class FakeProcess:
        pid = 12345

    def fake_popen(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        del args
        state = ResourceLock(tmp_path, route.lock_name).read()
        nonlocal seen_lock_owner
        seen_lock_owner = state.owner_run_id
        seen_env.update(kwargs["env"])
        return FakeProcess()

    with patch("roboclaws.operator_console.launcher.subprocess.Popen", side_effect=fake_popen):
        state = start_console_run(
            tmp_path,
            LaunchRequest(
                route_id=route.id,
                env_overrides={
                    "ROBOCLAWS_CODEX_PROVIDER": "mify",
                    "ROBOCLAWS_CODEX_MODEL": "xiaomi/mimo-v2.5",
                },
            ),
            env={"XM_LLM_API_KEY": "key"},
        )

    assert seen_lock_owner == state["run_id"]
    assert seen_env["ROBOCLAWS_CODEX_PROVIDER"] == "mify"
    assert seen_env["ROBOCLAWS_CODEX_MODEL"] == "xiaomi/mimo-v2.5"
    assert state["env_overrides"] == {
        "ROBOCLAWS_CODEX_PROVIDER": "mify",
        "ROBOCLAWS_CODEX_MODEL": "xiaomi/mimo-v2.5",
    }
    lock = ResourceLock(tmp_path, route.lock_name).read()
    assert lock.pid == 12345
    state_path = console_output_root(tmp_path) / "runs" / state["run_id"] / "operator_state.json"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["lock"]["owner_run_id"] == state["run_id"]


def test_readiness_exposes_attachable_run_for_held_backend_lock(tmp_path: Path) -> None:
    route = get_route("codex-mujoco-cleanup")
    run_id = "existing-run"
    pid = os.getpid()
    run_dir = console_output_root(tmp_path) / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "route": route.to_payload(),
                "phase": "running",
                "pid": pid,
                "backend_lock": route.lock_name,
                "run_dir": str(run_dir),
            }
        ),
        encoding="utf-8",
    )
    ResourceLock(tmp_path, route.lock_name).acquire(run_id=run_id, pid=pid)

    readiness = route_readiness(tmp_path, route, env=CODEX_ENV)

    assert readiness["can_start"] is False
    assert readiness["blocker_kind"] == "locked"
    assert "Attach to the existing run" in readiness["blocker"]
    assert readiness["attachable_run"] == {
        "run_id": run_id,
        "route_id": route.id,
        "route_label": route.label,
        "phase": "running",
        "run_dir": str(run_dir),
        "display_run_dir": str(run_dir.resolve()),
        "backend_lock": route.lock_name,
        "pid": pid,
        "started_at": "",
    }


def test_readiness_keeps_stale_wrapper_lock_attachable_when_child_live_run_is_active(
    tmp_path: Path,
) -> None:
    route = get_route("codex-mujoco-cleanup")
    run_id = "wrapper-run"
    run_dir = console_output_root(tmp_path) / "runs" / run_id
    attempt_dir = run_dir / "0608_1807" / "seed-7"
    attempt_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "route": route.to_payload(),
                "phase": "starting",
                "pid": 99999999,
                "backend_lock": route.lock_name,
                "run_dir": str(run_dir),
            }
        ),
        encoding="utf-8",
    )
    (attempt_dir / "live_status.json").write_text(
        json.dumps({"phase": "running-codex", "started_at_epoch": 2.0}),
        encoding="utf-8",
    )
    (attempt_dir / "driver.log").write_text("running\n", encoding="utf-8")
    lock = ResourceLock(tmp_path, route.lock_name)
    lock.acquire(run_id=run_id, pid=99999999)

    readiness = route_readiness(tmp_path, route, env=CODEX_ENV)

    assert readiness["can_start"] is False
    assert readiness["blocker_kind"] == "locked"
    assert "Attach to the existing run" in readiness["blocker"]
    assert readiness["attachable_run"]["run_id"] == run_id
    assert readiness["attachable_run"]["phase"] == "running-codex"
    assert readiness["attachable_run"]["display_run_dir"] == str(attempt_dir.resolve())


def test_stop_console_run_targets_nested_live_attempt(tmp_path: Path) -> None:
    route = get_route("codex-mujoco-cleanup")
    run_id = "wrapper-run"
    wrapper_pid = 111
    server_pid = 222
    run_dir = console_output_root(tmp_path) / "runs" / run_id
    attempt_dir = run_dir / "0608_1807" / "seed-7"
    attempt_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "route": route.to_payload(),
                "phase": "starting",
                "pid": wrapper_pid,
                "backend_lock": route.lock_name,
                "run_dir": str(run_dir),
            }
        ),
        encoding="utf-8",
    )
    (attempt_dir / "live_status.json").write_text(
        json.dumps({"phase": "running-codex"}),
        encoding="utf-8",
    )
    (attempt_dir / "server.pid").write_text(f"{server_pid}\n", encoding="utf-8")
    (attempt_dir / "tmux_session.txt").write_text("roboclaws-test\n", encoding="utf-8")
    ResourceLock(tmp_path, route.lock_name).acquire(run_id=run_id, pid=wrapper_pid)

    killed_pids: list[int] = []
    tmux_commands: list[list[str]] = []

    def fake_run(command, **kwargs):  # noqa: ANN001, ANN003, ANN202
        del kwargs
        tmux_commands.append(list(command))

        class Result:
            returncode = 0

        return Result()

    with (
        patch("roboclaws.operator_console.launcher.os.killpg") as killpg,
        patch("roboclaws.operator_console.launcher.subprocess.run", side_effect=fake_run),
    ):
        killpg.side_effect = lambda pid, signal: killed_pids.append(pid)
        state = stop_console_run(tmp_path, run_id)

    assert state["phase"] == "stopped_by_operator"
    assert state["display_run_dir"] == str(attempt_dir.resolve())
    assert server_pid in killed_pids
    assert wrapper_pid in killed_pids
    assert ["tmux", "kill-session", "-t", "roboclaws-test"] in tmux_commands
    assert ResourceLock(tmp_path, route.lock_name).read().held is False


def test_provider_gate_requires_agent_key_route(tmp_path: Path, monkeypatch) -> None:
    for key in ("XM_LLM_API_KEY", "CODEX_API_KEY", "KIMI_API_KEY", "MIMO_TP_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    readiness = route_readiness(tmp_path, get_route("codex-mujoco-cleanup"))
    assert not readiness["can_start"]
    assert "CODEX_BASE_URL" in readiness["blocker"]
    assert "CODEX_API_KEY" in readiness["blocker"]
    assert readiness["blocker_kind"] == "needs_provider"


def test_provider_gate_auto_loads_codex_env_from_repo_dotenv(tmp_path: Path, monkeypatch) -> None:
    for key in ("XM_LLM_API_KEY", "CODEX_API_KEY", "KIMI_API_KEY", "MIMO_TP_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "CODEX_BASE_URL=https://codex.example.test/v1\nCODEX_API_KEY=from-dotenv\n",
        encoding="utf-8",
    )

    readiness = route_readiness(tmp_path, get_route("codex-mujoco-cleanup"))

    assert readiness["can_start"] is True
    assert load_repo_dotenv(tmp_path, {})["CODEX_API_KEY"] == "from-dotenv"
    assert readiness["provider"]["provider"] == "codex-env"


def test_provider_gate_allows_explicit_mify_override_with_xm_key(tmp_path: Path) -> None:
    readiness = route_readiness(
        tmp_path,
        get_route("codex-mujoco-cleanup"),
        env={"XM_LLM_API_KEY": "key"},
        env_overrides={"ROBOCLAWS_CODEX_PROVIDER": "mify"},
    )

    assert readiness["can_start"] is True
    assert readiness["provider"]["provider"] == "mify"


def test_provider_gate_rejects_invalid_env_override(tmp_path: Path) -> None:
    with patch.dict(os.environ, {}, clear=True):
        try:
            route_readiness(
                tmp_path,
                get_route("codex-mujoco-cleanup"),
                env_overrides={"ROBOCLAWS_CODEX_PROVIDER": "system"},
            )
        except ValueError as exc:
            assert "unsupported Codex provider override" in str(exc)
        else:  # pragma: no cover - assertion style keeps dependency surface small.
            raise AssertionError("expected invalid provider override to fail")


def test_mcp_port_gate_rejects_port_that_is_already_accepting_connections(
    tmp_path: Path,
) -> None:
    route = get_route("codex-mujoco-cleanup")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        readiness = route_readiness(
            tmp_path,
            route,
            overrides={"host": "127.0.0.1", "port": str(port)},
            env=CODEX_ENV,
        )

    assert readiness["can_start"] is False
    assert readiness["blocker_kind"] == "mcp_port_in_use"
    assert f"127.0.0.1:{port}" in readiness["blocker"]
    assert any(
        gate["id"] == "mcp_port_free" and gate["status"] == "needs_action"
        for gate in readiness["gates"]
    )


def test_claude_cleanup_route_uses_claude_driver(tmp_path: Path) -> None:
    route = get_route("claude-mujoco-cleanup")
    argv = build_launch_argv(route, root=tmp_path, run_id="run-1")

    assert argv[:4] == ["just", "task::run", "household-cleanup", "claude"]
    assert "backend=molmospaces_subprocess" in argv
