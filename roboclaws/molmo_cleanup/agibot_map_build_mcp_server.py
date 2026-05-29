from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from roboclaws.molmo_cleanup.agibot_sdk_runner import (
    AGIBOT_GDK_BACKEND_VARIANT,
    AGIBOT_SDK_RUNNER_BACKEND,
    BLOCKED_MANIPULATION_TOOLS,
    AgibotSDKRunnerAdapter,
)
from roboclaws.molmo_cleanup.nav2_adapter import BLOCKED_CAPABILITY_PROVENANCE
from roboclaws.molmo_cleanup.realworld_contract import REALWORLD_CONTRACT
from roboclaws.molmo_cleanup.report import render_cleanup_report, write_state_snapshot
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.types import CleanupScenario

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18788
STARTUP_TIMEOUT_S = 2.0
MCP_SERVER_NAME = "agibot_semantic_map_build"
AGIBOT_SEMANTIC_MAP_BUILD_SCHEMA = "agibot_semantic_map_build_mcp_v1"
AGIBOT_SEMANTIC_MAP_BUILD_POLICY = "codex_agibot_semantic_map_build_pilot"
DEFAULT_TASK_PROMPT = "Build a semantic map from Agibot G2 public navigation and camera evidence."
AGIBOT_SEMANTIC_MAP_BUILD_TOOLS = (
    "metric_map",
    "fixture_hints",
    "navigate_to_room",
    "navigate_to_waypoint",
    "navigate_to_receptacle",
    "navigate_to_object",
    "navigate_to_visual_candidate",
    "observe",
    "adjust_camera",
    *BLOCKED_MANIPULATION_TOOLS,
    "done",
)


def make_agibot_semantic_map_build_mcp(
    *,
    run_dir: Path,
    context_json: Path,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    policy: str = AGIBOT_SEMANTIC_MAP_BUILD_POLICY,
    task_prompt: str = DEFAULT_TASK_PROMPT,
    runner_script: Path | None = None,
    runner_python: str | Path | None = None,
    real_movement_enabled: bool = False,
    agibot_map_artifact_dir: Path | None = None,
    scenario: CleanupScenario | None = None,
) -> "AgibotSemanticMapBuildMCPServer":
    return AgibotSemanticMapBuildMCPServer(
        run_dir=run_dir,
        context_json=context_json,
        host=host,
        port=port,
        policy=policy,
        task_prompt=task_prompt,
        runner_script=runner_script,
        runner_python=runner_python,
        real_movement_enabled=real_movement_enabled,
        agibot_map_artifact_dir=agibot_map_artifact_dir,
        scenario=scenario,
    )


class AgibotSemanticMapBuildMCPServer:
    """FastMCP bridge for Agibot-backed semantic-map-build pilot runs."""

    def __init__(
        self,
        *,
        run_dir: Path,
        context_json: Path,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        policy: str = AGIBOT_SEMANTIC_MAP_BUILD_POLICY,
        task_prompt: str = DEFAULT_TASK_PROMPT,
        runner_script: Path | None = None,
        runner_python: str | Path | None = None,
        real_movement_enabled: bool = False,
        agibot_map_artifact_dir: Path | None = None,
        scenario: CleanupScenario | None = None,
    ) -> None:
        self.run_dir = Path(run_dir).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.context_json = Path(context_json).resolve()
        self.host = host
        self.port = port
        self.policy = policy
        self.task_prompt = task_prompt
        self.real_movement_enabled = bool(real_movement_enabled)
        self.scenario = scenario or build_cleanup_scenario(seed=7)
        self.adapter = AgibotSDKRunnerAdapter(
            context_json=self.context_json,
            run_dir=self.run_dir,
            runner_script=runner_script,
            runner_python=runner_python,
            real_movement_enabled=self.real_movement_enabled,
            agibot_map_artifact_dir=agibot_map_artifact_dir,
        )
        self.trace_path = self.run_dir / "trace.jsonl"
        self.run_result_path = self.run_dir / "run_result.json"
        self._started_at = time.time()
        self._trace_fp = self.trace_path.open("a", encoding="utf-8", buffering=1)
        self._trace_lock = threading.Lock()
        self._server_thread: threading.Thread | None = None
        self._closed = False
        self._done_result: dict[str, Any] | None = None
        self.done_event = threading.Event()
        self._mcp = FastMCP("roboclaws", host=host, port=port)
        self._before_snapshot = write_state_snapshot(
            self.scenario,
            _initial_locations(self.scenario),
            self.run_dir / "before.png",
            title="Before Agibot semantic map build",
        )
        self._register_tools()
        self.write_runtime_event(
            "agibot_semantic_map_build_mcp_initialized",
            contract=REALWORLD_CONTRACT,
            policy=self.policy,
            backend_variant=AGIBOT_GDK_BACKEND_VARIANT,
            real_movement_enabled=self.real_movement_enabled,
        )

    def _register_tools(self) -> None:
        @self._mcp.tool()
        def metric_map() -> dict:
            """Return the backend-agnostic Agibot metric map projection."""
            return self.call_tool("metric_map")

        @self._mcp.tool()
        def fixture_hints() -> dict:
            """Return public fixture hints derived from Agibot map context."""
            return self.call_tool("fixture_hints")

        @self._mcp.tool()
        def navigate_to_room(room_id: str) -> dict:
            """Navigate to a verified public waypoint for a room."""
            return self.call_tool("navigate_to_room", room_id=room_id)

        @self._mcp.tool()
        def navigate_to_waypoint(waypoint_id: str) -> dict:
            """Navigate to a verified public Agibot waypoint."""
            return self.call_tool("navigate_to_waypoint", waypoint_id=waypoint_id)

        @self._mcp.tool()
        def navigate_to_receptacle(fixture_id: str) -> dict:
            """Navigate to a fixture-preferred waypoint without claiming manipulation."""
            return self.call_tool("navigate_to_receptacle", fixture_id=fixture_id)

        @self._mcp.tool()
        def navigate_to_object(
            object_id: str,
            waypoint_id: str = "",
            fixture_id: str = "",
        ) -> dict:
            """Navigate to a public waypoint associated with an object when available."""
            return self.call_tool(
                "navigate_to_object",
                object_id=object_id,
                waypoint_id=waypoint_id,
                fixture_id=fixture_id,
            )

        @self._mcp.tool()
        def navigate_to_visual_candidate(
            source_observation_id: str,
            candidate_id: str = "",
            waypoint_id: str = "",
            fixture_id: str = "",
            target_fixture_id: str = "",
        ) -> dict:
            """Navigate to a grounded visual candidate when a public waypoint resolves."""
            return self.call_tool(
                "navigate_to_visual_candidate",
                source_observation_id=source_observation_id,
                candidate_id=candidate_id,
                waypoint_id=waypoint_id,
                fixture_id=fixture_id,
                target_fixture_id=target_fixture_id,
            )

        @self._mcp.tool()
        def observe() -> dict:
            """Capture or rehearse robot-local head_color policy observation."""
            return self.call_tool("observe")

        @self._mcp.tool()
        def adjust_camera(yaw_delta_deg: float = 0.0, pitch_delta_deg: float = 0.0) -> dict:
            """Report bounded camera adjustment as blocked until G2 control is proven."""
            return self.call_tool(
                "adjust_camera",
                yaw_delta_deg=yaw_delta_deg,
                pitch_delta_deg=pitch_delta_deg,
            )

        @self._mcp.tool()
        def pick(object_id: str = "") -> dict:
            """Blocked during Agibot semantic-map-build pilot."""
            return self.call_tool("pick", object_id=object_id)

        @self._mcp.tool()
        def place(fixture_id: str = "") -> dict:
            """Blocked during Agibot semantic-map-build pilot."""
            return self.call_tool("place", fixture_id=fixture_id)

        @self._mcp.tool()
        def place_inside(fixture_id: str = "") -> dict:
            """Blocked during Agibot semantic-map-build pilot."""
            return self.call_tool("place_inside", fixture_id=fixture_id)

        @self._mcp.tool()
        def open_receptacle(fixture_id: str = "") -> dict:
            """Blocked during Agibot semantic-map-build pilot."""
            return self.call_tool("open_receptacle", fixture_id=fixture_id)

        @self._mcp.tool()
        def close_receptacle(fixture_id: str = "") -> dict:
            """Blocked during Agibot semantic-map-build pilot."""
            return self.call_tool("close_receptacle", fixture_id=fixture_id)

        @self._mcp.tool()
        def done(reason: str) -> dict:
            """Finish the Agibot semantic-map-build pilot and write report artifacts."""
            return self.call_tool("done", reason=reason)

    @property
    def registered_tool_names(self) -> tuple[str, ...]:
        return AGIBOT_SEMANTIC_MAP_BUILD_TOOLS

    def call_tool(self, name: str, **kwargs: Any) -> dict[str, Any]:
        if name not in AGIBOT_SEMANTIC_MAP_BUILD_TOOLS:
            raise ValueError(f"unknown Agibot semantic-map-build MCP tool {name!r}")
        if self.done_event.is_set() and name != "done":
            return {"ok": False, "tool": name, "status": "error", "error_reason": "run_done"}
        request = _json_safe(kwargs)
        self._write_trace(tool=name, event="request", arguments=request)
        try:
            response = self._dispatch_tool(name, request)
        except Exception as exc:  # noqa: BLE001
            response = {
                "ok": False,
                "tool": name,
                "status": "error",
                "error_reason": "exception",
                "error": str(exc),
            }
        response = _json_safe(response)
        self._write_trace(tool=name, event="response", response=response)
        if name == "done" and response.get("ok"):
            self.done_event.set()
        return response

    def _dispatch_tool(self, name: str, request: dict[str, Any]) -> dict[str, Any]:
        if name == "metric_map":
            response = dict(self.adapter.metric_map())
            response["instruction"] = (
                "Use only public inspection_waypoints. Navigate to each selected waypoint, "
                "then call observe. Do not invent coordinates or read Agibot map source."
            )
            return response
        if name == "fixture_hints":
            return dict(self.adapter.fixture_hints())
        if name == "navigate_to_room":
            return self.adapter.navigate_to_room(room_id=str(request.get("room_id") or ""))
        if name == "navigate_to_waypoint":
            return self.adapter.navigate_to_waypoint(
                waypoint_id=str(request.get("waypoint_id") or "")
            )
        if name == "navigate_to_receptacle":
            return self.adapter.navigate_to_fixture_preferred_waypoint(
                fixture_id=str(request.get("fixture_id") or "")
            )
        if name == "navigate_to_object":
            return self.adapter.navigate_to_object(
                object_id=str(request.get("object_id") or ""),
                waypoint_id=str(request.get("waypoint_id") or ""),
                fixture_id=str(request.get("fixture_id") or ""),
            )
        if name == "navigate_to_visual_candidate":
            return self.adapter.navigate_to_visual_candidate(
                source_observation_id=str(request.get("source_observation_id") or ""),
                candidate_id=str(request.get("candidate_id") or ""),
                waypoint_id=str(request.get("waypoint_id") or ""),
                fixture_id=str(request.get("fixture_id") or ""),
                target_fixture_id=str(request.get("target_fixture_id") or ""),
            )
        if name == "observe":
            return self.adapter.observe(label=f"semantic_map_build_{self._observe_count() + 1}")
        if name == "adjust_camera":
            return _blocked_response(
                "adjust_camera",
                "agibot_camera_motion_unproven",
                (
                    "Agibot G2 camera adjustment is intentionally blocked until "
                    "bounded control is proven."
                ),
            )
        if name in BLOCKED_MANIPULATION_TOOLS:
            return self.adapter.blocked_manipulation(tool=name)
        if name == "done":
            return self._finalize_done(reason=str(request.get("reason") or ""))
        raise AssertionError(f"unhandled Agibot semantic-map-build tool {name!r}")

    def _finalize_done(self, *, reason: str) -> dict[str, Any]:
        if self._done_result is not None:
            return self._done_result
        after_snapshot = write_state_snapshot(
            self.scenario,
            _initial_locations(self.scenario),
            self.run_dir / "after.png",
            title="After Agibot semantic map build",
        )
        trace_events = self._read_trace_events()
        metric_map = self.adapter.metric_map()
        fixture_hints = self.adapter.fixture_hints()
        policy_events = _policy_events_from_trace(trace_events, metric_map)
        readiness = _readiness_from_trace(
            trace_events=trace_events,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
            real_movement_enabled=self.real_movement_enabled,
        )
        run_result = {
            "schema": AGIBOT_SEMANTIC_MAP_BUILD_SCHEMA,
            "contract": REALWORLD_CONTRACT,
            "cleanup_profile": "real_robot_cleanup_v1",
            "backend": AGIBOT_SDK_RUNNER_BACKEND,
            "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
            "policy": self.policy,
            "planner": self.policy,
            "agent_driven": True,
            "mcp_server": MCP_SERVER_NAME,
            "scenario_id": self.scenario.scenario_id,
            "task_prompt": self.task_prompt,
            "seed": self.scenario.seed,
            "cleanup_status": readiness["status"],
            "completion_status": readiness["status"],
            "terminate_reason": reason,
            "primitive_provenance": _dominant_provenance(trace_events),
            "generated_mess_count": 0,
            "requested_generated_mess_count": 0,
            "sweep_coverage_rate": readiness["observed_waypoint_rate"],
            "disturbance_count": 0,
            "score": _empty_score(readiness["observed_waypoint_rate"]),
            "private_evaluation": {
                "generated_mess_count": 0,
                "generated_mess_set": [],
                "acceptable_destination_sets": {},
                "mess_restoration_rate": 0.0,
                "sweep_coverage_rate": readiness["observed_waypoint_rate"],
                "disturbance_count": 0,
                "public_contract_note": (
                    "Agibot semantic-map-build does not run private cleanup scoring."
                ),
            },
            "agent_view": {
                "metric_map": metric_map,
                "fixture_hints": fixture_hints,
                "observed_objects": [],
                "raw_fpv_observations": [],
                "perception_mode": "robot_policy_camera",
                "policy_view": {"policy_observation_camera": "head_color"},
                "cleanup_worklist": {"schema": "cleanup_worklist_v1", "objects": []},
                "forbidden_private_fields_absent": True,
                "public_tool_names": list(AGIBOT_SEMANTIC_MAP_BUILD_TOOLS),
            },
            "runtime_metric_map": {
                "schema": "runtime_metric_map_v1",
                "source": "agibot_semantic_map_build_mcp",
                "metric_map": metric_map,
                "fixture_hints": fixture_hints,
                "observed_objects": [],
                "visited_waypoint_ids": readiness["visited_waypoint_ids"],
                "observed_waypoint_ids": readiness["observed_waypoint_ids"],
            },
            "cleanup_policy_trace": {
                "schema": "cleanup_policy_trace_v1",
                "agent_review_kind": "agibot_codex_semantic_map_build_review",
                "agent_reasoning_visible": True,
                "waypoint_source": "agibot_sdk_agent_view_export",
                "loop_style": "codex_agibot_semantic_map_build",
                "total_waypoints": len(metric_map.get("inspection_waypoints") or []),
                "visited_waypoint_count": len(readiness["visited_waypoint_ids"]),
                "observed_waypoint_count": len(readiness["observed_waypoint_ids"]),
                "scan_observe_count": readiness["observe_count"],
                "cleanup_action_count": 0,
                "placed_object_count": 0,
                "post_place_observe_count": 0,
                "post_place_observe_complete": True,
                "first_cleanup_before_full_survey": False,
                "events": policy_events,
                "operator_review_note": (
                    "Agibot semantic-map-build records Codex-visible map, navigation, "
                    "observation, skipped waypoint, and blocked manipulation decisions."
                ),
            },
            "semantic_substeps": [],
            "real_robot_readiness": readiness,
            "agibot_sdk_runner": {
                "schema": "agibot_sdk_runner_boundary_v1",
                "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
                "runner_script": str(self.adapter.runner_script),
                "real_movement_enabled": self.real_movement_enabled,
                "subphase_reports": _subphase_reports(self.adapter.subphase_results, self.run_dir),
                "gdk_imported_by_roboclaws": False,
                "public_tool_boundary": list(AGIBOT_SEMANTIC_MAP_BUILD_TOOLS),
            },
            "manipulation_evidence": {
                "schema": "physical_manipulation_block_v1",
                "status": "blocked_capability",
                "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
                "planner_backed": False,
                "strict_proof_eligible": False,
                "api_semantic_state_edits": 0,
                "evidence_note": (
                    "Agibot semantic-map-build intentionally disables physical manipulation."
                ),
                "blockers": list(BLOCKED_MANIPULATION_TOOLS),
            },
            "artifacts": {
                "run_result": "run_result.json",
                "trace": "trace.jsonl",
                "before_snapshot": "before.png",
                "after_snapshot": "after.png",
                "report": "report.html",
                "agibot_subphases": "subphases",
                "runtime_metric_map": "runtime_metric_map.json",
            },
            "runtime_timing": _runtime_timing(trace_events),
        }
        (self.run_dir / "runtime_metric_map.json").write_text(
            json.dumps(run_result["runtime_metric_map"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report_path = render_cleanup_report(
            run_dir=self.run_dir,
            scenario=self.scenario,
            run_result=run_result,
            trace_events=trace_events,
            before_snapshot=self._before_snapshot,
            after_snapshot=after_snapshot,
            robot_view_steps=[],
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
            "cleanup_status": run_result["cleanup_status"],
            "run_result": str(self.run_result_path),
            "report": str(report_path),
            "contract": REALWORLD_CONTRACT,
            "agent_driven": True,
        }
        return self._done_result

    def write_runtime_event(self, event: str, **data: Any) -> None:
        self._write_trace(tool="<runtime>", event=event, **data)

    def run_in_thread(self) -> threading.Thread:
        if self._server_thread is not None and self._server_thread.is_alive():
            return self._server_thread
        thread = threading.Thread(
            target=self._mcp.run,
            kwargs={"transport": "streamable-http"},
            name=f"agibot-semantic-map-build-mcp-{self.port}",
            daemon=True,
        )
        thread.start()
        self._server_thread = thread
        if self.port == 0:
            return thread
        deadline = time.monotonic() + STARTUP_TIMEOUT_S
        probe_host = "127.0.0.1" if self.host in {"0.0.0.0", "::"} else self.host
        while time.monotonic() < deadline:
            if not thread.is_alive():
                raise RuntimeError(
                    f"Agibot semantic-map-build MCP server failed on {self.host}:{self.port}"
                )
            if _port_accepting(probe_host, self.port):
                return thread
            time.sleep(0.05)
        raise RuntimeError(
            f"Agibot semantic-map-build MCP server did not start on {self.host}:{self.port}"
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

    def _observe_count(self) -> int:
        return sum(
            1
            for event in self._read_trace_events()
            if event.get("tool") == "observe" and event.get("event") == "response"
        )

    def _write_trace(self, *, tool: str, event: str, **data: Any) -> None:
        payload = {
            "ts": time.time(),
            "wallclock_elapsed": time.time() - self._started_at,
            "tool": tool,
            "event": event,
            **_json_safe(data),
        }
        with self._trace_lock:
            self._trace_fp.write(json.dumps(payload, sort_keys=True) + "\n")
            self._trace_fp.flush()

    def _read_trace_events(self) -> list[dict[str, Any]]:
        try:
            self._trace_fp.flush()
        except Exception:
            pass
        events = []
        if not self.trace_path.is_file():
            return events
        for line in self.trace_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                events.append(item)
        return events


def _blocked_response(tool: str, failure_type: str, message: str) -> dict[str, Any]:
    return {
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


def _policy_events_from_trace(
    trace_events: list[dict[str, Any]],
    metric_map: dict[str, Any],
) -> list[dict[str, Any]]:
    responses = [
        event
        for event in trace_events
        if event.get("event") == "response" and isinstance(event.get("response"), dict)
    ]
    selected_waypoints = {
        str((event.get("response") or {}).get("waypoint_id") or "")
        for event in responses
        if event.get("tool")
        in {"navigate_to_waypoint", "navigate_to_room", "navigate_to_receptacle"}
    }
    selected_waypoints.discard("")
    events: list[dict[str, Any]] = []
    for event in responses:
        tool = str(event.get("tool") or "")
        response = dict(event.get("response") or {})
        if tool == "done":
            continue
        events.append(_policy_event(len(events), tool, response))
    for waypoint in metric_map.get("inspection_waypoints") or []:
        if not isinstance(waypoint, dict):
            continue
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if not waypoint_id or waypoint_id in selected_waypoints:
            continue
        events.append(
            {
                "index": len(events) + 1,
                "tool": "navigate_to_waypoint",
                "role": "inspection_waypoint",
                "waypoint_id": waypoint_id,
                "fixture_id": waypoint.get("fixture_id", ""),
                "status": "skipped",
                "decision": "skip_public_waypoint",
                "progress": f"Skipped public waypoint {waypoint_id}; Codex did not visit it.",
                "reason": (
                    "The report keeps skipped generated/public waypoints visible "
                    "for operator review."
                ),
            }
        )
    return events


def _policy_event(index: int, tool: str, response: dict[str, Any]) -> dict[str, Any]:
    decision = {
        "metric_map": "inspect_public_metric_map",
        "fixture_hints": "inspect_public_fixture_hints",
        "navigate_to_room": "visit_public_waypoint",
        "navigate_to_waypoint": "visit_public_waypoint",
        "navigate_to_receptacle": "visit_public_waypoint",
        "navigate_to_object": "visit_public_waypoint",
        "navigate_to_visual_candidate": "visit_public_waypoint",
        "observe": "observe_head_color",
        "adjust_camera": "block_camera_adjustment",
        "pick": "block_manipulation",
        "place": "block_manipulation",
        "place_inside": "block_manipulation",
        "open_receptacle": "block_manipulation",
        "close_receptacle": "block_manipulation",
    }.get(tool, tool)
    return {
        "index": index + 1,
        "tool": response.get("tool", tool),
        "role": _policy_role(tool),
        "waypoint_id": response.get("waypoint_id", ""),
        "object_id": response.get("object_id", ""),
        "fixture_id": response.get("fixture_id", ""),
        "navigation_backend": response.get("navigation_backend", ""),
        "status": response.get("status") or response.get("navigation_status", ""),
        "decision": decision,
        "progress": _policy_progress(tool, response),
        "reason": _policy_reason(tool, response),
    }


def _policy_role(tool: str) -> str:
    if tool.startswith("navigate"):
        return "navigation"
    if tool == "observe":
        return "policy_observation"
    if tool in BLOCKED_MANIPULATION_TOOLS:
        return "blocked_manipulation"
    return "map_build_context"


def _policy_progress(tool: str, response: dict[str, Any]) -> str:
    if tool == "observe":
        camera = response.get("policy_observation_camera") or response.get("would_capture_camera")
        return f"Observed Agibot policy camera {camera or 'head_color'}."
    if tool.startswith("navigate"):
        waypoint = response.get("waypoint_id", "")
        status = response.get("navigation_status") or response.get("status")
        return f"Navigation tool {tool} targeted {waypoint or 'unresolved waypoint'}: {status}."
    if tool in BLOCKED_MANIPULATION_TOOLS:
        return f"Physical manipulation is intentionally blocked: {tool}."
    if tool == "adjust_camera":
        return "Agibot camera adjustment is intentionally blocked."
    return f"Codex called {tool}."


def _policy_reason(tool: str, response: dict[str, Any]) -> str:
    if tool == "metric_map":
        return "Metric map is the backend-agnostic public navigation context."
    if tool == "fixture_hints":
        return "Fixture hints are public map context, not private cleanup target truth."
    if tool == "observe":
        return "Agibot G2 semantic map building uses robot-local head_color evidence."
    if tool.startswith("navigate"):
        return "Navigation must resolve through verified public Agibot waypoints."
    if tool in BLOCKED_MANIPULATION_TOOLS:
        return "The first Agibot G2 milestone is navigation and perception, not cleanup."
    if tool == "adjust_camera":
        return "Bounded G2 camera motion remains unproven."
    return str(response.get("backend_error_summary") or "")


def _readiness_from_trace(
    *,
    trace_events: list[dict[str, Any]],
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    real_movement_enabled: bool,
) -> dict[str, Any]:
    responses = [
        dict(event.get("response") or {})
        for event in trace_events
        if event.get("event") == "response" and isinstance(event.get("response"), dict)
    ]
    waypoint_responses = [
        item
        for item in responses
        if item.get("tool")
        in {"navigate_to_waypoint", "navigate_to_room", "navigate_to_receptacle"}
        and item.get("waypoint_id")
    ]
    observed_count = sum(1 for item in responses if item.get("tool") == "observe")
    observed_waypoint_ids = [
        str(item.get("waypoint_id") or "")
        for item in waypoint_responses
        if item.get("ok") or item.get("navigation_status") == "dry_run_not_executed"
    ]
    observed_waypoint_ids = [item for item in dict.fromkeys(observed_waypoint_ids) if item]
    total = len(metric_map.get("inspection_waypoints") or [])
    rate = (len(observed_waypoint_ids) / total) if total else 0.0
    return {
        "schema": "real_robot_readiness_v1",
        "status": "physical_agibot_semantic_map_build_complete"
        if real_movement_enabled and rate >= 1.0
        else "physical_agibot_semantic_map_build_rehearsal",
        "real_robot_ready": False,
        "navigation_perception_ready": bool(real_movement_enabled and rate >= 1.0),
        "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
        "movement_enabled": real_movement_enabled,
        "map_bundle_schema": metric_map.get("schema", ""),
        "map_bundle_fields_present": bool(metric_map.get("inspection_waypoints") is not None),
        "pose_stamped_waypoints": True,
        "static_fixture_semantic_map": (
            fixture_hints.get("schema") == "static_fixture_semantic_map_v1"
        ),
        "physical_navigation_pilot": True,
        "physical_cleanup_ready": False,
        "semantic_map_build": True,
        "inspection_waypoint_attempt_count": len(waypoint_responses),
        "inspection_waypoint_total": total,
        "reached_waypoint_count": sum(1 for item in waypoint_responses if item.get("ok")),
        "observed_reached_waypoint_count": len(observed_waypoint_ids),
        "observed_reached_waypoint_rate": rate,
        "observed_waypoint_rate": rate,
        "visited_waypoint_ids": observed_waypoint_ids,
        "observed_waypoint_ids": observed_waypoint_ids if observed_count else [],
        "observe_count": observed_count,
        "manipulation_blocked": True,
        "blocked_capabilities": list(BLOCKED_MANIPULATION_TOOLS),
        "human_takeover_stop": any(
            item.get("failure_type", "").startswith("operator_") for item in responses
        ),
        "public_contract_note": (
            "Agibot semantic-map-build keeps real_robot_cleanup_v1 public tools stable "
            "while the SDK runner owns GDK map, camera, and PNC evidence."
        ),
    }


def _dominant_provenance(trace_events: list[dict[str, Any]]) -> str:
    for event in trace_events:
        response = event.get("response")
        if not isinstance(response, dict):
            continue
        if response.get("primitive_provenance") == "agibot_gdk_normal_navi":
            return "agibot_gdk_normal_navi"
    for event in trace_events:
        response = event.get("response")
        if isinstance(response, dict) and response.get("primitive_provenance"):
            return str(response["primitive_provenance"])
    return BLOCKED_CAPABILITY_PROVENANCE


def _empty_score(sweep_rate: float) -> dict[str, Any]:
    return {
        "completion_status": "semantic_map_build_rehearsal",
        "cleanup_status": "semantic_map_build_rehearsal",
        "restored_count": 0,
        "total_targets": 0,
        "object_results": [],
        "mess_restoration_rate": 0.0,
        "sweep_coverage_rate": sweep_rate,
        "disturbance_count": 0,
        "semantic_acceptability": {
            "accepted_count": 0,
            "total_targets": 0,
            "acceptance_rate": 0.0,
        },
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


def _runtime_timing(trace_events: list[dict[str, Any]]) -> dict[str, Any]:
    elapsed = 0.0
    if trace_events:
        elapsed = float(trace_events[-1].get("wallclock_elapsed") or 0.0)
    return {
        "total_elapsed_s": elapsed,
        "tool_handler_s": 0.0,
        "robot_view_capture_s": 0.0,
        "between_tool_gap_s": 0.0,
        "tool_call_count": sum(1 for item in trace_events if item.get("event") == "request"),
    }


def _initial_locations(scenario: CleanupScenario) -> dict[str, str]:
    return {obj.object_id: obj.location_id for obj in scenario.objects}


def _relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False
