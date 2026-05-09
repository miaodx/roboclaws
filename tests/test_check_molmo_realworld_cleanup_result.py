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

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PATH = REPO_ROOT / "examples" / "molmospaces_realworld_cleanup.py"
CHECKER_PATH = REPO_ROOT / "scripts" / "check_molmo_realworld_cleanup_result.py"
SMOKE_PATH = REPO_ROOT / "scripts" / "run_molmo_realworld_agent_mcp_smoke.py"


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
    report = tmp_path / "report.html"
    report.write_text(
        report.read_text(encoding="utf-8") + "\n<section><h2>Robot View Timeline</h2></section>",
        encoding="utf-8",
    )
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
    report = tmp_path / "report.html"
    report.write_text(
        report.read_text(encoding="utf-8") + "\n<section><h2>Robot View Timeline</h2></section>",
        encoding="utf-8",
    )
    result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
    result["artifacts"]["robot_views"] = str(robot_views)
    result["robot_view_steps"] = [
        _robot_step("navigate_to_object observed_001"),
        _robot_step("pick observed_001"),
        _robot_step("navigate_to_receptacle refrigerator_01"),
        _robot_step("open_receptacle refrigerator_01"),
        _robot_step("place_inside observed_001"),
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
    report = tmp_path / "report.html"
    report.write_text(
        report.read_text(encoding="utf-8") + "\n<section><h2>Robot View Timeline</h2></section>",
        encoding="utf-8",
    )
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


def _write_strict_planner_proof(base: Path) -> Path:
    base.mkdir(parents=True)
    views = base / "planner_views"
    views.mkdir()
    (views / "initial_wrist_camera.png").write_bytes(b"initial")
    (views / "final_wrist_camera.png").write_bytes(b"final")
    evidence = planner_backed_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="franka",
        task="pick_and_place",
        probe_mode="execute",
        upstream_policy_class="PickAndPlacePlannerPolicy",
        steps_requested=2,
        steps_executed=2,
        max_abs_qpos_delta=0.01,
        image_artifacts={
            "initial": "planner_views/initial_wrist_camera.png",
            "final": "planner_views/final_wrist_camera.png",
        },
    )
    evidence["runtime_diagnostics"] = {"renderer_adapter_enabled": True}
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
