from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from roboclaws.household.backend import ApiSemanticCleanupBackend
from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.profiles import WORLD_LABELS_PROFILE
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    MINIMAL_MAP_MODE,
    RAW_FPV_ONLY_MODE,
    REALWORLD_CONTRACT,
    RICH_MAP_MODE,
    RealWorldCleanupContract,
)
from roboclaws.household.realworld_mcp_atomic_tools import ATOMIC_CLEANUP_TOOL_NAMES
from roboclaws.household.realworld_mcp_semantic_tools import SEMANTIC_CLEANUP_TOOL_NAMES
from roboclaws.household.realworld_mcp_server import (
    MCP_SERVER_NAME,
    make_molmo_realworld_cleanup_mcp,
)
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.mcp.profiles import MOLMOSPACES_CLEANUP_PROFILE, contract_profile

REPO_ROOT = Path(__file__).resolve().parents[3]
SMOKE_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_molmo_realworld_agent_mcp_smoke.py"
PREBUILT_BUNDLE = REPO_ROOT / "assets" / "maps" / "molmo-cleanup-default-7"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("run_molmo_realworld_agent_mcp_smoke", SMOKE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _fastmcp_tool_names(server: Any) -> set[str]:
    return set(server._mcp._tool_manager._tools)


def test_realworld_mcp_registered_tools_match_profile_public_surface(tmp_path: Path) -> None:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
    )
    try:
        profile = contract_profile(MOLMOSPACES_CLEANUP_PROFILE)

        assert _fastmcp_tool_names(server) == set(profile.public_tool_names())
        assert not profile.privileged_tool_names()
    finally:
        server.close()


def test_realworld_mcp_tool_files_are_layered_by_capability(tmp_path: Path) -> None:
    semantic = set(SEMANTIC_CLEANUP_TOOL_NAMES)
    atomic = set(ATOMIC_CLEANUP_TOOL_NAMES)

    assert semantic
    assert atomic
    assert semantic.isdisjoint(atomic)

    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        cleanup_profile=WORLD_LABELS_PROFILE,
    )
    try:
        assert _fastmcp_tool_names(server) == semantic | atomic | {"done"}
    finally:
        server.close()


def test_realworld_mcp_surface_uses_metric_map_and_visible_handles(tmp_path: Path) -> None:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        map_bundle_dir=PREBUILT_BUNDLE,
        map_mode=RICH_MAP_MODE,
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
    assert metric_map["schema"] == "real_robot_map_bundle_v1"
    assert metric_map["map_bundle"]["environment_id"] == "molmo-cleanup-default-7"
    assert "static map/fixture coverage candidates" in metric_map["instruction"]
    assert "objects" not in metric_map
    assert fixture_hints["fixture_hint_mode"] == "room_only"
    assert fixture_hints["schema"] == "static_fixture_semantic_map_v1"
    assert "Runtime movable objects come only from observe" in fixture_hints["instruction"]
    assert observation["visible_object_detections"]
    assert observation["visible_object_detections"][0]["object_id"].startswith("observed_")
    assert "target_receptacle_id" not in json.dumps(observation)
    assert "close_receptacle" in server.contract.public_tool_names()


def test_realworld_mcp_can_seed_runtime_metric_map_priors(tmp_path: Path) -> None:
    prior_server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path / "prior",
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
        map_mode=RICH_MAP_MODE,
    )
    try:
        metric_map = prior_server.call_tool("metric_map")
        for waypoint in metric_map["inspection_waypoints"]:
            prior_server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
            observation = prior_server.call_tool("observe")
            declared = prior_server.call_tool(
                "declare_visual_candidates",
                observation_id=observation["raw_fpv_observation"]["observation_id"],
            )
            if declared["model_declared_observations"]:
                break
        prior_snapshot = prior_server._agent_view_payload()["runtime_metric_map"]
    finally:
        prior_server.close()

    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path / "consumer",
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
        runtime_map_prior=prior_snapshot,
        runtime_map_prior_source="prior/runtime_metric_map.json",
        map_mode=RICH_MAP_MODE,
    )
    try:
        runtime_map = server._agent_view_payload()["runtime_metric_map"]
        prior_rows = [
            item for item in runtime_map["observed_objects"] if item["freshness"] == "prior"
        ]
        metric_map = server.call_tool("metric_map")
        for waypoint in metric_map["inspection_waypoints"]:
            server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
            server.call_tool("observe")
        done = server.call_tool("done", reason="prior seeded smoke")
        run_result = json.loads(Path(done["run_result"]).read_text(encoding="utf-8"))
    finally:
        server.close()

    assert prior_rows
    assert all(item["actionability"] == "needs_confirm" for item in prior_rows)
    assert run_result["runtime_metric_map_prior"] == {
        "loaded": True,
        "source": "prior/runtime_metric_map.json",
        "observed_object_count": len(prior_rows),
    }


def test_realworld_mcp_done_persists_facade_rerun_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    smoke = _load_smoke_module()
    prior = "output/household/semantic-map-build/anchor/seed-7/runtime_metric_map.json"
    command = (
        "just task::run household-cleanup codex world-labels seed=7 "
        "generated_mess_count=5 map_mode=minimal robot_views=on "
        f"runtime_map_prior={prior} "
        f"output_dir={tmp_path}"
    )
    monkeypatch.setenv(
        "ROBOCLAWS_REPORT_RERUN_COMMAND",
        "just task::run household-cleanup direct world-labels seed=7",
    )
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        rerun_command=command,
    )
    try:
        smoke._drive_public_sweep(server)
        server.call_tool("done", reason="rerun command smoke")
    finally:
        server.close()

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    report = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert run_result["rerun_command"] == command
    assert command in report
    assert "household-cleanup direct world-labels" not in report


def test_realworld_mcp_defaults_to_minimal_map_mode(tmp_path: Path) -> None:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
    )
    try:
        metric_map = server.call_tool("metric_map")
        fixture_hints = server.call_tool("fixture_hints")
        runtime_map = server._agent_view_payload()["runtime_metric_map"]
        for waypoint in metric_map["inspection_waypoints"]:
            server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
            server.call_tool("observe")
        agent_view = server._agent_view_payload()
    finally:
        server.close()

    assert metric_map["mode"] == MINIMAL_MAP_MODE
    assert metric_map["rooms"] == []
    assert metric_map["driveable_ways"] == []
    assert fixture_hints["rooms"] == []
    assert runtime_map["map_mode"] == MINIMAL_MAP_MODE
    assert runtime_map["static_map"]["fixtures"] == []
    assert agent_view["runtime_metric_map"]["map_mode"] == MINIMAL_MAP_MODE
    assert agent_view["cleanup_worklist"]["objects"]


def test_realworld_mcp_minimal_map_exposes_actionable_runtime_anchors(
    tmp_path: Path,
) -> None:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        map_mode=MINIMAL_MAP_MODE,
    )
    try:
        metric_map = server.call_tool("metric_map")
        fixture_hints = server.call_tool("fixture_hints")
        observed = None
        for waypoint in metric_map["inspection_waypoints"]:
            server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
            observation = server.call_tool("observe")
            if observation["visible_object_detections"]:
                observed = observation["visible_object_detections"][0]
        assert observed is not None

        agent_view = server._agent_view_payload()
        worklist_item = next(
            item
            for item in agent_view["cleanup_worklist"]["objects"]
            if item["object_id"] == observed["object_id"]
        )
        target_anchor_id = worklist_item["candidate_fixture_id"]
        server.call_tool("navigate_to_object", object_id=observed["object_id"])
        server.call_tool("pick", object_id=observed["object_id"])
        navigation = server.call_tool("navigate_to_receptacle", fixture_id=target_anchor_id)
    finally:
        server.close()

    assert fixture_hints["rooms"] == []
    assert "runtime_metric_map.public_semantic_anchors" in fixture_hints["instruction"]
    assert target_anchor_id.startswith("anchor_fixture_")
    assert navigation["fixture_id"] == target_anchor_id


def test_realworld_mcp_rejects_removed_cleanup_composite(
    tmp_path: Path,
) -> None:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        cleanup_profile=WORLD_LABELS_PROFILE,
    )
    try:
        removed_tool = "clean_observed_object"
        assert removed_tool not in _fastmcp_tool_names(server)
        assert removed_tool not in server._agent_view_payload()["public_tool_names"]
        with pytest.raises(ValueError, match=removed_tool):
            server.call_tool(
                removed_tool,
                object_id="observed_001",
                fixture_id="sink_01",
            )
    finally:
        server.close()


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
    assert run_result["agent_diagnostics"]["premature_done"] is False
    assert run_result["agent_diagnostics"]["premature_done_source"] == "sweep_coverage_rate"
    assert run_result["agent_diagnostics"]["semantic_order_errors"] == 0
    assert run_result["advisory_evaluation"]["authoritative"] is False
    assert run_result["advisory_evaluation"]["object_reviews"]
    assert run_result["agent_view"]["observed_objects"]
    assert run_result["cleanup_policy_trace"]["loop_style"] == "interleaved_cleanup_loop"
    assert run_result["cleanup_policy_trace"]["post_place_observe_complete"] is True
    assert run_result["real_robot_readiness"]["schema"] == "real_robot_readiness_v1"
    assert run_result["real_robot_readiness"]["semantic_navigation_only"] is True
    assert run_result["real_robot_readiness"]["map_bundle_snapshot_present"] is True
    assert "planner_object_id" not in json.dumps(run_result["agent_view"])
    assert run_result["planner_proof_requests"]["schema"] == "planner_cleanup_proof_requests_v1"
    assert run_result["planner_proof_requests"]["agent_view_exposed"] is False
    assert run_result["artifacts"]["planner_proof_requests"].endswith("planner_proof_requests.json")
    assert run_result["nav2_map_bundle"]["snapshot_complete"] is True
    assert "Planner Proof Requests" in report_text
    assert "Waypoint Honesty & Cleanup Loop" in report_text
    assert "Real-Robot Readiness" in report_text
    assert "Nav2 Map Bundle" in report_text
    assert "map_bundle/map.yaml" in report_text
    assert "report_only_simulation_view" in report_text
    assert "metric_map" in trace_text
    assert "fixture_hints" in trace_text
    assert '"tool": "scene_objects"' not in trace_text
    assert "Agent View" in report_text
    assert "Private Evaluation" in report_text
    assert (tmp_path / "agent_view.json").is_file()
    assert (tmp_path / "private_evaluation.json").is_file()
    assert (tmp_path / "advisory_evaluation.json").is_file()
    assert (tmp_path / "planner_proof_requests.json").is_file()
    assert (tmp_path / "map_bundle" / "map.yaml").is_file()
    assert (tmp_path / "map_bundle" / "map.pgm").is_file()
    assert (tmp_path / "map_bundle" / "semantics.json").is_file()
    assert (tmp_path / "map_bundle" / "preview.png").is_file()


class _FakeVisualBackend(ApiSemanticCleanupBackend):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.robot_view_camera_offsets: list[dict[str, float]] = []

    def write_robot_views(
        self,
        output_dir: Path,
        *,
        label: str,
        focus_object_id: str | None = None,
        focus_receptacle_id: str | None = None,
        camera_yaw_offset_deg: float = 0.0,
        camera_pitch_offset_deg: float = 0.0,
    ) -> dict[str, Any]:
        self.robot_view_camera_offsets.append(
            {
                "yaw_delta_deg": camera_yaw_offset_deg,
                "pitch_delta_deg": camera_pitch_offset_deg,
            }
        )
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
            "camera_control_contract": {
                "schema": "robot_view_camera_control_contract_v1",
                "status": "backend_local_robot_camera",
                "camera_model": "backend_local_robot_view",
                "same_pose_api": False,
                "agent_facing_fpv": {
                    "source": "test_fake_fpv",
                    "canonical_camera_control": False,
                },
            },
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
    base_contract = CleanupBackendSession(scenario, backend=backend)
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=scenario,
        base_contract=base_contract,
        port=0,
        record_robot_views=True,
    )
    try:
        smoke._drive_public_sweep(server)
        done = server.call_tool("done", reason="realworld_contract_smoke_agent cleanup complete")
    finally:
        server.close()

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    report_text = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert done["cleanup_status"] in {"success", "partial_success"}
    assert run_result["view_variant"] == "molmospaces-rby1m-fpv-map-chase-verify"
    assert run_result["robot_view_camera_control"]["schema"] == (
        "robot_view_camera_control_summary_v1"
    )
    assert run_result["robot_view_camera_control"]["same_pose_api"] is False
    assert run_result["robot_view_steps"][0]["action"] == "before"
    assert any(
        step["semantic_phase"] == "navigate_to_object" for step in run_result["robot_view_steps"]
    )
    assert "Robot View Timeline" in report_text
    assert "Robot-view camera" in report_text


def test_realworld_mcp_raw_fpv_mode_delivers_fpv_image_blocks(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    backend = _FakeVisualBackend(scenario)
    base_contract = CleanupBackendSession(scenario, backend=backend)
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=scenario,
        base_contract=base_contract,
        port=0,
        record_robot_views=True,
        perception_mode=RAW_FPV_ONLY_MODE,
    )
    try:
        metric_map = server.call_tool("metric_map")
        server.call_tool(
            "navigate_to_waypoint",
            waypoint_id=metric_map["inspection_waypoints"][0]["waypoint_id"],
        )
        server.call_tool("adjust_camera", yaw_delta_deg=15, pitch_delta_deg=-5)
        observation_blocks = server._mcp_observe_response()
    finally:
        server.close()

    assert isinstance(observation_blocks, list)
    assert len(observation_blocks) == 2
    observation = json.loads(observation_blocks[0])
    raw = observation["raw_fpv_observation"]

    assert observation["schema"] == "raw_fpv_mcp_observe_state_v1"
    assert observation["perception_mode"] == RAW_FPV_ONLY_MODE
    assert observation["visible_object_detections"] == []
    assert observation["cleanup_worklist_summary"] == {
        "schema": "cleanup_worklist_summary_v1",
        "object_count": 0,
        "handled_object_handles": [],
        "pending_object_handles": [],
        "objects": [],
        "next_actions": [],
        "next_action_count": 0,
        "held_object_id": None,
    }
    assert "inline_on_navigate" in observation["instruction"]
    assert "navigate_to_visual_candidate" in observation["instruction"]
    assert "declare_visual_candidates" not in observation["instruction"]
    assert raw["image_artifacts"]["fpv"].endswith(".png")
    assert "camera_control_contract" not in raw
    assert raw["camera_control_summary"] == {
        "schema": "robot_view_camera_control_contract_summary_v1",
        "contract_schema": "robot_view_camera_control_contract_v1",
        "status": "backend_local_robot_camera",
        "camera_model": "backend_local_robot_view",
        "same_pose_api": False,
        "agent_facing_fpv_source": "test_fake_fpv",
        "canonical_camera_control": False,
    }
    assert raw["camera_offset"] == {"yaw_delta_deg": 15.0, "pitch_delta_deg": -5.0}
    assert backend.robot_view_camera_offsets[-1] == {
        "yaw_delta_deg": 15.0,
        "pitch_delta_deg": -5.0,
    }
    assert (tmp_path / raw["image_artifacts"]["fpv"]).is_file()
    image_block = observation_blocks[1]
    assert hasattr(image_block, "data")
    assert isinstance(image_block.data, bytes)
    assert len(image_block.data) > 0


def test_realworld_mcp_raw_fpv_compact_state_includes_public_handled_handles(
    tmp_path: Path,
) -> None:
    scenario = build_cleanup_scenario(seed=7)
    backend = _FakeVisualBackend(scenario)
    base_contract = CleanupBackendSession(scenario, backend=backend)
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=scenario,
        base_contract=base_contract,
        port=0,
        record_robot_views=True,
        perception_mode=RAW_FPV_ONLY_MODE,
    )
    try:
        work_waypoint = next(
            item
            for item in server.contract.metric_map()["inspection_waypoints"]
            if item["waypoint_id"] == "generated_exploration_007"
        )
        server.call_tool("navigate_to_waypoint", waypoint_id=str(work_waypoint["waypoint_id"]))
        observation = server.call_tool("observe")
        candidate = server.call_tool(
            "navigate_to_visual_candidate",
            source_observation_id=observation["raw_fpv_observation"]["observation_id"],
            category="tomato",
            evidence_note="round produce item on the desk",
            image_region={"type": "verbal_region", "value": "front of desk"},
        )
        assert candidate["ok"] is True
        assert server.call_tool("pick", object_id=candidate["object_id"])["ok"] is True
        fixture_id = candidate["candidate_fixture_id"]
        assert server.call_tool("navigate_to_receptacle", fixture_id=fixture_id)["ok"] is True
        assert server.call_tool("place_inside", fixture_id=fixture_id)["ok"] is True
        observation_blocks = server._mcp_observe_response()
    finally:
        server.close()

    assert isinstance(observation_blocks, list)
    observation_state = json.loads(observation_blocks[0])
    image_block = observation_blocks[1]
    summary = observation_state["cleanup_worklist_summary"]
    objects = {item["object_id"]: item for item in summary["objects"]}
    assert candidate["object_id"] in summary["handled_object_handles"]
    assert objects[candidate["object_id"]]["state"] == "placed"
    assert objects[candidate["object_id"]]["category"]
    assert len(image_block.data) > 0


def test_realworld_mcp_raw_fpv_trace_records_agent_facing_compact_state(
    tmp_path: Path,
) -> None:
    scenario = build_cleanup_scenario(seed=7)
    backend = _FakeVisualBackend(scenario)
    base_contract = CleanupBackendSession(scenario, backend=backend)
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=scenario,
        base_contract=base_contract,
        port=0,
        record_robot_views=True,
        perception_mode=RAW_FPV_ONLY_MODE,
    )
    try:
        metric_map = server.call_tool("metric_map")
        server.call_tool(
            "navigate_to_waypoint",
            waypoint_id=metric_map["inspection_waypoints"][0]["waypoint_id"],
        )
        observation_blocks = server._mcp_observe_response()
    finally:
        server.close()

    observation_state = json.loads(observation_blocks[0])
    trace_events = [
        json.loads(line)
        for line in (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    trace_observe = next(
        event
        for event in trace_events
        if event["tool"] == "observe" and event["event"] == "response"
    )
    compact_state = trace_observe["response"]["agent_facing_compact_state"]

    assert compact_state["schema"] == "raw_fpv_mcp_observe_state_v1"
    assert compact_state["cleanup_worklist_summary"] == observation_state[
        "cleanup_worklist_summary"
    ]
    assert compact_state["raw_fpv_observation"]["observation_id"] == observation_state[
        "raw_fpv_observation"
    ]["observation_id"]
    assert "camera_control_contract" not in compact_state["raw_fpv_observation"]


def test_realworld_mcp_raw_fpv_compact_state_lists_actionable_pending_handles(
    tmp_path: Path,
) -> None:
    scenario = build_cleanup_scenario(seed=7)
    backend = _FakeVisualBackend(scenario)
    base_contract = CleanupBackendSession(scenario, backend=backend)
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=scenario,
        base_contract=base_contract,
        port=0,
        record_robot_views=True,
        perception_mode=RAW_FPV_ONLY_MODE,
    )
    try:
        server.call_tool("metric_map")
        server.call_tool("navigate_to_waypoint", waypoint_id="generated_exploration_003")
        server.call_tool("observe")
        server.call_tool("navigate_to_waypoint", waypoint_id="generated_exploration_007")
        observation = server.call_tool("observe")
        candidate = server.call_tool(
            "navigate_to_visual_candidate",
            source_observation_id=observation["raw_fpv_observation"]["observation_id"],
            category="tomato",
            evidence_note="round produce item on the desk",
            image_region={"type": "verbal_region", "value": "front of desk"},
        )
        assert candidate["ok"] is True
        assert candidate["required_next_tool"] == "pick"
        observation_blocks = server._mcp_observe_response()
    finally:
        server.close()

    observation_state = json.loads(observation_blocks[0])
    summary = observation_state["cleanup_worklist_summary"]
    next_action = summary["next_actions"][0]

    assert summary["next_action_count"] == 1
    assert next_action["object_id"] == candidate["object_id"]
    assert next_action["candidate_fixture_id"] == candidate["candidate_fixture_id"]
    assert next_action["recommended_tool"] == candidate["recommended_tool"]
    assert next_action["state"] == "navigating_to_object"
    assert next_action["tool_sequence"] == [
        "pick",
        "navigate_to_receptacle",
        candidate["recommended_tool"],
    ]


def test_realworld_mcp_raw_fpv_artifact_filters_private_camera_contract_keys(
    tmp_path: Path,
) -> None:
    scenario = build_cleanup_scenario(seed=7)
    contract = RealWorldCleanupContract(
        CleanupBackendSession(scenario),
        perception_mode=RAW_FPV_ONLY_MODE,
    )
    metric_map = contract.metric_map()
    contract.navigate_to_waypoint(metric_map["inspection_waypoints"][0]["waypoint_id"])
    observation = contract.observe()
    observation_id = observation["raw_fpv_observation"]["observation_id"]

    attached = contract.attach_raw_fpv_observation_artifact(
        observation_id,
        views={"fpv": "robot_views/raw_fpv_001.fpv.png"},
        robot_view_label="0001_observe_raw_fpv_001",
        camera_control_contract={
            "schema": "robot_view_camera_control_contract_v1",
            "agent_facing_fpv": {"source": "robot_0/head_camera"},
            "robot_pose": {
                "target_receptacle_id": "private_sink_01",
                "pose_request": {"target_receptacle_id": "private_sink_01"},
            },
        },
    )

    assert attached is not None
    assert attached["camera_control_contract"]["schema"] == (
        "robot_view_camera_control_contract_v1"
    )
    assert "target_receptacle_id" not in json.dumps(attached)


def test_realworld_mcp_camera_labels_declare_response_is_agent_compact(
    tmp_path: Path,
) -> None:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )
    try:
        metric_map = server.call_tool("metric_map")
        declaration = {}
        for waypoint in metric_map["inspection_waypoints"]:
            server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
            observation = server.call_tool("observe")
            declaration = server.call_tool(
                "declare_visual_candidates",
                observation_id=observation["raw_fpv_observation"]["observation_id"],
            )
            if declaration["model_declared_observations"]:
                break
        agent_view = server._agent_view_payload()
    finally:
        server.close()

    assert declaration["ok"] is True
    assert declaration["visual_grounding_pipeline"]["pipeline_id"] == "sim"
    assert declaration["model_declared_observations"]
    assert declaration["camera_model_candidates"]
    assert "model_declared_observation_evidence" not in declaration
    assert "visual_grounding_pipeline" not in declaration["model_declared_observations"][0]
    assert "model_declared_observation" not in declaration["camera_model_candidates"][0]
    assert agent_view["camera_model_policy_evidence"]["visual_grounding_pipeline_id"] == "sim"
