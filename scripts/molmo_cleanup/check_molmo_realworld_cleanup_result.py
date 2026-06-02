#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from roboclaws.maps.route import SIM_COSTMAP_PLANNER
from roboclaws.household.backend import API_SEMANTIC_PROVENANCE
from roboclaws.household.cleanup_primitive_evidence import (
    validate_cleanup_primitive_evidence,
)
from roboclaws.household.isaac_lab_backend import (
    ISAAC_SCENE_INDEX_ARTIFACT_SCHEMA,
    ISAAC_SEMANTIC_POSE_EVENT_SCHEMA,
    ISAAC_SEMANTIC_POSE_PROVENANCE,
    ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
    ISAAC_SEMANTIC_POSE_STATE_SOURCE,
    ISAACLAB_ROBOT_VIEW_VARIANT,
    ISAACLAB_SUBPROCESS_BACKEND,
)
from roboclaws.household.planner_cleanup_bridge import (
    validate_planner_cleanup_bridge_evidence,
)
from roboclaws.household.planner_proof_attachment import (
    validate_planner_proof_attachment,
)
from roboclaws.household.planner_proof_bundle import (
    PLANNER_PROOF_BUNDLE_SCHEMA,
    planner_proof_attachments,
    validate_planner_proof_bundle,
)
from roboclaws.household.planner_proof_quality import (
    planner_proof_quality_evidence,
    validate_planner_proof_quality_evidence,
)
from roboclaws.household.planner_proof_requests import PLANNER_PROOF_REQUESTS_SCHEMA
from roboclaws.household.profiles import (
    WORLD_LABELS_PROFILE,
    cleanup_profile,
    validate_cleanup_profile_metadata,
)
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_NAME,
    CAMERA_MODEL_POLICY_SCHEMA,
    CLEANUP_POLICY_TRACE_SCHEMA,
    CLEANUP_WORKLIST_SCHEMA,
    MAIN_CLEANUP_AGENT_PRODUCER,
    MODEL_DECLARED_OBSERVATION_SOURCE,
    MODEL_DECLARED_OBSERVATIONS_SCHEMA,
    REAL_ROBOT_MAP_BUNDLE_SCHEMA,
    REAL_ROBOT_READINESS_SCHEMA,
    REALWORLD_CONTRACT,
    RUNTIME_METRIC_MAP_SCHEMA,
    SIMULATED_CAMERA_MODEL_PROVENANCE,
    forbidden_agent_view_keys,
)
from roboclaws.household.realworld_mcp_atomic_tools import ATOMIC_CLEANUP_TOOL_NAMES
from roboclaws.household.report_visual_core import assert_cleanup_report_visual_core
from roboclaws.household.semantic_timeline import (
    CANONICAL_INSIDE_CLEANUP_PHASES,
    CANONICAL_SURFACE_CLEANUP_PHASES,
    CLOSE_RECEPTACLE_PHASE,
    FOCUSED_SEMANTIC_ACTION_PREFIXES,
    OPEN_RECEPTACLE_PHASE,
    PLACE_INSIDE_PHASE,
    SEMANTIC_LOOP_VARIANT,
    SEMANTIC_RESPONSE_PHASES,
    annotate_focus_visual_grounding,
    duplicate_post_place_navigations,
    has_complete_semantic_sequence,
    successful_semantic_phases,
)
from roboclaws.household.visual_grounding import EXTERNAL_VISUAL_GROUNDING_PROVENANCE

ISAAC_PUBLIC_SCENE_BINDING_SCHEMA = "isaac_public_scene_bindings_v1"
AGIBOT_SEMANTIC_MAP_BUILD_SCHEMA = "agibot_semantic_map_build_mcp_v1"
AGIBOT_SEMANTIC_MAP_BUILD_MCP_SERVER = "agibot_semantic_map_build"
AGIBOT_SEMANTIC_MAP_BUILD_POLICY = "codex_agibot_semantic_map_build_pilot"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate ADR-0003 real-world-style Molmo cleanup artifacts."
    )
    parser.add_argument("path", type=Path, help="run_result.json or a directory of seed-* runs")
    parser.add_argument("--expect-task")
    parser.add_argument("--expect-backend")
    parser.add_argument("--expect-policy")
    parser.add_argument("--expect-profile")
    parser.add_argument("--expect-mcp-server")
    parser.add_argument("--expect-seeds")
    parser.add_argument("--min-generated-mess-count", type=int, default=1)
    parser.add_argument("--require-agent-driven", action="store_true")
    parser.add_argument("--require-clean-agent-run", action="store_true")
    parser.add_argument(
        "--allow-partial-cleanup",
        action="store_true",
        help="Validate contract/report evidence without requiring cleanup success.",
    )
    parser.add_argument("--require-openclaw-minimum", action="store_true")
    parser.add_argument("--require-robot-views", action="store_true")
    parser.add_argument("--require-advisory-scoring", action="store_true")
    parser.add_argument("--require-raw-fpv-observations", action="store_true")
    parser.add_argument("--require-camera-model-policy", action="store_true")
    parser.add_argument("--require-runtime-metric-map", action="store_true")
    parser.add_argument("--require-semantic-sweep", action="store_true")
    parser.add_argument("--require-agibot-g2-hardware", action="store_true")
    parser.add_argument("--require-minimal-map", action="store_true")
    parser.add_argument("--expect-visual-grounding-pipeline")
    parser.add_argument("--require-visual-grounding-failure", action="store_true")
    parser.add_argument("--require-model-declared-observations", action="store_true")
    parser.add_argument("--min-model-declared-observations", type=int, default=1)
    parser.add_argument("--min-model-declared-actions", type=int, default=0)
    parser.add_argument("--min-restored-count", type=int, default=None)
    parser.add_argument("--min-semantic-accepted-count", type=int, default=None)
    parser.add_argument("--min-sweep-coverage", type=float, default=None)
    parser.add_argument("--require-planner-proof-attachment", action="store_true")
    parser.add_argument("--require-planner-proof-quality", action="store_true")
    parser.add_argument(
        "--require-planner-proof-min-steps",
        type=int,
        default=None,
        help="Require every attached planner proof to execute at least this many steps.",
    )
    parser.add_argument("--accept-blocked-planner-cleanup-primitives", action="store_true")
    parser.add_argument("--require-planner-backed-cleanup-primitives", action="store_true")
    parser.add_argument(
        "--require-bound-planner-cleanup-object",
        action="append",
        default=[],
        metavar="OBJECT_ID:TARGET_RECEPTACLE_ID",
        help=(
            "Require one cleanup object/target pair to have all cleanup subphases "
            "strictly planner_backed. Repeat for multiple bound objects."
        ),
    )
    parser.add_argument(
        "--require-mixed-planner-cleanup-primitives",
        action="store_true",
        help=(
            "Require a partial rerun state: at least one bound planner-backed "
            "object and at least one unmatched api_semantic object, with the "
            "global primitive gate still blocked."
        ),
    )
    parser.add_argument("--accept-blocked-planner-cleanup-bridge", action="store_true")
    parser.add_argument("--require-planner-cleanup-bridge-ready", action="store_true")
    parser.add_argument("--require-waypoint-honesty", action="store_true")
    parser.add_argument("--require-real-robot-alignment", action="store_true")
    parser.add_argument("--require-isaac-runtime", action="store_true")
    parser.add_argument("--require-isaac-real-runtime", action="store_true")
    parser.add_argument("--require-isaac-scene-loaded", action="store_true")
    parser.add_argument("--require-isaac-local-scene-usd", action="store_true")
    parser.add_argument("--require-isaac-selected-usd-bindings", action="store_true")
    parser.add_argument("--require-isaac-semantic-pose", action="store_true")
    parser.add_argument("--require-isaac-robot-view-provenance", action="store_true")
    parser.add_argument("--require-isaac-segmentation-evidence", action="store_true")
    parser.add_argument("--require-isaac-snapshot-provenance", action="store_true")
    parser.add_argument(
        "--require-isaac-scene-index-map-context",
        action="store_true",
        help=(
            "Require Isaac scene-index cleanup runs to expose map/waypoint context "
            "generated from the loaded scene instead of a stale prebuilt map bundle."
        ),
    )
    parser.add_argument(
        "--require-canonical-robot-view-camera-control",
        action="store_true",
        help=(
            "Legacy alias for --require-robot-head-camera-fpv. Canonical free-camera "
            "control is no longer accepted as agent-facing FPV proof."
        ),
    )
    parser.add_argument(
        "--require-robot-head-camera-fpv",
        action="store_true",
        help=(
            "Require every cleanup agent-facing FPV view to come from a robot-mounted "
            "head camera or an explicit backend head-camera-equivalent contract."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_results = _load_run_results(args.path)
    if args.expect_seeds:
        expected = {int(item) for item in args.expect_seeds.split(",") if item}
        actual = {int(data["seed"]) for data, _path in run_results}
        assert expected <= actual, (expected, actual)
    assert len(run_results) >= 1, args.path
    expect_policy = args.expect_policy
    if expect_policy is None:
        expect_policy = (
            "semantic_sweep_baseline"
            if args.require_semantic_sweep
            else "openclaw_agent"
            if args.require_openclaw_minimum
            else CAMERA_MODEL_POLICY_NAME
            if args.require_camera_model_policy
            else "deterministic_sweep_baseline"
        )
    for data, path in run_results:
        _assert_result(
            data,
            path.parent,
            expect_task=args.expect_task,
            expect_backend=args.expect_backend,
            expect_policy=expect_policy,
            expect_profile=args.expect_profile,
            expect_mcp_server=args.expect_mcp_server,
            min_generated_mess_count=args.min_generated_mess_count,
            require_agent_driven=args.require_agent_driven,
            require_clean_agent_run=args.require_clean_agent_run,
            allow_partial_cleanup=args.allow_partial_cleanup,
            require_openclaw_minimum=args.require_openclaw_minimum,
            require_robot_views=args.require_robot_views,
            require_advisory_scoring=args.require_advisory_scoring,
            require_raw_fpv_observations=args.require_raw_fpv_observations,
            require_camera_model_policy=args.require_camera_model_policy,
            require_runtime_metric_map=args.require_runtime_metric_map,
            require_semantic_sweep=args.require_semantic_sweep,
            require_agibot_g2_hardware=args.require_agibot_g2_hardware,
            require_minimal_map=args.require_minimal_map,
            expect_visual_grounding_pipeline=args.expect_visual_grounding_pipeline,
            require_visual_grounding_failure=args.require_visual_grounding_failure,
            require_model_declared_observations=args.require_model_declared_observations,
            min_model_declared_observations=args.min_model_declared_observations,
            min_model_declared_actions=args.min_model_declared_actions,
            min_restored_count=args.min_restored_count,
            min_semantic_accepted_count=args.min_semantic_accepted_count,
            min_sweep_coverage=args.min_sweep_coverage,
            require_planner_proof_attachment=args.require_planner_proof_attachment,
            require_planner_proof_quality=args.require_planner_proof_quality,
            require_planner_proof_min_steps=args.require_planner_proof_min_steps,
            accept_blocked_planner_cleanup_primitives=(
                args.accept_blocked_planner_cleanup_primitives
            ),
            require_planner_backed_cleanup_primitives=(
                args.require_planner_backed_cleanup_primitives
            ),
            require_bound_planner_cleanup_objects=args.require_bound_planner_cleanup_object,
            require_mixed_planner_cleanup_primitives=(
                args.require_mixed_planner_cleanup_primitives
            ),
            accept_blocked_planner_cleanup_bridge=(args.accept_blocked_planner_cleanup_bridge),
            require_planner_cleanup_bridge_ready=(args.require_planner_cleanup_bridge_ready),
            require_waypoint_honesty=args.require_waypoint_honesty,
            require_real_robot_alignment=args.require_real_robot_alignment,
            require_isaac_runtime=args.require_isaac_runtime,
            require_isaac_real_runtime=args.require_isaac_real_runtime,
            require_isaac_scene_loaded=args.require_isaac_scene_loaded,
            require_isaac_local_scene_usd=args.require_isaac_local_scene_usd,
            require_isaac_selected_usd_bindings=args.require_isaac_selected_usd_bindings,
            require_isaac_semantic_pose=args.require_isaac_semantic_pose,
            require_isaac_robot_view_provenance=args.require_isaac_robot_view_provenance,
            require_isaac_segmentation_evidence=args.require_isaac_segmentation_evidence,
            require_isaac_snapshot_provenance=args.require_isaac_snapshot_provenance,
            require_isaac_scene_index_map_context=(args.require_isaac_scene_index_map_context),
            require_canonical_robot_view_camera_control=(
                args.require_canonical_robot_view_camera_control
                or args.require_robot_head_camera_fpv
            ),
        )
    print(f"molmo-realworld-cleanup ok: {args.path} ({len(run_results)} run(s))")


def _load_run_results(path: Path) -> list[tuple[dict[str, Any], Path]]:
    if path.is_file():
        return [(json.loads(path.read_text(encoding="utf-8")), path)]
    results = []
    for child in sorted(path.glob("seed-*/run_result.json")):
        results.append((json.loads(child.read_text(encoding="utf-8")), child))
    if not results and (path / "run_result.json").is_file():
        child = path / "run_result.json"
        results.append((json.loads(child.read_text(encoding="utf-8")), child))
    return results


def _assert_result(
    data: dict[str, Any],
    base: Path,
    *,
    expect_task: str | None,
    expect_backend: str | None,
    expect_policy: str | None = "deterministic_sweep_baseline",
    expect_profile: str | None = None,
    expect_mcp_server: str | None = None,
    min_generated_mess_count: int = 1,
    require_agent_driven: bool = False,
    require_clean_agent_run: bool = False,
    allow_partial_cleanup: bool = False,
    require_openclaw_minimum: bool = False,
    require_robot_views: bool = False,
    require_advisory_scoring: bool = False,
    require_raw_fpv_observations: bool = False,
    require_camera_model_policy: bool = False,
    require_runtime_metric_map: bool = False,
    require_semantic_sweep: bool = False,
    require_agibot_g2_hardware: bool = False,
    require_minimal_map: bool = False,
    expect_visual_grounding_pipeline: str | None = None,
    require_visual_grounding_failure: bool = False,
    require_model_declared_observations: bool = False,
    min_model_declared_observations: int = 1,
    min_model_declared_actions: int = 0,
    min_restored_count: int | None = None,
    min_semantic_accepted_count: int | None = None,
    min_sweep_coverage: float | None = None,
    require_planner_proof_attachment: bool = False,
    require_planner_proof_quality: bool = False,
    require_planner_proof_min_steps: int | None = None,
    accept_blocked_planner_cleanup_primitives: bool = False,
    require_planner_backed_cleanup_primitives: bool = False,
    require_bound_planner_cleanup_objects: list[str] | None = None,
    require_mixed_planner_cleanup_primitives: bool = False,
    accept_blocked_planner_cleanup_bridge: bool = False,
    require_planner_cleanup_bridge_ready: bool = False,
    require_waypoint_honesty: bool = False,
    require_real_robot_alignment: bool = False,
    require_isaac_runtime: bool = False,
    require_isaac_real_runtime: bool = False,
    require_isaac_scene_loaded: bool = False,
    require_isaac_local_scene_usd: bool = False,
    require_isaac_selected_usd_bindings: bool = False,
    require_isaac_semantic_pose: bool = False,
    require_isaac_robot_view_provenance: bool = False,
    require_isaac_segmentation_evidence: bool = False,
    require_isaac_snapshot_provenance: bool = False,
    require_isaac_scene_index_map_context: bool = False,
    require_canonical_robot_view_camera_control: bool = False,
) -> None:
    assert data.get("contract") == REALWORLD_CONTRACT, data
    if data.get("schema") == AGIBOT_SEMANTIC_MAP_BUILD_SCHEMA:
        _assert_agibot_semantic_map_build_result(
            data,
            base,
            expect_backend=expect_backend,
            expect_policy=expect_policy,
            expect_profile=expect_profile,
            expect_mcp_server=expect_mcp_server,
            require_agent_driven=require_agent_driven,
            require_camera_model_policy=require_camera_model_policy,
            require_runtime_metric_map=require_runtime_metric_map,
            require_semantic_sweep=require_semantic_sweep,
            require_agibot_g2_hardware=require_agibot_g2_hardware,
            expect_visual_grounding_pipeline=expect_visual_grounding_pipeline,
            require_visual_grounding_failure=require_visual_grounding_failure,
            min_sweep_coverage=min_sweep_coverage,
        )
        return
    assert data.get("adr_0003_satisfied") is True, data
    if require_semantic_sweep and expect_policy == "deterministic_sweep_baseline":
        expect_policy = "semantic_sweep_baseline"
    if expect_policy is not None:
        assert data.get("policy") == expect_policy, data
    assert data.get("semantic_loop_variant") == SEMANTIC_LOOP_VARIANT, data
    assert data.get("policy_uses_private_truth") is False, data
    assert data.get("planner_uses_private_manifest") is False, data
    assert data.get("fixture_hint_mode") == "room_only", data
    assert data.get("generated_mess_count", 0) >= min_generated_mess_count, data
    raw_contract_only = (
        require_raw_fpv_observations
        and not require_model_declared_observations
        and not require_clean_agent_run
    )
    enforce_success = (
        (require_clean_agent_run or not require_openclaw_minimum)
        and not raw_contract_only
        and not allow_partial_cleanup
        and not require_semantic_sweep
    )
    semantic_success_gate = min_semantic_accepted_count is not None
    if enforce_success:
        assert data.get("sweep_coverage_rate", 0) >= 0.90, data
        assert data.get("disturbance_count", 999) <= 2, data
        if semantic_success_gate:
            _assert_semantic_acceptability(data, min_semantic_accepted_count)
        else:
            assert data.get("mess_restoration_rate", 0) >= 0.70, data
            assert data.get("cleanup_status") == "success", data
    if min_restored_count is not None:
        assert int((data.get("score") or {}).get("restored_count") or 0) >= min_restored_count, data
    if min_semantic_accepted_count is not None:
        _assert_semantic_acceptability(data, min_semantic_accepted_count)
    if min_sweep_coverage is not None:
        assert float(data.get("sweep_coverage_rate") or 0.0) >= min_sweep_coverage, data
    if expect_task is not None:
        assert data.get("task_prompt") == expect_task, data
    if expect_backend is not None:
        assert data.get("backend") == expect_backend, data
    if expect_mcp_server is not None:
        assert data.get("mcp_server") == expect_mcp_server, data
    if require_agent_driven:
        assert data.get("agent_driven") is True, data

    agent_view = data.get("agent_view") or {}
    _assert_public_agent_view(agent_view)
    if require_minimal_map:
        _assert_minimal_map(data, agent_view)
    if require_runtime_metric_map:
        _assert_runtime_metric_map(
            data.get("runtime_metric_map") or agent_view.get("runtime_metric_map") or {},
            agent_view=agent_view,
        )
    runtime_metric_map = (
        data.get("runtime_metric_map") or agent_view.get("runtime_metric_map") or {}
    )
    semantic_sweep = (
        data.get("semantic_sweep_mode") is True
        or runtime_metric_map.get("mode") == "semantic_sweep"
    )
    if require_semantic_sweep:
        assert semantic_sweep, data
        assert data.get("cleanup_actions_disabled") is True, data
        assert data.get("policy") == "semantic_sweep_baseline", data
        assert (data.get("semantic_sweep") or {}).get("snapshot_artifact"), data
        assert len((data.get("semantic_sweep") or {}).get("camera_schedule") or []) >= 1, data
    if semantic_sweep:
        _assert_semantic_sweep_did_not_clean(data)
    trace_path = _resolve_path(base, data["artifacts"]["trace"])
    _assert_trace_is_public(trace_path)
    _assert_no_duplicate_post_place_navigation(trace_path)
    private = data.get("private_evaluation") or {}
    assert private.get("generated_mess_count") == data.get("generated_mess_count"), data
    assert private.get("generated_mess_count", 0) >= min_generated_mess_count, data
    assert private.get("acceptable_destination_sets"), data
    if enforce_success and not semantic_success_gate:
        for item in data.get("semantic_substeps") or []:
            phases = successful_semantic_phases(item.get("steps", []))
            assert has_complete_semantic_sequence(phases), (phases, item)
    elif enforce_success and semantic_success_gate:
        assert _complete_semantic_substep_count(data) >= min_semantic_accepted_count, data

    artifacts = data.get("artifacts") or {}
    for key in (
        "agent_view",
        "private_evaluation",
        "trace",
        "before_snapshot",
        "after_snapshot",
        "report",
    ):
        path = _resolve_path(base, artifacts.get(key, ""))
        assert path.is_file(), path
        assert path.stat().st_size > 0, path
    if require_runtime_metric_map:
        path = _resolve_path(base, artifacts.get("runtime_metric_map", ""))
        assert path.is_file(), path
        assert path.stat().st_size > 0, path
    report_text = _resolve_path(base, artifacts["report"]).read_text(encoding="utf-8")
    if expect_profile is not None:
        _assert_cleanup_profile(data, report_text, expect_profile)
    assert "Agent View" in report_text, report_text[:500]
    assert "Private Evaluation" in report_text, report_text[:500]
    assert "Score" in report_text, report_text[:500]
    if enforce_success or data.get("semantic_substeps"):
        assert "Semantic Substeps" in report_text, report_text[:500]
    assert "ADR-0003 real-world-style cleanup run" in report_text, report_text[:500]
    if require_runtime_metric_map:
        assert "Runtime Metric Map" in report_text, report_text[:500]
    if require_semantic_sweep:
        assert "Semantic Sweep Mode" in report_text, report_text[:500]
    assert_cleanup_report_visual_core(
        report_text,
        require_semantic_subphases=enforce_success or bool(data.get("semantic_substeps")),
        require_robot_timeline=require_robot_views,
        require_agent_view=True,
        require_private_evaluation=True,
        require_planner_proof_requests=_has_planner_proof_requests(data),
    )
    _assert_planner_proof_requests(data, base, report_text)
    if require_openclaw_minimum:
        _assert_openclaw_minimum(data)
    if require_clean_agent_run and not allow_partial_cleanup:
        _assert_clean_agent_run(data, min_complete_count=min_semantic_accepted_count)
    if require_robot_views:
        _assert_robot_views(data, base, require_complete_actions=enforce_success)
    if require_canonical_robot_view_camera_control:
        _assert_robot_head_camera_fpv(data, base)
    if require_advisory_scoring:
        _assert_advisory_scoring(data, base, report_text)
    if require_raw_fpv_observations:
        _assert_raw_fpv_observations(data, base, report_text)
    if require_camera_model_policy:
        _assert_camera_model_policy(
            data,
            base,
            report_text,
            expect_pipeline_id=expect_visual_grounding_pipeline,
            require_failure=require_visual_grounding_failure,
        )
    if require_model_declared_observations:
        _assert_model_declared_observations(
            data,
            report_text,
            min_observations=min_model_declared_observations,
            min_actions=min_model_declared_actions,
        )
    if (
        require_planner_proof_attachment
        or require_planner_proof_quality
        or require_planner_proof_min_steps is not None
    ):
        _assert_planner_proof_attachment(
            data,
            base,
            report_text,
            require_quality=require_planner_proof_quality,
            min_steps_executed=require_planner_proof_min_steps,
        )
    if accept_blocked_planner_cleanup_primitives or require_planner_backed_cleanup_primitives:
        _assert_cleanup_primitive_gate(
            data,
            report_text,
            accept_blocked=accept_blocked_planner_cleanup_primitives,
            require_planner_backed=require_planner_backed_cleanup_primitives,
        )
    if require_bound_planner_cleanup_objects:
        _assert_bound_planner_cleanup_objects(
            data,
            report_text,
            require_bound_planner_cleanup_objects,
        )
    if require_mixed_planner_cleanup_primitives:
        _assert_mixed_planner_cleanup_primitives(data, report_text)
    if accept_blocked_planner_cleanup_bridge or require_planner_cleanup_bridge_ready:
        _assert_planner_cleanup_bridge(
            data,
            report_text,
            accept_blocked=accept_blocked_planner_cleanup_bridge,
            require_ready=require_planner_cleanup_bridge_ready,
        )
    if require_waypoint_honesty:
        _assert_waypoint_honesty(data, report_text)
    if require_real_robot_alignment:
        _assert_real_robot_alignment(data, base, report_text)
    if (
        require_isaac_runtime
        or require_isaac_real_runtime
        or require_isaac_scene_loaded
        or require_isaac_local_scene_usd
        or require_isaac_selected_usd_bindings
        or require_isaac_semantic_pose
        or require_isaac_robot_view_provenance
        or require_isaac_segmentation_evidence
        or require_isaac_snapshot_provenance
        or require_isaac_scene_index_map_context
    ):
        _assert_isaac_runtime(
            data,
            base,
            report_text,
            require_real_runtime=require_isaac_real_runtime,
            require_scene_loaded=require_isaac_scene_loaded,
            require_local_scene_usd=require_isaac_local_scene_usd,
            require_selected_usd_bindings=require_isaac_selected_usd_bindings,
            require_semantic_pose=require_isaac_semantic_pose,
            require_robot_view_provenance=require_isaac_robot_view_provenance,
            require_segmentation_evidence=require_isaac_segmentation_evidence,
            require_snapshot_provenance=require_isaac_snapshot_provenance,
            require_scene_index_map_context=require_isaac_scene_index_map_context,
        )


def _assert_agibot_semantic_map_build_result(
    data: dict[str, Any],
    base: Path,
    *,
    expect_backend: str | None,
    expect_policy: str | None,
    expect_profile: str | None,
    expect_mcp_server: str | None,
    require_agent_driven: bool,
    require_camera_model_policy: bool,
    require_runtime_metric_map: bool,
    require_semantic_sweep: bool,
    require_agibot_g2_hardware: bool,
    expect_visual_grounding_pipeline: str | None,
    require_visual_grounding_failure: bool,
    min_sweep_coverage: float | None,
) -> None:
    assert require_semantic_sweep, data
    assert data.get("schema") == AGIBOT_SEMANTIC_MAP_BUILD_SCHEMA, data
    assert data.get("cleanup_profile") == "real_robot_cleanup_v1", data
    assert data.get("backend_variant") == "agibot_gdk", data
    if require_semantic_sweep and expect_policy in {
        "deterministic_sweep_baseline",
        "semantic_sweep_baseline",
    }:
        expect_policy = AGIBOT_SEMANTIC_MAP_BUILD_POLICY
    if expect_backend is not None:
        assert (
            data.get("backend_variant") == expect_backend or data.get("backend") == expect_backend
        ), data
    if expect_policy is not None:
        assert data.get("policy") == expect_policy, data
    if expect_mcp_server is not None:
        assert data.get("mcp_server") == expect_mcp_server, data
    else:
        assert data.get("mcp_server") == AGIBOT_SEMANTIC_MAP_BUILD_MCP_SERVER, data
    if require_agent_driven:
        assert data.get("agent_driven") is True, data

    agent_view = data.get("agent_view") or {}
    _assert_agibot_semantic_map_build_agent_view(agent_view)

    if require_runtime_metric_map:
        _assert_agibot_semantic_map_build_runtime_map(
            data.get("runtime_metric_map") or agent_view.get("runtime_metric_map") or {}
        )
    if min_sweep_coverage is not None:
        assert float(data.get("sweep_coverage_rate") or 0.0) >= min_sweep_coverage, data

    readiness = data.get("real_robot_readiness") or {}
    assert readiness.get("schema") == REAL_ROBOT_READINESS_SCHEMA, readiness
    assert readiness.get("backend_variant") == "agibot_gdk", readiness
    assert readiness.get("semantic_map_build") is True, readiness
    assert readiness.get("physical_navigation_pilot") is True, readiness
    assert readiness.get("physical_cleanup_ready") is False, readiness
    assert readiness.get("manipulation_blocked") is True, readiness
    if require_agibot_g2_hardware:
        _assert_agibot_g2_hardware_semantic_map_build(data, base, readiness)

    manipulation = data.get("manipulation_evidence") or {}
    assert manipulation.get("status") == "blocked_capability", manipulation
    assert manipulation.get("primitive_provenance") == "blocked_capability", manipulation

    trace = data.get("cleanup_policy_trace") or {}
    assert trace.get("schema") == CLEANUP_POLICY_TRACE_SCHEMA, trace
    assert trace.get("agent_reasoning_visible") is True, trace
    assert trace.get("cleanup_action_count") == 0, trace
    decisions = {str(item.get("decision") or "") for item in trace.get("events") or []}
    assert {"inspect_public_metric_map", "inspect_public_fixture_hints"} <= decisions, trace
    assert "observe_head_color" in decisions, trace

    private = data.get("private_evaluation") or {}
    assert private.get("generated_mess_count") == 0, private
    assert private.get("acceptable_destination_sets") == {}, private

    artifacts = data.get("artifacts") or {}
    for key in ("trace", "before_snapshot", "after_snapshot", "report"):
        path = _resolve_path(base, artifacts.get(key, ""))
        assert path.is_file(), path
        assert path.stat().st_size > 0, path
    if require_runtime_metric_map:
        path = _resolve_path(base, artifacts.get("runtime_metric_map", ""))
        assert path.is_file(), path
        assert path.stat().st_size > 0, path
    trace_path = _resolve_path(base, artifacts["trace"])
    _assert_trace_is_public(trace_path)
    _assert_no_duplicate_post_place_navigation(trace_path)

    report_text = _resolve_path(base, artifacts["report"]).read_text(encoding="utf-8")
    if expect_profile is not None:
        assert expect_profile in report_text, report_text[:500]
    assert "AgiBot Backend Evidence" in report_text, report_text[:500]
    assert "Real-Robot Readiness" in report_text, report_text[:500]
    assert "Agent View" in report_text, report_text[:500]
    assert "Private Evaluation" in report_text, report_text[:500]
    assert "Score" in report_text, report_text[:500]
    if require_runtime_metric_map:
        assert "Runtime Metric Map" in report_text, report_text[:500]
    if require_camera_model_policy:
        _assert_agibot_semantic_map_build_camera_model_policy(
            data,
            report_text,
            expect_pipeline_id=expect_visual_grounding_pipeline,
            require_failure=require_visual_grounding_failure,
        )


def _assert_agibot_semantic_map_build_agent_view(agent_view: dict[str, Any]) -> None:
    assert agent_view.get("forbidden_private_fields_absent") is True, agent_view
    assert "metric_map" in agent_view, agent_view
    assert "fixture_hints" in agent_view, agent_view
    assert agent_view.get("observed_objects") == [], agent_view
    policy_view = agent_view.get("policy_view") or {}
    assert policy_view.get("policy_observation_camera") == "head_color", policy_view
    raw = agent_view.get("raw_fpv_observations") or []
    assert raw, agent_view
    for item in raw:
        assert item.get("camera") == "head_color", item
        assert item.get("source") == "agibot_g2_policy_camera", item
        assert item.get("primitive_provenance") in {
            "blocked_capability",
            "agibot_gdk_head_color",
            "agibot_gdk_head_color_camera",
        }, item
    _assert_no_forbidden_keys(agent_view)


def _assert_agibot_semantic_map_build_runtime_map(runtime_metric_map: dict[str, Any]) -> None:
    assert runtime_metric_map.get("schema") == RUNTIME_METRIC_MAP_SCHEMA, runtime_metric_map
    assert runtime_metric_map.get("source") == "agibot_semantic_map_build_mcp", runtime_metric_map
    assert "metric_map" in runtime_metric_map, runtime_metric_map
    assert "fixture_hints" in runtime_metric_map, runtime_metric_map
    assert isinstance(runtime_metric_map.get("observed_objects") or [], list), runtime_metric_map
    assert isinstance(runtime_metric_map.get("visited_waypoint_ids") or [], list), (
        runtime_metric_map
    )
    assert isinstance(runtime_metric_map.get("observed_waypoint_ids") or [], list), (
        runtime_metric_map
    )
    _assert_no_forbidden_keys(runtime_metric_map)


def _assert_agibot_semantic_map_build_camera_model_policy(
    data: dict[str, Any],
    report_text: str,
    *,
    expect_pipeline_id: str | None,
    require_failure: bool,
) -> None:
    assert data.get("perception_mode") == CAMERA_MODEL_POLICY_MODE, data
    evidence = data.get("camera_model_policy_evidence") or (
        (data.get("agent_view") or {}).get("camera_model_policy_evidence") or {}
    )
    assert evidence.get("schema") == CAMERA_MODEL_POLICY_SCHEMA, evidence
    assert evidence.get("enabled") is True, evidence
    assert evidence.get("model_provenance") == EXTERNAL_VISUAL_GROUNDING_PROVENANCE, evidence
    assert evidence.get("private_truth_included") is False, evidence
    pipeline_id = str(evidence.get("visual_grounding_pipeline_id") or "")
    pipeline_ids = [str(item) for item in evidence.get("visual_grounding_pipeline_ids") or []]
    if expect_pipeline_id is not None:
        assert expect_pipeline_id in pipeline_ids, evidence
    assert pipeline_id in pipeline_ids, evidence
    assert int(evidence.get("event_count") or 0) >= 1, evidence
    failure_count = int(evidence.get("visual_grounding_failure_count") or 0)
    if require_failure:
        assert failure_count >= 1, evidence
    events = evidence.get("events") or []
    assert events, evidence
    for event in events:
        pipeline = event.get("visual_grounding_pipeline") or {}
        assert pipeline.get("schema") == "visual_grounding_pipeline_v1", event
        assert pipeline.get("pipeline_id") in pipeline_ids, event
        if require_failure:
            assert event.get("candidate_count") == 0, event
            assert pipeline.get("status") == "failed", event
            assert pipeline.get("failure_reason"), event
            stages = pipeline.get("stages") or []
            stage_names = {str(stage.get("stage") or "") for stage in stages}
            assert "agibot_head_color_capture" in stage_names, event
            assert "external_visual_grounding_not_invoked" in stage_names, event
        else:
            assert pipeline.get("status") in {"ok", "failed"}, event
    assert data.get("raw_fpv_observations"), data
    assert "Camera Model Policy" in report_text, report_text[:500]
    assert "Raw FPV Observations" in report_text, report_text[:500]
    assert pipeline_id in report_text, report_text[:500]
    assert "Bearer " not in json.dumps(data), data
    assert "Bearer " not in report_text, report_text[:500]


def _assert_agibot_g2_hardware_semantic_map_build(
    data: dict[str, Any],
    base: Path,
    readiness: dict[str, Any],
) -> None:
    assert data.get("agent_driven") is True, data
    assert data.get("mcp_server") == AGIBOT_SEMANTIC_MAP_BUILD_MCP_SERVER, data
    assert data.get("policy") == AGIBOT_SEMANTIC_MAP_BUILD_POLICY, data
    assert data.get("evidence_lane") == "camera-labels", data
    assert data.get("perception_mode") == CAMERA_MODEL_POLICY_MODE, data
    runtime_metric_map = data.get("runtime_metric_map") or (data.get("agent_view") or {}).get(
        "runtime_metric_map"
    )
    assert isinstance(runtime_metric_map, dict), data
    _assert_agibot_semantic_map_build_runtime_map(runtime_metric_map)
    assert readiness.get("status") == "physical_agibot_semantic_map_build_complete", readiness
    assert readiness.get("movement_enabled") is True, readiness
    assert readiness.get("navigation_perception_ready") is True, readiness
    assert readiness.get("human_takeover_stop") is False, readiness
    assert int(readiness.get("inspection_waypoint_attempt_count") or 0) >= 1, readiness
    assert int(readiness.get("inspection_waypoint_total") or 0) >= 1, readiness
    assert int(readiness.get("reached_waypoint_count") or 0) >= 1, readiness
    assert float(readiness.get("observed_waypoint_rate") or 0.0) >= 1.0, readiness
    assert data.get("cleanup_status") == "physical_agibot_semantic_map_build_complete", data
    assert data.get("primitive_provenance") == "agibot_gdk_normal_navi", data
    assert float(data.get("sweep_coverage_rate") or 0.0) >= 1.0, data

    raw = data.get("raw_fpv_observations") or []
    assert raw, data
    live_head_color = [
        item
        for item in raw
        if item.get("ok") is True
        and item.get("camera") == "head_color"
        and item.get("primitive_provenance") == "agibot_gdk_head_color_camera"
        and (item.get("image_artifacts") or {}).get("fpv")
    ]
    assert live_head_color, raw
    for item in live_head_color:
        path = _resolve_path(base, str((item.get("image_artifacts") or {}).get("fpv") or ""))
        assert path.is_file(), item
        assert path.stat().st_size > 0, item

    camera_policy = data.get("camera_model_policy_evidence") or {}
    assert camera_policy.get("enabled") is True, camera_policy
    assert camera_policy.get("model_provenance") == EXTERNAL_VISUAL_GROUNDING_PROVENANCE, (
        camera_policy
    )
    pipeline_id = str(camera_policy.get("visual_grounding_pipeline_id") or "")
    pipeline_ids = [
        str(item)
        for item in (camera_policy.get("visual_grounding_pipeline_ids") or [pipeline_id])
        if str(item)
    ]
    assert pipeline_ids, camera_policy
    assert pipeline_id in pipeline_ids, camera_policy
    assert not {"sim", "manual"}.intersection(pipeline_ids), camera_policy
    assert int(camera_policy.get("event_count") or 0) >= 1, camera_policy
    assert int(camera_policy.get("candidate_count") or 0) >= 1, camera_policy
    assert int(camera_policy.get("visual_grounding_failure_count") or 0) == 0, camera_policy
    for event in camera_policy.get("events") or []:
        pipeline = event.get("visual_grounding_pipeline") or {}
        assert pipeline.get("schema") == "visual_grounding_pipeline_v1", event
        assert str(pipeline.get("pipeline_id") or "") in pipeline_ids, event
        assert str(pipeline.get("pipeline_id") or "") not in {"sim", "manual"}, event
        assert pipeline.get("status") == "ok", event
        assert int(pipeline.get("candidate_count") or 0) >= 1, event
        stages = pipeline.get("stages") or []
        assert stages, event
        assert all(str(stage.get("status") or "ok") != "blocked" for stage in stages), event

    trace = data.get("cleanup_policy_trace") or {}
    decisions = {str(item.get("decision") or "") for item in trace.get("events") or []}
    assert "visit_public_waypoint" in decisions, trace
    assert "observe_head_color" in decisions, trace
    manipulation = data.get("manipulation_evidence") or {}
    assert manipulation.get("status") == "blocked_capability", manipulation


def _assert_openclaw_minimum(data: dict[str, Any]) -> None:
    assert data.get("policy") == "openclaw_agent", data
    assert data.get("agent_driven") is True, data
    assert data.get("mcp_server") == "molmo_cleanup_realworld", data
    artifacts = data.get("artifacts") or {}
    assert artifacts.get("trace"), data
    assert artifacts.get("report"), data
    counts = data.get("tool_event_counts") or {}
    public_requests = 0
    for tool in (
        "metric_map",
        "fixture_hints",
        "navigate_to_waypoint",
        "observe",
        *SEMANTIC_RESPONSE_PHASES,
        "done",
    ):
        public_requests += int(counts.get(f"{tool}:request") or 0)
    assert public_requests >= 1, (public_requests, counts, data)
    assert int(counts.get("scene_objects:request") or 0) == 0, (counts, data)


def _assert_cleanup_profile(
    data: dict[str, Any],
    report_text: str,
    expected_profile: str,
) -> None:
    profile = cleanup_profile(expected_profile)
    assert data.get("cleanup_profile") == profile.profile, data
    metadata = data.get("cleanup_profile_metadata") or {}
    validate_cleanup_profile_metadata(
        metadata,
        expected_profile=profile.profile,
        expected_backend=data.get("backend"),
        expected_perception_mode=data.get("perception_mode"),
    )
    assert profile.profile in report_text, report_text[:500]
    assert profile.agent_input in report_text, report_text[:500]
    if profile.profile == WORLD_LABELS_PROFILE:
        assert "image reasoning" not in report_text.lower(), report_text[:500]
        assert "not model input" in report_text.lower(), report_text[:500]
        assert "map_mode" in report_text, report_text[:500]
        assert "runtime_map_prior" in report_text, report_text[:500]


def _assert_clean_agent_run(
    data: dict[str, Any],
    *,
    min_complete_count: int | None = None,
) -> None:
    assert data.get("agent_driven") is True, data
    assert data.get("mcp_server") == "molmo_cleanup_realworld", data
    counts = data.get("tool_event_counts") or {}
    for tool in (
        "metric_map",
        "fixture_hints",
        "navigate_to_waypoint",
        "observe",
        *CANONICAL_SURFACE_CLEANUP_PHASES,
        "done",
    ):
        request_count = int(counts.get(f"{tool}:request") or 0)
        if tool == "navigate_to_object":
            request_count += int(counts.get("navigate_to_visual_candidate:request") or 0)
        assert request_count >= 1, (tool, counts, data)
    diagnostics = data.get("agent_diagnostics") or {}
    assert diagnostics.get("stale_reference_errors") == 0, data
    assert _unrecovered_semantic_order_error_count(data) == 0, data
    assert int(diagnostics.get("duplicate_post_place_navigation_count") or 0) == 0, data
    assert diagnostics.get("premature_done") is False, data
    assert diagnostics.get("fridge_inside_sequence_ok") is True, data
    required_complete = min_complete_count or int(data.get("generated_mess_count") or 0)
    assert _complete_semantic_substep_count(data) >= required_complete, data


def _unrecovered_semantic_order_error_count(data: dict[str, Any]) -> int:
    diagnostics = data.get("agent_diagnostics") or {}
    if "semantic_order_unrecovered_errors" in diagnostics:
        return int(diagnostics.get("semantic_order_unrecovered_errors") or 0)

    total_errors = int(diagnostics.get("semantic_order_errors") or 0)
    if total_errors == 0:
        return 0

    covered = 0
    unrecovered = 0
    for item in data.get("semantic_substeps") or []:
        steps = item.get("steps", [])
        item_errors = sum(
            1
            for step in steps
            if isinstance(step, dict) and step.get("error_reason") == "semantic_order"
        )
        if item_errors == 0:
            continue
        covered += item_errors
        phases = successful_semantic_phases(steps)
        if not has_complete_semantic_sequence(phases):
            unrecovered += item_errors
    untracked_errors = max(0, total_errors - covered)
    return unrecovered + untracked_errors


def _assert_semantic_acceptability(data: dict[str, Any], min_accepted_count: int) -> None:
    summary = (data.get("score") or {}).get("semantic_acceptability") or {}
    assert summary, data
    assert summary.get("status") == "success", summary
    accepted_count = int(summary.get("accepted_count") or 0)
    assert accepted_count >= min_accepted_count, (accepted_count, min_accepted_count, data)
    accepted_levels = set(summary.get("accepted_levels") or [])
    assert accepted_levels <= {"preferred", "acceptable"}, summary


def _complete_semantic_substep_count(data: dict[str, Any]) -> int:
    complete = 0
    for item in data.get("semantic_substeps") or []:
        phases = successful_semantic_phases(item.get("steps", []))
        if has_complete_semantic_sequence(phases):
            complete += 1
    return complete


def _successful_semantic_phase_set(data: dict[str, Any]) -> set[str]:
    phases: set[str] = set()
    for item in data.get("semantic_substeps") or []:
        phases.update(successful_semantic_phases(item.get("steps", [])))
    return phases


def _assert_public_agent_view(agent_view: dict[str, Any]) -> None:
    assert agent_view.get("contract") == REALWORLD_CONTRACT, agent_view
    assert agent_view.get("forbidden_private_fields_absent") is True, agent_view
    assert "metric_map" in agent_view, agent_view
    assert "fixture_hints" in agent_view, agent_view
    assert "observed_objects" in agent_view, agent_view
    assert "objects" not in agent_view.get("metric_map", {}), agent_view
    if agent_view.get("runtime_metric_map"):
        _assert_runtime_metric_map(agent_view["runtime_metric_map"], agent_view=agent_view)
    worklist = agent_view.get("cleanup_worklist") or {}
    if worklist:
        assert worklist.get("schema") == CLEANUP_WORKLIST_SCHEMA, worklist
        expected_waypoint_source = (
            "generated_exploration_candidate"
            if (agent_view.get("runtime_metric_map") or {}).get("minimal_map_mode") is True
            else "static_map_fixture_coverage"
        )
        assert worklist.get("waypoint_source") == expected_waypoint_source, worklist
    policy_view = agent_view.get("policy_view") or {}
    if policy_view:
        assert policy_view.get("chase_camera_policy_input") is False, policy_view
    _assert_no_forbidden_keys(agent_view)
    if agent_view.get("perception_mode") == "raw_fpv_only":
        assert agent_view.get("structured_detections_available") is False, agent_view
        raw = agent_view.get("raw_fpv_observations") or []
        assert raw, agent_view
        for item in raw:
            assert item.get("perception_mode") == "raw_fpv_only", item
            assert item.get("structured_detections_available") is False, item
            forbidden = {"category", "name", "support_estimate", "target_receptacle_id"}
            assert not forbidden.intersection(item), item
        declared = agent_view.get("model_declared_observations") or []
        observed = agent_view.get("observed_objects") or []
        if declared:
            assert observed, agent_view
            for item in observed:
                assert item.get("perception_source") == MODEL_DECLARED_OBSERVATION_SOURCE, item
                assert item.get("source_observation_id"), item
                assert "target_receptacle_id" not in item, item
        else:
            assert not observed, agent_view
        return
    if agent_view.get("perception_mode") == CAMERA_MODEL_POLICY_MODE:
        assert agent_view.get("structured_detections_available") is False, agent_view
        raw = agent_view.get("raw_fpv_observations") or []
        assert raw, agent_view
        evidence = agent_view.get("camera_model_policy_evidence") or {}
        assert evidence.get("schema") == CAMERA_MODEL_POLICY_SCHEMA, evidence
        assert evidence.get("enabled") is True, evidence
        observed = agent_view.get("observed_objects") or []
        assert observed, agent_view
        allowed_producer_types = {
            SIMULATED_CAMERA_MODEL_PROVENANCE,
            EXTERNAL_VISUAL_GROUNDING_PROVENANCE,
            MAIN_CLEANUP_AGENT_PRODUCER,
        }
        for item in observed:
            assert str(item.get("object_id", "")).startswith("observed_"), item
            assert item.get("perception_source") in {
                CAMERA_MODEL_POLICY_MODE,
                MODEL_DECLARED_OBSERVATION_SOURCE,
            }, item
            assert item.get("producer_type") in allowed_producer_types, item
            assert item.get("model_provenance") in {
                SIMULATED_CAMERA_MODEL_PROVENANCE,
                EXTERNAL_VISUAL_GROUNDING_PROVENANCE,
                MAIN_CLEANUP_AGENT_PRODUCER,
                None,
            }, item
            assert item.get("source_observation_id"), item
            support = item.get("support_estimate") or {}
            if support:
                assert support.get("source") in {
                    CAMERA_MODEL_POLICY_MODE,
                    MODEL_DECLARED_OBSERVATION_SOURCE,
                    "public_semantic_anchor",
                }, item
            else:
                assert item.get("producer_type") in {
                    EXTERNAL_VISUAL_GROUNDING_PROVENANCE,
                    MAIN_CLEANUP_AGENT_PRODUCER,
                }, item
            assert "is_misplaced" not in item, item
            assert "target_receptacle_id" not in item, item
        return
    observed = agent_view.get("observed_objects") or []
    assert observed, agent_view
    for item in observed:
        assert str(item.get("object_id", "")).startswith("observed_"), item
        assert "support_estimate" in item, item
        assert "is_misplaced" not in item, item
        assert "target_receptacle_id" not in item, item


def _assert_runtime_metric_map(
    runtime_metric_map: dict[str, Any],
    *,
    agent_view: dict[str, Any],
) -> None:
    assert runtime_metric_map.get("schema") == RUNTIME_METRIC_MAP_SCHEMA, runtime_metric_map
    assert runtime_metric_map.get("contract") == REALWORLD_CONTRACT, runtime_metric_map
    assert runtime_metric_map.get("source_map_mutated") is False, runtime_metric_map
    assert runtime_metric_map.get("private_truth_included") is False, runtime_metric_map
    static_map = runtime_metric_map.get("static_map") or {}
    assert isinstance(static_map.get("rooms") or [], list), runtime_metric_map
    assert isinstance(static_map.get("fixtures") or [], list), runtime_metric_map
    assert isinstance(static_map.get("inspection_waypoints") or [], list), runtime_metric_map
    assert static_map.get("contains_runtime_observations") is False, static_map
    for fixture in static_map.get("fixtures") or []:
        assert "observed_objects" not in fixture, fixture
        assert "objects" not in fixture, fixture
        assert not str(fixture.get("fixture_id") or "").startswith("observed_"), fixture
    anchors = runtime_metric_map.get("public_semantic_anchors") or []
    assert isinstance(anchors, list), runtime_metric_map
    for anchor in anchors:
        assert str(anchor.get("anchor_id") or ""), anchor
        assert str(anchor.get("anchor_id") or "").startswith("anchor_"), anchor
        assert anchor.get("anchor_type") in {
            "room_area",
            "surface",
            "receptacle",
            "fixture",
            "observation_waypoint",
        }, anchor
        for key in (
            "category",
            "label",
            "waypoint_id",
            "affordances",
            "producer_type",
            "producer_id",
            "confidence",
            "source_observation_id",
            "promotion_status",
        ):
            assert key in anchor, anchor
        assert isinstance(anchor.get("affordances") or [], list), anchor
        assert anchor.get("promotion_status") != "promoted", anchor
        assert not str(anchor.get("anchor_id") or "").startswith("observed_"), anchor
        assert "target_receptacle_id" not in anchor, anchor
        assert "is_misplaced" not in anchor, anchor
    observed = runtime_metric_map.get("observed_objects") or []
    agent_observed = agent_view.get("observed_objects") or []
    current_observed = [item for item in observed if item.get("freshness") != "prior"]
    assert len(current_observed) == len(agent_observed), (runtime_metric_map, agent_view)
    for item in observed:
        assert str(item.get("object_id", "")).startswith("observed_"), item
        for key in (
            "category",
            "room_id",
            "waypoint_id",
            "source_observation_id",
            "image_region",
            "producer_type",
            "producer_id",
            "confidence",
            "freshness",
            "actionability",
            "state",
        ):
            assert key in item, item
        assert item.get("freshness") in {"current_run", "prior"}, item
        if item.get("freshness") == "prior":
            assert item.get("actionability") != "actionable", item
        assert "target_receptacle_id" not in item, item
        assert "is_misplaced" not in item, item
    assert isinstance(runtime_metric_map.get("map_update_candidates") or [], list), (
        runtime_metric_map
    )
    for candidate in runtime_metric_map.get("map_update_candidates") or []:
        assert "target_receptacle_id" not in candidate, candidate
        assert "is_misplaced" not in candidate, candidate
        assert candidate.get("promotion_status") != "promoted", candidate
    _assert_no_forbidden_keys(runtime_metric_map)


def _assert_minimal_map(data: dict[str, Any], agent_view: dict[str, Any]) -> None:
    assert data.get("map_mode") == "minimal", data
    metric_map = agent_view.get("metric_map") or {}
    fixture_hints = agent_view.get("fixture_hints") or {}
    runtime_map = data.get("runtime_metric_map") or agent_view.get("runtime_metric_map") or {}
    static_map = runtime_map.get("static_map") or {}
    assert metric_map.get("mode") == "minimal", metric_map
    assert fixture_hints.get("mode") == "minimal", fixture_hints
    assert runtime_map.get("map_mode") == "minimal", runtime_map
    assert runtime_map.get("minimal_map_mode") is True, runtime_map
    assert metric_map.get("rooms") == [], metric_map
    assert metric_map.get("driveable_ways") == [], metric_map
    assert fixture_hints.get("rooms") == [], fixture_hints
    assert static_map.get("rooms") == [], static_map
    assert static_map.get("fixtures") == [], static_map
    assert static_map.get("driveable_ways") == [], static_map
    waypoints = metric_map.get("inspection_waypoints") or []
    assert waypoints, metric_map
    generated = runtime_map.get("generated_exploration_candidates") or []
    assert len(generated) == len(waypoints), runtime_map
    anchors = runtime_map.get("public_semantic_anchors") or []
    assert anchors, runtime_map
    assert any(item.get("anchor_type") == "observation_waypoint" for item in anchors), anchors
    for waypoint in waypoints:
        assert str(waypoint.get("waypoint_id") or "").startswith("generated_"), waypoint
        assert waypoint.get("waypoint_source") == "generated_exploration_candidate", waypoint
        assert waypoint.get("purpose") == "minimal_map_exploration", waypoint
        provenance = waypoint.get("candidate_provenance") or {}
        assert provenance.get("source") == "public_occupancy_free_space", waypoint
        assert provenance.get("source_room_hidden") is True, waypoint
        assert provenance.get("source_fixtures_hidden") is True, waypoint
        assert provenance.get("source_waypoint_hidden") is True, waypoint
        assert "source_waypoint_id" not in provenance, waypoint
    semantic_sweep = data.get("semantic_sweep")
    if semantic_sweep is not None:
        assert semantic_sweep.get("minimal_map_mode") is True, data
    _assert_no_forbidden_keys(metric_map)
    _assert_no_forbidden_keys(fixture_hints)


def _assert_semantic_sweep_did_not_clean(data: dict[str, Any]) -> None:
    counts = data.get("tool_event_counts") or {}
    cleanup_tools = {
        "navigate_to_object",
        "navigate_to_visual_candidate",
        "pick",
        "navigate_to_receptacle",
        "open_receptacle",
        "place",
        "place_inside",
        "close_receptacle",
    }
    called = {
        tool: int(counts.get(f"{tool}:request") or 0)
        for tool in cleanup_tools
        if int(counts.get(f"{tool}:request") or 0)
    }
    assert not called, (called, data)


def _assert_trace_is_public(trace_path: Path) -> None:
    for payload in _trace_events_from_path(trace_path):
        assert payload.get("tool") != "scene_objects", payload
        if payload.get("tool") == "done":
            continue
        public_payload = _without_internal_proof_evidence(payload)
        _assert_no_forbidden_keys(public_payload)
        response = public_payload.get("response")
        if isinstance(response, dict):
            assert "objects" not in response, response
            assert "scene_objects" not in response, response


def _assert_no_duplicate_post_place_navigation(trace_path: Path) -> None:
    duplicates = duplicate_post_place_navigations(_trace_events_from_path(trace_path))
    assert not duplicates, (trace_path, duplicates)


def _trace_events_from_path(trace_path: Path) -> list[dict[str, Any]]:
    events = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def _without_internal_proof_evidence(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: _without_internal_proof_evidence(value)
            for key, value in payload.items()
            if key != "planner_primitive_evidence"
        }
    if isinstance(payload, list):
        return [_without_internal_proof_evidence(value) for value in payload]
    return payload


def _assert_robot_views(
    data: dict[str, Any],
    base: Path,
    *,
    require_complete_actions: bool = True,
) -> None:
    expected_variants = {"molmospaces-rby1m-fpv-map-chase-verify"}
    if data.get("backend") == ISAACLAB_SUBPROCESS_BACKEND:
        expected_variants.add(ISAACLAB_ROBOT_VIEW_VARIANT)
    assert data.get("view_variant") in expected_variants, data
    artifacts = data.get("artifacts") or {}
    robot_views_dir = _resolve_path(base, artifacts.get("robot_views", ""))
    assert robot_views_dir.is_dir(), robot_views_dir
    report_path = _resolve_path(base, artifacts.get("report", ""))
    report_text = report_path.read_text(encoding="utf-8")
    assert "Robot View Timeline" in report_text, report_text[:500]
    steps = data.get("robot_view_steps") or []
    assert len(steps) >= 2, data
    camera_summary = data.get("robot_view_camera_control")
    if camera_summary is not None:
        assert isinstance(camera_summary, dict), data
        assert camera_summary.get("schema") == "robot_view_camera_control_summary_v1", data
        assert isinstance(camera_summary.get("same_pose_api"), bool), data
    focused_actions: set[str] = set()
    for step in steps:
        views = step.get("views") or {}
        assert int(step.get("room_outline_count") or 0) > 0, step
        for key in ("fpv", "chase", "map", "verify"):
            path = _resolve_path(report_path.parent, views.get(key, ""))
            assert path.is_file(), path
            assert path.stat().st_size > 0, path
        action = str(step.get("action", ""))
        if _is_focused_robot_action(action):
            focused_actions.add(action.split(" ", 1)[0])
            if not action.startswith("observe "):
                _assert_focused_robot_step(step)
    if require_complete_actions:
        assert focused_actions, (focused_actions, data)
        for expected in CANONICAL_SURFACE_CLEANUP_PHASES:
            assert expected in focused_actions, (expected, focused_actions, data)
        if any(
            item.get("target_receptacle_category") == "Fridge"
            for item in data.get("semantic_substeps") or []
        ):
            assert OPEN_RECEPTACLE_PHASE in focused_actions, data
            assert PLACE_INSIDE_PHASE in focused_actions, data
            assert CLOSE_RECEPTACLE_PHASE in focused_actions, data


def _assert_robot_head_camera_fpv(data: dict[str, Any], base: Path) -> None:
    _assert_robot_views(data, base, require_complete_actions=False)
    summary = data.get("robot_view_camera_control") or {}
    assert summary.get("schema") == "robot_view_camera_control_summary_v1", data
    assert summary.get("status") == "all_robot_views_use_head_camera_fpv", summary
    assert summary.get("head_camera_fpv") is True, summary
    steps = data.get("robot_view_steps") or []
    assert steps, data
    assert int(summary.get("contract_count") or 0) == len(steps), summary
    assert int(summary.get("head_camera_contract_count") or 0) == len(steps), summary
    report_path = _resolve_path(base, (data.get("artifacts") or {}).get("report", ""))
    for step in steps:
        contract = step.get("camera_control_contract") or {}
        assert contract.get("schema") == "robot_view_camera_control_contract_v1", step
        assert contract.get("status") in {
            "robot_mounted_head_camera_robot_view",
            "robot_head_camera_equivalent_robot_view",
        }, step
        assert contract.get("camera_control_api") is None, step
        assert contract.get("camera_model") in {
            "robot_mounted_head_camera_v1",
            "robot_head_camera_equivalent_v1",
        }, step
        fpv = contract.get("agent_facing_fpv") or {}
        verify = contract.get("report_verify_view") or {}
        assert fpv.get("canonical_camera_control") is False, step
        assert verify.get("canonical_camera_control") is False, step
        assert fpv.get("source"), step
        assert "head_camera" in str(fpv.get("source")) or fpv.get("head_camera_equivalent"), step
        robot_pose = contract.get("robot_pose") or step.get("robot_pose") or {}
        if robot_pose:
            assert robot_pose.get("schema") == "cleanup_robot_pose_result_v1", step
            pose_request = robot_pose.get("pose_request") or {}
            assert pose_request.get("schema") == "cleanup_robot_pose_request_v1", step
            assert pose_request.get("resolver") == "roboclaws.cleanup_robot_pose.near_target_v1", (
                step
            )
        views = step.get("views") or {}
        _assert_nonblank_image(
            _resolve_path(report_path.parent, str(views.get("fpv") or "")),
            "robot head-camera FPV",
        )
        _assert_nonblank_image(
            _resolve_path(report_path.parent, str(views.get("verify") or "")),
            "robot verify",
        )


def _assert_canonical_robot_view_camera_control(data: dict[str, Any], base: Path) -> None:
    _assert_robot_head_camera_fpv(data, base)


def _assert_isaac_runtime(
    data: dict[str, Any],
    base: Path,
    report_text: str,
    *,
    require_real_runtime: bool,
    require_scene_loaded: bool,
    require_local_scene_usd: bool = False,
    require_selected_usd_bindings: bool,
    require_semantic_pose: bool,
    require_robot_view_provenance: bool,
    require_segmentation_evidence: bool,
    require_snapshot_provenance: bool,
    require_scene_index_map_context: bool = False,
) -> None:
    assert data.get("backend") == ISAACLAB_SUBPROCESS_BACKEND, data
    isaac = data.get("isaac_runtime") or {}
    assert isaac, data
    assert "Isaac Runtime Diagnostics" in report_text, report_text[:500]

    runtime = isaac.get("runtime") or {}
    rendering = runtime.get("rendering") or {}
    scene_load = isaac.get("scene_load") or {}
    scene_bindings = isaac.get("scene_binding_diagnostics") or {}
    segmentation = isaac.get("segmentation") or {}

    assert runtime.get("primitive_provenance") == ISAAC_SEMANTIC_POSE_PROVENANCE, runtime
    assert segmentation.get("status") in {
        "blocked_capability",
        "available",
        "unavailable",
    }, segmentation
    assert segmentation.get("agent_facing") is not True, segmentation
    assert segmentation.get("no_simulator_label_fallback") is not False, segmentation

    if require_real_runtime:
        assert runtime.get("runtime_mode") == "real", runtime
        _assert_isaac_real_runtime_diagnostics(runtime)
        assert rendering.get("real_rendering_proven") is True, rendering
        assert rendering.get("placeholder_visuals") is not True, rendering
        assert rendering.get("status") == "real_rendering_proven", rendering

    if require_scene_loaded:
        _assert_isaac_scene_loaded(isaac, scene_load, base)

    if require_local_scene_usd:
        _assert_isaac_scene_loaded(isaac, scene_load, base)
        assert scene_load.get("loaded_asset_kind") == "local_scene_usd", scene_load

    scene_index_payload: dict[str, Any] | None = None
    if require_selected_usd_bindings:
        _assert_selected_isaac_usd_bindings(scene_bindings)
        scene_index_payload = _assert_isaac_scene_index_artifact(data, isaac, base)
        _assert_isaac_scene_index_matches_runtime_bindings(
            scene_bindings,
            scene_index_payload.get("scene_binding_diagnostics") or {},
        )
        _assert_isaac_scene_index_report_rows(
            scene_index_payload.get("scene_binding_diagnostics") or scene_bindings,
            report_text,
        )

    if require_semantic_pose:
        assert data.get("primitive_provenance") == ISAAC_SEMANTIC_POSE_PROVENANCE, data
        evidence = data.get("manipulation_evidence") or {}
        assert evidence.get("primitive_provenance") == ISAAC_SEMANTIC_POSE_PROVENANCE, evidence
        assert evidence.get("isaac_semantic_pose_edits") is True, evidence
        assert evidence.get("planner_backed") is False, evidence
        assert evidence.get("physical_robot") is False, evidence
        assert ISAAC_SEMANTIC_POSE_PROVENANCE in report_text, report_text[:500]
        for expected_label in (
            "Semantic Pose State",
            "Semantic Pose Events",
            "Rendered to USD",
            "Planner backed",
        ):
            assert expected_label in report_text, report_text[:1000]
        for item in data.get("semantic_substeps") or []:
            for step in item.get("steps") or []:
                if step.get("phase") in SEMANTIC_RESPONSE_PHASES and step.get("status") == "ok":
                    assert step.get("primitive_provenance") == ISAAC_SEMANTIC_POSE_PROVENANCE, step
                    assert step.get("planner_backed") is not True, step
                    assert step.get("physical_robot") is not True, step
        _assert_isaac_semantic_pose_state(
            isaac,
            scene_bindings=scene_bindings if require_selected_usd_bindings else None,
            scene_index_payload=scene_index_payload,
        )
        _assert_isaac_semantic_pose_report_rows(
            isaac.get("semantic_pose_state") or {},
            report_text,
        )
        _assert_isaac_semantic_pose_trace(data, base, isaac.get("semantic_pose_state") or {})

    if require_robot_view_provenance:
        _assert_robot_views(data, base, require_complete_actions=False)
        assert data.get("view_variant") == ISAACLAB_ROBOT_VIEW_VARIANT, data
        steps = data.get("robot_view_steps") or []
        assert steps, data
        semantic_pose_state = isaac.get("semantic_pose_state") or {}
        require_refreshed_views = semantic_pose_state.get("rendered_to_usd") is True
        for step in steps:
            provenance = step.get("view_provenance") or {}
            provenance_text = json.dumps(provenance, sort_keys=True).lower()
            camera_contract = step.get("camera_control_contract") or {}
            assert camera_contract.get("schema") == "robot_view_camera_control_contract_v1", step
            assert "placeholder" not in provenance_text, step
            assert "isaac_lab_camera_rgb" in provenance_text, step
            if require_refreshed_views:
                assert provenance.get("semantic_pose_state_refreshed") is True, step
                assert "isaac_lab_camera_rgb_semantic_pose_robot_views" in provenance_text, step
                capture = semantic_pose_state.get("semantic_pose_view_capture") or {}
                if capture.get("robot_mounted_head_camera") is True:
                    assert camera_contract.get("same_pose_api") is False, step
                    assert camera_contract.get("camera_control_api") is None, step
                    assert camera_contract.get("status") == (
                        "robot_mounted_head_camera_robot_view"
                    ), step
                    assert camera_contract.get("camera_model") == (
                        "robot_mounted_head_camera_v1"
                    ), step
                    fpv = camera_contract.get("agent_facing_fpv") or {}
                    assert fpv.get("robot_mounted") is True, step
                    assert camera_contract.get("camera_prim_path") == (
                        "/World/robot_0/head_camera"
                    ), step
                elif capture.get("head_camera_equivalent") is True:
                    assert camera_contract.get("same_pose_api") is False, step
                    assert camera_contract.get("camera_control_api") is None, step
                    assert camera_contract.get("status") == (
                        "robot_head_camera_equivalent_robot_view"
                    ), step
                    assert camera_contract.get("camera_model") == (
                        "robot_head_camera_equivalent_v1"
                    ), step
                else:
                    assert camera_contract.get("same_pose_api") is False, step
                    assert camera_contract.get("camera_control_api") is None, step
                    assert camera_contract.get("status") == "backend_local_scene_bounds_camera", (
                        step
                    )
            else:
                assert camera_contract.get("same_pose_api") is False, step
                assert camera_contract.get("camera_control_api") is None, step
                assert camera_contract.get("status") == "backend_local_scene_bounds_camera", step
            views = step.get("views") or {}
            assert isinstance(views, dict), step
            for key in ("fpv", "chase", "map", "verify"):
                _assert_nonblank_image(
                    _resolve_path(base, str(views.get(key) or "")),
                    f"Isaac {key} robot view",
                )

    if require_segmentation_evidence:
        assert segmentation.get("schema") == "isaac_segmentation_diagnostics_v1", segmentation
        assert segmentation.get("status") == "available", segmentation
        assert segmentation.get("available") is True, segmentation
        assert segmentation.get("tensor_output_available") is True, segmentation
        assert segmentation.get("candidate_overlay_status") == "available", segmentation
        assert int(segmentation.get("candidate_bbox_count") or 0) > 0, segmentation
        assert int(segmentation.get("selected_usd_prim_match_count") or 0) > 0, segmentation
        assert segmentation.get("agent_facing") is False, segmentation
        assert segmentation.get("no_simulator_label_fallback") is True, segmentation
        assert "Segmentation" in report_text, report_text[:500]
        if scene_index_payload is not None:
            _assert_isaac_scene_index_matches_runtime_segmentation(
                segmentation,
                scene_index_payload.get("segmentation") or {},
            )

    if require_snapshot_provenance:
        _assert_isaac_snapshot_provenance(isaac, base)

    if require_scene_index_map_context:
        _assert_isaac_scene_index_map_context(data, base)


def _assert_isaac_real_runtime_diagnostics(runtime: dict[str, Any]) -> None:
    assert runtime.get("python_version"), runtime
    assert runtime.get("isaac_sim_version"), runtime
    assert runtime.get("isaac_lab_version"), runtime
    assert runtime.get("cuda_available") is True, runtime
    assert runtime.get("gpu_name"), runtime
    assert int(runtime.get("gpu_vram_mb") or 0) > 0, runtime
    assert runtime.get("renderer_mode"), runtime
    camera_resolution = runtime.get("camera_resolution")
    assert isinstance(camera_resolution, list), runtime
    assert len(camera_resolution) == 2, runtime
    assert all(int(value or 0) > 0 for value in camera_resolution), runtime


def _assert_isaac_scene_index_map_context(data: dict[str, Any], base: Path) -> None:
    isaac = data.get("isaac_runtime") or {}
    scenario_id = str(data.get("scenario_id") or "")
    assert scenario_id.startswith("isaac-scene-index-"), data
    assert isaac.get("scenario_source") == "isaac_scene_index", isaac

    agent_view = data.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    runtime_map = data.get("runtime_metric_map") or agent_view.get("runtime_metric_map") or {}
    static_map = runtime_map.get("static_map") or {}
    nav2_bundle = data.get("nav2_map_bundle") or {}
    fixture_hints = agent_view.get("fixture_hints") or {}
    scene_index_overlay = fixture_hints.get("scene_index_fixture_overlay") or {}

    if scene_index_overlay:
        assert scene_index_overlay.get("enabled") is True, scene_index_overlay
        assert scene_index_overlay.get("source") == "isaac_scene_index", scene_index_overlay
    else:
        assert isaac.get("scenario_source") == "isaac_scene_index", {
            "isaac_runtime": isaac,
            "fixture_hints": fixture_hints,
        }
    _assert_map_bundle_environment(metric_map.get("map_bundle") or {}, scenario_id)
    _assert_map_bundle_environment(static_map.get("map_bundle") or {}, scenario_id)
    _assert_map_bundle_environment(nav2_bundle, scenario_id)
    _assert_isaac_scene_index_room_scale(metric_map)
    _assert_isaac_scene_index_room_scale(static_map)
    assert "source_bundle_root" not in nav2_bundle, nav2_bundle
    assert nav2_bundle.get("source_provenance") == "molmospaces_public_semantic_map", nav2_bundle

    artifact_paths = nav2_bundle.get("artifact_paths") or {}
    semantics_path = _resolve_path(base, str(artifact_paths.get("semantics_json") or ""))
    assert semantics_path.is_file(), nav2_bundle
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    assert semantics.get("environment_id") == scenario_id, semantics
    assert str(semantics.get("map_id") or "").startswith(scenario_id), semantics
    assert "molmospaces-procthor-val-0-7" not in json.dumps(
        {
            "metric_map": metric_map.get("map_bundle"),
            "static_map": static_map.get("map_bundle"),
            "nav2_bundle": nav2_bundle,
            "semantics_environment_id": semantics.get("environment_id"),
            "semantics_map_id": semantics.get("map_id"),
        },
        sort_keys=True,
    )


def _assert_map_bundle_environment(bundle: dict[str, Any], scenario_id: str) -> None:
    assert bundle.get("schema") in {
        "nav2_map_bundle_v1",
        "nav2_map_bundle_snapshot_v1",
    }, bundle
    assert bundle.get("environment_id") == scenario_id, bundle
    assert str(bundle.get("map_id") or "").startswith(scenario_id), bundle


def _assert_isaac_scene_index_room_scale(metric_map: dict[str, Any]) -> None:
    rooms = [room for room in metric_map.get("rooms") or [] if isinstance(room, dict)]
    assert rooms, metric_map
    outlines = [
        room.get("scene_room_outline")
        for room in rooms
        if isinstance(room.get("scene_room_outline"), dict)
    ]
    assert outlines, rooms
    assert any(
        outline.get("provenance") == "isaac_usd_room_mesh_world_bounds" for outline in outlines
    ), outlines
    max_width = max(_polygon_extent(room.get("polygon") or [], "x") for room in rooms)
    max_depth = max(_polygon_extent(room.get("polygon") or [], "y") for room in rooms)
    assert max_width > 2.5 or max_depth > 2.5, rooms


def _polygon_extent(points: list[Any], axis: str) -> float:
    values = [
        float(point.get(axis, 0.0))
        for point in points
        if isinstance(point, dict) and point.get(axis) is not None
    ]
    if not values:
        return 0.0
    return max(values) - min(values)


def _assert_isaac_scene_loaded(
    isaac: dict[str, Any],
    scene_load: dict[str, Any],
    base: Path,
) -> None:
    assert scene_load.get("status") == "loaded", scene_load
    assert scene_load.get("usd_stage_loaded") is True, scene_load
    assert scene_load.get("loaded_asset_kind"), scene_load
    assert scene_load.get("manual_editor_steps_required") is False, scene_load
    scene_usd = str(isaac.get("scene_usd") or scene_load.get("scene_usd") or "")
    assert scene_usd, isaac
    scene_path = Path(scene_usd)
    if scene_path.is_absolute():
        assert scene_path.is_file(), scene_path
    else:
        resolved = _resolve_path(base, scene_usd)
        assert resolved.is_file(), resolved


def _assert_selected_isaac_usd_bindings(scene_bindings: dict[str, Any]) -> None:
    _assert_selected_isaac_usd_bindings_for_indexes(scene_bindings)


def _assert_selected_isaac_usd_bindings_for_indexes(
    scene_bindings: dict[str, Any],
    *,
    object_index: dict[str, Any] | None = None,
    receptacle_index: dict[str, Any] | None = None,
) -> None:
    assert scene_bindings.get("schema") == ISAAC_PUBLIC_SCENE_BINDING_SCHEMA, scene_bindings
    assert scene_bindings.get("status") == "selected_bound", scene_bindings
    assert scene_bindings.get("source") == "usd_stage_traversal", scene_bindings
    assert scene_bindings.get("private_manifest_exposed_to_agent") is False, scene_bindings
    selected_object_count = int(scene_bindings.get("selected_object_count") or 0)
    selected_receptacle_count = int(scene_bindings.get("selected_target_receptacle_count") or 0)
    selected_object_bound_count = int(scene_bindings.get("selected_object_bound_count") or 0)
    selected_receptacle_bound_count = int(
        scene_bindings.get("selected_target_receptacle_bound_count") or 0
    )
    assert selected_object_count > 0, scene_bindings
    assert selected_receptacle_count > 0, scene_bindings
    assert selected_object_bound_count >= selected_object_count, scene_bindings
    assert selected_receptacle_bound_count >= selected_receptacle_count, scene_bindings
    assert not scene_bindings.get("blockers"), scene_bindings
    _assert_bound_isaac_binding_rows(
        scene_bindings.get("selected_object_bindings") or {},
        expected_count=selected_object_count,
        index=object_index,
        index_label="object index",
        label="object",
    )
    _assert_bound_isaac_binding_rows(
        scene_bindings.get("selected_target_receptacle_bindings") or {},
        expected_count=selected_receptacle_count,
        index=receptacle_index,
        index_label="receptacle index",
        label="target receptacle",
    )


def _assert_isaac_scene_index_artifact(
    data: dict[str, Any],
    isaac: dict[str, Any],
    base: Path,
) -> dict[str, Any]:
    artifacts = data.get("artifacts") or {}
    artifact_path = str(
        isaac.get("scene_index_artifact") or artifacts.get("isaac_scene_index") or ""
    )
    assert artifact_path, isaac
    resolved = _resolve_path(base, artifact_path)
    assert resolved.is_file(), resolved
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    assert payload.get("schema") == ISAAC_SCENE_INDEX_ARTIFACT_SCHEMA, payload
    assert payload.get("backend") == ISAACLAB_SUBPROCESS_BACKEND, payload
    assert payload.get("agent_facing") is False, payload
    assert payload.get("private_manifest_exposed_to_agent") is False, payload
    assert "private_manifest" not in payload, payload
    assert payload.get("object_index"), payload
    assert payload.get("receptacle_index"), payload
    assert int(payload.get("object_index_count") or 0) == len(payload["object_index"]), payload
    assert int(payload.get("receptacle_index_count") or 0) == len(payload["receptacle_index"]), (
        payload
    )
    _assert_bound_isaac_index_rows(payload.get("object_index") or {})
    _assert_bound_isaac_index_rows(payload.get("receptacle_index") or {})
    _assert_isaac_scene_index_matches_runtime_indexes(isaac, payload)
    _assert_selected_isaac_usd_bindings_for_indexes(
        payload.get("scene_binding_diagnostics") or {},
        object_index=payload.get("object_index") or {},
        receptacle_index=payload.get("receptacle_index") or {},
    )
    return payload


def _assert_isaac_scene_index_matches_runtime_indexes(
    isaac: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    for index_key, count_key in (
        ("object_index", "object_index_count"),
        ("receptacle_index", "receptacle_index_count"),
    ):
        runtime_index = isaac.get(index_key) or {}
        artifact_index = payload.get(index_key) or {}
        assert runtime_index, (index_key, isaac)
        assert runtime_index == artifact_index, (index_key, runtime_index, artifact_index)
        assert int(isaac.get(count_key) or 0) == len(runtime_index), (count_key, isaac)
        assert int(payload.get(count_key) or 0) == len(artifact_index), (count_key, payload)


def _assert_isaac_scene_index_matches_runtime_bindings(
    runtime_bindings: dict[str, Any],
    artifact_bindings: dict[str, Any],
) -> None:
    for key in (
        "schema",
        "status",
        "source",
        "selected_object_count",
        "selected_target_receptacle_count",
        "selected_object_bound_count",
        "selected_target_receptacle_bound_count",
        "private_manifest_exposed_to_agent",
    ):
        assert artifact_bindings.get(key) == runtime_bindings.get(key), (
            key,
            runtime_bindings,
            artifact_bindings,
        )
    for bindings_key in (
        "selected_object_bindings",
        "selected_target_receptacle_bindings",
    ):
        runtime_rows = runtime_bindings.get(bindings_key) or {}
        artifact_rows = artifact_bindings.get(bindings_key) or {}
        assert runtime_rows.keys() == artifact_rows.keys(), (
            bindings_key,
            runtime_rows,
            artifact_rows,
        )
        for public_id, runtime_row in runtime_rows.items():
            artifact_row = artifact_rows.get(public_id)
            assert isinstance(runtime_row, dict), (bindings_key, public_id, runtime_row)
            assert isinstance(artifact_row, dict), (bindings_key, public_id, artifact_row)
            for row_key in (
                "status",
                "usd_handle",
                "usd_prim_path",
                "match_strategy",
                "index_source",
            ):
                assert artifact_row.get(row_key) == runtime_row.get(row_key), (
                    bindings_key,
                    public_id,
                    row_key,
                    runtime_row,
                    artifact_row,
                )


def _assert_isaac_scene_index_matches_runtime_segmentation(
    runtime_segmentation: dict[str, Any],
    artifact_segmentation: dict[str, Any],
) -> None:
    for key in (
        "schema",
        "status",
        "available",
        "source",
        "capture_method",
        "tensor_output_available",
        "candidate_overlay_status",
        "candidate_bbox_count",
        "selected_usd_prim_match_count",
        "agent_facing",
        "no_simulator_label_fallback",
    ):
        assert artifact_segmentation.get(key) == runtime_segmentation.get(key), (
            key,
            runtime_segmentation,
            artifact_segmentation,
        )
    for key in (
        "requested_data_types",
        "output_data_types",
        "selected_usd_prim_paths",
        "selected_candidate_bboxes",
        "candidate_bboxes",
    ):
        assert artifact_segmentation.get(key) == runtime_segmentation.get(key), (
            key,
            runtime_segmentation,
            artifact_segmentation,
        )


def _assert_isaac_scene_index_report_rows(
    scene_bindings: dict[str, Any],
    report_text: str,
) -> None:
    for expected in (
        "Scene Index Artifact Rows",
        "Selected USD Binding Rows",
        "Selected USD Index Rows",
    ):
        assert expected in report_text, report_text[:1000]
    for bindings_key in (
        "selected_object_bindings",
        "selected_target_receptacle_bindings",
    ):
        bindings = scene_bindings.get(bindings_key) or {}
        assert bindings, scene_bindings
        for binding in bindings.values():
            assert isinstance(binding, dict), binding
            if binding.get("status") != "bound":
                continue
            usd_handle = str(binding.get("usd_handle") or "")
            usd_prim_path = str(binding.get("usd_prim_path") or "")
            assert usd_handle in report_text, (usd_handle, report_text[:1000])
            assert usd_prim_path in report_text, (usd_prim_path, report_text[:1000])


def _assert_bound_isaac_index_rows(index: dict[str, Any]) -> None:
    for handle, row in index.items():
        assert isinstance(row, dict), (handle, row)
        assert row.get("usd_prim_path"), row


def _assert_isaac_snapshot_provenance(isaac: dict[str, Any], base: Path) -> None:
    snapshots = isaac.get("snapshot_artifacts") or []
    assert len(snapshots) >= 2, isaac
    for snapshot in snapshots:
        assert isinstance(snapshot, dict), snapshot
        assert snapshot.get("placeholder_visuals") is False, snapshot
        assert snapshot.get("visual_artifact_provenance") == "isaac_lab_camera_rgb", snapshot
        output_path = _resolve_path(base, snapshot.get("output_path", ""))
        _assert_nonblank_image(output_path, "Isaac snapshot")
        provenance = snapshot.get("snapshot_provenance") or {}
        assert provenance.get("placeholder_visuals") is False, provenance
        assert provenance.get("visual_artifact_provenance") == "isaac_lab_camera_rgb", provenance
        assert provenance.get("static_isaac_capture") is True, provenance
        assert provenance.get("semantic_pose_rendered") is False, provenance
        source_path = _resolve_path(base, provenance.get("source_path", ""))
        _assert_nonblank_image(source_path, "Isaac snapshot source")
        assert "placeholder_protocol_image" not in json.dumps(provenance, sort_keys=True).lower(), (
            provenance
        )


def _assert_nonblank_image(path: Path, label: str) -> None:
    assert path.is_file(), path
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            extrema = rgb.getextrema()
            stat = ImageStat.Stat(rgb)
    except Exception as exc:
        raise AssertionError(f"{label} is not a readable image: {path}") from exc
    assert any(high > low for low, high in extrema), (label, path)
    assert max(stat.stddev or [0.0]) > 0.0, (label, path)


def _assert_isaac_semantic_pose_state(
    isaac: dict[str, Any],
    *,
    scene_bindings: dict[str, Any] | None = None,
    scene_index_payload: dict[str, Any] | None = None,
) -> None:
    state = isaac.get("semantic_pose_state") or {}
    assert state.get("schema") == ISAAC_SEMANTIC_POSE_STATE_SCHEMA, state
    assert state.get("state_source") == ISAAC_SEMANTIC_POSE_STATE_SOURCE, state
    assert state.get("primitive_provenance") == ISAAC_SEMANTIC_POSE_PROVENANCE, state
    rendered_to_usd = state.get("rendered_to_usd")
    assert rendered_to_usd in {False, True}, state
    if rendered_to_usd is True:
        capture = state.get("semantic_pose_view_capture") or {}
        assert isinstance(capture, dict), state
        assert capture.get("schema") == "isaac_semantic_pose_robot_view_capture_v1", capture
        assert capture.get("capture_method") == (
            "isaac_lab_camera_rgb_semantic_pose_robot_views"
        ), capture
        assert capture.get("rendered_to_usd") is True, capture
        assert int(capture.get("render_steps") or 0) > 0, capture
    assert state.get("planner_backed") is False, state
    assert state.get("physical_robot") is False, state
    assert state.get("semantic_pose_only") is True, state
    object_poses = state.get("object_poses") or {}
    assert object_poses, state
    events = state.get("transform_events") or []
    assert events, state
    tools = {str(event.get("tool") or "") for event in events if isinstance(event, dict)}
    assert "pick" in tools, events
    assert tools & {"place", "place_inside"}, events
    event_object_ids = {
        str(event.get("object_id") or "") for event in events if isinstance(event, dict)
    }
    assert any(object_id in object_poses for object_id in event_object_ids), (
        event_object_ids,
        object_poses,
    )
    for event in events:
        assert event.get("schema") == ISAAC_SEMANTIC_POSE_EVENT_SCHEMA, event
        assert event.get("state_source") == ISAAC_SEMANTIC_POSE_STATE_SOURCE, event
        assert event.get("primitive_provenance") == ISAAC_SEMANTIC_POSE_PROVENANCE, event
        assert event.get("rendered_to_usd") is False, event
        assert event.get("planner_backed") is False, event
        assert event.get("physical_robot") is False, event
        assert str(event.get("state_mutation") or "").startswith("isaac_"), event
    for pose in object_poses.values():
        assert pose.get("state_source") == ISAAC_SEMANTIC_POSE_STATE_SOURCE, pose
        assert pose.get("rendered_to_usd") is False, pose
    if scene_bindings is not None and scene_index_payload is not None:
        _assert_isaac_semantic_pose_usd_paths_match_scene_index(
            state,
            scene_bindings=scene_bindings,
            object_index=scene_index_payload.get("object_index") or {},
            receptacle_index=scene_index_payload.get("receptacle_index") or {},
        )


def _assert_isaac_semantic_pose_usd_paths_match_scene_index(
    state: dict[str, Any],
    *,
    scene_bindings: dict[str, Any],
    object_index: dict[str, Any],
    receptacle_index: dict[str, Any],
) -> None:
    object_paths = _index_usd_prim_paths(object_index)
    receptacle_paths = _index_usd_prim_paths(receptacle_index)
    selected_object_paths = _selected_binding_usd_prim_paths(
        scene_bindings,
        "selected_object_bindings",
    )
    selected_receptacle_paths = _selected_binding_usd_prim_paths(
        scene_bindings,
        "selected_target_receptacle_bindings",
    )
    object_poses = state.get("object_poses") or {}
    assert isinstance(object_poses, dict), state
    for object_id, pose in object_poses.items():
        assert isinstance(pose, dict), (object_id, pose)
        _assert_semantic_usd_path_matches_scene_index(
            "semantic object pose",
            public_id=str(object_id),
            usd_prim_path=str(pose.get("usd_prim_path") or ""),
            selected_paths=selected_object_paths,
            index_paths=object_paths,
        )
        support_receptacle_id = str(pose.get("support_receptacle_id") or "")
        if support_receptacle_id:
            _assert_semantic_usd_path_matches_scene_index(
                "semantic object support",
                public_id=support_receptacle_id,
                usd_prim_path=str(pose.get("support_usd_prim_path") or ""),
                selected_paths=selected_receptacle_paths,
                index_paths=receptacle_paths,
            )

    articulations = state.get("articulations") or {}
    assert isinstance(articulations, dict), state
    for receptacle_id, articulation in articulations.items():
        assert isinstance(articulation, dict), (receptacle_id, articulation)
        _assert_semantic_usd_path_matches_scene_index(
            "semantic articulation",
            public_id=str(receptacle_id),
            usd_prim_path=str(articulation.get("usd_prim_path") or ""),
            selected_paths=selected_receptacle_paths,
            index_paths=receptacle_paths,
        )

    events = state.get("transform_events") or []
    assert isinstance(events, list), state
    for event in events:
        assert isinstance(event, dict), event
        object_id = str(event.get("object_id") or "")
        if object_id:
            _assert_semantic_usd_path_matches_scene_index(
                "semantic pose event object",
                public_id=object_id,
                usd_prim_path=str(event.get("object_usd_prim_path") or ""),
                selected_paths=selected_object_paths,
                index_paths=object_paths,
            )
        receptacle_id = str(event.get("receptacle_id") or "")
        if receptacle_id:
            _assert_semantic_usd_path_matches_scene_index(
                "semantic pose event receptacle",
                public_id=receptacle_id,
                usd_prim_path=str(event.get("receptacle_usd_prim_path") or ""),
                selected_paths=selected_receptacle_paths,
                index_paths=receptacle_paths,
            )


def _selected_binding_usd_prim_paths(
    scene_bindings: dict[str, Any],
    bindings_key: str,
) -> dict[str, str]:
    paths: dict[str, str] = {}
    bindings = scene_bindings.get(bindings_key) or {}
    assert isinstance(bindings, dict), scene_bindings
    for public_id, binding in bindings.items():
        assert isinstance(binding, dict), (bindings_key, public_id, binding)
        if binding.get("status") != "bound":
            continue
        paths[str(public_id)] = str(binding.get("usd_prim_path") or "")
    return paths


def _index_usd_prim_paths(index: dict[str, Any]) -> dict[str, str]:
    assert isinstance(index, dict) and index, index
    paths: dict[str, str] = {}
    for handle, row in index.items():
        assert isinstance(row, dict), (handle, row)
        usd_prim_path = str(row.get("usd_prim_path") or "")
        assert usd_prim_path, (handle, row)
        paths[str(handle)] = usd_prim_path
    return paths


def _assert_semantic_usd_path_matches_scene_index(
    label: str,
    *,
    public_id: str,
    usd_prim_path: str,
    selected_paths: dict[str, str],
    index_paths: dict[str, str],
) -> None:
    selected_path = selected_paths.get(public_id)
    if selected_path is not None:
        assert usd_prim_path == selected_path, (label, public_id, usd_prim_path, selected_path)
    indexed_path = index_paths.get(public_id)
    if indexed_path:
        assert usd_prim_path == indexed_path, (label, public_id, usd_prim_path, indexed_path)
        return
    if not usd_prim_path:
        return
    assert usd_prim_path in index_paths.values(), (
        label,
        public_id,
        usd_prim_path,
        index_paths,
    )


def _assert_isaac_semantic_pose_report_rows(
    state: dict[str, Any],
    report_text: str,
) -> None:
    for expected in (
        "Object USD",
        "Support USD",
        "USD prim",
        "Mutation",
        "Receptacle USD",
    ):
        assert expected in report_text, (expected, report_text[:1000])

    object_poses = state.get("object_poses") or {}
    assert isinstance(object_poses, dict), state
    for object_id, pose in object_poses.items():
        assert isinstance(pose, dict), (object_id, pose)
        _assert_report_text_values(
            report_text,
            str(object_id),
            str(pose.get("support_receptacle_id") or ""),
            str(pose.get("usd_prim_path") or ""),
            str(pose.get("support_usd_prim_path") or ""),
        )

    articulations = state.get("articulations") or {}
    assert isinstance(articulations, dict), state
    for receptacle_id, articulation in articulations.items():
        assert isinstance(articulation, dict), (receptacle_id, articulation)
        _assert_report_text_values(
            report_text,
            str(receptacle_id),
            str(articulation.get("usd_prim_path") or ""),
        )

    events = state.get("transform_events") or []
    assert isinstance(events, list), state
    for event in events:
        assert isinstance(event, dict), event
        _assert_report_text_values(
            report_text,
            str(event.get("tool") or ""),
            str(event.get("state_mutation") or ""),
            str(event.get("object_id") or ""),
            str(event.get("receptacle_id") or ""),
            str(event.get("object_usd_prim_path") or ""),
            str(event.get("receptacle_usd_prim_path") or ""),
        )


def _assert_report_text_values(report_text: str, *values: str) -> None:
    for value in values:
        if value:
            assert value in report_text, (value, report_text[:1000])


def _assert_isaac_semantic_pose_trace(
    data: dict[str, Any],
    base: Path,
    state: dict[str, Any],
) -> None:
    artifacts = data.get("artifacts") or {}
    trace_path = _resolve_path(base, artifacts.get("trace", ""))
    assert trace_path.is_file(), (trace_path, data)
    trace_responses = [
        event.get("response")
        for event in _trace_events_from_path(trace_path)
        if event.get("event") == "response" and isinstance(event.get("response"), dict)
    ]
    successful_pose_responses = [
        response
        for response in trace_responses
        if response.get("tool") in _ISAAC_SEMANTIC_POSE_TRACE_TOOLS and response.get("ok") is True
    ]
    assert successful_pose_responses, trace_path
    trace_tools = {str(response.get("tool") or "") for response in successful_pose_responses}
    assert "pick" in trace_tools, (trace_path, trace_tools)
    assert trace_tools & {"place", "place_inside"}, (trace_path, trace_tools)

    state_events = state.get("transform_events") or []
    assert isinstance(state_events, list), state
    state_tools = {
        str(event.get("tool") or "")
        for event in state_events
        if isinstance(event, dict) and event.get("tool") in _ISAAC_SEMANTIC_POSE_TRACE_TOOLS
    }
    assert state_tools <= trace_tools, (state_tools, trace_tools, trace_path)
    for response in successful_pose_responses:
        assert response.get("primitive_provenance") == ISAAC_SEMANTIC_POSE_PROVENANCE, response
        assert str(response.get("state_mutation") or "").startswith("isaac_"), response
        assert response.get("planner_backed") is not True, response
        assert response.get("physical_robot") is not True, response


_ISAAC_SEMANTIC_POSE_TRACE_TOOLS = frozenset(ATOMIC_CLEANUP_TOOL_NAMES)


def _assert_bound_isaac_binding_rows(
    bindings: dict[str, Any],
    *,
    expected_count: int,
    index: dict[str, Any] | None,
    index_label: str,
    label: str,
) -> None:
    assert bindings and len(bindings) >= expected_count, (label, expected_count, bindings)
    for public_id, binding in bindings.items():
        assert isinstance(binding, dict), (label, public_id, binding)
        assert binding.get("status") == "bound", (label, public_id, binding)
        usd_handle = str(binding.get("usd_handle") or "")
        usd_prim_path = str(binding.get("usd_prim_path") or "")
        assert usd_handle, (label, public_id, binding)
        assert usd_prim_path, (label, public_id, binding)
        assert binding.get("index_source") == "usd_stage_traversal", (label, public_id, binding)
        assert binding.get("match_strategy") not in {"", "none"}, (label, public_id, binding)
        assert "private_manifest" not in binding, (label, public_id, binding)
        if index is None:
            continue
        index_row = index.get(usd_handle)
        assert isinstance(index_row, dict), (label, public_id, usd_handle, index_label, index)
        index_prim_path = str(index_row.get("usd_prim_path") or "")
        assert index_prim_path, (label, public_id, usd_handle, index_row)
        assert usd_prim_path == index_prim_path, (
            label,
            public_id,
            usd_prim_path,
            index_label,
            index_prim_path,
        )


def _assert_advisory_scoring(data: dict[str, Any], base: Path, report_text: str) -> None:
    advisory = data.get("advisory_evaluation") or {}
    assert advisory, data
    assert advisory.get("schema_version") == "advisory_cleanup_scoring_v1", advisory
    assert advisory.get("authoritative") is False, advisory
    assert advisory.get("status") == "ok", advisory
    assert advisory.get("object_reviews"), advisory
    counts = advisory.get("counts") or {}
    assert int(counts.get("total_reviewed") or 0) == len(advisory["object_reviews"]), advisory
    artifacts = data.get("artifacts") or {}
    advisory_path = _resolve_path(base, artifacts.get("advisory_evaluation", ""))
    assert advisory_path.is_file(), advisory_path
    loaded = json.loads(advisory_path.read_text(encoding="utf-8"))
    assert loaded.get("authoritative") is False, loaded
    assert "Advisory Review" in report_text, report_text[:500]


def _assert_raw_fpv_observations(
    data: dict[str, Any],
    base: Path,
    report_text: str,
) -> None:
    assert data.get("perception_mode") == "raw_fpv_only", data
    agent_view = data.get("agent_view") or {}
    assert agent_view.get("perception_mode") == "raw_fpv_only", agent_view
    assert agent_view.get("structured_detections_available") is False, agent_view
    observations = data.get("raw_fpv_observations") or agent_view.get("raw_fpv_observations") or []
    assert observations, data
    assert "Raw FPV Observations" in report_text, report_text[:500]
    artifacts = data.get("artifacts") or {}
    robot_views_dir = _resolve_path(base, artifacts.get("robot_views", ""))
    assert robot_views_dir.is_dir(), robot_views_dir
    for item in observations:
        assert item.get("perception_mode") == "raw_fpv_only", item
        assert item.get("structured_detections_available") is False, item
        assert not {"category", "name", "support_estimate", "target_receptacle_id"}.intersection(
            item
        ), item
        camera_contract = item.get("camera_control_contract")
        if camera_contract is not None:
            assert isinstance(camera_contract, dict), item
            assert camera_contract.get("schema") == "robot_view_camera_control_contract_v1", item
            assert isinstance(camera_contract.get("same_pose_api"), bool), item
        image_artifacts = item.get("image_artifacts") or {}
        fpv = image_artifacts.get("fpv") or item.get("fpv_image")
        assert fpv, item
        fpv_path = _resolve_path(base, str(fpv))
        if not fpv_path.exists():
            fpv_path = _resolve_path(robot_views_dir.parent, str(fpv))
        assert fpv_path.is_file(), (fpv_path, item)
        assert fpv_path.stat().st_size > 0, (fpv_path, item)


def _assert_camera_model_policy(
    data: dict[str, Any],
    base: Path,
    report_text: str,
    *,
    expect_pipeline_id: str | None = None,
    require_failure: bool = False,
) -> None:
    assert data.get("perception_mode") == CAMERA_MODEL_POLICY_MODE, data
    evidence = data.get("camera_model_policy_evidence") or (
        (data.get("agent_view") or {}).get("camera_model_policy_evidence") or {}
    )
    assert evidence.get("schema") == CAMERA_MODEL_POLICY_SCHEMA, evidence
    assert evidence.get("enabled") is True, evidence
    pipeline_id = str(evidence.get("visual_grounding_pipeline_id") or "sim")
    pipeline_ids = [
        str(item)
        for item in (evidence.get("visual_grounding_pipeline_ids") or [pipeline_id])
        if item
    ]
    if not pipeline_ids:
        pipeline_ids = [pipeline_id]
    if expect_pipeline_id is not None:
        assert expect_pipeline_id in pipeline_ids, evidence
        overlay_pipeline_id = expect_pipeline_id
    else:
        overlay_pipeline_id = next(
            (item for item in pipeline_ids if item not in {"sim", "manual"}),
            pipeline_id,
        )
    if set(pipeline_ids) == {"sim"}:
        assert evidence.get("model_provenance") == SIMULATED_CAMERA_MODEL_PROVENANCE, evidence
    else:
        assert evidence.get("model_provenance") == "external_visual_grounding_service", evidence
    assert evidence.get("private_truth_included") is False, evidence
    assert int(evidence.get("event_count") or 0) >= 1, evidence
    failure_count = int(evidence.get("visual_grounding_failure_count") or 0)
    if require_failure:
        assert failure_count >= 1, evidence
    else:
        assert int(evidence.get("candidate_count") or 0) >= 1, evidence
    assert evidence.get("events"), evidence
    for event in evidence.get("events") or []:
        pipeline = event.get("visual_grounding_pipeline") or {}
        assert pipeline.get("pipeline_id") in pipeline_ids, event
        assert pipeline.get("schema") == "visual_grounding_pipeline_v1", event
        assert pipeline.get("status") in {"ok", "failed"}, event
        stages = pipeline.get("stages") or []
        assert stages, event
        for stage in stages:
            assert stage.get("stage"), stage
            assert "latency_ms" in stage, stage
    assert data.get("raw_fpv_observations"), data
    counts = data.get("tool_event_counts") or {}
    assert int(counts.get("declare_visual_candidates:request") or 0) >= 1, counts
    assert "Camera Model Policy" in report_text, report_text[:500]
    assert "Raw FPV Observations" in report_text, report_text[:500]
    assert overlay_pipeline_id in report_text, report_text[:500]
    assert "Bearer " not in json.dumps(data), data
    assert "Bearer " not in report_text, report_text[:500]
    if overlay_pipeline_id not in {"sim", "manual"} and not require_failure:
        _assert_external_visual_grounding_overlays(
            data,
            base,
            report_text,
            pipeline_id=overlay_pipeline_id,
        )


def _assert_model_declared_observations(
    data: dict[str, Any],
    report_text: str,
    *,
    min_observations: int,
    min_actions: int,
) -> None:
    evidence = data.get("model_declared_observation_evidence") or (
        (data.get("agent_view") or {}).get("model_declared_observation_evidence") or {}
    )
    observations = data.get("model_declared_observations") or evidence.get("observations") or []
    assert evidence.get("schema") == MODEL_DECLARED_OBSERVATIONS_SCHEMA, evidence
    assert evidence.get("private_truth_included") is False, evidence
    assert len(observations) >= min_observations, (len(observations), min_observations, data)
    assert int(evidence.get("observation_count") or 0) >= min_observations, evidence
    assert int(evidence.get("resolved_count") or 0) >= min_observations, evidence
    assert int(evidence.get("acted_count") or 0) >= min_actions, evidence
    for item in observations:
        assert str(item.get("object_id", "")).startswith("observed_"), item
        assert item.get("source_observation_id"), item
        assert item.get("producer_type"), item
        assert item.get("category"), item
        assert item.get("target_fixture_id") is not None, item
        assert item.get("image_region"), item
        assert item.get("evidence_note") is not None, item
        assert item.get("grounding_status") in {"resolved", "ambiguous", "unresolved"}, item
        assert "grounding_confidence" in item, item
        assert "grounding_basis" in item, item
        assert "target_plausibility" in item, item
        assert item.get("private_truth_included") is False, item
        _assert_no_forbidden_keys(item)
    counts = data.get("tool_event_counts") or {}
    declaration_requests = int(counts.get("declare_visual_candidates:request") or 0) + int(
        counts.get("navigate_to_visual_candidate:request") or 0
    )
    assert declaration_requests >= 1, counts
    assert "Model-Declared Observations" in report_text, report_text[:500]


def _assert_external_visual_grounding_overlays(
    data: dict[str, Any],
    base: Path,
    report_text: str,
    *,
    pipeline_id: str,
) -> None:
    evidence = data.get("model_declared_observation_evidence") or (
        (data.get("agent_view") or {}).get("model_declared_observation_evidence") or {}
    )
    observations = data.get("model_declared_observations") or evidence.get("observations") or []
    assert observations, data
    bbox_candidates_with_source = 0
    for item in observations:
        pipeline = item.get("visual_grounding_pipeline") or {}
        if str(pipeline.get("pipeline_id") or "") != pipeline_id:
            continue
        if item.get("producer_type") != EXTERNAL_VISUAL_GROUNDING_PROVENANCE:
            continue
        image_region = item.get("image_region") or {}
        if image_region.get("type") != "bbox":
            continue
        source_image_path = _raw_fpv_image_path_for_observation(
            data,
            base,
            observation_id=str(item.get("source_observation_id") or ""),
        )
        if source_image_path is None or not source_image_path.is_file():
            continue
        bbox_candidates_with_source += 1
        overlay = str(item.get("visual_grounding_overlay") or "")
        assert overlay, item
        overlay_path = _resolve_path(base, overlay)
        assert overlay_path.is_file(), (overlay_path, item)
        assert overlay_path.stat().st_size > 0, (overlay_path, item)
    if bbox_candidates_with_source:
        assert "Overlay" in report_text, report_text[:500]


def _raw_fpv_image_path_for_observation(
    data: dict[str, Any],
    base: Path,
    *,
    observation_id: str,
) -> Path | None:
    agent_view = data.get("agent_view") or {}
    observations = data.get("raw_fpv_observations") or agent_view.get("raw_fpv_observations") or []
    for item in observations:
        if str(item.get("observation_id") or "") != observation_id:
            continue
        image_artifacts = item.get("image_artifacts") or {}
        fpv = image_artifacts.get("fpv") or item.get("fpv_image")
        if not fpv:
            return None
        return _resolve_path(base, str(fpv))
    return None


def _assert_planner_proof_attachment(
    data: dict[str, Any],
    base: Path,
    report_text: str,
    *,
    require_quality: bool = False,
    min_steps_executed: int | None = None,
) -> None:
    assert data.get("primitive_provenance") in {
        API_SEMANTIC_PROVENANCE,
        "planner_backed",
    }, data
    evidence = data.get("manipulation_evidence") or {}
    assert evidence.get("primitive_provenance") in {
        API_SEMANTIC_PROVENANCE,
        "planner_backed",
    }, evidence
    attachment = data.get("planner_backed_manipulation_proof") or {}
    if attachment.get("schema") == PLANNER_PROOF_BUNDLE_SCHEMA:
        validate_planner_proof_bundle(attachment)
        proof_attachments = planner_proof_attachments(attachment)
        assert "Attached Planner-Backed Proofs" in report_text, report_text[:500]
    else:
        validate_planner_proof_attachment(attachment)
        proof_attachments = [attachment]
        assert "Attached Planner-Backed Proof" in report_text, report_text[:500]
    for proof in proof_attachments:
        quality = planner_proof_quality_evidence(proof)
        validate_planner_proof_quality_evidence(
            quality,
            min_steps_executed=min_steps_executed or 1,
        )
        if require_quality:
            assert "Proof Quality" in report_text, report_text[:500]
            assert str(quality.get("quality_tier") or "") in report_text, report_text[:500]
        for value in (proof.get("image_artifacts") or {}).values():
            path = _resolve_path(base, str(value))
            assert path.is_file(), path
            assert path.stat().st_size > 0, path
    assert "Planner Initial" in report_text, report_text[:500]
    assert "Planner Final" in report_text, report_text[:500]
    if attachment.get("schema") != PLANNER_PROOF_BUNDLE_SCHEMA:
        assert "Cleanup object moves" in report_text, report_text[:500]


def _assert_cleanup_primitive_gate(
    data: dict[str, Any],
    report_text: str,
    *,
    accept_blocked: bool = False,
    require_planner_backed: bool = False,
) -> None:
    evidence = data.get("cleanup_primitive_evidence") or {}
    validate_cleanup_primitive_evidence(
        evidence,
        accept_blocked_capability=accept_blocked,
        require_planner_backed=require_planner_backed,
    )
    assert "Cleanup Primitive Gate" in report_text, report_text[:500]
    assert "Display subphase" in report_text, report_text[:500]
    assert "Subphase role" in report_text, report_text[:500]
    if require_planner_backed:
        assert data.get("primitive_provenance") != API_SEMANTIC_PROVENANCE, data


def _assert_bound_planner_cleanup_objects(
    data: dict[str, Any],
    report_text: str,
    specs: list[str],
) -> None:
    assert data.get("planner_proof_cleanup_executor_enabled") is True, data
    evidence = data.get("cleanup_primitive_evidence") or {}
    assert evidence.get("schema") == "planner_backed_cleanup_primitives_v1", evidence
    objects = evidence.get("objects") or []
    assert objects, evidence
    for spec in specs:
        object_id, target_receptacle_id = _parse_bound_object_spec(spec)
        row = next(
            (
                item
                for item in objects
                if item.get("object_id") == object_id
                and item.get("target_receptacle_id") == target_receptacle_id
            ),
            None,
        )
        assert row is not None, (spec, objects)
        assert row.get("planner_backed") is True, row
        assert row.get("strict_proof_eligible") is True, row
        subphases = row.get("subphases") or []
        assert subphases, row
        required_phases = _required_bound_cleanup_phases(subphases)
        assert required_phases <= {str(step.get("phase") or "") for step in subphases}, row
        for step in subphases:
            assert step.get("primitive_provenance") == "planner_backed", step
            assert step.get("planner_backed") is True, step
            assert step.get("strict_proof_eligible") is True, step
            assert step.get("status") == "ok", step
            assert step.get("object_id_matches") is True, step
            assert step.get("target_receptacle_id_matches") is True, step
        assert object_id in report_text, report_text[:500]
        assert target_receptacle_id in report_text, report_text[:500]
        assert "planner_backed" in report_text, report_text[:500]


def _required_bound_cleanup_phases(subphases: list[dict[str, Any]]) -> set[str]:
    phases = {str(step.get("phase") or "") for step in subphases}
    if OPEN_RECEPTACLE_PHASE in phases or PLACE_INSIDE_PHASE in phases:
        return set(CANONICAL_INSIDE_CLEANUP_PHASES) - {CLOSE_RECEPTACLE_PHASE}
    return set(CANONICAL_SURFACE_CLEANUP_PHASES)


def _assert_mixed_planner_cleanup_primitives(
    data: dict[str, Any],
    report_text: str,
) -> None:
    evidence = data.get("cleanup_primitive_evidence") or {}
    assert evidence.get("status") == "blocked_capability", evidence
    assert evidence.get("planner_backed") is False, evidence
    assert data.get("primitive_provenance") == API_SEMANTIC_PROVENANCE, data
    objects = evidence.get("objects") or []
    assert any(item.get("planner_backed") is True for item in objects), objects
    assert any(item.get("planner_backed") is False for item in objects), objects
    summary = evidence.get("primitive_provenance_summary") or {}
    assert int(summary.get("planner_backed") or 0) >= 1, summary
    assert int(summary.get(API_SEMANTIC_PROVENANCE) or 0) >= 1, summary
    blockers = evidence.get("blockers") or []
    assert any(
        blocker.get("code") == "cleanup_subphase_not_planner_backed" for blocker in blockers
    ), blockers
    assert "Cleanup Primitive Gate" in report_text, report_text[:500]
    assert "blocked_capability" in report_text, report_text[:500]


def _parse_bound_object_spec(spec: str) -> tuple[str, str]:
    object_id, sep, target_receptacle_id = spec.partition(":")
    assert sep and object_id and target_receptacle_id, spec
    return object_id, target_receptacle_id


def _assert_planner_cleanup_bridge(
    data: dict[str, Any],
    report_text: str,
    *,
    accept_blocked: bool = False,
    require_ready: bool = False,
) -> None:
    evidence = data.get("planner_cleanup_bridge_evidence") or {}
    validate_planner_cleanup_bridge_evidence(
        evidence,
        accept_blocked_capability=accept_blocked,
        require_ready=require_ready,
    )
    assert "Planner Cleanup Bridge" in report_text, report_text[:500]
    if require_ready:
        assert data.get("primitive_provenance") != API_SEMANTIC_PROVENANCE, data


def _assert_waypoint_honesty(data: dict[str, Any], report_text: str) -> None:
    agent_view = data.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    assert metric_map.get("schema") == REAL_ROBOT_MAP_BUNDLE_SCHEMA, metric_map
    assert metric_map.get("public_contract_note"), metric_map
    forbidden_words = ("mess", "target", "acceptable")
    waypoints = metric_map.get("inspection_waypoints") or []
    assert waypoints, metric_map
    for waypoint in waypoints:
        allowed_sources = {
            "static_map_coverage",
            "fixture_coverage",
            "static_map_fixture_coverage",
            "agibot_robot_map_9_static_rehearsal",
        }
        if metric_map.get("mode") == "minimal":
            allowed_sources.add("generated_exploration_candidate")
        assert waypoint.get("waypoint_source") in allowed_sources, waypoint
        assert waypoint.get("purpose"), waypoint
        label_text = f"{waypoint.get('waypoint_source', '')} {waypoint.get('purpose', '')}".lower()
        assert not any(word in label_text for word in forbidden_words), waypoint
    worklist = agent_view.get("cleanup_worklist") or {}
    assert worklist.get("schema") == CLEANUP_WORKLIST_SCHEMA, worklist
    assert worklist.get("objects"), worklist
    assert worklist.get("waypoints"), worklist
    trace = data.get("cleanup_policy_trace") or {}
    assert trace.get("schema") == CLEANUP_POLICY_TRACE_SCHEMA, trace
    if metric_map.get("mode") == "minimal":
        assert trace.get("waypoint_source") == "generated_exploration_candidate", trace
        if data.get("semantic_sweep_mode") is True:
            assert trace.get("first_cleanup_before_full_survey") is False, trace
            assert trace.get("loop_style") == "scan_only", trace
            assert trace.get("cleanup_action_count") == 0, trace
        else:
            assert trace.get("loop_style") in {
                "survey_first_cleanup_loop",
                "interleaved_cleanup_loop",
            }, trace
            if trace.get("loop_style") == "survey_first_cleanup_loop":
                assert trace.get("first_cleanup_before_full_survey") is False, trace
            else:
                assert trace.get("first_cleanup_before_full_survey") is True, trace
            assert int(trace.get("cleanup_action_count") or 0) > 0, trace
            placed_object_count = int(trace.get("placed_object_count") or 0)
            post_place_observe_count = int(trace.get("post_place_observe_count") or 0)
            observed_waypoint_count = int(trace.get("observed_waypoint_count") or 0)
            total_waypoints = int(trace.get("total_waypoints") or 0)
            if trace.get("post_place_observe_complete") is not True:
                post_place_observe_count = max(
                    post_place_observe_count,
                    _post_place_observe_count_allowing_public_state_queries(trace),
                )
            assert placed_object_count > 0, trace
            assert total_waypoints > 0, trace
            assert observed_waypoint_count >= total_waypoints, trace
            assert post_place_observe_count >= placed_object_count, trace
        assert "Waypoint Honesty & Cleanup Loop" in report_text, report_text[:500]
        assert "generated_exploration_candidate" in report_text, report_text[:500]
        return
    assert trace.get("waypoint_source") == "static_map_fixture_coverage", trace
    assert trace.get("loop_style") == "interleaved_cleanup_loop", trace
    assert _trace_started_cleanup_after_first_actionable_observation(trace), trace
    placed_object_count = int(trace.get("placed_object_count") or 0)
    post_place_observe_count = int(trace.get("post_place_observe_count") or 0)
    if trace.get("post_place_observe_complete") is not True:
        post_place_observe_count = max(
            post_place_observe_count,
            _post_place_observe_count_allowing_public_state_queries(trace),
        )
    assert post_place_observe_count >= placed_object_count, trace
    assert "Waypoint Honesty & Cleanup Loop" in report_text, report_text[:500]
    assert "static_map_fixture_coverage" in report_text, report_text[:500]
    assert "post_place_observe" in report_text, report_text[:500]


def _trace_started_cleanup_after_first_actionable_observation(trace: dict[str, Any]) -> bool:
    first_cleanup = trace.get("first_cleanup_index")
    first_actionable = trace.get("first_actionable_observation_index")
    if first_cleanup is not None or first_actionable is not None:
        try:
            return int(first_cleanup) == int(first_actionable) + 1
        except (TypeError, ValueError):
            return False
    return trace.get("first_cleanup_before_full_survey") is True


def _post_place_observe_count_allowing_public_state_queries(trace: dict[str, Any]) -> int:
    pending = 0
    count = 0
    for event in trace.get("events") or []:
        if not isinstance(event, dict):
            continue
        tool = str(event.get("tool") or "")
        role = str(event.get("role") or "")
        if tool in {"place", "place_inside"} and role == "cleanup_action":
            pending += 1
            continue
        if tool == "observe" and pending > 0:
            count += 1
            pending -= 1
            continue
        if pending > 0 and role in {"coverage_scan_navigation", "cleanup_action"}:
            if tool != "close_receptacle":
                pending = 0
    return count


def _assert_real_robot_alignment(data: dict[str, Any], base: Path, report_text: str) -> None:
    agent_view = data.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    fixture_hints = agent_view.get("fixture_hints") or {}
    assert metric_map.get("schema") == REAL_ROBOT_MAP_BUNDLE_SCHEMA, metric_map
    for key in (
        "frame_id",
        "map_id",
        "map_version",
        "resolution_m",
        "origin",
        "width",
        "height",
        "occupancy_values",
        "map_bundle",
        "robot_pose",
    ):
        assert key in metric_map, metric_map
    map_bundle_metadata = metric_map.get("map_bundle") or {}
    assert map_bundle_metadata.get("schema") == "nav2_map_bundle_v1", map_bundle_metadata
    assert map_bundle_metadata.get("robot_profile_id") == "rby1m", map_bundle_metadata
    assert map_bundle_metadata.get("parameter_hash"), map_bundle_metadata
    waypoints = metric_map.get("inspection_waypoints") or []
    assert waypoints, metric_map
    for waypoint in waypoints:
        for key in ("frame_id", "x", "y", "yaw", "room_id", "label", "visited", "purpose"):
            assert key in waypoint, waypoint
    assert fixture_hints.get("schema") == "static_fixture_semantic_map_v1", fixture_hints
    assert fixture_hints.get("contains_runtime_observations") is False, fixture_hints
    assert "observations" not in fixture_hints, fixture_hints
    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            assert fixture.get("fixture_id"), fixture
            assert fixture.get("affordances"), fixture
            assert fixture.get("pose", {}).get("frame_id") == "map", fixture
            assert "observed_objects" not in fixture, fixture
    policy_view = agent_view.get("policy_view") or {}
    assert policy_view.get("chase_camera_policy_input") is False, policy_view
    assert not any("chase" in str(item).lower() for item in policy_view.get("allowed_inputs", []))
    readiness = data.get("real_robot_readiness") or {}
    assert readiness.get("schema") == REAL_ROBOT_READINESS_SCHEMA, readiness
    assert readiness.get("map_bundle_fields_present") is True, readiness
    assert readiness.get("pose_stamped_waypoints") is True, readiness
    assert readiness.get("static_fixture_semantic_map") is True, readiness
    assert readiness.get("policy_view_chase_excluded") is True, readiness
    assert readiness.get("semantic_navigation_only") is True, readiness
    assert readiness.get("sim_costmap_route_validation") is True, readiness
    assert readiness.get("real_robot_ready") is False, readiness
    assert readiness.get("physical_navigation_pilot") is False, readiness
    assert readiness.get("physical_cleanup_ready") is False, readiness
    assert readiness.get("map_bundle_snapshot_present") is True, readiness
    assert readiness.get("map_bundle_parameter_hash"), readiness
    assert readiness.get("navigation_backend_summary", {}).get(SIM_COSTMAP_PLANNER), readiness
    nav2_bundle = data.get("nav2_map_bundle") or {}
    assert nav2_bundle.get("schema") == "nav2_map_bundle_snapshot_v1", nav2_bundle
    assert nav2_bundle.get("snapshot_complete") is True, nav2_bundle
    artifact_paths = nav2_bundle.get("artifact_paths") or {}
    artifact_hashes = nav2_bundle.get("artifact_hashes") or {}
    for key in (
        "map_yaml",
        "occupancy_image",
        "semantics_json",
        "robot_profile",
        "costmap_params",
        "preview_png",
    ):
        assert key in artifact_paths, nav2_bundle
        assert key in artifact_hashes, nav2_bundle
        assert len(str(artifact_hashes[key])) == 64, artifact_hashes
        assert _resolve_path(base, str(artifact_paths[key])).is_file(), artifact_paths[key]
    assert "Real-Robot Readiness" in report_text, report_text[:500]
    assert "Nav2 Map Bundle" in report_text, report_text[:500]
    assert "map_bundle/map.yaml" in report_text, report_text[:500]
    assert "report_only_simulation_view" in report_text, report_text[:500]


def _has_planner_proof_requests(data: dict[str, Any]) -> bool:
    artifacts = data.get("artifacts") or {}
    return bool(data.get("planner_proof_requests") or artifacts.get("planner_proof_requests"))


def _assert_planner_proof_requests(data: dict[str, Any], base: Path, report_text: str) -> None:
    artifacts = data.get("artifacts") or {}
    manifest = data.get("planner_proof_requests")
    if manifest is None and artifacts.get("planner_proof_requests"):
        path = _resolve_path(base, str(artifacts["planner_proof_requests"]))
        assert path.is_file(), path
        manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest is None:
        return
    assert "Planner Proof Requests" in report_text, report_text[:500]
    assert manifest.get("schema") == PLANNER_PROOF_REQUESTS_SCHEMA, manifest
    assert manifest.get("agent_view_exposed") is False, manifest
    requests = manifest.get("requests") or []
    assert manifest.get("request_count") == len(requests), manifest
    semantic_substeps = data.get("semantic_substeps") or []
    if semantic_substeps:
        assert len(requests) == len(semantic_substeps), manifest
    for request in requests:
        assert request.get("object_id"), request
        if request.get("ready") is False:
            assert request.get("blockers"), request
        else:
            assert request.get("target_receptacle_id"), request
        assert "planner_probe_args" in request, request
    assert "planner_proof_requests" not in data.get("agent_view", {}), data.get("agent_view")


def _is_focused_robot_action(action: str) -> bool:
    return action.startswith(
        ("navigate_to_waypoint ", "observe ", *FOCUSED_SEMANTIC_ACTION_PREFIXES)
    )


def _assert_focused_robot_step(step: dict[str, Any]) -> None:
    focus = annotate_focus_visual_grounding(step.get("focus") or {}) or {}
    assert focus.get("has_focus") is True, step
    fpv_visibility = focus.get("fpv_visibility") or {}
    verify_visibility = focus.get("visibility") or {}
    visibility_states = [
        _focus_visibility_grounding_state(fpv_visibility, focus, step),
        _focus_visibility_grounding_state(verify_visibility, focus, step),
    ]
    assert any(state == "grounded" for state in visibility_states) or all(
        state == "unavailable" for state in visibility_states
    ), step


def _focus_visibility_grounding_state(
    visibility: dict[str, Any],
    focus: dict[str, Any],
    step: dict[str, Any],
) -> str:
    status = visibility.get("status")
    assert status in {
        "ok",
        "contained_inside",
        "segmentation_unavailable",
        "weak_object_visibility",
    }, step
    if status == "segmentation_unavailable":
        return "unavailable"
    if status == "contained_inside":
        return "grounded"
    if status == "weak_object_visibility":
        return "weak"
    has_object_focus = bool(
        focus.get("object_id") or focus.get("object_body_name") or focus.get("object_label")
    )
    if status == "ok" and "object_pixels" in visibility and has_object_focus:
        assert int(visibility.get("object_pixels") or 0) > 0, step
    return "grounded"


def _assert_no_forbidden_keys(payload: Any) -> None:
    if isinstance(payload, dict):
        forbidden = forbidden_agent_view_keys().intersection(payload)
        assert not forbidden, (sorted(forbidden), payload)
        for value in payload.values():
            _assert_no_forbidden_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_no_forbidden_keys(value)


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or path.exists():
        return path
    repo_path = Path(__file__).resolve().parents[2] / path
    if repo_path.exists():
        return repo_path
    return base / path


if __name__ == "__main__":
    main()
