"""Runner command builders for launch plans."""

from __future__ import annotations

from roboclaws.launch.environment_setup_metadata import (
    ENVIRONMENT_SETUP_METADATA_ENV,
    environment_setup_metadata_json,
)


def build_agent_run_argv(
    *,
    dispatch_target: str,
    agent_engine: str,
    mode: str,
    overrides: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the private dispatcher command for a public launch route."""

    return ("just", "agent::run", dispatch_target, agent_engine, mode, *overrides)


def export_env_from_overrides(overrides: tuple[str, ...]) -> dict[str, str]:
    """Return environment variables implied by launch-only overrides."""

    env: dict[str, str] = {}
    for override in overrides:
        if override.startswith("goal_contract_json="):
            env["ROBOCLAWS_GOAL_CONTRACT_JSON"] = override.removeprefix("goal_contract_json=")
        elif override.startswith("goal_contract_path="):
            env["ROBOCLAWS_GOAL_CONTRACT_PATH"] = override.removeprefix("goal_contract_path=")
        elif override.startswith("task_surface="):
            env["ROBOCLAWS_TASK_SURFACE"] = override.removeprefix("task_surface=")
        elif override.startswith("task_intent="):
            env["ROBOCLAWS_TASK_INTENT"] = override.removeprefix("task_intent=")
    agent_engine = _override_value(overrides, "agent_engine")
    provider_profile = _override_value(overrides, "provider_profile")
    if agent_engine == "codex-cli" and provider_profile:
        env["ROBOCLAWS_CODEX_PROVIDER"] = provider_profile
    elif agent_engine == "claude-code" and provider_profile:
        env["ROBOCLAWS_CLAUDE_PROVIDER"] = provider_profile
    elif agent_engine == "openai-agents-sdk" and provider_profile:
        env["ROBOCLAWS_CODEX_PROVIDER"] = provider_profile
    setup = _override_value(overrides, "scenario_setup")
    if setup:
        env[ENVIRONMENT_SETUP_METADATA_ENV] = environment_setup_metadata_json(
            setup=setup,
            seed=_override_value(overrides, "seed"),
            relocation_count=_override_value(overrides, "relocation_count"),
        )
    return env


def _override_value(overrides: tuple[str, ...], key: str) -> str | None:
    prefix = f"{key}="
    for override in overrides:
        if override.startswith(prefix):
            return override.removeprefix(prefix)
    return None
