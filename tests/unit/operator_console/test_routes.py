from __future__ import annotations

import pytest

from roboclaws.operator_console.launcher import ConsoleLaunchError, build_launch_argv
from roboclaws.operator_console.routes import (
    get_route,
    list_console_routes,
    validate_supported_routes_against_catalog,
)


def test_route_registry_exposes_supported_agent_targets() -> None:
    enabled = list_console_routes(include_disabled=False)
    assert {route.id for route in enabled} == {
        "codex-mujoco-cleanup",
        "claude-mujoco-cleanup",
        "codex-isaac-cleanup",
        "claude-isaac-cleanup",
        "codex-agibot-g2-map-build",
        "codex-mujoco-map-build",
        "codex-isaac-map-build",
    }
    assert {route.driver for route in enabled} == {"codex", "claude"}
    assert {
        (route.task, route.driver, route.profile, route.backend, route.lock_name)
        for route in enabled
    } == {
        (
            "household-cleanup",
            "codex",
            "world-labels",
            "molmospaces_subprocess",
            "molmospaces_mujoco",
        ),
        (
            "household-cleanup",
            "claude",
            "world-labels",
            "molmospaces_subprocess",
            "molmospaces_mujoco",
        ),
        ("household-cleanup", "codex", "world-labels", "isaaclab_subprocess", "isaac_gpu"),
        ("household-cleanup", "claude", "world-labels", "isaaclab_subprocess", "isaac_gpu"),
        ("semantic-map-build", "codex", "camera-labels", "agibot_gdk", "agibot_g2"),
        (
            "semantic-map-build",
            "codex",
            "world-labels",
            "molmospaces_subprocess",
            "molmospaces_mujoco",
        ),
        ("semantic-map-build", "codex", "world-labels", "isaaclab_subprocess", "isaac_gpu"),
    }
    validate_supported_routes_against_catalog()


def test_disabled_routes_have_concrete_blockers() -> None:
    disabled = [route for route in list_console_routes() if not route.enabled]
    assert disabled
    assert all(route.disabled_reason for route in disabled)
    assert get_route("agibot-g2-cleanup").disabled_reason == (
        "Physical manipulation is blocked. Run Agibot G2 Map Build first."
    )
    assert get_route("claude-map-build").disabled_reason == (
        "semantic-map-build does not support the Claude driver yet."
    )


def test_prompt_gating_uses_argv_element_not_shell_joining(tmp_path) -> None:
    route = get_route("codex-mujoco-cleanup")
    argv = build_launch_argv(
        route,
        root=tmp_path,
        run_id="run-1",
        prompt="collect mugs; rm -rf / should stay text",
    )
    assert argv[:4] == ["just", "task::run", "household-cleanup", "codex"]
    assert "backend=molmospaces_subprocess" in argv
    assert "prompt=collect mugs; rm -rf / should stay text" in argv


def test_prompt_rejected_for_unsupported_route(tmp_path) -> None:
    route = get_route("agibot-g2-cleanup")
    with pytest.raises(ConsoleLaunchError, match="custom prompt"):
        build_launch_argv(route, root=tmp_path, run_id="run-1", prompt="unsafe")
