from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.household.agibot_map_build_mcp_server import (
    AGIBOT_SEMANTIC_MAP_BUILD_POLICY,
    AGIBOT_SEMANTIC_MAP_BUILD_SCHEMA,
)
from roboclaws.household.profiles import CAMERA_GROUNDED_LABELS_LANE
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_SCHEMA,
    CLEANUP_POLICY_TRACE_SCHEMA,
    REAL_ROBOT_READINESS_SCHEMA,
    RUNTIME_METRIC_MAP_SCHEMA,
    forbidden_agent_view_keys,
)
from roboclaws.household.semantic_timeline import duplicate_post_place_navigations
from roboclaws.household.visual_grounding import EXTERNAL_VISUAL_GROUNDING_PROVENANCE

AGIBOT_SEMANTIC_MAP_BUILD_MCP_SERVER = "agibot_semantic_map_build"


def assert_agibot_semantic_map_build_result(
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
    expected_policy = _expected_policy(expect_policy, require_semantic_sweep=require_semantic_sweep)
    _assert_expected_identity(
        data,
        expect_backend=expect_backend,
        expect_policy=expected_policy,
        expect_mcp_server=expect_mcp_server,
        require_agent_driven=require_agent_driven,
    )

    agent_view = data.get("agent_view") or {}
    _assert_agibot_semantic_map_build_agent_view(agent_view)
    if require_runtime_metric_map:
        _assert_agibot_semantic_map_build_runtime_map(
            data.get("runtime_metric_map") or agent_view.get("runtime_metric_map") or {}
        )
    if min_sweep_coverage is not None:
        assert float(data.get("sweep_coverage_rate") or 0.0) >= min_sweep_coverage, data

    readiness = data.get("real_robot_readiness") or {}
    _assert_agibot_readiness(readiness)
    if require_agibot_g2_hardware:
        _assert_agibot_g2_hardware_semantic_map_build(data, base, readiness)
    _assert_agibot_blocked_manipulation(data)
    _assert_agibot_policy_trace(data)
    _assert_agibot_private_evaluation(data)
    report_text = _assert_agibot_artifacts(
        data,
        base,
        require_runtime_metric_map=require_runtime_metric_map,
    )
    _assert_agibot_report_text(
        report_text,
        expect_profile=expect_profile,
        require_runtime_metric_map=require_runtime_metric_map,
    )
    if require_camera_model_policy:
        _assert_agibot_semantic_map_build_camera_model_policy(
            data,
            report_text,
            expect_pipeline_id=expect_visual_grounding_pipeline,
            require_failure=require_visual_grounding_failure,
        )


def _expected_policy(
    expect_policy: str | None,
    *,
    require_semantic_sweep: bool,
) -> str | None:
    if require_semantic_sweep and expect_policy in {
        "deterministic_sweep_baseline",
        "semantic_sweep_baseline",
    }:
        return AGIBOT_SEMANTIC_MAP_BUILD_POLICY
    return expect_policy


def _assert_expected_identity(
    data: dict[str, Any],
    *,
    expect_backend: str | None,
    expect_policy: str | None,
    expect_mcp_server: str | None,
    require_agent_driven: bool,
) -> None:
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


def _assert_agibot_readiness(readiness: dict[str, Any]) -> None:
    assert readiness.get("schema") == REAL_ROBOT_READINESS_SCHEMA, readiness
    assert readiness.get("backend_variant") == "agibot_gdk", readiness
    assert readiness.get("semantic_map_build") is True, readiness
    assert readiness.get("physical_navigation_pilot") is True, readiness
    assert readiness.get("physical_cleanup_ready") is False, readiness
    assert readiness.get("manipulation_blocked") is True, readiness


def _assert_agibot_blocked_manipulation(data: dict[str, Any]) -> None:
    manipulation = data.get("manipulation_evidence") or {}
    assert manipulation.get("status") == "blocked_capability", manipulation
    assert manipulation.get("primitive_provenance") == "blocked_capability", manipulation


def _assert_agibot_policy_trace(data: dict[str, Any]) -> None:
    trace = data.get("cleanup_policy_trace") or {}
    assert trace.get("schema") == CLEANUP_POLICY_TRACE_SCHEMA, trace
    assert trace.get("agent_reasoning_visible") is True, trace
    assert trace.get("cleanup_action_count") == 0, trace
    decisions = {str(item.get("decision") or "") for item in trace.get("events") or []}
    assert "inspect_public_metric_map" in decisions, trace
    assert "inspect_public_fixture_hints" not in decisions, trace
    assert "observe_head_color" in decisions, trace


def _assert_agibot_private_evaluation(data: dict[str, Any]) -> None:
    private = data.get("private_evaluation") or {}
    assert private.get("generated_mess_count") == 0, private
    assert private.get("acceptable_destination_sets") == {}, private


def _assert_agibot_artifacts(
    data: dict[str, Any],
    base: Path,
    *,
    require_runtime_metric_map: bool,
) -> str:
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
    return _resolve_path(base, artifacts["report"]).read_text(encoding="utf-8")


def _assert_agibot_report_text(
    report_text: str,
    *,
    expect_profile: str | None,
    require_runtime_metric_map: bool,
) -> None:
    if expect_profile is not None:
        assert expect_profile in report_text, report_text[:500]
    assert "AgiBot Backend Evidence" in report_text, report_text[:500]
    assert "Real-Robot Readiness" in report_text, report_text[:500]
    assert "Agent View" in report_text, report_text[:500]
    assert "Private Evaluation" in report_text, report_text[:500]
    assert "Score" in report_text, report_text[:500]
    if require_runtime_metric_map:
        assert "Runtime Metric Map" in report_text, report_text[:500]


def _assert_agibot_semantic_map_build_agent_view(agent_view: dict[str, Any]) -> None:
    assert agent_view.get("forbidden_private_fields_absent") is True, agent_view
    assert "metric_map" in agent_view, agent_view
    assert "fixture_hints" in agent_view, agent_view
    assert "fixture_hints" not in (agent_view.get("public_tool_names") or []), agent_view
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


def _assert_agibot_semantic_map_build_runtime_map(
    runtime_metric_map: dict[str, Any],
) -> None:
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
    failure_count = int(evidence.get("visual_grounding_failure_count") or 0)
    assert int(evidence.get("event_count") or 0) >= 1, evidence
    if require_failure:
        assert failure_count >= 1, evidence
    _assert_agibot_camera_policy_events(evidence, pipeline_ids, require_failure=require_failure)
    assert data.get("raw_fpv_observations"), data
    assert "Camera Labeler Evidence" in report_text, report_text[:500]
    assert "Raw FPV Observations" in report_text, report_text[:500]
    assert pipeline_id in report_text, report_text[:500]
    assert "Bearer " not in json.dumps(data), data
    assert "Bearer " not in report_text, report_text[:500]


def _assert_agibot_camera_policy_events(
    evidence: dict[str, Any],
    pipeline_ids: list[str],
    *,
    require_failure: bool,
) -> None:
    events = evidence.get("events") or []
    assert events, evidence
    for event in events:
        pipeline = event.get("visual_grounding_pipeline") or {}
        assert pipeline.get("schema") == "visual_grounding_pipeline_v1", event
        assert pipeline.get("pipeline_id") in pipeline_ids, event
        if require_failure:
            _assert_failed_camera_policy_event(event, pipeline)
        else:
            assert pipeline.get("status") in {"ok", "failed"}, event


def _assert_failed_camera_policy_event(
    event: dict[str, Any],
    pipeline: dict[str, Any],
) -> None:
    assert event.get("candidate_count") == 0, event
    assert pipeline.get("status") == "failed", event
    assert pipeline.get("failure_reason"), event
    stage_names = {str(stage.get("stage") or "") for stage in pipeline.get("stages") or []}
    assert "agibot_head_color_capture" in stage_names, event
    assert "external_visual_grounding_not_invoked" in stage_names, event


def _assert_agibot_g2_hardware_semantic_map_build(
    data: dict[str, Any],
    base: Path,
    readiness: dict[str, Any],
) -> None:
    assert data.get("agent_driven") is True, data
    assert data.get("mcp_server") == AGIBOT_SEMANTIC_MAP_BUILD_MCP_SERVER, data
    assert data.get("policy") == AGIBOT_SEMANTIC_MAP_BUILD_POLICY, data
    assert data.get("evidence_lane") == CAMERA_GROUNDED_LABELS_LANE, data
    assert data.get("camera_labeler"), data
    assert data.get("perception_mode") == CAMERA_MODEL_POLICY_MODE, data
    runtime_metric_map = data.get("runtime_metric_map") or (data.get("agent_view") or {}).get(
        "runtime_metric_map"
    )
    assert isinstance(runtime_metric_map, dict), data
    _assert_agibot_semantic_map_build_runtime_map(runtime_metric_map)
    _assert_agibot_g2_readiness(data, readiness)
    _assert_agibot_g2_live_head_color(data, base)
    _assert_agibot_g2_camera_policy(data)
    _assert_agibot_g2_trace_and_manipulation(data)


def _assert_agibot_g2_readiness(
    data: dict[str, Any],
    readiness: dict[str, Any],
) -> None:
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


def _assert_agibot_g2_live_head_color(data: dict[str, Any], base: Path) -> None:
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


def _assert_agibot_g2_camera_policy(data: dict[str, Any]) -> None:
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
        _assert_agibot_g2_camera_policy_event(event, pipeline_ids)


def _assert_agibot_g2_camera_policy_event(
    event: dict[str, Any],
    pipeline_ids: list[str],
) -> None:
    pipeline = event.get("visual_grounding_pipeline") or {}
    assert pipeline.get("schema") == "visual_grounding_pipeline_v1", event
    assert str(pipeline.get("pipeline_id") or "") in pipeline_ids, event
    assert str(pipeline.get("pipeline_id") or "") not in {"sim", "manual"}, event
    assert pipeline.get("status") == "ok", event
    assert int(pipeline.get("candidate_count") or 0) >= 1, event
    stages = pipeline.get("stages") or []
    assert stages, event
    assert all(str(stage.get("status") or "ok") != "blocked" for stage in stages), event


def _assert_agibot_g2_trace_and_manipulation(data: dict[str, Any]) -> None:
    trace = data.get("cleanup_policy_trace") or {}
    decisions = {str(item.get("decision") or "") for item in trace.get("events") or []}
    assert "visit_public_waypoint" in decisions, trace
    assert "observe_head_color" in decisions, trace
    manipulation = data.get("manipulation_evidence") or {}
    assert manipulation.get("status") == "blocked_capability", manipulation


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
        if line.strip():
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
