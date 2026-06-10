"""Household task declarations."""

from __future__ import annotations

from roboclaws.household.profiles import cleanup_profile_names
from roboclaws.launch.task_specs import TaskSurfaceSpec

HOUSEHOLD_PROFILES: tuple[str, ...] = cleanup_profile_names()

HOUSEHOLD_TASK_SPECS: dict[str, TaskSurfaceSpec] = {
    "household-world": TaskSurfaceSpec(
        surface_id="household-world",
        domain="household",
        supported_drivers=(
            "direct",
            "mcp-smoke",
            "codex",
            "claude",
            "openai-agents-live",
            "openclaw",
        ),
        supported_intents=("cleanup", "map-build", "open-ended"),
        default_intent="cleanup",
        supported_reports=(),
        default_report=None,
        default_profile="world-oracle-labels",
        supported_profiles=HOUSEHOLD_PROFILES,
        default_backend="molmospaces_subprocess",
        mcp_server_id="molmo_cleanup_realworld",
        checker_base="household_world",
        required_capabilities=(
            "household_world",
            "household_manipulation",
            "household_episode",
        ),
    ),
    "planner-proof": TaskSurfaceSpec(
        surface_id="planner-proof",
        domain="household",
        supported_drivers=("direct", "script", "mcp-smoke"),
        supported_intents=("planner-proof",),
        default_intent="planner-proof",
        supported_reports=("visual", "minimal"),
        default_report="visual",
        default_profile=None,
        supported_profiles=(),
        default_backend="molmospaces_subprocess",
        mcp_server_id="planner_proof",
        checker_base="planner_proof_report",
        required_capabilities=("planner_proof",),
    ),
}
