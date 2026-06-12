"""Public surface launch catalog.

The public launch catalog resolves orthogonal launch axes:

``surface`` + ``world`` + ``backend`` + ``intent`` + ``agent_engine`` +
``provider_profile`` + evidence/report mode + ``scenario_setup``.

The current implementation still lowers to the private ``agent::run``
dispatcher. That dispatcher may call older implementation recipes, but the
catalog emits launch-shaped private dispatch targets rather than legacy public
task ids.
"""

from __future__ import annotations

from roboclaws.household.evidence_lane_policy import evidence_lane_compatibility
from roboclaws.household.profiles import (
    cleanup_evidence_lane_names,
    validate_evidence_lane_camera_labeler,
)
from roboclaws.household.tasks import HOUSEHOLD_TASK_SPECS
from roboclaws.launch.agent_engines import AGENT_ENGINE_SPECS, AgentEngineSpec
from roboclaws.launch.backends import BACKEND_SPECS, BackendSpec
from roboclaws.launch.environment_setup import (
    ENVIRONMENT_SETUP_BASELINE,
    ENVIRONMENT_SETUP_OPTIONS,
    ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS,
    RELOCATION_SETUP_OPTIONS,
)
from roboclaws.launch.evaluation import evaluation_spec_for_intent
from roboclaws.launch.goals import normalize_goal_contract
from roboclaws.launch.intents import TASK_INTENT_SPECS, TaskIntentSpec
from roboclaws.launch.plans import LaunchPlan
from roboclaws.launch.runners import build_agent_run_argv
from roboclaws.launch.task_specs import TaskSurfaceSpec
from roboclaws.launch.worlds import DEFAULT_WORLD_BY_SURFACE, WORLD_SPECS, WorldSpec

CANONICAL_SURFACES: set[str] = {
    "household-world",
    "planner-proof",
}

CANONICAL_INTENTS: set[str] = set(TASK_INTENT_SPECS)
CANONICAL_AGENT_ENGINES: set[str] = set(AGENT_ENGINE_SPECS)

SURFACE_SPECS: dict[str, TaskSurfaceSpec] = {
    **HOUSEHOLD_TASK_SPECS,
}

SUPPORTED_SURFACE_ROUTES: set[tuple[str, str, str]] = {
    (surface_id, intent_id, dispatch_runner)
    for surface_id, spec in SURFACE_SPECS.items()
    for intent_id in spec.supported_intents
    for dispatch_runner in spec.supported_dispatch_runners
    if dispatch_runner in TASK_INTENT_SPECS[intent_id].supported_dispatch_runners
}


class LaunchError(ValueError):
    """User-facing launch resolution error."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


def resolve_surface_launch(args: list[str] | tuple[str, ...]) -> LaunchPlan:
    """Resolve ``just run::surface`` named arguments into a launch plan."""

    overrides = tuple(args)
    _reject_removed_public_axes(overrides)

    surface_value = _override_value(overrides, "surface")
    agent_engine_value = _override_value(overrides, "agent_engine")
    if not surface_value or not agent_engine_value:
        raise LaunchError(
            "run::surface requires named surface= and agent_engine=",
            "usage: just run::surface surface=<surface> agent_engine=<agent-engine> "
            "[world=<world>] [backend=<backend>] [intent=<intent>] "
            "[report=<report>|evidence_lane=<lane>] [key=value ...]",
        )

    surface_id = _normalize_surface(surface_value)
    surface = SURFACE_SPECS[surface_id]
    world = _normalize_world(_override_value(overrides, "world"), surface_id=surface_id)
    backend = _normalize_backend(_override_value(overrides, "backend"), world=world)
    agent_engine = _normalize_agent_engine(agent_engine_value)
    provider_profile = _override_value(overrides, "provider_profile")
    prompt = _override_value(overrides, "prompt") or ""
    intent = TASK_INTENT_SPECS[
        _normalize_intent(_override_value(overrides, "intent"), surface=surface, prompt=prompt)
    ]

    stripped_overrides = overrides
    for key in (
        "surface",
        "world",
        "backend",
        "agent_engine",
        "provider_profile",
        "intent",
    ):
        stripped_overrides = _without_override(stripped_overrides, key)

    return _resolve_launch(
        surface=surface,
        intent=intent,
        world=world,
        backend=backend,
        agent_engine=agent_engine,
        provider_profile=provider_profile,
        raw_mode="",
        overrides=stripped_overrides,
        prompt=prompt,
    )


def _resolve_launch(
    *,
    surface: TaskSurfaceSpec,
    intent: TaskIntentSpec,
    world: WorldSpec,
    backend: BackendSpec,
    agent_engine: AgentEngineSpec,
    provider_profile: str | None,
    raw_mode: str,
    overrides: tuple[str, ...],
    prompt: str,
) -> LaunchPlan:
    if surface.surface_id not in intent.surface_ids:
        raise LaunchError(
            f"intent '{intent.intent_id}' cannot run on surface '{surface.surface_id}'"
        )

    dispatch_runner = _dispatch_runner_for_selection(
        agent_engine=agent_engine,
        intent=intent,
        raw_mode=raw_mode,
        overrides=overrides,
    )
    if (surface.surface_id, intent.intent_id, dispatch_runner) not in SUPPORTED_SURFACE_ROUTES:
        raise LaunchError(
            f"agent_engine '{agent_engine.id}' cannot run surface '{surface.surface_id}' "
            f"intent '{intent.intent_id}'"
        )

    resolved_provider_profile = _resolve_provider_profile(
        agent_engine=agent_engine,
        provider_profile=provider_profile,
    )
    evidence_mode, profile, report, overrides = _resolve_evidence_mode(surface, raw_mode, overrides)
    if profile and profile != "smoke":
        lane_compatibility = evidence_lane_compatibility(
            evidence_lane=profile,
            agent_engine=agent_engine.id,
            provider_profile=resolved_provider_profile,
        )
        if not lane_compatibility.allowed:
            raise LaunchError(str(lane_compatibility.reason))
    overrides = _merge_default_overrides(overrides, world.default_overrides)
    overrides = _merge_default_overrides(overrides, backend.default_overrides)
    overrides, dispatch_setup_overrides = _normalize_scenario_setup_overrides(
        overrides,
        surface=surface,
        intent=intent,
    )
    goal_contract = normalize_goal_contract(surface=surface, intent=intent, raw_prompt=prompt)
    plan_overrides = _overrides_with_surface_context(
        overrides,
        surface_id=surface.surface_id,
        intent_id=intent.intent_id,
        world_id=world.id,
        backend_id=backend.id,
        agent_engine_id=agent_engine.id,
        provider_profile=resolved_provider_profile,
        goal_contract_json=goal_contract.to_json(),
    )
    dispatch_overrides = (
        *_without_launch_only_overrides(plan_overrides),
        f"backend={backend.implementation_backend}",
        *dispatch_setup_overrides,
    )
    argv = build_agent_run_argv(
        dispatch_target=intent.dispatch_target,
        agent_engine=agent_engine.id,
        mode=evidence_mode,
        overrides=dispatch_overrides,
    )
    evaluation = evaluation_spec_for_intent(intent)
    return LaunchPlan(
        argv=argv,
        surface=surface.surface_id,
        intent=intent.intent_id,
        world=world.id,
        backend=backend.id,
        implementation_backend=backend.implementation_backend,
        agent_engine=agent_engine.id,
        provider_profile=resolved_provider_profile,
        internal_runner_class=_internal_runner_class(
            agent_engine=agent_engine,
            dispatch_runner=dispatch_runner,
            evidence_mode=evidence_mode,
        ),
        dispatch_runner=dispatch_runner,
        dispatch_target=intent.dispatch_target,
        evidence_mode=evidence_mode,
        profile=profile,
        report=report,
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


def _reject_removed_public_axes(overrides: tuple[str, ...]) -> None:
    if _override_value(overrides, "driver"):
        raise LaunchError(
            "driver= is no longer a public run::surface argument",
            "use agent_engine=codex-cli|claude-code|openai-agents-sdk|direct-runner",
        )
    if _override_value(overrides, "map_mode"):
        raise LaunchError(
            "map_mode= is no longer a public run::surface argument",
            "Base Navigation Map is the start-of-run map contract; "
            "use runtime_map_prior=<path> to supply Runtime Metric Map evidence",
        )
    if _override_value(overrides, "environment_setup"):
        raise LaunchError(
            "environment_setup= is no longer a public run::surface argument",
            "use scenario_setup=baseline|relocate-loose-objects|relocate-cleanup-related-objects",
        )


def _strip_named(value: str, name: str) -> str:
    prefix = f"{name}="
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _normalize_surface(value: str) -> str:
    surface = _strip_named(value, "surface")
    if surface not in CANONICAL_SURFACES:
        raise LaunchError(
            f"unsupported surface '{surface}'",
            "expected household-world|planner-proof",
        )
    return surface


def _normalize_world(value: str | None, *, surface_id: str) -> WorldSpec:
    world_id = _strip_named(value, "world") if value else DEFAULT_WORLD_BY_SURFACE[surface_id]
    spec = WORLD_SPECS.get(world_id)
    if spec is None:
        raise LaunchError(f"unsupported world '{world_id}'")
    if spec.surface_id != surface_id:
        raise LaunchError(
            f"world '{world_id}' cannot run surface '{surface_id}'",
            f"world '{world_id}' belongs to surface '{spec.surface_id}'",
        )
    return spec


def _normalize_backend(value: str | None, *, world: WorldSpec) -> BackendSpec:
    backend_id = _strip_named(value, "backend") if value else world.default_backend
    spec = BACKEND_SPECS.get(backend_id)
    if spec is None:
        raise LaunchError(f"unsupported backend '{backend_id}'")
    if backend_id not in world.available_backends:
        raise LaunchError(
            f"backend '{backend_id}' cannot run world '{world.id}'",
            f"expected {'|'.join(world.available_backends)}",
        )
    return spec


def _normalize_agent_engine(value: str) -> AgentEngineSpec:
    agent_engine = _strip_named(value, "agent_engine")
    spec = AGENT_ENGINE_SPECS.get(agent_engine)
    if spec is None:
        raise LaunchError(
            f"unsupported agent_engine '{agent_engine}'",
            "expected codex-cli|claude-code|openai-agents-sdk|direct-runner|"
            "openclaw-gateway|script-runner",
        )
    return spec


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
        if _override_value(overrides, "profile") is not None:
            raise LaunchError(
                "profile= is no longer a public run::surface argument",
                "use evidence_lane=world-oracle-labels|world-public-labels|"
                "camera-grounded-labels|camera-raw-fpv",
            )
        run_preset = _override_value(overrides, "run_preset") or _override_value(
            overrides, "preset"
        )
        if run_preset and run_preset != "smoke":
            raise LaunchError("unsupported run_preset", "expected smoke")
        evidence_lane = raw_mode or _override_value(overrides, "evidence_lane")
        if evidence_lane == "smoke":
            raise LaunchError(
                "smoke is not an evidence lane",
                "use run_preset=smoke with evidence_lane=world-oracle-labels",
            )
        profile = evidence_lane or surface.default_profile
        if profile not in surface.supported_profiles:
            raise LaunchError(
                f"unsupported household-world evidence_lane '{raw_mode}'",
                f"expected {'|'.join(cleanup_evidence_lane_names())}",
            )
        camera_labeler = _override_value(overrides, "camera_labeler")
        visual_grounding = _override_value(overrides, "visual_grounding")
        if visual_grounding:
            raise LaunchError(
                "visual_grounding is no longer a public task axis",
                "use camera_labeler=<labeler> with evidence_lane=camera-grounded-labels",
            )
        try:
            validate_evidence_lane_camera_labeler(
                evidence_lane=profile,
                camera_labeler=camera_labeler,
            )
        except ValueError as exc:
            raise LaunchError(str(exc)) from exc
        if run_preset == "smoke":
            return "smoke", "smoke", None, overrides
        return profile, profile, None, overrides

    report = raw_mode or _override_value(overrides, "report") or surface.default_report
    if report not in surface.supported_reports:
        raise LaunchError(f"unsupported report '{report}'", "expected visual|minimal")
    return report, None, report, overrides


def _resolve_provider_profile(
    *,
    agent_engine: AgentEngineSpec,
    provider_profile: str | None,
) -> str | None:
    if not agent_engine.supported_provider_profiles:
        if provider_profile:
            raise LaunchError(f"agent_engine '{agent_engine.id}' does not accept provider_profile")
        return None
    selected = provider_profile or agent_engine.default_provider_profile
    if selected not in agent_engine.supported_provider_profiles:
        raise LaunchError(
            f"provider_profile '{selected}' is unsupported for agent_engine '{agent_engine.id}'",
            f"expected {'|'.join(agent_engine.supported_provider_profiles)}",
        )
    return selected


def _dispatch_runner_for_selection(
    *,
    agent_engine: AgentEngineSpec,
    intent: TaskIntentSpec,
    raw_mode: str,
    overrides: tuple[str, ...],
) -> str:
    if agent_engine.id == "direct-runner":
        run_preset = _override_value(overrides, "run_preset") or _override_value(
            overrides, "preset"
        )
        if run_preset == "smoke" and intent.intent_id in {"cleanup", "open-ended"}:
            return "mcp-smoke"
    return agent_engine.dispatch_runner


def _internal_runner_class(
    *,
    agent_engine: AgentEngineSpec,
    dispatch_runner: str,
    evidence_mode: str,
) -> str:
    if dispatch_runner == "mcp-smoke" or evidence_mode == "smoke":
        return "smoke"
    return agent_engine.internal_runner_class


def _merge_default_overrides(
    overrides: tuple[str, ...],
    defaults: tuple[str, ...],
) -> tuple[str, ...]:
    merged = overrides
    for item in defaults:
        key = _override_key(item)
        if key and _override_value(merged, key) is None:
            merged = (*merged, item)
    return merged


def _normalize_scenario_setup_overrides(
    overrides: tuple[str, ...],
    *,
    surface: TaskSurfaceSpec,
    intent: TaskIntentSpec,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if surface.surface_id != "household-world":
        return overrides, ()
    if _override_value(overrides, "environment_setup") is not None:
        raise LaunchError(
            "environment_setup= is no longer a public run::surface argument",
            "use scenario_setup=baseline|relocate-loose-objects|relocate-cleanup-related-objects",
        )
    if _override_value(overrides, "generated_mess_count") is not None:
        raise LaunchError(
            "generated_mess_count is no longer a public run::surface argument",
            "use scenario_setup=baseline|relocate-loose-objects|"
            "relocate-cleanup-related-objects and relocation_count=<N>",
        )
    default_setup = (
        ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS
        if intent.intent_id == "cleanup"
        else ENVIRONMENT_SETUP_BASELINE
    )
    setup = _override_value(overrides, "scenario_setup") or default_setup
    if setup not in ENVIRONMENT_SETUP_OPTIONS:
        raise LaunchError(
            f"unsupported scenario_setup '{setup}'",
            f"expected {'|'.join(ENVIRONMENT_SETUP_OPTIONS)}",
        )
    relocation_count = _override_value(overrides, "relocation_count")
    private_count = "0"
    if setup in RELOCATION_SETUP_OPTIONS:
        relocation_count = relocation_count or "5"
        _parse_nonnegative_int(relocation_count, key="relocation_count")
        private_count = relocation_count
    elif relocation_count not in {None, "", "0"}:
        raise LaunchError(
            "relocation_count is only valid when scenario_setup relocates objects",
            "use scenario_setup=relocate-loose-objects or "
            "scenario_setup=relocate-cleanup-related-objects",
        )
    merged = _without_override(
        _without_override(
            _without_override(overrides, "scenario_setup"),
            "relocation_count",
        ),
        "generated_mess_count",
    )
    merged = (*merged, f"scenario_setup={setup}")
    if setup in RELOCATION_SETUP_OPTIONS:
        merged = (*merged, f"relocation_count={relocation_count}")
    return merged, (f"generated_mess_count={private_count}",)


def _overrides_with_surface_context(
    overrides: tuple[str, ...],
    *,
    surface_id: str,
    intent_id: str,
    world_id: str,
    backend_id: str,
    agent_engine_id: str,
    provider_profile: str | None,
    goal_contract_json: str,
) -> tuple[str, ...]:
    merged = overrides
    for key in (
        "surface",
        "intent",
        "world",
        "backend",
        "agent_engine",
        "provider_profile",
        "goal_contract_json",
    ):
        merged = _without_override(merged, key)
    if _override_value(merged, "task_surface") is None:
        merged = (*merged, f"task_surface={surface_id}")
    if _override_value(merged, "task_intent") is None:
        merged = (*merged, f"task_intent={intent_id}")
    if _override_value(merged, "world") is None:
        merged = (*merged, f"world={world_id}")
    if _override_value(merged, "backend") is None:
        merged = (*merged, f"backend={backend_id}")
    if _override_value(merged, "agent_engine") is None:
        merged = (*merged, f"agent_engine={agent_engine_id}")
    if provider_profile and _override_value(merged, "provider_profile") is None:
        merged = (*merged, f"provider_profile={provider_profile}")
    if _override_value(merged, "goal_contract_json") is None:
        merged = (*merged, f"goal_contract_json={goal_contract_json}")
    return merged


def _without_launch_only_overrides(overrides: tuple[str, ...]) -> tuple[str, ...]:
    result = overrides
    for key in (
        "task_surface",
        "task_intent",
        "world",
        "backend",
        "agent_engine",
        "provider_profile",
        "goal_contract_json",
        "goal_contract_path",
        "evidence_lane",
        "profile",
        "report",
        "run_preset",
        "preset",
        "scenario_setup",
        "relocation_count",
    ):
        result = _without_override(result, key)
    return result


def _parse_nonnegative_int(raw: str, *, key: str) -> int:
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise LaunchError(f"{key} must be an integer") from exc
    if value < 0:
        raise LaunchError(f"{key} must be >= 0")
    return value


def _override_key(item: str) -> str:
    if "=" not in item:
        return ""
    return item.split("=", 1)[0].removeprefix("--").replace("-", "_")
