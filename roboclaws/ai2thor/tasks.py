"""AI2-THOR task declarations."""

from __future__ import annotations

from roboclaws.launch.task_specs import TaskSpec

AI2THOR_TASK_SPECS: dict[str, TaskSpec] = {
    "ai2thor-nav": TaskSpec(
        name="ai2thor-nav",
        domain="ai2thor",
        supported_drivers=("openclaw", "codex", "claude"),
        supported_reports=("visual", "minimal"),
        default_report="visual",
        default_profile=None,
        supported_profiles=(),
        default_backend="ai2thor",
        prompt_id="ai2thor_nav",
        checker_id="ai2thor_nav_report",
        required_capabilities=("navigation_world", "movement_actions"),
    ),
    "photo-chairs": TaskSpec(
        name="photo-chairs",
        domain="ai2thor",
        supported_drivers=("openclaw", "codex", "claude"),
        supported_reports=("visual", "minimal"),
        default_report="visual",
        default_profile=None,
        supported_profiles=(),
        default_backend="ai2thor",
        prompt_id="photo_chairs",
        checker_id="photo_report",
        required_capabilities=("navigation_world", "movement_actions", "photo_capture"),
    ),
}
