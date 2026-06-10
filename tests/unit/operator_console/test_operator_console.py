from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

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
from roboclaws.operator_console.server import ConsoleRequestHandler
from roboclaws.operator_console.state import (
    derive_operator_state,
    redacted_artifact_text,
)

CODEX_ENV = {
    "CODEX_BASE_URL": "https://codex.example.test/v1",
    "CODEX_API_KEY": "key",
}


def _free_port() -> str:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return str(listener.getsockname()[1])


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
        "codex-b1-map12-open-ended",
    }
    assert {route.driver for route in supported} == {"codex", "claude"}
    assert {route.lock_name for route in supported} == {
        "molmospaces_mujoco",
        "isaac_gpu",
        "agibot_g2",
    }
    assert disabled["agibot-g2-cleanup"] == (
        "Physical manipulation is not available yet. Run Agibot G2 Map Build first."
    )
    assert set(disabled) == {"agibot-g2-cleanup"}
    validate_supported_routes_against_catalog()


def test_console_route_payload_supports_backend_specific_ui_metadata() -> None:
    mujoco = get_route("codex-mujoco-cleanup").to_payload()
    isaac = get_route("codex-isaac-cleanup").to_payload()
    agibot = get_route("codex-agibot-g2-map-build").to_payload()

    assert mujoco["field_groups"] == ["common"]
    assert "grounding" not in mujoco["view_modes"]
    assert {"overview", "fpv", "map", "outputs"}.issubset(set(mujoco["view_modes"]))

    assert isaac["field_groups"] == ["common", "isaac"]
    assert "grounding" in isaac["view_modes"]

    assert agibot["field_groups"] == ["common", "agibot", "agibot_gates"]
    assert "grounding" in agibot["view_modes"]
    assert "chase" not in agibot["view_modes"]


def test_console_prompt_gating_and_argv_construction_are_fixed_argv(tmp_path: Path) -> None:
    route = get_route("codex-mujoco-cleanup")
    argv = build_launch_argv(
        route,
        root=tmp_path,
        run_id="run-1",
        prompt="pick up the mug; rm -rf /",
        overrides={
            "seed": "8",
            "scenario_setup": "relocate-loose-objects",
            "relocation_count": "2",
        },
    )

    assert argv[:7] == [
        "just",
        "run::surface",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=cleanup",
        "agent_engine=codex-cli",
    ]
    assert "intent=cleanup" in argv
    assert "evidence_lane=world-oracle-labels" in argv
    assert "provider_profile=codex-env" in argv
    assert "prompt=pick up the mug; rm -rf /" in argv
    assert "scenario_setup=relocate-loose-objects" in argv
    assert "relocation_count=2" in argv
    assert not any(item.startswith("generated_mess_count=") for item in argv)
    assert not any("OpenClaw" in item or "claude" in item for item in argv)

    open_ended = build_launch_argv(
        route,
        root=tmp_path,
        run_id="run-1-open-ended",
        intent="open-ended",
        prompt="pick up the mug; rm -rf /",
    )
    assert "intent=open-ended" in open_ended
    assert "intent=cleanup" not in open_ended
    assert "scenario_setup=baseline" in open_ended
    assert not any(item.startswith("relocation_count=") for item in open_ended)
    assert not any(item.startswith("generated_mess_count=") for item in open_ended)

    disabled = get_route("agibot-g2-cleanup")
    with pytest.raises(ConsoleLaunchError, match="cannot accept a custom prompt"):
        build_launch_argv(disabled, root=tmp_path, run_id="run-2", prompt="custom")

    with pytest.raises(ConsoleLaunchError, match="unsupported route parameter"):
        build_launch_argv(route, root=tmp_path, run_id="run-3", overrides={"shell": "true"})


def test_console_readiness_keeps_isaac_preflight_advisory_but_locks_blocking(
    tmp_path: Path,
) -> None:
    route = get_route("codex-isaac-cleanup")
    readiness = route_readiness(tmp_path, route, overrides={"port": _free_port()}, env=CODEX_ENV)
    assert readiness["can_start"] is True
    isaac_gate = next(gate for gate in readiness["gates"] if gate["id"] == "isaac_preflight")
    assert isaac_gate["severity"] == "advisory"
    assert isaac_gate["blocks_start"] is False

    accepted = tmp_path / "output" / "isaaclab" / "runtime-preflight-accepted.json"
    accepted.parent.mkdir(parents=True)
    accepted.write_text("{}", encoding="utf-8")
    readiness = route_readiness(tmp_path, route, overrides={"port": _free_port()}, env=CODEX_ENV)
    assert readiness["can_start"] is True
    isaac_gate = next(gate for gate in readiness["gates"] if gate["id"] == "isaac_preflight")
    assert isaac_gate["status"] == "ready"
    assert isaac_gate["evidence"] == str(accepted)

    lock = ResourceLock(tmp_path, route.lock_name)
    lock.acquire(run_id="active", pid=os.getpid())
    readiness = route_readiness(tmp_path, route, overrides={"port": _free_port()}, env=CODEX_ENV)
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


def test_operator_console_static_assets_are_not_cached(tmp_path: Path) -> None:
    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with urllib.request.urlopen(f"http://{host}:{port}/styles.css") as response:
            assert response.headers["Cache-Control"] == "no-store, max-age=0"
            assert response.headers["Content-Type"] == "text/css; charset=utf-8"
        request = urllib.request.Request(f"http://{host}:{port}/styles.css", method="HEAD")
        with urllib.request.urlopen(request) as response:
            assert response.headers["Cache-Control"] == "no-store, max-age=0"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_operator_console_latest_run_endpoint_returns_artifact_backed_history(
    tmp_path: Path,
) -> None:
    route = get_route("codex-mujoco-cleanup")
    run_id = "latest-run"
    run_dir = tmp_path / "output" / "operator-console" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps({"run_id": run_id, "route": route.to_payload(), "phase": "finished"}),
        encoding="utf-8",
    )
    (run_dir / "report.html").write_text("<html>ok</html>", encoding="utf-8")

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with urllib.request.urlopen(f"http://{host}:{port}/api/runs/latest") as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["run_id"] == run_id
    assert payload["route_id"] == route.id
    assert payload["run_dir"] == str(run_dir.resolve())


def test_operator_console_run_endpoint_passes_explicit_intent(tmp_path: Path) -> None:
    launched: dict[str, object] = {}

    def fake_start(root, request):  # noqa: ANN001, ANN202
        launched["root"] = root
        launched["request"] = request
        return {"run_id": "started-run"}

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/runs",
            method="POST",
            data=json.dumps(
                {
                    "route_id": "codex-mujoco-cleanup",
                    "intent": "open-ended",
                    "prompt": "收拾桌面上的杯子",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with patch("roboclaws.operator_console.server.start_console_run", fake_start):
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["run_id"] == "started-run"
    launch_request = launched["request"]
    assert launch_request.route_id == "codex-mujoco-cleanup"
    assert launch_request.intent_id == "open-ended"
    assert launch_request.prompt == "收拾桌面上的杯子"


def test_operator_console_next_goal_autostarts_ready_followup(tmp_path: Path) -> None:
    route = get_route("codex-mujoco-cleanup")
    run_id = "parent-run"
    run_dir = tmp_path / "output" / "operator-console" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "operator_session_id": "session-test",
                "selected_intent": "open-ended",
                "route": route.to_payload(),
                "phase": "finished",
                "backend_lock": route.lock_name,
            }
        ),
        encoding="utf-8",
    )
    session_dir = tmp_path / "output" / "operator-console" / "sessions"
    session_dir.mkdir(parents=True)
    (session_dir / "session-test.json").write_text(
        json.dumps(
            {
                "schema": "operator_console_session_v1",
                "operator_session_id": "session-test",
                "created_at_epoch": 1,
                "created_at": "2026-06-09T00:00:00Z",
                "active_run_id": run_id,
                "run_ids": [run_id],
                "message_ids": [],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "run_result.json").write_text(
        json.dumps({"cleanup_success": True}),
        encoding="utf-8",
    )
    (run_dir / "report.html").write_text("<html>ok</html>", encoding="utf-8")

    launched: dict[str, object] = {}

    def fake_start(root, request):  # noqa: ANN001, ANN202
        launched["root"] = root
        launched["request"] = request
        return {"run_id": "child-run"}

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/{run_id}/next-goal",
            method="POST",
            data=json.dumps({"prompt": "Run the next sweep"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with patch("roboclaws.operator_console.server.start_console_run", fake_start):
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["status"] == "started"
    assert payload["started_run"]["run_id"] == "child-run"
    launch_request = launched["request"]
    assert launch_request.route_id == route.id
    assert launch_request.intent_id == "open-ended"
    assert launch_request.operator_session_id == "session-test"
    assert launch_request.parent_run_id == run_id


def test_operator_console_continue_endpoint_is_not_public(tmp_path: Path) -> None:
    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/parent-run/continue",
            method="POST",
            data=json.dumps({"prompt": "Run the next sweep"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert exc_info.value.code == 404
