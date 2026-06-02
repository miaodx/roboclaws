"""Compatibility adapter for the public Just facade.

The root Justfile historically called this module. Public CLI parsing now lives
in :mod:`roboclaws.cli`, while this module keeps import-compatible helpers for
tests and older local scripts.
"""

from __future__ import annotations

from dataclasses import dataclass

from roboclaws.cli.main import main
from roboclaws.cli.task_run import task_run_main
from roboclaws.launch.catalog import (
    CANONICAL_DRIVERS,
    CANONICAL_TASKS,
    LEGACY_TASK_ALIASES,
    SUPPORTED_ROUTES,
    LaunchError,
    resolve_task_launch,
)

__all__ = [
    "CANONICAL_DRIVERS",
    "CANONICAL_TASKS",
    "LEGACY_TASK_ALIASES",
    "SUPPORTED_ROUTES",
    "CommandError",
    "ResolvedCommand",
    "main",
    "resolve_task_run",
    "task_run_main",
]


class CommandError(LaunchError):
    """User-facing command routing error."""


@dataclass(frozen=True)
class ResolvedCommand:
    """A command ready to execute."""

    argv: tuple[str, ...]
    task: str
    driver: str
    mode: str
    overrides: tuple[str, ...]


def resolve_task_run(args: list[str] | tuple[str, ...]) -> ResolvedCommand:
    """Resolve `just task::run ...` arguments to the next Just command."""

    try:
        plan = resolve_task_launch(args)
    except LaunchError as exc:
        raise CommandError(str(exc), exc.hint) from exc
    return ResolvedCommand(
        argv=plan.argv,
        task=plan.task,
        driver=plan.driver,
        mode=plan.mode,
        overrides=plan.overrides,
    )


if __name__ == "__main__":
    raise SystemExit(main())
