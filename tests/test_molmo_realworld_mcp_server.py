from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from roboclaws.molmo_cleanup.backend import ApiSemanticCleanupBackend
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.realworld_contract import REALWORLD_CONTRACT
from roboclaws.molmo_cleanup.realworld_mcp_server import (
    MCP_SERVER_NAME,
    make_molmo_realworld_cleanup_mcp,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario

REPO_ROOT = Path(__file__).resolve().parent.parent
SMOKE_PATH = REPO_ROOT / "scripts" / "run_molmo_realworld_agent_mcp_smoke.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("run_molmo_realworld_agent_mcp_smoke", SMOKE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_realworld_mcp_surface_uses_metric_map_and_visible_handles(tmp_path: Path) -> None:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
    )
    try:
        metric_map = server.call_tool("metric_map")
        fixture_hints = server.call_tool("fixture_hints")
        observation = {}
        for waypoint in metric_map["inspection_waypoints"]:
            waypoint_id = waypoint["waypoint_id"]
            server.call_tool("navigate_to_waypoint", waypoint_id=waypoint_id)
            observation = server.call_tool("observe")
            if observation["visible_object_detections"]:
                break
        with pytest.raises(ValueError, match="scene_objects"):
            server.call_tool("scene_objects")
    finally:
        server.close()

    assert metric_map["contract"] == REALWORLD_CONTRACT
    assert "objects" not in metric_map
    assert fixture_hints["fixture_hint_mode"] == "room_only"
    assert observation["visible_object_detections"]
    assert observation["visible_object_detections"][0]["object_id"].startswith("observed_")
    assert "target_receptacle_id" not in json.dumps(observation)


def test_realworld_mcp_rejects_skipped_semantic_pick_with_public_guidance(
    tmp_path: Path,
) -> None:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
    )
    try:
        metric_map = server.call_tool("metric_map")
        detection = None
        for waypoint in metric_map["inspection_waypoints"]:
            server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
            observation = server.call_tool("observe")
            detections = observation.get("visible_object_detections", [])
            if detections:
                detection = detections[0]
                break
        assert detection is not None

        skipped = server.call_tool("pick", object_id=detection["object_id"])
    finally:
        server.close()

    assert skipped["ok"] is False
    assert skipped["error_reason"] == "semantic_order"
    assert skipped["required_tool"] == "navigate_to_object"
    assert "generated_mess_set" not in json.dumps(skipped)
    assert "target_receptacle_id" not in json.dumps(skipped)


def test_realworld_mcp_smoke_writes_agent_artifacts(tmp_path: Path) -> None:
    smoke = _load_smoke_module()

    run_result = smoke.run_smoke(output_dir=tmp_path, seed=7)
    trace_text = (tmp_path / "trace.jsonl").read_text(encoding="utf-8")
    report_text = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert run_result["contract"] == REALWORLD_CONTRACT
    assert run_result["adr_0003_satisfied"] is True
    assert run_result["agent_driven"] is True
    assert run_result["policy"] == "realworld_contract_smoke_agent"
    assert run_result["policy_uses_private_truth"] is False
    assert run_result["planner_uses_private_manifest"] is False
    assert run_result["mcp_server"] == MCP_SERVER_NAME
    assert run_result["generated_mess_count"] == 5
    assert run_result["semantic_substeps"]
    assert run_result["tool_event_counts"]["metric_map:request"] == 1
    assert run_result["tool_event_counts"]["fixture_hints:request"] == 1
    assert run_result["tool_event_counts"]["observe:request"] >= 1
    assert run_result["agent_bridge"]["premature_done"] is False
    assert run_result["agent_bridge"]["premature_done_source"] == "sweep_coverage_rate"
    assert run_result["agent_bridge"]["semantic_order_errors"] == 0
    assert run_result["agent_view"]["observed_objects"]
    assert "metric_map" in trace_text
    assert "fixture_hints" in trace_text
    assert '"tool": "scene_objects"' not in trace_text
    assert "Agent View" in report_text
    assert "Private Evaluation" in report_text
    assert (tmp_path / "agent_view.json").is_file()
    assert (tmp_path / "private_evaluation.json").is_file()


class _FakeVisualBackend(ApiSemanticCleanupBackend):
    def write_robot_views(
        self,
        output_dir: Path,
        *,
        label: str,
        focus_object_id: str | None = None,
        focus_receptacle_id: str | None = None,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        views = {}
        for key in ("fpv", "chase", "map", "verify"):
            path = output_dir / f"{label}_{key}.png"
            path.write_bytes(b"fake png")
            views[key] = str(path)
        has_focus = bool(focus_object_id or focus_receptacle_id)
        return {
            "ok": True,
            "robot_pose": {
                "x": 1.0,
                "y": 2.0,
                "theta": 0.0,
                "head_pitch": -0.25,
                "theta_source": "target_facing_base_yaw",
                "head_pitch_source": "target_framing_head_pitch",
                "same_room_as_target": True,
            },
            "robot_trajectory": [{"x": 1.0, "y": 2.0}],
            "view_variant": "molmospaces-rby1m-fpv-map-chase-verify",
            "view_provenance": "test_fake_visual_backend",
            "focus": {
                "has_focus": has_focus,
                "object_id": focus_object_id,
                "receptacle_id": focus_receptacle_id,
                "provenance": "public_mujoco_state_report_aid" if has_focus else None,
                "fpv_visibility": {
                    "status": "ok",
                    "boxes": [{"label": focus_object_id or focus_receptacle_id}],
                    "object_pixels": 300,
                    "receptacle_pixels": 120,
                },
                "visibility": {
                    "status": "ok",
                    "boxes": [{"label": focus_object_id or focus_receptacle_id}],
                    "object_pixels": 150,
                    "receptacle_pixels": 120,
                },
            },
            "room_outline_count": 1,
            "views": views,
        }


def test_realworld_mcp_can_record_robot_view_timeline(tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    scenario = build_cleanup_scenario(seed=7)
    backend = _FakeVisualBackend(scenario)
    base_contract = MolmoCleanupToolContract(scenario, backend=backend)
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=scenario,
        base_contract=base_contract,
        port=0,
        record_robot_views=True,
    )
    try:
        smoke._drive_public_sweep(server, policy="realworld_contract_smoke_agent")
        done = server.call_tool("done", reason="realworld_contract_smoke_agent cleanup complete")
    finally:
        server.close()

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    report_text = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert done["cleanup_status"] in {"success", "partial_success"}
    assert run_result["view_variant"] == "molmospaces-rby1m-fpv-map-chase-verify"
    assert run_result["robot_view_steps"][0]["action"] == "before"
    assert any(
        step["semantic_phase"] == "navigate_to_object" for step in run_result["robot_view_steps"]
    )
    assert "Robot View Timeline" in report_text
