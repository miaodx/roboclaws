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
    result["agent_bridge"]["semantic_order_errors"] = 1

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
    result["agent_bridge"]["complete_semantic_substep_objects"] = (
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


def test_checker_rejects_unlabelled_camera_model_candidates(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )
    result["agent_view"]["observed_objects"][0].pop("model_provenance")

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
        }
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
