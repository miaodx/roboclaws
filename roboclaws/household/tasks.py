"""Household task declarations."""

from __future__ import annotations

from roboclaws.launch.task_specs import TaskSpec

HOUSEHOLD_PROFILES: tuple[str, ...] = (
    "smoke",
    "world-labels",
    "world-labels-sanitized",
    "camera-raw",
    "camera-labels",
)

HOUSEHOLD_TASK_SPECS: dict[str, TaskSpec] = {
    "semantic-map-build": TaskSpec(
        name="semantic-map-build",
        domain="household",
        supported_drivers=("direct", "codex"),
        supported_reports=(),
        default_report=None,
        default_profile="world-labels",
        supported_profiles=HOUSEHOLD_PROFILES,
        default_backend="molmospaces_subprocess",
        prompt_id="semantic_map_build",
        checker_id="runtime_metric_map",
        required_capabilities=("household_world", "household_episode"),
    ),
    "household-cleanup": TaskSpec(
        name="household-cleanup",
        domain="household",
        supported_drivers=("direct", "mcp-smoke", "codex", "claude", "openclaw"),
        supported_reports=(),
        default_report=None,
        default_profile="world-labels",
        supported_profiles=HOUSEHOLD_PROFILES,
        default_backend="molmospaces_subprocess",
        prompt_id="household_cleanup",
        checker_id="cleanup_report",
        required_capabilities=(
            "household_world",
            "household_manipulation",
            "household_episode",
        ),
    ),
    "molmo-planner-proof": TaskSpec(
        name="molmo-planner-proof",
        domain="household",
        supported_drivers=("direct", "script", "mcp-smoke"),
        supported_reports=("visual", "minimal"),
        default_report="visual",
        default_profile=None,
        supported_profiles=(),
        default_backend="molmospaces_subprocess",
        prompt_id="molmo_planner_proof",
        checker_id="planner_proof_report",
        required_capabilities=("planner_proof",),
    ),
}
