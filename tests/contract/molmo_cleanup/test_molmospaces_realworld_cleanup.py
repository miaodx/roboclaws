from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from roboclaws.molmo_cleanup.agibot_map_bundle import write_agibot_nav2_map_bundle
from roboclaws.molmo_cleanup.isaac_lab_backend import ISAACLAB_ROBOT_VIEW_VARIANT
from roboclaws.molmo_cleanup.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_NAME,
    RAW_FPV_ONLY_MODE,
    REALWORLD_CONTRACT,
)
from roboclaws.molmo_cleanup.semantic_timeline import (
    CANONICAL_BASE_CLEANUP_PHASES,
    CLOSE_RECEPTACLE_PHASE,
    PLACE_CLEANUP_PHASES,
    SEMANTIC_LOOP_VARIANT,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_PATH = REPO_ROOT / "examples" / "molmo_cleanup" / "molmospaces_realworld_cleanup.py"
CHECKER_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "check_molmo_realworld_cleanup_result.py"
AGIBOT_SEMANTIC_ACTIONS_PATH = (
    REPO_ROOT / "scripts" / "molmo_cleanup" / "run_agibot_robot_map_9_semantic_actions.py"
)
PREBUILT_BUNDLE = REPO_ROOT / "assets" / "maps" / "molmo-cleanup-default-7"
ROBOT_MAP_9_ARTIFACT = REPO_ROOT / "vendors" / "agibot_sdk" / "artifacts" / "maps" / "robot_map_9"
ROBOT_MAP_9_CONTEXT = REPO_ROOT / "tests" / "fixtures" / "agibot_robot_map_9_context.completed.json"


def _load_demo_module():
    spec = importlib.util.spec_from_file_location("molmospaces_realworld_cleanup", DEMO_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_checker_module():
    spec = importlib.util.spec_from_file_location(
        "check_molmo_realworld_cleanup_result",
        CHECKER_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_agibot_semantic_actions_module():
    spec = importlib.util.spec_from_file_location(
        "run_agibot_robot_map_9_semantic_actions",
        AGIBOT_SEMANTIC_ACTIONS_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_realworld_cleanup_demo_writes_public_private_artifacts(tmp_path: Path) -> None:
    demo = _load_demo_module()

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        map_bundle_dir=PREBUILT_BUNDLE,
        require_map_bundle=True,
    )

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    trace_lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    report_text = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert result["cleanup_status"] == "success"
    assert result["contract"] == REALWORLD_CONTRACT
    assert result["adr_0003_satisfied"] is True
    assert run_result["policy"] == "deterministic_sweep_baseline"
    assert run_result["policy_uses_private_truth"] is False
    assert run_result["planner_uses_private_manifest"] is False
    assert run_result["fixture_hint_mode"] == "room_only"
    assert run_result["requested_generated_mess_count"] == 10
    assert run_result["generated_mess_count"] == 5
    assert run_result["mess_restoration_rate"] >= 0.70
    assert run_result["sweep_coverage_rate"] >= 0.90
    assert run_result["disturbance_count"] <= 2
    assert run_result["semantic_loop_variant"] == SEMANTIC_LOOP_VARIANT
    for item in run_result["semantic_substeps"]:
        phases = [step["phase"] for step in item["steps"]]
        assert phases[:3] == list(CANONICAL_BASE_CLEANUP_PHASES)
        assert phases[-1] in {*PLACE_CLEANUP_PHASES, CLOSE_RECEPTACLE_PHASE}
    assert run_result["agent_view"]["observed_objects"]
    assert "generated_mess_set" not in run_result["agent_view"]
    assert "acceptable_destination_sets" not in run_result["agent_view"]
    assert "planner_object_id" not in json.dumps(run_result["agent_view"])
    assert run_result["private_evaluation"]["generated_mess_set"]
    assert run_result["private_evaluation"]["requested_generated_mess_count"] == 10
    assert run_result["planner_proof_requests"]["schema"] == "planner_cleanup_proof_requests_v1"
    assert run_result["planner_proof_requests"]["agent_view_exposed"] is False
    assert run_result["artifacts"]["planner_proof_requests"].endswith("planner_proof_requests.json")
    assert run_result["nav2_map_bundle"]["snapshot_complete"] is True
    assert run_result["nav2_map_bundle"]["source_bundle_root"] == str(PREBUILT_BUNDLE)
    assert run_result["agent_view"]["metric_map"]["map_bundle"]["environment_id"] == (
        "molmo-cleanup-default-7"
    )
    assert run_result["artifacts"]["nav2_map_yaml"].endswith("map_bundle/map.yaml")
    assert run_result["real_robot_readiness"]["map_bundle_snapshot_present"] is True
    assert "Planner Proof Requests" in report_text
    assert "Nav2 Map Bundle" in report_text
    assert "map_bundle/map.yaml" in report_text
    assert run_result["advisory_evaluation"]["authoritative"] is False
    assert run_result["advisory_evaluation"]["object_reviews"]
    assert (tmp_path / "agent_view.json").is_file()
    assert (tmp_path / "private_evaluation.json").is_file()
    assert (tmp_path / "advisory_evaluation.json").is_file()
    assert (tmp_path / "planner_proof_requests.json").is_file()
    assert (tmp_path / "map_bundle" / "map.yaml").is_file()
    assert (tmp_path / "map_bundle" / "map.pgm").is_file()
    assert (tmp_path / "map_bundle" / "semantics.json").is_file()
    assert (tmp_path / "map_bundle" / "profiles" / "rby1m.yaml").is_file()
    assert (tmp_path / "map_bundle" / "costmaps" / "rby1m.costmap_params.yaml").is_file()
    assert (tmp_path / "map_bundle" / "preview.png").is_file()
    assert (tmp_path / "before.png").is_file()
    assert (tmp_path / "after.png").is_file()
    assert (tmp_path / "report.html").is_file()
    assert any('"tool": "metric_map"' in line for line in trace_lines)
    assert any('"tool": "observe"' in line for line in trace_lines)
    assert not any('"tool": "scene_objects"' in line for line in trace_lines)


def test_realworld_cleanup_demo_navigates_on_agibot_robot_map_9_mock(
    tmp_path: Path,
) -> None:
    demo = _load_demo_module()
    bundle_dir = tmp_path / "agibot-robot-map-9-bundle"
    write_agibot_nav2_map_bundle(
        source_map_dir=ROBOT_MAP_9_ARTIFACT,
        context_json=ROBOT_MAP_9_CONTEXT,
        bundle_dir=bundle_dir,
    )

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path / "run",
        seed=7,
        map_bundle_dir=bundle_dir,
        require_map_bundle=True,
        generated_mess_count=5,
    )

    run_dir = tmp_path / "run"
    run_result = json.loads((run_dir / "run_result.json").read_text(encoding="utf-8"))
    trace_lines = (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    report_text = (run_dir / "report.html").read_text(encoding="utf-8")

    assert result["cleanup_status"] == "success"
    assert run_result["agent_view"]["metric_map"]["map_bundle"]["environment_id"] == (
        "agibot-robot-map-9"
    )
    assert run_result["nav2_map_bundle"]["source_bundle_root"] == str(bundle_dir)
    assert run_result["nav2_map_bundle"]["source_provenance"] == "agibot_gdk_map_artifact"
    assert run_result["real_robot_readiness"]["map_bundle_snapshot_present"] is True
    assert (run_dir / "map_bundle" / "map.pgm").stat().st_size > 600_000
    assert (run_dir / "map_bundle" / "report_static_navigation_map.png").is_file()
    assert "agibot-robot-map-9" in report_text
    assert "Nav2 Map Bundle" in report_text
    assert any('"tool": "navigate_to_waypoint"' in line for line in trace_lines)
    assert any('"route_validation"' in line and '"ok": true' in line for line in trace_lines)


def test_agibot_robot_map_9_semantic_actions_rehearsal(tmp_path: Path) -> None:
    rehearsal = _load_agibot_semantic_actions_module()

    result = rehearsal.run_agibot_robot_map_9_semantic_actions(
        run_dir=tmp_path / "run",
        context_json=ROBOT_MAP_9_CONTEXT,
        agibot_map_artifact_dir=ROBOT_MAP_9_ARTIFACT,
    )

    run_dir = tmp_path / "run"
    run_result = json.loads((run_dir / "run_result.json").read_text(encoding="utf-8"))
    report_text = (run_dir / "report.html").read_text(encoding="utf-8")
    layer = run_result["agibot_robot_map_9_semantic_actions"]

    assert result["confidence_layer"] == "Agibot Robot Map 9 Semantic Actions Rehearsal"
    assert run_result["report_title"] == "Agibot Robot Map 9 Semantic Actions Rehearsal"
    assert run_result["backend"] == "api_semantic_synthetic"
    assert run_result["primitive_provenance"] == "api_semantic"
    assert run_result["semantic_substeps"]
    assert layer["semantic_substep_count"] == len(run_result["semantic_substeps"])
    assert layer["agibot_map_artifact_dir"] == str(ROBOT_MAP_9_ARTIFACT)
    assert layer["map_source_provenance"] == "agibot_gdk_map_artifact"
    assert layer["physical_robot"] is False
    assert layer["sdk_runner_execution"] is False
    assert layer["gdk_navigation_executed"] is False
    assert layer["molmospaces_contract_rehearsal"] is False
    assert run_result["next_confidence_layer"] == "MolmoSpaces Agibot Contract Rehearsal"
    assert "agibot_gdk_normal_navi" not in json.dumps(run_result)
    assert "Agibot Robot Map 9 Semantic Actions Rehearsal" in report_text
    assert "Next confidence layer: MolmoSpaces Agibot Contract Rehearsal" in report_text
    assert "Semantic Substeps" in report_text
    assert "No semantic cleanup actions recorded" not in report_text
    assert run_result["nav2_map_bundle"]["source_provenance"] == "agibot_gdk_map_artifact"


def test_realworld_cleanup_live_bundle_gate_requires_selected_bundle(tmp_path: Path) -> None:
    demo = _load_demo_module()

    try:
        demo.run_realworld_cleanup(output_dir=tmp_path, seed=7, require_map_bundle=True)
    except ValueError as exc:
        assert "map_bundle_dir is required" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("expected require_map_bundle to fail without a selected bundle")


def test_realworld_cleanup_live_bundle_gate_rejects_invalid_bundle(tmp_path: Path) -> None:
    demo = _load_demo_module()
    invalid_bundle = tmp_path / "invalid-bundle"
    invalid_bundle.mkdir()

    try:
        demo.run_realworld_cleanup(
            output_dir=tmp_path / "run",
            seed=7,
            map_bundle_dir=invalid_bundle,
            require_map_bundle=True,
        )
    except ValueError as exc:
        assert "invalid Nav2 map bundle" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("expected invalid selected bundle to fail before cleanup")


def test_realworld_cleanup_report_separates_agent_view_and_private_eval(
    tmp_path: Path,
) -> None:
    demo = _load_demo_module()

    demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    report = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Agent View" in report
    assert "Private Evaluation" in report
    assert "Advisory Review" in report
    assert "Generated mess" in report
    assert "ADR-0003 real-world-style cleanup run" in report


def test_realworld_cleanup_demo_can_run_raw_fpv_evidence_mode(tmp_path: Path) -> None:
    demo = _load_demo_module()

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode=RAW_FPV_ONLY_MODE,
    )
    report = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert result["perception_mode"] == RAW_FPV_ONLY_MODE
    assert result["cleanup_status"] == "success"
    assert result["agent_view"]["observed_objects"]
    assert result["agent_view"]["raw_fpv_observations"]
    assert result["model_declared_observations"]
    evidence = result["model_declared_observation_evidence"]
    assert evidence["observation_count"] >= 7
    assert evidence["resolved_count"] >= result["generated_mess_count"]
    assert any(
        item.get("actionability_status") == "already_handled"
        for item in result["model_declared_observations"]
    )
    assert result["raw_fpv_observations"]
    assert "Raw FPV Observations" in report
    assert "Model-Declared Observations" in report


def test_realworld_cleanup_demo_can_run_camera_model_policy_mode(tmp_path: Path) -> None:
    demo = _load_demo_module()

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )
    report = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert result["perception_mode"] == CAMERA_MODEL_POLICY_MODE
    assert result["policy"] == CAMERA_MODEL_POLICY_NAME
    assert result["cleanup_status"] == "success"
    assert result["agent_view"]["observed_objects"]
    assert result["raw_fpv_observations"]
    assert result["camera_model_policy_evidence"]["enabled"] is True
    assert result["camera_model_policy_evidence"]["candidate_count"] >= 1
    assert result["tool_event_counts"]["declare_visual_candidates:request"] >= 1
    assert "Camera Model Policy" in report
    assert "Model-Declared Observations" in report
    assert "Raw FPV Observations" in report
    assert "Semantic Substeps" in report


def test_realworld_cleanup_demo_can_run_isaaclab_fake_backend(
    tmp_path: Path,
    monkeypatch,
) -> None:
    demo = _load_demo_module()
    checker = _load_checker_module()
    monkeypatch.setenv("ROBOCLAWS_ISAACLAB_PYTHON", sys.executable)
    monkeypatch.setenv("ROBOCLAWS_ISAACLAB_RUNTIME_MODE", "fake")

    result = demo.run_realworld_cleanup(
        output_dir=tmp_path,
        seed=7,
        backend="isaaclab_subprocess",
        include_robot=True,
        record_robot_views=True,
        generated_mess_count=1,
        cleanup_profile="world-labels",
        map_bundle_dir=Path("assets/maps/molmospaces-procthor-val-0-7"),
        require_map_bundle=True,
    )

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    report_text = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert result["backend"] == "isaaclab_subprocess"
    assert result["generated_mess_count"] == 1
    assert result["primitive_provenance"] == "isaac_semantic_pose"
    assert result["manipulation_evidence"]["isaac_semantic_pose_edits"] is True
    assert result["manipulation_evidence"]["planner_backed"] is False
    assert result["agent_view"]["observed_objects"]
    assert result["semantic_substeps"]
    assert result["score"]["semantic_acceptability"]["accepted_count"] >= 1
    assert run_result["isaac_runtime"]["runtime"]["runtime_mode"] == "fake"
    assert run_result["isaac_runtime"]["segmentation"]["status"] == "blocked_capability"
    assert run_result["cleanup_profile_metadata"]["backend"] == "isaaclab_subprocess"
    assert run_result["cleanup_profile_metadata"]["world_backend"] == "isaac_sim"
    assert run_result["view_variant"] == ISAACLAB_ROBOT_VIEW_VARIANT
    assert run_result["robot_view_steps"]
    assert "Isaac Runtime Diagnostics" in report_text
    assert "isaac_semantic_pose" in report_text

    checker._assert_result(
        run_result,
        tmp_path,
        expect_task=None,
        expect_backend="isaaclab_subprocess",
        expect_policy="deterministic_sweep_baseline",
        expect_profile="world-labels",
        min_generated_mess_count=1,
        require_robot_views=True,
        require_advisory_scoring=True,
        min_semantic_accepted_count=1,
        min_sweep_coverage=1.0,
        require_waypoint_honesty=True,
        require_real_robot_alignment=True,
    )
