"""Public surface launch catalog.

This module is the Python source of truth for surface/intent/driver/evidence
resolution. It deliberately stays shallow: declarations live in domain facades,
while execution still delegates to the existing lower dispatcher in this
migration checkpoint.
"""

from __future__ import annotations

from roboclaws.ai2thor.tasks import AI2THOR_TASK_SPECS
from roboclaws.games.tasks import GAME_TASK_SPECS
from roboclaws.household.profiles import (
    CAMERA_GROUNDED_LABELS_LANE,
    SIM_PROJECTED_LABELS_CAMERA_LABELER,
    cleanup_profile_names,
    validate_evidence_lane_camera_labeler,
)
from roboclaws.household.tasks import HOUSEHOLD_TASK_SPECS
from roboclaws.launch.evaluation import evaluation_spec_for_intent
from roboclaws.launch.goals import normalize_goal_contract
from roboclaws.launch.intents import TASK_INTENT_SPECS, TaskIntentSpec
from roboclaws.launch.plans import LaunchPlan
from roboclaws.launch.runners import build_agent_run_argv
from roboclaws.launch.task_specs import TaskSurfaceSpec

CANONICAL_SURFACES: set[str] = {
    "ai2thor-world",
    "ai2thor-games",
    "household-world",
    "planner-proof",
}

CANONICAL_INTENTS: set[str] = set(TASK_INTENT_SPECS)

CANONICAL_DRIVERS: set[str] = {
    "openclaw",
    "vlm",
    "codex",
    "claude",
    "script",
    "direct",
    "mcp-smoke",
}

SURFACE_SPECS: dict[str, TaskSurfaceSpec] = {
    **AI2THOR_TASK_SPECS,
    **GAME_TASK_SPECS,
    **HOUSEHOLD_TASK_SPECS,
}

SUPPORTED_SURFACE_ROUTES: set[tuple[str, str, str]] = {
    (surface_id, intent_id, driver)
    for surface_id, spec in SURFACE_SPECS.items()
    for intent_id in spec.supported_intents
    for driver in spec.supported_drivers
    if driver in TASK_INTENT_SPECS[intent_id].supported_drivers
}

# Compatibility constants for old lower dispatcher callers/tests.
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

LEGACY_TASK_TO_SURFACE_INTENT: dict[str, tuple[str, str]] = {
    "ai2thor-nav": ("ai2thor-world", "navigate"),
    "photo-chairs": ("ai2thor-world", "photo-capture"),
    "territory": ("ai2thor-games", "territory"),
    "coverage": ("ai2thor-games", "coverage"),
    "semantic-map-build": ("household-world", "map-build"),
    "household-cleanup": ("household-world", "cleanup"),
    "molmo-planner-proof": ("planner-proof", "planner-proof"),
}

SUPPORTED_ROUTES: set[tuple[str, str]] = {
    (legacy_task, driver)
    for legacy_task, (surface_id, intent_id) in LEGACY_TASK_TO_SURFACE_INTENT.items()
    for driver in SURFACE_SPECS[surface_id].supported_drivers
    if driver in TASK_INTENT_SPECS[intent_id].supported_drivers
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


def _normalize_driver(value: str) -> str:
    driver = _strip_named(value, "driver")
    if driver not in CANONICAL_DRIVERS:
        raise LaunchError(
            f"unsupported driver '{driver}'",
            "expected openclaw|vlm|codex|claude|script|direct|mcp-smoke",
        )
    return driver


def _normalize_surface(value: str) -> str:
    surface = _strip_named(value, "surface")
    if surface not in CANONICAL_SURFACES:
        raise LaunchError(
            f"unsupported surface '{surface}'",
            "expected ai2thor-world|ai2thor-games|household-world|planner-proof",
        )
    return surface


def _normalize_intent(value: str | None, *, surface: TaskSurfaceSpec, prompt: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("intent="):
        raw = raw.removeprefix("intent=")
    intent_id = raw or ("open-ended" if prompt and surface.surface_id == "household-world" else "")
    intent_id = intent_id or surface.default_intent
    if intent_id not in surface.supported_intents:
        raise LaunchError(
            f"unsupported intent '{intent_id}' for surface '{surface.surface_id}'",
            f"expected {'|'.join(surface.supported_intents)}",
        )
    if intent_id not in TASK_INTENT_SPECS:
        raise LaunchError(f"unsupported intent '{intent_id}'")
    return intent_id


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


def _split_mode_and_overrides(
    raw_mode: str, raw_overrides: list[str]
) -> tuple[str, tuple[str, ...]]:
    mode = raw_mode
    overrides = list(raw_overrides)

    if mode.startswith("report="):
        mode = mode.removeprefix("report=")
    elif mode.startswith("profile="):
        mode = mode.removeprefix("profile=")
    elif mode.startswith("evidence_lane="):
        mode = mode.removeprefix("evidence_lane=")
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


def _without_override(overrides: tuple[str, ...], key: str) -> tuple[str, ...]:
    prefixes = (f"{key}=", f"--{key}=", f"{key.replace('_', '-')}=", f"--{key.replace('_', '-')}=")
    return tuple(
        override
        for override in overrides
        if not any(override.startswith(prefix) for prefix in prefixes)
    )


def _resolve_evidence_mode(
    surface: TaskSurfaceSpec,
    raw_mode: str,
    overrides: tuple[str, ...],
) -> tuple[str, str | None, str | None, tuple[str, ...]]:
    if surface.supported_profiles:
        profile = raw_mode or _override_value(overrides, "evidence_lane")
        profile = profile or _override_value(overrides, "profile") or surface.default_profile
        if profile not in surface.supported_profiles:
            raise LaunchError(
                f"unsupported household cleanup lane '{raw_mode}'",
                f"expected {'|'.join(cleanup_profile_names())}",
            )
        camera_labeler = _override_value(overrides, "camera_labeler")
        backend = _override_value(overrides, "backend") or surface.default_backend
        if (
            profile == CAMERA_GROUNDED_LABELS_LANE
            and not camera_labeler
            and backend == "agibot_molmospaces_sim"
        ):
            camera_labeler = SIM_PROJECTED_LABELS_CAMERA_LABELER
            overrides = (*overrides, f"camera_labeler={camera_labeler}")
        visual_grounding = _override_value(overrides, "visual_grounding")
        if visual_grounding and not camera_labeler:
            raise LaunchError(
                "visual_grounding is no longer a public task axis",
                "use camera_labeler=<labeler> with evidence_lane=camera-grounded-labels",
            )
        if profile != "smoke":
            try:
                validate_evidence_lane_camera_labeler(
                    evidence_lane=profile,
                    camera_labeler=camera_labeler,
                )
            except ValueError as exc:
                raise LaunchError(str(exc)) from exc
        return profile, profile, None, overrides

    report = raw_mode or _override_value(overrides, "report") or surface.default_report
    if report not in surface.supported_reports:
        raise LaunchError(f"unsupported report '{report}'", "expected visual|minimal")
    return report, None, report, overrides


def resolve_surface_launch(args: list[str] | tuple[str, ...]) -> LaunchPlan:
    """Resolve ``just run::surface`` named arguments into a launch plan."""

    overrides = tuple(args)
    surface_value = _override_value(overrides, "surface")
    driver_value = _override_value(overrides, "driver")
    if not surface_value or not driver_value:
        raise LaunchError(
            "run::surface requires named surface= and driver=",
            "usage: just run::surface surface=<surface> driver=<driver> [intent=<intent>] "
            "[report=<report>|evidence_lane=<lane>] [key=value ...]",
        )
    surface_id = _normalize_surface(surface_value)
    driver = _normalize_driver(driver_value)
    surface = SURFACE_SPECS[surface_id]
    prompt = _override_value(overrides, "prompt") or ""
    intent_id = _normalize_intent(
        _override_value(overrides, "intent"),
        surface=surface,
        prompt=prompt,
    )
    stripped_overrides = _without_override(
        _without_override(_without_override(overrides, "surface"), "driver"),
        "intent",
    )
    return _resolve_launch(
        surface=surface,
        intent=TASK_INTENT_SPECS[intent_id],
        driver=driver,
        raw_mode="",
        overrides=stripped_overrides,
        prompt=prompt,
    )


def resolve_task_launch(args: list[str] | tuple[str, ...]) -> LaunchPlan:
    """Resolve legacy ``just task::run`` arguments through the surface model."""

    if len(args) < 2:
        raise LaunchError(
            "task::run requires a task and driver",
            "usage: just task::run <task> <driver> [mode] [key=value ...]",
        )

    task = _normalize_task(args[0])
    driver = _normalize_driver(args[1])
    raw_mode = args[2] if len(args) >= 3 else ""
    mode, overrides = _split_mode_and_overrides(raw_mode, list(args[3:]))
    surface_id, intent_id = LEGACY_TASK_TO_SURFACE_INTENT[task]
    prompt = _override_value(overrides, "prompt") or ""
    if (
        task == "household-cleanup"
        and prompt
        and driver in {"codex", "claude"}
        and not _override_value(overrides, "task_intent_mode")
    ):
        intent_id = "open-ended"
    return _resolve_launch(
        surface=SURFACE_SPECS[surface_id],
        intent=TASK_INTENT_SPECS[intent_id],
        driver=driver,
        raw_mode=mode,
        overrides=overrides,
        prompt=prompt,
    )


def _resolve_launch(
    *,
    surface: TaskSurfaceSpec,
    intent: TaskIntentSpec,
    driver: str,
    raw_mode: str,
    overrides: tuple[str, ...],
    prompt: str,
) -> LaunchPlan:
    if surface.surface_id not in intent.surface_ids:
        raise LaunchError(
            f"intent '{intent.intent_id}' cannot run on surface '{surface.surface_id}'"
        )
    if (surface.surface_id, intent.intent_id, driver) not in SUPPORTED_SURFACE_ROUTES:
        raise LaunchError(
            f"driver '{driver}' cannot run surface '{surface.surface_id}' "
            f"intent '{intent.intent_id}'"
        )
    evidence_mode, profile, report, overrides = _resolve_evidence_mode(surface, raw_mode, overrides)
    backend = _override_value(overrides, "backend") or surface.default_backend
    goal_contract = normalize_goal_contract(surface=surface, intent=intent, raw_prompt=prompt)
    plan_overrides = _overrides_with_surface_context(
        overrides,
        surface_id=surface.surface_id,
        intent_id=intent.intent_id,
        goal_contract_json=goal_contract.to_json(),
    )
    dispatch_overrides = _without_launch_only_overrides(plan_overrides)
    argv = build_agent_run_argv(
        task=intent.lower_task,
        driver=driver,
        mode=evidence_mode,
        overrides=dispatch_overrides,
    )
    evaluation = evaluation_spec_for_intent(intent)
    return LaunchPlan(
        argv=argv,
        surface=surface.surface_id,
        intent=intent.intent_id,
        lower_task=intent.lower_task,
        driver=driver,
        evidence_mode=evidence_mode,
        profile=profile,
        report=report,
        backend=backend,
        prompt_id=intent.prompt_id,
        checker_id=intent.checker_id,
        mcp_server_id=surface.mcp_server_id,
        required_capabilities=tuple(
            dict.fromkeys((*surface.required_capabilities, *intent.required_capabilities))
        ),
        required_artifacts=intent.required_artifacts,
        goal_contract=goal_contract,
        evaluation_id=evaluation.evaluation_id,
        evaluation_hard_gates=evaluation.hard_gates,
        evaluation_intent_gates=evaluation.intent_gates,
        completion_claim_required=evaluation.completion_claim_required,
        supported_reports=surface.supported_reports,
        supported_profiles=surface.supported_profiles,
        overrides=plan_overrides,
    )


def _overrides_with_surface_context(
    overrides: tuple[str, ...],
    *,
    surface_id: str,
    intent_id: str,
    goal_contract_json: str,
) -> tuple[str, ...]:
    merged = _without_override(
        _without_override(_without_override(overrides, "surface"), "intent"),
        "goal_contract_json",
    )
    if _override_value(merged, "task_surface") is None:
        merged = (*merged, f"task_surface={surface_id}")
    if _override_value(merged, "task_intent") is None:
        merged = (*merged, f"task_intent={intent_id}")
    if _override_value(merged, "goal_contract_json") is None:
        merged = (*merged, f"goal_contract_json={goal_contract_json}")
    return merged


def _without_launch_only_overrides(overrides: tuple[str, ...]) -> tuple[str, ...]:
    result = overrides
    for key in (
        "task_surface",
        "task_intent",
        "goal_contract_json",
        "goal_contract_path",
        "evidence_lane",
        "profile",
        "report",
    ):
        result = _without_override(result, key)
    return result
