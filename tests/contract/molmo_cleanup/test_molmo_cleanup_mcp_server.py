from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.backend import ApiSemanticCleanupBackend
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.mcp_server import (
    CURRENT_CONTRACT,
    MolmoCleanupMCPServer,
    make_molmo_cleanup_mcp,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario


def _clean_agent_sequence(server: MolmoCleanupMCPServer) -> dict:
    server.call_tool("observe")
    scene_objects = server.call_tool("scene_objects")
    target_by_object = {
        "mug_01": "sink_01",
        "book_01": "bookshelf_01",
        "towel_01": "laundry_hamper_01",
        "apple_01": "fridge_01",
        "toy_car_01": "toy_bin_01",
    }
    for object_id, receptacle_id in target_by_object.items():
        server.call_tool("navigate_to_object", object_id=object_id)
        server.call_tool("pick", object_id=object_id)
        server.call_tool("navigate_to_receptacle", receptacle_id=receptacle_id)
        if receptacle_id == "fridge_01":
            fridge = next(
                item
                for item in scene_objects["receptacles"]
                if item["receptacle_id"] == receptacle_id
            )
            assert fridge["name"] == "fridge"
            server.call_tool("open_receptacle", receptacle_id=receptacle_id)
            server.call_tool("place_inside", receptacle_id=receptacle_id)
        else:
            server.call_tool("place", receptacle_id=receptacle_id)
        server.call_tool("object_done", object_id=object_id, receptacle_id=receptacle_id)
    return server.call_tool("done", reason="agent cleanup complete")


def test_molmo_cleanup_mcp_server_exposes_current_contract_tools(tmp_path: Path) -> None:
    server = make_molmo_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        policy="codex_agent",
    )
    try:
        observe = server.call_tool("observe")
        scene_objects = server.call_tool("scene_objects")
    finally:
        server.close()

    assert observe["contract"] == CURRENT_CONTRACT
    assert "global_scene_objects" in observe["current_contract_shortcuts"]
    assert scene_objects["contract"] == CURRENT_CONTRACT
    assert scene_objects["private_target_truth_included"] is False
    assert "valid_receptacle_ids" not in json.dumps(scene_objects)


def test_molmo_cleanup_mcp_server_finalizes_agent_artifacts(tmp_path: Path) -> None:
    server = make_molmo_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        policy="codex_agent",
    )
    try:
        done = _clean_agent_sequence(server)
    finally:
        server.close()

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    trace_lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()

    assert done["cleanup_status"] == "success"
    assert done["contract"] == CURRENT_CONTRACT
    assert Path(done["report"]).is_file()
    assert run_result["contract"] == CURRENT_CONTRACT
    assert run_result["policy"] == "codex_agent"
    assert run_result["agent_driven"] is True
    assert run_result["policy_uses_private_truth"] is False
    assert run_result["mcp_server"] == "molmo_cleanup"
    assert run_result["score"]["restored_count"] == 5
    assert run_result["score"]["semantic_acceptability"]["accepted_count"] == 5
    assert run_result["score"]["object_results"][0]["exact_private_match"] is True
    assert run_result["score"]["object_results"][0]["semantic_acceptability"] == "preferred"
    assert run_result["agent_bridge"]["object_done_count"] == 5
    assert run_result["agent_bridge"]["stale_reference_errors"] == 0
    assert run_result["agent_bridge"]["fridge_inside_sequence_ok"] is True
    assert run_result["semantic_substeps"][0]["steps"][0]["phase"] == "navigate_to_object"
    assert "Semantic acceptability" in (tmp_path / "report.html").read_text(encoding="utf-8")
    assert any('"tool": "scene_objects"' in line for line in trace_lines)
    assert (tmp_path / "before.png").is_file()
    assert (tmp_path / "after.png").is_file()
    assert (tmp_path / "report.html").is_file()


def test_molmo_cleanup_mcp_server_records_stale_reference_errors(tmp_path: Path) -> None:
    server = make_molmo_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        policy="claude_code_agent",
    )
    try:
        stale = server.call_tool("pick", object_id="missing_01")
        server.call_tool("done", reason="stopped after stale reference")
    finally:
        server.close()
    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))

    assert stale["error_reason"] == "stale_reference"
    assert run_result["policy"] == "claude_code_agent"
    assert run_result["agent_bridge"]["stale_reference_errors"] == 1
    assert run_result["agent_bridge"]["premature_done"] is True


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


def test_molmo_cleanup_mcp_server_can_record_robot_view_timeline(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    backend = _FakeVisualBackend(scenario)
    contract = MolmoCleanupToolContract(scenario, backend=backend)
    server = make_molmo_cleanup_mcp(
        run_dir=tmp_path,
        scenario=scenario,
        contract=contract,
        port=0,
        policy="codex_agent",
        record_robot_views=True,
    )
    try:
        done = _clean_agent_sequence(server)
    finally:
        server.close()

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    report_text = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert done["cleanup_status"] == "success"
    assert run_result["view_variant"] == "molmospaces-rby1m-fpv-map-chase-verify"
    assert run_result["artifacts"]["robot_views"].endswith("robot_views")
    assert len(run_result["robot_view_steps"]) >= 20
    assert run_result["robot_view_steps"][0]["action"] == "before"
    assert "navigate_to_object mug_01" in {
        step["action"] for step in run_result["robot_view_steps"]
    }
    assert "Robot View Timeline" in report_text
