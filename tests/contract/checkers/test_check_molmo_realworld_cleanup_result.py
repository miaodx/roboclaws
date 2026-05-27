from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from roboclaws.molmo_cleanup.manipulation_provenance import (
    MANIPULATION_PROBE_CONTRACT,
    PLANNER_BACKED_PROVENANCE,
    planner_backed_probe_evidence,
)
from roboclaws.molmo_cleanup.realworld_contract import CAMERA_MODEL_POLICY_MODE

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_PATH = REPO_ROOT / "examples" / "molmo_cleanup" / "molmospaces_realworld_cleanup.py"
CHECKER_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "check_molmo_realworld_cleanup_result.py"
SMOKE_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_molmo_realworld_agent_mcp_smoke.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_checker_accepts_single_realworld_run(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    data, path = checker._load_run_results(tmp_path / "run_result.json")[0]
    checker._assert_result(
        data,
        path.parent,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
    )


def test_checker_can_require_runtime_metric_map(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_runtime_metric_map=True,
    )
    runtime_map = json.loads((tmp_path / "runtime_metric_map.json").read_text())
    assert runtime_map["schema"] == checker.RUNTIME_METRIC_MAP_SCHEMA
    assert "Runtime Metric Map" in (tmp_path / "report.html").read_text()


def test_checker_can_require_semantic_sweep_mode(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        semantic_sweep=True,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_runtime_metric_map=True,
        require_semantic_sweep=True,
        require_camera_model_policy=True,
    )
    counts = result["tool_event_counts"]
    assert counts["adjust_camera:request"] >= 1
    assert counts.get("pick:request") is None
    assert result["runtime_metric_map"]["observed_objects"]


def test_checker_rejects_runtime_metric_map_private_leak(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)
    result["runtime_metric_map"]["observed_objects"][0]["target_receptacle_id"] = "sink_01"
    result["agent_view"]["runtime_metric_map"] = result["runtime_metric_map"]

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_runtime_metric_map=True,
        )


def test_checker_rejects_actionable_runtime_map_prior(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    sweep = demo.run_realworld_cleanup(
        output_dir=tmp_path / "sweep",
        seed=7,
        semantic_sweep=True,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )
    result = demo.run_realworld_cleanup(
        output_dir=tmp_path / "cleanup",
        seed=7,
        runtime_map_prior_path=sweep["artifacts"]["runtime_metric_map"],
    )
    prior = next(
        item
        for item in result["runtime_metric_map"]["observed_objects"]
        if item["freshness"] == "prior"
    )
    prior["actionability"] = "actionable"
    result["agent_view"]["runtime_metric_map"] = result["runtime_metric_map"]

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path / "cleanup",
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_runtime_metric_map=True,
        )


def test_checker_allows_actionable_current_run_confirmation_of_prior(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)
    current = result["runtime_metric_map"]["observed_objects"][0]
    current["freshness"] = "current_run"
    current["prior_object_id"] = "observed_prior_001"
    current["snapshot_object_id"] = "observed_prior_001"
    current["actionability"] = "actionable"
    result["agent_view"]["runtime_metric_map"] = result["runtime_metric_map"]

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_runtime_metric_map=True,
    )


def test_checker_accepts_smoke_profile_metadata_and_report_note(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        cleanup_profile="smoke",
    )

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_profile="smoke",
        min_generated_mess_count=5,
    )


def test_checker_can_require_waypoint_honesty_and_real_robot_alignment(
    tmp_path: Path,
) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_waypoint_honesty=True,
        require_real_robot_alignment=True,
    )


def test_checker_accepts_isaac_selected_bindings_when_rows_match_scene_index(
    tmp_path: Path,
) -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    scene_bindings = _isaac_selected_scene_bindings()
    data = _isaac_runtime_result(tmp_path, scene_bindings)
    _write_isaac_scene_index(tmp_path, scene_bindings)

    checker._assert_isaac_runtime(
        data,
        tmp_path,
        _isaac_report_text(scene_bindings),
        require_real_runtime=False,
        require_scene_loaded=False,
        require_selected_usd_bindings=True,
        require_semantic_pose=False,
        require_robot_view_provenance=False,
        require_segmentation_evidence=False,
        require_snapshot_provenance=False,
    )


def test_checker_rejects_isaac_selected_binding_rows_without_usd_handle(
    tmp_path: Path,
) -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    scene_bindings = _isaac_selected_scene_bindings()
    scene_bindings["selected_object_bindings"]["mug_01"].pop("usd_handle")
    data = _isaac_runtime_result(tmp_path, scene_bindings)
    _write_isaac_scene_index(tmp_path, scene_bindings)

    with pytest.raises(AssertionError):
        checker._assert_isaac_runtime(
            data,
            tmp_path,
            _isaac_report_text(scene_bindings),
            require_real_runtime=False,
            require_scene_loaded=False,
            require_selected_usd_bindings=True,
            require_semantic_pose=False,
            require_robot_view_provenance=False,
            require_segmentation_evidence=False,
            require_snapshot_provenance=False,
        )


def test_checker_rejects_isaac_selected_binding_index_mismatch(
    tmp_path: Path,
) -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    scene_bindings = _isaac_selected_scene_bindings()
    data = _isaac_runtime_result(tmp_path, scene_bindings)
    _write_isaac_scene_index(
        tmp_path,
        scene_bindings,
        object_prim_path="/World/Objects/other_mug",
    )

    with pytest.raises(AssertionError):
        checker._assert_isaac_runtime(
            data,
            tmp_path,
            _isaac_report_text(scene_bindings),
            require_real_runtime=False,
            require_scene_loaded=False,
            require_selected_usd_bindings=True,
            require_semantic_pose=False,
            require_robot_view_provenance=False,
            require_segmentation_evidence=False,
            require_snapshot_provenance=False,
        )


def test_waypoint_honesty_allows_public_state_query_before_post_place_observe() -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    count = checker._post_place_observe_count_allowing_public_state_queries(
        {
            "events": [
                {"tool": "place", "role": "cleanup_action"},
                {"tool": "metric_map", "role": "setup_or_completion"},
                {"tool": "observe", "role": "coverage_scan_observe"},
            ]
        }
    )

    assert count == 1


def test_checker_rejects_waypoint_honesty_when_loop_is_survey_first(
    tmp_path: Path,
) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)
    result["cleanup_policy_trace"]["loop_style"] = "survey_first_cleanup_loop"
    result["cleanup_policy_trace"]["first_cleanup_before_full_survey"] = False

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_waypoint_honesty=True,
        )


def test_checker_rejects_real_robot_alignment_when_chase_is_policy_input(
    tmp_path: Path,
) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)
    result["agent_view"]["policy_view"]["chase_camera_policy_input"] = True
    result["real_robot_readiness"]["policy_view_chase_excluded"] = False

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_real_robot_alignment=True,
        )


def test_checker_rejects_too_small_generated_mess_set(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=6,
        )


def test_checker_accepts_realworld_mcp_smoke_policy(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="realworld_contract_smoke_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_clean_agent_run=True,
    )


def test_checker_accepts_openclaw_minimum_gate(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7, policy="openclaw_agent")

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="openclaw_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_openclaw_minimum=True,
    )


def test_checker_openclaw_minimum_allows_partial_report_without_semantic_section(
    tmp_path: Path,
) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7, policy="openclaw_agent")
    result["semantic_substeps"] = []
    result["mess_restoration_rate"] = 0.0
    result["sweep_coverage_rate"] = 0.0
    result["disturbance_count"] = 99
    result["cleanup_status"] = "incomplete"
    report_path = tmp_path / "report.html"
    report_path.write_text(
        report_path.read_text(encoding="utf-8").replace("Semantic Substeps", "Partial Trace"),
        encoding="utf-8",
    )

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="openclaw_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_openclaw_minimum=True,
    )


def test_checker_rejects_openclaw_minimum_without_public_tool_use(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7, policy="openclaw_agent")
    result["tool_event_counts"] = {}

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            expect_policy="openclaw_agent",
            expect_mcp_server="molmo_cleanup_realworld",
            min_generated_mess_count=5,
            require_agent_driven=True,
            require_openclaw_minimum=True,
        )


def test_checker_rejects_openclaw_minimum_for_non_openclaw_policy(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            expect_policy=None,
            expect_mcp_server="molmo_cleanup_realworld",
            min_generated_mess_count=5,
            require_agent_driven=True,
            require_openclaw_minimum=True,
        )


def test_checker_rejects_scene_objects_in_realworld_trace(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)
    trace_path = tmp_path / "trace.jsonl"
    with trace_path.open("a", encoding="utf-8") as fp:
        fp.write('{"tool": "scene_objects", "event": "request"}\n')

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            expect_policy="realworld_contract_smoke_agent",
            expect_mcp_server="molmo_cleanup_realworld",
            min_generated_mess_count=5,
            require_agent_driven=True,
            require_clean_agent_run=True,
        )


def test_checker_rejects_clean_run_with_semantic_order_errors(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)
    result["agent_diagnostics"]["semantic_order_errors"] = 1
    result["agent_diagnostics"]["semantic_order_unrecovered_errors"] = 1

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            expect_policy="realworld_contract_smoke_agent",
            expect_mcp_server="molmo_cleanup_realworld",
            min_generated_mess_count=5,
            require_agent_driven=True,
            require_clean_agent_run=True,
        )


def test_checker_accepts_clean_run_with_recovered_semantic_order_error(
    tmp_path: Path,
) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)
    retried_item = result["semantic_substeps"][0]
    placement_index = next(
        index
        for index, step in enumerate(retried_item["steps"])
        if step.get("phase") in {"place", "place_inside"} and step.get("ok") is True
    )
    recovered_tool = retried_item["steps"][placement_index]["phase"]
    failed_placement = dict(retried_item["steps"][placement_index])
    failed_placement.update(
        {
            "ok": False,
            "status": "error",
            "error_reason": "semantic_order",
            "required_tool": recovered_tool,
            "primitive_provenance": None,
            "location_id": None,
            "contained_in": None,
        }
    )
    retried_item["steps"].insert(placement_index, failed_placement)
    result["agent_diagnostics"]["semantic_order_errors"] = 1
    result["agent_diagnostics"].pop("semantic_order_recovered_errors", None)
    result["agent_diagnostics"].pop("semantic_order_unrecovered_errors", None)

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="realworld_contract_smoke_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_clean_agent_run=True,
    )


def test_checker_accepts_clean_run_with_successful_retry_after_failed_attempt(
    tmp_path: Path,
) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)
    retried_item = result["semantic_substeps"][0]
    pick_index = next(
        index for index, step in enumerate(retried_item["steps"]) if step.get("phase") == "pick"
    )
    failed_pick = dict(retried_item["steps"][pick_index])
    failed_pick.update(
        {
            "ok": False,
            "status": "error",
            "error_reason": "exception",
            "object_id": None,
            "primitive_provenance": None,
        }
    )
    retried_item["steps"].insert(pick_index, failed_pick)
    result["agent_diagnostics"]["complete_semantic_substep_objects"] = (
        int(result["generated_mess_count"]) - 1
    )

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="realworld_contract_smoke_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_clean_agent_run=True,
    )


def test_checker_rejects_clean_run_when_failed_attempt_never_recovers(
    tmp_path: Path,
) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)
    failed_item = result["semantic_substeps"][0]
    pick_step = next(step for step in failed_item["steps"] if step.get("phase") == "pick")
    pick_step.update(
        {
            "ok": False,
            "status": "error",
            "error_reason": "exception",
            "object_id": None,
            "primitive_provenance": None,
        }
    )

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            expect_policy="realworld_contract_smoke_agent",
            expect_mcp_server="molmo_cleanup_realworld",
            min_generated_mess_count=5,
            require_agent_driven=True,
            require_clean_agent_run=True,
        )


def test_checker_can_require_advisory_scoring(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="realworld_contract_smoke_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_clean_agent_run=True,
        require_advisory_scoring=True,
    )


def test_checker_can_require_raw_fpv_observation_artifacts(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode="raw_fpv_only",
    )
    robot_views = tmp_path / "robot_views"
    robot_views.mkdir()
    for name in ("raw.fpv.png", "raw.chase.png", "raw.map.png", "raw.verify.png"):
        (robot_views / name).write_bytes(b"placeholder")
    result["artifacts"]["robot_views"] = str(robot_views)
    _insert_robot_timeline_before_score(tmp_path / "report.html")
    for item in result["raw_fpv_observations"]:
        item["image_artifacts"] = {"fpv": "robot_views/raw.fpv.png"}
    for item in result["agent_view"]["raw_fpv_observations"]:
        item["image_artifacts"] = {"fpv": "robot_views/raw.fpv.png"}
    result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
    result["robot_view_steps"] = [
        {
            "action": "before",
            "room_outline_count": 1,
            "views": {
                "fpv": "robot_views/raw.fpv.png",
                "chase": "robot_views/raw.chase.png",
                "map": "robot_views/raw.map.png",
                "verify": "robot_views/raw.verify.png",
            },
            "focus": {"has_focus": False},
        },
        {
            "action": "observe raw_fpv_001",
            "room_outline_count": 1,
            "views": {
                "fpv": "robot_views/raw.fpv.png",
                "chase": "robot_views/raw.chase.png",
                "map": "robot_views/raw.map.png",
                "verify": "robot_views/raw.verify.png",
            },
            "focus": {"has_focus": False},
        },
    ]

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_robot_views=True,
        require_raw_fpv_observations=True,
    )


def test_checker_can_require_raw_fpv_model_declared_success_gate(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode="raw_fpv_only",
    )
    result["mess_restoration_rate"] = 0.5
    result["cleanup_status"] = "partial_success"
    result["score"]["restored_count"] = 3

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_model_declared_observations=True,
        min_model_declared_observations=5,
        min_model_declared_actions=5,
        min_semantic_accepted_count=5,
    )


def test_checker_rejects_raw_fpv_model_declared_semantic_shortfall(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode="raw_fpv_only",
    )
    result["score"]["semantic_acceptability"]["accepted_count"] = 4

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_model_declared_observations=True,
            min_model_declared_observations=5,
            min_model_declared_actions=5,
            min_semantic_accepted_count=5,
        )


def test_checker_rejects_duplicate_post_place_visual_navigation(tmp_path: Path) -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            _trace_response("observe", {"ok": True, "tool": "observe"}),
            _trace_response(
                "navigate_to_visual_candidate",
                {
                    "ok": True,
                    "tool": "navigate_to_visual_candidate",
                    "object_id": "observed_001",
                },
            ),
            _trace_response("pick", {"ok": True, "tool": "pick", "object_id": "observed_001"}),
            _trace_response("place", {"ok": True, "tool": "place", "object_id": "observed_001"}),
            _trace_response(
                "navigate_to_visual_candidate",
                {
                    "ok": True,
                    "tool": "navigate_to_visual_candidate",
                    "object_id": "observed_001",
                },
            ),
        ],
    )

    with pytest.raises(AssertionError):
        checker._assert_no_duplicate_post_place_navigation(trace_path)


def test_checker_allows_normal_visual_cleanup_trace(tmp_path: Path) -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            _trace_response("observe", {"ok": True, "tool": "observe"}),
            _trace_response(
                "navigate_to_visual_candidate",
                {
                    "ok": True,
                    "tool": "navigate_to_visual_candidate",
                    "object_id": "observed_001",
                },
            ),
            _trace_response("pick", {"ok": True, "tool": "pick", "object_id": "observed_001"}),
            _trace_response(
                "navigate_to_receptacle",
                {
                    "ok": True,
                    "tool": "navigate_to_receptacle",
                    "object_id": "observed_001",
                    "receptacle_id": "sink_01",
                },
            ),
            _trace_response("place", {"ok": True, "tool": "place", "object_id": "observed_001"}),
        ],
    )

    checker._assert_no_duplicate_post_place_navigation(trace_path)


def test_checker_can_require_attached_planner_proof(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    proof_path = _write_strict_planner_proof(tmp_path / "proof")
    cleanup_dir = tmp_path / "cleanup"

    result = demo.run_realworld_cleanup(
        output_dir=cleanup_dir,
        seed=7,
        planner_proof_run_result=proof_path,
    )

    assert result["primitive_provenance"] == "api_semantic"
    checker._assert_result(
        result,
        cleanup_dir,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_planner_proof_attachment=True,
        require_planner_proof_quality=True,
        require_planner_proof_min_steps=2,
    )


def test_checker_rejects_attached_proof_below_min_steps(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    proof_path = _write_strict_planner_proof(tmp_path / "proof", steps_executed=1)
    cleanup_dir = tmp_path / "cleanup"

    result = demo.run_realworld_cleanup(
        output_dir=cleanup_dir,
        seed=7,
        planner_proof_run_result=proof_path,
    )

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            cleanup_dir,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_planner_proof_attachment=True,
            require_planner_proof_quality=True,
            require_planner_proof_min_steps=2,
        )


def test_checker_accepts_blocked_planner_cleanup_bridge(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    proof_path = _write_strict_planner_proof(
        tmp_path / "proof",
        embodiment="rby1m",
        upstream_policy_class="CuroboPickAndPlacePlannerPolicy",
        curobo_available=True,
    )
    cleanup_dir = tmp_path / "cleanup"

    result = demo.run_realworld_cleanup(
        output_dir=cleanup_dir,
        seed=7,
        planner_proof_run_result=proof_path,
    )

    bridge = result["planner_cleanup_bridge_evidence"]
    assert bridge["status"] == "blocked_capability"
    assert bridge["target_runtime_ready"] is True
    assert bridge["cleanup_primitives_ready"] is False
    checker._assert_result(
        result,
        cleanup_dir,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_planner_proof_attachment=True,
        accept_blocked_planner_cleanup_primitives=True,
        accept_blocked_planner_cleanup_bridge=True,
    )


def test_realworld_cleanup_can_use_matching_probe_backed_executor(
    tmp_path: Path,
) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    proof_path = _write_strict_planner_proof(
        tmp_path / "proof",
        embodiment="rby1m",
        upstream_policy_class="CuroboPickAndPlacePlannerPolicy",
        curobo_available=True,
        cleanup_binding={
            "schema": "planner_probe_cleanup_primitive_binding_v1",
            "object_id": "observed_001",
            "target_receptacle_id": "toy_bin_01",
            "source_receptacle_id": "coffee_table_01",
            "planner_object_id": "pickup/body",
            "planner_target_receptacle_id": "dropoff/body",
            "tools": [
                "navigate_to_object",
                "pick",
                "navigate_to_receptacle",
                "place",
            ],
        },
    )
    cleanup_dir = tmp_path / "cleanup"

    result = demo.run_realworld_cleanup(
        output_dir=cleanup_dir,
        seed=7,
        planner_proof_run_result=proof_path,
        use_planner_proof_for_cleanup_primitives=True,
    )

    assert result["cleanup_status"] == "success"
    assert result["planner_proof_cleanup_executor_enabled"] is True
    evidence = result["cleanup_primitive_evidence"]
    assert evidence["status"] == "blocked_capability"
    bounded_object = next(
        item for item in evidence["objects"] if item["object_id"] == "observed_001"
    )
    assert bounded_object["planner_backed"] is True
    assert bounded_object["strict_proof_eligible"] is True
    for step in bounded_object["subphases"]:
        assert step["primitive_provenance"] == "planner_backed"
        assert step["planner_backed"] is True
        assert step["strict_proof_eligible"] is True
    normal_object = next(
        item for item in evidence["objects"] if item["object_id"] == "observed_002"
    )
    assert normal_object["planner_backed"] is False
    assert {step["primitive_provenance"] for step in normal_object["subphases"]} == {"api_semantic"}
    bridge = result["planner_cleanup_bridge_evidence"]
    assert bridge["target_runtime_ready"] is True
    assert bridge["cleanup_primitives_ready"] is False
    report = (cleanup_dir / "report.html").read_text(encoding="utf-8")
    assert "Cleanup Primitive Gate" in report
    assert "Planner Cleanup Bridge" in report
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    checker._assert_result(
        result,
        cleanup_dir,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        require_planner_proof_attachment=True,
        accept_blocked_planner_cleanup_primitives=True,
        require_bound_planner_cleanup_objects=["observed_001:toy_bin_01"],
        require_mixed_planner_cleanup_primitives=True,
        accept_blocked_planner_cleanup_bridge=True,
    )


def test_realworld_cleanup_mismatched_probe_binding_keeps_semantic_path(
    tmp_path: Path,
) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    proof_path = _write_strict_planner_proof(
        tmp_path / "proof",
        embodiment="rby1m",
        upstream_policy_class="CuroboPickAndPlacePlannerPolicy",
        curobo_available=True,
        cleanup_binding={
            "schema": "planner_probe_cleanup_primitive_binding_v1",
            "object_id": "observed_999",
            "target_receptacle_id": "toy_bin_01",
            "tools": [
                "navigate_to_object",
                "pick",
                "navigate_to_receptacle",
                "place",
            ],
        },
    )

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path / "cleanup",
        seed=7,
        planner_proof_run_result=proof_path,
        use_planner_proof_for_cleanup_primitives=True,
    )

    assert result["cleanup_status"] == "success"
    assert result["planner_proof_cleanup_executor_enabled"] is True
    primitive_summary = result["cleanup_primitive_evidence"]["primitive_provenance_summary"]
    assert set(primitive_summary) == {"api_semantic"}
    assert result["cleanup_primitive_evidence"]["planner_backed"] is False
    assert result["planner_cleanup_bridge_evidence"]["cleanup_primitives_ready"] is False


def test_realworld_cleanup_can_use_proof_bundle_for_full_gate_readiness(
    tmp_path: Path,
) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    proof_paths = [
        _write_strict_planner_proof(
            tmp_path / f"proof-{binding['object_id']}",
            embodiment="rby1m",
            upstream_policy_class="CuroboPickAndPlacePlannerPolicy",
            curobo_available=True,
            cleanup_binding=binding,
        )
        for binding in _seed7_cleanup_bindings()
    ]
    cleanup_dir = tmp_path / "cleanup"

    result = demo.run_realworld_cleanup(
        output_dir=cleanup_dir,
        seed=7,
        planner_proof_run_results=proof_paths,
        use_planner_proof_for_cleanup_primitives=True,
    )

    assert result["cleanup_status"] == "success"
    assert result["primitive_provenance"] == "planner_backed"
    assert result["cleanup_primitive_evidence"]["status"] == "planner_backed"
    assert result["planner_cleanup_bridge_evidence"]["status"] == "planner_backed"
    assert result["planner_backed_manipulation_proof"]["schema"] == (
        "planner_backed_cleanup_proof_bundle_v1"
    )
    assert result["planner_backed_manipulation_proof"]["proof_count"] == 5
    report = (cleanup_dir / "report.html").read_text(encoding="utf-8")
    assert "Attached Planner-Backed Proofs" in report
    assert "proof_001 Planner Initial" in report
    checker._assert_result(
        result,
        cleanup_dir,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        require_planner_proof_attachment=True,
        require_planner_backed_cleanup_primitives=True,
        require_bound_planner_cleanup_objects=["observed_006:fridge_01"],
        require_planner_cleanup_bridge_ready=True,
    )


def test_checker_rejects_current_cleanup_when_bridge_ready_required(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    proof_path = _write_strict_planner_proof(
        tmp_path / "proof",
        embodiment="rby1m",
        upstream_policy_class="CuroboPickAndPlacePlannerPolicy",
        curobo_available=True,
    )
    cleanup_dir = tmp_path / "cleanup"

    result = demo.run_realworld_cleanup(
        output_dir=cleanup_dir,
        seed=7,
        planner_proof_run_result=proof_path,
    )

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            cleanup_dir,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_planner_cleanup_bridge_ready=True,
        )


def test_checker_accepts_blocked_cleanup_primitive_gate(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
        accept_blocked_planner_cleanup_primitives=True,
    )
    assert result["cleanup_primitive_evidence"]["status"] == "blocked_capability"


def test_checker_rejects_current_cleanup_when_planner_primitives_required(
    tmp_path: Path,
) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_planner_backed_cleanup_primitives=True,
        )


def test_checker_rejects_missing_required_planner_proof(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_planner_proof_attachment=True,
        )


def test_checker_rejects_raw_fpv_when_structured_detections_leak(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode="raw_fpv_only",
    )
    robot_views = tmp_path / "robot_views"
    robot_views.mkdir()
    fpv = robot_views / "raw.fpv.png"
    fpv.write_bytes(b"placeholder")
    result["artifacts"]["robot_views"] = str(robot_views)
    result["raw_fpv_observations"][0]["image_artifacts"] = {"fpv": "robot_views/raw.fpv.png"}
    result["raw_fpv_observations"][0]["support_estimate"] = {"fixture_id": "sink_01"}
    result["agent_view"]["raw_fpv_observations"] = result["raw_fpv_observations"]

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=5,
            require_raw_fpv_observations=True,
        )


def test_checker_can_require_camera_model_policy(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="camera_model_policy_baseline",
        min_generated_mess_count=5,
        require_camera_model_policy=True,
        accept_blocked_planner_cleanup_primitives=True,
    )


def test_checker_allows_main_agent_model_declared_camera_policy_retry(tmp_path: Path) -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    raw_fpv = tmp_path / "robot_views" / "raw_fpv_001.jpg"
    raw_fpv.parent.mkdir(parents=True)
    raw_fpv.write_bytes(b"raw-fpv")
    overlay = tmp_path / "visual_grounding" / "overlays" / "raw_fpv_001" / "candidate_001.jpg"
    overlay.parent.mkdir(parents=True)
    overlay.write_bytes(b"overlay")
    result = _external_visual_grounding_checker_result(
        overlay="visual_grounding/overlays/raw_fpv_001/candidate_001.jpg"
    )
    result["model_declared_observations"][0]["perception_source"] = "model_declared_observation"
    main_agent_retry = dict(result["model_declared_observations"][0])
    main_agent_retry.update(
        {
            "object_id": "observed_002",
            "producer_type": "main_cleanup_agent",
            "producer_id": "cleanup_agent",
            "model_provenance": None,
            "support_estimate": None,
            "grounding_status": "unresolved",
            "grounding_confidence": 0.05,
            "grounding_basis": "no public camera-context object matched",
            "recovery_hint": "Reobserve from another waypoint.",
        }
    )
    main_agent_retry.pop("visual_grounding_overlay", None)
    main_agent_retry.pop("visual_grounding_pipeline", None)
    manual_event = dict(result["camera_model_policy_evidence"]["events"][0])
    manual_event.update(
        {
            "producer_type": "main_cleanup_agent",
            "producer_id": "cleanup_agent",
            "registered_observed_handles": ["observed_002"],
            "visual_grounding_pipeline": {
                "schema": "visual_grounding_pipeline_v1",
                "pipeline_id": "manual",
                "status": "ok",
                "candidate_count": 1,
                "unresolved_count": 0,
                "duplicate_rate": 0.0,
                "stages": [
                    {
                        "stage": "manual_declaration",
                        "producer_id": "cleanup_agent",
                        "model_id": "main_cleanup_agent",
                        "status": "ok",
                        "latency_ms": 0,
                    }
                ],
            },
        }
    )
    result["camera_model_policy_evidence"]["visual_grounding_pipeline_id"] = "manual"
    result["camera_model_policy_evidence"]["visual_grounding_pipeline_ids"] = [
        "fake-http",
        "manual",
    ]
    result["camera_model_policy_evidence"]["events"].append(manual_event)

    checker._assert_public_agent_view(
        {
            "contract": checker.REALWORLD_CONTRACT,
            "forbidden_private_fields_absent": True,
            "metric_map": {},
            "fixture_hints": [],
            "perception_mode": CAMERA_MODEL_POLICY_MODE,
            "structured_detections_available": False,
            "raw_fpv_observations": result["raw_fpv_observations"],
            "camera_model_policy_evidence": result["camera_model_policy_evidence"],
            "observed_objects": [
                result["model_declared_observations"][0],
                main_agent_retry,
            ],
        }
    )
    checker._assert_camera_model_policy(
        result,
        tmp_path,
        "Camera Model Policy Raw FPV Observations fake-http manual Overlay",
        expect_pipeline_id="fake-http",
    )


def test_checker_requires_external_visual_grounding_bbox_overlay(tmp_path: Path) -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    raw_fpv = tmp_path / "robot_views" / "raw_fpv_001.jpg"
    raw_fpv.parent.mkdir(parents=True)
    raw_fpv.write_bytes(b"raw-fpv")
    overlay = tmp_path / "visual_grounding" / "overlays" / "raw_fpv_001" / "candidate_001.jpg"
    overlay.parent.mkdir(parents=True)
    overlay.write_bytes(b"overlay")
    result = _external_visual_grounding_checker_result(
        overlay="visual_grounding/overlays/raw_fpv_001/candidate_001.jpg"
    )

    checker._assert_camera_model_policy(
        result,
        tmp_path,
        "Camera Model Policy Raw FPV Observations fake-http Overlay",
        expect_pipeline_id="fake-http",
    )


def test_checker_rejects_external_visual_grounding_bbox_without_overlay(
    tmp_path: Path,
) -> None:
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")
    raw_fpv = tmp_path / "robot_views" / "raw_fpv_001.jpg"
    raw_fpv.parent.mkdir(parents=True)
    raw_fpv.write_bytes(b"raw-fpv")
    result = _external_visual_grounding_checker_result(overlay="")

    with pytest.raises(AssertionError):
        checker._assert_camera_model_policy(
            result,
            tmp_path,
            "Camera Model Policy Raw FPV Observations fake-http Overlay",
            expect_pipeline_id="fake-http",
        )


def test_checker_rejects_unlabelled_camera_model_candidates(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )
    result["agent_view"]["observed_objects"][0].pop("model_provenance")
    result["agent_view"]["observed_objects"][0].pop("producer_type")

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            expect_policy="camera_model_policy_baseline",
            min_generated_mess_count=5,
            require_camera_model_policy=True,
        )


def test_checker_can_require_robot_view_report_artifacts(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)
    robot_views = tmp_path / "robot_views"
    robot_views.mkdir()
    for name in ("step.fpv.png", "step.chase.png", "step.map.png", "step.verify.png"):
        (robot_views / name).write_bytes(b"placeholder")
    _insert_robot_timeline_before_score(tmp_path / "report.html")
    result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
    result["artifacts"]["robot_views"] = str(robot_views)
    result["robot_view_steps"] = [
        _robot_step("navigate_to_object observed_001"),
        _robot_step("pick observed_001"),
        _robot_step("navigate_to_receptacle refrigerator_01"),
        _robot_step("open_receptacle refrigerator_01"),
        _robot_step("place_inside observed_001"),
        _robot_step("close_receptacle refrigerator_01"),
        _robot_step("place observed_002"),
    ]

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        require_robot_views=True,
    )


def test_checker_openclaw_minimum_robot_views_allows_partial_visual_actions(
    tmp_path: Path,
) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7, policy="openclaw_agent")
    robot_views = tmp_path / "robot_views"
    robot_views.mkdir()
    for name in ("step.fpv.png", "step.chase.png", "step.map.png", "step.verify.png"):
        (robot_views / name).write_bytes(b"placeholder")
    _insert_robot_timeline_before_score(tmp_path / "report.html")
    result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
    result["artifacts"]["robot_views"] = str(robot_views)
    result["robot_view_steps"] = [
        _robot_step("pick observed_001"),
        _robot_step("place observed_001"),
    ]

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="openclaw_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_openclaw_minimum=True,
        require_robot_views=True,
    )


def test_checker_rejects_zero_pixel_focused_surface_action(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7, policy="openclaw_agent")
    robot_views = tmp_path / "robot_views"
    robot_views.mkdir()
    for name in ("step.fpv.png", "step.chase.png", "step.map.png", "step.verify.png"):
        (robot_views / name).write_bytes(b"placeholder")
    _insert_robot_timeline_before_score(tmp_path / "report.html")
    result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
    result["artifacts"]["robot_views"] = str(robot_views)
    result["robot_view_steps"] = [
        {
            **_robot_step("navigate_to_object observed_001"),
            "focus": {
                "has_focus": True,
                "object_id": "observed_001",
                "receptacle_id": "table_01",
                "fpv_visibility": {
                    "status": "ok",
                    "object_pixels": 0,
                    "receptacle_pixels": 100,
                },
                "visibility": {
                    "status": "ok",
                    "object_pixels": 0,
                    "receptacle_pixels": 100,
                },
            },
        },
        _robot_step("pick observed_001"),
    ]

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            expect_policy="openclaw_agent",
            expect_mcp_server="molmo_cleanup_realworld",
            min_generated_mess_count=5,
            require_agent_driven=True,
            require_openclaw_minimum=True,
            require_robot_views=True,
        )


def test_checker_allows_weak_fpv_when_verify_view_is_grounded(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7, policy="openclaw_agent")
    robot_views = tmp_path / "robot_views"
    robot_views.mkdir()
    for name in ("step.fpv.png", "step.chase.png", "step.map.png", "step.verify.png"):
        (robot_views / name).write_bytes(b"placeholder")
    _insert_robot_timeline_before_score(tmp_path / "report.html")
    result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
    result["artifacts"]["robot_views"] = str(robot_views)
    result["robot_view_steps"] = [
        {
            **_robot_step("navigate_to_object observed_001"),
            "focus": {
                "has_focus": True,
                "object_id": "observed_001",
                "receptacle_id": "table_01",
                "fpv_visibility": {
                    "status": "ok",
                    "object_pixels": 0,
                    "receptacle_pixels": 100,
                },
                "visibility": {
                    "status": "ok",
                    "object_pixels": 42,
                    "receptacle_pixels": 100,
                },
            },
        },
        _robot_step("pick observed_001"),
    ]

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="openclaw_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_openclaw_minimum=True,
        require_robot_views=True,
    )


def test_checker_allows_segmentation_unavailable_focused_surface_action(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7, policy="openclaw_agent")
    robot_views = tmp_path / "robot_views"
    robot_views.mkdir()
    for name in ("step.fpv.png", "step.chase.png", "step.map.png", "step.verify.png"):
        (robot_views / name).write_bytes(b"placeholder")
    _insert_robot_timeline_before_score(tmp_path / "report.html")
    result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
    result["artifacts"]["robot_views"] = str(robot_views)
    result["robot_view_steps"] = [
        {
            **_robot_step("navigate_to_object observed_001"),
            "focus": {
                "has_focus": True,
                "object_id": "observed_001",
                "receptacle_id": "table_01",
                "fpv_visibility": {
                    "status": "segmentation_unavailable",
                    "error": "IndexError",
                    "object_pixels": 0,
                    "receptacle_pixels": 0,
                },
                "visibility": {
                    "status": "segmentation_unavailable",
                    "error": "IndexError",
                    "object_pixels": 0,
                    "receptacle_pixels": 0,
                },
            },
        },
        _robot_step("pick observed_001"),
    ]

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="openclaw_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
        require_agent_driven=True,
        require_openclaw_minimum=True,
        require_robot_views=True,
    )


def test_checker_rejects_agent_view_private_leak(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)
    result["agent_view"]["generated_mess_set"] = ["leak"]

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
        )


def _external_visual_grounding_checker_result(*, overlay: str) -> dict[str, object]:
    pipeline = {
        "schema": "visual_grounding_pipeline_v1",
        "pipeline_id": "fake-http",
        "status": "ok",
        "stages": [
            {
                "stage": "proposer",
                "producer_id": "fake-http",
                "model_id": "fake",
                "status": "ok",
                "latency_ms": 1,
            }
        ],
        "candidate_count": 1,
        "unresolved_count": 0,
        "duplicate_rate": 0.0,
    }
    observation = {
        "schema": "model_declared_observation_v1",
        "declaration_id": "declared_001",
        "object_id": "observed_001",
        "source_observation_id": "raw_fpv_001",
        "waypoint_id": "wp_kitchen_01",
        "room_id": "kitchen",
        "category": "dish",
        "target_fixture_id": "sink_01",
        "target_fixture_category": "sink",
        "source_fixture_id": "counter_01",
        "evidence_note": "fake dish",
        "image_region": {"type": "bbox", "value": [0.1, 0.2, 0.3, 0.4]},
        "confidence": 0.8,
        "producer_type": "external_visual_grounding_service",
        "producer_id": "fake-http",
        "grounding_status": "resolved",
        "grounding_confidence": 0.8,
        "grounding_basis": "single public camera-context object matched",
        "recovery_hint": "",
        "target_plausibility": {"status": "plausible"},
        "actionability_status": "actionable",
        "private_truth_included": False,
        "visual_grounding_pipeline": pipeline,
        "visual_grounding_overlay": overlay,
    }
    event = {
        "schema": "model_declared_observations_v1",
        "perception_mode": CAMERA_MODEL_POLICY_MODE,
        "observation_id": "raw_fpv_001",
        "waypoint_id": "wp_kitchen_01",
        "room_id": "kitchen",
        "producer_type": "external_visual_grounding_service",
        "producer_id": "fake-http",
        "candidate_count": 1,
        "registered_observed_handles": ["observed_001"],
        "visual_grounding_pipeline": pipeline,
        "private_truth_included": False,
    }
    return {
        "perception_mode": CAMERA_MODEL_POLICY_MODE,
        "raw_fpv_observations": [
            {
                "observation_id": "raw_fpv_001",
                "waypoint_id": "wp_kitchen_01",
                "room_id": "kitchen",
                "image_artifacts": {"fpv": "robot_views/raw_fpv_001.jpg"},
            }
        ],
        "camera_model_policy_evidence": {
            "schema": "camera_model_policy_v1",
            "perception_mode": CAMERA_MODEL_POLICY_MODE,
            "enabled": True,
            "model_provenance": "external_visual_grounding_service",
            "visual_grounding_pipeline_id": "fake-http",
            "visual_grounding_pipeline_ids": ["fake-http"],
            "visual_grounding_failure_count": 0,
            "event_count": 1,
            "candidate_count": 1,
            "unresolved_count": 0,
            "duplicate_rate": 0.0,
            "events": [event],
            "private_truth_included": False,
        },
        "model_declared_observation_evidence": {
            "schema": "model_declared_observations_v1",
            "observation_count": 1,
            "resolved_count": 1,
            "acted_count": 0,
            "observations": [observation],
            "private_truth_included": False,
        },
        "model_declared_observations": [observation],
        "tool_event_counts": {"declare_visual_candidates:request": 1},
    }


def _robot_step(action: str) -> dict[str, object]:
    return {
        "action": action,
        "room_outline_count": 1,
        "views": {
            "fpv": "robot_views/step.fpv.png",
            "chase": "robot_views/step.chase.png",
            "map": "robot_views/step.map.png",
            "verify": "robot_views/step.verify.png",
        },
        "focus": {
            "has_focus": True,
            "fpv_visibility": {"status": "ok"},
            "visibility": {"status": "ok"},
        },
    }


def _trace_response(tool: str, response: dict[str, object]) -> dict[str, object]:
    return {"event": "response", "tool": tool, "response": response}


def _write_trace(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )


def _isaac_selected_scene_bindings() -> dict[str, object]:
    return {
        "schema": "isaac_public_scene_bindings_v1",
        "status": "selected_bound",
        "source": "usd_stage_traversal",
        "selected_object_count": 1,
        "selected_target_receptacle_count": 1,
        "selected_object_bound_count": 1,
        "selected_target_receptacle_bound_count": 1,
        "selected_object_bindings": {
            "mug_01": {
                "status": "bound",
                "usd_handle": "mug_01",
                "usd_prim_path": "/World/Objects/mug_01",
                "match_strategy": "exact_public_id",
                "index_source": "usd_stage_traversal",
            }
        },
        "selected_target_receptacle_bindings": {
            "sink_01": {
                "status": "bound",
                "usd_handle": "sink_01",
                "usd_prim_path": "/World/Receptacles/sink_01",
                "match_strategy": "exact_public_id",
                "index_source": "usd_stage_traversal",
            }
        },
        "blockers": [],
        "private_manifest_exposed_to_agent": False,
    }


def _isaac_runtime_result(
    base: Path,
    scene_bindings: dict[str, object],
) -> dict[str, object]:
    return {
        "backend": "isaaclab_subprocess",
        "artifacts": {"isaac_scene_index": str(base / "isaac_scene_index.json")},
        "isaac_runtime": {
            "runtime": {"primitive_provenance": "isaac_semantic_pose"},
            "scene_binding_diagnostics": scene_bindings,
            "scene_index_artifact": str(base / "isaac_scene_index.json"),
            "segmentation": {
                "status": "blocked_capability",
                "agent_facing": False,
                "no_simulator_label_fallback": True,
            },
        },
    }


def _write_isaac_scene_index(
    base: Path,
    scene_bindings: dict[str, object],
    *,
    object_prim_path: str = "/World/Objects/mug_01",
) -> None:
    payload = {
        "schema": "isaac_scene_index_artifact_v1",
        "backend": "isaaclab_subprocess",
        "agent_facing": False,
        "private_manifest_exposed_to_agent": False,
        "object_index": {"mug_01": {"usd_prim_path": object_prim_path}},
        "object_index_count": 1,
        "receptacle_index": {
            "sink_01": {"usd_prim_path": "/World/Receptacles/sink_01"},
        },
        "receptacle_index_count": 1,
        "scene_binding_diagnostics": scene_bindings,
    }
    (base / "isaac_scene_index.json").write_text(json.dumps(payload), encoding="utf-8")


def _isaac_report_text(scene_bindings: dict[str, object]) -> str:
    selected_objects = scene_bindings.get("selected_object_bindings") or {}
    selected_receptacles = scene_bindings.get("selected_target_receptacle_bindings") or {}
    rows = [*selected_objects.values(), *selected_receptacles.values()]
    row_text = " ".join(
        f"{row.get('usd_handle', '')} {row.get('usd_prim_path', '')}"
        for row in rows
        if isinstance(row, dict)
    )
    return (
        "Isaac Runtime Diagnostics Scene Index Artifact Rows "
        "Selected USD Binding Rows Selected USD Index Rows "
        f"{row_text}"
    )


def _seed7_cleanup_bindings() -> list[dict[str, object]]:
    return [
        _cleanup_binding("observed_001", "coffee_table_01", "toy_bin_01", ["place"]),
        _cleanup_binding("observed_002", "sofa_01", "sink_01", ["place"]),
        _cleanup_binding(
            "observed_003",
            "armchair_01",
            "laundry_hamper_01",
            ["place"],
        ),
        _cleanup_binding("observed_005", "floor_01", "bookshelf_01", ["place_inside"]),
        _cleanup_binding(
            "observed_006",
            "desk_01",
            "fridge_01",
            ["open_receptacle", "place_inside", "close_receptacle"],
        ),
    ]


def _cleanup_binding(
    object_id: str,
    source_receptacle_id: str,
    target_receptacle_id: str,
    target_tools: list[str],
) -> dict[str, object]:
    return {
        "schema": "planner_probe_cleanup_primitive_binding_v1",
        "object_id": object_id,
        "target_receptacle_id": target_receptacle_id,
        "source_receptacle_id": source_receptacle_id,
        "planner_object_id": f"{object_id}/body",
        "planner_target_receptacle_id": f"{target_receptacle_id}/body",
        "tools": [
            "navigate_to_object",
            "pick",
            "navigate_to_receptacle",
            *target_tools,
        ],
    }


def _insert_robot_timeline_before_score(report: Path) -> None:
    report_text = report.read_text(encoding="utf-8")
    robot_timeline = (
        '\n<section class="panel robot-timeline"><h2>Robot View Timeline</h2></section>'
    )
    score_marker = '<section class="panel">\n      <h2>Score</h2>'
    if score_marker in report_text:
        report_text = report_text.replace(score_marker, robot_timeline + "\n" + score_marker)
    else:
        report_text += robot_timeline
    report.write_text(report_text, encoding="utf-8")


def _write_strict_planner_proof(
    base: Path,
    *,
    embodiment: str = "franka",
    upstream_policy_class: str = "PickAndPlacePlannerPolicy",
    curobo_available: bool = False,
    cleanup_binding: dict[str, object] | None = None,
    steps_executed: int = 2,
    max_abs_qpos_delta: float = 0.01,
) -> Path:
    base.mkdir(parents=True)
    views = base / "planner_views"
    views.mkdir()
    (views / "initial_wrist_camera.png").write_bytes(b"initial")
    (views / "final_wrist_camera.png").write_bytes(b"final")
    evidence = planner_backed_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment=embodiment,
        task="pick_and_place",
        probe_mode="execute",
        upstream_policy_class=upstream_policy_class,
        steps_requested=2,
        steps_executed=steps_executed,
        max_abs_qpos_delta=max_abs_qpos_delta,
        image_artifacts={
            "initial": "planner_views/initial_wrist_camera.png",
            "final": "planner_views/final_wrist_camera.png",
        },
    )
    evidence["runtime_diagnostics"] = {
        "renderer_adapter_enabled": True,
        "modules": {"curobo": {"available": curobo_available}},
    }
    if cleanup_binding is not None:
        evidence["cleanup_primitive_binding"] = cleanup_binding
    path = base / "run_result.json"
    path.write_text(
        json.dumps(
            {
                "contract": MANIPULATION_PROBE_CONTRACT,
                "status": PLANNER_BACKED_PROVENANCE,
                "primitive_provenance": PLANNER_BACKED_PROVENANCE,
                "manipulation_evidence": evidence,
            }
        ),
        encoding="utf-8",
    )
    return path
