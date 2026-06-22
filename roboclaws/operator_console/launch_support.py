"""Focused helpers for operator-console launch validation and cleanup."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from roboclaws.agents.provider_registry import provider_route_spec
from roboclaws.operator_console.routes import ConsoleLaunchSelection

ALLOWED_ENV_OVERRIDES = {"ROBOCLAWS_PROVIDER_PROFILE"}
RunCommand = Callable[..., Any]


def validate_env_overrides(
    route: ConsoleLaunchSelection,
    env_overrides: dict[str, str],
    *,
    error_type: type[ValueError] = ValueError,
) -> None:
    if env_overrides and route.agent_engine_id not in {
        "codex-cli",
        "claude-code",
        "openai-agents-sdk",
    }:
        raise error_type("provider overrides are only supported for coding-agent routes")
    for key, value in env_overrides.items():
        _validate_env_override(route, key, value, error_type=error_type)


def _validate_env_override(
    route: ConsoleLaunchSelection,
    key: str,
    value: str,
    *,
    error_type: type[ValueError],
) -> None:
    if key not in ALLOWED_ENV_OVERRIDES:
        raise error_type(f"unsupported provider override: {key}")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise error_type(f"invalid control character in provider override: {key}")
    if key == "ROBOCLAWS_PROVIDER_PROFILE":
        _validate_provider_override(
            route,
            value,
            {"codex-cli", "claude-code", "openai-agents-sdk"},
            provider_label="provider profile",
            error_type=error_type,
        )


def _validate_provider_override(
    route: ConsoleLaunchSelection,
    value: str,
    allowed_engines: set[str],
    *,
    provider_label: str,
    error_type: type[ValueError],
) -> None:
    if route.agent_engine_id not in allowed_engines:
        raise error_type(f"{provider_label} override is not supported for this route")
    try:
        route_spec = provider_route_spec(value)
    except KeyError:
        route_spec = None
    if route_spec is None or route.agent_engine_id not in route_spec.supported_engines:
        expected = ", ".join(route.to_payload()["supported_provider_profiles"])
        raise error_type(
            f"unsupported {provider_label} override: {value}; expected {expected}"
        )


def docker_container_ids_with_mount(
    source: Path,
    *,
    run_command: RunCommand = subprocess.run,
) -> list[str]:
    result = _docker_ps(run_command)
    if result is None:
        return []
    container_ids: list[str] = []
    for container_id in result.stdout.split():
        if _docker_container_mounts_source(container_id, source, run_command=run_command):
            container_ids.append(container_id)
    return container_ids


def _docker_ps(run_command: RunCommand) -> Any | None:
    try:
        result = run_command(
            ["docker", "ps", "-q"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    return result if result.returncode == 0 else None


def _docker_container_mounts_source(
    container_id: str,
    source: Path,
    *,
    run_command: RunCommand,
) -> bool:
    mounts = _docker_container_mounts(container_id, run_command=run_command)
    return any(_mount_source_matches(mount, source) for mount in mounts)


def _docker_container_mounts(container_id: str, *, run_command: RunCommand) -> list[Any]:
    try:
        inspect = run_command(
            ["docker", "inspect", "--format", "{{json .Mounts}}", container_id],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return []
    if inspect.returncode != 0:
        return []
    try:
        mounts = json.loads(inspect.stdout)
    except json.JSONDecodeError:
        return []
    return mounts if isinstance(mounts, list) else []


def _mount_source_matches(mount: Any, source: Path) -> bool:
    if not isinstance(mount, dict):
        return False
    mount_source = mount.get("Source")
    if not mount_source:
        return False
    try:
        return Path(str(mount_source)).resolve() == source
    except OSError:
        return False
