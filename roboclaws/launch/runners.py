"""Runner command builders for launch plans."""

from __future__ import annotations

from roboclaws.launch.environment_setup_metadata import (
    ENVIRONMENT_SETUP_METADATA_ENV,
    environment_setup_metadata_json,
)


def build_agent_run_argv(
    *,
    task: str,
    driver: str,
    mode: str,
    overrides: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the current lower dispatcher command for a public task route."""

    return ("just", "agent::run", task, driver, mode, *overrides)


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
    setup = _override_value(overrides, "environment_setup")
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
