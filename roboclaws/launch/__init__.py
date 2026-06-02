"""Launch composition root for public Roboclaws task routes."""

from __future__ import annotations

from roboclaws.launch.plans import LaunchPlan

__all__ = [
    "CANONICAL_DRIVERS",
    "CANONICAL_TASKS",
    "LEGACY_TASK_ALIASES",
    "SUPPORTED_ROUTES",
    "LaunchPlan",
    "resolve_task_launch",
]


def __getattr__(name: str) -> object:
    if name in {
        "CANONICAL_DRIVERS",
        "CANONICAL_TASKS",
        "LEGACY_TASK_ALIASES",
        "SUPPORTED_ROUTES",
        "resolve_task_launch",
    }:
        from roboclaws.launch import catalog

        return getattr(catalog, name)
    raise AttributeError(name)
