from __future__ import annotations

import pytest

from roboclaws.launch.catalog import LaunchError, resolve_surface_launch
from roboclaws.launch.environment_setup_metadata import ENVIRONMENT_SETUP_METADATA_ENV
from roboclaws.launch.runners import export_env_from_overrides


def test_cleanup_surface_exposes_setup_overrides_but_dispatches_private_count() -> None:
    plan = resolve_surface_launch(
        [
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=cleanup",
            "agent_engine=codex-cli",
            "provider_profile=codex-env",
            "evidence_lane=world-oracle-labels",
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
            "evidence_lane=world-oracle-labels",
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
            "evidence_lane=world-oracle-labels",
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


def test_surface_rejects_old_public_generated_mess_count() -> None:
    with pytest.raises(LaunchError, match="generated_mess_count is no longer"):
        resolve_surface_launch(
            [
                "surface=household-world",
                "world=molmospaces/val_0",
                "backend=mujoco",
                "intent=cleanup",
                "agent_engine=codex-cli",
                "evidence_lane=world-oracle-labels",
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
            "evidence_lane=world-oracle-labels",
        ]
    )

    assert plan.provider_profile == "mimo-openai-chat"
    assert "provider_profile=mimo-openai-chat" in plan.overrides


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
                "evidence_lane=world-oracle-labels",
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
                "evidence_lane=world-oracle-labels",
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
                "evidence_lane=world-oracle-labels",
                "scenario_setup=relocate-loose-objects",
                "relocation_count=-1",
            ]
        )
