"""Launch constants for household live-agent drivers."""

from __future__ import annotations

HOUSEHOLD_CLEANUP_SERVER_MODULE = "roboclaws.cli.agent_server"
HOUSEHOLD_CLEANUP_SERVER_TASK = "household-world.cleanup"
SEMANTIC_MAP_BUILD_SERVER_MODULE = "roboclaws.cli.agent_server"
SEMANTIC_MAP_BUILD_SERVER_TASK = "household-world.map-build"


def household_cleanup_server_argv(python_bin: str) -> list[str]:
    """Return the package entrypoint for the household cleanup MCP server."""

    return [
        python_bin,
        "-m",
        HOUSEHOLD_CLEANUP_SERVER_MODULE,
        HOUSEHOLD_CLEANUP_SERVER_TASK,
    ]


def semantic_map_build_server_argv(python_bin: str) -> list[str]:
    """Return the package entrypoint for the Agibot semantic-map MCP server."""

    return [
        python_bin,
        "-m",
        SEMANTIC_MAP_BUILD_SERVER_MODULE,
        SEMANTIC_MAP_BUILD_SERVER_TASK,
    ]
