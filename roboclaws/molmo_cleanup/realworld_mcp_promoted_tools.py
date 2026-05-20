"""Promoted-candidate Molmo cleanup MCP tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from roboclaws.molmo_cleanup.semantic_timeline import CLEAN_OBSERVED_OBJECT_TOOL

PROMOTED_CLEANUP_TOOL_NAMES = (CLEAN_OBSERVED_OBJECT_TOOL,)


def promoted_cleanup_tool_names(enabled: bool) -> tuple[str, ...]:
    if enabled:
        return PROMOTED_CLEANUP_TOOL_NAMES
    return ()


def register_promoted_cleanup_tools(server: Any) -> None:
    """Register promoted-candidate composite tools for explicit perf profiles."""

    if not server.enable_promoted_cleanup_tools:
        return

    @server._mcp.tool()
    def clean_observed_object(
        object_id: str,
        fixture_id: str,
        placement_tool: str = "auto",
    ) -> dict:
        """Clean one observed handle with public substeps in one perf-lane call."""
        return server.call_tool(
            CLEAN_OBSERVED_OBJECT_TOOL,
            object_id=object_id,
            fixture_id=fixture_id,
            placement_tool=placement_tool,
        )


def promoted_cleanup_handlers(
    server: Any,
    kwargs: dict[str, Any],
) -> dict[str, Callable[[], dict[str, Any]]]:
    def clean_observed_object() -> dict[str, Any]:
        result = server.contract.clean_observed_object(
            str(kwargs.get("object_id", "")),
            str(kwargs.get("fixture_id", "")),
            placement_tool=str(kwargs.get("placement_tool") or "auto"),
            step_callback=server._record_composite_step_robot_view
            if server.record_robot_views
            else None,
        )
        if server.record_robot_views:
            result = dict(result)
            result["composite_robot_views_recorded_inline"] = True
        return result

    return {
        CLEAN_OBSERVED_OBJECT_TOOL: clean_observed_object,
    }
