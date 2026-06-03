from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from roboclaws.operator_console.launcher import (
    ConsoleLaunchError,
    build_launch_argv,
    route_readiness,
)
from roboclaws.operator_console.locks import ResourceLock, ResourceLockError
from roboclaws.operator_console.redaction import redact_text
from roboclaws.operator_console.routes import (
    get_route,
    list_console_routes,
    validate_supported_routes_against_catalog,
)
from roboclaws.operator_console.state import (
    derive_operator_state,
    redacted_artifact_text,
)


def _just_bin() -> str:
    path = shutil.which("just")
    if path:
        return path
    local_path = Path.home() / ".local" / "bin" / "just"
    if local_path.exists():
        return str(local_path)
    pytest.skip("just binary is not available")


def test_console_route_registry_exposes_agent_routes_and_explains_disabled_routes() -> None:
    routes = list_console_routes()
    supported = [route for route in routes if route.enabled]
    disabled = {route.id: route.disabled_reason for route in routes if not route.enabled}

    assert {route.id for route in supported} == {
        "codex-mujoco-cleanup",
        "claude-mujoco-cleanup",
        "codex-isaac-cleanup",
        "claude-isaac-cleanup",
        "codex-agibot-g2-map-build",
        "codex-mujoco-map-build",
        "codex-isaac-map-build",
    }
    assert {route.driver for route in supported} == {"codex", "claude"}
    assert {route.lock_name for route in supported} == {
        "molmospaces_mujoco",
        "isaac_gpu",
        "agibot_g2",
    }
    assert disabled["agibot-g2-cleanup"] == (
        "Physical manipulation is blocked. Run Agibot G2 Map Build first."
    )
    assert disabled["unsupported-drivers"] == (
        "This console supports local coding-agent drivers only."
    )
    assert disabled["claude-map-build"] == (
        "semantic-map-build does not support the Claude driver yet."
    )
    validate_supported_routes_against_catalog()


def test_console_prompt_gating_and_argv_construction_are_fixed_argv(tmp_path: Path) -> None:
    route = get_route("codex-mujoco-cleanup")
    argv = build_launch_argv(
        route,
        root=tmp_path,
        run_id="run-1",
        prompt="pick up the mug; rm -rf /",
        overrides={"seed": "8", "generated_mess_count": "2"},
    )

    assert argv[:4] == ["just", "task::run", "household-cleanup", "codex"]
    assert "world-labels" in argv
    assert "backend=molmospaces_subprocess" in argv
    assert "prompt=pick up the mug; rm -rf /" in argv
    assert not any("OpenClaw" in item or "claude" in item for item in argv)

    disabled = get_route("agibot-g2-cleanup")
    with pytest.raises(ConsoleLaunchError, match="cannot accept a custom prompt"):
        build_launch_argv(disabled, root=tmp_path, run_id="run-2", prompt="custom")

    with pytest.raises(ConsoleLaunchError, match="unsupported route parameter"):
        build_launch_argv(route, root=tmp_path, run_id="run-3", overrides={"shell": "true"})


def test_console_readiness_enforces_locks_and_preflights(tmp_path: Path) -> None:
    route = get_route("codex-isaac-cleanup")
    readiness = route_readiness(tmp_path, route, env={"XM_LLM_API_KEY": "key"})
    assert readiness["can_start"] is False
    assert "Isaac preflight has not passed" in readiness["blocker"]

    accepted = tmp_path / "output" / "isaaclab" / "runtime-preflight-accepted.json"
    accepted.parent.mkdir(parents=True)
    accepted.write_text("{}", encoding="utf-8")
    readiness = route_readiness(tmp_path, route, env={"XM_LLM_API_KEY": "key"})
    assert readiness["can_start"] is True

    lock = ResourceLock(tmp_path, route.lock_name)
    lock.acquire(run_id="active", pid=os.getpid())
    readiness = route_readiness(tmp_path, route, env={"XM_LLM_API_KEY": "key"})
    assert readiness["can_start"] is False
    assert "Backend lock is held" in readiness["blocker"]


def test_resource_lock_prevents_conflicting_starts(tmp_path: Path) -> None:
    lock = ResourceLock(tmp_path, "molmospaces_mujoco")
    first = lock.acquire(run_id="run-a", pid=os.getpid())
    assert first.held is True
    assert first.owner_run_id == "run-a"

    with pytest.raises(ResourceLockError):
        lock.acquire(run_id="run-b", pid=os.getpid())

    lock.release(run_id="run-a")
    assert lock.read().held is False


def test_operator_state_derives_public_fields_and_artifact_links(tmp_path: Path) -> None:
    run_dir = tmp_path / "output" / "operator-console" / "runs" / "run-a"
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": "run-a",
                "phase": "running",
                "backend_lock": "molmospaces_mujoco",
                "started_at_epoch": 1,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "trace.jsonl").write_text(
        json.dumps(
            {
                "tool_name": "navigate_to_object",
                "ok": True,
                "reasoning": "public reason",
                "observation_summary": "mug visible",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "task": "household-cleanup",
                "backend": "molmospaces_subprocess",
                "cleanup_success": True,
                "private_manifest": {"must_not": "surface"},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "report.html").write_text("<html>ok</html>", encoding="utf-8")

    state = derive_operator_state(tmp_path, run_dir, get_route("codex-mujoco-cleanup"))

    assert state["run_id"] == "run-a"
    assert state["latest_tool_call"]["name"] == "navigate_to_object"
    assert state["latest_public_decision_evidence"]["observation_summary"] == "mug visible"
    assert state["checker_status"]["status"] == "passed"
    assert "private_manifest" not in state["public_run_result"]
    assert any(item["label"] == "Report" for item in state["artifact_paths"])


def test_redaction_removes_secret_values_and_headers(tmp_path: Path) -> None:
    text = (
        "Authorization: Bearer live-token\n"
        "CODEX_API_KEY=secret-key\n"
        "api_key: secret-key\n"
        "base https://secret.example/v1"
    )
    redacted = redact_text(
        text,
        env={"CODEX_API_KEY": "secret-key", "CODEX_BASE_URL": "https://secret.example/v1"},
    )
    assert "secret-key" not in redacted
    assert "live-token" not in redacted
    assert "https://secret.example/v1" not in redacted

    artifact = tmp_path / "driver.log"
    artifact.write_text("Authorization: Bearer live-token\n", encoding="utf-8")
    assert "live-token" not in redacted_artifact_text(artifact)


def test_just_console_run_recipe_is_public() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [_just_bin(), "--summary"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = set(result.stdout.split())
    assert "console::run" in summary
