"""Game task declarations."""

from __future__ import annotations

from roboclaws.launch.task_specs import TaskSpec

GAME_TASK_SPECS: dict[str, TaskSpec] = {
    "territory": TaskSpec(
        name="territory",
        domain="games",
        supported_drivers=("openclaw", "vlm", "script"),
        supported_reports=("visual", "minimal"),
        default_report="visual",
        default_profile=None,
        supported_profiles=(),
        default_backend="ai2thor",
        prompt_id="territory_game",
        checker_id="territory_report",
        required_capabilities=("navigation_world", "movement_actions", "game_score"),
    ),
    "coverage": TaskSpec(
        name="coverage",
        domain="games",
        supported_drivers=("openclaw", "vlm", "script"),
        supported_reports=("visual", "minimal"),
        default_report="visual",
        default_profile=None,
        supported_profiles=(),
        default_backend="ai2thor",
        prompt_id="coverage_game",
        checker_id="coverage_report",
        required_capabilities=("navigation_world", "movement_actions", "coverage_score"),
    ),
}
