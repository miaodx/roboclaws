from __future__ import annotations

import json
from typing import Any

import pytest

from roboclaws.mcp.entrypoint import (
    MCPProfileRouter,
    load_contract_profile,
    register_profile_tools,
)
from roboclaws.mcp.profiles import (
    AI2THOR_NAVIGATION_PROFILE,
    CLASSIFICATION_PRIVILEGED_TOOL,
    MOLMOSPACES_CLEANUP_PROFILE,
    REAL_ROBOT_CLEANUP_PROFILE,
    ContractProfile,
    ToolDescriptor,
    assert_public_profile_metadata_safe,
    contract_profile,
    contract_profile_metadata,
    contract_profile_names,
    validate_contract_profile,
)


class FakeFastMCP:
    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}

    def tool(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        **_: Any,
    ):
        def decorator(func: Any) -> Any:
            self.tools[name or func.__name__] = {"description": description, "func": func}
            return func

        return decorator


def _handlers(profile_id: str) -> dict[str, Any]:
    return {
        name: (lambda **_: {"ok": True})
        for name in contract_profile(profile_id).public_tool_names()
    }


def test_contract_profile_registry_contains_backend_domain_profiles() -> None:
    assert contract_profile_names() == (
        AI2THOR_NAVIGATION_PROFILE,
        MOLMOSPACES_CLEANUP_PROFILE,
        REAL_ROBOT_CLEANUP_PROFILE,
    )


def test_ai2thor_profile_labels_scene_objects_and_goto_as_privileged_tools() -> None:
    metadata = contract_profile_metadata(AI2THOR_NAVIGATION_PROFILE)

    public_names = {tool["name"] for tool in metadata["public_tools"]}
    privileged_tool_names = {tool["name"] for tool in metadata["privileged_tools"]}

    assert {"observe", "observe_archived", "move", "done"} <= public_names
    assert "scene_objects" not in public_names
    assert "goto" not in public_names
    assert {"scene_objects", "goto"} <= privileged_tool_names
    assert {tool["classification"] for tool in metadata["privileged_tools"]} == {
        CLASSIFICATION_PRIVILEGED_TOOL
    }


def test_molmo_profile_public_metadata_omits_private_evaluator_terms() -> None:
    profile = contract_profile(MOLMOSPACES_CLEANUP_PROFILE)
    metadata = profile.metadata()
    payload = json.dumps(metadata, sort_keys=True).lower()

    for forbidden in profile.privacy_exclusions:
        assert forbidden not in payload
    assert "scene_objects" not in payload
    assert {tool["name"] for tool in metadata["public_tools"]} >= {
        "metric_map",
        "fixture_hints",
        "observe",
        "pick",
        "place",
        "done",
    }


def test_real_robot_cleanup_profile_keeps_manipulation_blocked() -> None:
    profile = contract_profile(REAL_ROBOT_CLEANUP_PROFILE)
    metadata = profile.metadata()
    tools = {tool["name"]: tool for tool in metadata["public_tools"]}

    assert {
        "metric_map",
        "fixture_hints",
        "navigate_to_room",
        "navigate_to_waypoint",
        "observe",
        "adjust_camera",
        "declare_visual_candidates",
        "navigate_to_visual_candidate",
        "inspect_visible_object",
        "navigate_to_object",
        "navigate_to_receptacle",
        "done",
    } <= set(tools)
    assert metadata["backend"] == "physical_robot"
    assert metadata["backend_variants"] == ["nav2_ros2", "agibot_gdk"]
    assert "scene_objects" not in json.dumps(metadata)
    assert "goto" not in tools
    assert "nav2_action" in tools["navigate_to_waypoint"]["provenance"]
    assert "agibot_gdk_normal_navi" in tools["navigate_to_waypoint"]["provenance"]
    assert "agibot_gdk_normal_navi" in tools["navigate_to_receptacle"]["provenance"]
    assert "agibot_gdk_map_context" in tools["metric_map"]["provenance"]
    assert "nav2_action" in tools["navigate_to_visual_candidate"]["provenance"]
    assert "camera_artifact" in tools["declare_visual_candidates"]["provenance"]
    for tool_name in {"pick", "place", "place_inside", "open_receptacle", "close_receptacle"}:
        assert tools[tool_name]["provenance"] == ["blocked_capability"]


def test_profile_validation_rejects_privileged_public_tool() -> None:
    profile = ContractProfile(
        profile_id="bad_profile_v1",
        version=1,
        backend="test",
        domain="test",
        capability_families=("navigation",),
        public_tools=(
            ToolDescriptor(
                name="goto",
                semantic_name="navigation.teleport_to_object",
                family="navigation",
                classification="privileged_tool",
                provenance=("simulator_metadata",),
                summary="bad public privileged tool",
            ),
        ),
        privileged_tools=(),
    )

    with pytest.raises(ValueError, match="public tool 'goto' is classified as privileged_tool"):
        validate_contract_profile(profile)


def test_public_profile_safety_rejects_private_terms_in_serialized_metadata() -> None:
    profile = contract_profile(MOLMOSPACES_CLEANUP_PROFILE)
    unsafe_metadata = profile.metadata() | {"debug": "generated_mess_set"}

    with pytest.raises(ValueError, match="private exclusion terms"):
        assert_public_profile_metadata_safe(unsafe_metadata, profile)


def test_router_registers_only_selected_profile_public_tools() -> None:
    fake_mcp = FakeFastMCP()
    router = MCPProfileRouter(AI2THOR_NAVIGATION_PROFILE, _handlers(AI2THOR_NAVIGATION_PROFILE))

    registered = router.register_tools(fake_mcp)

    assert set(registered) == set(contract_profile(AI2THOR_NAVIGATION_PROFILE).public_tool_names())
    assert set(fake_mcp.tools) == set(registered)
    assert "scene_objects" not in fake_mcp.tools
    assert "goto" not in fake_mcp.tools


def test_register_profile_tools_helper_registers_selected_public_tools() -> None:
    fake_mcp = FakeFastMCP()

    registered = register_profile_tools(
        fake_mcp,
        profile_id=MOLMOSPACES_CLEANUP_PROFILE,
        handlers=_handlers(MOLMOSPACES_CLEANUP_PROFILE),
    )

    assert set(registered) == set(contract_profile(MOLMOSPACES_CLEANUP_PROFILE).public_tool_names())
    assert set(fake_mcp.tools) == set(registered)


def test_router_rejects_unknown_profile_with_allowed_ids() -> None:
    with pytest.raises(
        ValueError,
        match="allowed profiles: ai2thor_navigation_v1, molmospaces_cleanup_v1, "
        "real_robot_cleanup_v1",
    ):
        load_contract_profile("missing_profile")


def test_router_rejects_handlers_not_in_public_profile() -> None:
    handlers = _handlers(AI2THOR_NAVIGATION_PROFILE)
    handlers["goto"] = lambda **_: {"ok": True}

    with pytest.raises(ValueError, match="handlers outside public profile: goto"):
        MCPProfileRouter(AI2THOR_NAVIGATION_PROFILE, handlers)
