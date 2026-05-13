#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.cleanup_primitive_evidence import (
    validate_cleanup_primitive_evidence,
)
from roboclaws.molmo_cleanup.planner_cleanup_bridge import (
    validate_planner_cleanup_bridge_evidence,
)
from roboclaws.molmo_cleanup.planner_proof_attachment import (
    validate_planner_proof_attachment,
)
from roboclaws.molmo_cleanup.planner_proof_bundle import (
    PLANNER_PROOF_BUNDLE_SCHEMA,
    planner_proof_attachments,
    validate_planner_proof_bundle,
)
from roboclaws.molmo_cleanup.planner_proof_quality import (
    planner_proof_quality_evidence,
    validate_planner_proof_quality_evidence,
)
from roboclaws.molmo_cleanup.planner_proof_requests import PLANNER_PROOF_REQUESTS_SCHEMA
from roboclaws.molmo_cleanup.profiles import (
    WORLD_LABELS_PROFILE,
    cleanup_profile,
    validate_cleanup_profile_metadata,
)
from roboclaws.molmo_cleanup.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_NAME,
    CAMERA_MODEL_POLICY_SCHEMA,
    CLEANUP_POLICY_TRACE_SCHEMA,
    CLEANUP_WORKLIST_SCHEMA,
    REAL_ROBOT_MAP_BUNDLE_SCHEMA,
    REAL_ROBOT_READINESS_SCHEMA,
    REALWORLD_CONTRACT,
    SIMULATED_CAMERA_MODEL_PROVENANCE,
    forbidden_agent_view_keys,
)
from roboclaws.molmo_cleanup.report_visual_core import assert_cleanup_report_visual_core
from roboclaws.molmo_cleanup.semantic_timeline import (
    CANONICAL_INSIDE_CLEANUP_PHASES,
    CANONICAL_SURFACE_CLEANUP_PHASES,
    CLOSE_RECEPTACLE_PHASE,
    FOCUSED_SEMANTIC_ACTION_PREFIXES,
    OPEN_RECEPTACLE_PHASE,
    PLACE_INSIDE_PHASE,
    SEMANTIC_LOOP_VARIANT,
    SEMANTIC_RESPONSE_PHASES,
    annotate_focus_visual_grounding,
    has_complete_semantic_sequence,
    successful_semantic_phases,
)


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
    parser.add_argument("--require-openclaw-minimum", action="store_true")
    parser.add_argument("--require-robot-views", action="store_true")
    parser.add_argument("--require-advisory-scoring", action="store_true")
    parser.add_argument("--require-raw-fpv-observations", action="store_true")
    parser.add_argument("--require-camera-model-policy", action="store_true")
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
            "openclaw_agent"
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
            require_openclaw_minimum=args.require_openclaw_minimum,
            require_robot_views=args.require_robot_views,
            require_advisory_scoring=args.require_advisory_scoring,
            require_raw_fpv_observations=args.require_raw_fpv_observations,
            require_camera_model_policy=args.require_camera_model_policy,
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
    require_openclaw_minimum: bool = False,
    require_robot_views: bool = False,
    require_advisory_scoring: bool = False,
    require_raw_fpv_observations: bool = False,
    require_camera_model_policy: bool = False,
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
) -> None:
    assert data.get("contract") == REALWORLD_CONTRACT, data
    assert data.get("adr_0003_satisfied") is True, data
    if expect_policy is not None:
        assert data.get("policy") == expect_policy, data
    assert data.get("semantic_loop_variant") == SEMANTIC_LOOP_VARIANT, data
    assert data.get("policy_uses_private_truth") is False, data
    assert data.get("planner_uses_private_manifest") is False, data
    assert data.get("fixture_hint_mode") == "room_only", data
    assert data.get("generated_mess_count", 0) >= min_generated_mess_count, data
    enforce_success = (
        require_clean_agent_run or not require_openclaw_minimum
    ) and not require_raw_fpv_observations
    if enforce_success:
        assert data.get("mess_restoration_rate", 0) >= 0.70, data
        assert data.get("sweep_coverage_rate", 0) >= 0.90, data
        assert data.get("disturbance_count", 999) <= 2, data
        assert data.get("cleanup_status") == "success", data
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
    _assert_trace_is_public(_resolve_path(base, data["artifacts"]["trace"]))
    private = data.get("private_evaluation") or {}
    assert private.get("generated_mess_count") == data.get("generated_mess_count"), data
    assert private.get("generated_mess_count", 0) >= min_generated_mess_count, data
    assert private.get("acceptable_destination_sets"), data
    if enforce_success:
        for item in data.get("semantic_substeps") or []:
            phases = successful_semantic_phases(item.get("steps", []))
            assert has_complete_semantic_sequence(phases), (phases, item)

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
    report_text = _resolve_path(base, artifacts["report"]).read_text(encoding="utf-8")
    if expect_profile is not None:
        _assert_cleanup_profile(data, report_text, expect_profile)
    assert "Agent View" in report_text, report_text[:500]
    assert "Private Evaluation" in report_text, report_text[:500]
    assert "Score" in report_text, report_text[:500]
    if enforce_success or data.get("semantic_substeps"):
        assert "Semantic Substeps" in report_text, report_text[:500]
    assert "ADR-0003 real-world-style cleanup run" in report_text, report_text[:500]
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
    if require_clean_agent_run:
        _assert_clean_agent_run(data)
    if require_robot_views:
        _assert_robot_views(data, base, require_complete_actions=enforce_success)
    if require_advisory_scoring:
        _assert_advisory_scoring(data, base, report_text)
    if require_raw_fpv_observations:
        _assert_raw_fpv_observations(data, base, report_text)
    if require_camera_model_policy:
        _assert_camera_model_policy(data, report_text)
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
        _assert_real_robot_alignment(data, report_text)


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


def _assert_clean_agent_run(data: dict[str, Any]) -> None:
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
        assert int(counts.get(f"{tool}:request") or 0) >= 1, (tool, counts, data)
    diagnostics = data.get("agent_bridge") or {}
    assert diagnostics.get("stale_reference_errors") == 0, data
    assert int(diagnostics.get("semantic_order_errors") or 0) == 0, data
    assert diagnostics.get("premature_done") is False, data
    assert diagnostics.get("fridge_inside_sequence_ok") is True, data
    assert _complete_semantic_substep_count(data) >= int(data.get("generated_mess_count") or 0), (
        data
    )


def _complete_semantic_substep_count(data: dict[str, Any]) -> int:
    complete = 0
    for item in data.get("semantic_substeps") or []:
        phases = successful_semantic_phases(item.get("steps", []))
        if has_complete_semantic_sequence(phases):
            complete += 1
    return complete


def _assert_public_agent_view(agent_view: dict[str, Any]) -> None:
    assert agent_view.get("contract") == REALWORLD_CONTRACT, agent_view
    assert agent_view.get("forbidden_private_fields_absent") is True, agent_view
    assert "metric_map" in agent_view, agent_view
    assert "fixture_hints" in agent_view, agent_view
    assert "observed_objects" in agent_view, agent_view
    assert "objects" not in agent_view.get("metric_map", {}), agent_view
    worklist = agent_view.get("cleanup_worklist") or {}
    if worklist:
        assert worklist.get("schema") == CLEANUP_WORKLIST_SCHEMA, worklist
        assert worklist.get("waypoint_source") == "static_map_fixture_coverage", worklist
    policy_view = agent_view.get("policy_view") or {}
    if policy_view:
        assert policy_view.get("chase_camera_policy_input") is False, policy_view
    _assert_no_forbidden_keys(agent_view)
    if agent_view.get("perception_mode") == "raw_fpv_only":
        assert agent_view.get("structured_detections_available") is False, agent_view
        assert not agent_view.get("observed_objects"), agent_view
        raw = agent_view.get("raw_fpv_observations") or []
        assert raw, agent_view
        for item in raw:
            assert item.get("perception_mode") == "raw_fpv_only", item
            assert item.get("structured_detections_available") is False, item
            forbidden = {"category", "name", "support_estimate", "target_receptacle_id"}
            assert not forbidden.intersection(item), item
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
        for item in observed:
            assert str(item.get("object_id", "")).startswith("observed_"), item
            assert item.get("perception_source") == CAMERA_MODEL_POLICY_MODE, item
            assert item.get("model_provenance") == SIMULATED_CAMERA_MODEL_PROVENANCE, item
            assert item.get("source_observation_id"), item
            support = item.get("support_estimate") or {}
            assert support.get("source") == CAMERA_MODEL_POLICY_MODE, item
            assert support.get("model_provenance") == SIMULATED_CAMERA_MODEL_PROVENANCE, item
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


def _assert_trace_is_public(trace_path: Path) -> None:
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)
        assert payload.get("tool") != "scene_objects", payload
        if payload.get("tool") == "done":
            continue
        public_payload = _without_internal_proof_evidence(payload)
        _assert_no_forbidden_keys(public_payload)
        response = public_payload.get("response")
        if isinstance(response, dict):
            assert "objects" not in response, response
            assert "scene_objects" not in response, response


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
    assert data.get("view_variant") == "molmospaces-rby1m-fpv-map-chase-verify", data
    artifacts = data.get("artifacts") or {}
    robot_views_dir = _resolve_path(base, artifacts.get("robot_views", ""))
    assert robot_views_dir.is_dir(), robot_views_dir
    report_path = _resolve_path(base, artifacts.get("report", ""))
    report_text = report_path.read_text(encoding="utf-8")
    assert "Robot View Timeline" in report_text, report_text[:500]
    steps = data.get("robot_view_steps") or []
    assert len(steps) >= 2, data
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
    assert focused_actions, (focused_actions, data)
    if require_complete_actions:
        for expected in CANONICAL_SURFACE_CLEANUP_PHASES:
            assert expected in focused_actions, (expected, focused_actions, data)
        if any(
            item.get("target_receptacle_category") == "Fridge"
            for item in data.get("semantic_substeps") or []
        ):
            assert OPEN_RECEPTACLE_PHASE in focused_actions, data
            assert PLACE_INSIDE_PHASE in focused_actions, data
            assert CLOSE_RECEPTACLE_PHASE in focused_actions, data


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
    assert not agent_view.get("observed_objects"), agent_view
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
        image_artifacts = item.get("image_artifacts") or {}
        fpv = image_artifacts.get("fpv") or item.get("fpv_image")
        assert fpv, item
        fpv_path = _resolve_path(base, str(fpv))
        if not fpv_path.exists():
            fpv_path = _resolve_path(robot_views_dir.parent, str(fpv))
        assert fpv_path.is_file(), (fpv_path, item)
        assert fpv_path.stat().st_size > 0, (fpv_path, item)


def _assert_camera_model_policy(data: dict[str, Any], report_text: str) -> None:
    assert data.get("perception_mode") == CAMERA_MODEL_POLICY_MODE, data
    evidence = data.get("camera_model_policy_evidence") or (
        (data.get("agent_view") or {}).get("camera_model_policy_evidence") or {}
    )
    assert evidence.get("schema") == CAMERA_MODEL_POLICY_SCHEMA, evidence
    assert evidence.get("enabled") is True, evidence
    assert evidence.get("model_provenance") == SIMULATED_CAMERA_MODEL_PROVENANCE, evidence
    assert evidence.get("private_truth_included") is False, evidence
    assert int(evidence.get("event_count") or 0) >= 1, evidence
    assert int(evidence.get("candidate_count") or 0) >= 1, evidence
    assert evidence.get("events"), evidence
    assert data.get("raw_fpv_observations"), data
    counts = data.get("tool_event_counts") or {}
    assert int(counts.get("infer_camera_model_candidates:request") or 0) >= 1, counts
    assert "Camera Model Policy" in report_text, report_text[:500]
    assert "Raw FPV Observations" in report_text, report_text[:500]
    assert "simulated_camera_model" in report_text, report_text[:500]


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
        assert waypoint.get("waypoint_source") in {
            "static_map_coverage",
            "fixture_coverage",
            "static_map_fixture_coverage",
        }, waypoint
        assert waypoint.get("purpose"), waypoint
        label_text = f"{waypoint.get('waypoint_source', '')} {waypoint.get('purpose', '')}".lower()
        assert not any(word in label_text for word in forbidden_words), waypoint
    worklist = agent_view.get("cleanup_worklist") or {}
    assert worklist.get("schema") == CLEANUP_WORKLIST_SCHEMA, worklist
    assert worklist.get("objects"), worklist
    assert worklist.get("waypoints"), worklist
    trace = data.get("cleanup_policy_trace") or {}
    assert trace.get("schema") == CLEANUP_POLICY_TRACE_SCHEMA, trace
    assert trace.get("waypoint_source") == "static_map_fixture_coverage", trace
    assert trace.get("loop_style") == "interleaved_cleanup_loop", trace
    assert trace.get("first_cleanup_before_full_survey") is True, trace
    assert trace.get("post_place_observe_complete") is True, trace
    assert int(trace.get("post_place_observe_count") or 0) >= int(
        trace.get("placed_object_count") or 0
    ), trace
    assert "Waypoint Honesty & Cleanup Loop" in report_text, report_text[:500]
    assert "static_map_fixture_coverage" in report_text, report_text[:500]
    assert "post_place_observe" in report_text, report_text[:500]


def _assert_real_robot_alignment(data: dict[str, Any], report_text: str) -> None:
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
        "robot_pose",
    ):
        assert key in metric_map, metric_map
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
    assert readiness.get("real_robot_ready") is False, readiness
    assert readiness.get("navigation_backend_summary", {}).get(API_SEMANTIC_PROVENANCE), readiness
    assert "Real-Robot Readiness" in report_text, report_text[:500]
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
    _assert_focus_visibility_status(fpv_visibility, focus, step)
    _assert_focus_visibility_status(verify_visibility, focus, step)


def _assert_focus_visibility_status(
    visibility: dict[str, Any],
    focus: dict[str, Any],
    step: dict[str, Any],
) -> None:
    status = visibility.get("status")
    assert status in {"ok", "contained_inside"}, step
    if (
        status == "ok"
        and "object_pixels" in visibility
        and (focus.get("object_id") or focus.get("object_body_name") or focus.get("object_label"))
    ):
        assert int(visibility.get("object_pixels") or 0) > 0, step


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
