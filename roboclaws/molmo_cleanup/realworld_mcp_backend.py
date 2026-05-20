"""Backend/lifecycle glue for layered Molmo cleanup MCP tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from roboclaws.molmo_cleanup.profiles import WORLD_LABELS_PERF_PROFILE
from roboclaws.molmo_cleanup.realworld_mcp_atomic_tools import (
    ATOMIC_CLEANUP_TOOL_NAMES,
    atomic_cleanup_handlers,
    register_atomic_cleanup_tools,
)
from roboclaws.molmo_cleanup.realworld_mcp_promoted_tools import (
    promoted_cleanup_handlers,
    promoted_cleanup_tool_names,
    register_promoted_cleanup_tools,
)
from roboclaws.molmo_cleanup.realworld_mcp_semantic_tools import (
    SEMANTIC_CLEANUP_TOOL_NAMES,
    register_semantic_cleanup_tools,
    semantic_cleanup_handlers,
)
from roboclaws.molmo_cleanup.semantic_timeline import CLEAN_OBSERVED_OBJECT_TOOL


def register_realworld_mcp_tools(server: Any) -> None:
    """Register public tools in explicit layer order."""

    register_semantic_cleanup_tools(server)
    register_atomic_cleanup_tools(server)
    register_promoted_cleanup_tools(server)
    register_lifecycle_tools(server)


def register_lifecycle_tools(server: Any) -> None:
    @server._mcp.tool()
    def done(reason: str) -> dict:
        """Finish the run and write trace, run_result, and report."""
        return server.call_tool("done", reason=reason)


def dispatch_realworld_mcp_tool(
    server: Any,
    name: str,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    validate_realworld_mcp_tool_call(server, name)
    if server.done_event.is_set() and name != "done":
        return {"ok": False, "tool": name, "status": "error", "error_reason": "run_done"}

    handlers = tool_handlers_for_call(server, kwargs)
    return handlers[name]()


def validate_realworld_mcp_tool_call(server: Any, name: str) -> None:
    if name == "scene_objects":
        raise ValueError("scene_objects is not part of the ADR-0003 real-world MCP contract")
    if name == CLEAN_OBSERVED_OBJECT_TOOL and not server.enable_promoted_cleanup_tools:
        raise ValueError(
            f"{CLEAN_OBSERVED_OBJECT_TOOL} is only available when promoted cleanup "
            "tools are explicitly enabled"
        )
    if name not in public_tool_names_for_profile(
        server.cleanup_profile,
        enable_promoted_cleanup_tools=server.enable_promoted_cleanup_tools,
    ):
        raise ValueError(f"unknown Molmo real-world cleanup MCP tool {name!r}")


def public_tool_names_for_profile(
    cleanup_profile: str | None,
    *,
    enable_promoted_cleanup_tools: bool | None = None,
) -> tuple[str, ...]:
    if enable_promoted_cleanup_tools is None:
        enable_promoted_cleanup_tools = cleanup_profile == WORLD_LABELS_PERF_PROFILE
    return (
        *SEMANTIC_CLEANUP_TOOL_NAMES,
        *ATOMIC_CLEANUP_TOOL_NAMES,
        *promoted_cleanup_tool_names(enable_promoted_cleanup_tools),
        "done",
    )


def tool_handlers_for_call(
    server: Any,
    kwargs: dict[str, Any],
) -> dict[str, Callable[[], dict[str, Any]]]:
    return {
        **semantic_cleanup_handlers(server, kwargs),
        **atomic_cleanup_handlers(server, kwargs),
        **promoted_cleanup_handlers(server, kwargs),
        "done": lambda: server.contract.done(str(kwargs.get("reason", ""))),
    }


def agent_view_public_tool_names(server: Any, base_tool_names: list[str]) -> list[str]:
    tools = list(base_tool_names)
    for tool in promoted_cleanup_tool_names(server.enable_promoted_cleanup_tools):
        if tool not in tools:
            tools.append(tool)
    return tools
