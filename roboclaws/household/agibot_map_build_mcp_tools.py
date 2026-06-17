"""Agibot semantic map-build MCP tool registration and dispatch."""

from __future__ import annotations

from typing import Any

from roboclaws.household.agibot_sdk_runner import BLOCKED_MANIPULATION_TOOLS
from roboclaws.household.nav2_adapter import BLOCKED_CAPABILITY_PROVENANCE
from roboclaws.household.realworld_contract import REALWORLD_CONTRACT

AGIBOT_SEMANTIC_MAP_BUILD_TOOLS = (
    "metric_map",
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


def register_agibot_semantic_map_build_tools(server: Any) -> None:
    """Register public tools in the same layer order as the shared MCP backend."""

    _register_map_tools(server)
    _register_navigation_tools(server)
    _register_observation_tools(server)
    _register_manipulation_tools(server)
    _register_lifecycle_tools(server)


def _register_map_tools(server: Any) -> None:
    @server._mcp.tool()
    def metric_map() -> dict:
        """Return the backend-agnostic Agibot metric map projection."""
        return server.call_tool("metric_map")


def _register_navigation_tools(server: Any) -> None:
    @server._mcp.tool()
    def navigate_to_room(room_id: str) -> dict:
        """Navigate to a verified public waypoint for a room."""
        return server.call_tool("navigate_to_room", room_id=room_id)

    @server._mcp.tool()
    def navigate_to_waypoint(waypoint_id: str) -> dict:
        """Navigate to a verified public Agibot waypoint."""
        return server.call_tool("navigate_to_waypoint", waypoint_id=waypoint_id)

    @server._mcp.tool()
    def navigate_to_receptacle(fixture_id: str) -> dict:
        """Navigate to a fixture-preferred waypoint without claiming manipulation."""
        return server.call_tool("navigate_to_receptacle", fixture_id=fixture_id)

    @server._mcp.tool()
    def navigate_to_object(
        object_id: str,
        waypoint_id: str = "",
        fixture_id: str = "",
    ) -> dict:
        """Navigate to a public waypoint associated with an object when available."""
        return server.call_tool(
            "navigate_to_object",
            object_id=object_id,
            waypoint_id=waypoint_id,
            fixture_id=fixture_id,
        )

    @server._mcp.tool()
    def navigate_to_visual_candidate(
        source_observation_id: str,
        candidate_id: str = "",
        waypoint_id: str = "",
        fixture_id: str = "",
        target_fixture_id: str = "",
    ) -> dict:
        """Navigate to a grounded visual candidate when a public waypoint resolves."""
        return server.call_tool(
            "navigate_to_visual_candidate",
            source_observation_id=source_observation_id,
            candidate_id=candidate_id,
            waypoint_id=waypoint_id,
            fixture_id=fixture_id,
            target_fixture_id=target_fixture_id,
        )


def _register_observation_tools(server: Any) -> None:
    @server._mcp.tool()
    def observe() -> dict:
        """Capture or rehearse robot-local head_color policy observation."""
        return server.call_tool("observe")

    @server._mcp.tool()
    def adjust_camera(yaw_delta_deg: float = 0.0, pitch_delta_deg: float = 0.0) -> dict:
        """Report bounded camera adjustment as blocked until G2 control is proven."""
        return server.call_tool(
            "adjust_camera",
            yaw_delta_deg=yaw_delta_deg,
            pitch_delta_deg=pitch_delta_deg,
        )


def _register_manipulation_tools(server: Any) -> None:
    @server._mcp.tool()
    def pick(object_id: str = "") -> dict:
        """Blocked during Agibot intent=map-build pilot."""
        return server.call_tool("pick", object_id=object_id)

    @server._mcp.tool()
    def place(fixture_id: str = "") -> dict:
        """Blocked during Agibot intent=map-build pilot."""
        return server.call_tool("place", fixture_id=fixture_id)

    @server._mcp.tool()
    def place_inside(fixture_id: str = "") -> dict:
        """Blocked during Agibot intent=map-build pilot."""
        return server.call_tool("place_inside", fixture_id=fixture_id)

    @server._mcp.tool()
    def open_receptacle(fixture_id: str = "") -> dict:
        """Blocked during Agibot intent=map-build pilot."""
        return server.call_tool("open_receptacle", fixture_id=fixture_id)

    @server._mcp.tool()
    def close_receptacle(fixture_id: str = "") -> dict:
        """Blocked during Agibot intent=map-build pilot."""
        return server.call_tool("close_receptacle", fixture_id=fixture_id)


def _register_lifecycle_tools(server: Any) -> None:
    @server._mcp.tool()
    def done(reason: str) -> dict:
        """Finish the Agibot intent=map-build pilot and write report artifacts."""
        return server.call_tool("done", reason=reason)


def dispatch_agibot_semantic_map_build_tool(
    server: Any,
    name: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    if name == "metric_map":
        return _dispatch_metric_map(server)
    if name.startswith("navigate_to_"):
        return _dispatch_navigation_tool(server, name, request)
    if name in {"observe", "adjust_camera"}:
        return _dispatch_observation_tool(server, name)
    if name in BLOCKED_MANIPULATION_TOOLS:
        return server.adapter.blocked_manipulation(tool=name)
    if name == "done":
        return server._finalize_done(reason=str(request.get("reason") or ""))
    raise AssertionError(f"unhandled Agibot intent=map-build tool {name!r}")


def _dispatch_metric_map(server: Any) -> dict[str, Any]:
    response = dict(server.adapter.metric_map())
    response["instruction"] = (
        "Use only public inspection_waypoints. Navigate to each selected waypoint, "
        "then call observe. Use public_semantic_anchors and waypoint metadata for "
        "map evidence instead of a static_fixture_projection-first tool habit. Do not invent "
        "coordinates or read Agibot map source."
    )
    return response


def _dispatch_navigation_tool(
    server: Any,
    name: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    if name == "navigate_to_room":
        return server.adapter.navigate_to_room(room_id=str(request.get("room_id") or ""))
    if name == "navigate_to_waypoint":
        return server.adapter.navigate_to_waypoint(
            waypoint_id=str(request.get("waypoint_id") or "")
        )
    if name == "navigate_to_receptacle":
        return server.adapter.navigate_to_fixture_preferred_waypoint(
            fixture_id=str(request.get("fixture_id") or "")
        )
    if name == "navigate_to_object":
        return server.adapter.navigate_to_object(
            object_id=str(request.get("object_id") or ""),
            waypoint_id=str(request.get("waypoint_id") or ""),
            fixture_id=str(request.get("fixture_id") or ""),
        )
    if name == "navigate_to_visual_candidate":
        return server.adapter.navigate_to_visual_candidate(
            source_observation_id=str(request.get("source_observation_id") or ""),
            candidate_id=str(request.get("candidate_id") or ""),
            waypoint_id=str(request.get("waypoint_id") or ""),
            fixture_id=str(request.get("fixture_id") or ""),
            target_fixture_id=str(request.get("target_fixture_id") or ""),
        )
    raise AssertionError(f"unhandled Agibot navigation tool {name!r}")


def _dispatch_observation_tool(server: Any, name: str) -> dict[str, Any]:
    if name == "observe":
        return server.adapter.observe(label=f"semantic_map_build_{server._observe_count() + 1}")
    return _blocked_response(
        "adjust_camera",
        "agibot_camera_motion_unproven",
        ("Agibot G2 camera adjustment is intentionally blocked until bounded control is proven."),
    )


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
