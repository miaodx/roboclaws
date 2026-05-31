"""FastMCP bridge for the ADR-0003 MolmoSpaces cleanup contract."""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Image as MCPImage

from roboclaws.molmo_cleanup.advisory_scoring import build_advisory_evaluation
from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.backend_contract import CleanupBackendSession
from roboclaws.molmo_cleanup.cleanup_primitive_evidence import (
    cleanup_primitive_evidence_from_substeps,
)
from roboclaws.molmo_cleanup.manipulation_provenance import (
    api_semantic_manipulation_evidence,
)
from roboclaws.molmo_cleanup.nav2_map_bundle import attach_nav2_map_bundle_snapshot
from roboclaws.molmo_cleanup.planner_proof_attachment import attach_planner_proof
from roboclaws.molmo_cleanup.planner_proof_requests import write_planner_proof_requests
from roboclaws.molmo_cleanup.profiles import cleanup_profile_metadata_for_run
from roboclaws.molmo_cleanup.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    DEFAULT_REALWORLD_TASK,
    RAW_FPV_ONLY_MODE,
    REALWORLD_CONTRACT,
    RICH_MAP_MODE,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    RealWorldCleanupContract,
    cleanup_policy_trace_from_events,
    raw_fpv_inline_candidate_instruction,
    real_robot_readiness_from_events,
)
from roboclaws.molmo_cleanup.realworld_mcp_backend import (
    agent_view_public_tool_names,
    dispatch_realworld_mcp_tool,
    register_realworld_mcp_tools,
    validate_realworld_mcp_tool_call,
)
from roboclaws.molmo_cleanup.report import (
    render_cleanup_report,
    runtime_timing_from_trace,
    write_state_snapshot,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.semantic_timeline import (
    ROBOT_VIEW_VARIANT,
    SEMANTIC_LOOP_VARIANT,
    cleanup_plan_from_semantic_substeps,
    primitive_provenance_counts,
    record_robot_view_step,
    robot_view_capture_for_tool,
    semantic_diagnostics,
    semantic_substeps,
)
from roboclaws.molmo_cleanup.skill_scratchpad import read_or_create_skill_scratchpad
from roboclaws.molmo_cleanup.types import CleanupScenario
from roboclaws.molmo_cleanup.visual_grounding import (
    SIM_VISUAL_GROUNDING_PIPELINE_ID,
    visual_grounding_client_from_env,
)

__all__ = ["MCP_SERVER_NAME", "RealWorldMolmoCleanupMCPServer", "make_molmo_realworld_cleanup_mcp"]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18788
STARTUP_TIMEOUT_S = 2.0
MCP_SERVER_NAME = "molmo_cleanup_realworld"
AGENT_POLICIES = {
    "realworld_contract_smoke_agent",
    "codex_agent",
    "claude_code_agent",
    "openclaw_agent",
}


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
    task_prompt: str = DEFAULT_REALWORLD_TASK,
    fixture_hint_mode: str = "room_only",
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    record_robot_views: bool = False,
    cleanup_profile: str | None = None,
    planner_proof_run_result: Path | None = None,
    map_bundle_dir: str | Path | None = None,
    runtime_map_prior: dict[str, Any] | None = None,
    runtime_map_prior_source: str = "",
    map_mode: str = RICH_MAP_MODE,
    visual_grounding: str = SIM_VISUAL_GROUNDING_PIPELINE_ID,
    visual_grounding_base_url: str | None = None,
    visual_grounding_timeout_s: float | None = None,
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
        task_prompt: str = DEFAULT_REALWORLD_TASK,
        fixture_hint_mode: str = "room_only",
        perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
        record_robot_views: bool = False,
        cleanup_profile: str | None = None,
        planner_proof_run_result: Path | None = None,
        map_bundle_dir: str | Path | None = None,
        runtime_map_prior: dict[str, Any] | None = None,
        runtime_map_prior_source: str = "",
        map_mode: str = RICH_MAP_MODE,
        visual_grounding: str = SIM_VISUAL_GROUNDING_PIPELINE_ID,
        visual_grounding_base_url: str | None = None,
        visual_grounding_timeout_s: float | None = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.host = host
        self.port = int(port)
        self.policy = policy
        self.agent_driven = _default_agent_driven(policy) if agent_driven is None else agent_driven
        self.policy_uses_private_truth = False
        self.map_bundle_dir = Path(map_bundle_dir) if map_bundle_dir is not None else None
        self.runtime_map_prior_source = runtime_map_prior_source
        if contract is None:
            scenario = scenario or build_cleanup_scenario()
            base_contract = base_contract or CleanupBackendSession(scenario)
            contract = RealWorldCleanupContract(
                base_contract,
                task_prompt=task_prompt,
                fixture_hint_mode=fixture_hint_mode,
                perception_mode=perception_mode,
                map_bundle_dir=self.map_bundle_dir,
                runtime_map_prior=runtime_map_prior,
                map_mode=map_mode,
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
        self.scenario = contract.scenario
        self.task_prompt = task_prompt
        self.fixture_hint_mode = fixture_hint_mode
        self.perception_mode = contract.perception_mode
        self.record_robot_views = bool(record_robot_views)
        self.cleanup_profile = cleanup_profile
        self.planner_proof_run_result = planner_proof_run_result
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
            perception_mode=self.perception_mode,
            cleanup_profile=self.cleanup_profile,
            visual_grounding_pipeline_id=contract.visual_grounding_pipeline_id,
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
        response = self._attach_raw_fpv_artifact_if_needed(name, response)
        self._write_tool_response(name, response)
        if name == "done" and response.get("ok"):
            return self._finalize_done(str(kwargs.get("reason", "")), response)
        self._record_tool_robot_view(name, request, response)
        return response

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
                "not mess hints. Prefer navigate_to_waypoint -> observe -> clean "
                "visible observed_* candidates before continuing the sweep."
            )
        if tool == "observe" and self.perception_mode == CAMERA_MODEL_POLICY_MODE:
            raw = augmented.get("raw_fpv_observation") or {}
            augmented["instruction"] = (
                "Call declare_visual_candidates with observation_id="
                f"{raw.get('observation_id', '')} before choosing cleanup candidates. "
                "For camera-labels, pass only observation_id and omit candidates so the "
                "configured visual-grounding pipeline produces labels. Service URLs, "
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
                    "Minimal map mode hides authored rooms and fixture hints. Use "
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
                "worklist. For each candidate, call navigate_to_object, pick, "
                "navigate_to_receptacle, then the recommended placement tool."
            )
        if tool in {"place", "place_inside", "close_receptacle"} and augmented.get("ok"):
            augmented["instruction"] = (
                "After placing and closing if needed, call observe once in the current "
                "room/fixture area before choosing the next object or waypoint."
            )
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
        real_robot_readiness = real_robot_readiness_from_events(
            agent_view=agent_view,
            trace_events=trace_events,
            robot_view_steps=self.robot_view_steps,
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

        run_result = {
            "backend": _backend_name(self.base_contract.backend),
            "scenario_id": self.scenario.scenario_id,
            "seed": self.scenario.seed,
            "task_prompt": self.task_prompt,
            "contract": REALWORLD_CONTRACT,
            "adr_0003_satisfied": True,
            "final_status": done_response["cleanup_status"],
            "terminate_reason": reason,
            "cleanup_status": done_response["cleanup_status"],
            "completion_status": done_response["score"]["completion_status"],
            "primitive_provenance": API_SEMANTIC_PROVENANCE,
            "primitive_provenance_summary": primitive_counts,
            "manipulation_evidence": api_semantic_manipulation_evidence(
                backend=_backend_name(self.base_contract.backend),
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
        if self.cleanup_profile is not None:
            profile_metadata = cleanup_profile_metadata_for_run(
                profile_name=self.cleanup_profile,
                backend=_backend_name(self.base_contract.backend),
                perception_mode=self.perception_mode,
                record_robot_views=self.record_robot_views,
            )
            run_result["cleanup_profile"] = profile_metadata["profile"]
            run_result["cleanup_profile_metadata"] = profile_metadata
        attach_nav2_map_bundle_snapshot(
            run_result=run_result,
            run_dir=self.run_dir,
            source_bundle_dir=self.map_bundle_dir,
        )
        _add_backend_runtime_metadata(run_result, self.base_contract.backend)
        if self.robot_view_steps:
            run_result["view_variant"] = ROBOT_VIEW_VARIANT
            run_result["robot_view_steps"] = self.robot_view_steps
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
        )
        if step is None:
            return response
        attached = self.contract.attach_raw_fpv_observation_artifact(
            observation_id,
            views=step.get("views") or {},
            robot_view_label=str(step.get("label", "")),
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
        state_text = json.dumps(response, sort_keys=True)
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
        capture = robot_view_capture_for_tool(
            tool,
            request,
            response,
            object_id_transform=self._internal_object_id,
        )
        if capture is None:
            return
        self._record_robot_view(**capture)

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
        self._write_trace(tool=tool, event="response", response=response)

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
        ),
    )
    support_estimate = item.get("support_estimate")
    if isinstance(support_estimate, dict):
        compact["support_estimate"] = _select_keys(
            support_estimate,
            ("fixture_id", "relation", "confidence", "source", "perception_source"),
        )
    return compact


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


def _backend_name(backend: Any) -> str:
    if backend.__class__.__name__ == "MolmoSpacesSubprocessBackend":
        return "molmospaces_subprocess"
    return "api_semantic_synthetic"


def _resolve_artifact_path(run_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else run_dir / path


def _add_backend_runtime_metadata(run_result: dict[str, Any], backend: Any) -> None:
    if _backend_name(backend) != "molmospaces_subprocess":
        return
    mess_diagnostics = getattr(backend, "mess_placement_diagnostics", None)
    placement_diagnostics = getattr(backend, "placement_diagnostics", None)
    if mess_diagnostics is not None:
        run_result["mess_placement_diagnostics"] = mess_diagnostics
    if placement_diagnostics is not None:
        run_result["placement_diagnostics"] = placement_diagnostics
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


def _startup_probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False
