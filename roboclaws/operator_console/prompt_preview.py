"""Operator-console prompt previews for live agent routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roboclaws.agents.prompts.household_cleanup import (
    PROMPT_MODE_COMPACT,
    PROMPT_MODE_FULL,
    PROMPT_MODE_RAW_FPV_COMPACT,
    render_kickoff_prompt,
    render_semantic_map_build_prompt,
)
from roboclaws.launch.catalog import LaunchError, resolve_surface_launch
from roboclaws.operator_console.routes import ConsoleLaunchSelection

CODEX_RUNNER_WRAPPER_SUMMARY = (
    "Codex CLI receives an additional live-route wrapper that blocks coding/developer "
    "tools, planning/resource helpers, and provider-prefixed MCP names before this "
    "household kickoff prompt."
)
AGIBOT_MAP_BUILD_WRAPPER_SUMMARY = (
    "Agibot map-build adds a live-route wrapper that restricts the agent to public "
    "metric_map, navigate_to_waypoint, observe, and done behavior."
)
PROMPT_PREVIEW_ENV_KEYS = (
    "ROBOCLAWS_OPENAI_AGENTS_PROMPT_MODE",
    "ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE",
    "ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_CANDIDATE_BUDGET",
    "ROBOCLAWS_OPENAI_AGENTS_MAX_OBSERVE_PER_WAYPOINT",
    "ROBOCLAWS_OPENAI_AGENTS_DONE_RETRY_BUDGET",
    "ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_COMPOSITE_TOOLS",
)


@dataclass(frozen=True)
class PromptPreviewRequest:
    """Resolved prompt-preview inputs from the operator console."""

    intent_id: str = ""
    prompt: str = ""
    overrides: dict[str, str] | None = None
    env_overrides: dict[str, str] | None = None


def build_prompt_preview(
    route: ConsoleLaunchSelection,
    request: PromptPreviewRequest | None = None,
) -> dict[str, Any]:
    """Return the prompt text an operator should expect the route to send."""

    request = request or PromptPreviewRequest()
    selected_intent = str(request.intent_id or route.intent_id)
    raw_prompt = " ".join(str(request.prompt or "").split())
    operator_prompt = _operator_prompt(route, selected_intent, raw_prompt)
    overrides = {str(key): str(value) for key, value in (request.overrides or {}).items()}
    env_overrides = {str(key): str(value) for key, value in (request.env_overrides or {}).items()}
    lane = route.evidence_lane
    prompt_mode = _prompt_mode(route=route, evidence_lane=lane, env_overrides=env_overrides)
    target_cleanup_count = _target_cleanup_count(
        selected_intent=selected_intent,
        evidence_lane=lane,
        scenario_setup=overrides.get("scenario_setup") or route.scenario_setup,
        relocation_count=overrides.get("relocation_count"),
    )
    raw_budget = _positive_int(
        env_overrides.get("ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_CANDIDATE_BUDGET"),
        default=24,
    )
    max_observe = _positive_int(
        env_overrides.get("ROBOCLAWS_OPENAI_AGENTS_MAX_OBSERVE_PER_WAYPOINT"),
        default=1,
    )
    done_retry_budget = _nonnegative_int(
        env_overrides.get("ROBOCLAWS_OPENAI_AGENTS_DONE_RETRY_BUDGET"),
        default=1,
    )
    composite_tools = _truthy(
        env_overrides.get("ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_COMPOSITE_TOOLS")
    )

    kickoff_prompt = operator_prompt
    source = "operator-task"
    if route.surface == "household-world":
        if selected_intent == "map-build":
            kickoff_prompt = render_semantic_map_build_prompt(lane, operator_prompt)
            source = "household-map-build"
        elif selected_intent in {"cleanup", "open-ended"}:
            kickoff_prompt = render_kickoff_prompt(
                lane,
                task=operator_prompt,
                target_cleanup_count=target_cleanup_count,
                intent=selected_intent,
                goal_contract=_goal_contract(route, selected_intent, raw_prompt, overrides),
                prompt_mode=prompt_mode,
                raw_fpv_candidate_budget=raw_budget,
                max_observe_per_waypoint=max_observe,
                done_retry_budget=done_retry_budget,
                camera_grounded_composite_tools=composite_tools,
            )
            source = (
                "household-open-task" if selected_intent == "open-ended" else "household-cleanup"
            )

    wrapper_notes = _wrapper_notes(route)
    return {
        "operator_prompt": operator_prompt,
        "raw_operator_prompt": raw_prompt,
        "agent_kickoff_prompt": kickoff_prompt,
        "prompt": kickoff_prompt,
        "source": source,
        "intent": selected_intent,
        "evidence_lane": lane,
        "prompt_mode": prompt_mode,
        "target_cleanup_count": target_cleanup_count,
        "wrapper_notes": wrapper_notes,
        "summary": _summary(source=source, prompt_mode=prompt_mode, wrapper_notes=wrapper_notes),
    }


def _operator_prompt(route: ConsoleLaunchSelection, intent_id: str, prompt: str) -> str:
    if prompt:
        return prompt
    return route.task_prompt_default or _default_prompt_for_intent(intent_id)


def _default_prompt_for_intent(intent_id: str) -> str:
    if intent_id == "map-build":
        return "帮我建立这个房间的语义地图"
    if intent_id == "open-ended":
        return "在这个场景中完成开放性导航任务，并报告你看到的证据。"
    return "帮我收拾这个房间"


def prompt_preview_env(
    env: dict[str, str] | None = None,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return non-secret env values that affect prompt rendering."""

    preview_env = {
        key: str(value) for key in PROMPT_PREVIEW_ENV_KEYS if env and (value := env.get(key))
    }
    for key, value in (env_overrides or {}).items():
        if key in PROMPT_PREVIEW_ENV_KEYS and str(value) != "":
            preview_env[key] = str(value)
    return preview_env


def _goal_contract(
    route: ConsoleLaunchSelection,
    intent_id: str,
    raw_prompt: str,
    overrides: dict[str, str],
) -> Any:
    args = [
        f"surface={route.surface}",
        f"world={route.world_id}",
        f"backend={route.backend_id}",
        f"agent_engine={route.agent_engine_id}",
        f"evidence_lane={route.evidence_lane}",
        f"scenario_setup={overrides.get('scenario_setup') or route.scenario_setup}",
    ]
    if intent_id in {"cleanup", "map-build"}:
        args.insert(3, f"preset={intent_id}")
    elif intent_id:
        args.insert(3, f"intent={intent_id}")
    provider_profile = overrides.get("provider_profile") or route.provider_profile
    if provider_profile:
        args.append(f"provider_profile={provider_profile}")
    if raw_prompt:
        args.append(f"prompt={raw_prompt}")
    present_keys = {_override_key(item) for item in args}
    for item in route.launch_default_overrides:
        key = _override_key(item)
        if key and key not in present_keys:
            args.append(item)
            present_keys.add(key)
    for key, value in sorted(overrides.items()):
        if key in {"scenario_setup", "provider_profile"}:
            continue
        if value:
            args.append(f"{key}={value}")
    try:
        return resolve_surface_launch(args).goal_contract
    except LaunchError:
        return None


def _prompt_mode(
    *,
    route: ConsoleLaunchSelection,
    evidence_lane: str,
    env_overrides: dict[str, str],
) -> str:
    if route.agent_engine_id != "openai-agents-sdk":
        return PROMPT_MODE_FULL
    explicit = str(env_overrides.get("ROBOCLAWS_OPENAI_AGENTS_PROMPT_MODE") or "").strip()
    if explicit:
        return explicit
    perf_profile = str(env_overrides.get("ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE") or "").strip()
    if perf_profile in {"gpt_compact_v1", "mimo_compact_v1"}:
        return PROMPT_MODE_COMPACT
    if perf_profile == "raw_fpv_budgeted_v1":
        return PROMPT_MODE_RAW_FPV_COMPACT
    if evidence_lane == "camera-raw-fpv" and perf_profile == "raw_fpv_budgeted_v1":
        return PROMPT_MODE_RAW_FPV_COMPACT
    return PROMPT_MODE_FULL


def _target_cleanup_count(
    *,
    selected_intent: str,
    evidence_lane: str,
    scenario_setup: str,
    relocation_count: str | None,
) -> int:
    if selected_intent != "cleanup":
        return 7
    try:
        count = int(
            str(
                relocation_count
                if relocation_count not in {None, ""}
                else ("0" if scenario_setup == "baseline" else "5")
            )
        )
    except ValueError:
        count = 0
    if count <= 0:
        count = 0
    if evidence_lane == "camera-raw-fpv":
        return max(1, (count * 7 + 9) // 10) if count else 1
    return max(1, count) if count else 1


def _positive_int(value: str | None, *, default: int) -> int:
    try:
        parsed = int(str(value or ""))
    except ValueError:
        return default
    return max(1, parsed)


def _nonnegative_int(value: str | None, *, default: int) -> int:
    try:
        parsed = int(str(value or ""))
    except ValueError:
        return default
    return max(0, parsed)


def _truthy(value: str | None) -> bool:
    return str(value or "").strip() in {"1", "true", "True", "TRUE", "yes", "Yes", "YES", "on"}


def _wrapper_notes(route: ConsoleLaunchSelection) -> list[str]:
    notes: list[str] = []
    if route.agent_engine_id == "codex-cli":
        notes.append(CODEX_RUNNER_WRAPPER_SUMMARY)
    if route.world_id == "agibot-g2/map-12" and route.intent_id == "map-build":
        notes.append(AGIBOT_MAP_BUILD_WRAPPER_SUMMARY)
    return notes


def _summary(*, source: str, prompt_mode: str, wrapper_notes: list[str]) -> str:
    parts = [f"{source} kickoff prompt", f"mode={prompt_mode}"]
    if wrapper_notes:
        parts.append("plus live-route wrapper")
    return "; ".join(parts)


def _override_key(item: str) -> str:
    if "=" not in item:
        return ""
    return item.split("=", 1)[0].removeprefix("--").replace("-", "_")
