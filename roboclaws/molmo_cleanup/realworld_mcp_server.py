"""FastMCP bridge for the ADR-0003 MolmoSpaces cleanup contract."""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from roboclaws.molmo_cleanup.advisory_scoring import build_advisory_evaluation
from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.realworld_contract import (
    DEFAULT_REALWORLD_TASK,
    RAW_FPV_ONLY_MODE,
    REALWORLD_CONTRACT,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    RealWorldCleanupContract,
)
from roboclaws.molmo_cleanup.report import render_cleanup_report, write_state_snapshot
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.semantic_timeline import (
    ROBOT_VIEW_VARIANT,
    SEMANTIC_LOOP_VARIANT,
    cleanup_plan_from_semantic_substeps,
    primitive_provenance_counts,
    record_robot_view_step,
    semantic_diagnostics,
    semantic_substeps,
)
from roboclaws.molmo_cleanup.types import CleanupScenario

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
    base_contract: MolmoCleanupToolContract | None = None,
    contract: RealWorldCleanupContract | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    policy: str = "realworld_contract_smoke_agent",
    agent_driven: bool | None = None,
    task_prompt: str = DEFAULT_REALWORLD_TASK,
    fixture_hint_mode: str = "room_only",
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    record_robot_views: bool = False,
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
    )


class RealWorldMolmoCleanupMCPServer:
    """FastMCP server wrapping ``RealWorldCleanupContract`` for agent dogfood."""

    def __init__(
        self,
        *,
        run_dir: Path,
        scenario: CleanupScenario | None = None,
        base_contract: MolmoCleanupToolContract | None = None,
        contract: RealWorldCleanupContract | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        policy: str = "realworld_contract_smoke_agent",
        agent_driven: bool | None = None,
        task_prompt: str = DEFAULT_REALWORLD_TASK,
        fixture_hint_mode: str = "room_only",
        perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
        record_robot_views: bool = False,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.host = host
        self.port = int(port)
        self.policy = policy
        self.agent_driven = _default_agent_driven(policy) if agent_driven is None else agent_driven
        self.policy_uses_private_truth = False
        if contract is None:
            scenario = scenario or build_cleanup_scenario()
            base_contract = base_contract or MolmoCleanupToolContract(scenario)
            contract = RealWorldCleanupContract(
                base_contract,
                task_prompt=task_prompt,
                fixture_hint_mode=fixture_hint_mode,
                perception_mode=perception_mode,
            )
        self.contract = contract
        self.base_contract = contract.contract
        self.scenario = contract.scenario
        self.task_prompt = task_prompt
        self.fixture_hint_mode = fixture_hint_mode
        self.perception_mode = contract.perception_mode
        self.record_robot_views = bool(record_robot_views)
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
        self._register_tools()
        self.write_runtime_event(
            "molmo_realworld_cleanup_mcp_initialized",
            contract=REALWORLD_CONTRACT,
            policy=policy,
            agent_driven=self.agent_driven,
            perception_mode=self.perception_mode,
        )

    def _register_tools(self) -> None:
        server = self

        @self._mcp.tool()
        def metric_map() -> dict:
            """Return public room topology and inspection waypoints."""
            return server.call_tool("metric_map")

        @self._mcp.tool()
        def fixture_hints() -> dict:
            """Return room-level public fixture identities and affordances."""
            return server.call_tool("fixture_hints")

        @self._mcp.tool()
        def navigate_to_room(room_id: str) -> dict:
            """Navigate to the first public waypoint in a room."""
            return server.call_tool("navigate_to_room", room_id=room_id)

        @self._mcp.tool()
        def navigate_to_waypoint(waypoint_id: str) -> dict:
            """Navigate to a public inspection waypoint before observing."""
            return server.call_tool("navigate_to_waypoint", waypoint_id=waypoint_id)

        @self._mcp.tool()
        def observe() -> dict:
            """Observe robot-local visible objects at the current waypoint."""
            return server.call_tool("observe")

        @self._mcp.tool()
        def inspect_visible_object(object_id: str) -> dict:
            """Inspect a previously observed object handle."""
            return server.call_tool("inspect_visible_object", object_id=object_id)

        @self._mcp.tool()
        def navigate_to_object(object_id: str) -> dict:
            """Navigate to a previously observed object handle before pick."""
            return server.call_tool("navigate_to_object", object_id=object_id)

        @self._mcp.tool()
        def pick(object_id: str) -> dict:
            """Pick one previously observed object handle."""
            return server.call_tool("pick", object_id=object_id)

        @self._mcp.tool()
        def navigate_to_receptacle(fixture_id: str) -> dict:
            """Navigate to a public fixture before place or place_inside."""
            return server.call_tool("navigate_to_receptacle", fixture_id=fixture_id)

        @self._mcp.tool()
        def open_receptacle(fixture_id: str) -> dict:
            """Open fridge-like public fixtures before place_inside."""
            return server.call_tool("open_receptacle", fixture_id=fixture_id)

        @self._mcp.tool()
        def place(fixture_id: str) -> dict:
            """Place the held object on/at a public fixture."""
            return server.call_tool("place", fixture_id=fixture_id)

        @self._mcp.tool()
        def place_inside(fixture_id: str) -> dict:
            """Place the held object inside an opened public fixture."""
            return server.call_tool("place_inside", fixture_id=fixture_id)

        @self._mcp.tool()
        def done(reason: str) -> dict:
            """Finish the run and write trace, run_result, and report."""
            return server.call_tool("done", reason=reason)

    def call_tool(self, name: str, **kwargs: Any) -> dict[str, Any]:
        if name == "scene_objects":
            raise ValueError("scene_objects is not part of the ADR-0003 real-world MCP contract")
        if self.done_event.is_set() and name != "done":
            return {"ok": False, "tool": name, "status": "error", "error_reason": "run_done"}
        handlers = {
            "metric_map": self.contract.metric_map,
            "fixture_hints": self.contract.fixture_hints,
            "navigate_to_room": lambda: self.contract.navigate_to_room(
                str(kwargs.get("room_id", ""))
            ),
            "navigate_to_waypoint": lambda: self.contract.navigate_to_waypoint(
                str(kwargs.get("waypoint_id", ""))
            ),
            "observe": self.contract.observe,
            "inspect_visible_object": lambda: self.contract.inspect_visible_object(
                str(kwargs.get("object_id", ""))
            ),
            "navigate_to_object": lambda: self.contract.navigate_to_object(
                str(kwargs.get("object_id", ""))
            ),
            "pick": lambda: self.contract.pick(str(kwargs.get("object_id", ""))),
            "navigate_to_receptacle": lambda: self.contract.navigate_to_receptacle(
                str(kwargs.get("fixture_id", ""))
            ),
            "open_receptacle": lambda: self.contract.open_receptacle(
                str(kwargs.get("fixture_id", ""))
            ),
            "place": lambda: self.contract.place(str(kwargs.get("fixture_id", ""))),
            "place_inside": lambda: self.contract.place_inside(str(kwargs.get("fixture_id", ""))),
            "done": lambda: self.contract.done(str(kwargs.get("reason", ""))),
        }
        if name not in handlers:
            raise ValueError(f"unknown Molmo real-world cleanup MCP tool {name!r}")

        request = _json_safe(kwargs)
        self._write_tool_request(name, request)
        try:
            response = handlers[name]()
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

    def _augment_response(
        self,
        tool: str,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:
        augmented = dict(response)
        if tool == "metric_map":
            augmented["instruction"] = (
                "Use inspection_waypoints to sweep rooms. Call navigate_to_waypoint "
                "then observe. Use only observed_* object handles returned by observe."
            )
        if tool == "fixture_hints":
            augmented["instruction"] = (
                "Use room-level fixture ids and affordances as public landmarks. "
                "Acceptable destination sets and target receptacles are private."
            )
        return augmented

    def _finalize_done(self, reason: str, done_response: dict[str, Any]) -> dict[str, Any]:
        if self._done_result is not None:
            return self._done_result

        after_snapshot = self._write_snapshot("after.png", title="After real-world cleanup")
        self._record_robot_view("after", label_suffix="after")
        trace_events = self._read_trace_events()
        substeps = semantic_substeps(trace_events, self.contract.public_receptacles_by_id())
        cleanup_plan = cleanup_plan_from_semantic_substeps(substeps)
        diagnostics = semantic_diagnostics(trace_events, substeps, done_response)
        diagnostics["premature_done"] = done_response["score"].get("sweep_coverage_rate", 0) < 0.90
        diagnostics["premature_done_source"] = "sweep_coverage_rate"
        primitive_counts = primitive_provenance_counts(trace_events)
        agent_view = self.contract.agent_view_payload()
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
        private_evaluation_path = self.run_dir / "private_evaluation.json"
        advisory_evaluation_path = self.run_dir / "advisory_evaluation.json"
        agent_view_path.write_text(json.dumps(agent_view, indent=2, sort_keys=True) + "\n")
        private_evaluation_path.write_text(
            json.dumps(private_evaluation, indent=2, sort_keys=True) + "\n"
        )
        advisory_evaluation_path.write_text(
            json.dumps(advisory_evaluation, indent=2, sort_keys=True) + "\n"
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
            "policy": self.policy,
            "planner": self.policy,
            "agent_driven": self.agent_driven,
            "policy_uses_private_truth": self.policy_uses_private_truth,
            "planner_uses_private_manifest": False,
            "fixture_hint_mode": self.fixture_hint_mode,
            "perception_mode": self.perception_mode,
            "requested_generated_mess_count": requested_count,
            "generated_mess_count": private_evaluation["generated_mess_count"],
            "mcp_server": MCP_SERVER_NAME,
            "mess_restoration_rate": done_response["score"]["mess_restoration_rate"],
            "sweep_coverage_rate": done_response["score"]["sweep_coverage_rate"],
            "disturbance_count": done_response["score"]["disturbance_count"],
            "semantic_loop_variant": SEMANTIC_LOOP_VARIANT,
            "semantic_substeps": substeps,
            "cleanup_plan": cleanup_plan,
            "agent_view": agent_view,
            "raw_fpv_observations": agent_view.get("raw_fpv_observations", []),
            "private_evaluation": private_evaluation,
            "advisory_evaluation": advisory_evaluation,
            "score": done_response["score"],
            "final_locations": done_response["final_locations"],
            "final_containment": done_response.get("final_containment", {}),
            "tool_event_counts": dict(self._tool_event_counts),
            "backend_tool_event_counts": done_response["tool_event_counts"],
            "agent_bridge": diagnostics,
            "artifacts": {
                "agent_view": str(agent_view_path),
                "private_evaluation": str(private_evaluation_path),
                "advisory_evaluation": str(advisory_evaluation_path),
                "trace": str(self.trace_path),
                "before_snapshot": str(self._before_snapshot),
                "after_snapshot": str(after_snapshot),
            },
        }
        _add_backend_runtime_metadata(run_result, self.base_contract.backend)
        if self.robot_view_steps:
            run_result["view_variant"] = ROBOT_VIEW_VARIANT
            run_result["robot_view_steps"] = self.robot_view_steps
            run_result["artifacts"]["robot_views"] = str(self.run_dir / "robot_views")
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
            or self.perception_mode != RAW_FPV_ONLY_MODE
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
            return writer(output_path, title=title)
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
        capture = self._robot_view_capture(tool, request, response)
        if capture is None:
            return
        self._record_robot_view(**capture)

    def _robot_view_capture(
        self,
        tool: str,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, str | None] | None:
        if tool == "navigate_to_object":
            handle = _optional_str(response.get("object_id") or request.get("object_id"))
            return {
                "action": f"navigate_to_object {handle}",
                "label_suffix": _label_suffix("navigate_object", handle),
                "focus_object_id": self._internal_object_id(handle),
                "focus_receptacle_id": _optional_str(
                    response.get("source_receptacle_id") or response.get("location_id")
                ),
                "semantic_phase": "navigate_to_object",
            }
        if tool == "pick":
            handle = _optional_str(response.get("object_id") or request.get("object_id"))
            return {
                "action": f"pick {handle}",
                "label_suffix": _label_suffix("pick", handle),
                "focus_object_id": self._internal_object_id(handle),
                "focus_receptacle_id": _optional_str(
                    response.get("previous_location_id") or response.get("source_receptacle_id")
                ),
                "semantic_phase": "pick",
            }
        if tool == "navigate_to_receptacle":
            handle = _optional_str(response.get("object_id"))
            fixture_id = _optional_str(response.get("fixture_id") or request.get("fixture_id"))
            return {
                "action": f"navigate_to_receptacle {fixture_id}",
                "label_suffix": _label_suffix("navigate_receptacle", fixture_id),
                "focus_object_id": self._internal_object_id(handle),
                "focus_receptacle_id": fixture_id,
                "semantic_phase": "navigate_to_receptacle",
            }
        if tool == "open_receptacle":
            handle = _optional_str(response.get("object_id"))
            fixture_id = _optional_str(response.get("fixture_id") or request.get("fixture_id"))
            return {
                "action": f"open_receptacle {fixture_id}",
                "label_suffix": _label_suffix("open_receptacle", fixture_id),
                "focus_object_id": self._internal_object_id(handle),
                "focus_receptacle_id": fixture_id,
                "semantic_phase": "open_receptacle",
            }
        if tool in {"place", "place_inside"}:
            handle = _optional_str(response.get("object_id"))
            fixture_id = _optional_str(response.get("fixture_id") or request.get("fixture_id"))
            return {
                "action": f"{tool} {handle}",
                "label_suffix": _label_suffix(tool, handle),
                "focus_object_id": self._internal_object_id(handle),
                "focus_receptacle_id": fixture_id,
                "semantic_phase": tool,
            }
        return None

    def _internal_object_id(self, handle: str | None) -> str | None:
        if handle is None:
            return None
        return self.contract._internal_object_id(handle)

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
        self._robot_view_index = record_robot_view_step(
            steps=self.robot_view_steps,
            backend=self.base_contract.backend,
            output_dir=self.run_dir,
            index=self._robot_view_index,
            action=action,
            label_suffix=label_suffix,
            focus_object_id=focus_object_id,
            focus_receptacle_id=focus_receptacle_id,
            semantic_phase=semantic_phase,
        )
        if len(self.robot_view_steps) <= previous_count:
            return None
        return self.robot_view_steps[-1]

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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _add_backend_runtime_metadata(run_result: dict[str, Any], backend: Any) -> None:
    if _backend_name(backend) != "molmospaces_subprocess":
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


def _startup_probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _label_suffix(prefix: str, value: str | None) -> str:
    if not value:
        return prefix
    safe_value = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)
    return f"{prefix}_{safe_value}"
