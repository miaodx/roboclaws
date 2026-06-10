"""Launch composition root for public Roboclaws run surfaces."""

from __future__ import annotations

from roboclaws.launch.plans import LaunchPlan

__all__ = [
    "CANONICAL_AGENT_ENGINES",
    "CANONICAL_INTENTS",
    "CANONICAL_SURFACES",
    "SUPPORTED_SURFACE_ROUTES",
    "LaunchPlan",
    "resolve_surface_launch",
]


def __getattr__(name: str) -> object:
    if name in {
        "CANONICAL_AGENT_ENGINES",
        "CANONICAL_INTENTS",
        "CANONICAL_SURFACES",
        "SUPPORTED_SURFACE_ROUTES",
        "resolve_surface_launch",
    }:
        from roboclaws.launch import catalog

        return getattr(catalog, name)
    raise AttributeError(name)
