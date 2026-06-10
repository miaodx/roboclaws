from __future__ import annotations

import pytest

from roboclaws.operator_console.launcher import ConsoleLaunchError, build_launch_argv
from roboclaws.operator_console.routes import (
    get_route,
    get_selection,
    list_console_combinations,
    list_worlds,
    validate_supported_routes_against_catalog,
)


def test_world_catalog_exposes_scene_first_console_choices() -> None:
    worlds = {world["id"]: world for world in list_worlds()}

    assert "molmospaces/val_0" in worlds
    assert worlds["molmospaces/val_0"]["available_backends"] == ["mujoco", "isaaclab"]
    assert worlds["agibot-g2/map-12"]["available_backends"] == ["agibot-gdk"]
    assert worlds["b1-map12"]["default_backend"] == "isaaclab"


def test_console_combinations_are_catalog_backed_axes() -> None:
    enabled = list_console_combinations(include_disabled=False)

    assert {
        (
            route.world_id,
            route.backend_id,
            route.intent_id,
            route.agent_engine_id,
            route.provider_profile,
            route.evidence_lane,
        )
        for route in enabled
    } >= {
        (
            "molmospaces/val_0",
            "mujoco",
            "cleanup",
            "codex-cli",
            "codex-env",
            "world-oracle-labels",
        ),
        (
            "molmospaces/val_0",
            "mujoco",
            "cleanup",
            "claude-code",
            "mimo-anthropic",
            "world-oracle-labels",
        ),
        (
            "molmospaces/val_0",
            "mujoco",
            "cleanup",
            "openai-agents-sdk",
            "codex-env",
            "world-oracle-labels",
        ),
        (
            "molmospaces/val_0",
            "mujoco",
            "map-build",
            "codex-cli",
            "codex-env",
            "world-oracle-labels",
        ),
        (
            "agibot-g2/map-12",
            "agibot-gdk",
            "map-build",
            "codex-cli",
            "codex-env",
            "camera-grounded-labels",
        ),
        (
            "b1-map12",
            "isaaclab",
            "open-ended",
            "codex-cli",
            "codex-env",
            "world-oracle-labels",
        ),
    }
    validate_supported_routes_against_catalog()


def test_disabled_combinations_have_concrete_reasons() -> None:
    disabled = [route for route in list_console_combinations() if not route.enabled]

    assert disabled
    reasons = {route.id: route.disabled_reason for route in disabled}
    assert (
        reasons["agibot-g2/map-12::agibot-gdk::cleanup::codex-cli::camera-grounded-labels"]
        == "Physical manipulation is not available yet. Run Agibot G2 Map Build first."
    )
    assert (
        "Map-build"
        in reasons["molmospaces/val_0::mujoco::map-build::claude-code::world-oracle-labels"]
    )


def test_payload_exposes_orthogonal_ui_metadata() -> None:
    mujoco = get_selection(
        "molmospaces/val_0::mujoco::cleanup::codex-cli::world-oracle-labels"
    ).to_payload()
    isaac = get_selection(
        "molmospaces/val_0::isaaclab::cleanup::codex-cli::world-oracle-labels"
    ).to_payload()
    agibot = get_selection(
        "agibot-g2/map-12::agibot-gdk::map-build::codex-cli::camera-grounded-labels"
    ).to_payload()
    b1 = get_selection(
        "b1-map12::isaaclab::open-ended::codex-cli::world-oracle-labels"
    ).to_payload()

    assert mujoco["world_id"] == "molmospaces/val_0"
    assert mujoco["backend_id"] == "mujoco"
    assert mujoco["agent_engine_id"] == "codex-cli"
    assert mujoco["provider_profile"] == "codex-env"
    assert mujoco["scenario_setup"] == "relocate-cleanup-related-objects"
    assert "agent_engine=codex-cli" in mujoco["argv_preview"]
    assert "scenario_setup=relocate-cleanup-related-objects" in mujoco["argv_preview"]
    assert mujoco["field_groups"] == ["common"]
    assert "grounding" not in mujoco["view_modes"]

    assert isaac["field_groups"] == ["common", "isaac"]
    assert "grounding" in isaac["view_modes"]

    assert agibot["field_groups"] == ["common", "agibot", "agibot_gates"]
    assert "context_json" in agibot["required_overrides"]
    assert "grounding" in agibot["view_modes"]

    assert b1["default_intent"] == "open-ended"
    assert "map_bundle=agibot-robot-map-12" in b1["argv_preview"]
    assert "robot_views=on" in b1["argv_preview"]


def test_legacy_route_lookup_is_display_only_wrapper() -> None:
    route = get_route("codex-mujoco-cleanup")
    payload = route.to_payload()

    assert payload["legacy_route_id"] == "codex-mujoco-cleanup"
    assert payload["world_id"] == "molmospaces/val_0"
    assert payload["agent_engine_id"] == "codex-cli"


def test_prompt_gating_uses_argv_element_not_shell_joining(tmp_path) -> None:
    selection = get_selection("molmospaces/val_0::mujoco::cleanup::codex-cli::world-oracle-labels")
    argv = build_launch_argv(
        selection,
        root=tmp_path,
        run_id="run-1",
        prompt="collect mugs; rm -rf / should stay text",
    )

    assert argv[:7] == [
        "just",
        "run::surface",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=cleanup",
        "agent_engine=codex-cli",
    ]
    assert "evidence_lane=world-oracle-labels" in argv
    assert "provider_profile=codex-env" in argv
    assert "scenario_setup=relocate-cleanup-related-objects" in argv
    assert "prompt=collect mugs; rm -rf / should stay text" in argv


def test_map_build_launch_defaults_to_baseline_scenario_setup(tmp_path) -> None:
    selection = get_selection(
        "molmospaces/val_0::mujoco::map-build::codex-cli::world-oracle-labels"
    )
    argv = build_launch_argv(selection, root=tmp_path, run_id="run-1")

    assert "intent=map-build" in argv
    assert "scenario_setup=baseline" in argv
    assert not any(item.startswith("relocation_count=") for item in argv)
    assert not any(item.startswith("generated_mess_count=") for item in argv)


def test_b1_map12_open_ended_launch_uses_scene_and_map_bundle(tmp_path) -> None:
    selection = get_selection("b1-map12::isaaclab::open-ended::codex-cli::world-oracle-labels")
    argv = build_launch_argv(selection, root=tmp_path, run_id="run-1")

    assert "intent=open-ended" in argv
    assert "backend=isaaclab" in argv
    assert "scenario_setup=baseline" in argv
    assert "map_bundle=agibot-robot-map-12" in argv
    assert "robot_views=on" in argv
    assert any(item.startswith("isaac_scene_usd_path=data/robot-data-lab/") for item in argv)
    assert not any(item.startswith("relocation_count=") for item in argv)


def test_prompt_rejected_for_unsupported_selection(tmp_path) -> None:
    selection = get_selection(
        "agibot-g2/map-12::agibot-gdk::cleanup::codex-cli::camera-grounded-labels"
    )
    with pytest.raises(ConsoleLaunchError, match="custom prompt"):
        build_launch_argv(selection, root=tmp_path, run_id="run-1", prompt="unsafe")
