"""FastMCP bridge for the ADR-0003 MolmoSpaces cleanup contract."""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Image as MCPImage

from roboclaws.household.advisory_scoring import build_advisory_evaluation
from roboclaws.household.backend import API_SEMANTIC_PROVENANCE
from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.cleanup_primitive_evidence import (
    cleanup_primitive_evidence_from_substeps,
)
from roboclaws.household.manipulation_provenance import (
    api_semantic_manipulation_evidence,
)
from roboclaws.household.nav2_map_bundle import attach_nav2_map_bundle_snapshot
from roboclaws.household.planner_proof_attachment import attach_planner_proof
from roboclaws.household.planner_proof_requests import write_planner_proof_requests
from roboclaws.household.profiles import (
    camera_labeler_from_visual_grounding_pipeline,
    cleanup_profile_metadata_for_run,
)
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    DEFAULT_MAP_MODE,
    DEFAULT_REALWORLD_TASK,
    RAW_FPV_ONLY_MODE,
    REALWORLD_CONTRACT,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    RealWorldCleanupContract,
    cleanup_policy_trace_from_events,
    raw_fpv_inline_candidate_instruction,
    real_robot_readiness_from_events,
)
from roboclaws.household.realworld_mcp_backend import (
    agent_view_public_tool_names,
    dispatch_realworld_mcp_tool,
    register_realworld_mcp_tools,
    validate_realworld_mcp_tool_call,
)
from roboclaws.household.report import (
    render_cleanup_report,
    runtime_timing_from_trace,
    write_state_snapshot,
)
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.semantic_timeline import (
    ROBOT_VIEW_VARIANT,
    SEMANTIC_LOOP_VARIANT,
    camera_offsets_from_raw_fpv_observation,
    cleanup_plan_from_semantic_substeps,
    has_complete_semantic_sequence,
    primitive_provenance_counts,
    record_robot_view_step,
    robot_view_camera_control_summary,
    robot_view_capture_for_tool,
    semantic_diagnostics,
    semantic_substeps,
    successful_semantic_phases,
)
from roboclaws.household.skill_scratchpad import read_or_create_skill_scratchpad
from roboclaws.household.task_intent import (
    HOUSEHOLD_INTENT_OPEN_ENDED,
    TASK_INTENT_MODE_DEFAULT,
    household_intent_from_goal_contract,
    normalize_household_intent,
    normalize_task_intent_mode,
)
from roboclaws.household.types import CleanupScenario
from roboclaws.household.visual_grounding import (
    SIM_VISUAL_GROUNDING_PIPELINE_ID,
    visual_grounding_client_from_env,
)
from roboclaws.household.visual_scan_guidance import visual_scan_metric_map_instruction
from roboclaws.launch.environment_setup_metadata import (
    environment_setup_run_metadata_from_env,
)
from roboclaws.launch.goals import (
    GoalContract,
    completion_claim_from_done_reason,
    goal_contract_from_file,
    goal_contract_from_json,
    write_goal_contract,
)
from roboclaws.operator_console.interactions import (
    check_operator_messages_for_mcp,
    pending_operator_message_hint,
)

__all__ = ["MCP_SERVER_NAME", "RealWorldMolmoCleanupMCPServer", "make_molmo_realworld_cleanup_mcp"]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18788
STARTUP_TIMEOUT_S = 2.0
MCP_SERVER_NAME = "molmo_cleanup_realworld"
ROBOT_VIEW_CAPTURE_POLICY_FULL = "full"
ROBOT_VIEW_CAPTURE_POLICY_ACTION_TIMELINE = "action_timeline"
ROBOT_VIEW_CAPTURE_POLICIES = frozenset(
    {ROBOT_VIEW_CAPTURE_POLICY_FULL, ROBOT_VIEW_CAPTURE_POLICY_ACTION_TIMELINE}
)
AGENT_POLICIES = {
    "realworld_contract_smoke_agent",
    "codex_agent",
    "claude_code_agent",
    "openclaw_agent",
}
REPORT_RERUN_COMMAND_ENV = "ROBOCLAWS_REPORT_RERUN_COMMAND"


def make_molmo_realworld_cleanup_mcp(
    *,
    run_dir: Path,
    scenario: CleanupScenario | None = None,
    base_contract: CleanupBackendSession | None = None,
    contract: RealWorldCleanupContract | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    policy: str = "realworld_contract_smoke_agent",
    agent_driven: bool | None = None,
    task_name: str = "household-cleanup",
    task_prompt: str = DEFAULT_REALWORLD_TASK,
    fixture_hint_mode: str = "room_only",
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    record_robot_views: bool = False,
    cleanup_profile: str | None = None,
    planner_proof_run_result: Path | None = None,
    map_bundle_dir: str | Path | None = None,
    runtime_map_prior: dict[str, Any] | None = None,
    runtime_map_prior_source: str = "",
    map_mode: str = DEFAULT_MAP_MODE,
    visual_grounding: str = SIM_VISUAL_GROUNDING_PIPELINE_ID,
    visual_grounding_base_url: str | None = None,
    visual_grounding_timeout_s: float | None = None,
    task_intent_mode: str = TASK_INTENT_MODE_DEFAULT,
    goal_contract: GoalContract | None = None,
    operator_messages_path: str | Path | None = None,
    agent_sdk_camera_grounded_composite_tools: bool = False,
    robot_view_capture_policy: str = ROBOT_VIEW_CAPTURE_POLICY_FULL,
    rerun_command: str | None = None,
) -> "RealWorldMolmoCleanupMCPServer":
    return RealWorldMolmoCleanupMCPServer(
        run_dir=run_dir,
        scenario=scenario,
        base_contract=base_contract,
        contract=contract,
        host=host,
        port=port,
        policy=policy,
        agent_driven=agent_driven,
        task_name=task_name,
        task_prompt=task_prompt,
        fixture_hint_mode=fixture_hint_mode,
        perception_mode=perception_mode,
        record_robot_views=record_robot_views,
        cleanup_profile=cleanup_profile,
        planner_proof_run_result=planner_proof_run_result,
        map_bundle_dir=map_bundle_dir,
        runtime_map_prior=runtime_map_prior,
        runtime_map_prior_source=runtime_map_prior_source,
        map_mode=map_mode,
        visual_grounding=visual_grounding,
        visual_grounding_base_url=visual_grounding_base_url,
        visual_grounding_timeout_s=visual_grounding_timeout_s,
        task_intent_mode=task_intent_mode,
        goal_contract=goal_contract,
        operator_messages_path=operator_messages_path,
        agent_sdk_camera_grounded_composite_tools=agent_sdk_camera_grounded_composite_tools,
        robot_view_capture_policy=robot_view_capture_policy,
        rerun_command=rerun_command,
    )


class RealWorldMolmoCleanupMCPServer:
    """FastMCP server wrapping ``RealWorldCleanupContract`` for agent dogfood."""

    def __init__(
        self,
        *,
        run_dir: Path,
        scenario: CleanupScenario | None = None,
        base_contract: CleanupBackendSession | None = None,
        contract: RealWorldCleanupContract | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        policy: str = "realworld_contract_smoke_agent",
        agent_driven: bool | None = None,
        task_name: str = "household-cleanup",
        task_prompt: str = DEFAULT_REALWORLD_TASK,
        fixture_hint_mode: str = "room_only",
        perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
        record_robot_views: bool = False,
        cleanup_profile: str | None = None,
        planner_proof_run_result: Path | None = None,
        map_bundle_dir: str | Path | None = None,
        runtime_map_prior: dict[str, Any] | None = None,
        runtime_map_prior_source: str = "",
        map_mode: str = DEFAULT_MAP_MODE,
        visual_grounding: str = SIM_VISUAL_GROUNDING_PIPELINE_ID,
        visual_grounding_base_url: str | None = None,
        visual_grounding_timeout_s: float | None = None,
        task_intent_mode: str = TASK_INTENT_MODE_DEFAULT,
        goal_contract: GoalContract | None = None,
        operator_messages_path: str | Path | None = None,
        agent_sdk_camera_grounded_composite_tools: bool = False,
        robot_view_capture_policy: str = ROBOT_VIEW_CAPTURE_POLICY_FULL,
        rerun_command: str | None = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.host = host
        self.port = int(port)
        self.policy = policy
        self.task_name = task_name
        self.agent_driven = _default_agent_driven(policy) if agent_driven is None else agent_driven
        self.policy_uses_private_truth = False
        self.task_intent_mode = normalize_task_intent_mode(task_intent_mode)
        self.goal_contract = goal_contract or _goal_contract_from_env()
        self.task_intent = household_intent_from_goal_contract(
            self.goal_contract,
            fallback=HOUSEHOLD_INTENT_OPEN_ENDED
            if self.task_intent_mode != TASK_INTENT_MODE_DEFAULT
            else "",
        )
        self.map_bundle_dir = Path(map_bundle_dir) if map_bundle_dir is not None else None
        self.runtime_map_prior_source = runtime_map_prior_source
        if contract is None:
            scenario = scenario or build_cleanup_scenario()
            base_contract = base_contract or CleanupBackendSession(scenario)
            acceptance_config = _public_acceptance_config_from_backend(base_contract)
            acceptance_config["task_intent"] = self.task_intent
            if self.task_intent_mode != TASK_INTENT_MODE_DEFAULT:
                acceptance_config["task_intent_mode"] = self.task_intent_mode
            contract = RealWorldCleanupContract(
                base_contract,
                task_prompt=task_prompt,
                fixture_hint_mode=fixture_hint_mode,
                perception_mode=perception_mode,
                map_bundle_dir=self.map_bundle_dir,
                runtime_map_prior=runtime_map_prior,
                map_mode=map_mode,
                cleanup_profile=cleanup_profile,
                public_acceptance_config=acceptance_config,
                visual_grounding_client=visual_grounding_client_from_env(
                    visual_grounding,
                    base_url=visual_grounding_base_url,
                    timeout_s=visual_grounding_timeout_s,
                ),
                visual_grounding_pipeline_id=visual_grounding,
                visual_grounding_artifact_base_dir=self.run_dir,
                visual_grounding_run_id=f"seed-{scenario.seed if scenario else 'run'}",
            )
        self.contract = contract
        self.base_contract = contract.contract
        backend_name = getattr(contract, "backend_name", None)
        self.backend_name = str(backend_name()) if callable(backend_name) else ""
        self.scenario = contract.scenario
        self.task_prompt = task_prompt
        self.task_intent_mode = normalize_task_intent_mode(
            getattr(contract, "task_intent_mode", self.task_intent_mode)
        )
        self.task_intent = normalize_household_intent(
            getattr(contract, "task_intent", self.task_intent),
            task_name=self.task_name,
        )
        self.fixture_hint_mode = fixture_hint_mode
        self.perception_mode = contract.perception_mode
        self.record_robot_views = bool(record_robot_views)
        self.cleanup_profile = cleanup_profile
        self.planner_proof_run_result = planner_proof_run_result
        self.operator_messages_path = (
            Path(operator_messages_path) if operator_messages_path is not None else None
        )
        self.agent_sdk_camera_grounded_composite_tools = bool(
            agent_sdk_camera_grounded_composite_tools
        )
        self.robot_view_capture_policy = _normalize_robot_view_capture_policy(
            robot_view_capture_policy
        )
        self.rerun_command = (
            str(rerun_command or "").strip() or os.environ.get(REPORT_RERUN_COMMAND_ENV, "").strip()
        )
        if self.record_robot_views and not callable(
            getattr(self.base_contract.backend, "write_robot_views", None)
        ):
            raise ValueError("record_robot_views requires a backend with write_robot_views")

        self.trace_path = self.run_dir / "trace.jsonl"
        self.run_result_path = self.run_dir / "run_result.json"
        self.done_event = threading.Event()
        self.robot_view_steps: list[dict[str, Any]] = []
        self._robot_view_index = 0
        self._started_at = time.time()
        self._trace_fp = self.trace_path.open("a", encoding="utf-8", buffering=1)
        self._trace_lock = threading.Lock()
        self._tool_event_counts: dict[str, int] = {}
        self._server_thread: threading.Thread | None = None
        self._closed = False
        self._done_result: dict[str, Any] | None = None

        self._before_snapshot = self._write_snapshot(
            "before.png", title="Before real-world cleanup"
        )
        self._record_robot_view("before", label_suffix="before")
        self._mcp = FastMCP("roboclaws", host=host, port=self.port)
        register_realworld_mcp_tools(self)
        self.write_runtime_event(
            "molmo_realworld_cleanup_mcp_initialized",
            contract=REALWORLD_CONTRACT,
            policy=policy,
            agent_driven=self.agent_driven,
            task_intent=self.task_intent,
            task_intent_mode=self.task_intent_mode,
            goal_contract=self.goal_contract.to_payload() if self.goal_contract is not None else {},
            perception_mode=self.perception_mode,
            cleanup_profile=self.cleanup_profile,
            visual_grounding_pipeline_id=contract.visual_grounding_pipeline_id,
            agent_sdk_camera_grounded_composite_tools=(
                self.agent_sdk_camera_grounded_composite_tools
            ),
            robot_view_capture_policy=self.robot_view_capture_policy,
        )

    def call_tool(self, name: str, **kwargs: Any) -> dict[str, Any]:
        validate_realworld_mcp_tool_call(self, name)
        request = _json_safe(kwargs)
        self._write_tool_request(name, request)
        try:
            response = dispatch_realworld_mcp_tool(self, name, kwargs)
        except Exception as exc:
            response = {
                "ok": False,
                "tool": name,
                "status": "error",
                "error_reason": "exception",
                "error": str(exc),
            }
        response = self._augment_response(name, request, response)
        if name != "check_operator_messages":
            response = self._attach_operator_message_hint(response)
        response = self._attach_raw_fpv_artifact_if_needed(name, response)
        self._write_tool_response(name, response)
        if name == "done" and response.get("ok"):
            return self._finalize_done(str(kwargs.get("reason", "")), response)
        self._record_tool_robot_view(name, request, response)
        return response

    def check_operator_messages(self, max_messages: int = 10) -> dict[str, Any]:
        path = self.operator_messages_path
        run_dir = path.parent if path is not None else self.run_dir
        return check_operator_messages_for_mcp(run_dir, max_messages=max(1, max_messages))

    def observe_camera_grounded_candidates(self) -> dict[str, Any]:
        if self.perception_mode != CAMERA_MODEL_POLICY_MODE:
            return {
                "ok": False,
                "tool": "observe_camera_grounded_candidates",
                "status": "error",
                "error_reason": "unsupported_perception_mode",
                "perception_mode": self.perception_mode,
                "supported_perception_mode": CAMERA_MODEL_POLICY_MODE,
            }
        observation = self.call_tool("observe")
        if not observation.get("ok"):
            return {
                "ok": False,
                "tool": "observe_camera_grounded_candidates",
                "status": "error",
                "error_reason": "observe_failed",
                "observation": observation,
                "private_target_truth_included": False,
            }
        raw = observation.get("raw_fpv_observation")
        raw = raw if isinstance(raw, dict) else {}
        observation_id = str(raw.get("observation_id") or "")
        if not observation_id:
            return {
                "ok": False,
                "tool": "observe_camera_grounded_candidates",
                "status": "error",
                "error_reason": "missing_raw_fpv_observation",
                "observation": observation,
                "private_target_truth_included": False,
            }
        declaration = self.call_tool("declare_visual_candidates", observation_id=observation_id)
        return {
            "ok": bool(declaration.get("ok")),
            "tool": "observe_camera_grounded_candidates",
            "status": declaration.get("status", "ok" if declaration.get("ok") else "error"),
            "contract": REALWORLD_CONTRACT,
            "perception_mode": self.perception_mode,
            "observation_id": observation_id,
            "waypoint_id": observation.get("waypoint_id", raw.get("waypoint_id", "")),
            "room_id": observation.get("current_room_id", raw.get("room_id", "")),
            "observation": observation,
            "declaration": declaration,
            "candidate_count": declaration.get("candidate_count", 0),
            "registered_observed_handles": list(
                declaration.get("registered_observed_handles") or []
            ),
            "camera_model_candidates": list(declaration.get("camera_model_candidates") or []),
            "model_declared_observations": list(
                declaration.get("model_declared_observations") or []
            ),
            "visual_grounding_pipeline": declaration.get("visual_grounding_pipeline") or {},
            "private_target_truth_included": False,
            "trace_review_note": (
                "Composite shortcut for private Agent SDK Candidate O. It preserves the "
                "underlying observe and declare_visual_candidates trace events."
            ),
            "instruction": declaration.get("instruction", ""),
        }

    def done_readiness_evidence(self) -> dict[str, Any]:
        trace_events = self._read_trace_events()
        substeps = semantic_substeps(trace_events, self.contract.public_receptacles_by_id())
        complete_handles = _complete_semantic_substep_handles(substeps)
        return {
            "schema": "public_semantic_cleanup_evidence_v1",
            "complete_semantic_substep_objects": len(complete_handles),
            "complete_semantic_substep_object_ids": complete_handles,
            "semantic_substep_count": len(substeps),
            "evidence_source": "public_mcp_trace_semantic_substeps",
        }

    def _agent_view_payload(self) -> dict[str, Any]:
        agent_view = self.contract.agent_view_payload()
        agent_view["public_tool_names"] = agent_view_public_tool_names(
            self,
            list(agent_view.get("public_tool_names") or []),
        )
        return agent_view

    def _augment_response(
        self,
        tool: str,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:
        augmented = dict(response)
        if tool == "metric_map":
            augmented["instruction"] = (
                "inspection_waypoints are static map/fixture coverage candidates, "
                f"not mess hints. Prefer navigate_to_waypoint -> observe. "
                f"{visual_scan_metric_map_instruction()}"
            )
        if tool == "observe" and self.perception_mode == CAMERA_MODEL_POLICY_MODE:
            raw = augmented.get("raw_fpv_observation") or {}
            augmented["instruction"] = (
                "Call declare_visual_candidates with observation_id="
                f"{raw.get('observation_id', '')} before choosing cleanup candidates. "
                "For camera-grounded-labels, pass only observation_id and omit "
                "candidates so the configured camera labeler produces labels. Service URLs, "
                "credentials, and image paths are server-side details."
            )
        if tool == "observe" and self.perception_mode == RAW_FPV_ONLY_MODE:
            raw = augmented.get("raw_fpv_observation") or {}
            augmented["instruction"] = raw_fpv_inline_candidate_instruction(
                str(raw.get("observation_id") or "")
            )
        if tool == "fixture_hints":
            if self.contract.map_mode == "minimal":
                augmented["instruction"] = (
                    "Base Navigation Map exposes public room labels but hides fixture hints. Use "
                    "runtime_metric_map.public_semantic_anchors and each observed object's "
                    "cleanup_worklist.candidate_fixture_id as public destination anchors. "
                    "Those anchor_fixture_* ids are valid for navigate_to_receptacle, place, "
                    "place_inside, open_receptacle, and close_receptacle. Acceptable "
                    "destination sets and generated mess truth are private."
                )
            else:
                augmented["instruction"] = (
                    "Use room-level fixture ids and affordances as static public landmarks. "
                    "Runtime movable objects come only from observe; acceptable destination "
                    "sets and generated mess truth are private."
                )
        if tool == "declare_visual_candidates" and augmented.get("ok"):
            augmented = _compact_declare_visual_candidates_response(augmented)
            augmented["instruction"] = (
                "Use camera_model_candidates with cleanup_recommended=true as the actionable "
                "worklist only when candidate_state is navigation_authorized. For each "
                "authorized candidate, call navigate_to_object, pick, navigate_to_receptacle, "
                "then the recommended placement tool."
            )
        if tool in {"place", "place_inside", "close_receptacle"} and augmented.get("ok"):
            augmented["instruction"] = (
                "After placing and closing if needed, call observe once in the current "
                "room/fixture area before choosing the next object or waypoint."
            )
        return augmented

    def _attach_operator_message_hint(self, response: dict[str, Any]) -> dict[str, Any]:
        path = self.operator_messages_path
        run_dir = path.parent if path is not None else self.run_dir
        hint = pending_operator_message_hint(run_dir)
        if not hint:
            return response
        augmented = dict(response)
        augmented.update(hint)
        return augmented

    def _finalize_done(self, reason: str, done_response: dict[str, Any]) -> dict[str, Any]:
        if self._done_result is not None:
            return self._done_result

        after_snapshot = self._write_snapshot("after.png", title="After real-world cleanup")
        self._record_robot_view("after", label_suffix="after")
        trace_events = self._read_trace_events()
        runtime_timing = runtime_timing_from_trace(trace_events, self.robot_view_steps)
        substeps = semantic_substeps(trace_events, self.contract.public_receptacles_by_id())
        cleanup_primitive_evidence = cleanup_primitive_evidence_from_substeps(substeps)
        cleanup_plan = cleanup_plan_from_semantic_substeps(substeps)
        planner_proof_requests_path = self.run_dir / "planner_proof_requests.json"
        planner_proof_requests = write_planner_proof_requests(
            output_path=planner_proof_requests_path,
            contract=self.contract,
            substeps=substeps,
        )
        diagnostics = semantic_diagnostics(trace_events, substeps, done_response)
        diagnostics["premature_done"] = done_response["score"].get("sweep_coverage_rate", 0) < 0.90
        diagnostics["premature_done_source"] = "sweep_coverage_rate"
        primitive_counts = primitive_provenance_counts(trace_events)
        agent_view = self._agent_view_payload()
        cleanup_policy_trace = cleanup_policy_trace_from_events(trace_events, agent_view)
        readiness_hook = getattr(self.contract, "real_robot_readiness_payload", None)
        real_robot_readiness = (
            readiness_hook(trace_events)
            if callable(readiness_hook)
            else real_robot_readiness_from_events(
                agent_view=agent_view,
                trace_events=trace_events,
                robot_view_steps=self.robot_view_steps,
            )
        )
        private_evaluation = self.contract.private_evaluation_payload(done_response["score"])
        requested_count = getattr(
            self.base_contract.backend,
            "requested_generated_mess_count",
            private_evaluation["generated_mess_count"],
        )
        private_evaluation["requested_generated_mess_count"] = requested_count
        advisory_evaluation = build_advisory_evaluation(
            score=done_response["score"],
            scenario_id=self.scenario.scenario_id,
        )
        agent_view_path = self.run_dir / "agent_view.json"
        runtime_metric_map_path = self.run_dir / "runtime_metric_map.json"
        private_evaluation_path = self.run_dir / "private_evaluation.json"
        advisory_evaluation_path = self.run_dir / "advisory_evaluation.json"
        goal_contract_path = self.run_dir / "goal_contract.json"
        goal_contract_payload: dict[str, Any] = {}
        completion_claim: dict[str, Any] = {}
        if self.goal_contract is not None:
            write_goal_contract(goal_contract_path, self.goal_contract)
            goal_contract_payload = self.goal_contract.to_payload()
            completion_claim = completion_claim_from_done_reason(
                reason,
                goal_contract=self.goal_contract,
            )
        runtime_metric_map = agent_view.get("runtime_metric_map", {})
        runtime_prior_rows = [
            item
            for item in runtime_metric_map.get("observed_objects", [])
            if item.get("freshness") == "prior"
        ]
        agent_view_path.write_text(json.dumps(agent_view, indent=2, sort_keys=True) + "\n")
        runtime_metric_map_path.write_text(
            json.dumps(runtime_metric_map, indent=2, sort_keys=True) + "\n"
        )
        private_evaluation_path.write_text(
            json.dumps(private_evaluation, indent=2, sort_keys=True) + "\n"
        )
        advisory_evaluation_path.write_text(
            json.dumps(advisory_evaluation, indent=2, sort_keys=True) + "\n"
        )
        agent_scratchpad, agent_scratchpad_path = read_or_create_skill_scratchpad(
            run_dir=self.run_dir,
            note=(
                "No live cleanup_scratch.json was present when the MCP server finalized; "
                "cleanup_worklist remains authoritative."
            ),
        )
        task_intent = normalize_household_intent(
            goal_contract_payload.get("intent") or self.task_intent,
            task_name=self.task_name,
        )
        terminal_status = (
            "success" if task_intent == "open-ended" else done_response["cleanup_status"]
        )
        intent_status = terminal_status

        run_result = {
            "backend": _backend_name(self.base_contract.backend, override=self.backend_name),
            "task_name": self.task_name,
            "scenario_id": self.scenario.scenario_id,
            "seed": self.scenario.seed,
            "task_prompt": self.task_prompt,
            "task_surface": goal_contract_payload.get("surface", "household-world"),
            "task_intent": task_intent,
            "goal_contract": goal_contract_payload,
            "agent_completion_claim": completion_claim,
            "contract": REALWORLD_CONTRACT,
            "adr_0003_satisfied": True,
            "final_status": terminal_status,
            "intent_status": intent_status,
            "goal_status": intent_status,
            "cleanup_status_role": "advisory" if task_intent == "open-ended" else "terminal",
            "terminate_reason": reason,
            "cleanup_status": done_response["cleanup_status"],
            "completion_status": done_response["score"]["completion_status"],
            "primitive_provenance": API_SEMANTIC_PROVENANCE,
            "primitive_provenance_summary": primitive_counts,
            "manipulation_evidence": api_semantic_manipulation_evidence(
                backend=_backend_name(self.base_contract.backend, override=self.backend_name),
                primitive_summary=primitive_counts,
            ),
            "policy": self.policy,
            "planner": self.policy,
            "agent_driven": self.agent_driven,
            "policy_uses_private_truth": self.policy_uses_private_truth,
            "planner_uses_private_manifest": False,
            "fixture_hint_mode": self.fixture_hint_mode,
            "perception_mode": self.perception_mode,
            "map_mode": runtime_metric_map.get("map_mode", self.contract.map_mode),
            "minimal_map_mode": runtime_metric_map.get("minimal_map_mode", False),
            "runtime_metric_map_prior": {
                "loaded": bool(runtime_prior_rows),
                "source": self.runtime_map_prior_source,
                "observed_object_count": len(runtime_prior_rows),
            },
            "camera_labeler": camera_labeler_from_visual_grounding_pipeline(
                self.contract.visual_grounding_pipeline_id
            )
            if self.perception_mode == CAMERA_MODEL_POLICY_MODE
            else "",
            "visual_grounding_pipeline_id": self.contract.visual_grounding_pipeline_id,
            "requested_generated_mess_count": requested_count,
            "generated_mess_count": private_evaluation["generated_mess_count"],
            "mcp_server": MCP_SERVER_NAME,
            "mess_restoration_rate": done_response["score"]["mess_restoration_rate"],
            "sweep_coverage_rate": done_response["score"]["sweep_coverage_rate"],
            "disturbance_count": done_response["score"]["disturbance_count"],
            "semantic_loop_variant": SEMANTIC_LOOP_VARIANT,
            "semantic_substeps": substeps,
            "cleanup_primitive_evidence": cleanup_primitive_evidence,
            "planner_proof_requests": planner_proof_requests,
            "cleanup_plan": cleanup_plan,
            "cleanup_policy_trace": cleanup_policy_trace,
            "real_robot_readiness": real_robot_readiness,
            "agent_view": agent_view,
            "runtime_metric_map": runtime_metric_map,
            "raw_fpv_observations": agent_view.get("raw_fpv_observations", []),
            "camera_model_policy_evidence": agent_view.get("camera_model_policy_evidence", {}),
            "model_declared_observations": agent_view.get("model_declared_observations", []),
            "model_declared_observation_evidence": agent_view.get(
                "model_declared_observation_evidence",
                {},
            ),
            "agent_scratchpad": agent_scratchpad,
            "private_evaluation": private_evaluation,
            "advisory_evaluation": advisory_evaluation,
            "score": done_response["score"],
            "final_locations": done_response["final_locations"],
            "final_containment": done_response.get("final_containment", {}),
            "tool_event_counts": dict(self._tool_event_counts),
            "backend_tool_event_counts": done_response["tool_event_counts"],
            "runtime_timing": runtime_timing,
            "agent_diagnostics": diagnostics,
            "rerun_command": self.rerun_command,
            "artifacts": {
                "agent_view": str(agent_view_path),
                "runtime_metric_map": str(runtime_metric_map_path),
                "private_evaluation": str(private_evaluation_path),
                "advisory_evaluation": str(advisory_evaluation_path),
                "agent_scratchpad": str(agent_scratchpad_path),
                "planner_proof_requests": str(planner_proof_requests_path),
                "trace": str(self.trace_path),
                "before_snapshot": str(self._before_snapshot),
                "after_snapshot": str(after_snapshot),
            },
        }
        if self.goal_contract is not None:
            run_result["artifacts"]["goal_contract"] = str(goal_contract_path)
        if self.cleanup_profile is not None:
            profile_metadata = cleanup_profile_metadata_for_run(
                profile_name=self.cleanup_profile,
                backend=_backend_name(self.base_contract.backend, override=self.backend_name),
                perception_mode=self.perception_mode,
                record_robot_views=self.record_robot_views,
                camera_labeler=camera_labeler_from_visual_grounding_pipeline(
                    self.contract.visual_grounding_pipeline_id
                )
                if self.perception_mode == CAMERA_MODEL_POLICY_MODE
                else None,
            )
            run_result["evidence_lane"] = profile_metadata["evidence_lane"]
            run_result["cleanup_profile"] = profile_metadata["evidence_lane"]
            run_result["cleanup_profile_metadata"] = profile_metadata
        run_metadata = environment_setup_run_metadata_from_env()
        override_hook = getattr(self.contract, "run_result_overrides", None)
        if callable(override_hook):
            run_metadata = _merge_run_metadata(run_metadata, override_hook())
        if run_metadata:
            run_result = _merge_run_metadata(run_result, run_metadata)
        attach_nav2_map_bundle_snapshot(
            run_result=run_result,
            run_dir=self.run_dir,
            source_bundle_dir=self.map_bundle_dir,
        )
        _add_backend_runtime_metadata(run_result, self.base_contract.backend)
        if self.robot_view_steps:
            run_result["view_variant"] = ROBOT_VIEW_VARIANT
            run_result["robot_view_steps"] = self.robot_view_steps
            run_result["robot_view_capture_policy"] = self.robot_view_capture_policy
            run_result["robot_view_camera_control"] = robot_view_camera_control_summary(
                self.robot_view_steps
            )
            run_result["artifacts"]["robot_views"] = str(self.run_dir / "robot_views")
        if self.planner_proof_run_result is not None:
            run_result["planner_backed_manipulation_proof"] = attach_planner_proof(
                proof_run_result_path=self.planner_proof_run_result,
                cleanup_run_dir=self.run_dir,
            )
            run_result["artifacts"]["planner_proof_views"] = str(self.run_dir / "planner_proof")
        report_path = render_cleanup_report(
            run_dir=self.run_dir,
            scenario=self.scenario,
            run_result=run_result,
            trace_events=trace_events,
            before_snapshot=self._before_snapshot,
            after_snapshot=after_snapshot,
            robot_view_steps=self.robot_view_steps,
        )
        run_result["artifacts"]["report"] = str(report_path)
        self.run_result_path.write_text(
            json.dumps(run_result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._done_result = {
            "ok": True,
            "tool": "done",
            "status": "ok",
            "intent_status": intent_status,
            "goal_status": intent_status,
            "cleanup_status": done_response["cleanup_status"],
            "score": done_response["score"],
            "run_result": str(self.run_result_path),
            "report": str(report_path),
            "contract": REALWORLD_CONTRACT,
            "agent_driven": self.agent_driven,
        }
        self.done_event.set()
        self.write_runtime_event(
            "molmo_realworld_cleanup_mcp_done",
            cleanup_status=done_response["cleanup_status"],
            restored_count=done_response["score"]["restored_count"],
            total_targets=done_response["score"]["total_targets"],
        )
        return self._done_result

    def _attach_raw_fpv_artifact_if_needed(
        self,
        tool: str,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        if (
            tool != "observe"
            or self.perception_mode not in {RAW_FPV_ONLY_MODE, CAMERA_MODEL_POLICY_MODE}
            or not response.get("ok")
            or not self.record_robot_views
        ):
            return response
        raw = response.get("raw_fpv_observation")
        if not isinstance(raw, dict):
            return response
        observation_id = str(raw.get("observation_id", ""))
        if not observation_id:
            return response
        step = self._record_robot_view(
            f"observe {observation_id}",
            label_suffix=observation_id,
            **camera_offsets_from_raw_fpv_observation(raw),
        )
        if step is None:
            return response
        attached = self.contract.attach_raw_fpv_observation_artifact(
            observation_id,
            views=step.get("views") or {},
            robot_view_label=str(step.get("label", "")),
            camera_control_contract=step.get("camera_control_contract")
            if isinstance(step.get("camera_control_contract"), dict)
            else None,
        )
        if attached is None:
            return response
        updated = dict(response)
        updated["raw_fpv_observation"] = attached
        return updated

    def _mcp_observe_response(self) -> dict[str, Any] | list[Any]:
        response = self.call_tool("observe")
        if (
            self.perception_mode != RAW_FPV_ONLY_MODE
            or not response.get("ok")
            or not self.record_robot_views
        ):
            return response
        raw = response.get("raw_fpv_observation") or {}
        image_artifacts = raw.get("image_artifacts") or {}
        fpv_path = image_artifacts.get("fpv") or raw.get("fpv_image")
        if not fpv_path:
            return response
        resolved = _resolve_artifact_path(self.run_dir, str(fpv_path))
        if not resolved.is_file():
            return response
        state_text = json.dumps(
            _compact_raw_fpv_mcp_observe_state(
                response,
                cleanup_worklist=self.contract.cleanup_worklist_payload(),
            ),
            sort_keys=True,
        )
        return [state_text, MCPImage(data=resolved.read_bytes(), format="png")]

    def write_runtime_event(self, event: str, **data: Any) -> None:
        self._write_trace(tool="<runtime>", event=event, **data)

    def run_in_thread(self) -> threading.Thread:
        if self._server_thread is not None and self._server_thread.is_alive():
            return self._server_thread
        thread = threading.Thread(
            target=self._mcp.run,
            kwargs={"transport": "streamable-http"},
            name=f"molmo-realworld-cleanup-mcp-{self.port}",
            daemon=True,
        )
        thread.start()
        self._server_thread = thread
        if self.port == 0:
            return thread

        probe_host = _startup_probe_host(self.host)
        deadline = time.monotonic() + STARTUP_TIMEOUT_S
        while time.monotonic() < deadline:
            if not thread.is_alive():
                address = f"{self.host}:{self.port}"
                raise RuntimeError(
                    f"Molmo real-world cleanup MCP server failed to start on {address}"
                )
            if _port_accepting(probe_host, self.port):
                return thread
            time.sleep(0.05)
        raise RuntimeError(
            f"Molmo real-world cleanup MCP server did not become ready on {self.host}:{self.port}"
        )

    def close(self) -> None:
        if self._closed:
            return
        try:
            shutdown = getattr(self._mcp, "shutdown", None)
            if callable(shutdown):
                shutdown()
        except Exception:
            pass
        backend_close = getattr(self.base_contract.backend, "close", None)
        if callable(backend_close):
            try:
                backend_close()
            except Exception:
                pass
        with self._trace_lock:
            self._closed = True
            try:
                self._trace_fp.close()
            except Exception:
                pass
        if self._server_thread is not None:
            self._server_thread.join(timeout=0.5)

    def _write_snapshot(self, filename: str, *, title: str) -> Path:
        output_path = self.run_dir / filename
        writer = getattr(self.base_contract.backend, "write_snapshot", None)
        if callable(writer):
            try:
                return writer(output_path, title=title)
            except Exception as exc:
                self.write_runtime_event(
                    "snapshot_capture_failed",
                    filename=filename,
                    error=str(exc),
                    fallback="state_snapshot",
                )
        return write_state_snapshot(
            self.scenario,
            self.base_contract.backend.object_locations(),
            output_path,
            title=title,
        )

    def _record_tool_robot_view(
        self,
        tool: str,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        if not self.record_robot_views or not response.get("ok"):
            return
        if not self._should_record_tool_robot_view(tool):
            self.write_runtime_event(
                "robot_view_capture_skipped",
                skipped_tool=tool,
                policy=self.robot_view_capture_policy,
                reason="report_only_observation",
            )
            return
        capture = robot_view_capture_for_tool(
            tool,
            request,
            response,
            object_id_transform=self._internal_object_id,
        )
        if capture is None:
            return
        self._record_robot_view(**capture)

    def _should_record_tool_robot_view(self, tool: str) -> bool:
        if self.robot_view_capture_policy == ROBOT_VIEW_CAPTURE_POLICY_FULL:
            return True
        if self.robot_view_capture_policy == ROBOT_VIEW_CAPTURE_POLICY_ACTION_TIMELINE:
            return tool not in {"observe", "scene_objects"}
        raise ValueError(
            f"unsupported robot_view_capture_policy '{self.robot_view_capture_policy}'"
        )

    def _internal_object_id(self, handle: str | None) -> str | None:
        if handle is None:
            return None
        return self.contract._internal_object_id(handle)

    def _internal_fixture_id(self, fixture_id: str | None) -> str | None:
        return self.contract.internal_fixture_id_for_public_reference(fixture_id)

    def _record_robot_view(
        self,
        action: str,
        *,
        label_suffix: str,
        focus_object_id: str | None = None,
        focus_receptacle_id: str | None = None,
        semantic_phase: str | None = None,
        action_evidence: dict[str, Any] | None = None,
        camera_yaw_offset_deg: float = 0.0,
        camera_pitch_offset_deg: float = 0.0,
    ) -> dict[str, Any] | None:
        if not self.record_robot_views:
            return None
        writer = getattr(self.base_contract.backend, "write_robot_views", None)
        if not callable(writer):
            raise RuntimeError("robot view capture requires backend.write_robot_views")
        previous_count = len(self.robot_view_steps)
        capture_started = time.monotonic()
        try:
            self._robot_view_index = record_robot_view_step(
                steps=self.robot_view_steps,
                backend=self.base_contract.backend,
                output_dir=self.run_dir,
                index=self._robot_view_index,
                action=action,
                label_suffix=label_suffix,
                focus_object_id=focus_object_id,
                focus_receptacle_id=self._internal_fixture_id(focus_receptacle_id),
                semantic_phase=semantic_phase,
                action_evidence=action_evidence,
                camera_yaw_offset_deg=camera_yaw_offset_deg,
                camera_pitch_offset_deg=camera_pitch_offset_deg,
            )
        except Exception as exc:
            self.write_runtime_event(
                "robot_view_capture_failed",
                action=action,
                label_suffix=label_suffix,
                elapsed_s=round(time.monotonic() - capture_started, 6),
                error=str(exc),
            )
            return None
        if len(self.robot_view_steps) <= previous_count:
            return None
        capture_elapsed_s = round(time.monotonic() - capture_started, 6)
        step = self.robot_view_steps[-1]
        step["capture_elapsed_s"] = capture_elapsed_s
        self.write_runtime_event(
            "robot_view_capture",
            action=action,
            label=step.get("label", ""),
            elapsed_s=capture_elapsed_s,
        )
        return step

    def _write_tool_request(self, tool: str, request: dict[str, Any]) -> None:
        self._tool_event_counts[f"{tool}:request"] = (
            self._tool_event_counts.get(f"{tool}:request", 0) + 1
        )
        self._write_trace(tool=tool, event="request", request=request)

    def _write_tool_response(self, tool: str, response: dict[str, Any]) -> None:
        self._tool_event_counts[f"{tool}:response"] = (
            self._tool_event_counts.get(f"{tool}:response", 0) + 1
        )
        trace_response = response
        if tool == "observe" and self.perception_mode == RAW_FPV_ONLY_MODE:
            trace_response = dict(response)
            trace_response["agent_facing_compact_state"] = _compact_raw_fpv_mcp_observe_state(
                response,
                cleanup_worklist=self.contract.cleanup_worklist_payload(),
            )
        self._write_trace(tool=tool, event="response", response=trace_response)

    def _write_trace(self, *, tool: str, event: str, **payload: Any) -> None:
        trace_event = {
            "ts": time.time(),
            "wallclock_elapsed": round(time.time() - self._started_at, 6),
            "tool": tool,
            "event": event,
            **_json_safe(payload),
        }
        line = json.dumps(trace_event, sort_keys=True)
        with self._trace_lock:
            if self._closed:
                return
            self._trace_fp.write(line + "\n")
            self._trace_fp.flush()

    def _read_trace_events(self) -> list[dict[str, Any]]:
        with self._trace_lock:
            self._trace_fp.flush()
        return [
            json.loads(line)
            for line in self.trace_path.read_text(encoding="utf-8").splitlines()
            if line
        ]


def _compact_declare_visual_candidates_response(response: dict[str, Any]) -> dict[str, Any]:
    evidence = response.get("model_declared_observation_evidence") or {}
    declarations = list(response.get("model_declared_observations") or [])
    candidates = list(response.get("camera_model_candidates") or [])
    pipeline = evidence.get("visual_grounding_pipeline") or {}
    if not pipeline:
        for item in declarations:
            candidate_pipeline = item.get("visual_grounding_pipeline")
            if isinstance(candidate_pipeline, dict) and candidate_pipeline:
                pipeline = candidate_pipeline
                break

    return {
        "ok": response.get("ok", True),
        "tool": response.get("tool", "declare_visual_candidates"),
        "status": response.get("status", "ok"),
        "contract": response.get("contract", REALWORLD_CONTRACT),
        "observation_id": evidence.get("observation_id", ""),
        "waypoint_id": evidence.get("waypoint_id", ""),
        "room_id": evidence.get("room_id", ""),
        "producer_type": evidence.get("producer_type", ""),
        "producer_id": evidence.get("producer_id", ""),
        "candidate_count": evidence.get("candidate_count", len(declarations)),
        "registered_observed_handles": list(evidence.get("registered_observed_handles") or []),
        "visual_grounding_pipeline": _compact_visual_grounding_pipeline(pipeline),
        "model_declared_observations": [
            _compact_model_declared_observation(item) for item in declarations
        ],
        "camera_model_candidates": [_compact_camera_model_candidate(item) for item in candidates],
        "visible_object_detections": [],
        "private_target_truth_included": False,
    }


def _complete_semantic_substep_handles(substeps: list[dict[str, Any]]) -> list[str]:
    handles = []
    for item in substeps:
        phases = successful_semantic_phases(item.get("steps", []))
        if has_complete_semantic_sequence(phases):
            handles.append(str(item.get("object_id") or ""))
    return [handle for handle in handles if handle]


def _compact_visual_grounding_pipeline(pipeline: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(pipeline, dict):
        return {}
    compact = _select_keys(
        pipeline,
        (
            "schema",
            "pipeline_id",
            "status",
            "candidate_count",
            "unresolved_count",
            "duplicate_rate",
            "failure_reason",
            "failure_message",
            "auth_mode",
        ),
    )
    compact["stages"] = [
        _select_keys(
            stage,
            ("stage", "status", "producer_id", "model_id", "latency_ms", "version"),
        )
        for stage in pipeline.get("stages") or []
        if isinstance(stage, dict)
    ]
    return compact


def _compact_model_declared_observation(item: dict[str, Any]) -> dict[str, Any]:
    compact = _select_keys(
        item,
        (
            "declaration_id",
            "object_id",
            "source_observation_id",
            "waypoint_id",
            "room_id",
            "category",
            "target_fixture_id",
            "target_fixture_category",
            "source_fixture_id",
            "evidence_note",
            "image_region",
            "confidence",
            "producer_type",
            "producer_id",
            "grounding_status",
            "grounding_confidence",
            "grounding_basis",
            "recovery_hint",
            "actionability_status",
            "visual_grounding_evidence",
            "visual_grounding_destination_hint",
            "image_dimensions",
            "visual_grounding_overlay",
        ),
    )
    target_plausibility = item.get("target_plausibility")
    if isinstance(target_plausibility, dict):
        compact["target_plausibility"] = _select_keys(
            target_plausibility,
            ("status", "basis", "expected_fixture_id"),
        )
    return compact


def _compact_camera_model_candidate(item: dict[str, Any]) -> dict[str, Any]:
    compact = _select_keys(
        item,
        (
            "object_id",
            "category",
            "name",
            "current_room_id",
            "visibility_confidence",
            "image_bbox",
            "perception_source",
            "producer_type",
            "producer_id",
            "source_observation_id",
            "candidate_source",
            "candidate_fixture_id",
            "candidate_fixture_category",
            "cleanup_recommended",
            "recommended_tool",
            "model_declared_observation_id",
            "image_region",
            "evidence_note",
            "grounding_status",
            "grounding_confidence",
            "grounding_basis",
            "actionability_status",
            "visual_grounding_evidence",
        ),
    )
    support_estimate = item.get("support_estimate")
    if isinstance(support_estimate, dict):
        compact["support_estimate"] = _select_keys(
            support_estimate,
            ("fixture_id", "relation", "confidence", "source", "perception_source"),
        )
    return compact


def _compact_raw_fpv_mcp_observe_state(
    response: dict[str, Any],
    *,
    cleanup_worklist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = response.get("raw_fpv_observation") if isinstance(response, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    return {
        "schema": "raw_fpv_mcp_observe_state_v1",
        "ok": response.get("ok"),
        "tool": response.get("tool"),
        "status": response.get("status"),
        "contract": response.get("contract"),
        "perception_mode": response.get("perception_mode"),
        "waypoint_id": response.get("waypoint_id") or raw.get("waypoint_id"),
        "current_room_id": response.get("current_room_id") or raw.get("room_id"),
        "held_object_id": response.get("held_object_id") or raw.get("held_object_id"),
        "visible_object_detections": response.get("visible_object_detections") or [],
        "raw_fpv_observation": _compact_raw_fpv_observation(raw),
        "cleanup_worklist_summary": _compact_cleanup_worklist_summary(cleanup_worklist),
        "instruction": response.get("instruction"),
    }


def _compact_raw_fpv_observation(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "observation_id": raw.get("observation_id"),
        "waypoint_id": raw.get("waypoint_id"),
        "room_id": raw.get("room_id"),
        "held_object_id": raw.get("held_object_id"),
        "perception_mode": raw.get("perception_mode"),
        "structured_detections_available": raw.get("structured_detections_available"),
        "camera_offset": raw.get("camera_offset"),
        "image_artifacts": raw.get("image_artifacts") or {},
        "artifact_status": raw.get("artifact_status"),
        "robot_view_label": raw.get("robot_view_label"),
        "public_contract_note": raw.get("public_contract_note"),
        "camera_control_summary": _compact_camera_control_contract(
            raw.get("camera_control_contract")
        ),
    }


def _compact_camera_control_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        return {
            "schema": "robot_view_camera_control_contract_summary_v1",
            "status": "missing_camera_control_contract",
            "same_pose_api": False,
        }
    agent_facing_fpv = contract.get("agent_facing_fpv")
    agent_facing_fpv = agent_facing_fpv if isinstance(agent_facing_fpv, dict) else {}
    return {
        "schema": "robot_view_camera_control_contract_summary_v1",
        "contract_schema": contract.get("schema"),
        "status": contract.get("status"),
        "camera_model": contract.get("camera_model"),
        "same_pose_api": contract.get("same_pose_api") is True,
        "agent_facing_fpv_source": agent_facing_fpv.get("source"),
        "canonical_camera_control": agent_facing_fpv.get("canonical_camera_control") is True,
    }


def _normalize_robot_view_capture_policy(value: str) -> str:
    policy = str(value or ROBOT_VIEW_CAPTURE_POLICY_FULL).strip() or ROBOT_VIEW_CAPTURE_POLICY_FULL
    if policy not in ROBOT_VIEW_CAPTURE_POLICIES:
        allowed = ", ".join(sorted(ROBOT_VIEW_CAPTURE_POLICIES))
        raise ValueError(f"unsupported robot_view_capture_policy '{value}' (expected {allowed})")
    return policy


def _compact_cleanup_worklist_summary(worklist: dict[str, Any] | None) -> dict[str, Any]:
    worklist = worklist if isinstance(worklist, dict) else {}
    objects = [item for item in worklist.get("objects") or [] if isinstance(item, dict)]
    next_actions = _compact_worklist_next_actions(objects)
    return {
        "schema": "cleanup_worklist_summary_v1",
        "object_count": len(objects),
        "handled_object_handles": [
            str(item.get("object_id") or "")
            for item in objects
            if str(item.get("state") or "") in {"placed", "placed_closed", "skipped"}
        ],
        "pending_object_handles": [
            str(item.get("object_id") or "")
            for item in objects
            if str(item.get("state") or "") == "pending"
        ],
        "objects": [_compact_worklist_object(item) for item in objects],
        "next_actions": next_actions,
        "next_action_count": len(next_actions),
        "held_object_id": worklist.get("held_object_id"),
    }


def _compact_worklist_next_actions(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = []
    for item in objects:
        state = str(item.get("state") or "")
        object_id = str(item.get("object_id") or "")
        candidate_fixture_id = str(item.get("candidate_fixture_id") or "")
        if (
            state not in {"pending", "navigating_to_object", "held"}
            or not object_id
            or not candidate_fixture_id
            or not bool(item.get("cleanup_recommended"))
        ):
            continue
        recommended_tool = str(item.get("recommended_tool") or "place")
        if state == "held":
            tool_sequence = ["navigate_to_receptacle", recommended_tool]
        elif state == "navigating_to_object":
            tool_sequence = ["pick", "navigate_to_receptacle", recommended_tool]
        else:
            tool_sequence = [
                "navigate_to_object",
                "pick",
                "navigate_to_receptacle",
                recommended_tool,
            ]
        actions.append(
            {
                "object_id": object_id,
                "category": str(item.get("category") or ""),
                "candidate_fixture_id": candidate_fixture_id,
                "recommended_tool": recommended_tool,
                "state": state,
                "tool_sequence": tool_sequence,
                "source": "cleanup_worklist_summary",
            }
        )
    return actions


def _compact_worklist_object(item: dict[str, Any]) -> dict[str, Any]:
    return _select_keys(
        item,
        (
            "object_id",
            "state",
            "category",
            "room_id",
            "last_waypoint_id",
            "candidate_fixture_id",
            "candidate_source",
            "actionability_status",
            "cleanup_recommended",
            "recommended_tool",
            "visual_grounding_evidence",
        ),
    )


def _select_keys(source: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: source[key] for key in keys if key in source}


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(item) for item in value]
        return str(value)


def _default_agent_driven(policy: str) -> bool:
    return policy in AGENT_POLICIES or policy.endswith("_agent")


def _backend_name(backend: Any, *, override: str = "") -> str:
    if override:
        return override
    if backend.__class__.__name__ == "MolmoSpacesSubprocessBackend":
        return "molmospaces_subprocess"
    if backend.__class__.__name__ == "IsaacLabSubprocessBackend":
        return "isaaclab_subprocess"
    return "api_semantic_synthetic"


def _public_acceptance_config_from_backend(
    base_contract: CleanupBackendSession | None,
) -> dict[str, int]:
    if base_contract is None:
        return {}
    backend = getattr(base_contract, "backend", None)
    requested = getattr(backend, "requested_generated_mess_count", None)
    try:
        requested_run_size = int(requested)
    except (TypeError, ValueError):
        return {}
    if requested_run_size <= 0:
        return {}
    return {"requested_run_size": requested_run_size}


def _resolve_artifact_path(run_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else run_dir / path


def _goal_contract_from_env() -> GoalContract | None:
    path = os.environ.get("ROBOCLAWS_GOAL_CONTRACT_PATH", "")
    if path:
        return goal_contract_from_file(path)
    payload = os.environ.get("ROBOCLAWS_GOAL_CONTRACT_JSON", "")
    if payload:
        return goal_contract_from_json(payload)
    return None


def _add_backend_runtime_metadata(run_result: dict[str, Any], backend: Any) -> None:
    backend_name = _backend_name(backend)
    if backend_name not in {"molmospaces_subprocess", "isaaclab_subprocess"}:
        return
    mess_diagnostics = getattr(backend, "mess_placement_diagnostics", None)
    placement_diagnostics = getattr(backend, "placement_diagnostics", None)
    if mess_diagnostics is not None:
        run_result["mess_placement_diagnostics"] = mess_diagnostics
    if placement_diagnostics is not None:
        run_result["placement_diagnostics"] = placement_diagnostics
    if backend_name == "isaaclab_subprocess":
        scene_index_payload = {}
        scene_index_artifact = getattr(backend, "scene_index_artifact_payload", None)
        if callable(scene_index_artifact):
            scene_index_payload = scene_index_artifact()
        run_result["isaac_runtime"] = {
            "python_executable": str(getattr(backend, "python_executable", "")),
            "runtime": getattr(backend, "runtime", {}),
            "scene_usd": getattr(backend, "scene_usd", ""),
            "scene_load": getattr(backend, "scene_load", {}),
            "scene_index": getattr(backend, "scene_index", None),
            "scenario_source": getattr(backend, "scenario_source", ""),
            "object_index": getattr(backend, "object_index", {}),
            "receptacle_index": getattr(backend, "receptacle_index", {}),
            "scene_index_diagnostics": getattr(backend, "scene_index_diagnostics", {}),
            "scene_binding_diagnostics": getattr(backend, "scene_binding_diagnostics", {}),
            "mapping_gaps": getattr(backend, "current_mapping_gaps", []),
            "segmentation": getattr(backend, "segmentation", {}),
            "requested_generated_mess_count": getattr(
                backend,
                "requested_generated_mess_count",
                None,
            ),
            "generated_mess_count": getattr(backend, "generated_mess_count", None),
            "semantic_pose_state": getattr(backend, "semantic_pose_state", {}),
            "semantic_pose_view_capture": getattr(backend, "semantic_pose_view_capture", {}),
            "snapshot_artifacts": getattr(backend, "snapshot_artifacts", []),
        }
        if scene_index_payload:
            run_result["isaac_runtime"]["scene_index_artifact_payload"] = scene_index_payload
        return
    run_result["molmospaces_runtime"] = {
        "python_executable": str(getattr(backend, "python_executable", "")),
        "runtime": getattr(backend, "runtime", {}),
        "model_stats": getattr(backend, "model_stats", {}),
        "scene_xml": getattr(backend, "scene_xml", ""),
        "metadata_object_count": getattr(backend, "metadata_object_count", None),
        "requested_generated_mess_count": getattr(backend, "requested_generated_mess_count", None),
        "generated_mess_count": getattr(backend, "generated_mess_count", None),
    }
    robot = getattr(backend, "robot", None)
    if robot is not None:
        run_result["robot"] = robot
        run_result["robot_name"] = robot.get("robot_name")


def _merge_run_metadata(
    run_result: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(run_result)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _startup_probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False
