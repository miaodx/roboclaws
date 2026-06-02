"""Command routing helpers for the public Just facade.

The root Justfile should stay small and discoverable. This module owns the
structured route normalization that is awkward to maintain as shell control
flow, while lower implementation recipes remain in Just for now.
"""

from __future__ import annotations

import os
import shlex
import sys
from dataclasses import dataclass
from typing import NoReturn

from roboclaws.launch.catalog import (
    CANONICAL_DRIVERS,
    CANONICAL_TASKS,
    LEGACY_TASK_ALIASES,
    SUPPORTED_ROUTES,
    LaunchError,
    resolve_task_launch,
)
from roboclaws.launch.plans import LaunchPlan

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


def _print_launch_trace(plan: LaunchPlan) -> None:
    fields = (
        "launch-plan",
        f"task={plan.task}",
        f"driver={plan.driver}",
        f"mode={plan.mode}",
        f"profile={plan.profile or ''}",
        f"report={plan.report or ''}",
        f"backend={plan.backend}",
        f"prompt={plan.prompt_id}",
        f"checker={plan.checker_id}",
        f"target={shlex.join(plan.argv)}",
    )
    print("\t".join(fields), file=sys.stderr)


def _die(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def task_run_main(args: list[str]) -> int:
    try:
        plan = resolve_task_launch(args)
    except LaunchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.hint:
            print(f"       {exc.hint}", file=sys.stderr)
        return 1

    if os.environ.get("ROBOCLAWS_JUST_TRACE") == "1":
        _print_launch_trace(plan)

    os.execvp(plan.argv[0], list(plan.argv))
    return 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) >= 2 and args[0] == "task" and args[1] == "run":
        return task_run_main(args[2:])
    _die("expected subcommand: task run")


if __name__ == "__main__":
    raise SystemExit(main())
