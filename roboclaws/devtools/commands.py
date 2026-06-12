"""Compatibility adapter for the public Just facade."""

from __future__ import annotations

from dataclasses import dataclass

from roboclaws.cli.main import main
from roboclaws.cli.task_run import surface_run_main
from roboclaws.launch.catalog import (
    CANONICAL_AGENT_ENGINES,
    CANONICAL_INTENTS,
    CANONICAL_SURFACES,
    SUPPORTED_SURFACE_ROUTES,
    LaunchError,
    resolve_surface_launch,
)

__all__ = [
    "CANONICAL_AGENT_ENGINES",
    "CANONICAL_INTENTS",
    "CANONICAL_SURFACES",
    "SUPPORTED_SURFACE_ROUTES",
    "CommandError",
    "ResolvedCommand",
    "main",
    "resolve_surface_run",
    "surface_run_main",
]


class CommandError(LaunchError):
    """User-facing command routing error."""


@dataclass(frozen=True)
class ResolvedCommand:
    """A command ready to execute."""

    argv: tuple[str, ...]
    world: str
    backend: str
    agent_engine: str
    provider_profile: str | None
    mode: str
    overrides: tuple[str, ...]


def resolve_surface_run(args: list[str] | tuple[str, ...]) -> ResolvedCommand:
    """Resolve `just run::surface ...` arguments to the next Just command."""

    try:
        plan = resolve_surface_launch(args)
    except LaunchError as exc:
        raise CommandError(str(exc), exc.hint) from exc
    return ResolvedCommand(
        argv=plan.argv,
        world=plan.world,
        backend=plan.backend,
        agent_engine=plan.agent_engine,
        provider_profile=plan.provider_profile,
        mode=plan.mode,
        overrides=plan.overrides,
    )


if __name__ == "__main__":
    raise SystemExit(main())
