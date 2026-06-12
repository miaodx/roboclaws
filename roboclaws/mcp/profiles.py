"""Semantic MCP contract profiles for Roboclaws tool surfaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

PROFILE_SCHEMA = "roboclaws_mcp_contract_profile_v1"

HOUSEHOLD_WORLD_PROFILE = "household_world_v1"
HOUSEHOLD_MANIPULATION_PROFILE = "household_manipulation_v1"
HOUSEHOLD_EPISODE_PROFILE = "household_episode_v1"
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
PROVENANCE_AGIBOT_GDK_NORMAL_NAVI = "agibot_gdk_normal_navi"
PROVENANCE_AGIBOT_GDK_MAP_CONTEXT = "agibot_gdk_map_context"
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
    backend_variants: tuple[str, ...] = ()
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
            "backend_variants": list(self.backend_variants),
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


_MOLMO_PRIVATE_EXCLUSIONS = (
    "generated_mess_set",
    "acceptable_destination",
    "private_manifest",
    "is_misplaced",
    "hidden_target",
    "target_count",
)

_HOUSEHOLD_WORLD_TOOLS = (
    _tool(
        "metric_map",
        "mapping.metric_map",
        FAMILY_MAPPING,
        CLASSIFICATION_CANONICAL,
        (
            PROVENANCE_API_SEMANTIC,
            PROVENANCE_NAV2_ACTION,
            PROVENANCE_AGIBOT_GDK_MAP_CONTEXT,
        ),
        (
            "Return public room topology, static fixtures, runtime-map slots, "
            "and inspection waypoints."
        ),
    ),
    _tool(
        "navigate_to_room",
        "navigation.navigate_to_room",
        FAMILY_NAVIGATION,
        CLASSIFICATION_CANONICAL,
        (
            PROVENANCE_API_SEMANTIC,
            PROVENANCE_NAV2_ACTION,
            PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
            PROVENANCE_BLOCKED_CAPABILITY,
        ),
        "Navigate to a public room waypoint.",
    ),
    _tool(
        "navigate_to_waypoint",
        "navigation.navigate_to_waypoint",
        FAMILY_NAVIGATION,
        CLASSIFICATION_CANONICAL,
        (
            PROVENANCE_API_SEMANTIC,
            PROVENANCE_NAV2_ACTION,
            PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
            PROVENANCE_BLOCKED_CAPABILITY,
        ),
        "Navigate to a public inspection waypoint.",
    ),
    _tool(
        "observe",
        "perception.observe",
        FAMILY_PERCEPTION,
        CLASSIFICATION_CANONICAL,
        (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_API_SEMANTIC, PROVENANCE_BLOCKED_CAPABILITY),
        "Observe robot-local public candidates and camera evidence at the current waypoint.",
    ),
    _tool(
        "adjust_camera",
        "perception.adjust_camera",
        FAMILY_PERCEPTION,
        CLASSIFICATION_CANONICAL,
        (PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_BLOCKED_CAPABILITY),
        "Adjust bounded active camera yaw/pitch at the current waypoint.",
    ),
    _tool(
        "declare_visual_candidates",
        "perception.declare_visual_candidates",
        FAMILY_PERCEPTION,
        CLASSIFICATION_COMPOSED,
        (
            PROVENANCE_CAMERA_ARTIFACT,
            PROVENANCE_SIMULATED_CAMERA_MODEL,
            PROVENANCE_BLOCKED_CAPABILITY,
        ),
        "Register public model-declared candidates from camera evidence.",
    ),
    _tool(
        "navigate_to_visual_candidate",
        "navigation.navigate_to_visual_candidate",
        FAMILY_NAVIGATION,
        CLASSIFICATION_COMPOSED,
        (
            PROVENANCE_CAMERA_ARTIFACT,
            PROVENANCE_API_SEMANTIC,
            PROVENANCE_NAV2_ACTION,
            PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
            PROVENANCE_BLOCKED_CAPABILITY,
        ),
        "Ground one public visual candidate and navigate toward it when possible.",
    ),
    _tool(
        "inspect_visible_object",
        "perception.inspect_visible_object",
        FAMILY_PERCEPTION,
        CLASSIFICATION_CANONICAL,
        (PROVENANCE_API_SEMANTIC, PROVENANCE_CAMERA_ARTIFACT, PROVENANCE_BLOCKED_CAPABILITY),
        "Inspect a previously observed public object handle.",
    ),
    _tool(
        "resolve_target_query",
        "mapping.resolve_target_query",
        FAMILY_MAPPING,
        CLASSIFICATION_COMPOSED,
        (
            PROVENANCE_API_SEMANTIC,
            PROVENANCE_NAV2_ACTION,
            PROVENANCE_AGIBOT_GDK_MAP_CONTEXT,
            PROVENANCE_BLOCKED_CAPABILITY,
        ),
        "Resolve a target query against public Runtime Metric Map target candidates.",
    ),
)

_HOUSEHOLD_MANIPULATION_TOOLS = (
    _tool(
        "navigate_to_object",
        "navigation.navigate_to_object",
        FAMILY_NAVIGATION,
        CLASSIFICATION_CANONICAL,
        (
            PROVENANCE_API_SEMANTIC,
            PROVENANCE_CAMERA_ARTIFACT,
            PROVENANCE_NAV2_ACTION,
            PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
            PROVENANCE_BLOCKED_CAPABILITY,
        ),
        "Navigate toward a public observed object handle before manipulation.",
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
        (
            PROVENANCE_API_SEMANTIC,
            PROVENANCE_NAV2_ACTION,
            PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
            PROVENANCE_BLOCKED_CAPABILITY,
        ),
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
)

_HOUSEHOLD_DONE_TOOL = _tool(
    "done",
    "episode.done",
    FAMILY_EPISODE,
    CLASSIFICATION_CANONICAL,
    (
        PROVENANCE_API_SEMANTIC,
        PROVENANCE_NAV2_ACTION,
        PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
        PROVENANCE_BLOCKED_CAPABILITY,
    ),
    "Terminate the selected household task and write artifacts.",
)

_HOUSEHOLD_OPERATOR_MESSAGES_TOOL = _tool(
    "check_operator_messages",
    "episode.check_operator_messages",
    FAMILY_EPISODE,
    CLASSIFICATION_CANONICAL,
    (PROVENANCE_API_SEMANTIC,),
    "Read public operator steering messages at task-owned safe checkpoints.",
)

_HOUSEHOLD_WORLD_PROFILE = ContractProfile(
    profile_id=HOUSEHOLD_WORLD_PROFILE,
    version=1,
    backend="multi_backend",
    domain="household_world",
    backend_variants=(
        "api_semantic_synthetic",
        "molmospaces_subprocess",
        "nav2_ros2",
        "agibot_gdk",
    ),
    capability_families=(
        FAMILY_PERCEPTION,
        FAMILY_LOCALIZATION,
        FAMILY_MAPPING,
        FAMILY_NAVIGATION,
        FAMILY_MEMORY,
    ),
    public_tools=_HOUSEHOLD_WORLD_TOOLS,
    privileged_tools=(),
    privacy_exclusions=_MOLMO_PRIVATE_EXCLUSIONS,
    summary=(
        "Task-neutral household world profile for metric-map projection, runtime "
        "map evidence, observation, visual candidate declaration, and bounded navigation."
    ),
)

_HOUSEHOLD_MANIPULATION_PROFILE = ContractProfile(
    profile_id=HOUSEHOLD_MANIPULATION_PROFILE,
    version=1,
    backend="multi_backend",
    domain="household_manipulation",
    backend_variants=(
        "api_semantic_synthetic",
        "molmospaces_subprocess",
        "nav2_ros2",
        "agibot_gdk",
    ),
    capability_families=(
        FAMILY_NAVIGATION,
        FAMILY_MANIPULATION,
    ),
    public_tools=_HOUSEHOLD_MANIPULATION_TOOLS,
    privileged_tools=(),
    privacy_exclusions=_MOLMO_PRIVATE_EXCLUSIONS,
    summary=(
        "Composable household manipulation profile. Physical backends may return "
        "blocked-capability responses until manipulation is proven."
    ),
)

_HOUSEHOLD_EPISODE_PROFILE = ContractProfile(
    profile_id=HOUSEHOLD_EPISODE_PROFILE,
    version=1,
    backend="multi_backend",
    domain="household_task_lifecycle",
    backend_variants=(
        "api_semantic_synthetic",
        "molmospaces_subprocess",
        "nav2_ros2",
        "agibot_gdk",
    ),
    capability_families=(FAMILY_EPISODE,),
    public_tools=(_HOUSEHOLD_OPERATOR_MESSAGES_TOOL, _HOUSEHOLD_DONE_TOOL),
    privileged_tools=(),
    privacy_exclusions=_MOLMO_PRIVATE_EXCLUSIONS,
    summary="Composable household task lifecycle profile for explicit run completion.",
)

_MOLMO_PROFILE = ContractProfile(
    profile_id=MOLMOSPACES_CLEANUP_PROFILE,
    version=1,
    backend="molmospaces",
    backend_variants=("api_semantic_synthetic", "molmospaces_subprocess"),
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
        *_HOUSEHOLD_WORLD_TOOLS,
        *_HOUSEHOLD_MANIPULATION_TOOLS,
        _HOUSEHOLD_OPERATOR_MESSAGES_TOOL,
        _HOUSEHOLD_DONE_TOOL,
    ),
    privileged_tools=(),
    privacy_exclusions=_MOLMO_PRIVATE_EXCLUSIONS,
    summary=(
        "Legacy cleanup-shaped MolmoSpaces profile composed from the household "
        "world, manipulation, and lifecycle capability modules."
    ),
)

_REAL_ROBOT_PROFILE = ContractProfile(
    profile_id=REAL_ROBOT_CLEANUP_PROFILE,
    version=1,
    backend="physical_robot",
    backend_variants=("nav2_ros2", "agibot_gdk"),
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
            (PROVENANCE_NAV2_ACTION, PROVENANCE_AGIBOT_GDK_MAP_CONTEXT),
            "Return a backend-neutral real-robot map plus public fixture semantics.",
        ),
        _tool(
            "navigate_to_room",
            "navigation.navigate_to_room",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (
                PROVENANCE_NAV2_ACTION,
                PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
                PROVENANCE_BLOCKED_CAPABILITY,
            ),
            "Resolve a room-level cleanup goal to a bounded physical waypoint action.",
        ),
        _tool(
            "navigate_to_waypoint",
            "navigation.navigate_to_waypoint",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (
                PROVENANCE_NAV2_ACTION,
                PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
                PROVENANCE_BLOCKED_CAPABILITY,
            ),
            "Send a bounded waypoint goal through a physical navigation backend.",
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
            (
                PROVENANCE_CAMERA_ARTIFACT,
                PROVENANCE_NAV2_ACTION,
                PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
                PROVENANCE_BLOCKED_CAPABILITY,
            ),
            "Ground one visual cleanup candidate and navigate toward it when possible.",
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
            "resolve_target_query",
            "mapping.resolve_target_query",
            FAMILY_MAPPING,
            CLASSIFICATION_COMPOSED,
            (
                PROVENANCE_NAV2_ACTION,
                PROVENANCE_AGIBOT_GDK_MAP_CONTEXT,
                PROVENANCE_BLOCKED_CAPABILITY,
            ),
            "Resolve a target query against public runtime-map target candidates.",
        ),
        _tool(
            "navigate_to_object",
            "navigation.navigate_to_object",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (
                PROVENANCE_CAMERA_ARTIFACT,
                PROVENANCE_NAV2_ACTION,
                PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
                PROVENANCE_BLOCKED_CAPABILITY,
            ),
            "Navigate toward a public observed object handle using the physical pilot boundary.",
        ),
        _tool(
            "navigate_to_receptacle",
            "navigation.navigate_to_receptacle",
            FAMILY_NAVIGATION,
            CLASSIFICATION_CANONICAL,
            (
                PROVENANCE_NAV2_ACTION,
                PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
                PROVENANCE_BLOCKED_CAPABILITY,
            ),
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
            "check_operator_messages",
            "episode.check_operator_messages",
            FAMILY_EPISODE,
            CLASSIFICATION_CANONICAL,
            (PROVENANCE_BLOCKED_CAPABILITY,),
            "Return no public steering messages until the physical pilot route enables steering.",
        ),
        _tool(
            "done",
            "episode.done",
            FAMILY_EPISODE,
            CLASSIFICATION_CANONICAL,
            (
                PROVENANCE_NAV2_ACTION,
                PROVENANCE_AGIBOT_GDK_NORMAL_NAVI,
                PROVENANCE_BLOCKED_CAPABILITY,
            ),
            "Terminate the navigation and perception pilot episode.",
        ),
    ),
    privileged_tools=(),
    privacy_exclusions=_MOLMO_PRIVATE_EXCLUSIONS,
    summary=(
        "Real robot cleanup-shaped profile for physical navigation and "
        "perception pilots; manipulation remains blocked."
    ),
)

_PROFILES = {
    HOUSEHOLD_WORLD_PROFILE: _HOUSEHOLD_WORLD_PROFILE,
    HOUSEHOLD_MANIPULATION_PROFILE: _HOUSEHOLD_MANIPULATION_PROFILE,
    HOUSEHOLD_EPISODE_PROFILE: _HOUSEHOLD_EPISODE_PROFILE,
    MOLMOSPACES_CLEANUP_PROFILE: _MOLMO_PROFILE,
    REAL_ROBOT_CLEANUP_PROFILE: _REAL_ROBOT_PROFILE,
}

validate_all_contract_profiles()
