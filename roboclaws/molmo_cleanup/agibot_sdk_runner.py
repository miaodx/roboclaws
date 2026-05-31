from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from roboclaws.mcp.profiles import REAL_ROBOT_CLEANUP_PROFILE, contract_profile_metadata
from roboclaws.molmo_cleanup.agibot_map_bundle import write_agibot_nav2_map_bundle
from roboclaws.molmo_cleanup.nav2_adapter import BLOCKED_CAPABILITY_PROVENANCE
from roboclaws.molmo_cleanup.realworld_contract import REALWORLD_CONTRACT
from roboclaws.molmo_cleanup.report import render_cleanup_report, write_state_snapshot
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.types import CleanupScenario

AGIBOT_SDK_RUNNER_BACKEND = "agibot_sdk_runner"
AGIBOT_GDK_BACKEND_VARIANT = "agibot_gdk"
AGIBOT_GDK_NORMAL_NAVI_PROVENANCE = "agibot_gdk_normal_navi"
AGIBOT_GDK_RELATIVE_MOVE_PROVENANCE = "agibot_gdk_relative_move"
AGIBOT_HEAD_COLOR_CAMERA_PROVENANCE = "agibot_gdk_head_color_camera"
PHYSICAL_AGIBOT_PILOT_SCHEMA = "physical_agibot_cleanup_pilot_v1"
PHYSICAL_AGIBOT_PILOT_POLICY = "physical_agibot_navigation_perception_pilot"
BLOCKED_MANIPULATION_TOOLS = (
    "pick",
    "place",
    "place_inside",
    "open_receptacle",
    "close_receptacle",
)


class AgibotSDKRunnerError(RuntimeError):
    """Raised when the SDK runner subprocess fails before writing artifacts."""


class AgibotSDKRunnerAdapter:
    """Subprocess boundary from Roboclaws semantic tools to the AgiBot SDK runner."""

    def __init__(
        self,
        *,
        context_json: Path,
        run_dir: Path,
        runner_script: Path | None = None,
        runner_python: str | Path | None = None,
        real_movement_enabled: bool = False,
        agibot_map_artifact_dir: Path | None = None,
    ) -> None:
        self.context_json = Path(context_json).resolve()
        self.run_dir = Path(run_dir).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        repo_root = Path(__file__).resolve().parents[2]
        self.runner_script = (
            runner_script
            or (repo_root / "vendors" / "agibot_sdk" / "tools" / "run_agibot_cleanup_backend.py")
        ).resolve()
        self.runner_python = str(runner_python or sys.executable)
        self.real_movement_enabled = bool(real_movement_enabled)
        self.agibot_map_artifact_dir = (
            Path(agibot_map_artifact_dir).resolve() if agibot_map_artifact_dir else None
        )
        self.subphase_results: list[dict[str, Any]] = []
        self._agent_view_result: dict[str, Any] | None = None
        self._context_payload: dict[str, Any] | None = None

    @property
    def agent_view_path(self) -> Path:
        return self.run_dir / "subphases" / "01-agent-view" / "agent_view.json"

    @property
    def context_payload(self) -> dict[str, Any]:
        if self._context_payload is None:
            self._context_payload = _load_json(self.context_json)
        return self._context_payload

    def export_agent_view(self) -> dict[str, Any]:
        if self._agent_view_result is None:
            self._agent_view_result = self._run_stage(
                "01-agent-view",
                [
                    "agent-view",
                    "--context-json",
                    str(self.context_json),
                    "--output-dir",
                    str(self.run_dir / "subphases" / "01-agent-view"),
                ]
                + (
                    ["--agibot-map-artifact-dir", str(self.agibot_map_artifact_dir)]
                    if self.agibot_map_artifact_dir
                    else []
                ),
            )
        return self._agent_view_result

    def metric_map(self) -> dict[str, Any]:
        self.export_agent_view()
        return _load_json(self.agent_view_path)["metric_map"]

    def fixture_hints(self) -> dict[str, Any]:
        self.export_agent_view()
        return _load_json(self.agent_view_path)["fixture_hints"]

    def observe(self, *, label: str = "observe") -> dict[str, Any]:
        self.export_agent_view()
        gate_block = self._movement_gate_block(tool="observe")
        if gate_block is not None:
            gate_block.setdefault("observation_label", label)
            return gate_block
        args = [
            "observe",
            "--agent-view-json",
            str(self.agent_view_path),
            "--output-dir",
            str(self.run_dir / "subphases" / "02-observe"),
            "--camera",
            "head_color",
        ]
        if self.real_movement_enabled:
            args.append("--execute")
        result = self._run_stage("02-observe", args)
        response = dict(result.get("tool_response") or {})
        response.setdefault("observation_label", label)
        response.setdefault("agibot_sdk_report", _relpath(result["report_path"], self.run_dir))
        return response

    def navigate_to_waypoint(self, *, waypoint_id: str) -> dict[str, Any]:
        self.export_agent_view()
        gate_block = self._movement_gate_block(tool="navigate_to_waypoint")
        if gate_block is not None:
            gate_block.setdefault("waypoint_id", waypoint_id)
            return gate_block
        args = [
            "navigate-waypoint",
            "--agent-view-json",
            str(self.agent_view_path),
            "--output-dir",
            str(self.run_dir / "subphases" / "03-navigate-waypoint"),
            "--waypoint-id",
            waypoint_id,
        ]
        if self.real_movement_enabled:
            args.extend(["--execute", "--arrival-observe"])
        result = self._run_stage("03-navigate-waypoint", args)
        response = dict(result.get("tool_response") or {})
        response.setdefault("agibot_sdk_report", _relpath(result["report_path"], self.run_dir))
        return response

    def navigate_to_room(self, *, room_id: str) -> dict[str, Any]:
        metric_map = self.metric_map()
        waypoints = [
            item
            for item in metric_map.get("inspection_waypoints") or []
            if isinstance(item, dict) and str(item.get("room_id") or "") == room_id
        ]
        if not waypoints:
            return self._blocked_response(
                tool="navigate_to_room",
                failure_type="missing_room_waypoint",
                message=f"Room {room_id!r} does not resolve to a public inspection waypoint.",
                extra={"room_id": room_id},
            )
        waypoint_id = _preferred_verified_waypoint_id(waypoints) or str(
            waypoints[0].get("waypoint_id") or ""
        )
        response = dict(self.navigate_to_waypoint(waypoint_id=waypoint_id))
        response["tool"] = "navigate_to_room"
        response["room_id"] = room_id
        response["goal_source"] = "room_inspection_waypoint"
        return response

    def navigate_to_fixture_preferred_waypoint(self, *, fixture_id: str) -> dict[str, Any]:
        fixture = _fixture_by_id(self.fixture_hints(), fixture_id)
        waypoint_id = str(
            (fixture or {}).get("preferred_manipulation_waypoint_id")
            or (fixture or {}).get("preferred_inspection_waypoint_id")
            or ""
        )
        if not fixture or not waypoint_id:
            response = self._blocked_response(
                tool="navigate_to_receptacle",
                failure_type="missing_fixture_preferred_waypoint",
                message=f"Fixture {fixture_id!r} does not resolve to a public preferred waypoint.",
            )
        else:
            response = self.navigate_to_waypoint(waypoint_id=waypoint_id)
            response = dict(response)
            response["tool"] = "navigate_to_receptacle"
        response["fixture_id"] = fixture_id
        response["receptacle_id"] = fixture_id
        response["preferred_waypoint_id"] = waypoint_id
        response["manipulation_ready"] = False
        return response

    def navigate_to_object(
        self,
        *,
        object_id: str,
        waypoint_id: str = "",
        fixture_id: str = "",
    ) -> dict[str, Any]:
        if waypoint_id:
            response = dict(self.navigate_to_waypoint(waypoint_id=waypoint_id))
        elif fixture_id:
            response = dict(self.navigate_to_fixture_preferred_waypoint(fixture_id=fixture_id))
        else:
            response = self._blocked_response(
                tool="navigate_to_object",
                failure_type="object_not_mapped_to_public_waypoint",
                message=(
                    f"Object {object_id!r} does not resolve to a verified public waypoint "
                    "in the AgiBot pilot map context."
                ),
            )
        response["tool"] = "navigate_to_object"
        response["object_id"] = object_id
        response["fixture_id"] = fixture_id
        response["manipulation_ready"] = False
        return response

    def navigate_to_visual_candidate(
        self,
        *,
        source_observation_id: str,
        candidate_id: str = "",
        waypoint_id: str = "",
        fixture_id: str = "",
        target_fixture_id: str = "",
    ) -> dict[str, Any]:
        resolved_fixture_id = fixture_id or target_fixture_id
        if waypoint_id:
            response = dict(self.navigate_to_waypoint(waypoint_id=waypoint_id))
        elif resolved_fixture_id:
            response = dict(
                self.navigate_to_fixture_preferred_waypoint(fixture_id=resolved_fixture_id)
            )
        else:
            response = self._blocked_response(
                tool="navigate_to_visual_candidate",
                failure_type="visual_candidate_not_mapped_to_public_waypoint",
                message=(
                    "Visual candidate navigation requires a verified waypoint or "
                    "fixture-preferred waypoint in the AgiBot pilot map context."
                ),
            )
        response["tool"] = "navigate_to_visual_candidate"
        response["source_observation_id"] = source_observation_id
        response["candidate_id"] = candidate_id
        response["fixture_id"] = resolved_fixture_id
        response["target_fixture_id"] = target_fixture_id
        response["bounded_local_nudge"] = _bounded_local_nudge_status(enabled=False)
        response["manipulation_ready"] = False
        return response

    def blocked_manipulation(
        self,
        *,
        tool: str,
        reason: str = "physical_manipulation_unproven",
    ) -> dict[str, Any]:
        return self._blocked_response(tool=tool, failure_type=reason, message=reason)

    def _blocked_response(
        self,
        *,
        tool: str,
        failure_type: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = {
            "ok": False,
            "tool": tool,
            "status": "blocked_capability",
            "contract": REALWORLD_CONTRACT,
            "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
            "error_reason": "blocked_capability",
            "failure_type": failure_type,
            "backend_error_summary": message,
            "physical_navigation_pilot": True,
            "physical_cleanup_ready": False,
            "manipulation_ready": False,
        }
        if extra:
            response.update(extra)
        return response

    def _movement_gate_block(self, *, tool: str) -> dict[str, Any] | None:
        if not self.real_movement_enabled:
            return None
        context = self.context_payload
        localization_gate = _operator_localization_gate(context)
        run_gate = _operator_run_enablement_gate(context, movement_enabled=True)
        if not localization_gate["ok"]:
            return self._blocked_response(
                tool=tool,
                failure_type="operator_localization_gate_not_confirmed",
                message="Operator localization gate is required before AgiBot real movement.",
                extra={
                    "operator_localization_gate": localization_gate,
                    "operator_run_enablement_gate": run_gate,
                    "human_takeover_stop": True,
                },
            )
        if not run_gate["ok"]:
            return self._blocked_response(
                tool=tool,
                failure_type="operator_run_enablement_gate_not_confirmed",
                message="Operator run enablement gate is required before AgiBot real movement.",
                extra={
                    "operator_localization_gate": localization_gate,
                    "operator_run_enablement_gate": run_gate,
                    "human_takeover_stop": True,
                },
            )
        return None

    def _run_stage(self, stage_name: str, args: list[str]) -> dict[str, Any]:
        stage_dir = self.run_dir / "subphases" / stage_name
        stage_dir.mkdir(parents=True, exist_ok=True)
        command = [self.runner_python, str(self.runner_script), *args]
        proc = subprocess.run(
            command,
            cwd=self.runner_script.parent.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        (stage_dir / "runner_stdout.txt").write_text(proc.stdout, encoding="utf-8")
        (stage_dir / "runner_stderr.txt").write_text(proc.stderr, encoding="utf-8")
        result_path = stage_dir / "run_result.json"
        if not result_path.is_file():
            raise AgibotSDKRunnerError(
                f"SDK runner failed before writing run_result.json for {stage_name}: "
                f"exit={proc.returncode} stderr={proc.stderr.strip()}"
            )
        result = _load_json(result_path)
        result["returncode"] = proc.returncode
        result["command"] = command
        result["report_path"] = str(stage_dir / "report.html")
        result["stdout_path"] = str(stage_dir / "runner_stdout.txt")
        result["stderr_path"] = str(stage_dir / "runner_stderr.txt")
        self.subphase_results.append(result)
        if proc.returncode and stage_name == "01-agent-view":
            raise AgibotSDKRunnerError(
                f"SDK runner agent-view export failed: exit={proc.returncode}"
            )
        return result


def run_physical_agibot_cleanup_pilot(
    *,
    run_dir: Path,
    context_json: Path,
    runner_script: Path | None = None,
    runner_python: str | Path | None = None,
    real_movement_enabled: bool = False,
    agibot_map_artifact_dir: Path | None = None,
    waypoint_id: str | None = None,
    scenario: CleanupScenario | None = None,
) -> dict[str, Any]:
    """Run the AgiBot real-robot cleanup backend pilot through the SDK CLI boundary."""

    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    scenario = scenario or build_cleanup_scenario(seed=7)
    adapter = AgibotSDKRunnerAdapter(
        context_json=context_json,
        run_dir=run_dir,
        runner_script=runner_script,
        runner_python=runner_python,
        real_movement_enabled=real_movement_enabled,
        agibot_map_artifact_dir=agibot_map_artifact_dir,
    )
    started_at = time.time()
    trace_events: list[dict[str, Any]] = []
    policy_events: list[dict[str, Any]] = []

    before_snapshot = write_state_snapshot(
        scenario,
        _initial_locations(scenario),
        run_dir / "before.png",
        title="Before physical AgiBot pilot",
    )
    after_snapshot = write_state_snapshot(
        scenario,
        _initial_locations(scenario),
        run_dir / "after.png",
        title="After physical AgiBot pilot",
    )

    metric_map = adapter.metric_map()
    fixture_hints = adapter.fixture_hints()
    _record(trace_events, started_at, "metric_map", {}, metric_map)
    _record(trace_events, started_at, "fixture_hints", {}, fixture_hints)

    observation = adapter.observe(label="pre_navigation")
    policy_events.append(_policy_event(len(policy_events), observation, "pre_navigation_observe"))
    _record(trace_events, started_at, "observe", {"label": "pre_navigation"}, observation)

    waypoint_id = waypoint_id or _first_waypoint_id(metric_map)
    navigation = adapter.navigate_to_waypoint(waypoint_id=waypoint_id)
    policy_events.append(_policy_event(len(policy_events), navigation, "inspection_waypoint"))
    _record(
        trace_events,
        started_at,
        "navigate_to_waypoint",
        {"waypoint_id": waypoint_id},
        navigation,
    )

    manipulation_results = []
    for tool in BLOCKED_MANIPULATION_TOOLS:
        result = adapter.blocked_manipulation(tool=tool)
        manipulation_results.append(result)
        policy_events.append(_policy_event(len(policy_events), result, "blocked_manipulation"))
        _record(trace_events, started_at, tool, {}, result)

    trace_path = run_dir / "trace.jsonl"
    trace_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in trace_events),
        encoding="utf-8",
    )

    readiness = _readiness_payload(
        context=adapter.context_payload,
        metric_map=metric_map,
        fixture_hints=fixture_hints,
        observation=observation,
        navigation=navigation,
        manipulation_results=manipulation_results,
        real_movement_enabled=real_movement_enabled,
    )
    subphase_reports = _subphase_reports(adapter.subphase_results, run_dir)
    nav2_map_bundle = (
        write_agibot_nav2_map_bundle(
            source_map_dir=Path(agibot_map_artifact_dir),
            context_json=context_json,
            bundle_dir=run_dir / "map_bundle",
        )
        if agibot_map_artifact_dir is not None
        else {}
    )
    if nav2_map_bundle:
        readiness["map_bundle_snapshot_present"] = bool(nav2_map_bundle.get("snapshot_complete"))
        readiness["map_bundle_artifact_count"] = len(nav2_map_bundle.get("artifact_hashes") or {})
        readiness["map_bundle_parameter_hash"] = nav2_map_bundle.get("parameter_hash", "")
        readiness["map_bundle_snapshot_root"] = nav2_map_bundle.get("snapshot_root", "")
    run_result = {
        "schema": PHYSICAL_AGIBOT_PILOT_SCHEMA,
        "contract": REALWORLD_CONTRACT,
        "cleanup_profile": REAL_ROBOT_CLEANUP_PROFILE,
        "cleanup_profile_metadata": contract_profile_metadata(REAL_ROBOT_CLEANUP_PROFILE),
        "backend": AGIBOT_SDK_RUNNER_BACKEND,
        "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
        "policy": PHYSICAL_AGIBOT_PILOT_POLICY,
        "agent_driven": False,
        "mcp_server": "roboclaws_real_robot_cleanup_v1_cli_boundary",
        "scenario_id": scenario.scenario_id,
        "task_prompt": scenario.task,
        "seed": scenario.seed,
        "cleanup_status": readiness["status"],
        "primitive_provenance": _dominant_primitive_provenance([navigation, observation]),
        "generated_mess_count": 0,
        "requested_generated_mess_count": 0,
        "sweep_coverage_rate": 1.0 if observation.get("ok") else 0.0,
        "disturbance_count": 0,
        "score": _empty_score(),
        "private_evaluation": {
            "generated_mess_count": 0,
            "generated_mess_set": [],
            "acceptable_destination_sets": {},
            "mess_restoration_rate": 0.0,
            "sweep_coverage_rate": 1.0 if observation.get("ok") else 0.0,
            "disturbance_count": 0,
            "public_contract_note": "AgiBot physical pilot does not run private cleanup scoring.",
        },
        "agent_view": {
            "metric_map": metric_map,
            "fixture_hints": fixture_hints,
            "observed_objects": [],
            "raw_fpv_observations": [],
            "perception_mode": "robot_policy_camera",
            "structured_detections_available": False,
            "policy_view": {"policy_observation_camera": "head_color"},
            "cleanup_worklist": {"schema": "cleanup_worklist_v1", "objects": []},
            "forbidden_private_fields_absent": True,
        },
        "cleanup_policy_trace": {
            "schema": "cleanup_policy_trace_v1",
            "waypoint_source": "agibot_sdk_agent_view_export",
            "loop_style": "physical_agibot_navigation_perception_pilot",
            "total_waypoints": len(metric_map.get("inspection_waypoints") or []),
            "observed_waypoint_count": 1 if observation.get("ok") else 0,
            "scan_observe_count": 1,
            "cleanup_action_count": 0,
            "placed_object_count": 0,
            "post_place_observe_count": 0,
            "post_place_observe_complete": True,
            "first_cleanup_before_full_survey": False,
            "events": policy_events,
            "public_contract_note": (
                "Roboclaws owns the cleanup-shaped session and calls the AgiBot SDK "
                "runner at semantic tool granularity."
            ),
        },
        "semantic_substeps": [],
        "real_robot_readiness": readiness,
        "nav2_map_bundle": nav2_map_bundle,
        "agibot_sdk_runner": {
            "schema": "agibot_sdk_runner_boundary_v1",
            "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
            "runner_script": str(adapter.runner_script),
            "agibot_map_artifact_dir": str(agibot_map_artifact_dir or ""),
            "real_movement_enabled": real_movement_enabled,
            "next_confidence_layer": "Agibot Robot Map 9 Semantic Actions Rehearsal",
            "subphase_reports": subphase_reports,
            "gdk_imported_by_roboclaws": False,
            "public_tool_boundary": [
                "metric_map",
                "fixture_hints",
                "observe",
                "navigate_to_waypoint",
                "navigate_to_room",
                "navigate_to_receptacle",
                "navigate_to_object",
                "navigate_to_visual_candidate",
                "done",
            ],
        },
        "physical_agibot_pilot": {
            "schema": PHYSICAL_AGIBOT_PILOT_SCHEMA,
            "observation": observation,
            "navigation_attempt": navigation,
            "blocked_manipulation_results": manipulation_results,
        },
        "manipulation_evidence": {
            "schema": "physical_manipulation_block_v1",
            "status": "blocked_capability",
            "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
            "planner_backed": False,
            "strict_proof_eligible": False,
            "api_semantic_state_edits": 0,
            "evidence_note": "First physical AgiBot pilot intentionally blocks manipulation.",
            "blockers": [str(item["tool"]) for item in manipulation_results],
            "strict_proof_requirements": [
                "planner-backed manipulation binding",
                "operator safety approval",
                "hardware pick/place validation",
            ],
        },
        "artifacts": {
            "run_result": "run_result.json",
            "trace": "trace.jsonl",
            "before_snapshot": "before.png",
            "after_snapshot": "after.png",
            "report": "report.html",
            "agibot_subphases": "subphases",
        },
        "runtime_timing": {
            "total_elapsed_s": time.time() - started_at,
            "tool_handler_s": 0.0,
            "robot_view_capture_s": 0.0,
            "between_tool_gap_s": 0.0,
            "tool_call_count": len(trace_events) // 2,
        },
    }
    if nav2_map_bundle:
        run_result["artifacts"]["map_bundle"] = "map_bundle"
        run_result["artifacts"]["nav2_map_yaml"] = "map_bundle/map.yaml"
        run_result["artifacts"]["nav2_occupancy_image"] = "map_bundle/map.pgm"
        run_result["artifacts"]["nav2_map_preview"] = "map_bundle/preview.png"
    (run_dir / "run_result.json").write_text(
        json.dumps(run_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_cleanup_report(
        run_dir=run_dir,
        scenario=scenario,
        run_result=run_result,
        trace_events=trace_events,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        robot_view_steps=[],
    )
    return run_result


def _readiness_payload(
    *,
    context: dict[str, Any],
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    observation: dict[str, Any],
    navigation: dict[str, Any],
    manipulation_results: list[dict[str, Any]],
    real_movement_enabled: bool,
) -> dict[str, Any]:
    all_manipulation_blocked = all(
        item.get("primitive_provenance") == BLOCKED_CAPABILITY_PROVENANCE
        and item.get("physical_cleanup_ready") is False
        for item in manipulation_results
    )
    navigation_complete = bool(navigation.get("ok"))
    observation_complete = bool(observation.get("ok"))
    complete = bool(navigation_complete and observation_complete and all_manipulation_blocked)
    backend = str(navigation.get("navigation_backend") or BLOCKED_CAPABILITY_PROVENANCE)
    pose_source = str(navigation.get("pose_source") or "")
    localization_gate = _operator_localization_gate(context)
    run_gate = _operator_run_enablement_gate(context, movement_enabled=real_movement_enabled)
    return {
        "schema": "real_robot_readiness_v1",
        "status": "physical_agibot_navigation_pilot_complete"
        if complete
        else "physical_agibot_navigation_pilot_rehearsal",
        "real_robot_ready": False,
        "navigation_perception_ready": complete,
        "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
        "movement_enabled": real_movement_enabled,
        "map_bundle_schema": metric_map.get("schema", ""),
        "map_bundle_fields_present": _map_fields_present(metric_map),
        "pose_stamped_waypoints": _pose_stamped_waypoints_present(metric_map),
        "static_fixture_semantic_map": (
            fixture_hints.get("schema") == "static_fixture_semantic_map_v1"
            and fixture_hints.get("contains_runtime_observations") is False
        ),
        "policy_view_chase_excluded": True,
        "report_only_simulation_view_count": 0,
        "report_only_simulation_view_label": "not_simulated",
        "navigation_backend_summary": {backend: 1},
        "pose_source_summary": {pose_source: 1} if pose_source else {},
        "semantic_navigation_only": False,
        "sim_costmap_route_validation": False,
        "physical_navigation_pilot": True,
        "physical_cleanup_ready": False,
        "inspection_waypoint_attempt_count": 1,
        "inspection_waypoint_total": len(metric_map.get("inspection_waypoints") or []),
        "fixture_preferred_waypoint_attempt_count": 0,
        "fixture_total": len(_fixtures(fixture_hints)),
        "reached_waypoint_count": 1 if navigation_complete else 0,
        "observed_reached_waypoint_count": 1 if observation_complete else 0,
        "observed_reached_waypoint_rate": 1.0 if complete else 0.0,
        "observed_waypoint_ids": [str(navigation.get("waypoint_id") or "")]
        if observation_complete
        else [],
        "manipulation_blocked": all_manipulation_blocked,
        "blocked_capabilities": list(BLOCKED_MANIPULATION_TOOLS),
        "operator_localization_gate": localization_gate,
        "operator_run_enablement_gate": run_gate,
        "human_takeover_stop": _human_takeover_stop_required(observation, navigation),
        "public_contract_note": (
            "AgiBot Navigation + Perception Pilot: Roboclaws keeps the public "
            "real_robot_cleanup_v1 tools stable while SDK runner artifacts own "
            "backend-specific GDK evidence."
        ),
    }


def _record(
    trace_events: list[dict[str, Any]],
    started_at: float,
    tool: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    elapsed = time.time() - started_at
    trace_events.append(
        {
            "tool": tool,
            "event": "request",
            "arguments": arguments,
            "wallclock_elapsed": elapsed,
        }
    )
    trace_events.append(
        {
            "tool": tool,
            "event": "response",
            "response": response,
            "wallclock_elapsed": time.time() - started_at,
        }
    )


def _policy_event(index: int, response: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "index": index + 1,
        "tool": response.get("tool", ""),
        "role": role,
        "waypoint_id": response.get("waypoint_id", ""),
        "fixture_id": response.get("fixture_id", ""),
        "navigation_backend": response.get("navigation_backend", ""),
        "status": response.get("status") or response.get("navigation_status", ""),
    }


def _subphase_reports(results: list[dict[str, Any]], run_dir: Path) -> list[dict[str, Any]]:
    reports = []
    for result in results:
        report_path = Path(str(result.get("report_path") or ""))
        reports.append(
            {
                "stage": result.get("stage", ""),
                "status": result.get("status", ""),
                "ok": result.get("ok", False),
                "report": _relpath(report_path, run_dir),
                "run_result": _relpath(report_path.with_name("run_result.json"), run_dir),
            }
        )
    return reports


def _fixtures(fixture_hints: dict[str, Any]) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            if isinstance(fixture, dict):
                fixtures.append(fixture)
    return fixtures


def _fixture_by_id(fixture_hints: dict[str, Any], fixture_id: str) -> dict[str, Any] | None:
    for fixture in _fixtures(fixture_hints):
        if str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "") == fixture_id:
            return fixture
    return None


def _preferred_verified_waypoint_id(waypoints: list[dict[str, Any]]) -> str:
    for waypoint in waypoints:
        if str(waypoint.get("reachability_status") or "") == "verified":
            return str(waypoint.get("waypoint_id") or "")
    return ""


def _operator_localization_gate(context: dict[str, Any]) -> dict[str, Any]:
    gate = context.get("operator_localization_gate")
    if not isinstance(gate, dict):
        return {
            "schema": "operator_localization_gate_v1",
            "ok": False,
            "status": "missing",
            "selected_map_confirmed": False,
            "g02_pad_relocalized": False,
            "localization_ready": False,
            "reason": "operator_localization_gate is missing from the AgiBot context.",
        }
    selected_map_confirmed = bool(
        gate.get("selected_map_confirmed")
        or gate.get("map_selected")
        or gate.get("selected_map_confirmed_at")
    )
    g02_pad_relocalized = bool(
        gate.get("g02_pad_relocalized")
        or gate.get("relocalized_on_g02_pad")
        or gate.get("relocalized")
    )
    localization_ready = bool(gate.get("localization_ready") or gate.get("ready"))
    ok = selected_map_confirmed and g02_pad_relocalized and localization_ready
    return {
        "schema": "operator_localization_gate_v1",
        "ok": ok,
        "status": "confirmed" if ok else "incomplete",
        "selected_map_confirmed": selected_map_confirmed,
        "g02_pad_relocalized": g02_pad_relocalized,
        "localization_ready": localization_ready,
        "operator": str(gate.get("operator") or ""),
        "confirmed_at": str(gate.get("confirmed_at") or ""),
        "reason": ""
        if ok
        else "selected map, G02 Pad relocalization, and localization ready are required.",
    }


def _operator_run_enablement_gate(
    context: dict[str, Any],
    *,
    movement_enabled: bool,
) -> dict[str, Any]:
    gate = context.get("operator_run_enablement_gate")
    if not movement_enabled:
        return {
            "schema": "operator_run_enablement_gate_v1",
            "ok": False,
            "status": "not_requested",
            "movement_enabled": False,
            "scope": "session",
            "reason": "real movement was not enabled for this rehearsal.",
        }
    if not isinstance(gate, dict):
        return {
            "schema": "operator_run_enablement_gate_v1",
            "ok": False,
            "status": "missing",
            "movement_enabled": True,
            "scope": "session",
            "reason": "operator_run_enablement_gate is missing from the AgiBot context.",
        }
    enabled = bool(
        gate.get("enabled")
        or gate.get("confirmed")
        or gate.get("autonomous_navigation_enabled")
        or gate.get("run_enabled")
    )
    return {
        "schema": "operator_run_enablement_gate_v1",
        "ok": enabled,
        "status": "confirmed" if enabled else "incomplete",
        "movement_enabled": True,
        "scope": str(gate.get("scope") or "session"),
        "operator": str(gate.get("operator") or ""),
        "confirmed_at": str(gate.get("confirmed_at") or ""),
        "reason": "" if enabled else "operator run enablement was not confirmed.",
    }


def _bounded_local_nudge_status(*, enabled: bool) -> dict[str, Any]:
    return {
        "schema": "agibot_bounded_local_nudge_v1",
        "status": "not_requested",
        "enabled": enabled,
        "primitive_provenance": AGIBOT_GDK_RELATIVE_MOVE_PROVENANCE if enabled else "",
        "safety_model": "Pnc.relative_move simple obstacle stop; no obstacle avoidance",
        "agent_facing_tool": False,
    }


def _human_takeover_stop_required(
    observation: dict[str, Any],
    navigation: dict[str, Any],
) -> bool:
    failure_types = {
        str(observation.get("failure_type") or ""),
        str(navigation.get("failure_type") or ""),
    }
    return bool(
        {"operator_localization_gate_not_confirmed", "operator_run_enablement_gate_not_confirmed"}
        & failure_types
    )


def _map_fields_present(metric_map: dict[str, Any]) -> bool:
    required = {
        "schema",
        "frame_id",
        "resolution_m",
        "origin",
        "width",
        "height",
        "rooms",
        "driveable_ways",
        "inspection_waypoints",
    }
    return required <= set(metric_map)


def _pose_stamped_waypoints_present(metric_map: dict[str, Any]) -> bool:
    waypoints = metric_map.get("inspection_waypoints") or []
    return bool(waypoints) and all(
        {"frame_id", "x", "y", "yaw", "waypoint_id"} <= set(item) for item in waypoints
    )


def _dominant_primitive_provenance(items: list[dict[str, Any]]) -> str:
    if any(item.get("primitive_provenance") == AGIBOT_GDK_NORMAL_NAVI_PROVENANCE for item in items):
        return AGIBOT_GDK_NORMAL_NAVI_PROVENANCE
    if any(
        item.get("primitive_provenance") == AGIBOT_HEAD_COLOR_CAMERA_PROVENANCE for item in items
    ):
        return AGIBOT_HEAD_COLOR_CAMERA_PROVENANCE
    return BLOCKED_CAPABILITY_PROVENANCE


def _first_waypoint_id(metric_map: dict[str, Any]) -> str:
    waypoints = metric_map.get("inspection_waypoints") or []
    if not waypoints:
        raise ValueError("AgiBot agent view does not contain any inspection waypoints")
    return str(waypoints[0].get("waypoint_id") or "")


def _empty_score() -> dict[str, Any]:
    return {
        "restored_count": 0,
        "total_targets": 0,
        "object_results": [],
        "semantic_acceptability": {
            "accepted_count": 0,
            "total_targets": 0,
            "acceptance_rate": 0.0,
        },
    }


def _initial_locations(scenario: CleanupScenario) -> dict[str, str]:
    return {item.object_id: item.location_id for item in scenario.objects}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def _relpath(path: Path | str, root: Path) -> str:
    path = Path(path)
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
