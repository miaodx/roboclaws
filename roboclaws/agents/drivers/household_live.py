"""Launch constants for household live-agent drivers."""

from __future__ import annotations

import argparse
from pathlib import Path

from roboclaws.household.task_intent import TASK_INTENT_MODE_DEFAULT

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


def add_household_cleanup_live_runner_args(
    parser: argparse.ArgumentParser,
    *,
    policy_default: str | None = None,
) -> None:
    """Add shared CLI args for household cleanup live-agent runners."""

    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument("--client-url", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--server-startup-timeout-s", type=float, default=600.0)
    parser.add_argument("--kickoff-prompt", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--task-name", default="household-cleanup")
    parser.add_argument("--skill-name", default="molmo-realworld-cleanup")
    parser.add_argument("--task-intent-mode", default=TASK_INTENT_MODE_DEFAULT)
    if policy_default is None:
        parser.add_argument("--policy", required=True)
    else:
        parser.add_argument("--policy", default=policy_default)
    parser.add_argument("--task", required=True)
    parser.add_argument("--min-generated-mess-count", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--server-arg", action="append", default=[])
    parser.add_argument("--checker-visual-arg", action="append", default=[])
