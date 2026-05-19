"""Semantic MCP contract profiles for Roboclaws tool surfaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

PROFILE_SCHEMA = "roboclaws_mcp_contract_profile_v1"

AI2THOR_NAVIGATION_PROFILE = "ai2thor_navigation_v1"
MOLMOSPACES_CLEANUP_PROFILE = "molmospaces_cleanup_v1"
REAL_ROBOT_CLEANUP_PROFILE = "real_robot_cleanup_v1"

FAMILY_PERCEPTION = "perception"
FAMILY_LOCALIZATION = "localization"
FAMILY_MAPPING = "mapping"
FAMILY_NAVIGATION = "navigation"
FAMILY_MANIPULATION = "manipulation"
FAMILY_MEMORY = "memory"
FAMILY_EPISODE = "episode"

VALID_CAPABILITY_FAMILIES = frozenset(
    {
        FAMILY_PERCEPTION,
        FAMILY_LOCALIZATION,
        FAMILY_MAPPING,
        FAMILY_NAVIGATION,
        FAMILY_MANIPULATION,
        FAMILY_MEMORY,
        FAMILY_EPISODE,
    }
)

CLASSIFICATION_CANONICAL = "canonical"
CLASSIFICATION_COMPOSED = "composed"
CLASSIFICATION_PRIVILEGED_TOOL = "privileged_tool"

VALID_TOOL_CLASSIFICATIONS = frozenset(
    {
        CLASSIFICATION_CANONICAL,
        CLASSIFICATION_COMPOSED,
        CLASSIFICATION_PRIVILEGED_TOOL,
    }
)

PROVENANCE_API_SEMANTIC = "api_semantic"
PROVENANCE_SIM_PLANNER = "sim_planner"
PROVENANCE_SIMULATOR_METADATA = "simulator_metadata"
PROVENANCE_SYNTHETIC_CONTRACT = "synthetic_contract"
PROVENANCE_CAMERA_ARTIFACT = "camera_artifact"
PROVENANCE_SIMULATED_CAMERA_MODEL = "simulated_camera_model"
PROVENANCE_PLANNER_BACKED = "planner_backed"
PROVENANCE_NAV2_ACTION = "nav2_action"
PROVENANCE_BLOCKED_CAPABILITY = "blocked_capability"


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    semantic_name: str
    family: str
    classification: str
    provenance: tuple[str, ...]
    summary: str

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "semantic_name": self.semantic_name,
            "family": self.family,
            "classification": self.classification,
            "provenance": list(self.provenance),
            "summary": self.summary,
        }


@dataclass(frozen=True)
class ContractProfile:
    profile_id: str
    version: int
    backend: str
    domain: str
    capability_families: tuple[str, ...]
    public_tools: tuple[ToolDescriptor, ...]
    privileged_tools: tuple[ToolDescriptor, ...]
    privacy_exclusions: tuple[str, ...] = ()
    summary: str = ""

    def public_tool_names(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self.public_tools)

    def privileged_tool_names(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self.privileged_tools)

    def metadata(self) -> dict[str, Any]:
        metadata = {
            "schema": PROFILE_SCHEMA,
            "profile_id": self.profile_id,
            "version": self.version,
            "backend": self.backend,
            "domain": self.domain,
            "capability_families": list(self.capability_families),
            "public_tools": [tool.metadata() for tool in self.public_tools],
            "privileged_tools": [tool.metadata() for tool in self.privileged_tools],
            "privacy_boundary": bool(self.privacy_exclusions),
            "summary": self.summary,
        }
        assert_public_profile_metadata_safe(metadata, self)
        return metadata


def contract_profile_names() -> tuple[str, ...]:
    return tuple(_PROFILES)


def contract_profile(profile_id: str) -> ContractProfile:
    normalized = normalize_profile_id(profile_id)
    try:
        return _PROFILES[normalized]
    except KeyError as exc:
        expected = ", ".join(contract_profile_names())
        raise ValueError(
            f"unsupported MCP contract profile {profile_id!r} (expected one of: {expected})"
        ) from exc


def contract_profile_metadata(profile_id: str) -> dict[str, Any]:
    return contract_profile(profile_id).metadata()


def normalize_profile_id(profile_id: str) -> str:
    return profile_id.strip().lower().replace("-", "_")


def validate_contract_profile(profile: ContractProfile) -> None:
    _require(profile.profile_id, "profile_id")
    _require(profile.version, "version")
    _require(profile.backend, "backend")
    _require(profile.domain, "domain")
    _require(profile.capability_families, "capability_families")
    _require(profile.public_tools, "public_tools")
    for family in profile.capability_families:
        if family not in VALID_CAPABILITY_FAMILIES:
            raise ValueError(
                f"profile {profile.profile_id} declares unknown capability family {family!r}"
            )
    declared_families = set(profile.capability_families)
    _validate_tools(profile.profile_id, profile.public_tools, declared_families, public=True)
    _validate_tools(profile.profile_id, profile.privileged_tools, declared_families, public=False)
    duplicate_names = _duplicates(
        [tool.name for tool in (*profile.public_tools, *profile.privileged_tools)]
    )
    if duplicate_names:
        names = ", ".join(duplicate_names)
        raise ValueError(f"profile {profile.profile_id} declares duplicate tool names: {names}")
    assert_public_profile_metadata_safe(profile.metadata(), profile)


def validate_all_contract_profiles() -> None:
    for profile in _PROFILES.values():
        validate_contract_profile(profile)


def assert_public_profile_metadata_safe(
    metadata: dict[str, Any],
    profile: ContractProfile,
) -> None:
    payload = json.dumps(metadata, sort_keys=True).lower()
    leaked = [term for term in profile.privacy_exclusions if term.lower() in payload]
    if leaked:
        raise ValueError(
            f"profile {profile.profile_id} public metadata contains private exclusion terms: "
            f"{', '.join(leaked)}"
        )


def _tool(
    name: str,
    semantic_name: str,
    family: str,
    classification: str,
    provenance: tuple[str, ...],
    summary: str,
) -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        semantic_name=semantic_name,
        family=family,
        classification=classification,
        provenance=provenance,
        summary=summary,
    )


def _validate_tools(
    profile_id: str,
    tools: tuple[ToolDescriptor, ...],
    declared_families: set[str],
    *,
    public: bool,
) -> None:
    for tool in tools:
        _require(tool.name, "tool.name")
        _require(tool.semantic_name, f"{tool.name}.semantic_name")
        _require(tool.provenance, f"{tool.name}.provenance")
        if tool.family not in declared_families:
            raise ValueError(
                f"profile {profile_id} tool {tool.name!r} uses undeclared family {tool.family!r}"
            )
        if tool.classification not in VALID_TOOL_CLASSIFICATIONS:
            raise ValueError(
                f"profile {profile_id} tool {tool.name!r} has unknown classification "
                f"{tool.classification!r}"
            )
        if public and tool.classification == CLASSIFICATION_PRIVILEGED_TOOL:
            raise ValueError(
                f"profile {profile_id} public tool {tool.name!r} is classified as privileged_tool"
            )
        if not public and tool.classification != CLASSIFICATION_PRIVILEGED_TOOL:
            raise ValueError(
                f"profile {profile_id} privileged tool {tool.name!r} must use "
                "privileged_tool classification"
            )


def _require(value: object, field_name: str) -> None:
    if not value:
        raise ValueError(f"missing required profile field {field_name}")


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


_AI2THOR_PROFILE = ContractProfile(
    profile_id=AI2THOR_NAVIGATION_PROFILE,
    version=1,
    backend="ai2thor",
    domain="navigation",
    capability_families=(
        FAMILY_PERCEPTION,
        FAMILY_LOCALIZATION,
        FAMILY_MAPPING,
        FAMILY_NAVIGATION,
        FAMILY_MEMORY,
        FAMILY_EPISODE,
    ),
    public_tools=(
        _tool(
            "observe",
            "perception.observe",
            FAMILY_PERCEPTION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_SIMULATOR_METADATA,),
            "Observe FPV, map, chase view, and structured navigation state.",
        ),
        _tool(
            "observe_archived",
            "perception.observe_archived",
            FAMILY_PERCEPTION,
            CLASSIFICATION_COMPOSED,
            (PROVENANCE_SIMULATOR_METADATA,),
            "Archive navigation observations without inlining image payloads.",
        ),
        _tool(
            "move",
            "navigation.move_step",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_SIM_PLANNER, PROVENANCE_BLOCKED_CAPABILITY),
            "Move one bounded AI2-THOR navigation step.",
        ),
        _tool(
            "done",
            "episode.done",
            FAMILY_EPISODE,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC,),
            "Terminate the current MCP-controlled navigation episode.",
        ),
    ),
    privileged_tools=(
        _tool(
            "scene_objects",
            "mapping.scene_inventory",
            FAMILY_MAPPING,
            CLASSIFICATION_PRIVILEGED_TOOL,
            (PROVENANCE_SIMULATOR_METADATA,),
            "Simulator inventory oracle; useful for demos, not a real robot perception surface.",
        ),
        _tool(
            "goto",
            "navigation.teleport_to_object",
            FAMILY_NAVIGATION,
            CLASSIFICATION_PRIVILEGED_TOOL,
            (PROVENANCE_SIMULATOR_METADATA,),
            "Teleport-like target-relative helper; excluded from canonical navigation profile.",
        ),
    ),
    summary=(
        "AI2-THOR navigation profile with privileged simulator tools excluded from public tools."
    ),
)

_MOLMO_PRIVATE_EXCLUSIONS = (
    "generated_mess_set",
    "acceptable_destination",
    "private_manifest",
    "is_misplaced",
    "hidden_target",
    "target_count",
)

_MOLMO_PROFILE = ContractProfile(
    profile_id=MOLMOSPACES_CLEANUP_PROFILE,
    version=1,
    backend="molmospaces",
    domain="cleanup",
    capability_families=(
        FAMILY_PERCEPTION,
        FAMILY_LOCALIZATION,
        FAMILY_MAPPING,
        FAMILY_NAVIGATION,
        FAMILY_MANIPULATION,
        FAMILY_EPISODE,
    ),
    public_tools=(
        _tool(
            "metric_map",
            "mapping.metric_map",
            FAMILY_MAPPING,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC,),
            "Return public room topology and inspection waypoints.",
        ),
        _tool(
            "fixture_hints",
            "mapping.fixture_hints",
            FAMILY_MAPPING,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC,),
            "Return public fixture identities and affordances.",
        ),
        _tool(
            "navigate_to_room",
            "navigation.navigate_to_room",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_BLOCKED_CAPABILITY),
            "Navigate to a public room waypoint.",
        ),
        _tool(
            "navigate_to_waypoint",
            "navigation.navigate_to_waypoint",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_BLOCKED_CAPABILITY),
            "Navigate to a public inspection waypoint.",
        ),
        _tool(
            "observe",
            "perception.observe",
            FAMILY_PERCEPTION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_API_SEMANTIC),
            "Observe robot-local public candidates at the current waypoint.",
        ),
        _tool(
            "adjust_camera",
            "perception.adjust_camera",
            FAMILY_PERCEPTION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_CAMERA_ARTIFACT,),
            "Adjust bounded active camera yaw/pitch at the current waypoint.",
        ),
        _tool(
            "declare_visual_candidates",
            "perception.declare_visual_candidates",
            FAMILY_PERCEPTION,
            CLASSIFICATION_COMPOSED,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_SIMULATED_CAMERA_MODEL),
            "Register model-declared cleanup candidates from public camera evidence.",
        ),
        _tool(
            "navigate_to_visual_candidate",
            "navigation.navigate_to_visual_candidate",
            FAMILY_NAVIGATION,
            CLASSIFICATION_COMPOSED,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_API_SEMANTIC),
            "Declare one visual cleanup candidate and navigate to it when grounded.",
        ),
        _tool(
            "inspect_visible_object",
            "perception.inspect_visible_object",
            FAMILY_PERCEPTION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC,),
            "Inspect a previously observed public object handle.",
        ),
        _tool(
            "navigate_to_object",
            "navigation.navigate_to_object",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_BLOCKED_CAPABILITY),
            "Navigate to a public observed object handle.",
        ),
        _tool(
            "pick",
            "manipulation.pick",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_PLANNER_BACKED, PROVENANCE_BLOCKED_CAPABILITY),
            "Pick a public observed object handle.",
        ),
        _tool(
            "navigate_to_receptacle",
            "navigation.navigate_to_receptacle",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_BLOCKED_CAPABILITY),
            "Navigate to a public fixture before placement.",
        ),
        _tool(
            "open_receptacle",
            "manipulation.open_receptacle",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_PLANNER_BACKED, PROVENANCE_BLOCKED_CAPABILITY),
            "Open a public receptacle before inside placement.",
        ),
        _tool(
            "place",
            "manipulation.place",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_PLANNER_BACKED, PROVENANCE_BLOCKED_CAPABILITY),
            "Place the held object on or at a public fixture.",
        ),
        _tool(
            "place_inside",
            "manipulation.place_inside",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_PLANNER_BACKED, PROVENANCE_BLOCKED_CAPABILITY),
            "Place the held object inside an opened public fixture.",
        ),
        _tool(
            "close_receptacle",
            "manipulation.close_receptacle",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC, PROVENANCE_PLANNER_BACKED, PROVENANCE_BLOCKED_CAPABILITY),
            "Close a public receptacle after inside placement.",
        ),
        _tool(
            "done",
            "episode.done",
            FAMILY_EPISODE,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_API_SEMANTIC,),
            "Terminate the cleanup episode and write artifacts.",
        ),
    ),
    privileged_tools=(),
    privacy_exclusions=_MOLMO_PRIVATE_EXCLUSIONS,
    summary="MolmoSpaces cleanup profile preserving the ADR-0003 public agent boundary.",
)

_REAL_ROBOT_PROFILE = ContractProfile(
    profile_id=REAL_ROBOT_CLEANUP_PROFILE,
    version=1,
    backend="ros2_nav2",
    domain="cleanup",
    capability_families=(
        FAMILY_PERCEPTION,
        FAMILY_LOCALIZATION,
        FAMILY_MAPPING,
        FAMILY_NAVIGATION,
        FAMILY_MANIPULATION,
        FAMILY_EPISODE,
    ),
    public_tools=(
        _tool(
            "metric_map",
            "mapping.metric_map",
            FAMILY_MAPPING,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_NAV2_ACTION,),
            "Return a prebuilt Nav2 map bundle plus public fixture semantics.",
        ),
        _tool(
            "fixture_hints",
            "mapping.fixture_hints",
            FAMILY_MAPPING,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_NAV2_ACTION,),
            "Return public fixture identities, affordances, and preferred waypoints.",
        ),
        _tool(
            "navigate_to_room",
            "navigation.navigate_to_room",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_NAV2_ACTION, PROVENANCE_BLOCKED_CAPABILITY),
            "Resolve a room-level cleanup goal to a bounded Nav2 waypoint action.",
        ),
        _tool(
            "navigate_to_waypoint",
            "navigation.navigate_to_waypoint",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_NAV2_ACTION, PROVENANCE_BLOCKED_CAPABILITY),
            "Send a bounded waypoint goal through a direct Nav2 backend adapter.",
        ),
        _tool(
            "observe",
            "perception.observe",
            FAMILY_PERCEPTION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_BLOCKED_CAPABILITY),
            "Observe robot-local public candidates at the reached waypoint.",
        ),
        _tool(
            "adjust_camera",
            "perception.adjust_camera",
            FAMILY_PERCEPTION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_BLOCKED_CAPABILITY),
            "Adjust bounded active camera yaw/pitch when the robot camera supports it.",
        ),
        _tool(
            "declare_visual_candidates",
            "perception.declare_visual_candidates",
            FAMILY_PERCEPTION,
            CLASSIFICATION_COMPOSED,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_BLOCKED_CAPABILITY),
            "Register model-declared cleanup candidates from public robot-camera evidence.",
        ),
        _tool(
            "navigate_to_visual_candidate",
            "navigation.navigate_to_visual_candidate",
            FAMILY_NAVIGATION,
            CLASSIFICATION_COMPOSED,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_NAV2_ACTION, PROVENANCE_BLOCKED_CAPABILITY),
            "Ground one visual cleanup candidate and navigate toward it with Nav2 when possible.",
        ),
        _tool(
            "inspect_visible_object",
            "perception.inspect_visible_object",
            FAMILY_PERCEPTION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_BLOCKED_CAPABILITY),
            "Inspect a robot-camera-visible public object handle.",
        ),
        _tool(
            "navigate_to_object",
            "navigation.navigate_to_object",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_NAV2_ACTION, PROVENANCE_BLOCKED_CAPABILITY),
            "Navigate toward a public observed object handle using the Nav2 pilot boundary.",
        ),
        _tool(
            "navigate_to_receptacle",
            "navigation.navigate_to_receptacle",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_NAV2_ACTION, PROVENANCE_BLOCKED_CAPABILITY),
            "Resolve a fixture to its preferred public waypoint and navigate there.",
        ),
        _tool(
            "pick",
            "manipulation.pick",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_BLOCKED_CAPABILITY,),
            "Return a structured blocked-capability response until manipulation is proven.",
        ),
        _tool(
            "place",
            "manipulation.place",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_BLOCKED_CAPABILITY,),
            "Return a structured blocked-capability response until manipulation is proven.",
        ),
        _tool(
            "place_inside",
            "manipulation.place_inside",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_BLOCKED_CAPABILITY,),
            "Return a structured blocked-capability response until manipulation is proven.",
        ),
        _tool(
            "open_receptacle",
            "manipulation.open_receptacle",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_BLOCKED_CAPABILITY,),
            "Return a structured blocked-capability response until manipulation is proven.",
        ),
        _tool(
            "close_receptacle",
            "manipulation.close_receptacle",
            FAMILY_MANIPULATION,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_BLOCKED_CAPABILITY,),
            "Return a structured blocked-capability response until manipulation is proven.",
        ),
        _tool(
            "done",
            "episode.done",
            FAMILY_EPISODE,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_NAV2_ACTION, PROVENANCE_BLOCKED_CAPABILITY),
            "Terminate the navigation and perception pilot episode.",
        ),
    ),
    privileged_tools=(),
    privacy_exclusions=_MOLMO_PRIVATE_EXCLUSIONS,
    summary=(
        "Real robot cleanup-shaped profile for the first Nav2 navigation and "
        "perception pilot; manipulation remains blocked."
    ),
)

_PROFILES = {
    AI2THOR_NAVIGATION_PROFILE: _AI2THOR_PROFILE,
    MOLMOSPACES_CLEANUP_PROFILE: _MOLMO_PROFILE,
    REAL_ROBOT_CLEANUP_PROFILE: _REAL_ROBOT_PROFILE,
}

validate_all_contract_profiles()
