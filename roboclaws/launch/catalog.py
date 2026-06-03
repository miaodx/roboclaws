"""Public task launch catalog.

This module is the Python source of truth for task/driver/profile/report
resolution. It deliberately stays shallow: task declarations live in domain
facades, while execution still delegates to the existing lower dispatcher in
this migration checkpoint.
"""

from __future__ import annotations

from roboclaws.ai2thor.tasks import AI2THOR_TASK_SPECS
from roboclaws.games.tasks import GAME_TASK_SPECS
from roboclaws.household.tasks import HOUSEHOLD_TASK_SPECS
from roboclaws.launch.plans import LaunchPlan
from roboclaws.launch.runners import build_agent_run_argv

CANONICAL_TASKS: set[str] = {
    "ai2thor-nav",
    "territory",
    "coverage",
    "photo-chairs",
    "semantic-map-build",
    "household-cleanup",
    "molmo-planner-proof",
}

LEGACY_TASK_ALIASES: dict[str, str] = {
    "molmo-cleanup": "household-cleanup",
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

TASK_SPECS = {
    **AI2THOR_TASK_SPECS,
    **GAME_TASK_SPECS,
    **HOUSEHOLD_TASK_SPECS,
}

SUPPORTED_ROUTES: set[tuple[str, str]] = {
    (task_name, driver)
    for task_name, spec in TASK_SPECS.items()
    for driver in spec.supported_drivers
}


class LaunchError(ValueError):
    """User-facing launch resolution error."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


def _strip_named(value: str, name: str) -> str:
    prefix = f"{name}="
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _normalize_task(value: str) -> str:
    task = _strip_named(value, "task")
    task = LEGACY_TASK_ALIASES.get(task, task)
    if task not in CANONICAL_TASKS:
        raise LaunchError(
            f"unsupported task '{task}'",
            "expected ai2thor-nav|territory|coverage|photo-chairs|"
            "semantic-map-build|household-cleanup|molmo-planner-proof",
        )
    return task


def _normalize_driver(value: str) -> str:
    driver = _strip_named(value, "driver")
    if driver not in CANONICAL_DRIVERS:
        raise LaunchError(
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


def _override_value(overrides: tuple[str, ...], key: str) -> str | None:
    prefixes = (f"{key}=", f"--{key}=", f"{key.replace('_', '-')}=", f"--{key.replace('_', '-')}=")
    for override in overrides:
        for prefix in prefixes:
            if override.startswith(prefix):
                return override[len(prefix) :]
    return None


def _resolve_evidence_mode(task: str, raw_mode: str) -> tuple[str, str | None, str | None]:
    spec = TASK_SPECS[task]
    if spec.supported_profiles:
        profile = raw_mode or spec.default_profile
        if profile not in spec.supported_profiles:
            raise LaunchError(
                f"unsupported household cleanup lane '{raw_mode}'",
                "expected smoke|world-labels|world-labels-sanitized|camera-raw|camera-labels",
            )
        return profile, profile, None

    report = raw_mode or spec.default_report
    if report not in spec.supported_reports:
        raise LaunchError(f"unsupported report '{report}'", "expected visual|minimal")
    return report, None, report


def resolve_task_launch(args: list[str] | tuple[str, ...]) -> LaunchPlan:
    """Resolve ``just task::run`` arguments into a launch plan."""

    if len(args) < 2:
        raise LaunchError(
            "task::run requires a task and driver",
            "usage: just task::run <task> <driver> [mode] [key=value ...]",
        )

    task = _normalize_task(args[0])
    driver = _normalize_driver(args[1])
    raw_mode = args[2] if len(args) >= 3 else ""
    mode, overrides = _split_mode_and_overrides(raw_mode, list(args[3:]))

    if (task, driver) not in SUPPORTED_ROUTES:
        raise LaunchError(f"driver '{driver}' cannot run task '{task}'")

    spec = TASK_SPECS[task]
    evidence_mode, profile, report = _resolve_evidence_mode(task, mode)
    backend = _override_value(overrides, "backend") or spec.default_backend
    argv = build_agent_run_argv(
        task=task,
        driver=driver,
        mode=evidence_mode,
        overrides=overrides,
    )
    return LaunchPlan(
        argv=argv,
        task=task,
        driver=driver,
        evidence_mode=evidence_mode,
        profile=profile,
        report=report,
        backend=backend,
        prompt_id=spec.prompt_id,
        checker_id=spec.checker_id,
        required_capabilities=spec.required_capabilities,
        supported_reports=spec.supported_reports,
        supported_profiles=spec.supported_profiles,
        overrides=overrides,
    )
