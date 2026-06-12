"""Game task declarations."""

from __future__ import annotations

from roboclaws.launch.task_specs import TaskSurfaceSpec

GAME_TASK_SPECS: dict[str, TaskSurfaceSpec] = {
    "ai2thor-games": TaskSurfaceSpec(
        surface_id="ai2thor-games",
        domain="games",
        supported_drivers=("openclaw", "vlm", "script"),
        supported_intents=("territory", "coverage"),
        default_intent="coverage",
        supported_reports=("visual", "minimal"),
        default_report="visual",
        default_profile=None,
        supported_profiles=(),
        default_backend="ai2thor",
        mcp_server_id="ai2thor_navigation",
        checker_base="ai2thor_game_report",
        required_capabilities=("navigation_world", "movement_actions", "coverage_score"),
    ),
}
