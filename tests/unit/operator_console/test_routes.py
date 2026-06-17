from __future__ import annotations

import json
from pathlib import Path

import pytest

import roboclaws.operator_console.routes as route_registry
from roboclaws.launch.agent_engines import agent_engine_spec
from roboclaws.launch.worlds import MOLMOSPACES_CONSOLE_WORLD_IDS
from roboclaws.operator_console.launcher import ConsoleLaunchError, build_launch_argv
from roboclaws.operator_console.routes import (
    MOLMOSPACES_MUJOCO_DEFAULT_CLEANUP_WORLD_IDS,
    get_selection,
    list_console_combinations,
    list_evidence_lanes,
    list_worlds,
    validate_supported_routes_against_catalog,
)

AGIBOT_CODEX_CLEANUP = "agibot-g2/map-12::agibot-gdk::cleanup::codex-cli::camera-grounded-labels"
AGIBOT_CODEX_MAP_BUILD = (
    "agibot-g2/map-12::agibot-gdk::map-build::codex-cli::camera-grounded-labels"
)
B1_CODEX_OPEN_TASK = "b1-map12::isaaclab::open-task::codex-cli::world-public-labels"
MUJOCO_CODEX_CLEANUP = "molmospaces/val_0::mujoco::cleanup::codex-cli::world-public-labels"
MUJOCO_CODEX_MAP_BUILD = "molmospaces/val_0::mujoco::map-build::codex-cli::world-public-labels"


def test_world_catalog_exposes_scene_first_console_choices() -> None:
    worlds = {world["id"]: world for world in list_worlds()}

    assert tuple(world_id for world_id in worlds if world_id.startswith("molmospaces/")) == (
        *MOLMOSPACES_CONSOLE_WORLD_IDS,
    )
    assert "molmospaces/val_6" not in worlds
    assert "molmospaces/val_8" not in worlds
    assert worlds["molmospaces/val_0"]["available_backends"] == ["mujoco"]
    assert worlds["molmospaces/val_5"]["available_backends"] == ["mujoco"]
    assert worlds["molmospaces/val_5"]["preview_assets"] == {
        "fpv": {
            "path": "/previews/molmospaces-val_5-fpv.png",
            "href": "/previews/molmospaces-val_5-fpv.png",
        },
        "map": {
            "path": "/previews/molmospaces-val_5-map.png",
            "href": "/previews/molmospaces-val_5-map.png",
        },
        "chase": {
            "path": "/previews/molmospaces-val_5-chase.png",
            "href": "/previews/molmospaces-val_5-chase.png",
        },
        "topdown": {
            "path": "/previews/molmospaces-val_5-topdown.png",
            "href": "/previews/molmospaces-val_5-topdown.png",
        },
    }
    assert "topdown" not in worlds["agibot-g2/map-12"]["preview_assets"]
    assert worlds["agibot-g2/map-12"]["preview_assets"]["map"]["href"] == (
        "/previews/b1-map12-map.png"
    )
    assert worlds["b1-map12"]["preview_assets"] == {
        "fpv": {
            "path": "/previews/b1-map12-fpv.png",
            "href": "/previews/b1-map12-fpv.png",
        },
        "map": {
            "path": "/previews/b1-map12-map.png",
            "href": "/previews/b1-map12-map.png",
        },
        "chase": {
            "path": "/previews/b1-map12-chase.png",
            "href": "/previews/b1-map12-chase.png",
        },
        "topdown": {
            "path": "/previews/b1-map12-topdown.png",
            "href": "/previews/b1-map12-topdown.png",
        },
    }
    assert "ai2thor/FloorPlan201" not in worlds
    assert "ai2thor-games/FloorPlan201" not in worlds
    assert worlds["planner-proof/default"]["preview_assets"] == {
        "map": {
            "path": "/previews/molmospaces-val_0-map.png",
            "href": "/previews/molmospaces-val_0-map.png",
        },
    }
    assert worlds["agibot-g2/map-12"]["available_backends"] == ["agibot-gdk"]
    assert worlds["b1-map12"]["available_backends"] == ["isaaclab"]
    assert worlds["b1-map12"]["default_backend"] == "isaaclab"


def test_scene_preview_rendered_views_never_alias_other_preview_types() -> None:
    worlds = {world["id"]: world for world in list_worlds()}

    for world_id, world in worlds.items():
        previews = world["preview_assets"]
        if "topdown" in previews:
            assert previews["topdown"]["href"] != previews.get("map", {}).get("href"), world_id
            assert previews["topdown"]["href"] != previews.get("fpv", {}).get("href"), world_id
            assert "-topdown." in previews["topdown"]["href"], world_id
        if "chase" in previews:
            assert previews["chase"]["href"] != previews.get("map", {}).get("href"), world_id
            assert previews["chase"]["href"] != previews.get("fpv", {}).get("href"), world_id
            assert previews["chase"]["href"] != previews.get("topdown", {}).get("href"), world_id
            assert "-chase." in previews["chase"]["href"], world_id


def test_molmospaces_scene_previews_have_render_provenance() -> None:
    preview_root = (
        Path(__file__).resolve().parents[3] / "roboclaws/operator_console/static/previews"
    )

    for world_id in MOLMOSPACES_CONSOLE_WORLD_IDS:
        scene_name = world_id.replace("/", "-")
        metadata_path = preview_root / f"{scene_name}-preview.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["schema"] == "operator_console_scene_preview_v1"
        assert metadata["world_id"] == world_id
        assert metadata["backend"] == "mujoco"
        assert metadata["views"]["fpv"]["view"] == "raw_fpv"
        assert metadata["views"]["fpv"]["waypoint_id"]
        assert metadata["views"]["fpv"]["provenance"] == (
            "mujoco_robot_head_camera_first_public_waypoint"
        )
        assert metadata["views"]["chase"]["view"] == "chase_camera"
        assert metadata["views"]["chase"]["waypoint_id"]
        assert metadata["views"]["chase"]["provenance"] == (
            "mujoco_robot_camera_follower_public_waypoint"
        )
        assert metadata["views"]["chase"]["selection_policy"] == (
            "first_reviewable_public_waypoint_fallback_to_first"
        )
        assert metadata["views"]["chase"]["selection_status"] in {
            "first_waypoint_reviewable",
            "alternate_waypoint_reviewable",
            "fallback_first_waypoint_low_detail",
        }
        assert metadata["views"]["topdown"]["view"] == "topdown_scene_render"
        assert metadata["views"]["topdown"]["semantic_map_fallback"] is False
        assert metadata["views"]["topdown"]["provenance"] == (
            "mujoco_camera_control_canonical_eye_target"
        )


def test_b1_map12_scene_preview_has_static_digital_twin_provenance() -> None:
    preview_root = (
        Path(__file__).resolve().parents[3] / "roboclaws/operator_console/static/previews"
    )

    metadata = json.loads((preview_root / "b1-map12-preview.json").read_text(encoding="utf-8"))

    assert metadata["schema"] == "operator_console_scene_preview_v1"
    assert metadata["world_id"] == "b1-map12"
    assert metadata["backend"] == "isaaclab"
    assert metadata["renderer"] == "static_b1_map12_with_isaac_runtime_camera_previews"
    assert metadata["views"]["fpv"]["view"] == "raw_fpv"
    assert metadata["views"]["fpv"]["provenance"] == ("isaac_runtime_robot_mounted_head_camera_fpv")
    assert metadata["views"]["chase"]["view"] == "chase_camera"
    assert metadata["views"]["chase"]["provenance"] == "isaac_runtime_report_chase_camera"
    assert metadata["map_bundle"] == "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot"
    assert metadata["review_manifest"] == "assets/maps/b1-map12-alignment-review.json"
    assert metadata["runtime_provenance"]["generated_from_review_manifest"] is True
    assert metadata["views"]["map"]["view"] == "source_map_preview"
    assert metadata["views"]["map"]["provenance"] == "compiled_vendor_map12_runtime_preview_png"
    assert metadata["views"]["topdown"]["view"] == "review_label_topdown"
    assert metadata["views"]["topdown"]["provenance"] == (
        "compiled_b1_map12_review_labels_topdown_png"
    )
    assert metadata["views"]["topdown"]["review_label_count"] >= 1
    assert metadata["views"]["topdown"]["room_count"] >= 1
    assert metadata["views"]["topdown"]["inspection_waypoint_count"] >= 1


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
            "world-public-labels",
        ),
        (
            "molmospaces/val_0",
            "mujoco",
            "cleanup",
            "claude-code",
            "mimo-anthropic",
            "world-public-labels",
        ),
        (
            "molmospaces/val_0",
            "mujoco",
            "cleanup",
            "openai-agents-sdk",
            "codex-env",
            "world-public-labels",
        ),
        (
            "molmospaces/val_0",
            "mujoco",
            "map-build",
            "codex-cli",
            "codex-env",
            "world-public-labels",
        ),
        (
            "molmospaces/val_0",
            "mujoco",
            "open-ended",
            "codex-cli",
            "codex-env",
            "world-public-labels",
        ),
        (
            "molmospaces/val_2",
            "mujoco",
            "open-ended",
            "codex-cli",
            "codex-env",
            "world-public-labels",
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
            "world-public-labels",
        ),
    }
    validate_supported_routes_against_catalog()


def test_openai_agents_route_payload_lists_provider_profiles() -> None:
    route = get_selection(
        "molmospaces/val_0::mujoco::cleanup::openai-agents-sdk::world-public-labels"
    )
    payload = route.to_payload()

    assert payload["provider_profile"] == "codex-env"
    assert payload["supported_provider_profiles"] == [
        "codex-env",
        "mify",
        "minimax",
        "mimo-openai-chat",
        "mimo-inside",
        "kimi-openai-chat",
    ]
    route_by_profile = {route["provider_profile"]: route for route in payload["provider_routes"]}
    assert route_by_profile["mify"]["route_status"] == "provisional"
    assert route_by_profile["mimo-openai-chat"]["wire_api"] == "chat-completions"
    assert route_by_profile["minimax"]["route_capabilities"]["image_transport"] == "unknown"


def test_openclaw_agent_engine_marks_validation_required() -> None:
    spec = agent_engine_spec("openclaw-gateway")

    assert spec.availability == "validation-required"


def test_console_exposes_all_supported_household_evidence_lanes() -> None:
    lanes = tuple(lane["id"] for lane in list_evidence_lanes())
    assert lanes == (
        "world-public-labels",
        "camera-grounded-labels",
        "camera-raw-fpv",
    )

    enabled_ids = {route.id for route in list_console_combinations(include_disabled=False)}
    for lane in lanes:
        assert f"molmospaces/val_0::mujoco::cleanup::codex-cli::{lane}" in enabled_ids
        assert f"molmospaces/val_0::mujoco::cleanup::claude-code::{lane}" in enabled_ids
        assert f"molmospaces/val_0::mujoco::cleanup::openai-agents-sdk::{lane}" in enabled_ids
        assert f"molmospaces/val_0::mujoco::map-build::codex-cli::{lane}" in enabled_ids
        assert f"molmospaces/val_0::mujoco::map-build::direct-runner::{lane}" in enabled_ids
        assert f"molmospaces/val_0::mujoco::open-task::codex-cli::{lane}" in enabled_ids
        assert f"molmospaces/val_0::mujoco::open-task::openai-agents-sdk::{lane}" in enabled_ids
        assert f"molmospaces/val_2::mujoco::open-task::codex-cli::{lane}" in enabled_ids
        assert f"agibot-g2/map-12::agibot-gdk::map-build::codex-cli::{lane}" in enabled_ids

    grounded = get_selection(
        "molmospaces/val_0::mujoco::cleanup::codex-cli::camera-grounded-labels"
    )
    assert "camera_labeler=grounding-dino" in grounded.launch_default_overrides
    agibot_grounded = get_selection(AGIBOT_CODEX_MAP_BUILD)
    assert "camera_labeler=grounding-dino" in agibot_grounded.launch_default_overrides


def test_molmospaces_scene_choices_use_scene_specific_launch_defaults(tmp_path) -> None:
    enabled_ids = {route.id for route in list_console_combinations(include_disabled=False)}
    for world_id in MOLMOSPACES_CONSOLE_WORLD_IDS:
        assert f"{world_id}::mujoco::map-build::direct-runner::world-public-labels" in enabled_ids
    for world_id in MOLMOSPACES_MUJOCO_DEFAULT_CLEANUP_WORLD_IDS:
        assert f"{world_id}::mujoco::cleanup::codex-cli::world-public-labels" in enabled_ids

    val0 = get_selection(MUJOCO_CODEX_CLEANUP)
    val5 = get_selection("molmospaces/val_5::mujoco::cleanup::codex-cli::world-public-labels")

    assert "scene_index=0" in val0.launch_default_overrides
    assert "map_bundle=none" not in val0.launch_default_overrides
    assert "scene_index=5" in val5.launch_default_overrides
    assert "map_bundle=none" in val5.launch_default_overrides
    assert val5.to_payload()["preview_assets"]["fpv"]["href"] == (
        "/previews/molmospaces-val_5-fpv.png"
    )

    argv = build_launch_argv(val5, root=tmp_path, run_id="run-val-5")
    assert "world=molmospaces/val_5" in argv
    assert "scene_source=procthor-10k-val" in argv
    assert "scene_index=5" in argv
    assert "map_bundle=none" in argv


def test_molmospaces_cleanup_routes_match_scene_target_capacity() -> None:
    all_ids = {route.id for route in list_console_combinations()}
    enabled_ids = {route.id for route in list_console_combinations(include_disabled=False)}
    disabled = {
        route.id: route.disabled_reason
        for route in list_console_combinations()
        if not route.enabled
    }

    assert not any(route_id.startswith("molmospaces/val_6::") for route_id in all_ids)
    assert not any(route_id.startswith("molmospaces/val_8::") for route_id in all_ids)

    assert "molmospaces/val_1::mujoco::map-build::codex-cli::world-public-labels" not in all_ids
    assert "molmospaces/val_1::mujoco::cleanup::codex-cli::world-public-labels" not in all_ids

    assert "molmospaces/val_2::mujoco::cleanup::codex-cli::world-public-labels" in disabled
    assert (
        "at least 5 generated cleanup targets"
        in disabled["molmospaces/val_2::mujoco::cleanup::codex-cli::world-public-labels"]
    )
    assert not any(
        "::isaaclab::" in route_id for route_id in all_ids if route_id.startswith("molmospaces/")
    )
    assert "molmospaces/val_2::mujoco::map-build::codex-cli::world-public-labels" in enabled_ids
    assert "molmospaces/val_2::mujoco::open-task::codex-cli::world-public-labels" in enabled_ids
    assert (
        "molmospaces/val_0::mujoco::open-task::openai-agents-sdk::world-public-labels"
        in enabled_ids
    )

    enabled_mujoco_cleanup_worlds = {
        route.world_id
        for route in list_console_combinations(include_disabled=False)
        if (
            route.backend_id == "mujoco"
            and route.intent_id == "cleanup"
            and route.agent_engine_id == "codex-cli"
            and route.evidence_lane == "world-public-labels"
        )
    }
    assert enabled_mujoco_cleanup_worlds == set(MOLMOSPACES_MUJOCO_DEFAULT_CLEANUP_WORLD_IDS)


def test_console_keeps_b1_unsupported_isaac_lane_visible_but_disabled() -> None:
    disabled = {
        route.id: route.disabled_reason
        for route in list_console_combinations()
        if not route.enabled
    }

    reason = disabled["b1-map12::isaaclab::open-task::codex-cli::camera-grounded-labels"]
    assert "not wired yet" in reason
    assert "b1-map12::isaaclab::open-task::codex-cli::camera-grounded-labels" not in {
        route.id for route in list_console_combinations(include_disabled=False)
    }
    assert "b1-map12::isaaclab::open-task::codex-cli::camera-raw-fpv" in {
        route.id for route in list_console_combinations(include_disabled=False)
    }


def test_disabled_combinations_have_concrete_reasons() -> None:
    disabled = [route for route in list_console_combinations() if not route.enabled]

    assert disabled
    reasons = {route.id: route.disabled_reason for route in disabled}
    assert (
        reasons[AGIBOT_CODEX_CLEANUP]
        == "Physical manipulation is not available yet. Run Agibot G2 Map Build first."
    )
    assert (
        "Map-build"
        in reasons["molmospaces/val_0::mujoco::map-build::claude-code::world-public-labels"]
    )
    b1_camera_grounded = "b1-map12::isaaclab::open-task::codex-cli::camera-grounded-labels"
    assert "not wired yet" in reasons[b1_camera_grounded]


def test_payload_exposes_orthogonal_ui_metadata() -> None:
    mujoco = get_selection(MUJOCO_CODEX_CLEANUP).to_payload()
    agibot = get_selection(AGIBOT_CODEX_MAP_BUILD).to_payload()
    b1 = get_selection(B1_CODEX_OPEN_TASK).to_payload()

    assert mujoco["world_id"] == "molmospaces/val_0"
    assert mujoco["backend_id"] == "mujoco"
    assert mujoco["agent_engine_id"] == "codex-cli"
    assert mujoco["provider_profile"] == "codex-env"
    assert mujoco["scenario_setup"] == "relocate-cleanup-related-objects"
    assert "agent_engine=codex-cli" in mujoco["argv_preview"]
    assert "scenario_setup=relocate-cleanup-related-objects" in mujoco["argv_preview"]
    assert mujoco["field_groups"] == ["common"]
    assert "grounding" not in mujoco["view_modes"]

    assert agibot["field_groups"] == ["common", "agibot", "agibot_gates"]
    assert "context_json" in agibot["required_overrides"]
    assert "grounding" in agibot["view_modes"]

    assert b1["default_intent"] == "open-ended"
    assert b1["field_groups"] == ["common", "isaac"]
    assert "grounding" in b1["view_modes"]
    assert "map_bundle=vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot" in b1[
        "argv_preview"
    ]
    assert "b1_alignment_review=assets/maps/b1-map12-alignment-review.json" in b1["argv_preview"]
    assert "robot_views=on" in b1["argv_preview"]


def test_legacy_route_api_stays_removed() -> None:
    assert not hasattr(route_registry, "ConsoleRoute")
    assert not hasattr(route_registry, "get_route")
    assert not hasattr(route_registry, "list_console_routes")

    with pytest.raises(KeyError):
        get_selection("codex-mujoco-cleanup")


def test_prompt_gating_uses_argv_element_not_shell_joining(tmp_path) -> None:
    selection = get_selection(MUJOCO_CODEX_CLEANUP)
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
        "preset=cleanup",
        "agent_engine=codex-cli",
    ]
    assert "evidence_lane=world-public-labels" in argv
    assert "provider_profile=codex-env" in argv
    assert "scenario_setup=relocate-cleanup-related-objects" in argv
    assert "prompt=collect mugs; rm -rf / should stay text" in argv


def test_map_build_launch_defaults_to_baseline_scenario_setup(tmp_path) -> None:
    selection = get_selection(MUJOCO_CODEX_MAP_BUILD)
    argv = build_launch_argv(selection, root=tmp_path, run_id="run-1")

    assert "preset=map-build" in argv
    assert "scenario_setup=baseline" in argv
    assert not any(item.startswith("relocation_count=") for item in argv)
    assert not any(item.startswith("generated_mess_count=") for item in argv)


def test_camera_grounded_lane_launch_includes_default_camera_labeler(tmp_path) -> None:
    selection = get_selection(
        "molmospaces/val_0::mujoco::cleanup::codex-cli::camera-grounded-labels"
    )
    argv = build_launch_argv(selection, root=tmp_path, run_id="run-1")

    assert "evidence_lane=camera-grounded-labels" in argv
    assert "camera_labeler=grounding-dino" in argv


def test_b1_map12_open_ended_launch_uses_scene_and_map_bundle(tmp_path) -> None:
    selection = get_selection(B1_CODEX_OPEN_TASK)
    argv = build_launch_argv(selection, root=tmp_path, run_id="run-1")

    assert not any(item.startswith("intent=") for item in argv)
    assert not any(item.startswith("preset=") for item in argv)
    assert "backend=isaaclab" in argv
    assert "scenario_setup=baseline" in argv
    assert "map_bundle=vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot" in argv
    assert "b1_alignment_review=assets/maps/b1-map12-alignment-review.json" in argv
    assert "robot_views=on" in argv
    assert (
        "isaac_scene_usd_path=data/robot-data-lab/scene-engine/data/"
        "2rd_floor_seperated/storey_1/configuration/scene_base.usd"
    ) in argv
    assert not any(item.startswith("relocation_count=") for item in argv)


def test_prompt_rejected_for_unsupported_selection(tmp_path) -> None:
    selection = get_selection(AGIBOT_CODEX_CLEANUP)
    with pytest.raises(ConsoleLaunchError, match="custom prompt"):
        build_launch_argv(selection, root=tmp_path, run_id="run-1", prompt="unsafe")
