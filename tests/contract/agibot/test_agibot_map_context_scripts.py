from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CAPTURE_PATH = REPO_ROOT / "scripts" / "agibot" / "capture_map_context_views.py"
GENERATOR_PATH = REPO_ROOT / "scripts" / "agibot" / "generate_metric_map_from_context.py"
VERIFY_PATH = REPO_ROOT / "scripts" / "agibot" / "verify_waypoints_with_pnc.py"
SDK_RUNNER_PATH = REPO_ROOT / "vendors" / "agibot_sdk" / "tools" / "run_agibot_cleanup_backend.py"
COMPLETED_CONTEXT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "agibot_map_context.completed.json"


def test_generate_metric_map_from_completed_agibot_context(tmp_path: Path) -> None:
    generator = _load_module(GENERATOR_PATH, "generate_metric_map_from_context")
    context_path = tmp_path / "agibot_map_context.completed.json"
    output_dir = tmp_path / "generated"
    context_path.write_text(json.dumps(_completed_context()), encoding="utf-8")

    generator.main([str(context_path), "--output-dir", str(output_dir)])

    metric_map = json.loads((output_dir / "metric_map.json").read_text(encoding="utf-8"))
    fixture_hints = json.loads((output_dir / "fixture_hints.json").read_text(encoding="utf-8"))
    agent_view = json.loads((output_dir / "agent_view.json").read_text(encoding="utf-8"))

    assert metric_map["schema"] == "real_robot_map_bundle_v1"
    assert "map_source" not in metric_map
    assert "map_bundle" not in metric_map
    assert metric_map["occupancy_grid_artifact"] is None
    assert metric_map["map_preview_artifact"] == "semantic_preview.png"
    assert metric_map["inspection_waypoints"][0]["waypoint_source"] == "operator_recorded_pose"
    assert metric_map["inspection_waypoints"][0]["reachability_status"] == "verified"
    assert "verification" not in metric_map["inspection_waypoints"][0]
    assert metric_map["robot_pose"]["pose_source"] == "operator_recorded_pose"
    assert fixture_hints["schema"] == "static_fixture_semantic_map_v1"
    assert fixture_hints["fixture_hint_mode"] == "operator_authored_semantic_map"
    assert fixture_hints["contains_runtime_observations"] is False
    assert "agibot_gdk" not in json.dumps(agent_view)
    assert (output_dir / "semantic_preview.png").is_file()


def test_reachability_unverified_does_not_pass_as_verified(tmp_path: Path) -> None:
    generator = _load_module(GENERATOR_PATH, "generate_metric_map_from_context_unverified")
    context = _completed_context()
    context["inspection_waypoints"][0]["reachability_status"] = "unverified"
    context["inspection_waypoints"][0].pop("verification")
    context_path = tmp_path / "agibot_map_context.completed.json"
    output_dir = tmp_path / "generated"
    context_path.write_text(json.dumps(context), encoding="utf-8")

    generator.main([str(context_path), "--output-dir", str(output_dir)])

    metric_map = json.loads((output_dir / "metric_map.json").read_text(encoding="utf-8"))
    assert metric_map["inspection_waypoints"][0]["reachability_status"] == "unverified"


def test_generate_metric_map_rejects_todo_context(tmp_path: Path) -> None:
    generator = _load_module(GENERATOR_PATH, "generate_metric_map_from_context_todo")
    context = _completed_context()
    context["rooms"][0]["room_label"] = "TODO: room label"

    errors = generator.validate_context(context)

    assert "rooms[0].room_label is required" in errors


def test_capture_context_upsert_records_multiple_waypoints(tmp_path: Path) -> None:
    capture = _load_module(CAPTURE_PATH, "capture_map_context_views")
    context_path = tmp_path / "agibot_map_context.todo.json"
    context = {
        "schema": "agibot_gdk_map_context_authoring_v1",
        "map_source": {"type": "agibot_gdk_map_context", "map_id": 3, "map_name": "office"},
        "rooms": [],
        "fixtures": [],
        "inspection_waypoints": [],
        "waypoint_captures": [],
    }
    context_path.write_text(json.dumps(context), encoding="utf-8")

    loaded = json.loads(context_path.read_text(encoding="utf-8"))
    capture._upsert_capture_into_context(
        loaded,
        manifest=_capture_manifest("wp_sofa_front", x=1.0, y=2.0),
        manifest_path=tmp_path / "captures" / "wp_sofa_front" / "capture_manifest.json",
        context_dir=tmp_path,
        room_id="living_room",
        room_label="Living room",
        fixture_id="sofa",
        fixture_label="Sofa",
        fixture_category="sofa",
        waypoint_id="wp_sofa_front",
        waypoint_label="Sofa front",
    )
    capture._upsert_capture_into_context(
        loaded,
        manifest=_capture_manifest("wp_table_front", x=2.0, y=3.0),
        manifest_path=tmp_path / "captures" / "wp_table_front" / "capture_manifest.json",
        context_dir=tmp_path,
        room_id="living_room",
        room_label="Living room",
        fixture_id="table",
        fixture_label="Table",
        fixture_category="table",
        waypoint_id="wp_table_front",
        waypoint_label="Table front",
    )

    assert [item["waypoint_id"] for item in loaded["inspection_waypoints"]] == [
        "wp_sofa_front",
        "wp_table_front",
    ]
    assert {item["fixture_id"] for item in loaded["fixtures"]} == {"sofa", "table"}
    assert len(loaded["rooms"]) == 1
    assert loaded["inspection_waypoints"][0]["capture"]["manifest_path"] == (
        "captures/wp_sofa_front/capture_manifest.json"
    )


def test_verify_helpers_select_map_check_and_record_status() -> None:
    verifier = _load_module(VERIFY_PATH, "verify_waypoints_with_pnc")
    context = _completed_context()
    context["inspection_waypoints"].append(
        {
            "waypoint_id": "wp_table_front",
            "room_id": "living_room",
            "fixture_id": "sofa",
            "label": "Table front",
            "x": 2.0,
            "y": 2.0,
            "yaw": 0.0,
        }
    )

    selected = verifier.select_waypoints(
        context,
        all_waypoints=False,
        waypoint_ids=["wp_table_front"],
    )
    map_check = verifier.compare_current_map(
        context,
        {"id": 3, "name": "office_floor_1", "is_curr_map": True},
    )
    result = {
        "reachability_status": verifier.VERIFIED,
        "navigation_backend": "agibot_gdk",
        "primitive_provenance": "agibot_gdk_normal_navi",
    }
    verifier.record_waypoint_verification(selected[0], result)

    assert len(selected) == 1
    assert map_check["ok"] is True
    assert selected[0]["reachability_status"] == "verified"
    assert selected[0]["verification"]["primitive_provenance"] == "agibot_gdk_normal_navi"


def test_sdk_runner_writes_three_reviewable_dry_run_reports(tmp_path: Path) -> None:
    context_path = tmp_path / "agibot_map_context.completed.json"
    context_path.write_text(json.dumps(_completed_context()), encoding="utf-8")
    root = tmp_path / "sdk-runner"
    agent_view_dir = root / "01-agent-view"
    observe_dir = root / "02-observe"
    navigate_dir = root / "03-navigate"

    _run_sdk(
        "agent-view",
        "--context-json",
        str(context_path),
        "--output-dir",
        str(agent_view_dir),
    )
    _run_sdk(
        "observe",
        "--agent-view-json",
        str(agent_view_dir / "agent_view.json"),
        "--output-dir",
        str(observe_dir),
    )
    _run_sdk(
        "navigate-waypoint",
        "--agent-view-json",
        str(agent_view_dir / "agent_view.json"),
        "--output-dir",
        str(navigate_dir),
        "--waypoint-id",
        "wp_sofa_front",
    )

    agent_view = json.loads((agent_view_dir / "agent_view.json").read_text(encoding="utf-8"))
    navigate_result = json.loads((navigate_dir / "run_result.json").read_text(encoding="utf-8"))

    for report in (
        agent_view_dir / "report.html",
        observe_dir / "report.html",
        navigate_dir / "report.html",
    ):
        text = report.read_text(encoding="utf-8")
        assert "AgiBot SDK Runner Report" in text
        assert len(text) > 1000

    assert "agibot" not in json.dumps(agent_view).lower()
    assert "map_source" not in json.dumps(agent_view)
    assert "verification" not in json.dumps(agent_view)
    assert navigate_result["tool_response"]["navigation_status"] == "dry_run_not_executed"
    assert navigate_result["tool_response"]["primitive_provenance"] == "blocked_capability"


def test_sdk_runner_blocks_unverified_waypoint_before_dry_run_navigation(tmp_path: Path) -> None:
    context = _completed_context()
    context["inspection_waypoints"][0]["reachability_status"] = "unverified"
    context["inspection_waypoints"][0].pop("verification")
    context_path = tmp_path / "agibot_map_context.completed.json"
    context_path.write_text(json.dumps(context), encoding="utf-8")
    root = tmp_path / "sdk-runner"
    agent_view_dir = root / "01-agent-view"
    navigate_dir = root / "03-navigate"

    _run_sdk(
        "agent-view",
        "--context-json",
        str(context_path),
        "--output-dir",
        str(agent_view_dir),
    )
    proc = _run_sdk_allowing_failure(
        "navigate-waypoint",
        "--agent-view-json",
        str(agent_view_dir / "agent_view.json"),
        "--output-dir",
        str(navigate_dir),
        "--waypoint-id",
        "wp_sofa_front",
    )
    navigate_result = json.loads((navigate_dir / "run_result.json").read_text(encoding="utf-8"))

    assert proc.returncode == 2
    assert navigate_result["status"] == "blocked_capability"
    assert navigate_result["tool_response"]["failure_type"] == "waypoint_not_pnc_verified"
    assert navigate_result["tool_response"]["navigation_status"] == "blocked"


def _completed_context() -> dict:
    return json.loads(COMPLETED_CONTEXT_FIXTURE.read_text(encoding="utf-8"))


def _capture_manifest(waypoint_id: str, *, x: float, y: float) -> dict:
    return {
        "schema": "agibot_gdk_map_context_capture_v1",
        "captured_at": "2026-05-19T00:00:00Z",
        "waypoint_id": waypoint_id,
        "map_source": {
            "type": "agibot_gdk_map_context",
            "map_id": 3,
            "map_name": "office_floor_1",
            "is_curr_map": True,
        },
        "robot_pose": {
            "frame_id": "map",
            "x": x,
            "y": y,
            "yaw": 0.1,
            "pose_source": "agibot_gdk_slam_get_curr_pose",
        },
        "camera_results": [
            {
                "camera_name": "head_color",
                "ok": True,
                "image_path": "head_color.jpg",
            }
        ],
    }


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run_sdk(*args: str) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, str(SDK_RUNNER_PATH), *args],
        cwd=SDK_RUNNER_PATH.parent.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc


def _run_sdk_allowing_failure(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SDK_RUNNER_PATH), *args],
        cwd=SDK_RUNNER_PATH.parent.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
