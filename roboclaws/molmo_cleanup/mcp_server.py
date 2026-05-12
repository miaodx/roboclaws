"""FastMCP bridge for the MolmoSpaces current cleanup contract.

This server is intentionally separate from ``roboclaws.mcp.server``. The
AI2-THOR navigation server owns image-heavy movement tools, while this bridge
wraps the semantic Molmo cleanup contract: observe the public room state,
choose object/receptacle pairs externally, execute semantic substeps, and call
done for scorer readback.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.manipulation_provenance import (
    api_semantic_manipulation_evidence,
)
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.report import (
    render_cleanup_report,
    write_state_snapshot,
)
from roboclaws.molmo_cleanup.scenario import (
    build_cleanup_scenario,
    write_scenario_bundle,
)
from roboclaws.molmo_cleanup.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)
from roboclaws.molmo_cleanup.semantic_timeline import (
    CURRENT_CONTRACT_SEMANTIC_LOOP_VARIANT,
    ROBOT_VIEW_VARIANT,
    cleanup_plan_from_semantic_substeps,
    primitive_provenance_counts,
    record_robot_view_step,
    robot_view_capture_for_tool,
    semantic_diagnostics,
    semantic_substeps,
)
from roboclaws.molmo_cleanup.types import CleanupScenario

__all__ = ["MolmoCleanupMCPServer", "make_molmo_cleanup_mcp"]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18788
STARTUP_TIMEOUT_S = 2.0
CURRENT_CONTRACT = "current_contract"
MCP_SERVER_NAME = "molmo_cleanup"
GLOBAL_SCENE_OBJECTS_SHORTCUT = "global_scene_objects"
SEMANTIC_LOOP_VARIANT = CURRENT_CONTRACT_SEMANTIC_LOOP_VARIANT
AGENT_POLICIES = {"codex_agent", "claude_code_agent", "openclaw_agent", "manual_agent"}


def make_molmo_cleanup_mcp(
    *,
    run_dir: Path,
    scenario: CleanupScenario | None = None,
    contract: MolmoCleanupToolContract | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    policy: str = "codex_agent",
    agent_driven: bool | None = None,
    task_prompt: str | None = None,
    record_robot_views: bool = False,
) -> "MolmoCleanupMCPServer":
    """Factory mirroring the AI2-THOR MCP server's construction style."""
    return MolmoCleanupMCPServer(
        run_dir=run_dir,
        scenario=scenario,
        contract=contract,
        host=host,
        port=port,
        policy=policy,
        agent_driven=agent_driven,
        task_prompt=task_prompt,
        record_robot_views=record_robot_views,
    )


class MolmoCleanupMCPServer:
    """FastMCP server wrapping ``MolmoCleanupToolContract`` for agent dogfood."""

    def __init__(
        self,
        *,
        run_dir: Path,
        scenario: CleanupScenario | None = None,
        contract: MolmoCleanupToolContract | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        policy: str = "codex_agent",
        agent_driven: bool | None = None,
        task_prompt: str | None = None,
        record_robot_views: bool = False,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.host = host
        self.port = int(port)
        self.policy = policy
        self.agent_driven = _default_agent_driven(policy) if agent_driven is None else agent_driven
        self.policy_uses_private_truth = False
        self.scenario = scenario or build_cleanup_scenario()
        self.contract = contract or MolmoCleanupToolContract(self.scenario)
        self.task_prompt = task_prompt or self.scenario.task
        self.record_robot_views = bool(record_robot_views)
        if self.record_robot_views and not callable(
            getattr(self.contract.backend, "write_robot_views", None)
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

        self._scenario_paths = write_scenario_bundle(self.run_dir, self.scenario)
        self._before_snapshot = self._write_snapshot("before.png", title="Before cleanup")
        self._record_robot_view("before", label_suffix="before")
        self._mcp = FastMCP("roboclaws", host=host, port=self.port)
        self._register_tools()
        self.write_runtime_event(
            "molmo_cleanup_mcp_initialized",
            contract=CURRENT_CONTRACT,
            policy=policy,
            agent_driven=self.agent_driven,
        )

    def _register_tools(self) -> None:
        server = self

        @self._mcp.tool()
        def observe() -> dict:
            """Return public cleanup state. Call this before any cleanup substep."""
            return server.call_tool("observe")

        @self._mcp.tool()
        def scene_objects(category: str | None = None) -> dict:
            """List public objects and receptacles with current semantic locations.

            This is a current-contract shortcut: it returns the global public
            object list so external agents can prove tool sequencing before the
            later ADR-0003 robot-local perception restriction.
            """
            return server.call_tool("scene_objects", category=category)

        @self._mcp.tool()
        def navigate_to_object(object_id: str) -> dict:
            """Navigate to an object's current public location before pick."""
            return server.call_tool("navigate_to_object", object_id=object_id)

        @self._mcp.tool()
        def navigate_to_receptacle(receptacle_id: str) -> dict:
            """Navigate to a target receptacle before place or place_inside."""
            return server.call_tool("navigate_to_receptacle", receptacle_id=receptacle_id)

        @self._mcp.tool()
        def pick(object_id: str) -> dict:
            """Pick up one known pickupable object by object_id."""
            return server.call_tool("pick", object_id=object_id)

        @self._mcp.tool()
        def open_receptacle(receptacle_id: str) -> dict:
            """Open fridge-like receptacles before calling place_inside."""
            return server.call_tool("open_receptacle", receptacle_id=receptacle_id)

        @self._mcp.tool()
        def place(receptacle_id: str) -> dict:
            """Place the held object on/at a target receptacle."""
            return server.call_tool("place", receptacle_id=receptacle_id)

        @self._mcp.tool()
        def place_inside(receptacle_id: str) -> dict:
            """Place the held object inside an opened fridge-like receptacle."""
            return server.call_tool("place_inside", receptacle_id=receptacle_id)

        @self._mcp.tool()
        def close_receptacle(receptacle_id: str) -> dict:
            """Close a fridge-like receptacle after place_inside."""
            return server.call_tool("close_receptacle", receptacle_id=receptacle_id)

        @self._mcp.tool()
        def object_done(object_id: str, receptacle_id: str) -> dict:
            """Record public readback for one completed object before done."""
            return server.call_tool(
                "object_done",
                object_id=object_id,
                receptacle_id=receptacle_id,
            )

        @self._mcp.tool()
        def done(reason: str) -> dict:
            """Finish the cleanup run and write trace, run_result, and report."""
            return server.call_tool("done", reason=reason)

    def call_tool(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Invoke the same external tool names registered with FastMCP."""
        if self.done_event.is_set() and name != "done":
            return {"ok": False, "tool": name, "status": "error", "error_reason": "run_done"}
        handlers = {
            "observe": lambda: self.contract.observe(),
            "scene_objects": lambda: self.contract.scene_objects(
                category=_optional_str(kwargs.get("category"))
            ),
            "navigate_to_object": lambda: self.contract.navigate_to_object(
                str(kwargs.get("object_id", ""))
            ),
            "navigate_to_receptacle": lambda: self.contract.navigate_to_receptacle(
                str(kwargs.get("receptacle_id", ""))
            ),
            "pick": lambda: self.contract.pick(str(kwargs.get("object_id", ""))),
            "open_receptacle": lambda: self.contract.open_receptacle(
                str(kwargs.get("receptacle_id", ""))
            ),
            "place": lambda: self.contract.place(str(kwargs.get("receptacle_id", ""))),
            "place_inside": lambda: self.contract.place_inside(
                str(kwargs.get("receptacle_id", ""))
            ),
            "close_receptacle": lambda: self.contract.close_receptacle(
                str(kwargs.get("receptacle_id", ""))
            ),
            "object_done": lambda: self.contract.object_done(
                str(kwargs.get("object_id", "")),
                str(kwargs.get("receptacle_id", "")),
            ),
            "done": lambda: self.contract.done(str(kwargs.get("reason", ""))),
        }
        if name not in handlers:
            raise ValueError(f"unknown Molmo cleanup MCP tool {name!r}")

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
        if tool == "observe" and isinstance(augmented.get("scenario"), dict):
            augmented["contract"] = CURRENT_CONTRACT
            augmented["current_contract_shortcuts"] = [GLOBAL_SCENE_OBJECTS_SHORTCUT]
            augmented["instruction"] = (
                "Choose object/receptacle order yourself. Use scene_objects; "
                "use only pickupable object_id values from scene_objects.objects "
                "with a non-empty location_id. Receptacles are targets, not "
                "objects to pick. When several receptacles have the same "
                "suitable category, choose the first matching receptacle in "
                "scene_objects.receptacles order. Then per object: "
                "navigate_to_object -> pick -> navigate_to_receptacle -> "
                "open_receptacle if target is fridge -> place/place_inside -> "
                "close_receptacle if opened -> object_done. Call done last."
            )
        if tool == "scene_objects":
            augmented["contract"] = CURRENT_CONTRACT
            augmented["current_contract_shortcuts"] = [GLOBAL_SCENE_OBJECTS_SHORTCUT]
            augmented["private_target_truth_included"] = False
        if tool == "navigate_to_receptacle" and self.contract.backend.held_object_id:
            augmented.setdefault("object_id", self.contract.backend.held_object_id)
        if tool == "open_receptacle" and self.contract.backend.held_object_id:
            augmented.setdefault("object_id", self.contract.backend.held_object_id)
        if tool == "close_receptacle":
            request_object_id = request.get("object_id")
            if request_object_id:
                augmented.setdefault("object_id", request_object_id)
        if tool in {"place", "place_inside"} and "receptacle_id" not in augmented:
            augmented["receptacle_id"] = request.get("receptacle_id")
        return augmented

    def _finalize_done(self, reason: str, done_response: dict[str, Any]) -> dict[str, Any]:
        if self._done_result is not None:
            return self._done_result

        after_snapshot = self._write_snapshot("after.png", title="After cleanup")
        self._record_robot_view("after", label_suffix="after")
        trace_events = self._read_trace_events()
        substeps = semantic_substeps(trace_events, self._receptacles_by_id())
        cleanup_plan = cleanup_plan_from_semantic_substeps(substeps)
        annotated_score = annotate_score_with_semantic_acceptability(
            done_response["score"],
            self.scenario,
        )
        done_response = {**done_response, "score": annotated_score}
        diagnostics = semantic_diagnostics(trace_events, substeps, done_response)
        primitive_counts = primitive_provenance_counts(trace_events)
        run_result = {
            "backend": _backend_name(self.contract.backend),
            "scenario_id": self.scenario.scenario_id,
            "seed": self.scenario.seed,
            "task_prompt": self.task_prompt,
            "contract": CURRENT_CONTRACT,
            "current_contract_shortcuts": [GLOBAL_SCENE_OBJECTS_SHORTCUT],
            "adr_0003_satisfied": False,
            "adr_0003_note": (
                "This bridge proves agent/tool viability against the current "
                "curated contract. It still exposes global scene_objects and "
                "does not satisfy ADR-0003 robot-local perception."
            ),
            "final_status": done_response["cleanup_status"],
            "terminate_reason": reason,
            "cleanup_status": done_response["cleanup_status"],
            "primitive_provenance": API_SEMANTIC_PROVENANCE,
            "primitive_provenance_summary": primitive_counts,
            "manipulation_evidence": api_semantic_manipulation_evidence(
                backend=_backend_name(self.contract.backend),
                primitive_summary=primitive_counts,
            ),
            "policy": self.policy,
            "planner": self.policy,
            "agent_driven": self.agent_driven,
            "policy_uses_private_truth": self.policy_uses_private_truth,
            "planner_uses_private_manifest": False,
            "mcp_server": MCP_SERVER_NAME,
            "cleanup_plan": cleanup_plan,
            "semantic_loop_variant": SEMANTIC_LOOP_VARIANT,
            "semantic_substeps": substeps,
            "score": done_response["score"],
            "final_locations": done_response["final_locations"],
            "final_containment": done_response.get("final_containment", {}),
            "tool_event_counts": done_response["tool_event_counts"],
            "agent_bridge": diagnostics,
            "artifacts": {
                "scenario": str(self._scenario_paths["scenario"]),
                "trace": str(self.trace_path),
                "before_snapshot": str(self._before_snapshot),
                "after_snapshot": str(after_snapshot),
            },
        }
        _add_backend_runtime_metadata(run_result, self.contract.backend)
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
            "contract": CURRENT_CONTRACT,
            "agent_driven": self.agent_driven,
        }
        self.done_event.set()
        self.write_runtime_event(
            "molmo_cleanup_mcp_done",
            cleanup_status=done_response["cleanup_status"],
            restored_count=done_response["score"]["restored_count"],
            total_targets=done_response["score"]["total_targets"],
        )
        return self._done_result

    def write_runtime_event(self, event: str, **data: Any) -> None:
        self._write_trace(tool="<runtime>", event=event, **data)

    def run_in_thread(self) -> threading.Thread:
        if self._server_thread is not None and self._server_thread.is_alive():
            return self._server_thread
        thread = threading.Thread(
            target=self._mcp.run,
            kwargs={"transport": "streamable-http"},
            name=f"molmo-cleanup-mcp-{self.port}",
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
                raise RuntimeError(
                    f"Molmo cleanup MCP server failed to start on {self.host}:{self.port}"
                )
            if _port_accepting(probe_host, self.port):
                return thread
            time.sleep(0.05)
        raise RuntimeError(
            f"Molmo cleanup MCP server did not become ready on {self.host}:{self.port}"
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
        writer = getattr(self.contract.backend, "write_snapshot", None)
        if callable(writer):
            return writer(output_path, title=title)
        return write_state_snapshot(
            self.scenario,
            self.contract.backend.object_locations(),
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
        capture = robot_view_capture_for_tool(tool, request, response)
        if capture is None:
            return
        self._record_robot_view(
            capture["action"],
            label_suffix=capture["label_suffix"],
            focus_object_id=capture.get("focus_object_id"),
            focus_receptacle_id=capture.get("focus_receptacle_id"),
            semantic_phase=capture.get("semantic_phase"),
        )

    def _record_robot_view(
        self,
        action: str,
        *,
        label_suffix: str,
        focus_object_id: str | None = None,
        focus_receptacle_id: str | None = None,
        semantic_phase: str | None = None,
    ) -> None:
        if not self.record_robot_views:
            return
        writer = getattr(self.contract.backend, "write_robot_views", None)
        if not callable(writer):
            raise RuntimeError("robot view capture requires backend.write_robot_views")
        self._robot_view_index = record_robot_view_step(
            steps=self.robot_view_steps,
            backend=self.contract.backend,
            output_dir=self.run_dir,
            index=self._robot_view_index,
            action=action,
            label_suffix=label_suffix,
            focus_object_id=focus_object_id,
            focus_receptacle_id=focus_receptacle_id,
            semantic_phase=semantic_phase,
        )

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

    def _receptacles_by_id(self) -> dict[str, dict[str, Any]]:
        return {item.receptacle_id: item.to_public_dict() for item in self.scenario.receptacles}


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
