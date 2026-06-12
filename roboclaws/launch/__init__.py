"""Launch composition root for public Roboclaws run surfaces."""

from __future__ import annotations

from roboclaws.launch.plans import LaunchPlan

__all__ = [
    "CANONICAL_DRIVERS",
    "CANONICAL_INTENTS",
    "CANONICAL_SURFACES",
    "CANONICAL_TASKS",
    "LEGACY_TASK_ALIASES",
    "SUPPORTED_SURFACE_ROUTES",
    "SUPPORTED_ROUTES",
    "LaunchPlan",
    "resolve_surface_launch",
    "resolve_task_launch",
]


def __getattr__(name: str) -> object:
    if name in {
        "CANONICAL_DRIVERS",
        "CANONICAL_INTENTS",
        "CANONICAL_SURFACES",
        "CANONICAL_TASKS",
        "LEGACY_TASK_ALIASES",
        "SUPPORTED_SURFACE_ROUTES",
        "SUPPORTED_ROUTES",
        "resolve_surface_launch",
        "resolve_task_launch",
    }:
        from roboclaws.launch import catalog

        return getattr(catalog, name)
    raise AttributeError(name)
