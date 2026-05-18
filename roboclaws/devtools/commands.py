"""Command routing helpers for the public Just facade.

The root Justfile should stay small and discoverable. This module owns the
structured route normalization that is awkward to maintain as shell control
flow, while lower implementation recipes remain in Just for now.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import NoReturn

CANONICAL_TASKS: set[str] = {
    "ai2thor-nav",
    "territory",
    "coverage",
    "photo-chairs",
    "molmo-cleanup",
    "molmo-planner-proof",
}

CANONICAL_DRIVERS: set[str] = {
    "openclaw",
    "vlm",
    "codex",
    "claude",
    "script",
    "direct",
    "mcp-smoke",
}

SUPPORTED_ROUTES: set[tuple[str, str]] = {
    ("ai2thor-nav", "openclaw"),
    ("ai2thor-nav", "codex"),
    ("ai2thor-nav", "claude"),
    ("territory", "openclaw"),
    ("territory", "vlm"),
    ("territory", "script"),
    ("coverage", "openclaw"),
    ("coverage", "vlm"),
    ("coverage", "script"),
    ("photo-chairs", "openclaw"),
    ("photo-chairs", "codex"),
    ("photo-chairs", "claude"),
    ("molmo-cleanup", "direct"),
    ("molmo-cleanup", "mcp-smoke"),
    ("molmo-cleanup", "codex"),
    ("molmo-cleanup", "claude"),
    ("molmo-cleanup", "openclaw"),
    ("molmo-planner-proof", "direct"),
    ("molmo-planner-proof", "script"),
    ("molmo-planner-proof", "mcp-smoke"),
}

NON_MOLMO_REPORTS = {"visual", "minimal"}
MOLMO_CLEANUP_PROFILES = {"smoke", "world-labels", "camera-raw", "camera-labels"}


class CommandError(ValueError):
    """User-facing command routing error."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


@dataclass(frozen=True)
class ResolvedCommand:
    """A command ready to execute."""

    argv: tuple[str, ...]
    task: str
    driver: str
    mode: str
    overrides: tuple[str, ...]


def _strip_named(value: str, name: str) -> str:
    prefix = f"{name}="
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _normalize_task(value: str) -> str:
    task = _strip_named(value, "task")
    if task not in CANONICAL_TASKS:
        raise CommandError(
            f"unsupported task '{task}'",
            "expected ai2thor-nav|territory|coverage|photo-chairs|"
            "molmo-cleanup|molmo-planner-proof",
        )
    return task


def _normalize_driver(value: str) -> str:
    driver = _strip_named(value, "driver")
    if driver not in CANONICAL_DRIVERS:
        raise CommandError(
            f"unsupported driver '{driver}'",
            "expected openclaw|vlm|codex|claude|script|direct|mcp-smoke",
        )
    return driver


def _split_mode_and_overrides(
    raw_mode: str, raw_overrides: list[str]
) -> tuple[str, tuple[str, ...]]:
    mode = raw_mode
    overrides = list(raw_overrides)

    if mode.startswith("report="):
        mode = mode.removeprefix("report=")
    elif mode.startswith("profile="):
        mode = mode.removeprefix("profile=")
    elif "=" in mode:
        overrides.insert(0, mode)
        mode = ""

    return mode, tuple(overrides)


def _resolve_dispatch_mode(task: str, raw_mode: str) -> str:
    if task == "molmo-cleanup":
        profile = raw_mode or "world-labels"
        if profile not in MOLMO_CLEANUP_PROFILES:
            raise CommandError(
                f"unsupported molmo-cleanup profile '{raw_mode}'",
                "expected smoke|world-labels|camera-raw|camera-labels",
            )
        return profile

    report = raw_mode or "visual"
    if report not in NON_MOLMO_REPORTS:
        raise CommandError(f"unsupported report '{report}'", "expected visual|minimal")
    return report


def resolve_task_run(args: list[str] | tuple[str, ...]) -> ResolvedCommand:
    """Resolve `just task::run ...` arguments to the next Just command."""

    if len(args) < 2:
        raise CommandError(
            "task::run requires a task and driver",
            "usage: just task::run <task> <driver> [mode] [key=value ...]",
        )

    task = _normalize_task(args[0])
    driver = _normalize_driver(args[1])
    raw_mode = args[2] if len(args) >= 3 else ""
    mode, overrides = _split_mode_and_overrides(raw_mode, list(args[3:]))

    if (task, driver) not in SUPPORTED_ROUTES:
        raise CommandError(f"driver '{driver}' cannot run task '{task}'")

    dispatch_mode = _resolve_dispatch_mode(task, mode)
    argv = ("just", "agent::run", task, driver, dispatch_mode, *overrides)
    return ResolvedCommand(
        argv=argv,
        task=task,
        driver=driver,
        mode=dispatch_mode,
        overrides=overrides,
    )


def _die(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def task_run_main(args: list[str]) -> int:
    try:
        resolved = resolve_task_run(args)
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.hint:
            print(f"       {exc.hint}", file=sys.stderr)
        return 1

    os.execvp(resolved.argv[0], list(resolved.argv))
    return 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) >= 2 and args[0] == "task" and args[1] == "run":
        return task_run_main(args[2:])
    _die("expected subcommand: task run")


if __name__ == "__main__":
    raise SystemExit(main())
