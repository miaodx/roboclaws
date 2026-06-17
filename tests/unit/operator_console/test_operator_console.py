from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import urllib.error
import urllib.parse
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
    get_selection,
    list_console_combinations,
    validate_supported_routes_against_catalog,
)
from roboclaws.operator_console.server import (
    ConsoleRequestHandler,
    _registered_preview_asset_names,
)
from roboclaws.operator_console.server import (
    main as operator_console_main,
)
from roboclaws.operator_console.state import (
    derive_operator_state,
    redacted_artifact_text,
)

CODEX_ENV = {
    "CODEX_BASE_URL": "https://codex.example.test/v1",
    "CODEX_API_KEY": "key",
}
AGIBOT_CODEX_CLEANUP = "agibot-g2/map-12::agibot-gdk::cleanup::codex-cli::camera-grounded-labels"
AGIBOT_CODEX_MAP_BUILD = (
    "agibot-g2/map-12::agibot-gdk::map-build::codex-cli::camera-grounded-labels"
)
B1_CODEX_OPEN_TASK = "b1-map12::isaaclab::open-task::codex-cli::world-public-labels"
MUJOCO_CLAUDE_CLEANUP = "molmospaces/val_0::mujoco::cleanup::claude-code::world-public-labels"
MUJOCO_CODEX_CLEANUP = "molmospaces/val_0::mujoco::cleanup::codex-cli::world-public-labels"
MUJOCO_CODEX_MAP_BUILD = "molmospaces/val_0::mujoco::map-build::codex-cli::world-public-labels"


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
    routes = list_console_combinations()
    supported = [route for route in routes if route.enabled]
    disabled = {route.id: route.disabled_reason for route in routes if not route.enabled}

    assert {route.id for route in supported} >= {
        MUJOCO_CODEX_CLEANUP,
        MUJOCO_CLAUDE_CLEANUP,
        AGIBOT_CODEX_MAP_BUILD,
        MUJOCO_CODEX_MAP_BUILD,
        B1_CODEX_OPEN_TASK,
    }
    assert {route.agent_engine_id for route in supported} >= {"codex-cli", "claude-code"}
    assert {route.lock_name for route in supported} == {
        "molmospaces_mujoco",
        "isaac_gpu",
        "agibot_g2",
    }
    assert disabled[AGIBOT_CODEX_CLEANUP] == (
        "Physical manipulation is not available yet. Run Agibot G2 Map Build first."
    )
    validate_supported_routes_against_catalog()


def test_console_route_payload_supports_backend_specific_ui_metadata() -> None:
    mujoco = get_selection(MUJOCO_CODEX_CLEANUP).to_payload()
    b1 = get_selection(B1_CODEX_OPEN_TASK).to_payload()
    agibot = get_selection(AGIBOT_CODEX_MAP_BUILD).to_payload()

    assert mujoco["field_groups"] == ["common"]
    assert "grounding" not in mujoco["view_modes"]
    assert {"overview", "fpv", "map", "outputs"}.issubset(set(mujoco["view_modes"]))

    assert b1["field_groups"] == ["common", "isaac"]
    assert "grounding" in b1["view_modes"]

    assert agibot["field_groups"] == ["common", "agibot", "agibot_gates"]
    assert "grounding" in agibot["view_modes"]
    assert "chase" not in agibot["view_modes"]


def test_console_prompt_gating_and_argv_construction_are_fixed_argv(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
    argv = build_launch_argv(
        route,
        root=tmp_path,
        run_id="run-1",
        prompt="pick up the mug; rm -rf /",
        overrides={
            "seed": "8",
            "scenario_setup": "relocate-cleanup-related-objects",
            "relocation_count": "2",
        },
    )

    assert argv[:7] == [
        "just",
        "run::surface",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "preset=cleanup",
        "agent_engine=codex-cli",
    ]
    assert "preset=cleanup" in argv
    assert "evidence_lane=world-public-labels" in argv
    assert "provider_profile=codex-env" in argv
    assert "prompt=pick up the mug; rm -rf /" in argv
    assert "scenario_setup=relocate-cleanup-related-objects" in argv
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
    assert not any(item.startswith("intent=") for item in open_ended)
    assert not any(item.startswith("preset=") for item in open_ended)
    assert "scenario_setup=baseline" in open_ended
    assert not any(item.startswith("relocation_count=") for item in open_ended)
    assert not any(item.startswith("generated_mess_count=") for item in open_ended)

    default_open_ended = build_launch_argv(
        route,
        root=tmp_path,
        run_id="run-1-open-ended-default",
        intent="open-ended",
    )
    assert not any(item.startswith("intent=") for item in default_open_ended)
    assert not any(item.startswith("preset=") for item in default_open_ended)
    assert "prompt=在这个场景中完成开放性导航任务，并报告你看到的证据。" in default_open_ended

    disabled = get_selection(AGIBOT_CODEX_CLEANUP)
    with pytest.raises(ConsoleLaunchError, match="cannot accept a custom prompt"):
        build_launch_argv(disabled, root=tmp_path, run_id="run-2", prompt="custom")

    with pytest.raises(ConsoleLaunchError, match="unsupported route parameter"):
        build_launch_argv(route, root=tmp_path, run_id="run-3", overrides={"shell": "true"})


def test_operator_console_prompt_preview_endpoint_renders_agent_kickoff_prompt(
    tmp_path: Path,
) -> None:
    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/prompt-preview",
            method="POST",
            data=json.dumps(
                {
                    "world_id": "molmospaces/val_0",
                    "backend_id": "mujoco",
                    "intent_id": "cleanup",
                    "agent_engine_id": "codex-cli",
                    "provider_profile": "codex-env",
                    "evidence_lane": "world-public-labels",
                    "scenario_setup": "relocate-cleanup-related-objects",
                    "prompt": "只收拾桌面上的杯子",
                    "overrides": {"relocation_count": "5"},
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["operator_prompt"] == "只收拾桌面上的杯子"
    assert payload["source"] == "household-cleanup"
    assert payload["intent"] == "cleanup"
    assert payload["prompt_mode"] == "full"
    assert "This run is surface=household-world intent=cleanup" in payload["agent_kickoff_prompt"]
    assert "只收拾桌面上的杯子" in payload["agent_kickoff_prompt"]
    assert "metric_map.inspection_waypoints" in payload["agent_kickoff_prompt"]
    assert "Codex CLI receives an additional live-route wrapper" in payload["wrapper_notes"][0]


def test_console_readiness_omits_isaac_marker_diagnostic_but_keeps_locks_blocking(
    tmp_path: Path,
) -> None:
    route = get_selection(B1_CODEX_OPEN_TASK)
    readiness = route_readiness(tmp_path, route, overrides={"port": _free_port()}, env=CODEX_ENV)
    assert readiness["can_start"] is True
    assert {gate["id"] for gate in readiness["gates"]} == {"provider_key", "mcp_port_free"}

    lock = ResourceLock(tmp_path, route.lock_name)
    lock.acquire(run_id="active", pid=os.getpid())
    readiness = route_readiness(tmp_path, route, overrides={"port": _free_port()}, env=CODEX_ENV)
    assert readiness["can_start"] is False
    assert "Backend lock is held" in readiness["blocker"]


def test_console_readiness_uses_provider_profile_override(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
    readiness = route_readiness(
        tmp_path,
        route,
        overrides={"port": _free_port(), "provider_profile": "mify"},
        env={"XM_LLM_API_KEY": "key"},
    )

    assert readiness["can_start"] is True
    assert readiness["provider"]["provider"] == "mify"
    assert readiness["provider"]["model"] == "xiaomi/mimo-v2.5"


def test_console_readiness_uses_claude_provider_profile_override(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CLAUDE_CLEANUP)
    readiness = route_readiness(
        tmp_path,
        route,
        overrides={"port": _free_port(), "provider_profile": "kimi-anthropic"},
        env={"KIMI_API_KEY": "key"},
    )

    assert readiness["can_start"] is True
    assert readiness["provider"]["provider"] == "kimi-anthropic"
    assert readiness["provider"]["model"] == "kimi-k2.6"


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

    state = derive_operator_state(tmp_path, run_dir, get_selection(MUJOCO_CODEX_CLEANUP))

    assert state["run_id"] == "run-a"
    assert state["latest_tool_call"]["name"] == "navigate_to_object"
    assert state["latest_public_decision_evidence"]["observation_summary"] == "mug visible"
    assert state["checker_status"]["status"] == "passed"
    assert "private_manifest" not in state["public_run_result"]
    assert any(item["label"] == "Report" for item in state["artifact_paths"])
    report_link = next(item for item in state["artifact_paths"] if item["label"] == "Report")
    assert report_link["href"].startswith("/artifacts/")
    assert "?v=" in report_link["href"]


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


def test_operator_console_cli_defaults_to_all_interfaces() -> None:
    with patch("roboclaws.operator_console.server.run_server") as run_server:
        assert operator_console_main([]) == 0

    assert run_server.call_args.args[1] == "0.0.0.0"
    assert run_server.call_args.args[2] == 8765


def test_just_console_run_defaults_to_all_interfaces() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    recipe = (repo_root / "just" / "console.just").read_text(encoding="utf-8")

    assert 'run host="0.0.0.0" port="8765":' in recipe


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


def test_operator_console_routes_endpoint_exposes_evidence_lane_matrix(tmp_path: Path) -> None:
    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with urllib.request.urlopen(f"http://{host}:{port}/api/routes") as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert [lane["id"] for lane in payload["evidence_lanes"]] == [
        "world-public-labels",
        "world-public-labels",
        "camera-grounded-labels",
        "camera-raw-fpv",
    ]
    routes = {route["id"]: route for route in payload["combinations"]}
    worlds = {world["id"]: world for world in payload["worlds"]}
    assert "molmospaces/val_5" in worlds
    assert worlds["molmospaces/val_5"]["preview_assets"]["map"]["href"] == (
        "/previews/molmospaces-val_5-map.png"
    )
    assert worlds["molmospaces/val_5"]["preview_assets"]["topdown"]["href"] == (
        "/previews/molmospaces-val_5-topdown.png"
    )
    assert worlds["molmospaces/val_5"]["preview_assets"]["chase"]["href"] == (
        "/previews/molmospaces-val_5-chase.png"
    )
    assert worlds["b1-map12"]["preview_assets"]["fpv"]["href"] == "/previews/b1-map12-fpv.png"
    assert worlds["b1-map12"]["preview_assets"]["map"]["href"] == "/previews/b1-map12-map.png"
    assert worlds["b1-map12"]["preview_assets"]["topdown"]["href"] == (
        "/previews/b1-map12-topdown.png"
    )
    assert worlds["b1-map12"]["preview_assets"]["chase"]["href"] == ("/previews/b1-map12-chase.png")
    assert (
        worlds["molmospaces/val_5"]["preview_assets"]["topdown"]["href"]
        != (worlds["molmospaces/val_5"]["preview_assets"]["map"]["href"])
    )
    assert (
        routes["molmospaces/val_5::mujoco::cleanup::codex-cli::world-public-labels"][
            "preview_assets"
        ]["fpv"]["href"]
        == "/previews/molmospaces-val_5-fpv.png"
    )
    assert (
        routes["molmospaces/val_5::mujoco::cleanup::codex-cli::world-public-labels"][
            "preview_assets"
        ]["chase"]["href"]
        == "/previews/molmospaces-val_5-chase.png"
    )
    assert (
        routes["molmospaces/val_5::mujoco::cleanup::codex-cli::world-public-labels"][
            "preview_assets"
        ]["topdown"]["href"]
        == "/previews/molmospaces-val_5-topdown.png"
    )
    if "ai2thor/FloorPlan201" in worlds:
        assert "topdown" not in worlds["ai2thor/FloorPlan201"]["preview_assets"]
    assert routes["molmospaces/val_0::mujoco::cleanup::codex-cli::camera-grounded-labels"][
        "enabled"
    ]
    assert not routes["b1-map12::isaaclab::open-task::codex-cli::camera-grounded-labels"]["enabled"]
    assert not any(
        "::isaaclab::" in route_id for route_id in routes if route_id.startswith("molmospaces/")
    )


def test_operator_console_messup_preview_endpoint_is_non_launching(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def fake_preview(root, **kwargs):  # noqa: ANN001, ANN003, ANN202
        seen["root"] = root
        seen.update(kwargs)
        return {
            "schema": "operator_console_messup_preview_v1",
            "ok": False,
            "status": "partial",
            "requested_count": 10,
            "eligible_count": 2,
            "message": "only 2 targets; baseline remains available",
        }

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/messup-preview",
            method="POST",
            data=json.dumps(
                {
                    "world_id": "molmospaces/val_1",
                    "backend_id": "mujoco",
                    "scenario_setup": "relocate-cleanup-related-objects",
                    "relocation_count": "10",
                    "seed": "7",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with patch("roboclaws.operator_console.server.preview_messup", fake_preview):
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["ok"] is False
    assert payload["status"] == "partial"
    assert seen["root"] == tmp_path
    assert seen["world_id"] == "molmospaces/val_1"
    assert seen["backend_id"] == "mujoco"
    assert seen["relocation_count"] == "10"


def test_operator_console_serves_scene_preview_assets(tmp_path: Path) -> None:
    registered_previews = _registered_preview_asset_names()
    assert "molmospaces-val_5-map.png" in registered_previews
    assert "molmospaces-val_5-preview.json" in registered_previews
    assert "b1-map12-map.png" in registered_previews
    assert "b1-map12-fpv.png" in registered_previews
    assert "b1-map12-chase.png" in registered_previews
    assert "b1-map12-preview.json" in registered_previews
    assert "molmospaces-val_6-map.png" not in registered_previews
    assert "molmospaces-val_8-map.png" not in registered_previews

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with urllib.request.urlopen(
            f"http://{host}:{port}/previews/molmospaces-val_5-map.png"
        ) as response:
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        with urllib.request.urlopen(f"http://{host}:{port}/previews/b1-map12-map.png") as response:
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        with urllib.request.urlopen(
            f"http://{host}:{port}/previews/molmospaces-val_5-topdown.png"
        ) as response:
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        with urllib.request.urlopen(
            f"http://{host}:{port}/previews/molmospaces-val_5-chase.png"
        ) as response:
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        with urllib.request.urlopen(f"http://{host}:{port}/previews/b1-map12-map.png") as response:
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        with urllib.request.urlopen(f"http://{host}:{port}/previews/b1-map12-fpv.png") as response:
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        with urllib.request.urlopen(
            f"http://{host}:{port}/previews/b1-map12-chase.png"
        ) as response:
            assert response.headers["Content-Type"] == "image/png"
            assert response.read(8) == b"\x89PNG\r\n\x1a\n"
        with urllib.request.urlopen(
            f"http://{host}:{port}/previews/molmospaces-val_5-preview.json"
        ) as response:
            preview = json.loads(response.read().decode("utf-8"))
            assert preview["views"]["chase"]["view"] == "chase_camera"
            assert preview["views"]["topdown"]["semantic_map_fallback"] is False
        with urllib.request.urlopen(
            f"http://{host}:{port}/previews/b1-map12-preview.json"
        ) as response:
            preview = json.loads(response.read().decode("utf-8"))
            assert preview["renderer"] == "static_b1_map12_with_isaac_runtime_camera_previews"
            assert preview["views"]["fpv"]["provenance"] == (
                "isaac_runtime_robot_mounted_head_camera_fpv"
            )
            assert preview["views"]["chase"]["provenance"] == "isaac_runtime_report_chase_camera"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://{host}:{port}/previews/../app.js")
        assert exc_info.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://{host}:{port}/previews/molmospaces-val_6-map.png")
        assert exc_info.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://{host}:{port}/asset-previews/maps/../README.md")
        assert exc_info.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_operator_console_latest_run_endpoint_returns_artifact_backed_history(
    tmp_path: Path,
) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
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
    assert payload["selection_id"] == route.id
    assert payload["run_dir"] == str(run_dir.resolve())


def test_operator_console_run_reload_ignores_legacy_route_query(tmp_path: Path) -> None:
    run_id = "route-less-run"
    run_dir = tmp_path / "output" / "operator-console" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps({"run_id": run_id, "phase": "running"}),
        encoding="utf-8",
    )

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with urllib.request.urlopen(
            f"http://{host}:{port}/api/runs/{run_id}?route=molmospaces/val_0::mujoco::cleanup::codex-cli::world-public-labels"
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["run_id"] == run_id
    assert payload["route"] is None
    assert payload["selected_intent"] == ""


def test_operator_console_run_endpoint_rejects_legacy_route_id_field(
    tmp_path: Path,
) -> None:
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
                    "route_id": MUJOCO_CODEX_CLEANUP,
                    "intent": "open-ended",
                    "prompt": "收拾桌面上的杯子",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request)
        payload = json.loads(exc_info.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert exc_info.value.code == 400
    assert "launch requires" in payload["error"]


def test_operator_console_next_goal_autostarts_ready_followup(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
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
    assert launch_request.selection_id_override == route.id
    assert launch_request.intent_id == "open-ended"
    assert launch_request.operator_session_id == "session-test"
    assert launch_request.parent_run_id == run_id


def test_operator_console_control_endpoint_is_allowlisted_and_records_operator_rows(
    tmp_path: Path,
) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
    run_id = "control-run"
    run_dir = tmp_path / "output" / "operator-console" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "route": route.to_payload(),
                "phase": "running",
                "backend_lock": route.lock_name,
                "mcp_url": "http://127.0.0.1:19999/mcp",
            }
        ),
        encoding="utf-8",
    )

    async def fake_call_mcp_tool(mcp_url, action, arguments):  # noqa: ANN001, ANN202
        assert mcp_url == "http://127.0.0.1:19999/mcp"
        assert action == "navigate_to_relative_pose"
        assert arguments == {"forward_m": 0.25, "lateral_m": 0.0, "yaw_delta_deg": 0.0}
        return {
            "ok": True,
            "tool": action,
            "status": "ok",
            "frame_id": "base_link",
            "applied_delta": dict(arguments),
            "requires_reobserve": True,
        }

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/{run_id}/control",
            method="POST",
            data=json.dumps(
                {
                    "action": "navigate_to_relative_pose",
                    "forward_m": 0.25,
                    "lateral_m": 0.0,
                    "yaw_delta_deg": 0.0,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with patch("roboclaws.operator_console.control._call_mcp_tool", fake_call_mcp_tool):
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))

        blocked_request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/{run_id}/control",
            method="POST",
            data=json.dumps({"action": "shell", "command": "whoami"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(blocked_request)
        blocked_payload = json.loads(exc_info.value.read().decode("utf-8"))

        large_request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/{run_id}/control",
            method="POST",
            data=json.dumps(
                {
                    "action": "navigate_to_relative_pose",
                    "forward_m": 2.0,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as large_exc_info:
            urllib.request.urlopen(large_request)
        large_payload = json.loads(large_exc_info.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["ok"] is True
    assert payload["actor"] == "operator"
    assert payload["action"] == "navigate_to_relative_pose"
    assert payload["operator_interventions"]["count"] == 1
    assert payload["response"]["requires_reobserve"] is True
    assert blocked_payload["error"] == "unsupported control action: shell"
    assert large_payload["error"] == "relative movement request exceeds console limits"

    rows = [
        json.loads(line)
        for line in (run_dir / "operator_control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event"] for row in rows] == ["request", "response"]
    assert {row["actor"] for row in rows} == {"operator"}
    persisted = json.loads((run_dir / "operator_state.json").read_text(encoding="utf-8"))
    assert persisted["operator_interventions"]["assisted"] is True
    assert persisted["operator_interventions"]["autonomous_behavior_proof"] is False
    interventions = json.loads(
        (run_dir / "operator_interventions.json").read_text(encoding="utf-8")
    )
    assert interventions["count"] == 1
    assert interventions["events"][0]["action"] == "navigate_to_relative_pose"
    state = derive_operator_state(tmp_path, run_dir, route)
    assert state["operator_interventions"]["count"] == 1
    assert any(item["label"] == "Operator Control" for item in state["artifact_paths"])
    assert any(item["label"] == "Operator Interventions" for item in state["artifact_paths"])


def test_operator_console_control_endpoint_allows_paused_operator_handoff(
    tmp_path: Path,
) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
    run_id = "handoff-run"
    run_dir = tmp_path / "output" / "operator-console" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "route": route.to_payload(),
                "phase": "paused",
                "reason": "operator_handoff_requested",
                "backend_lock": route.lock_name,
                "mcp_url": "http://127.0.0.1:19999/mcp",
            }
        ),
        encoding="utf-8",
    )

    async def fake_call_mcp_tool(mcp_url, action, arguments):  # noqa: ANN001, ANN202
        assert mcp_url == "http://127.0.0.1:19999/mcp"
        assert action == "observe"
        assert arguments == {}
        return {
            "ok": True,
            "tool": action,
            "status": "ok",
            "visible_object_detections": [],
        }

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/{run_id}/control",
            method="POST",
            data=json.dumps({"action": "observe"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with patch("roboclaws.operator_console.control._call_mcp_tool", fake_call_mcp_tool):
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["ok"] is True
    state = derive_operator_state(tmp_path, run_dir, route)
    assert state["phase"] == "paused"
    assert state["controls"]["relative_navigation_control_available"] is True
    assert state["controls"]["next_goal_available"] is False
    assert state["latest_operator_control"]["action"] == "observe"


def test_operator_console_control_endpoint_rejects_unsupported_route(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CODEX_MAP_BUILD)
    run_id = "map-build-run"
    run_dir = tmp_path / "output" / "operator-console" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "route": route.to_payload(),
                "phase": "running",
                "backend_lock": route.lock_name,
                "mcp_url": "http://127.0.0.1:19999/mcp",
            }
        ),
        encoding="utf-8",
    )

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/{run_id}/control",
            method="POST",
            data=json.dumps({"action": "observe"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request)
        payload = json.loads(exc_info.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert exc_info.value.code == 409
    assert payload["error"] == "route does not support relative navigation control"


def test_operator_console_control_endpoint_rejects_terminal_run(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
    run_id = "finished-run"
    run_dir = tmp_path / "output" / "operator-console" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "route": route.to_payload(),
                "phase": "finished",
                "backend_lock": route.lock_name,
                "mcp_url": "http://127.0.0.1:19999/mcp",
            }
        ),
        encoding="utf-8",
    )

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/{run_id}/control",
            method="POST",
            data=json.dumps({"action": "observe"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request)
        payload = json.loads(exc_info.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert exc_info.value.code == 409
    assert payload["error"] == "terminal run cannot be controlled"


def test_operator_console_stop_endpoint_decodes_browser_encoded_run_id(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
    run_id = "20260610-224107-molmospaces/val_0::mujoco::cleanup::codex-cli::world-public-labels"
    run_dir = tmp_path / "output" / "operator-console" / "runs" / run_id
    attempt_dir = run_dir / "0610_2241" / "seed-7"
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
        json.dumps({"phase": "running-codex"}),
        encoding="utf-8",
    )
    ResourceLock(tmp_path, route.lock_name).acquire(run_id=run_id, pid=99999999)

    handler = partial(ConsoleRequestHandler, root=tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/api/runs/{urllib.parse.quote(run_id, safe='')}/stop",
            method="POST",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        with (
            patch("roboclaws.operator_console.launcher._stop_live_child_run"),
            patch("roboclaws.operator_console.launcher._terminate_process_group"),
        ):
            with urllib.request.urlopen(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["run_id"] == run_id
    assert payload["phase"] == "stopped_by_operator"
    assert ResourceLock(tmp_path, route.lock_name).read().held is False


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
