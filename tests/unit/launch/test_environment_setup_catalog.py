from __future__ import annotations

import pytest

from roboclaws.launch.backends import (
    cleanup_implementation_backend_ids,
    map_build_codex_implementation_backend_ids,
    normalize_cleanup_implementation_backend,
    normalize_map_build_codex_implementation_backend,
)
from roboclaws.launch.catalog import SURFACE_SPECS, LaunchError, resolve_surface_launch
from roboclaws.launch.environment_setup_metadata import ENVIRONMENT_SETUP_METADATA_ENV
from roboclaws.launch.goals import normalize_goal_contract
from roboclaws.launch.intents import TASK_INTENT_SPECS
from roboclaws.launch.runners import export_env_from_overrides


def test_launch_backend_catalog_exposes_private_implementation_choices() -> None:
    assert cleanup_implementation_backend_ids() == (
        "api_semantic_synthetic",
        "molmospaces_subprocess",
        "isaaclab_subprocess",
    )
    assert map_build_codex_implementation_backend_ids() == (
        "auto",
        "molmospaces_subprocess",
        "isaaclab_subprocess",
        "agibot_gdk",
    )


def test_launch_backend_catalog_normalizes_command_layer_backend_values() -> None:
    assert normalize_cleanup_implementation_backend("auto") is None
    assert normalize_cleanup_implementation_backend("") is None
    assert normalize_cleanup_implementation_backend("isaaclab_subprocess") == (
        "isaaclab_subprocess"
    )
    assert (
        normalize_map_build_codex_implementation_backend(
            "agibot_gdk",
            context="household-world.map-build codex-cli",
        )
        == "agibot_gdk"
    )

    with pytest.raises(ValueError, match="unsupported backend 'agibot_gdk'"):
        normalize_cleanup_implementation_backend("agibot_gdk")

    with pytest.raises(
        ValueError,
        match="household-world.map-build codex-cli unsupported backend 'api_semantic_synthetic'",
    ):
        normalize_map_build_codex_implementation_backend(
            "api_semantic_synthetic",
            context="household-world.map-build codex-cli",
        )


def test_molmospaces_worlds_expose_only_mujoco_while_b1_exposes_isaac() -> None:
    molmo = resolve_surface_launch(
        [
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=map-build",
            "agent_engine=direct-runner",
            "evidence_lane=world-public-labels",
        ]
    )
    b1 = resolve_surface_launch(
        [
            "surface=household-world",
            "world=b1-map12",
            "backend=isaaclab",
            "agent_engine=codex-cli",
            "prompt=inspect the digital twin",
            "evidence_lane=world-public-labels",
        ]
    )

    assert molmo.world == "molmospaces/val_0"
    assert molmo.backend == "mujoco"
    assert molmo.implementation_backend == "molmospaces_subprocess"
    assert b1.world == "b1-map12"
    assert b1.backend == "isaaclab"
    assert b1.implementation_backend == "isaaclab_subprocess"
    assert "map_bundle=b1-map12-room-semantics" in b1.overrides
    assert "world=b1-map12" in b1.argv
    assert "backend=isaaclab_subprocess" in b1.argv


def test_molmospaces_world_rejects_public_isaac_backend() -> None:
    with pytest.raises(
        LaunchError,
        match="backend 'isaaclab' cannot run world 'molmospaces/val_0'",
    ) as exc:
        resolve_surface_launch(
            [
                "surface=household-world",
                "world=molmospaces/val_0",
                "backend=isaaclab",
                "intent=map-build",
                "agent_engine=direct-runner",
                "evidence_lane=world-public-labels",
            ]
        )

    assert exc.value.hint == "expected mujoco"


def test_cleanup_surface_exposes_setup_overrides_but_dispatches_private_count() -> None:
    plan = resolve_surface_launch(
        [
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=cleanup",
            "agent_engine=codex-cli",
            "provider_profile=codex-env",
            "evidence_lane=world-public-labels",
            "seed=7",
            "scenario_setup=relocate-cleanup-related-objects",
            "relocation_count=3",
        ]
    )

    assert "scenario_setup=relocate-cleanup-related-objects" in plan.overrides
    assert "relocation_count=3" in plan.overrides
    assert not any(item.startswith("generated_mess_count=") for item in plan.overrides)
    assert "generated_mess_count=3" in plan.argv
    assert "scenario_setup=relocate-cleanup-related-objects" not in plan.argv
    assert "relocation_count=3" not in plan.argv
    exported = export_env_from_overrides(plan.overrides)
    assert exported[ENVIRONMENT_SETUP_METADATA_ENV] == (
        '{"feeds_cleanup_scoring":true,"mode":"relocate-cleanup-related-objects",'
        '"relocated_objects":[],"relocation_count":3,'
        '"relocation_policy":"cleanup-related-objects","seed":7}'
    )


def test_household_non_cleanup_intents_default_to_baseline_setup() -> None:
    map_build = resolve_surface_launch(
        [
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=map-build",
            "agent_engine=codex-cli",
            "provider_profile=codex-env",
            "evidence_lane=world-public-labels",
        ]
    )
    open_ended = resolve_surface_launch(
        [
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=open-ended",
            "agent_engine=codex-cli",
            "provider_profile=codex-env",
            "evidence_lane=world-public-labels",
            "prompt=帮我找遥控器",
        ]
    )

    for plan in (map_build, open_ended):
        assert "scenario_setup=baseline" in plan.overrides
        assert not any(item.startswith("relocation_count=") for item in plan.overrides)
        assert not any(item.startswith("generated_mess_count=") for item in plan.overrides)
        assert "generated_mess_count=0" in plan.argv
        assert (
            '"mode":"baseline"'
            in export_env_from_overrides(plan.overrides)[ENVIRONMENT_SETUP_METADATA_ENV]
        )


def test_household_goal_contract_tool_plans_do_not_advertise_fixture_hints() -> None:
    surface = SURFACE_SPECS["household-world"]

    for intent_id in ("cleanup", "map-build", "open-ended"):
        contract = normalize_goal_contract(
            surface=surface,
            intent=TASK_INTENT_SPECS[intent_id],
            raw_prompt="find something useful to drink" if intent_id == "open-ended" else "",
        )

        tool_plan_text = " ".join(contract.tool_plan)
        assert "fixture_hints" not in tool_plan_text
        assert "metric_map" in tool_plan_text


def test_surface_rejects_old_public_generated_mess_count() -> None:
    with pytest.raises(LaunchError, match="generated_mess_count is no longer"):
        resolve_surface_launch(
            [
                "surface=household-world",
                "world=molmospaces/val_0",
                "backend=mujoco",
                "intent=cleanup",
                "agent_engine=codex-cli",
                "evidence_lane=world-public-labels",
                "generated_mess_count=3",
            ]
        )


def test_openai_agents_sdk_accepts_chat_provider_profiles() -> None:
    plan = resolve_surface_launch(
        [
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=cleanup",
            "agent_engine=openai-agents-sdk",
            "provider_profile=mimo-openai-chat",
            "evidence_lane=world-public-labels",
        ]
    )

    assert plan.provider_profile == "mimo-openai-chat"
    assert "provider_profile=mimo-openai-chat" in plan.overrides


@pytest.mark.parametrize(
    ("agent_engine", "provider_profile", "env_key"),
    (
        ("codex-cli", "mify", "ROBOCLAWS_CODEX_PROVIDER"),
        ("claude-code", "kimi-anthropic", "ROBOCLAWS_CLAUDE_PROVIDER"),
        ("openai-agents-sdk", "mimo-openai-chat", "ROBOCLAWS_CODEX_PROVIDER"),
    ),
)
def test_provider_profile_env_export_uses_agent_engine_catalog(
    agent_engine: str,
    provider_profile: str,
    env_key: str,
) -> None:
    plan = resolve_surface_launch(
        [
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=cleanup",
            f"agent_engine={agent_engine}",
            f"provider_profile={provider_profile}",
            "evidence_lane=world-public-labels",
        ]
    )

    exported = export_env_from_overrides(plan.overrides)

    assert exported[env_key] == provider_profile


@pytest.mark.parametrize("agent_engine", ["codex-cli", "openai-agents-sdk"])
def test_responses_agent_engines_accept_minimax_provider_profile(agent_engine: str) -> None:
    plan = resolve_surface_launch(
        [
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=cleanup",
            f"agent_engine={agent_engine}",
            "provider_profile=minimax",
            "evidence_lane=world-public-labels",
        ]
    )

    assert plan.provider_profile == "minimax"
    assert "provider_profile=minimax" in plan.overrides


def test_raw_fpv_rejects_routes_without_verified_image_transport() -> None:
    with pytest.raises(LaunchError, match="image_transport=unknown"):
        resolve_surface_launch(
            [
                "surface=household-world",
                "world=molmospaces/val_0",
                "backend=mujoco",
                "intent=cleanup",
                "agent_engine=codex-cli",
                "provider_profile=minimax",
                "evidence_lane=camera-raw-fpv",
            ]
        )


def test_codex_cli_rejects_openai_agents_chat_provider_profiles() -> None:
    with pytest.raises(LaunchError, match="provider_profile 'mimo-openai-chat' is unsupported"):
        resolve_surface_launch(
            [
                "surface=household-world",
                "world=molmospaces/val_0",
                "backend=mujoco",
                "intent=cleanup",
                "agent_engine=codex-cli",
                "provider_profile=mimo-openai-chat",
                "evidence_lane=world-public-labels",
            ]
        )


def test_surface_rejects_old_public_driver_and_environment_setup() -> None:
    with pytest.raises(LaunchError, match="driver= is no longer"):
        resolve_surface_launch(
            [
                "surface=household-world",
                "driver=codex",
                "intent=cleanup",
            ]
        )

    with pytest.raises(LaunchError, match="environment_setup= is no longer"):
        resolve_surface_launch(
            [
                "surface=household-world",
                "world=molmospaces/val_0",
                "backend=mujoco",
                "intent=cleanup",
                "agent_engine=codex-cli",
                "environment_setup=baseline",
            ]
        )


def test_baseline_rejects_active_relocation_count() -> None:
    with pytest.raises(LaunchError, match="relocation_count is only valid"):
        resolve_surface_launch(
            [
                "surface=household-world",
                "world=molmospaces/val_0",
                "backend=mujoco",
                "intent=cleanup",
                "agent_engine=codex-cli",
                "evidence_lane=world-public-labels",
                "scenario_setup=baseline",
                "relocation_count=3",
            ]
        )


def test_invalid_relocation_count_is_rejected() -> None:
    with pytest.raises(LaunchError, match="relocation_count must be >= 0"):
        resolve_surface_launch(
            [
                "surface=household-world",
                "world=molmospaces/val_0",
                "backend=mujoco",
                "intent=cleanup",
                "agent_engine=codex-cli",
                "evidence_lane=world-public-labels",
                "scenario_setup=relocate-loose-objects",
                "relocation_count=-1",
            ]
        )
