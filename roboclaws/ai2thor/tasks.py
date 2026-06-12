"""AI2-THOR task declarations."""

from __future__ import annotations

from roboclaws.launch.task_specs import TaskSurfaceSpec

AI2THOR_TASK_SPECS: dict[str, TaskSurfaceSpec] = {
    "ai2thor-world": TaskSurfaceSpec(
        surface_id="ai2thor-world",
        domain="ai2thor",
        supported_dispatch_runners=("openclaw", "codex", "claude"),
        supported_intents=("navigate", "photo-capture"),
        default_intent="navigate",
        supported_reports=("visual", "minimal"),
        default_report="visual",
        default_profile=None,
        supported_profiles=(),
        default_backend="ai2thor",
        mcp_server_id="ai2thor_navigation",
        checker_base="ai2thor_nav_report",
        required_capabilities=("navigation_world", "movement_actions"),
    ),
}
