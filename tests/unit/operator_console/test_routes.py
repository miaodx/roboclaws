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
            "world-oracle-labels",
            "molmospaces_subprocess",
            "molmospaces_mujoco",
        ),
        (
            "household-cleanup",
            "claude",
            "world-oracle-labels",
            "molmospaces_subprocess",
            "molmospaces_mujoco",
        ),
        ("household-cleanup", "codex", "world-oracle-labels", "isaaclab_subprocess", "isaac_gpu"),
        ("household-cleanup", "claude", "world-oracle-labels", "isaaclab_subprocess", "isaac_gpu"),
        ("semantic-map-build", "codex", "camera-grounded-labels", "agibot_gdk", "agibot_g2"),
        (
            "semantic-map-build",
            "codex",
            "world-oracle-labels",
            "molmospaces_subprocess",
            "molmospaces_mujoco",
        ),
        ("semantic-map-build", "codex", "world-oracle-labels", "isaaclab_subprocess", "isaac_gpu"),
    }
    validate_supported_routes_against_catalog()


def test_disabled_routes_have_concrete_blockers() -> None:
    disabled = [route for route in list_console_routes() if not route.enabled]
    assert disabled
    assert all(route.disabled_reason for route in disabled)
    assert get_route("agibot-g2-cleanup").disabled_reason == (
        "Physical manipulation is not available yet. Run Agibot G2 Map Build first."
    )
    assert get_route("claude-map-build").disabled_reason == (
        "semantic-map-build does not support the Claude driver yet."
    )


def test_route_payload_exposes_ui_field_groups_and_view_modes() -> None:
    mujoco = get_route("codex-mujoco-cleanup").to_payload()
    isaac = get_route("codex-isaac-cleanup").to_payload()
    agibot = get_route("codex-agibot-g2-map-build").to_payload()

    assert mujoco["supports_operator_steer"] is True
    assert isaac["supports_operator_steer"] is True
    assert agibot["supports_operator_steer"] is False
    assert mujoco["field_groups"] == ["common"]
    assert any(gate["id"] == "mcp_port_free" for gate in mujoco["gates"])
    assert "overview" in mujoco["view_modes"]
    assert "map" in mujoco["view_modes"]
    assert "grounding" not in mujoco["view_modes"]
    assert "outputs" in mujoco["view_modes"]

    assert isaac["field_groups"] == ["common", "isaac"]
    assert "grounding" in isaac["view_modes"]

    assert agibot["field_groups"] == ["common", "agibot", "agibot_gates"]
    assert "grounding" in agibot["view_modes"]
    assert "chase" not in agibot["view_modes"]


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
