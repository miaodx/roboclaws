"""CLI adapter for the public task runner."""

from __future__ import annotations

import os
import shlex
import sys
from typing import NoReturn

from roboclaws.launch.catalog import LaunchError, resolve_task_launch
from roboclaws.launch.plans import LaunchPlan


def print_launch_trace(plan: LaunchPlan) -> None:
    """Emit a structured trace for the resolved launch plan."""

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


def die(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def task_run_main(args: list[str]) -> int:
    """Resolve and execute ``roboclaws task run`` arguments."""

    try:
        plan = resolve_task_launch(args)
    except LaunchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.hint:
            print(f"       {exc.hint}", file=sys.stderr)
        return 1

    if os.environ.get("ROBOCLAWS_JUST_TRACE") == "1":
        print_launch_trace(plan)

    os.execvp(plan.argv[0], list(plan.argv))
    return 1
