from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from roboclaws.operator_console.launcher import (
    LaunchRequest,
    build_launch_argv,
    load_repo_dotenv,
    route_readiness,
    start_console_run,
)
from roboclaws.operator_console.locks import ResourceLock
from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import get_route


def test_launcher_readiness_validates_isaac_and_agibot_gates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XM_LLM_API_KEY", "test-key")

    isaac = route_readiness(tmp_path, get_route("codex-isaac-cleanup"))
    assert not isaac["can_start"]
    assert "Isaac preflight" in isaac["blocker"]

    agibot = route_readiness(
        tmp_path,
        get_route("codex-agibot-g2-map-build"),
        overrides={"context_json": str(tmp_path / "context.json")},
        gates={"localization_ready": True, "run_enabled": False, "estop_ready": True},
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
            "real_movement_enabled": "false",
        },
    )
    assert f"output_dir={tmp_path / 'output' / 'operator-console' / 'runs' / 'run-1'}" in argv
    assert f"context_json={tmp_path / 'context.json'}" in argv
    assert "real_movement_enabled=false" in argv


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

    class FakeProcess:
        pid = 12345

    def fake_popen(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        del args, kwargs
        state = ResourceLock(tmp_path, route.lock_name).read()
        nonlocal seen_lock_owner
        seen_lock_owner = state.owner_run_id
        return FakeProcess()

    with patch("roboclaws.operator_console.launcher.subprocess.Popen", side_effect=fake_popen):
        state = start_console_run(
            tmp_path,
            LaunchRequest(route_id=route.id),
            env={"XM_LLM_API_KEY": "key"},
        )

    assert seen_lock_owner == state["run_id"]
    lock = ResourceLock(tmp_path, route.lock_name).read()
    assert lock.pid == 12345
    state_path = console_output_root(tmp_path) / "runs" / state["run_id"] / "operator_state.json"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["lock"]["owner_run_id"] == state["run_id"]


def test_provider_gate_requires_agent_key_route(tmp_path: Path, monkeypatch) -> None:
    for key in ("XM_LLM_API_KEY", "CODEX_API_KEY", "KIMI_API_KEY", "MIMO_TP_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    readiness = route_readiness(tmp_path, get_route("codex-mujoco-cleanup"))
    assert not readiness["can_start"]
    assert "provider route" in readiness["blocker"].lower()
    assert readiness["blocker_kind"] == "needs_provider"


def test_provider_gate_auto_loads_repo_dotenv(tmp_path: Path, monkeypatch) -> None:
    for key in ("XM_LLM_API_KEY", "CODEX_API_KEY", "KIMI_API_KEY", "MIMO_TP_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text("XM_LLM_API_KEY=from-dotenv\n", encoding="utf-8")

    readiness = route_readiness(tmp_path, get_route("codex-mujoco-cleanup"))

    assert readiness["can_start"] is True
    assert load_repo_dotenv(tmp_path, {})["XM_LLM_API_KEY"] == "from-dotenv"


def test_claude_cleanup_route_uses_claude_driver(tmp_path: Path) -> None:
    route = get_route("claude-mujoco-cleanup")
    argv = build_launch_argv(route, root=tmp_path, run_id="run-1")

    assert argv[:4] == ["just", "task::run", "household-cleanup", "claude"]
    assert "backend=molmospaces_subprocess" in argv
