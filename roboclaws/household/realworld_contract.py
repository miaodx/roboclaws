from __future__ import annotations

import copy
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from roboclaws.household import realworld_contract_init, realworld_contract_payloads
from roboclaws.household.backend import API_SEMANTIC_PROVENANCE
from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.planner_observed_binding import (
    observed_handle_planner_binding,
)
from roboclaws.household.raw_fpv_guidance import (
    RAW_FPV_DECLARATION_STRATEGY,
    raw_fpv_inline_candidate_instruction,
    raw_fpv_visual_candidate_recovery,
    raw_fpv_visual_candidate_recovery_hint,
)
from roboclaws.household.realworld_policy_trace import (
    cleanup_policy_trace_from_events as _cleanup_policy_trace_from_events,
)
from roboclaws.household.robot_view_pose import room_for_point
from roboclaws.household.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)
from roboclaws.household.semantic_timeline import SEMANTIC_LOOP_VARIANT
from roboclaws.household.target_query import resolve_target_query
from roboclaws.household.task_intent import (
    TASK_INTENT_MODE_DEFAULT,
    household_intent_is_open_ended,
    normalize_household_intent,
    normalize_task_intent_mode,
)
from roboclaws.household.types import CleanupScenario
from roboclaws.household.visual_grounding import (
    EXTERNAL_VISUAL_GROUNDING_PROVENANCE,
    SIM_VISUAL_GROUNDING_PIPELINE_ID,
    VisualGroundingClient,
    VisualGroundingContractError,
    image_payload_for_raw_observation,
    pipeline_summary_from_response,
    sim_visual_grounding_pipeline,
    visual_grounding_failure_response,
    visual_grounding_request,
)
from roboclaws.household.visual_scan_guidance import (
    VISUAL_SCAN_NOOP_ERROR_REASON,
    noop_camera_adjustment_hint,
    visual_evidence_recovery_hint,
    visual_scan_done_recovery_hint,
    visual_scan_payload,
)
from roboclaws.maps.bundle import metric_map_bundle_metadata
from roboclaws.maps.route import SIM_COSTMAP_PLANNER, validate_metric_map_route

REALWORLD_CONTRACT = "realworld_cleanup_v1"
REAL_ROBOT_MAP_BUNDLE_SCHEMA = "real_robot_map_bundle_v1"
RUNTIME_METRIC_MAP_SCHEMA = "runtime_metric_map_v1"
TARGET_SEARCH_SUMMARY_SCHEMA = "target_search_summary_v1"
INSPECTION_OBSERVATION_SCHEMA = "target_inspection_observation_v1"
CLEANUP_WORKLIST_SCHEMA = "cleanup_worklist_v1"
CLEANUP_POLICY_TRACE_SCHEMA = "cleanup_policy_trace_v1"
REAL_ROBOT_READINESS_SCHEMA = "real_robot_readiness_v1"
MINIMAL_MAP_MODE = "minimal"
DEFAULT_MAP_MODE = MINIMAL_MAP_MODE
REALWORLD_MAP_MODES = frozenset({MINIMAL_MAP_MODE})
DETERMINISTIC_SWEEP_POLICY = "deterministic_sweep_baseline"
DEFAULT_REALWORLD_TASK = "帮我收拾这个房间"
VISIBLE_OBJECT_DETECTIONS_MODE = "visible_object_detections"
RAW_FPV_ONLY_MODE = "raw_fpv_only"
CAMERA_MODEL_POLICY_MODE = "camera_model_policy"
WORLD_LABELS_DETECTION_POLICY = "world_labels"
SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY = "sanitized_visible_object_detections"
VISIBLE_DETECTION_EXPOSURE_POLICIES = frozenset(
    {WORLD_LABELS_DETECTION_POLICY, SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY}
)
CAMERA_MODEL_POLICY_SCHEMA = "camera_model_policy_v1"
CAMERA_MODEL_POLICY_NAME = "camera_model_policy_baseline"
MODEL_DECLARED_OBSERVATION_SCHEMA = "model_declared_observation_v1"
MODEL_DECLARED_OBSERVATIONS_SCHEMA = "model_declared_observations_v1"
VISUAL_GROUNDING_EVIDENCE_SCHEMA = "visual_grounding_evidence_v1"
DONE_READINESS_SCHEMA = "done_readiness_v1"
DONE_READINESS_POLICY_RAW_FPV = "raw_fpv_grounded_cleanup_chains"
DONE_READINESS_POLICY_EXPLICIT = "explicit_grounded_cleanup_chains"
MODEL_DECLARED_OBSERVATION_SOURCE = "model_declared_observation"
MAIN_CLEANUP_AGENT_PRODUCER = "main_cleanup_agent"
TEST_AGENT_PRODUCER = "test_agent"
SIMULATED_CAMERA_MODEL_PROVENANCE = "simulated_camera_model"
SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE = "sanitized_visible_object_detections"
WORLD_LABELS_SANITIZED_PROFILE = "world-public-labels"
VISUAL_CANDIDATE_ALREADY_HANDLED_REASON = "visual_candidate_already_handled"
VISUAL_EVIDENCE_REVIEWABLE_STATUS = "reviewable"
VISUAL_EVIDENCE_NOT_REVIEWABLE_STATUS = "not_reviewable"
VISUAL_EVIDENCE_REQUIRED_ACTIONABILITY = "needs_visual_evidence"
TARGET_ACTIONABILITY_QUERY_UNMATCHED = "query_unmatched"
TARGET_ACTIONABILITY_VISIBLE_ONLY = "visible_only"
TARGET_ACTIONABILITY_ANCHOR_UNBOUND = "anchor_unbound"
TARGET_ACTIONABILITY_UNREACHABLE = "unreachable"
TARGET_ACTIONABILITY_NEEDS_OBSERVE = "needs_observe"
TARGET_ACTIONABILITY_ACTIONABLE = "actionable"
TARGET_ACTIONABILITY_STATUSES = frozenset(
    {
        TARGET_ACTIONABILITY_QUERY_UNMATCHED,
        TARGET_ACTIONABILITY_VISIBLE_ONLY,
        TARGET_ACTIONABILITY_ANCHOR_UNBOUND,
        TARGET_ACTIONABILITY_UNREACHABLE,
        TARGET_ACTIONABILITY_NEEDS_OBSERVE,
        TARGET_ACTIONABILITY_ACTIONABLE,
    }
)
CANDIDATE_STATE_SEMANTIC = "semantic_candidate"
CANDIDATE_STATE_VISUAL_SCAN_REQUIRED = "visual_scan_required"
CANDIDATE_STATE_VISUALLY_CONFIRMED = "visually_confirmed"
CANDIDATE_STATE_NAVIGATION_AUTHORIZED = "navigation_authorized"
VISUAL_GROUNDING_CATEGORY_HINTS = [
    "food",
    "dish",
    "book",
    "linen",
    "toy",
    "electronics",
    "pillow",
]
REALWORLD_PERCEPTION_MODES = frozenset(
    {
        VISIBLE_OBJECT_DETECTIONS_MODE,
        RAW_FPV_ONLY_MODE,
        CAMERA_MODEL_POLICY_MODE,
    }
)
_NON_ACTIONABLE_HANDLE_STATES = frozenset({"placed", "placed_closed", "skipped", "stale"})
_EXACT_VISUAL_CATEGORY_ALIASES = frozenset(
    {"cup", "mug", "plate", "bowl", "utensil", "fork", "knife", "spoon"}
)


_FORBIDDEN_AGENT_VIEW_KEYS = frozenset(
    {
        "generated_mess_set",
        "generated_mess_count",
        "environment_setup",
        "relocation_policy",
        "relocation_count",
        "relocated_object_ids",
        "relocated_objects",
        "before_relocation_positions",
        "after_relocation_positions",
        "target_count",
        "acceptable_destination_sets",
        "valid_receptacle_ids",
        "private_manifest",
        "is_misplaced",
        "global_movable_object_inventory",
        "target_receptacle_id",
    }
)

_OBJECT_CATEGORY_TARGETS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("dish", "cup", "mug", "plate", "bowl", "utensil", "fork", "knife", "spoon"),
        ("sink", "countertop"),
    ),
    (
        ("book", "newspaper", "notebook", "paper", "magazine"),
        ("shelvingunit", "bookshelf", "shelf", "desk"),
    ),
    (
        (
            "food",
            "apple",
            "bread",
            "egg",
            "potato",
            "lettuce",
            "tomato",
            "banana",
            "orange",
            "fruit",
            "vegetable",
            "produce",
        ),
        ("fridge", "refrigerator"),
    ),
    (
        (
            "remotecontrol",
            "remote",
            "electronics",
            "phone",
            "cellphone",
            "smartphone",
            "mobilephone",
            "laptop",
            "computer",
            "tablet",
            "controller",
            "alarmclock",
            "clock",
        ),
        ("tvstand", "tv stand"),
    ),
    (("pillow", "teddybear", "teddy", "plush", "cushion"), ("bed", "sofa")),
    (
        ("linen", "towel", "cloth", "blanket", "shirt", "clothing", "clothes"),
        ("laundryhamper", "laundry hamper", "hamper"),
    ),
    (
        ("toy", "toycar", "ball", "basketball", "soccer", "game", "teddybear", "teddy", "plush"),
        ("toybin", "toy bin"),
    ),
)

_INSIDE_DESTINATION_CATEGORY_TERMS = frozenset(
    {
        "bookcase",
        "bookshelf",
        "fridge",
        "refrigerator",
        "shelf",
        "shelving",
        "shelvingunit",
    }
)


class RealWorldCleanupContract:
    """ADR-0003 public/private cleanup contract.

    The wrapped ``CleanupBackendSession`` still owns state mutation and
    deterministic private scoring. This contract is the public agent boundary:
    it exposes metric navigation, room-level fixture hints, and robot-local
    observed object handles instead of a global object-inventory oracle.
    """

    def __init__(
        self,
        contract: CleanupBackendSession,
        *,
        task_prompt: str = DEFAULT_REALWORLD_TASK,
        fixture_hint_mode: str = "room_only",
        perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
        map_bundle_dir: str | Path | None = None,
        visual_grounding_client: VisualGroundingClient | None = None,
        visual_grounding_pipeline_id: str = SIM_VISUAL_GROUNDING_PIPELINE_ID,
        visual_grounding_artifact_base_dir: str | Path | None = None,
        visual_grounding_run_id: str = "",
        runtime_map_prior: dict[str, Any] | None = None,
        map_mode: str = DEFAULT_MAP_MODE,
        cleanup_profile: str | None = None,
        public_acceptance_config: dict[str, Any] | None = None,
    ) -> None:
        realworld_contract_init.validate_contract_options(
            fixture_hint_mode=fixture_hint_mode,
            perception_mode=perception_mode,
            map_mode=map_mode,
        )
        self.contract = contract
        self.backend = contract.backend
        self.scenario: CleanupScenario = contract.backend.scenario
        self.task_prompt = task_prompt
        self.fixture_hint_mode = fixture_hint_mode
        self.perception_mode = perception_mode
        self.map_mode = map_mode
        realworld_contract_init.init_profile_and_acceptance(
            self,
            cleanup_profile,
            public_acceptance_config,
        )
        realworld_contract_init.init_visual_grounding(
            self,
            visual_grounding_client=visual_grounding_client,
            visual_grounding_pipeline_id=visual_grounding_pipeline_id,
            visual_grounding_artifact_base_dir=visual_grounding_artifact_base_dir,
            visual_grounding_run_id=visual_grounding_run_id,
        )
        realworld_contract_init.init_map_projection(self, map_bundle_dir)
        realworld_contract_init.init_public_map_projection(self)
        self._current_waypoint_id = realworld_contract_init.initial_waypoint_id(self)
        realworld_contract_init.init_runtime_state(self, runtime_map_prior)

    def _apply_scene_room_outlines_to_fixtures(
        self,
        room_outlines: list[dict[str, Any]],
    ) -> None:
        for fixture_id, fixture in list(self._fixtures.items()):
            pose = _scene_index_fixture_pose(self.backend, fixture_id)
            if pose is None:
                continue
            room_id = room_for_point(room_outlines, pose[:2]) or str(
                room_outlines[0].get("room_id")
                or fixture.get("room_id")
                or fixture.get("room_area")
            )
            outline = _room_outline_by_id(room_outlines, room_id) or room_outlines[0]
            fixture["room_id"] = room_id
            fixture["room_area"] = room_id
            fixture["scene_room_outline"] = dict(outline)
            fixture["pose"] = {
                "frame_id": "map",
                "x": round(float(pose[0]), 6),
                "y": round(float(pose[1]), 6),
                "yaw": 0.0,
            }
            fixture["scene_room_outline_provenance"] = str(
                outline.get("provenance") or "scene_room_outline"
            )

    def public_tool_names(self) -> list[str]:
        return [
            "metric_map",
            "navigate_to_room",
            "navigate_to_waypoint",
            "observe",
            "adjust_camera",
            "declare_visual_candidates",
            "navigate_to_visual_candidate",
            "inspect_visible_object",
            "resolve_target_query",
            "navigate_to_object",
            "pick",
            "navigate_to_receptacle",
            "open_receptacle",
            "place",
            "place_inside",
            "close_receptacle",
            "done",
        ]

    def public_receptacles_by_id(self) -> dict[str, dict[str, Any]]:
        if self.map_mode == MINIMAL_MAP_MODE:
            return {
                str(item["fixture_id"]): dict(item)
                for item in self._public_runtime_fixture_candidates()
            }
        return {fixture_id: dict(fixture) for fixture_id, fixture in self._fixtures.items()}

    def internal_fixture_id_for_public_reference(self, fixture_id: str | None) -> str | None:
        if fixture_id is None:
            return None
        resolved = self._internal_fixture_id_for_public_anchor(str(fixture_id))
        return resolved or str(fixture_id)

    def _minimal_metric_map(self) -> dict[str, Any]:
        source = (
            copy.deepcopy(self._bundle_metric_map_template)
            if self._bundle_metric_map_template is not None
            else self._fallback_metric_map_template()
        )
        frame_id = str(source.get("frame_id") or "map")
        map_id = str(source.get("map_id") or f"{self.scenario.scenario_id}_minimal_map")
        map_version = str(source.get("map_version") or "minimal-navigation-map-v1")
        metric_map = {
            "ok": True,
            "tool": "metric_map",
            "status": "ok",
            "contract": REALWORLD_CONTRACT,
            "schema": REAL_ROBOT_MAP_BUNDLE_SCHEMA,
            "mode": MINIMAL_MAP_MODE,
            "frame_id": frame_id,
            "map_id": map_id,
            "map_version": map_version,
            "resolution_m": float(source.get("resolution_m") or 0.05),
            "origin": dict(source.get("origin") or {"x": 0.0, "y": 0.0, "yaw": 0.0}),
            "width": int(source.get("width") or 240),
            "height": int(source.get("height") or 180),
            "occupancy_values": dict(
                source.get("occupancy_values") or {"unknown": -1, "free": 0, "occupied": 100}
            ),
            "occupancy_grid_artifact": source.get("occupancy_grid_artifact"),
            "map_bundle": dict(
                source.get("map_bundle")
                or metric_map_bundle_metadata(
                    environment_id=self.scenario.scenario_id,
                    map_id=map_id,
                    map_version=map_version,
                )
            ),
            "rooms": [dict(item) for item in self._public_rooms],
            "room_category_hints": _room_category_hints_from_public_rooms(
                self._public_rooms,
                self._public_waypoints,
            ),
            "driveable_ways": _public_driveable_ways(source, self._public_rooms),
            "robot_pose": {
                "frame_id": frame_id,
                **self._current_pose(),
                "room_id": self._current_room_id(),
                "waypoint_id": self._current_waypoint_id,
                "pose_source": "generated_exploration_candidate",
            },
            "inspection_waypoints": [
                {
                    **dict(item),
                    "visited": str(item.get("waypoint_id") or "") in self._observed_waypoint_ids,
                }
                for item in self._public_navigation_waypoints()
            ],
            "generated_exploration_candidates": [
                {
                    **dict(item),
                    "visited": str(item.get("waypoint_id") or "") in self._observed_waypoint_ids,
                }
                for item in self._public_waypoints
            ],
            "generated_target_inspection_candidates": [
                {
                    **dict(item),
                    "visited": str(item.get("waypoint_id") or "") in self._observed_waypoint_ids,
                }
                for item in self._generated_inspection_waypoints.values()
            ],
            "minimal_map": {
                "enabled": True,
                "source": "public_occupancy_free_space",
                "generated_candidate_count": len(self._public_waypoints),
                "source_rooms_hidden": False,
                "source_room_labels_visible": bool(self._public_rooms),
                "source_fixtures_hidden": True,
                "source_inspection_waypoints_hidden": True,
                "public_contract_note": (
                    "Minimal map mode exposes occupancy geometry and generated "
                    "exploration candidates plus public room labels, not authored "
                    "fixture or movable-object semantics."
                ),
            },
            "public_contract_note": (
                "Base Navigation Map projection: public room labels and generated "
                "exploration candidates are visible. Static fixture tables, source "
                "inspection waypoint ids, movable-object inventory, and private scoring "
                "truth are hidden; Runtime Metric Map observations enrich the run."
            ),
        }
        metric_map["runtime_metric_map"] = self.runtime_metric_map_payload(
            metric_map=metric_map,
            fixture_hints=self.fixture_hints(),
        )
        _assert_no_forbidden_agent_view_keys(metric_map)
        return metric_map

    def metric_map(self) -> dict[str, Any]:
        if self.map_mode == MINIMAL_MAP_MODE:
            return self._minimal_metric_map()
        if self._bundle_metric_map_template is not None:
            metric_map = copy.deepcopy(self._bundle_metric_map_template)
            frame_id = str(metric_map.get("frame_id") or "map")
            metric_map["robot_pose"] = {
                "frame_id": frame_id,
                **self._current_pose(),
                "room_id": self._current_room_id(),
                "waypoint_id": self._current_waypoint_id,
                "pose_source": "selected_nav2_map_bundle_waypoint",
            }
            metric_map["inspection_waypoints"] = [
                {
                    **dict(item),
                    "visited": str(item.get("waypoint_id") or "") in self._observed_waypoint_ids,
                }
                for item in [
                    *(metric_map.get("inspection_waypoints") or []),
                    *self._generated_inspection_waypoints.values(),
                ]
            ]
            metric_map["generated_target_inspection_candidates"] = [
                {
                    **dict(item),
                    "visited": str(item.get("waypoint_id") or "") in self._observed_waypoint_ids,
                }
                for item in self._generated_inspection_waypoints.values()
            ]
            metric_map["contract"] = REALWORLD_CONTRACT
            metric_map["tool"] = "metric_map"
            metric_map["status"] = "ok"
            metric_map["ok"] = True
            metric_map["public_contract_note"] = (
                "Metric map projection was derived from the selected prebuilt Nav2 "
                "map bundle. Runtime movable objects and private scoring truth are "
                "not encoded."
            )
            metric_map["runtime_metric_map"] = self.runtime_metric_map_payload(
                metric_map=metric_map,
                fixture_hints=self.fixture_hints(),
            )
            _assert_no_forbidden_agent_view_keys(metric_map)
            return metric_map

        frame_id = "map"
        map_id = f"{self.scenario.scenario_id}_semantic_map"
        map_version = "static-fixture-map-v1"
        metric_map = self._ok(
            "metric_map",
            contract=REALWORLD_CONTRACT,
            schema=REAL_ROBOT_MAP_BUNDLE_SCHEMA,
            frame_id=frame_id,
            map_id=map_id,
            map_version=map_version,
            resolution_m=0.05,
            origin={"x": 0.0, "y": 0.0, "yaw": 0.0},
            width=240,
            height=180,
            occupancy_values={
                "unknown": -1,
                "free": 0,
                "occupied": 100,
            },
            occupancy_grid_artifact=None,
            map_bundle=metric_map_bundle_metadata(
                environment_id=self.scenario.scenario_id,
                map_id=map_id,
                map_version=map_version,
            ),
            rooms=[_metric_map_room_payload(room) for room in self._rooms],
            driveable_ways=_driveable_ways(self._rooms),
            robot_pose={
                "frame_id": frame_id,
                **self._current_pose(),
                "room_id": self._current_room_id(),
                "waypoint_id": self._current_waypoint_id,
                "pose_source": "metric_map_semantic_waypoint",
            },
            inspection_waypoints=[
                {
                    "waypoint_id": item["waypoint_id"],
                    "frame_id": frame_id,
                    "x": item["x"],
                    "y": item["y"],
                    "yaw": item["yaw"],
                    "room_id": item["room_id"],
                    "label": item["label"],
                    "purpose": item["purpose"],
                    "waypoint_source": item["waypoint_source"],
                    "coverage_estimate": item["coverage_estimate"],
                    "visited": item["waypoint_id"] in self._observed_waypoint_ids,
                }
                for item in self._public_navigation_waypoints()
            ],
            generated_target_inspection_candidates=[
                {
                    **dict(item),
                    "visited": str(item.get("waypoint_id") or "") in self._observed_waypoint_ids,
                }
                for item in self._generated_inspection_waypoints.values()
            ],
            public_contract_note=(
                "Inspection waypoints are static map/fixture coverage candidates, "
                "not generated from movable-object locations, generated mess set, "
                "target count, or acceptable destination sets."
            ),
        )
        metric_map["runtime_metric_map"] = self.runtime_metric_map_payload(
            metric_map=metric_map,
            fixture_hints=self.fixture_hints(),
        )
        _assert_no_forbidden_agent_view_keys(metric_map)
        return metric_map

    def fixture_hints(self) -> dict[str, Any]:
        if self.map_mode == MINIMAL_MAP_MODE:
            return self._minimal_fixture_hints()
        if self._bundle_fixture_hints_template is not None:
            fixture_hints = copy.deepcopy(self._bundle_fixture_hints_template)
            if self._scene_index_fixture_overlay:
                fixture_hints["rooms"] = _fixture_hints_with_scene_index_overlay(
                    fixture_hints.get("rooms") or [],
                    self._scene_index_fixture_overlay,
                    fixture_hint_mode=self.fixture_hint_mode,
                )
                fixture_hints["scene_index_fixture_overlay"] = {
                    "enabled": True,
                    "source": "isaac_scene_index",
                    "fixture_count": len(self._scene_index_fixture_overlay),
                    "public_contract_note": (
                        "Scene-index fixtures are public USD-stage receptacle candidates "
                        "used to keep cleanup routing aligned with the loaded Isaac scene. "
                        "They do not include private acceptable-destination sets."
                    ),
                }
            fixture_hints["contract"] = REALWORLD_CONTRACT
            fixture_hints["tool"] = "fixture_hints"
            fixture_hints["status"] = "ok"
            fixture_hints["ok"] = True
            fixture_hints["fixture_hint_mode"] = self.fixture_hint_mode
            overlay_note = (
                " A public Isaac scene-index fixture overlay is preferred for "
                "backend-generated scene-specific cleanup scenarios."
                if self._scene_index_fixture_overlay
                else ""
            )
            fixture_hints["public_contract_note"] = (
                "Static fixture hints are projected from the selected prebuilt Nav2 "
                "map bundle. Runtime movable-object observations remain separate "
                f"observed_* handles.{overlay_note}"
            )
            _assert_no_forbidden_agent_view_keys(fixture_hints)
            return fixture_hints

        rooms = []
        for room in self._rooms:
            fixtures = []
            for fixture_id in room["fixture_ids"]:
                fixture = self._fixtures[fixture_id]
                item = {
                    "fixture_id": fixture_id,
                    "category": fixture.get("category") or fixture.get("name", ""),
                    "name": fixture.get("name", fixture_id),
                    "room_id": room["room_id"],
                    "affordances": _fixture_affordances(fixture),
                    "footprint": _fixture_footprint(fixture_id),
                    "pose": self._fixture_pose(fixture_id),
                    "manipulation_frame": f"{fixture_id}_manipulation",
                    "preferred_inspection_waypoint_id": self._preferred_waypoint_for_fixture(
                        fixture_id
                    ),
                    "preferred_manipulation_waypoint_id": self._preferred_waypoint_for_fixture(
                        fixture_id
                    ),
                    "position_detail": self.fixture_hint_mode,
                }
                if self.fixture_hint_mode == "exact_fixtures":
                    item["room_position"] = "operator_selected_exact_fixture_hint"
                fixtures.append(item)
            rooms.append(
                {
                    "room_id": room["room_id"],
                    "room_label": room["room_label"],
                    "polygon": room.get("polygon", []),
                    "fixtures": fixtures,
                }
            )
        return self._ok(
            "fixture_hints",
            contract=REALWORLD_CONTRACT,
            schema="static_fixture_semantic_map_v1",
            fixture_hint_mode=self.fixture_hint_mode,
            contains_runtime_observations=False,
            public_contract_note=(
                "Static fixture hints describe rooms, fixed receptacles, and affordances. "
                "Runtime movable-object observations remain separate observed_* handles."
            ),
            rooms=rooms,
        )

    def _minimal_fixture_hints(self) -> dict[str, Any]:
        payload = self._ok(
            "fixture_hints",
            contract=REALWORLD_CONTRACT,
            schema="static_fixture_semantic_map_v1",
            mode=MINIMAL_MAP_MODE,
            fixture_hint_mode=self.fixture_hint_mode,
            contains_runtime_observations=False,
            rooms=[],
            generated_exploration_candidate_count=len(self._public_waypoints),
            public_contract_note=(
                "Base Navigation Map mode intentionally hides authored fixture tables. "
                "Public room labels live on metric_map.rooms and room_category_hints. "
                "Runtime observed handles and map update candidates must come from "
                "public observations, not source-map semantics."
            ),
        )
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

    def navigate_to_room(self, room_id: str) -> dict[str, Any]:
        room = next((item for item in self._rooms if item["room_id"] == room_id), None)
        if room is None:
            return self._error("navigate_to_room", "stale_reference", room_id=room_id)
        waypoint = next(item for item in self._waypoints if item["room_id"] == room_id)
        return self.navigate_to_waypoint(str(waypoint["waypoint_id"]))

    def navigate_to_waypoint(self, waypoint_id: str) -> dict[str, Any]:
        waypoint = self._waypoint_by_id(waypoint_id)
        if waypoint is None:
            return self._error("navigate_to_waypoint", "stale_reference", waypoint_id=waypoint_id)
        start_waypoint_id = self._current_waypoint_id
        route = validate_metric_map_route(
            self.metric_map(),
            self.fixture_hints(),
            start_waypoint_id=start_waypoint_id,
            goal_waypoint_id=waypoint_id,
        )
        if not route.ok:
            return self._error(
                "navigate_to_waypoint",
                "blocked_capability",
                navigation_backend=SIM_COSTMAP_PLANNER,
                primitive_provenance=API_SEMANTIC_PROVENANCE,
                route_validation=route.as_dict(),
                waypoint_id=waypoint_id,
                room_id=waypoint["room_id"],
                goal_pose={"frame_id": "map", **self._waypoint_pose(waypoint)},
                pose_source="inspection_waypoint",
            )
        self._current_waypoint_id = waypoint_id
        self._reset_camera_adjustment()
        navigation_waypoint = self._private_waypoint_for_public_waypoint(waypoint)
        navigation_waypoint = self._backend_navigation_waypoint(navigation_waypoint)
        navigation = self.contract.navigate_to_waypoint(navigation_waypoint)
        return self._ok(
            "navigate_to_waypoint",
            navigation_backend=SIM_COSTMAP_PLANNER,
            primitive_provenance=API_SEMANTIC_PROVENANCE,
            route_validation=route.as_dict(),
            goal_pose={"frame_id": "map", **self._waypoint_pose(waypoint)},
            backend_goal_pose={
                "frame_id": "map",
                **self._waypoint_pose(navigation_waypoint),
                "room_id": str(navigation_waypoint.get("room_id") or waypoint["room_id"]),
                "waypoint_id": str(navigation_waypoint.get("waypoint_id") or waypoint_id),
            },
            pose_source="inspection_waypoint",
            staleness_s=0.0,
            pose_confidence=1.0,
            pose_covariance=[0.0, 0.0, 0.0],
            requires_reobserve=False,
            waypoint_id=waypoint_id,
            room_id=waypoint["room_id"],
            coverage_estimate=waypoint["coverage_estimate"],
            backend_pose_mutation=navigation,
            navigation_status=(navigation or {}).get("status", "ok"),
        )

    def resolve_target_query(
        self,
        query: str,
        *,
        operation: str = "inspect",
        max_results: int = 8,
    ) -> dict[str, Any]:
        runtime_map = self.runtime_metric_map_payload(
            metric_map=self.metric_map(),
            fixture_hints=self.fixture_hints(),
        )
        resolution = resolve_target_query(
            runtime_map,
            query,
            operation=operation,
            max_results=max_results,
        )
        return self._ok(
            "resolve_target_query",
            **{key: value for key, value in resolution.items() if key not in {"tool", "ok"}},
        )

    def observe(self) -> dict[str, Any]:
        waypoint = self._waypoint_by_id(self._current_waypoint_id)
        if waypoint is None:
            return self._error("observe", "missing_waypoint")
        self._observed_waypoint_ids.add(str(waypoint["waypoint_id"]))
        self._seed_public_fixture_anchor_ids_for_waypoint(waypoint)
        if self.perception_mode in {RAW_FPV_ONLY_MODE, CAMERA_MODEL_POLICY_MODE}:
            raw_observation = self._record_raw_fpv_observation(
                waypoint,
                perception_mode=self.perception_mode,
            )
            if self.perception_mode == CAMERA_MODEL_POLICY_MODE:
                instruction = (
                    "Camera-labels mode: call declare_visual_candidates with this "
                    "observation_id to register model-declared cleanup candidates. "
                    "Built-in visible_object_detections remain empty."
                )
                perception_source = CAMERA_MODEL_POLICY_MODE
                camera_model_available = True
            else:
                instruction = raw_fpv_inline_candidate_instruction(
                    str(raw_observation["observation_id"])
                )
                perception_source = RAW_FPV_ONLY_MODE
                camera_model_available = False
            response = self._ok(
                "observe",
                contract=REALWORLD_CONTRACT,
                current_room_id=waypoint["room_id"],
                waypoint_id=waypoint["waypoint_id"],
                observation_role="coverage_scan"
                if self._held_handle is None
                else "held_object_area_check",
                waypoint_source=waypoint.get("waypoint_source", "static_map_coverage"),
                perception_mode=self.perception_mode,
                perception_source=perception_source,
                structured_detections_available=False,
                visible_object_detections=[],
                raw_fpv_observation=raw_observation,
                camera_model_policy_available=camera_model_available,
                model_declaration_available=True,
                held_object_id=self._held_handle,
                private_target_truth_included=False,
                instruction=instruction,
            )
            self._record_inspection_observation(
                response,
                detections=[],
                source_observation_id=str(raw_observation["observation_id"]),
            )
            return response
        source_observation_id = self._next_visible_observation_id()
        detections = self._visible_detections_for_waypoint(
            waypoint,
            source_observation_id=source_observation_id,
            visual_confirmation=self._camera_scan_confirmed(),
        )
        perception_source = (
            SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
            if self.sanitize_world_labels
            else "robot_local_visible_object_detections"
        )
        response = self._ok(
            "observe",
            contract=REALWORLD_CONTRACT,
            current_room_id=waypoint["room_id"],
            waypoint_id=waypoint["waypoint_id"],
            observation_role="coverage_scan"
            if self._held_handle is None
            else "held_object_area_check",
            source_observation_id=source_observation_id,
            waypoint_source=waypoint.get("waypoint_source", "static_map_coverage"),
            perception_mode=self.perception_mode,
            detection_exposure_policy=self.visible_detection_exposure_policy,
            structured_detections_available=True,
            visible_object_detections=[
                self._agent_visible_detection_payload(detection) for detection in detections
            ],
            held_object_id=self._held_handle,
            perception_source=perception_source,
            private_target_truth_included=False,
        )
        self._record_inspection_observation(
            response,
            detections=detections,
            source_observation_id=source_observation_id,
        )
        return response

    def adjust_camera(
        self,
        yaw_delta_deg: float = 0.0,
        pitch_delta_deg: float = 0.0,
    ) -> dict[str, Any]:
        previous = self._camera_offset()
        yaw_delta = _float_or_zero(yaw_delta_deg)
        pitch_delta = _float_or_zero(pitch_delta_deg)
        if not yaw_delta and not pitch_delta:
            return self._error(
                "adjust_camera",
                VISUAL_SCAN_NOOP_ERROR_REASON,
                camera_offset=previous,
                previous_camera_offset=previous,
                required_next_tool="adjust_camera",
                followup_tool="observe",
                yaw_bounds_deg=[-45, 45],
                pitch_bounds_deg=[-20, 20],
                waypoint_id=self._current_waypoint_id,
                recovery_hint=noop_camera_adjustment_hint(),
                no_camera_motion=True,
                fresh_fpv_observation_required=True,
            )
        self._camera_yaw_offset_deg = _clamp(
            self._camera_yaw_offset_deg + yaw_delta,
            -45.0,
            45.0,
        )
        self._camera_pitch_offset_deg = _clamp(
            self._camera_pitch_offset_deg + pitch_delta,
            -20.0,
            20.0,
        )
        current = self._camera_offset()
        event = {
            "event_id": f"camera_adjustment_{len(self._camera_adjustment_events) + 1:03d}",
            "waypoint_id": self._current_waypoint_id,
            "previous_camera_offset": previous,
            "camera_offset": current,
            "yaw_delta_deg": yaw_delta,
            "pitch_delta_deg": pitch_delta,
            "followup_tool": "observe",
            "public_contract_note": (
                "Camera adjustment is bounded public perception control and resets on navigation."
            ),
        }
        _assert_no_forbidden_agent_view_keys(event)
        self._camera_adjustment_events.append(event)
        return self._ok(
            "adjust_camera",
            camera_offset=current,
            previous_camera_offset=previous,
            yaw_bounds_deg=[-45, 45],
            pitch_bounds_deg=[-20, 20],
            waypoint_id=self._current_waypoint_id,
            public_contract_note=(
                "Camera adjustment is bounded public perception control and resets on navigation."
            ),
        )

    def declare_visual_candidates(
        self,
        observation_id: str | None = None,
        *,
        candidates: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
        producer_type: str = SIMULATED_CAMERA_MODEL_PROVENANCE,
        producer_id: str = CAMERA_MODEL_POLICY_NAME,
    ) -> dict[str, Any]:
        if self.perception_mode not in {RAW_FPV_ONLY_MODE, CAMERA_MODEL_POLICY_MODE}:
            return self._error(
                "declare_visual_candidates",
                "unsupported_perception_mode",
                perception_mode=self.perception_mode,
            )
        raw_observation = self._raw_fpv_observation_by_id(observation_id)
        if raw_observation is None:
            return self._error(
                "declare_visual_candidates",
                "missing_raw_fpv_observation",
                observation_id=observation_id or "",
            )
        waypoint = self._waypoint_by_id(str(raw_observation["waypoint_id"]))
        if waypoint is None:
            return self._error(
                "declare_visual_candidates",
                "missing_waypoint",
                observation_id=str(raw_observation["observation_id"]),
            )

        candidate_inputs = list(candidates or [])
        visual_grounding_pipeline: dict[str, Any]
        if not candidate_inputs:
            if self.perception_mode == RAW_FPV_ONLY_MODE:
                return self._error(
                    "declare_visual_candidates",
                    "empty_raw_fpv_candidate_registration",
                    observation_id=str(raw_observation["observation_id"]),
                    recovery_hint=(
                        "In camera-raw-fpv mode, call navigate_to_visual_candidate with one "
                        "explicit candidate when acting on public FPV evidence. Empty "
                        "candidate registration is reserved for camera-grounded-labels producers."
                    ),
                )
            producer_result = self._camera_label_producer_candidates(
                raw_observation=raw_observation,
                waypoint=waypoint,
            )
            visual_grounding_pipeline = producer_result["visual_grounding_pipeline"]
            if not producer_result["ok"]:
                return self._error(
                    "declare_visual_candidates",
                    str(producer_result["error_reason"]),
                    observation_id=str(raw_observation["observation_id"]),
                    visual_grounding_pipeline=visual_grounding_pipeline,
                    recovery_hint=producer_result.get("recovery_hint", ""),
                )
            candidate_inputs = list(producer_result["candidates"])
            if visual_grounding_pipeline.get("status") == "failed":
                evidence = self._model_declared_observation_event(
                    raw_observation=raw_observation,
                    producer_type=EXTERNAL_VISUAL_GROUNDING_PROVENANCE,
                    producer_id=self.visual_grounding_pipeline_id,
                    declared=[],
                    visual_grounding_pipeline=visual_grounding_pipeline,
                )
                self._camera_model_policy_events.append(evidence)
                return self._ok(
                    "declare_visual_candidates",
                    contract=REALWORLD_CONTRACT,
                    model_declared_observation_evidence=evidence,
                    model_declared_observations=[],
                    camera_model_candidates=[],
                    visible_object_detections=[],
                    private_target_truth_included=False,
                )
            if self.visual_grounding_pipeline_id != SIM_VISUAL_GROUNDING_PIPELINE_ID:
                producer_type = EXTERNAL_VISUAL_GROUNDING_PROVENANCE
                producer_id = self.visual_grounding_pipeline_id
        else:
            visual_grounding_pipeline = _manual_visual_grounding_pipeline(
                candidate_count=len(candidate_inputs),
                producer_type=producer_type,
                producer_id=producer_id,
            )
        declared = []
        for index, candidate in enumerate(candidate_inputs):
            candidate_error = _visual_candidate_validation_error(
                candidate,
                require_target_fixture_id=self.map_mode != MINIMAL_MAP_MODE,
                map_mode=self.map_mode,
                perception_mode=self.perception_mode,
                producer_type=producer_type,
            )
            if candidate_error is not None:
                source_observation_id = str(raw_observation["observation_id"])
                return self._error(
                    "declare_visual_candidates",
                    "invalid_visual_candidate",
                    observation_id=source_observation_id,
                    candidate_index=index,
                    candidate_error=candidate_error,
                    raw_fpv_candidate_recovery=raw_fpv_visual_candidate_recovery(
                        source_observation_id=source_observation_id,
                        map_mode=self.map_mode,
                    ),
                    recovery_hint=raw_fpv_visual_candidate_recovery_hint(
                        source_observation_id=source_observation_id,
                        map_mode=self.map_mode,
                    ),
                )
            declared.append(
                self._register_model_declared_candidate(
                    raw_observation=raw_observation,
                    waypoint=waypoint,
                    candidate=candidate,
                    producer_type=producer_type,
                    producer_id=producer_id,
                )
            )
        resolved_candidates = [
            dict(self._detections_by_handle[str(item["object_id"])])
            for item in declared
            if item.get("grounding_status") == "resolved"
            and str(item.get("object_id") or "") in self._detections_by_handle
        ]
        evidence = self._model_declared_observation_event(
            raw_observation=raw_observation,
            producer_type=producer_type,
            producer_id=producer_id,
            declared=declared,
            visual_grounding_pipeline=visual_grounding_pipeline,
        )
        _assert_no_forbidden_agent_view_keys(evidence)
        if self.perception_mode == CAMERA_MODEL_POLICY_MODE:
            self._camera_model_policy_events.append(evidence)
        return self._ok(
            "declare_visual_candidates",
            contract=REALWORLD_CONTRACT,
            model_declared_observation_evidence=evidence,
            model_declared_observations=[
                self._public_fixture_reference_payload(item) for item in declared
            ],
            camera_model_candidates=[
                self._agent_visible_detection_payload(item) for item in resolved_candidates
            ],
            visible_object_detections=[],
            private_target_truth_included=False,
        )

    def navigate_to_visual_candidate(
        self,
        source_observation_id: str | None = None,
        category: str = "",
        target_fixture_id: str = "",
        evidence_note: str = "",
        image_region: dict[str, Any] | str | None = None,
        *,
        source_fixture_id: str = "",
        confidence: float | None = None,
        producer_type: str = MAIN_CLEANUP_AGENT_PRODUCER,
        producer_id: str = "cleanup_agent",
    ) -> dict[str, Any]:
        declaration_response = self.declare_visual_candidates(
            source_observation_id,
            candidates=[
                {
                    "category": category,
                    "target_fixture_id": target_fixture_id,
                    "evidence_note": evidence_note,
                    "image_region": image_region,
                    "source_fixture_id": source_fixture_id,
                    "confidence": confidence,
                }
            ],
            producer_type=producer_type,
            producer_id=producer_id,
        )
        if not declaration_response.get("ok"):
            return self._error(
                "navigate_to_visual_candidate",
                str(declaration_response.get("error_reason") or "declaration_failed"),
                candidate_error=declaration_response.get("candidate_error", {}),
                raw_fpv_candidate_recovery=declaration_response.get(
                    "raw_fpv_candidate_recovery", {}
                ),
                recovery_hint=declaration_response.get("recovery_hint", ""),
            )
        declarations = declaration_response.get("model_declared_observations") or []
        declaration = declarations[0] if declarations else {}
        handle = str(declaration.get("object_id") or "")
        if declaration.get("actionability_status") == "already_handled":
            return self._error(
                "navigate_to_visual_candidate",
                VISUAL_CANDIDATE_ALREADY_HANDLED_REASON,
                model_declared_observation=self._public_fixture_reference_payload(declaration),
                object_id=handle,
                grounding_status=declaration.get("grounding_status", "unresolved"),
                actionability_status="already_handled",
                required_next_tool="observe",
                recovery_hint=declaration.get(
                    "recovery_hint",
                    "This observed handle was already handled; continue the waypoint sweep.",
                ),
            )
        if declaration.get("grounding_status") != "resolved":
            return self._error(
                "navigate_to_visual_candidate",
                "visual_candidate_not_resolved",
                model_declared_observation=self._public_fixture_reference_payload(declaration),
                object_id=handle,
                grounding_status=declaration.get("grounding_status", "unresolved"),
                grounding_confidence=declaration.get("grounding_confidence", 0.0),
                required_next_tool="observe",
                recovery_hint=declaration.get(
                    "recovery_hint",
                    "If one retry with a tighter image_region still does not resolve, "
                    "treat this visible item as non-actionable public clutter and "
                    "continue to another waypoint.",
                ),
            )
        detection = self._detections_by_handle.get(handle, {})
        candidate_fixture_id = self._public_fixture_reference_id(
            str(detection.get("candidate_fixture_id") or "")
        )
        cleanup_recommended = bool(detection.get("cleanup_recommended", False))
        recommended_tool = str(detection.get("recommended_tool") or "")
        visual_evidence_error = self._visual_evidence_actionability_error(
            "navigate_to_visual_candidate",
            handle,
        )
        if visual_evidence_error is not None:
            return self._error(
                "navigate_to_visual_candidate",
                str(visual_evidence_error.get("error_reason") or "visual_evidence_not_reviewable"),
                model_declared_observation=self._public_fixture_reference_payload(declaration),
                object_id=handle,
                candidate_fixture_id=candidate_fixture_id,
                candidate_fixture_category=detection.get("candidate_fixture_category", ""),
                cleanup_recommended=False,
                recommended_tool="",
                grounding_status=declaration.get("grounding_status", "resolved"),
                required_next_tool="observe",
                recovery_tool_options=visual_evidence_error.get("recovery_tool_options", []),
                actionability_status=visual_evidence_error.get(
                    "actionability_status",
                    VISUAL_EVIDENCE_REQUIRED_ACTIONABILITY,
                ),
                visual_grounding_evidence=visual_evidence_error.get(
                    "visual_grounding_evidence",
                    {},
                ),
                recovery_hint=visual_evidence_error.get("recovery_hint", ""),
            )
        if not candidate_fixture_id or not recommended_tool:
            return self._error(
                "navigate_to_visual_candidate",
                "visual_candidate_not_actionable",
                model_declared_observation=self._public_fixture_reference_payload(declaration),
                object_id=handle,
                candidate_fixture_id=candidate_fixture_id,
                candidate_fixture_category=detection.get("candidate_fixture_category", ""),
                cleanup_recommended=cleanup_recommended,
                recommended_tool=recommended_tool,
                grounding_status=declaration.get("grounding_status", "resolved"),
                required_next_tool="observe",
                recovery_hint=(
                    "This grounded object has no public cleanup destination from the current "
                    "map context. Do not pick it; continue the waypoint sweep and observe for "
                    "other cleanup objects."
                ),
            )
        navigation = self.navigate_to_object(handle)
        if not navigation.get("ok"):
            return self._error(
                "navigate_to_visual_candidate",
                str(navigation.get("error_reason") or "navigation_failed"),
                model_declared_observation=self._public_fixture_reference_payload(declaration),
                object_id=handle,
                visual_grounding_evidence=navigation.get("visual_grounding_evidence", {}),
                actionability_status=navigation.get("actionability_status", ""),
                recovery_hint=navigation.get("recovery_hint", ""),
            )
        payload = {
            key: value
            for key, value in navigation.items()
            if key
            not in {
                "tool",
                "ok",
                "status",
                "object_id",
                "visual_grounding_evidence",
                "actionability_status",
                "candidate_state",
            }
        }
        detection = self._detections_by_handle.get(handle, {})
        return self._ok(
            "navigate_to_visual_candidate",
            **payload,
            object_id=handle,
            model_declared_observation=self._public_fixture_reference_payload(declaration),
            candidate_fixture_id=self._public_fixture_reference_id(
                str(detection.get("candidate_fixture_id") or "")
            ),
            candidate_fixture_category=detection.get("candidate_fixture_category", ""),
            cleanup_recommended=cleanup_recommended,
            recommended_tool=recommended_tool,
            visual_grounding_evidence=self._visual_evidence_for_handle(handle),
            actionability_status="actionable",
            candidate_state=CANDIDATE_STATE_NAVIGATION_AUTHORIZED,
            declaration_strategy=RAW_FPV_DECLARATION_STRATEGY,
            required_next_tool="pick",
        )

    def inspect_visible_object(self, object_id: str) -> dict[str, Any]:
        detection = self._detections_by_handle.get(object_id)
        if detection is None:
            return self._error("inspect_visible_object", "stale_reference", object_id=object_id)
        return self._ok(
            "inspect_visible_object",
            contract=REALWORLD_CONTRACT,
            detection=self._agent_visible_detection_payload(dict(detection)),
            detection_exposure_policy=self.visible_detection_exposure_policy,
            private_target_truth_included=False,
        )

    def planner_observed_handle_binding(
        self,
        object_id: str,
        target_receptacle_id: str,
        *,
        source_receptacle_id: str = "",
        tools: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        internal_target_receptacle_id = (
            self.internal_fixture_id_for_public_reference(target_receptacle_id)
            or target_receptacle_id
        )
        return observed_handle_planner_binding(
            self,
            object_id=object_id,
            target_receptacle_id=internal_target_receptacle_id,
            source_receptacle_id=source_receptacle_id,
            tools=tools,
        )

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        if self._handle_is_non_actionable(object_id):
            return self._error(
                "navigate_to_object",
                "already_handled",
                object_id=object_id,
                required_next_tool="observe",
                recovery_hint=(
                    "This observed handle has already been placed or skipped. "
                    "Continue the waypoint sweep and observe for other cleanup objects."
                ),
            )
        internal_id = self._internal_object_id(object_id)
        if internal_id is None:
            grounding_error = self._unresolved_visual_candidate_error(
                "navigate_to_object", object_id
            )
            if grounding_error is not None:
                return grounding_error
            return self._error("navigate_to_object", "stale_reference", object_id=object_id)
        visual_evidence_error = self._visual_evidence_actionability_error(
            "navigate_to_object",
            object_id,
        )
        if visual_evidence_error is not None:
            return visual_evidence_error
        self._reset_camera_adjustment()
        response = self.contract.navigate_to_object(internal_id)
        if not response.get("ok"):
            return self._public_error_from_private("navigate_to_object", object_id, response)
        self._current_object_handle = object_id
        self._set_handle_state(object_id, "navigating_to_object", tool="navigate_to_object")
        return self._ok(
            "navigate_to_object",
            object_id=object_id,
            navigation_backend=response.get("navigation_backend", API_SEMANTIC_PROVENANCE),
            primitive_provenance=response.get(
                "primitive_provenance",
                API_SEMANTIC_PROVENANCE,
            ),
            goal_pose=self._object_goal_pose(object_id),
            pose_source="latest_observation",
            staleness_s=0.0,
            pose_confidence=self._object_pose_confidence(object_id),
            pose_covariance=[0.1, 0.1, 0.05],
            requires_reobserve=False,
            visual_grounding_evidence=self._visual_evidence_for_handle(object_id),
            actionability_status="actionable",
            candidate_state=CANDIDATE_STATE_NAVIGATION_AUTHORIZED,
            source_receptacle_id=response.get("source_receptacle_id"),
            previous_receptacle_id=response.get("previous_receptacle_id"),
            location_id=response.get("location_id"),
            state_mutation=response.get("state_mutation"),
            navigation_status=response.get("status"),
        )

    def pick(self, object_id: str) -> dict[str, Any]:
        if self._handle_is_non_actionable(object_id):
            return self._error(
                "pick",
                "already_handled",
                object_id=object_id,
                required_next_tool="observe",
                recovery_hint=(
                    "This observed handle has already been handled. Continue the "
                    "waypoint sweep instead of picking it again."
                ),
            )
        internal_id = self._internal_object_id(object_id)
        if internal_id is None:
            grounding_error = self._unresolved_visual_candidate_error("pick", object_id)
            if grounding_error is not None:
                return grounding_error
            return self._error("pick", "stale_reference", object_id=object_id)
        visual_evidence_error = self._visual_evidence_actionability_error("pick", object_id)
        if visual_evidence_error is not None:
            return visual_evidence_error
        if getattr(self, "_current_object_handle", None) != object_id:
            return self._semantic_order_error(
                "pick",
                required_tool="navigate_to_object",
                object_id=object_id,
                recovery_hint=(
                    "Call navigate_to_object with this observed object handle before pick. "
                    "The ADR-0003 clean loop is navigate_to_object -> pick -> "
                    "navigate_to_receptacle -> open_receptacle? -> place/place_inside "
                    "-> close_receptacle?."
                ),
            )
        picked = self.contract.pick(internal_id)
        if picked.get("ok"):
            self._held_handle = object_id
            self._current_object_handle = None
            self._current_receptacle_for_handle = None
            self._opened_receptacle_for_handle = None
            self._set_handle_state(object_id, "held", tool="pick")
        return self._public_manipulation_response("pick", object_id, picked)

    def navigate_to_receptacle(self, fixture_id: str) -> dict[str, Any]:
        requested_fixture_id = str(fixture_id)
        internal_fixture_id = self._internal_fixture_id_for_public_anchor(requested_fixture_id)
        if internal_fixture_id not in self._fixtures:
            return self._error(
                "navigate_to_receptacle",
                "stale_reference",
                fixture_id=requested_fixture_id,
            )
        if self._held_handle is None:
            return self._semantic_order_error(
                "navigate_to_receptacle",
                required_tool="pick",
                fixture_id=requested_fixture_id,
                recovery_hint=(
                    "Pick an observed object before navigating to a cleanup fixture. "
                    "Use navigate_to_object -> pick first."
                ),
            )
        response = self.contract.navigate_to_receptacle(internal_fixture_id)
        if not response.get("ok"):
            return self._public_error_from_private(
                "navigate_to_receptacle",
                self._held_handle or "",
                response,
            )
        self._current_waypoint_id = self._public_waypoint_id_for_private_fixture(
            internal_fixture_id
        )
        self._reset_camera_adjustment()
        self._current_receptacle_for_handle = (self._held_handle, internal_fixture_id)
        self._opened_receptacle_for_handle = None
        public_fixture_id = self._public_fixture_response_id(
            internal_fixture_id,
            requested_fixture_id,
        )
        return self._ok(
            "navigate_to_receptacle",
            object_id=self._held_handle,
            receptacle_id=public_fixture_id,
            fixture_id=public_fixture_id,
            navigation_backend=response.get("navigation_backend", API_SEMANTIC_PROVENANCE),
            primitive_provenance=response.get(
                "primitive_provenance",
                API_SEMANTIC_PROVENANCE,
            ),
            goal_pose=self._fixture_pose(internal_fixture_id),
            pose_source="fixture_semantic_map",
            staleness_s=0.0,
            pose_confidence=1.0,
            pose_covariance=[0.0, 0.0, 0.0],
            requires_reobserve=False,
            previous_receptacle_id=self._public_fixture_reference_id(
                str(response.get("previous_receptacle_id") or "")
            ),
            state_mutation=response.get("state_mutation"),
            navigation_status=response.get("status"),
        )

    def open_receptacle(self, fixture_id: str) -> dict[str, Any]:
        requested_fixture_id = str(fixture_id)
        internal_fixture_id = self._internal_fixture_id_for_public_anchor(requested_fixture_id)
        if internal_fixture_id not in self._fixtures:
            return self._error(
                "open_receptacle",
                "stale_reference",
                fixture_id=requested_fixture_id,
            )
        if self._held_handle is None:
            return self._semantic_order_error(
                "open_receptacle",
                required_tool="pick",
                fixture_id=requested_fixture_id,
                recovery_hint="Pick an observed object before opening a cleanup fixture.",
            )
        if self._current_receptacle_for_handle != (self._held_handle, internal_fixture_id):
            return self._semantic_order_error(
                "open_receptacle",
                required_tool="navigate_to_receptacle",
                object_id=self._held_handle,
                fixture_id=requested_fixture_id,
                recovery_hint=(
                    "Call navigate_to_receptacle for this fixture before open_receptacle. "
                    "Fridge-like cleanup must be nav -> open -> place_inside -> close."
                ),
            )
        opened = self.contract.open_receptacle(internal_fixture_id)
        if opened.get("ok"):
            self._opened_receptacle_for_handle = (self._held_handle, internal_fixture_id)
        return self._public_fixture_response(
            "open_receptacle",
            self._public_fixture_response_id(internal_fixture_id, requested_fixture_id),
            opened,
        )

    def place(self, fixture_id: str) -> dict[str, Any]:
        return self._place(fixture_id, inside=False)

    def place_inside(self, fixture_id: str) -> dict[str, Any]:
        return self._place(fixture_id, inside=True)

    def close_receptacle(self, fixture_id: str) -> dict[str, Any]:
        requested_fixture_id = str(fixture_id)
        internal_fixture_id = self._internal_fixture_id_for_public_anchor(requested_fixture_id)
        if internal_fixture_id not in self._fixtures:
            return self._error(
                "close_receptacle", "stale_reference", fixture_id=requested_fixture_id
            )
        pending = self._pending_close_receptacle_for_handle
        if pending is None or pending[1] != internal_fixture_id:
            return self._semantic_order_error(
                "close_receptacle",
                required_tool="place_inside",
                object_id=pending[0] if pending is not None else None,
                fixture_id=requested_fixture_id,
                recovery_hint=(
                    "Call close_receptacle only after place_inside for the same fridge-like "
                    "fixture."
                ),
            )
        handle, _ = pending
        closed = self.contract.close_receptacle(internal_fixture_id)
        public_fixture_id = self._public_fixture_response_id(
            internal_fixture_id,
            requested_fixture_id,
        )
        if closed.get("ok"):
            self._pending_close_receptacle_for_handle = None
            self._set_handle_state(
                handle,
                "placed_closed",
                tool="close_receptacle",
                fixture_id=public_fixture_id,
            )
        return self._public_fixture_response(
            "close_receptacle",
            public_fixture_id,
            closed,
            object_id=handle,
        )

    def done(
        self,
        reason: str = "",
        *,
        semantic_cleanup_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        readiness = self.evaluate_done_readiness(
            semantic_cleanup_evidence=semantic_cleanup_evidence,
        )
        if readiness["status"] == "blocked":
            return self._done_readiness_blocked_response(readiness)
        done = self.contract.done(reason=reason)
        if not done.get("ok"):
            return done
        score = annotate_score_with_semantic_acceptability(done["score"], self.scenario)
        final_locations = dict(done["final_locations"])
        metrics = self._realworld_metrics(score, final_locations)
        score.update(metrics)
        return self._ok(
            "done",
            reason=reason,
            cleanup_status=metrics["completion_status"],
            score=score,
            final_locations=final_locations,
            final_containment=done.get("final_containment", {}),
            tool_event_counts=done.get("tool_event_counts", {}),
            contract=REALWORLD_CONTRACT,
            policy_uses_private_truth=False,
        )

    def evaluate_done_readiness(
        self,
        *,
        semantic_cleanup_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        blockers: list[dict[str, Any]] = []
        open_ended_task = self._open_ended_task_intent()
        pending = (
            self._held_cleanup_candidates()
            if open_ended_task
            else self._pending_cleanup_candidates()
        )
        if pending:
            required_tool = str(pending[0].get("required_tool") or "navigate_to_object")
            if any(str(item.get("state") or "") == "held" for item in pending):
                required_tool = "navigate_to_receptacle"
            if required_tool == "adjust_camera":
                recovery_hint = visual_scan_done_recovery_hint()
            else:
                recovery_hint = (
                    "Clean pending observed handles before done. For held objects, select a "
                    "public destination_options.candidate_fixture_id and call "
                    "navigate_to_receptacle -> open? -> place/place_inside. For pending "
                    "objects, call navigate_to_object -> pick first. Use "
                    "destination_options.recommended_tool when candidate_fixture_id is empty."
                )
            blockers.append(
                {
                    "type": "pending_cleanup_candidates",
                    "required_tool": required_tool,
                    "pending_observed_handles": [str(item["object_id"]) for item in pending],
                    "pending_cleanup_candidates": pending,
                    "recovery_hint": recovery_hint,
                }
            )

        coverage = self._sweep_coverage()
        if not open_ended_task and coverage["unvisited_waypoint_ids"]:
            next_waypoint_id = coverage["unvisited_waypoint_ids"][0]
            blockers.append(
                {
                    "type": "insufficient_sweep_coverage",
                    "required_tool": "navigate_to_waypoint",
                    "next_waypoint_id": next_waypoint_id,
                    "sweep_coverage_rate": coverage["sweep_coverage_rate"],
                    "observed_waypoint_count": coverage["observed_waypoint_count"],
                    "total_waypoints": coverage["total_waypoints"],
                    "unvisited_waypoint_ids": coverage["unvisited_waypoint_ids"],
                    "recovery_hint": (
                        "Continue the public sweep before done: call navigate_to_waypoint("
                        f"{next_waypoint_id}) and observe. Do not use done as a system "
                        "assessment while static-map inspection waypoints remain unvisited."
                    ),
                }
            )

        if self.perception_mode == RAW_FPV_ONLY_MODE:
            required_declaration_count = self._required_model_declared_observations()
            declaration_count = len(self._model_declared_observations)
            if declaration_count < required_declaration_count:
                blockers.append(
                    {
                        "type": "insufficient_model_declared_observations",
                        "required_tool": "navigate_to_visual_candidate",
                        "current": declaration_count,
                        "required": required_declaration_count,
                        "model_declared_observations": declaration_count,
                        "raw_fpv_observations": len(self._raw_fpv_observations),
                        "required_model_declared_observations": required_declaration_count,
                        "recovery_hint": (
                            "Continue sweeping public waypoints and use "
                            "navigate_to_visual_candidate for plausible cleanup objects "
                            "seen in raw FPV images before calling done."
                        ),
                    }
                )

        grounded_chain_blocker = self._grounded_cleanup_chain_blocker(semantic_cleanup_evidence)
        if grounded_chain_blocker is not None:
            blockers.append(grounded_chain_blocker)

        readiness = {
            "schema": DONE_READINESS_SCHEMA,
            "status": "blocked" if blockers else "ready",
            "blockers": blockers,
            "policy_uses_private_truth": False,
            "task_intent": self.task_intent,
            "task_intent_mode": self.task_intent_mode,
            "public_contract_note": (
                "Done readiness is evaluated from public Agent View state, public tool "
                "trace evidence, and public run acceptance configuration. It does not "
                "use private generated mess membership, hidden destinations, or scorer truth."
            ),
        }
        _assert_no_forbidden_agent_view_keys(readiness)
        return readiness

    def _done_readiness_blocked_response(self, readiness: dict[str, Any]) -> dict[str, Any]:
        blockers = [dict(item) for item in readiness.get("blockers") or []]
        first = blockers[0] if blockers else {"type": "done_readiness_blocked"}
        error_reason = str(first.get("type") or "done_readiness_blocked")
        payload = {
            key: value for key, value in first.items() if key not in {"type", "recovery_hint"}
        }
        if "recovery_hint" in first:
            payload["recovery_hint"] = first["recovery_hint"]
        payload["completion"] = {
            "schema": readiness.get("schema", DONE_READINESS_SCHEMA),
            "status": "blocked",
            "blockers": blockers,
            "policy_uses_private_truth": False,
        }
        return self._error("done", error_reason, status="blocked", **payload)

    def _required_model_declared_observations(self) -> int:
        if self._open_ended_task_intent():
            return 0
        configured = _positive_int(
            self.public_acceptance_config.get("required_model_declared_observations")
        )
        if configured is not None:
            return configured
        requested = _positive_int(self.public_acceptance_config.get("requested_run_size"))
        if requested is not None:
            return min(7, requested)
        return 0

    def _grounded_cleanup_chain_blocker(
        self,
        semantic_cleanup_evidence: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        required_count, policy_id = self._grounded_cleanup_chain_requirement()
        if required_count <= 0:
            return None
        evidence = semantic_cleanup_evidence or {}
        complete_handles = [
            str(item)
            for item in evidence.get("complete_semantic_substep_object_ids") or []
            if str(item)
        ]
        complete_count = _positive_int(evidence.get("complete_semantic_substep_objects"))
        if complete_count is None:
            complete_count = len(complete_handles)
        if complete_count >= required_count:
            return None
        required_tool = self._grounded_cleanup_chain_required_tool()
        blocker = {
            "type": "insufficient_grounded_cleanup_chains",
            "policy_id": policy_id,
            "current": complete_count,
            "required": required_count,
            "required_tool": required_tool,
            "complete_semantic_substep_objects": complete_count,
            "complete_semantic_substep_object_ids": complete_handles,
            "required_complete_semantic_substep_objects": required_count,
            "semantic_substep_count": _nonnegative_int(evidence.get("semantic_substep_count")),
            "recovery_hint": self._grounded_cleanup_chain_recovery_hint(required_tool),
        }
        _assert_no_forbidden_agent_view_keys(blocker)
        return blocker

    def _grounded_cleanup_chain_requirement(self) -> tuple[int, str]:
        if self._open_ended_task_intent():
            return 0, ""
        explicit_count = _positive_int(
            self.public_acceptance_config.get("required_grounded_cleanup_chains")
        )
        if explicit_count is not None:
            return explicit_count, str(
                self.public_acceptance_config.get("done_readiness_policy")
                or DONE_READINESS_POLICY_EXPLICIT
            )
        if self.perception_mode != RAW_FPV_ONLY_MODE:
            return 0, ""
        requested = _positive_int(self.public_acceptance_config.get("requested_run_size"))
        if requested is None:
            return 0, ""
        return _public_success_threshold(requested), DONE_READINESS_POLICY_RAW_FPV

    def _grounded_cleanup_chain_required_tool(self) -> str:
        if self.perception_mode == RAW_FPV_ONLY_MODE:
            return "navigate_to_visual_candidate"
        return "navigate_to_object"

    def _grounded_cleanup_chain_recovery_hint(self, required_tool: str) -> str:
        if required_tool == "navigate_to_visual_candidate":
            return (
                "Continue the cleanup loop before done. For each plausible object in a "
                "public observation, call navigate_to_visual_candidate when required; "
                "when it returns ok=true, call pick, navigate_to_receptacle with the "
                "public candidate fixture, then the recommended placement tool. Call "
                "done only after enough grounded cleanup chains have completed."
            )
        return (
            "Continue the cleanup loop before done. For each pending public observed "
            "handle, call navigate_to_object, pick, navigate_to_receptacle with a public "
            "candidate fixture, then the recommended placement tool. Call done only after "
            "enough grounded cleanup chains have completed."
        )

    def _sweep_coverage(self) -> dict[str, Any]:
        waypoints = self._public_waypoints
        total_waypoints = len(waypoints)
        unvisited = [
            str(item["waypoint_id"])
            for item in waypoints
            if str(item["waypoint_id"]) not in self._observed_waypoint_ids
        ]
        observed_count = total_waypoints - len(unvisited)
        rate = observed_count / total_waypoints if total_waypoints else 1.0
        return {
            "sweep_coverage_rate": round(rate, 6),
            "observed_waypoint_count": observed_count,
            "total_waypoints": total_waypoints,
            "unvisited_waypoint_ids": unvisited,
        }

    def _open_ended_task_intent(self) -> bool:
        return household_intent_is_open_ended(self.task_intent)

    def agent_view_payload(self) -> dict[str, Any]:
        observed_objects = [
            self._agent_visible_detection_payload(dict(self._detections_by_handle[handle]))
            for handle in sorted(self._detections_by_handle)
        ]
        metric_map = self.metric_map()
        fixture_hints = self.fixture_hints()
        cleanup_worklist = self.cleanup_worklist_payload(fixture_hints=fixture_hints)
        model_declared = self.model_declared_observations_payload()
        runtime_metric_map = dict(metric_map.get("runtime_metric_map") or {})
        if not runtime_metric_map:
            runtime_metric_map = self.runtime_metric_map_payload(
                metric_map=metric_map,
                fixture_hints=fixture_hints,
                cleanup_worklist=cleanup_worklist,
            )
        payload = {
            "contract": REALWORLD_CONTRACT,
            "perception_mode": self.perception_mode,
            "detection_exposure_policy": self.visible_detection_exposure_policy,
            "structured_detections_available": self.perception_mode
            == VISIBLE_OBJECT_DETECTIONS_MODE,
            "metric_map": metric_map,
            "runtime_metric_map": runtime_metric_map,
            "fixture_hints": fixture_hints,
            "observed_objects": observed_objects,
            "raw_fpv_observations": [dict(item) for item in self._raw_fpv_observations],
            "camera_model_policy_evidence": self.camera_model_policy_payload(),
            "model_declared_observations": model_declared["observations"],
            "model_declared_observation_evidence": model_declared,
            "policy_view": self.policy_view_payload(),
            "cleanup_worklist": cleanup_worklist,
            "observed_waypoint_ids": sorted(self._observed_waypoint_ids),
            "public_tool_names": self.public_tool_names(),
            "forbidden_private_fields_absent": True,
        }
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

    def runtime_metric_map_payload(
        self,
        *,
        metric_map: dict[str, Any] | None = None,
        fixture_hints: dict[str, Any] | None = None,
        cleanup_worklist: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return realworld_contract_payloads.runtime_metric_map_payload(
            self,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
            cleanup_worklist=cleanup_worklist,
            realworld_contract=REALWORLD_CONTRACT,
            runtime_metric_map_schema=RUNTIME_METRIC_MAP_SCHEMA,
            cleanup_worklist_schema=CLEANUP_WORKLIST_SCHEMA,
            minimal_map_mode=MINIMAL_MAP_MODE,
            runtime_map_producer_summary=_runtime_map_producer_summary,
            merge_public_rooms=_merge_public_rooms,
            room_category_hints_from_public_rooms=_room_category_hints_from_public_rooms,
            assert_no_forbidden_agent_view_keys=_assert_no_forbidden_agent_view_keys,
        )

    def _runtime_target_candidates(
        self,
        *,
        public_semantic_anchors: list[dict[str, Any]],
        observed_objects: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()

        for waypoint in self._public_navigation_waypoints():
            candidate = self._target_candidate_from_waypoint(waypoint)
            candidate_id = str(candidate.get("candidate_id") or "")
            if candidate_id and candidate_id not in seen:
                candidates.append(candidate)
                seen.add(candidate_id)

        for anchor in public_semantic_anchors:
            candidate = self._target_candidate_from_anchor(anchor)
            candidate_id = str(candidate.get("candidate_id") or "")
            if candidate_id and candidate_id not in seen:
                candidates.append(candidate)
                seen.add(candidate_id)

        for observed in observed_objects:
            candidate = self._target_candidate_from_observed_object(observed)
            candidate_id = str(candidate.get("candidate_id") or "")
            if candidate_id and candidate_id not in seen:
                candidates.append(candidate)
                seen.add(candidate_id)

        for candidate in candidates:
            _assert_no_forbidden_agent_view_keys(candidate)
        return candidates

    def _target_candidate_from_waypoint(self, waypoint: dict[str, Any]) -> dict[str, Any]:
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        visited = waypoint_id in self._observed_waypoint_ids
        actionability = (
            TARGET_ACTIONABILITY_ACTIONABLE if visited else TARGET_ACTIONABILITY_NEEDS_OBSERVE
        )
        candidate = {
            "candidate_id": f"target_candidate_waypoint_{_safe_anchor_id(waypoint_id)}",
            "candidate_type": _target_candidate_type_for_waypoint(waypoint),
            "query": str(waypoint.get("label") or waypoint_id),
            "label": str(waypoint.get("label") or waypoint_id),
            "category": "inspection_area",
            "room_id": str(waypoint.get("room_id") or ""),
            "room_label": str(waypoint.get("room_label") or ""),
            "aliases": [str(item) for item in waypoint.get("aliases") or []],
            "evidence_lane": self._target_candidate_evidence_lane(),
            "producer_type": str(
                (waypoint.get("candidate_provenance") or {}).get("source")
                or waypoint.get("waypoint_source")
                or "public_metric_map"
            ),
            "producer_id": str(waypoint.get("waypoint_source") or "public_metric_map"),
            "source_observation_id": self._observation_id_for_waypoint(waypoint_id)
            if visited
            else "",
            "waypoint_id": waypoint_id,
            "pose": self._waypoint_pose(waypoint),
            "waypoint_source": str(waypoint.get("waypoint_source") or ""),
            "verified_navigation": True,
            "actionability": actionability,
            "target_actionability_status": actionability,
            "confidence": 1.0 if visited else 0.72,
            "rank": int((waypoint.get("candidate_provenance") or {}).get("candidate_index") or 0),
            "visited": visited,
            "inspection_budget": self._candidate_inspection_budget(waypoint_id),
            "rejection_reason": "" if visited else "needs_observe_from_public_waypoint",
            "provenance": dict(waypoint.get("candidate_provenance") or {}),
        }
        if waypoint.get("source_target_candidate_id"):
            candidate["source_target_candidate_id"] = str(waypoint["source_target_candidate_id"])
        if waypoint.get("source_observation_id"):
            candidate["source_observation_id"] = str(
                candidate.get("source_observation_id") or waypoint.get("source_observation_id")
            )
        _assert_no_forbidden_agent_view_keys(candidate)
        return candidate

    def _target_candidate_from_anchor(self, anchor: dict[str, Any]) -> dict[str, Any]:
        anchor_id = str(anchor.get("anchor_id") or "")
        waypoint_id = str(anchor.get("waypoint_id") or "")
        verified_navigation = bool(waypoint_id and self._waypoint_by_id(waypoint_id) is not None)
        actionability = (
            TARGET_ACTIONABILITY_ACTIONABLE
            if verified_navigation
            else TARGET_ACTIONABILITY_ANCHOR_UNBOUND
        )
        candidate = {
            "candidate_id": f"target_candidate_anchor_{_safe_anchor_id(anchor_id)}",
            "candidate_type": "public_semantic_anchor",
            "query": str(anchor.get("label") or anchor.get("category") or anchor_id),
            "label": str(anchor.get("label") or anchor_id),
            "category": str(anchor.get("category") or ""),
            "anchor_id": anchor_id,
            "anchor_type": str(anchor.get("anchor_type") or ""),
            "room_id": str(anchor.get("room_id") or ""),
            "room_label": str(anchor.get("room_label") or ""),
            "aliases": [str(item) for item in anchor.get("aliases") or []],
            "evidence_lane": self._target_candidate_evidence_lane(),
            "producer_type": str(anchor.get("producer_type") or ""),
            "producer_id": str(anchor.get("producer_id") or ""),
            "source_observation_id": str(anchor.get("source_observation_id") or ""),
            "waypoint_id": waypoint_id,
            "pose": dict(anchor.get("pose") or {}),
            "verified_navigation": verified_navigation,
            "affordances": list(anchor.get("affordances") or []),
            "actionability": actionability,
            "target_actionability_status": actionability,
            "confidence": _float_or_zero(anchor.get("confidence")),
            "rank": 0,
            "visited": waypoint_id in self._observed_waypoint_ids,
            "inspection_budget": self._candidate_inspection_budget(waypoint_id),
            "rejection_reason": "" if verified_navigation else "anchor_missing_verified_waypoint",
        }
        _assert_no_forbidden_agent_view_keys(candidate)
        return candidate

    def _target_candidate_from_observed_object(self, observed: dict[str, Any]) -> dict[str, Any]:
        object_id = str(observed.get("object_id") or "")
        source_status = str(
            observed.get("actionability_status") or observed.get("actionability") or ""
        )
        candidate_state = str(observed.get("candidate_state") or "")
        if source_status == "actionable" or observed.get("actionability") == "actionable":
            actionability = TARGET_ACTIONABILITY_ACTIONABLE
            rejection_reason = ""
        elif candidate_state == CANDIDATE_STATE_VISUAL_SCAN_REQUIRED:
            actionability = TARGET_ACTIONABILITY_VISIBLE_ONLY
            rejection_reason = "visual_evidence_not_reviewable"
        elif source_status in {"needs_clarification", "needs_confirm"}:
            actionability = TARGET_ACTIONABILITY_VISIBLE_ONLY
            rejection_reason = source_status
        elif observed.get("freshness") == "prior":
            actionability = TARGET_ACTIONABILITY_NEEDS_OBSERVE
            rejection_reason = "prior_requires_current_observation"
        else:
            actionability = TARGET_ACTIONABILITY_NEEDS_OBSERVE
            rejection_reason = source_status or "needs_fresh_observation"
        candidate = {
            "candidate_id": f"target_candidate_object_{_safe_anchor_id(object_id)}",
            "candidate_type": "observed_object",
            "query": str(observed.get("category") or object_id),
            "label": str(observed.get("category") or object_id),
            "category": str(observed.get("category") or ""),
            "object_id": object_id,
            "evidence_lane": self._target_candidate_evidence_lane(),
            "producer_type": str(observed.get("producer_type") or ""),
            "producer_id": str(observed.get("producer_id") or ""),
            "source_observation_id": str(observed.get("source_observation_id") or ""),
            "waypoint_id": str(observed.get("waypoint_id") or ""),
            "source_fixture_id": str(observed.get("source_fixture_id") or ""),
            "candidate_fixture_id": str(observed.get("candidate_fixture_id") or ""),
            "visual_grounding_evidence": dict(observed.get("visual_grounding_evidence") or {}),
            "verified_navigation": actionability == TARGET_ACTIONABILITY_ACTIONABLE,
            "actionability": actionability,
            "target_actionability_status": actionability,
            "source_actionability_status": source_status,
            "candidate_state": candidate_state,
            "confidence": _float_or_zero(observed.get("confidence")),
            "rank": 0,
            "visited": bool(observed.get("source_observation_id")),
            "inspection_budget": self._candidate_inspection_budget(
                str(observed.get("waypoint_id") or "")
            ),
            "rejection_reason": rejection_reason,
        }
        generated = self._generated_inspection_waypoint_for_object(object_id)
        if generated:
            candidate["generated_inspection_waypoint_id"] = str(generated.get("waypoint_id") or "")
            candidate["generated_inspection_candidate"] = {
                key: generated[key]
                for key in (
                    "waypoint_id",
                    "label",
                    "waypoint_source",
                    "source_observation_id",
                    "verified_navigation",
                )
                if key in generated
            }
        _assert_no_forbidden_agent_view_keys(candidate)
        return candidate

    def _target_search_summary(self, target_candidates: list[dict[str, Any]]) -> dict[str, Any]:
        actionability_counts: dict[str, int] = {}
        for candidate in target_candidates:
            actionability = str(candidate.get("target_actionability_status") or "")
            actionability_counts[actionability] = actionability_counts.get(actionability, 0) + 1
        visited_waypoints = sorted(self._observed_waypoint_ids)
        summary = {
            "schema": TARGET_SEARCH_SUMMARY_SCHEMA,
            "candidate_count": len(target_candidates),
            "actionability_counts": actionability_counts,
            "viewpoint_budget": {
                "total_public_waypoints": len(self._public_navigation_waypoints()),
                "visited_waypoint_count": len(visited_waypoints),
                "unvisited_waypoint_count": max(
                    len(self._public_navigation_waypoints()) - len(visited_waypoints),
                    0,
                ),
                "observed_waypoint_ids": visited_waypoints,
                "unvisited_waypoint_ids": [
                    str(item.get("waypoint_id") or "")
                    for item in self._public_navigation_waypoints()
                    if str(item.get("waypoint_id") or "") not in self._observed_waypoint_ids
                ],
            },
            "camera_adjustment_budget": {
                "max_yaw_delta_deg": 45,
                "max_pitch_delta_deg": 20,
                "recommended_attempts_per_waypoint": 1,
                "attempt_count": len(self._camera_adjustment_events),
                "attempts": [dict(item) for item in self._camera_adjustment_events],
            },
            "inspection_observations": [dict(item) for item in self._inspection_observations],
            "missing_target_policy": (
                "A missing target claim must be based on inspected public waypoints, "
                "recorded camera-adjustment attempts when needed, and exhausted public "
                "candidate budget rather than private inventory."
            ),
            "private_truth_included": False,
        }
        _assert_no_forbidden_agent_view_keys(summary)
        return summary

    def _target_query_recovery_summary(
        self,
        target_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        runtime_map = {
            "target_candidates": target_candidates,
            "target_search_summary": self._target_search_summary(target_candidates),
        }
        summary = {
            "schema": "target_query_recovery_summary_v1",
            "source": "runtime_metric_map_target_candidates",
            "status": "available",
            "supported_operations": [
                "inspect",
                "map-build",
                "destination",
                "place",
                "navigate",
                "open-ended",
            ],
            "recovery_policy": (
                "Resolve stale labels, raw fixture ids, and open-ended target names "
                "through public target_candidates. Navigation may use only returned "
                "public waypoint ids, anchor ids, observed object handles, or "
                "candidate_fixture_id fields; not-found claims must include the "
                "public_search_budget from a resolution."
            ),
            "example_queries": [
                resolve_target_query(runtime_map, query, operation="destination")
                for query in self._target_query_recovery_examples(target_candidates)
            ],
            "private_truth_included": False,
        }
        _assert_no_forbidden_agent_view_keys(summary)
        return summary

    @staticmethod
    def _target_query_recovery_examples(
        target_candidates: list[dict[str, Any]],
    ) -> list[str]:
        examples: list[str] = []
        for candidate in target_candidates:
            for key in ("label", "category", "waypoint_id", "anchor_id", "object_id"):
                value = str(candidate.get(key) or "").strip()
                if value and value not in examples:
                    examples.append(value)
                if len(examples) >= 3:
                    return examples
        return examples

    def _candidate_inspection_budget(self, waypoint_id: str) -> dict[str, Any]:
        observations = [
            item
            for item in self._inspection_observations
            if str(item.get("waypoint_id") or "") == waypoint_id
        ]
        adjustments = [
            item
            for item in self._camera_adjustment_events
            if str(item.get("waypoint_id") or "") == waypoint_id
        ]
        return {
            "schema": "target_candidate_inspection_budget_v1",
            "observed": bool(observations),
            "observation_count": len(observations),
            "camera_adjustment_attempt_count": len(adjustments),
            "max_camera_adjustment_attempts": 1,
        }

    def _target_candidate_evidence_lane(self) -> str:
        if self.sanitize_world_labels:
            return "world-public-labels"
        if self.perception_mode == RAW_FPV_ONLY_MODE:
            return "camera-raw-fpv"
        if self.perception_mode == CAMERA_MODEL_POLICY_MODE:
            return "camera-grounded-labels"
        return "world-oracle-labels"

    def _runtime_public_semantic_anchors(self) -> list[dict[str, Any]]:
        """Build run-local anchors for fixed places discovered through public evidence."""

        anchors: list[dict[str, Any]] = []
        seen: set[str] = set()

        if self.map_mode == MINIMAL_MAP_MODE:
            for waypoint in self._public_waypoints:
                waypoint_id = str(waypoint.get("waypoint_id") or "")
                if waypoint_id not in self._observed_waypoint_ids:
                    continue
                for anchor in (
                    self._room_area_public_semantic_anchor(waypoint),
                    self._waypoint_public_semantic_anchor(waypoint),
                ):
                    anchor_id = str(anchor.get("anchor_id") or "")
                    if anchor_id and anchor_id not in seen:
                        anchors.append(anchor)
                        seen.add(anchor_id)

        for fixture_id, anchor_id in sorted(
            self._public_anchor_ids_by_private_fixture_id.items(),
            key=lambda item: item[1],
        ):
            anchor = self._fixture_public_semantic_anchor(fixture_id, anchor_id)
            if not anchor:
                continue
            if anchor_id in seen:
                continue
            anchors.append(anchor)
            seen.add(anchor_id)

        for prior_anchor in self._runtime_map_anchor_priors:
            anchor_id = str(prior_anchor.get("anchor_id") or "")
            if anchor_id and anchor_id in seen:
                continue
            anchors.append(dict(prior_anchor))
            if anchor_id:
                seen.add(anchor_id)

        for anchor in anchors:
            _assert_no_forbidden_agent_view_keys(anchor)
        return anchors

    def _room_area_public_semantic_anchor(self, waypoint: dict[str, Any]) -> dict[str, Any]:
        room_id = str(waypoint.get("room_id") or "generated_area")
        room_label = str(waypoint.get("room_label") or room_id.replace("_", " ").title())
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        observation_id = self._observation_id_for_waypoint(waypoint_id)
        anchor = {
            "anchor_id": f"anchor_room_{_safe_anchor_id(room_id)}",
            "anchor_type": "room_area",
            "category": _room_category_from_label(room_label, room_id),
            "label": room_label,
            "room_id": room_id,
            "room_label": room_label,
            "waypoint_id": waypoint_id,
            "pose": self._waypoint_pose(waypoint),
            "affordances": ["navigate", "observe"],
            "aliases": [room_id, room_label],
            "producer_type": "generated_exploration_candidate",
            "producer_id": "minimal_map_exploration",
            "confidence": 0.8 if room_label else 0.6,
            "freshness": "current_run",
            "actionability": "actionable",
            "source_observation_id": observation_id,
            "promotion_status": "run_local",
            "evidence": {
                "type": "visited_generated_area",
                "visited": True,
                "candidate_provenance": dict(waypoint.get("candidate_provenance") or {}),
            },
        }
        _assert_no_forbidden_agent_view_keys(anchor)
        return anchor

    def _waypoint_public_semantic_anchor(self, waypoint: dict[str, Any]) -> dict[str, Any]:
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        observation_id = self._observation_id_for_waypoint(waypoint_id)
        anchor = {
            "anchor_id": f"anchor_waypoint_{_safe_anchor_id(waypoint_id)}",
            "anchor_type": "observation_waypoint",
            "category": "observation_waypoint",
            "label": str(waypoint.get("label") or waypoint_id),
            "room_id": str(waypoint.get("room_id") or ""),
            "room_label": str(waypoint.get("room_label") or ""),
            "waypoint_id": waypoint_id,
            "pose": self._waypoint_pose(waypoint),
            "affordances": ["observe"],
            "producer_type": "generated_exploration_candidate",
            "producer_id": "minimal_map_exploration",
            "confidence": 1.0,
            "freshness": "current_run",
            "actionability": "actionable",
            "source_observation_id": observation_id,
            "promotion_status": "run_local",
            "evidence": {
                "type": "visited_generated_exploration_candidate",
                "visited": True,
                "candidate_provenance": dict(waypoint.get("candidate_provenance") or {}),
            },
        }
        _assert_no_forbidden_agent_view_keys(anchor)
        return anchor

    def _fixture_public_semantic_anchor(
        self,
        fixture_id: str,
        anchor_id: str,
    ) -> dict[str, Any]:
        fixture = self._fixtures.get(fixture_id)
        if fixture is None:
            return {}
        supporting = self._supporting_detections_for_fixture(fixture_id)
        best_detection = supporting[0] if supporting else {}
        best_lifecycle = self._object_lifecycle.get(str(best_detection.get("object_id") or ""), {})
        waypoint_id = str(best_lifecycle.get("waypoint_id") or self._current_waypoint_id)
        waypoint = self._waypoint_by_id(waypoint_id) or {}
        source_observation_id = str(
            best_detection.get("source_observation_id")
            or best_lifecycle.get("source_observation_id")
            or self._observation_id_for_waypoint(waypoint_id)
        )
        confidence_values = [
            _float_or_zero(item.get("visibility_confidence"))
            or _float_or_zero((item.get("support_estimate") or {}).get("confidence"))
            for item in supporting
        ]
        confidence = max(confidence_values) if confidence_values else 0.68
        anchor = {
            "anchor_id": anchor_id,
            "anchor_type": _semantic_anchor_type_for_fixture(fixture),
            "category": str(fixture.get("category") or fixture.get("name") or "fixture"),
            "label": str(fixture.get("category") or fixture.get("name") or "Observed fixture"),
            "room_id": str((waypoint or {}).get("room_id") or best_lifecycle.get("room_id") or ""),
            "waypoint_id": waypoint_id,
            "pose": self._waypoint_pose(waypoint),
            "affordances": _anchor_affordances_for_fixture(fixture),
            "producer_type": str(
                best_detection.get("producer_type")
                or best_detection.get("perception_source")
                or "visible_detection"
            ),
            "producer_id": str(
                best_detection.get("producer_id")
                or best_detection.get("model_provenance")
                or best_detection.get("producer_type")
                or "visible_detection"
            ),
            "confidence": round(float(confidence), 6),
            "freshness": "current_run",
            "actionability": "actionable",
            "source_observation_id": source_observation_id,
            "promotion_status": "run_local",
            "evidence": {
                "type": "support_estimate",
                "relation": str(
                    (best_detection.get("support_estimate") or {}).get("relation") or ""
                ),
                "supporting_observed_object_ids": [
                    str(item.get("object_id") or "") for item in supporting
                ],
                "image_region": (
                    best_detection.get("image_region")
                    or {"type": "bbox", "value": best_detection.get("image_bbox") or []}
                ),
            },
        }
        _assert_no_forbidden_agent_view_keys(anchor)
        return anchor

    def _supporting_detections_for_fixture(self, fixture_id: str) -> list[dict[str, Any]]:
        supporting = []
        for handle in sorted(self._detections_by_handle):
            detection = self._detections_by_handle[handle]
            support = detection.get("support_estimate") or {}
            if str(support.get("fixture_id") or "") != fixture_id:
                continue
            supporting.append(dict(detection))
        return supporting

    def _observation_id_for_waypoint(self, waypoint_id: str) -> str:
        for item in self._raw_fpv_observations:
            if str(item.get("waypoint_id") or "") == waypoint_id:
                return str(item.get("observation_id") or "")
        return f"waypoint_observation:{waypoint_id}"

    def _agent_visible_detection_payload(self, detection: dict[str, Any]) -> dict[str, Any]:
        if self.map_mode != MINIMAL_MAP_MODE:
            payload = copy.deepcopy(detection)
            if self.sanitize_world_labels:
                payload = self._sanitized_visible_detection_payload(payload)
            _assert_no_forbidden_agent_view_keys(payload)
            return payload
        payload = self._public_fixture_reference_payload(copy.deepcopy(detection))
        support = dict(payload.get("support_estimate") or {})
        public_fixture_id = str(support.get("fixture_id") or "")
        if public_fixture_id:
            support["source_fixture_hidden"] = True
            support["source"] = "public_semantic_anchor"
            payload["support_estimate"] = support
        if self.sanitize_world_labels:
            payload = self._sanitized_visible_detection_payload(payload)
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

    def _sanitized_visible_detection_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = copy.deepcopy(payload)
        for key in (
            "candidate_fixture_id",
            "candidate_fixture_category",
            "cleanup_recommended",
            "recommended_tool",
        ):
            payload.pop(key, None)
        payload["producer_type"] = SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
        payload["producer_id"] = SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
        payload["perception_source"] = SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
        payload["detection_exposure_policy"] = SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY
        payload["destination_policy_status"] = "policy_required"
        payload["destination_policy"] = _public_destination_policy_for_category(
            payload.get("category")
        )
        support = dict(payload.get("support_estimate") or {})
        if support:
            support["source"] = "public_support_evidence"
            support["perception_source"] = SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
            support["model_provenance"] = SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
            payload["support_estimate"] = support
        return payload

    def _seed_public_fixture_anchor_ids_from_prior_anchors(self) -> None:
        if self.map_mode != MINIMAL_MAP_MODE:
            return
        for anchor in self._runtime_map_anchor_priors:
            anchor_id = str(anchor.get("anchor_id") or "")
            if not _is_place_anchor(anchor) or not anchor_id:
                continue
            fixture_id = self._best_internal_fixture_for_anchor(anchor)
            if fixture_id:
                self._public_anchor_ids_by_private_fixture_id.setdefault(fixture_id, anchor_id)

    def _seed_public_fixture_anchor_ids_for_waypoint(self, waypoint: dict[str, Any]) -> None:
        if self.map_mode != MINIMAL_MAP_MODE:
            return
        private_waypoint = self._private_waypoint_for_public_waypoint(waypoint)
        for fixture_id in private_waypoint.get("fixture_ids") or []:
            fixture_id = str(fixture_id or "")
            if fixture_id and fixture_id in self._fixtures:
                self._public_anchor_id_for_fixture(fixture_id)

    def _public_runtime_fixture_candidates(self) -> list[dict[str, Any]]:
        if self.map_mode != MINIMAL_MAP_MODE:
            return []
        candidates = []
        for anchor in self._runtime_public_semantic_anchors():
            if not _is_place_anchor(anchor):
                continue
            anchor_id = str(anchor.get("anchor_id") or "")
            if not anchor_id:
                continue
            fixture_id = self._internal_fixture_id_for_public_anchor(anchor_id)
            fixture = self._fixtures.get(fixture_id) if fixture_id else {}
            category = str(anchor.get("category") or (fixture or {}).get("category") or "")
            name = str(anchor.get("label") or (fixture or {}).get("name") or category or anchor_id)
            waypoint_id = str(
                anchor.get("waypoint_id")
                or (
                    self._public_waypoint_for_private_fixture(fixture_id).get("waypoint_id")
                    if fixture_id
                    else ""
                )
                or self._current_waypoint_id
            )
            waypoint = self._waypoint_by_id(waypoint_id) or {}
            pose = dict(anchor.get("pose") or self._waypoint_pose(waypoint))
            item = {
                "fixture_id": anchor_id,
                "receptacle_id": anchor_id,
                "category": category,
                "name": name,
                "room_id": str(anchor.get("room_id") or waypoint.get("room_id") or ""),
                "affordances": list(anchor.get("affordances") or []),
                "pose": {"frame_id": "map", **pose},
                "preferred_inspection_waypoint_id": waypoint_id,
                "preferred_manipulation_waypoint_id": waypoint_id,
                "public_fixture_source": "runtime_semantic_anchor",
            }
            _assert_no_forbidden_agent_view_keys(item)
            candidates.append(item)
        return candidates

    def _minimal_target_fixture_for_detection(
        self,
        detection: dict[str, Any],
    ) -> dict[str, Any] | None:
        public_runtime_fixtures = self._public_runtime_fixture_candidates()
        public_hints = {
            "rooms": [
                {
                    "room_id": "runtime_semantic_anchors",
                    "room_label": "Runtime semantic anchors",
                    "fixtures": public_runtime_fixtures,
                }
            ]
        }
        inferred = infer_target_fixture_for_detection(detection, public_hints)
        if inferred is not None:
            return inferred
        requested = self.internal_fixture_id_for_public_reference(
            str((detection.get("support_estimate") or {}).get("fixture_id") or "")
        )
        if not requested:
            return None
        for fixture in public_runtime_fixtures:
            if (
                self.internal_fixture_id_for_public_reference(str(fixture.get("fixture_id") or ""))
                == requested
            ):
                return fixture
        return None

    def _resolve_runtime_anchor_target_fixture_id(self, category: str) -> str:
        if self.map_mode != MINIMAL_MAP_MODE:
            return ""
        pseudo_detection = {
            "category": category,
            "name": category,
            "support_estimate": {"fixture_id": ""},
        }
        target = self._minimal_target_fixture_for_detection(pseudo_detection)
        return str((target or {}).get("fixture_id") or "")

    def _public_fixture_reference_payload(self, value: Any) -> Any:
        if self.map_mode != MINIMAL_MAP_MODE:
            return value
        fixture_keys = {
            "fixture_id",
            "receptacle_id",
            "source_fixture_id",
            "target_fixture_id",
            "candidate_fixture_id",
            "expected_fixture_id",
            "requested_source_fixture_id",
            "source_receptacle_id",
            "previous_receptacle_id",
        }
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key in fixture_keys and isinstance(item, str):
                    result[key] = self._public_fixture_reference_id(item)
                elif key == "fixture_ids" and isinstance(item, list):
                    result[key] = [
                        self._public_fixture_reference_id(str(raw_item)) for raw_item in item
                    ]
                else:
                    result[key] = self._public_fixture_reference_payload(item)
            return result
        if isinstance(value, list):
            return [self._public_fixture_reference_payload(item) for item in value]
        return value

    def _public_fixture_reference_id(self, fixture_id: str) -> str:
        if not fixture_id or self.map_mode != MINIMAL_MAP_MODE:
            return fixture_id
        if fixture_id.startswith("anchor_"):
            return fixture_id
        return self._public_anchor_id_for_fixture(fixture_id)

    def _public_anchor_id_for_fixture(self, fixture_id: str) -> str:
        fixture_id = str(fixture_id or "")
        if not fixture_id:
            return ""
        anchor_id = self._public_anchor_ids_by_private_fixture_id.get(fixture_id)
        if anchor_id:
            return anchor_id
        anchor_id = f"anchor_fixture_{len(self._public_anchor_ids_by_private_fixture_id) + 1:03d}"
        self._public_anchor_ids_by_private_fixture_id[fixture_id] = anchor_id
        return anchor_id

    def _best_internal_fixture_for_anchor(self, anchor: dict[str, Any]) -> str:
        category = str(anchor.get("category") or "")
        waypoint_id = str(anchor.get("waypoint_id") or "")
        public_waypoint = self._waypoint_by_id(waypoint_id) or {}
        private_waypoint = self._private_waypoint_for_public_waypoint(public_waypoint)
        fixture_ids = [str(item) for item in private_waypoint.get("fixture_ids") or []]
        for fixture_id in fixture_ids:
            fixture = self._fixtures.get(fixture_id, {})
            if _norm(category) and _norm(category) in _norm(
                " ".join(str(fixture.get(key, "")) for key in ("fixture_id", "category", "name"))
            ):
                return fixture_id
        for fixture_id, public_anchor_id in self._public_anchor_ids_by_private_fixture_id.items():
            if public_anchor_id == str(anchor.get("anchor_id") or ""):
                return fixture_id
        for fixture_id, fixture in self._fixtures.items():
            if _norm(category) and _norm(category) in _norm(
                " ".join(str(fixture.get(key, "")) for key in ("fixture_id", "category", "name"))
            ):
                return fixture_id
        return ""

    def _internal_fixture_id_for_public_anchor(self, anchor_id: str) -> str:
        if not anchor_id:
            return ""
        if self.map_mode != MINIMAL_MAP_MODE:
            return anchor_id
        for fixture_id, public_anchor_id in self._public_anchor_ids_by_private_fixture_id.items():
            if public_anchor_id == anchor_id:
                return fixture_id
        anchor = next(
            (
                item
                for item in self._runtime_public_semantic_anchors()
                if str(item.get("anchor_id") or "") == anchor_id
            ),
            {},
        )
        fixture_id = (
            self._best_internal_fixture_for_anchor(anchor) if _is_place_anchor(anchor) else ""
        )
        if fixture_id:
            self._public_anchor_ids_by_private_fixture_id.setdefault(fixture_id, anchor_id)
        return fixture_id

    def _public_waypoint_for_private_fixture(self, fixture_id: str) -> dict[str, Any]:
        private_waypoint_id = self._preferred_waypoint_for_fixture(fixture_id)
        private_waypoint = next(
            (
                item
                for item in self._waypoints
                if str(item.get("waypoint_id") or "") == private_waypoint_id
            ),
            {},
        )
        if self.map_mode != MINIMAL_MAP_MODE:
            return private_waypoint
        for public_id, mapped in self._private_waypoint_by_public_id.items():
            if str(mapped.get("waypoint_id") or "") == str(
                private_waypoint.get("waypoint_id") or ""
            ):
                return self._waypoint_by_id(public_id) or {}
        return self._waypoint_by_id(self._current_waypoint_id) or {}

    def _public_waypoint_id_for_private_fixture(self, fixture_id: str) -> str:
        if self.map_mode != MINIMAL_MAP_MODE:
            return self._preferred_waypoint_for_fixture(fixture_id)
        waypoint = self._public_waypoint_for_private_fixture(fixture_id)
        public_waypoint_id = str(waypoint.get("waypoint_id") or "")
        return public_waypoint_id or self._current_waypoint_id

    def _public_fixture_response_id(
        self,
        internal_fixture_id: str,
        requested_fixture_id: str,
    ) -> str:
        if self.map_mode != MINIMAL_MAP_MODE:
            return internal_fixture_id
        if requested_fixture_id.startswith("anchor_"):
            return requested_fixture_id
        return self._public_fixture_reference_id(internal_fixture_id)

    def policy_view_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "realworld_cleanup_policy_view_v1",
            "allowed_inputs": [
                "metric_map",
                "runtime_metric_map",
                "fixture_hints",
                "observed_objects",
                "raw_fpv_observations",
                "camera_model_policy_evidence",
                "model_declared_observations",
                "navigation_status",
            ],
            "excluded_report_only_views": [
                "chase_camera",
                "third_person_simulation_view",
                "private_evaluation",
            ],
            "chase_camera_policy_input": False,
            "public_contract_note": (
                "Policy inputs are robot-local or static-map data. Chase and "
                "third-person simulation views are report-only evidence."
            ),
        }
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

    def _runtime_static_map_payload(
        self,
        *,
        metric_map: dict[str, Any],
        fixture_hints: dict[str, Any],
    ) -> dict[str, Any]:
        fixtures = []
        for room in fixture_hints.get("rooms") or []:
            room_id = str(room.get("room_id") or "")
            for fixture in room.get("fixtures") or []:
                item = {
                    "fixture_id": str(fixture.get("fixture_id") or ""),
                    "category": str(fixture.get("category") or ""),
                    "name": str(fixture.get("name") or fixture.get("fixture_id") or ""),
                    "room_id": str(fixture.get("room_id") or room_id),
                    "affordances": list(fixture.get("affordances") or []),
                    "pose": dict(fixture.get("pose") or {}),
                    "preferred_inspection_waypoint_id": str(
                        fixture.get("preferred_inspection_waypoint_id") or ""
                    ),
                    "preferred_manipulation_waypoint_id": str(
                        fixture.get("preferred_manipulation_waypoint_id") or ""
                    ),
                }
                _assert_no_forbidden_agent_view_keys(item)
                fixtures.append(item)
        return {
            "rooms": [dict(item) for item in metric_map.get("rooms") or []],
            "fixtures": fixtures,
            "inspection_waypoints": [
                dict(item) for item in metric_map.get("inspection_waypoints") or []
            ],
            "driveable_ways": [dict(item) for item in metric_map.get("driveable_ways") or []],
            "map_bundle": dict(metric_map.get("map_bundle") or {}),
            "contains_runtime_observations": False,
            "map_mode": self.map_mode,
            "minimal_map_mode": self.map_mode == MINIMAL_MAP_MODE,
            "generated_exploration_candidates": [
                dict(item) for item in metric_map.get("generated_exploration_candidates") or []
            ],
        }

    def _runtime_observed_object_payload(
        self,
        handle: str,
        detection: dict[str, Any],
        worklist_item: dict[str, Any],
    ) -> dict[str, Any]:
        lifecycle = dict(self._object_lifecycle.get(handle, {}))
        support = detection.get("support_estimate") or {}
        declaration = detection.get("model_declared_observation") or {}
        source_observation_id = str(
            detection.get("source_observation_id")
            or declaration.get("source_observation_id")
            or lifecycle.get("source_observation_id")
            or _synthetic_observation_id(handle, lifecycle.get("waypoint_id", ""))
        )
        waypoint_id = str(
            worklist_item.get("last_waypoint_id")
            or declaration.get("waypoint_id")
            or lifecycle.get("waypoint_id")
            or ""
        )
        room_id = str(
            worklist_item.get("room_id")
            or declaration.get("room_id")
            or detection.get("current_room_id")
            or lifecycle.get("room_id")
            or ""
        )
        state = str(worklist_item.get("state") or lifecycle.get("state") or "pending")
        grounding_status = str(
            worklist_item.get("grounding_status")
            or detection.get("grounding_status")
            or declaration.get("grounding_status")
            or "resolved"
        )
        confidence = _runtime_observed_confidence(detection, declaration)
        image_region = (
            detection.get("image_region")
            or declaration.get("image_region")
            or {"type": "bbox", "value": detection.get("image_bbox") or []}
        )
        producer_type = str(
            detection.get("producer_type")
            or declaration.get("producer_type")
            or detection.get("model_provenance")
            or detection.get("perception_source")
            or "visible_object_detections"
        )
        producer_id = str(
            detection.get("producer_id")
            or declaration.get("producer_id")
            or detection.get("model_provenance")
            or producer_type
        )
        actionability = _runtime_actionability(
            state=state,
            grounding_status=grounding_status,
            cleanup_recommended=bool(worklist_item.get("cleanup_recommended"))
            and not self.sanitize_world_labels,
        )
        evidence = self._visual_evidence_for_handle(handle)
        candidate_actionability_status = _candidate_actionability_status(
            {
                **detection,
                "visual_grounding_evidence": evidence,
                "grounding_status": grounding_status,
            }
        )
        if actionability == "actionable" and candidate_actionability_status != "actionable":
            actionability = candidate_actionability_status
        candidate_fixture_id = ""
        candidate_source = "policy_required_destination_selection"
        producer_type = (
            SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
            if self.sanitize_world_labels and self.perception_mode == VISIBLE_OBJECT_DETECTIONS_MODE
            else producer_type
        )
        producer_id = (
            SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
            if self.sanitize_world_labels and self.perception_mode == VISIBLE_OBJECT_DETECTIONS_MODE
            else producer_id
        )
        if not self.sanitize_world_labels:
            candidate_fixture_id = str(
                self._public_fixture_reference_id(
                    str(worklist_item.get("candidate_fixture_id") or "")
                )
            )
            candidate_source = str(
                worklist_item.get("candidate_source")
                or detection.get("candidate_source")
                or "public_category_fixture_affordance"
            )
        payload = {
            "object_id": handle,
            "category": str(detection.get("category") or worklist_item.get("category") or ""),
            "room_id": room_id,
            "waypoint_id": waypoint_id,
            "source_fixture_id": str(
                self._public_fixture_reference_id(
                    str(worklist_item.get("source_fixture_id") or support.get("fixture_id") or "")
                )
            ),
            "source_observation_id": source_observation_id,
            "image_region": image_region,
            "visual_grounding_evidence": evidence,
            "producer_type": producer_type,
            "producer_id": producer_id,
            "confidence": confidence,
            "freshness": str(detection.get("freshness") or "current_run"),
            "actionability": actionability,
            "actionability_status": candidate_actionability_status,
            "candidate_state": _candidate_state(
                {
                    **detection,
                    "visual_grounding_evidence": evidence,
                    "grounding_status": grounding_status,
                }
            ),
            "state": state,
            "grounding_status": grounding_status,
            "candidate_fixture_id": candidate_fixture_id,
            "candidate_source": candidate_source,
        }
        if self.sanitize_world_labels:
            payload["destination_policy_status"] = "policy_required"
            payload["destination_policy"] = _public_destination_policy_for_category(
                payload.get("category")
            )
        if detection.get("prior_object_id"):
            payload["prior_object_id"] = str(detection["prior_object_id"])
        if detection.get("snapshot_object_id"):
            payload["snapshot_object_id"] = str(detection["snapshot_object_id"])
        prior = self._matching_runtime_map_prior(payload)
        if prior is not None:
            payload["prior_object_id"] = str(prior.get("prior_object_id") or "")
            payload["snapshot_object_id"] = str(prior.get("snapshot_object_id") or "")
            payload["prior_match_basis"] = "category_room_source_fixture"
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

    def _matching_runtime_map_prior(self, current: dict[str, Any]) -> dict[str, Any] | None:
        category = _norm(current.get("category"))
        room_id = str(current.get("room_id") or "")
        source_fixture_id = str(current.get("source_fixture_id") or "")
        for prior in self._runtime_map_priors:
            if _norm(prior.get("category")) != category:
                continue
            if str(prior.get("room_id") or "") != room_id:
                continue
            if str(prior.get("source_fixture_id") or "") != source_fixture_id:
                continue
            return prior
        return None

    def cleanup_worklist_payload(
        self,
        *,
        fixture_hints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return realworld_contract_payloads.cleanup_worklist_payload(
            self,
            fixture_hints=fixture_hints,
            cleanup_worklist_schema=CLEANUP_WORKLIST_SCHEMA,
            minimal_map_mode=MINIMAL_MAP_MODE,
            non_actionable_handle_states=_NON_ACTIONABLE_HANDLE_STATES,
            candidate_actionability_status=_candidate_actionability_status,
            candidate_state=_candidate_state,
            public_destination_policy_for_category=_public_destination_policy_for_category,
            recommended_place_tool=_recommended_place_tool,
            assert_no_forbidden_agent_view_keys=_assert_no_forbidden_agent_view_keys,
        )

    def _pending_cleanup_candidates(self) -> list[dict[str, Any]]:
        worklist = self.cleanup_worklist_payload(fixture_hints=self.fixture_hints())
        pending = []
        for item in worklist.get("objects", []):
            state = str(item.get("state") or "")
            if state not in {"pending", "held"}:
                continue
            if item.get("grounding_status") in {"ambiguous", "unresolved"}:
                continue
            if self.sanitize_world_labels:
                destination_options = self._destination_options_for_policy(
                    item.get("destination_policy") or {}
                )
                pending.append(
                    {
                        "object_id": str(item.get("object_id") or ""),
                        "category": str(item.get("category") or ""),
                        "state": state,
                        "source_fixture_id": str(item.get("source_fixture_id") or ""),
                        "candidate_fixture_id": "",
                        "candidate_state": str(item.get("candidate_state") or ""),
                        "destination_policy_status": str(
                            item.get("destination_policy_status") or "policy_required"
                        ),
                        "destination_policy": dict(item.get("destination_policy") or {}),
                        "destination_options": destination_options,
                        "required_tool": "navigate_to_receptacle"
                        if state == "held"
                        else _required_tool_for_candidate_state(
                            str(item.get("candidate_state") or "")
                        ),
                    }
                )
                continue
            candidate_fixture_id = str(item.get("candidate_fixture_id") or "")
            source_fixture_id = str(item.get("source_fixture_id") or "")
            if not candidate_fixture_id or candidate_fixture_id == source_fixture_id:
                continue
            internal_candidate_fixture_id = (
                self.internal_fixture_id_for_public_reference(candidate_fixture_id)
                or candidate_fixture_id
            )
            pending.append(
                {
                    "object_id": str(item.get("object_id") or ""),
                    "category": str(item.get("category") or ""),
                    "state": state,
                    "source_fixture_id": source_fixture_id,
                    "candidate_fixture_id": candidate_fixture_id,
                    "candidate_state": str(item.get("candidate_state") or ""),
                    "required_tool": "navigate_to_receptacle"
                    if state == "held"
                    else _required_tool_for_candidate_state(str(item.get("candidate_state") or "")),
                    "recommended_tool": _recommended_place_tool(
                        internal_candidate_fixture_id,
                        self._fixtures,
                    ),
                }
            )
        return pending

    def _held_cleanup_candidates(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self._pending_cleanup_candidates()
            if str(item.get("state") or "") == "held"
        ]

    def _destination_options_for_policy(self, policy: dict[str, Any]) -> list[dict[str, Any]]:
        preferred = [
            _normalize_fixture_category_label(item)
            for item in policy.get("preferred_fixture_categories") or []
        ]
        if not preferred:
            return []
        options = []
        for anchor in self._runtime_public_semantic_anchors():
            if not _is_place_anchor(anchor):
                continue
            category = _normalize_fixture_category_label(anchor.get("category"))
            if category not in preferred:
                continue
            anchor_id = str(anchor.get("anchor_id") or "")
            if not anchor_id:
                continue
            tool_by_category = dict(policy.get("placement_tool_by_fixture_category") or {})
            recommended_tool = str(
                tool_by_category.get(category)
                or policy.get("placement_tool")
                or _public_destination_policy_tool_for_fixture_category(category)
            )
            options.append(
                {
                    "candidate_fixture_id": anchor_id,
                    "candidate_fixture_category": category,
                    "recommended_tool": recommended_tool,
                    "candidate_source": "runtime_public_semantic_anchor",
                    "waypoint_id": str(anchor.get("waypoint_id") or ""),
                }
            )
        return options

    def camera_model_policy_payload(self) -> dict[str, Any]:
        events = [dict(item) for item in self._camera_model_policy_events]
        pipeline_ids = [
            str((item.get("visual_grounding_pipeline") or {}).get("pipeline_id") or "")
            for item in events
        ]
        pipeline_ids = [item for item in pipeline_ids if item]
        failure_count = sum(
            1
            for item in events
            if (item.get("visual_grounding_pipeline") or {}).get("status") == "failed"
        )
        model_provenance = (
            SIMULATED_CAMERA_MODEL_PROVENANCE
            if not pipeline_ids or set(pipeline_ids) == {SIM_VISUAL_GROUNDING_PIPELINE_ID}
            else EXTERNAL_VISUAL_GROUNDING_PROVENANCE
        )
        return {
            "schema": CAMERA_MODEL_POLICY_SCHEMA,
            "perception_mode": self.perception_mode,
            "enabled": self.perception_mode == CAMERA_MODEL_POLICY_MODE,
            "model_provenance": model_provenance
            if self.perception_mode == CAMERA_MODEL_POLICY_MODE
            else "",
            "visual_grounding_pipeline_id": pipeline_ids[-1]
            if pipeline_ids
            else SIM_VISUAL_GROUNDING_PIPELINE_ID,
            "visual_grounding_pipeline_ids": sorted(set(pipeline_ids)),
            "visual_grounding_failure_count": failure_count,
            "event_count": len(events),
            "candidate_count": sum(int(item.get("candidate_count") or 0) for item in events),
            "unresolved_count": sum(
                int((item.get("visual_grounding_pipeline") or {}).get("unresolved_count") or 0)
                for item in events
            ),
            "duplicate_rate": _average_duplicate_rate(events),
            "events": events,
            "private_truth_included": False,
            "policy_note": (
                "Camera-model policy candidates must be explicitly labelled and "
                "must not include private scoring truth."
            ),
        }

    def model_declared_observations_payload(self) -> dict[str, Any]:
        observations = [dict(item) for item in self._model_declared_observations]
        acted_handles = {
            handle
            for handle, lifecycle in self._object_lifecycle.items()
            if lifecycle.get("state") in {"navigating_to_object", "held", "placed", "placed_closed"}
        }
        for item in observations:
            item["acted_on"] = str(item.get("object_id") or "") in acted_handles
        return {
            "schema": MODEL_DECLARED_OBSERVATIONS_SCHEMA,
            "perception_mode": self.perception_mode,
            "observation_count": len(observations),
            "resolved_count": sum(
                1 for item in observations if item.get("grounding_status") == "resolved"
            ),
            "acted_count": sum(1 for item in observations if item.get("acted_on")),
            "observations": observations,
            "private_truth_included": False,
        }

    def private_evaluation_payload(self, score: dict[str, Any]) -> dict[str, Any]:
        targets = self.scenario.private_manifest.targets
        return {
            "generated_mess_count": len(targets),
            "generated_mess_set": [target.object_id for target in targets],
            "acceptable_destination_sets": {
                target.object_id: list(target.valid_receptacle_ids) for target in targets
            },
            "mess_restoration_rate": score["mess_restoration_rate"],
            "sweep_coverage_rate": score["sweep_coverage_rate"],
            "disturbance_count": score["disturbance_count"],
            "completion_status": score["completion_status"],
            "object_results": score["object_results"],
        }

    def target_fixture_for_detection(
        self,
        detection: dict[str, Any],
        fixture_hints: dict[str, Any],
    ) -> dict[str, Any] | None:
        if self.map_mode == MINIMAL_MAP_MODE:
            return self._minimal_target_fixture_for_detection(detection)
        return infer_target_fixture_for_detection(detection, fixture_hints)

    def attach_raw_fpv_observation_artifact(
        self,
        observation_id: str,
        *,
        views: dict[str, Any],
        robot_view_label: str | None = None,
        camera_control_contract: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        for item in self._raw_fpv_observations:
            if item.get("observation_id") != observation_id:
                continue
            fpv_path = views.get("fpv")
            if fpv_path:
                item["image_artifacts"] = {"fpv": str(fpv_path)}
                item["fpv_image"] = str(fpv_path)
                item["artifact_status"] = "recorded"
            if robot_view_label:
                item["robot_view_label"] = robot_view_label
            if camera_control_contract:
                item["camera_control_contract"] = _strip_forbidden_agent_view_keys(
                    camera_control_contract
                )
            _assert_no_forbidden_agent_view_keys(item)
            return dict(item)
        return None

    def _place(self, fixture_id: str, *, inside: bool) -> dict[str, Any]:
        requested_fixture_id = str(fixture_id)
        internal_fixture_id = self._internal_fixture_id_for_public_anchor(requested_fixture_id)
        public_fixture_id = self._public_fixture_response_id(
            internal_fixture_id,
            requested_fixture_id,
        )
        if internal_fixture_id not in self._fixtures:
            return self._error(
                "place_inside" if inside else "place",
                "stale_reference",
                fixture_id=requested_fixture_id,
            )
        handle = self._held_handle
        if handle is None:
            return self._error("place_inside" if inside else "place", "not_holding")
        tool = "place_inside" if inside else "place"
        if self._current_receptacle_for_handle != (handle, internal_fixture_id):
            return self._semantic_order_error(
                tool,
                required_tool="navigate_to_receptacle",
                object_id=handle,
                fixture_id=requested_fixture_id,
                recovery_hint=(
                    "Call navigate_to_receptacle for this fixture after pick and before "
                    "placing the held object."
                ),
            )
        if not inside and _fixture_prefers_inside(self._fixtures[internal_fixture_id]):
            requires_open = _fixture_requires_open(self._fixtures[internal_fixture_id])
            needs_open = requires_open and self._opened_receptacle_for_handle != (
                handle,
                internal_fixture_id,
            )
            required_tool = "open_receptacle" if needs_open else "place_inside"
            return self._semantic_order_error(
                "place",
                required_tool=required_tool,
                object_id=handle,
                fixture_id=requested_fixture_id,
                recovery_hint=(
                    "Use place_inside for fridge-like or shelf-like fixtures; "
                    "fridge-like fixtures must be opened first."
                ),
            )
        if inside and _fixture_requires_open(self._fixtures[internal_fixture_id]):
            if self._opened_receptacle_for_handle != (handle, internal_fixture_id):
                return self._semantic_order_error(
                    "place_inside",
                    required_tool="open_receptacle",
                    object_id=handle,
                    fixture_id=requested_fixture_id,
                    recovery_hint=(
                        "Call open_receptacle for this fridge-like fixture before place_inside."
                    ),
                )
        placed = (
            self.contract.place_inside(internal_fixture_id)
            if inside
            else self.contract.place(internal_fixture_id)
        )
        if placed.get("ok"):
            self._handled_handles.add(handle)
            self._set_handle_state(
                handle,
                "placed",
                tool=tool,
                fixture_id=public_fixture_id,
            )
            if inside and _fixture_requires_open(self._fixtures[internal_fixture_id]):
                self._pending_close_receptacle_for_handle = (handle, internal_fixture_id)
            else:
                self._pending_close_receptacle_for_handle = None
            self._held_handle = None
            self._current_receptacle_for_handle = None
            self._opened_receptacle_for_handle = None
        return self._public_manipulation_response(
            tool,
            handle,
            placed,
            fixture_id=public_fixture_id,
        )

    def _visible_detections_for_waypoint(
        self,
        waypoint: dict[str, Any],
        *,
        source_observation_id: str,
        visual_confirmation: bool,
    ) -> list[dict[str, Any]]:
        public_waypoint = waypoint
        waypoint = self._private_waypoint_for_public_waypoint(waypoint)
        locations = self.backend.object_locations()
        fixture_ids = set(waypoint.get("fixture_ids") or [])
        detections = []
        for obj in self.scenario.objects:
            location_id = locations.get(obj.object_id)
            if not location_id or location_id == "held_by_agent":
                continue
            fixture = self._fixtures.get(location_id)
            if fixture is None:
                continue
            room_id = _room_id(str(fixture.get("room_area", "unknown")))
            if self.map_mode != MINIMAL_MAP_MODE and room_id != waypoint["room_id"]:
                continue
            if fixture_ids and location_id not in fixture_ids:
                continue
            handle = self._handle_for_object(obj.object_id)
            image_region = (
                {"type": "bbox", "value": _image_bbox(handle)}
                if visual_confirmation
                else {
                    "type": "verbal_region",
                    "value": (
                        "structured semantic candidate; run adjust_camera then observe "
                        "to bind a source FPV bbox before navigation"
                    ),
                }
            )
            candidate_state = (
                CANDIDATE_STATE_NAVIGATION_AUTHORIZED
                if visual_confirmation
                else CANDIDATE_STATE_VISUAL_SCAN_REQUIRED
            )
            detection = {
                "object_id": handle,
                "category": obj.category,
                "name": obj.name,
                "current_room_id": room_id,
                "visibility_confidence": _visibility_confidence(handle),
                "image_bbox": _image_bbox(handle) if visual_confirmation else [],
                "image_region": image_region,
                "perception_source": "visible_detection",
                "producer_type": "visible_object_detections",
                "producer_id": "simulator_visible_object_detections",
                "source_observation_id": source_observation_id,
                "waypoint_id": str(public_waypoint.get("waypoint_id") or ""),
                "candidate_state": candidate_state,
                "candidate_state_history": _candidate_state_history(candidate_state),
                "visual_scan": visual_scan_payload(visual_confirmation),
                "locality_status": "same_waypoint_source_observation"
                if visual_confirmation
                else "semantic_hint_requires_source_fpv_scan",
                "support_estimate": {
                    "fixture_id": location_id,
                    "relation": _location_relation(obj.object_id, self.backend),
                    "confidence": 0.74,
                    "source": "visible_detection",
                    "perception_source": "visible_detection",
                    "model_provenance": "visible_object_detections",
                    "source_observation_id": source_observation_id,
                },
            }
            previous_state = str(
                (self._detections_by_handle.get(handle) or {}).get("candidate_state") or ""
            )
            detection["visual_grounding_evidence"] = _visual_grounding_evidence_for_candidate(
                detection
            )
            detection["candidate_state"] = _candidate_state(detection)
            detection["candidate_state_changed"] = previous_state != detection["candidate_state"]
            detection["previous_candidate_state"] = previous_state
            detection["candidate_state_history"] = _candidate_state_history(
                detection["candidate_state"]
            )
            detection["actionability_status"] = _candidate_actionability_status(detection)
            detection.update(self._public_candidate_hint(detection))
            if detection["candidate_state"] == CANDIDATE_STATE_VISUAL_SCAN_REQUIRED:
                self._ensure_generated_inspection_waypoint_for_detection(handle, detection)
            self._detections_by_handle[handle] = detection
            self._record_detection_lifecycle(handle, detection, public_waypoint)
            detections.append(dict(detection))
        return sorted(detections, key=lambda item: str(item["object_id"]))

    def _camera_model_candidates_for_waypoint(
        self,
        waypoint: dict[str, Any],
        *,
        observation_id: str,
        model_provenance: str,
    ) -> list[dict[str, Any]]:
        public_waypoint = waypoint
        waypoint = self._private_waypoint_for_public_waypoint(waypoint)
        locations = self.backend.object_locations()
        fixture_ids = set(waypoint.get("fixture_ids") or [])
        candidates = []
        for obj in self.scenario.objects:
            location_id = locations.get(obj.object_id)
            if not location_id or location_id == "held_by_agent":
                continue
            fixture = self._fixtures.get(location_id)
            if fixture is None:
                continue
            room_id = _room_id(str(fixture.get("room_area", "unknown")))
            if self.map_mode != MINIMAL_MAP_MODE and room_id != waypoint["room_id"]:
                continue
            if fixture_ids and location_id not in fixture_ids:
                continue
            handle = self._handle_for_object(obj.object_id)
            detection = {
                "object_id": handle,
                "category": obj.category,
                "name": obj.name,
                "current_room_id": room_id,
                "visibility_confidence": _visibility_confidence(handle),
                "image_bbox": _image_bbox(handle),
                "image_region": {"type": "bbox", "value": _image_bbox(handle)},
                "perception_source": CAMERA_MODEL_POLICY_MODE,
                "model_provenance": model_provenance,
                "source_observation_id": observation_id,
                "candidate_source": "raw_fpv_observation",
                "candidate_state": CANDIDATE_STATE_NAVIGATION_AUTHORIZED,
                "candidate_state_history": _candidate_state_history(
                    CANDIDATE_STATE_NAVIGATION_AUTHORIZED
                ),
                "locality_status": "same_waypoint_source_observation",
                "support_estimate": {
                    "fixture_id": location_id,
                    "relation": _location_relation(obj.object_id, self.backend),
                    "confidence": 0.68,
                    "source": CAMERA_MODEL_POLICY_MODE,
                    "perception_source": CAMERA_MODEL_POLICY_MODE,
                    "model_provenance": model_provenance,
                    "source_observation_id": observation_id,
                },
            }
            detection["visual_grounding_evidence"] = _visual_grounding_evidence_for_candidate(
                detection
            )
            detection["candidate_state"] = _candidate_state(detection)
            detection["candidate_state_history"] = _candidate_state_history(
                detection["candidate_state"]
            )
            detection["actionability_status"] = _candidate_actionability_status(detection)
            detection.update(self._public_candidate_hint(detection))
            _assert_no_forbidden_agent_view_keys(detection)
            self._detections_by_handle[handle] = detection
            self._record_detection_lifecycle(handle, detection, public_waypoint)
            candidates.append(dict(detection))
        return sorted(candidates, key=lambda item: str(item["object_id"]))

    def _public_candidate_hint(self, detection: dict[str, Any]) -> dict[str, Any]:
        candidate = self.target_fixture_for_detection(detection, self.fixture_hints())
        if candidate is None:
            return {
                "candidate_fixture_id": "",
                "candidate_fixture_category": "",
                "cleanup_recommended": False,
                "candidate_source": "public_category_fixture_affordance",
            }
        candidate_fixture_id = str(candidate.get("fixture_id") or "")
        source_fixture_id = str((detection.get("support_estimate") or {}).get("fixture_id") or "")
        internal_candidate_fixture_id = (
            self.internal_fixture_id_for_public_reference(candidate_fixture_id)
            or candidate_fixture_id
        )
        public_candidate_fixture_id = self._public_fixture_reference_id(candidate_fixture_id)
        public_source_fixture_id = self._public_fixture_reference_id(source_fixture_id)
        return {
            "candidate_fixture_id": public_candidate_fixture_id,
            "candidate_fixture_category": str(candidate.get("category") or ""),
            "cleanup_recommended": bool(
                public_candidate_fixture_id
                and public_candidate_fixture_id != public_source_fixture_id
                and not self._handle_is_non_actionable(str(detection.get("object_id") or ""))
                and _candidate_state(detection) == CANDIDATE_STATE_NAVIGATION_AUTHORIZED
            ),
            "candidate_source": "public_semantic_anchor"
            if self.map_mode == MINIMAL_MAP_MODE and candidate_fixture_id
            else "public_category_fixture_affordance",
            "recommended_tool": _recommended_place_tool(
                internal_candidate_fixture_id,
                self._fixtures,
            ),
        }

    def _record_raw_fpv_observation(
        self,
        waypoint: dict[str, Any],
        *,
        perception_mode: str = RAW_FPV_ONLY_MODE,
    ) -> dict[str, Any]:
        observation_id = f"raw_fpv_{len(self._raw_fpv_observations) + 1:03d}"
        item = {
            "observation_id": observation_id,
            "waypoint_id": str(waypoint["waypoint_id"]),
            "room_id": str(waypoint["room_id"]),
            "held_object_id": self._held_handle,
            "perception_mode": perception_mode,
            "structured_detections_available": False,
            "camera_offset": self._camera_offset(),
            "image_artifacts": {},
            "artifact_status": "pending_robot_view_capture",
            "public_contract_note": (
                "No structured movable-object detections, categories, support estimates, "
                "target labels, or private scoring truth are included."
            ),
        }
        self._raw_fpv_observations.append(item)
        return dict(item)

    def _record_inspection_observation(
        self,
        response: dict[str, Any],
        *,
        detections: list[dict[str, Any]],
        source_observation_id: str,
    ) -> None:
        state_counts: dict[str, int] = {}
        actionability_counts: dict[str, int] = {}
        changed = 0
        for detection in detections:
            state = str(detection.get("candidate_state") or "")
            if state:
                state_counts[state] = state_counts.get(state, 0) + 1
            actionability = str(detection.get("actionability_status") or "")
            if actionability:
                actionability_counts[actionability] = actionability_counts.get(actionability, 0) + 1
            if detection.get("candidate_state_changed") is True:
                changed += 1
        observation = {
            "schema": INSPECTION_OBSERVATION_SCHEMA,
            "observation_id": str(source_observation_id),
            "waypoint_id": str(response.get("waypoint_id") or self._current_waypoint_id),
            "room_id": str(response.get("current_room_id") or ""),
            "perception_mode": self.perception_mode,
            "evidence_lane": self._target_candidate_evidence_lane(),
            "camera_offset": self._camera_offset(),
            "camera_adjusted": bool(
                self._camera_offset().get("yaw_delta_deg")
                or self._camera_offset().get("pitch_delta_deg")
            ),
            "structured_detections_available": bool(
                response.get("structured_detections_available")
            ),
            "candidate_count": len(detections),
            "candidate_state_counts": state_counts,
            "actionability_status_counts": actionability_counts,
            "changed_candidate_state_count": changed,
            "private_truth_included": False,
        }
        _assert_no_forbidden_agent_view_keys(observation)
        self._inspection_observations.append(observation)

    def _simulated_declaration_inputs_for_waypoint(
        self,
        waypoint: dict[str, Any],
        *,
        observation_id: str,
    ) -> list[dict[str, Any]]:
        inputs = []
        for obj, location_id in self._objects_visible_from_waypoint(waypoint):
            handle = self._handle_for_object(obj.object_id)
            detection = self._detection_for_object_at_location(
                obj,
                location_id=location_id,
                handle=handle,
                waypoint=waypoint,
                perception_source=CAMERA_MODEL_POLICY_MODE,
                producer_type=SIMULATED_CAMERA_MODEL_PROVENANCE,
                source_observation_id=observation_id,
            )
            target = self.target_fixture_for_detection(detection, self.fixture_hints())
            target_fixture_id = str((target or {}).get("fixture_id") or location_id)
            inputs.append(
                {
                    "category": obj.category,
                    "source_fixture_id": location_id,
                    "target_fixture_id": target_fixture_id,
                    "evidence_note": (
                        "simulated camera model declared a public camera-derived "
                        f"{obj.category} candidate"
                    ),
                    "image_region": {"type": "bbox", "value": detection["image_bbox"]},
                    "confidence": detection.get("visibility_confidence", 0.68),
                }
            )
        return inputs

    def _camera_label_producer_candidates(
        self,
        *,
        raw_observation: dict[str, Any],
        waypoint: dict[str, Any],
    ) -> dict[str, Any]:
        if self.visual_grounding_pipeline_id == SIM_VISUAL_GROUNDING_PIPELINE_ID:
            candidates = self._simulated_declaration_inputs_for_waypoint(
                waypoint,
                observation_id=str(raw_observation["observation_id"]),
            )
            return {
                "ok": True,
                "candidates": candidates,
                "visual_grounding_pipeline": sim_visual_grounding_pipeline(
                    candidate_count=len(candidates)
                ),
            }
        if self.visual_grounding_client is None:
            return {
                "ok": True,
                "candidates": [],
                "visual_grounding_pipeline": pipeline_summary_from_response(
                    visual_grounding_failure_response(
                        pipeline_id=self.visual_grounding_pipeline_id,
                        reason="missing_client",
                        message=(
                            "non-sim camera-grounded-labels camera labeler requires an "
                            "External Visual Grounding Service client"
                        ),
                        latency_ms=0,
                    )
                ),
            }
        client_config = getattr(self.visual_grounding_client, "config", None)
        request = visual_grounding_request(
            run_id=self.visual_grounding_run_id or self.scenario.scenario_id,
            raw_observation=raw_observation,
            category_hints=list(VISUAL_GROUNDING_CATEGORY_HINTS),
            fixture_hints=self._fixture_hints_for_visual_grounding_request(),
            pipeline_id=self.visual_grounding_pipeline_id,
            image=image_payload_for_raw_observation(
                raw_observation,
                base_dir=self.visual_grounding_artifact_base_dir,
            ),
            proposer={
                "producer_id": str(getattr(client_config, "proposer_id", "") or ""),
                "model_id": str(getattr(client_config, "proposer_model_id", "") or ""),
            },
        )
        try:
            response = self.visual_grounding_client.request_candidates(request)
            auth_mode = str(getattr(client_config, "auth_mode", "none"))
            pipeline = pipeline_summary_from_response(response, auth_mode=auth_mode)
        except VisualGroundingContractError as exc:
            return {
                "ok": False,
                "error_reason": "visual_grounding_contract_error",
                "recovery_hint": str(exc),
                "candidates": [],
                "visual_grounding_pipeline": {
                    "schema": "visual_grounding_pipeline_v1",
                    "pipeline_id": self.visual_grounding_pipeline_id,
                    "status": "contract_error",
                    "stages": [],
                    "candidate_count": 0,
                    "unresolved_count": 0,
                    "duplicate_rate": 0.0,
                    "failure_reason": "contract_error",
                    "failure_message": str(exc),
                    "auth_mode": "none",
                },
            }
        if pipeline.get("status") == "failed":
            return {
                "ok": True,
                "candidates": [],
                "visual_grounding_pipeline": pipeline,
            }
        return {
            "ok": True,
            "candidates": self._candidate_inputs_from_visual_grounding_response(
                response,
                raw_observation=raw_observation,
                visual_grounding_pipeline=pipeline,
            ),
            "visual_grounding_pipeline": pipeline,
        }

    def _candidate_inputs_from_visual_grounding_response(
        self,
        response: dict[str, Any],
        *,
        raw_observation: dict[str, Any],
        visual_grounding_pipeline: dict[str, Any],
    ) -> list[dict[str, Any]]:
        image = image_payload_for_raw_observation(
            raw_observation,
            base_dir=self.visual_grounding_artifact_base_dir,
        )
        candidates = []
        for index, candidate in enumerate(response.get("candidates") or [], start=1):
            category = str(candidate.get("category") or "object")
            source_fixture_id = str(candidate.get("source_fixture_id") or "")
            target_fixture_id = self._resolved_destination_fixture_id(
                category=category,
                source_fixture_id=source_fixture_id,
            )
            overlay_path = self._visual_grounding_overlay_for_candidate(
                raw_observation=raw_observation,
                candidate=candidate,
                index=index,
            )
            candidates.append(
                {
                    "category": category,
                    "source_fixture_id": source_fixture_id,
                    "target_fixture_id": target_fixture_id,
                    "evidence_note": str(candidate.get("evidence_note") or ""),
                    "image_region": candidate.get("image_region"),
                    "confidence": candidate.get("confidence"),
                    "producer_type": EXTERNAL_VISUAL_GROUNDING_PROVENANCE,
                    "producer_id": visual_grounding_pipeline.get("pipeline_id", ""),
                    "visual_grounding_pipeline": visual_grounding_pipeline,
                    "visual_grounding_stage_provenance": list(
                        visual_grounding_pipeline.get("stages") or []
                    ),
                    "visual_grounding_destination_hint": candidate.get("destination_hint") or {},
                    "tracking": candidate.get("tracking") or {},
                    "image_dimensions": {
                        "width": image.get("width", 0),
                        "height": image.get("height", 0),
                    },
                    "visual_grounding_overlay": overlay_path,
                }
            )
        return candidates

    def _visual_grounding_overlay_for_candidate(
        self,
        *,
        raw_observation: dict[str, Any],
        candidate: dict[str, Any],
        index: int,
    ) -> str:
        if self.visual_grounding_artifact_base_dir is None:
            return ""
        region = candidate.get("image_region") or {}
        if region.get("type") != "bbox":
            return ""
        source_path = _raw_fpv_artifact_path(
            raw_observation,
            base_dir=self.visual_grounding_artifact_base_dir,
        )
        if source_path is None or not source_path.is_file():
            return ""
        observation_id = _safe_artifact_id(str(raw_observation.get("observation_id") or "raw_fpv"))
        rel_path = (
            Path("visual_grounding") / "overlays" / observation_id / f"candidate_{index:03d}.jpg"
        )
        output_path = self.visual_grounding_artifact_base_dir / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image, ImageDraw

            with Image.open(source_path) as source:
                image = source.convert("RGB")
            draw = ImageDraw.Draw(image)
            x, y, w, h = _normalized_bbox_pixels(
                region.get("value") or [0, 0, 0, 0],
                width=int(image.width),
                height=int(image.height),
            )
            draw.rectangle((x, y, x + w, y + h), outline=(26, 115, 232), width=3)
            label = str(candidate.get("category") or "candidate")
            draw.text((x + 4, max(0, y - 14)), label, fill=(26, 77, 160))
            image.save(output_path, format="JPEG", quality=80)
        except Exception:
            return ""
        return str(rel_path)

    def _resolved_destination_fixture_id(self, *, category: str, source_fixture_id: str) -> str:
        pseudo_detection = {
            "category": category,
            "name": category,
            "support_estimate": {"fixture_id": source_fixture_id},
        }
        target = self.target_fixture_for_detection(pseudo_detection, self.fixture_hints())
        return str((target or {}).get("fixture_id") or "")

    def _fixture_hints_for_visual_grounding_request(self) -> list[dict[str, Any]]:
        hints = self.fixture_hints()
        rows = []
        for room in hints.get("rooms") or []:
            room_id = str(room.get("room_id") or "")
            for fixture in room.get("fixtures") or []:
                rows.append(
                    {
                        "fixture_id": str(fixture.get("fixture_id") or ""),
                        "room_id": str(fixture.get("room_id") or room_id),
                        "category": str(fixture.get("category") or ""),
                        "name": str(fixture.get("name") or ""),
                        "affordances": list(fixture.get("affordances") or []),
                    }
                )
        return rows

    def _model_declared_observation_event(
        self,
        *,
        raw_observation: dict[str, Any],
        producer_type: str,
        producer_id: str,
        declared: list[dict[str, Any]],
        visual_grounding_pipeline: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema": MODEL_DECLARED_OBSERVATIONS_SCHEMA,
            "perception_mode": self.perception_mode,
            "observation_id": str(raw_observation["observation_id"]),
            "waypoint_id": str(raw_observation["waypoint_id"]),
            "room_id": str(raw_observation["room_id"]),
            "producer_type": producer_type,
            "producer_id": producer_id,
            "candidate_count": len(declared),
            "registered_observed_handles": [str(item["object_id"]) for item in declared],
            "visual_grounding_pipeline": visual_grounding_pipeline,
            "private_truth_included": False,
            "policy_note": (
                "Model-declared observations are derived from public camera evidence "
                "and public fixture metadata; private scoring truth is not exposed."
            ),
        }

    def _register_model_declared_candidate(
        self,
        *,
        raw_observation: dict[str, Any],
        waypoint: dict[str, Any],
        candidate: dict[str, Any],
        producer_type: str,
        producer_id: str,
    ) -> dict[str, Any]:
        normalized = self._normalized_visual_candidate(
            raw_observation=raw_observation,
            candidate=candidate,
            producer_type=producer_type,
            producer_id=producer_id,
        )
        match = self._resolve_visual_candidate(waypoint, normalized)
        declaration = self._declaration_from_resolution(normalized, match)
        handle = str(declaration["object_id"])
        if match["status"] == "already_handled":
            return dict(declaration)
        if match["status"] == "resolved":
            obj = match["objects"][0]
            location_id = str(match["location_ids"][0])
            detection = self._detection_for_object_at_location(
                obj,
                location_id=location_id,
                handle=handle,
                waypoint=waypoint,
                perception_source=MODEL_DECLARED_OBSERVATION_SOURCE,
                producer_type=producer_type,
                source_observation_id=str(raw_observation["observation_id"]),
            )
            detection.update(
                {
                    "model_declared_observation": declaration,
                    "model_declared_observation_id": declaration["declaration_id"],
                    "producer_type": producer_type,
                    "producer_id": producer_id,
                    "image_region": declaration["image_region"],
                    "evidence_note": declaration["evidence_note"],
                    "grounding_status": declaration["grounding_status"],
                    "grounding_confidence": declaration["grounding_confidence"],
                    "grounding_basis": declaration["grounding_basis"],
                    "visual_grounding_evidence": declaration["visual_grounding_evidence"],
                }
            )
            evidence = declaration["visual_grounding_evidence"]
            if isinstance(evidence, dict):
                detection["image_bbox"] = list(evidence.get("image_bbox") or [])
                detection["locality_status"] = str(
                    evidence.get("locality_status") or "same_waypoint_source_observation"
                )
            detection["candidate_state"] = _candidate_state(detection)
            detection["candidate_state_history"] = _candidate_state_history(
                detection["candidate_state"]
            )
            detection["actionability_status"] = _candidate_actionability_status(detection)
            detection.update(self._public_candidate_hint(detection))
            detection["candidate_state"] = _candidate_state(detection)
            detection["candidate_state_history"] = _candidate_state_history(
                detection["candidate_state"]
            )
            detection["actionability_status"] = _candidate_actionability_status(detection)
            if isinstance(detection.get("visual_grounding_evidence"), dict):
                detection["visual_grounding_evidence"]["candidate_state"] = detection[
                    "candidate_state"
                ]
                detection["visual_grounding_evidence"]["actionability_status"] = detection[
                    "actionability_status"
                ]
            _assert_no_forbidden_agent_view_keys(detection)
            self._detections_by_handle[handle] = detection
            self._record_detection_lifecycle(handle, detection, waypoint)
        else:
            self._detections_by_handle[handle] = {
                "object_id": handle,
                "category": declaration["category"],
                "current_room_id": declaration["room_id"],
                "perception_source": MODEL_DECLARED_OBSERVATION_SOURCE,
                "model_declared_observation": declaration,
                "model_declared_observation_id": declaration["declaration_id"],
                "producer_type": producer_type,
                "producer_id": producer_id,
                "source_observation_id": declaration["source_observation_id"],
                "image_region": declaration["image_region"],
                "evidence_note": declaration["evidence_note"],
                "grounding_status": declaration["grounding_status"],
                "grounding_confidence": declaration["grounding_confidence"],
                "grounding_basis": declaration["grounding_basis"],
                "recovery_hint": declaration["recovery_hint"],
                "target_fixture_id": declaration["target_fixture_id"],
                "target_fixture_category": declaration["target_fixture_category"],
                "target_plausibility": declaration["target_plausibility"],
                "visual_grounding_evidence": declaration["visual_grounding_evidence"],
                "actionability_status": declaration["actionability_status"],
                "candidate_state": declaration["candidate_state"],
                "candidate_state_history": declaration["candidate_state_history"],
            }
            self._set_handle_state(
                handle,
                f"grounding_{declaration['grounding_status']}",
                tool="declare_visual_candidates",
                waypoint_id=str(waypoint["waypoint_id"]),
                room_id=str(waypoint["room_id"]),
                source_fixture_id=declaration.get("source_fixture_id", ""),
                category=declaration["category"],
                perception_source=MODEL_DECLARED_OBSERVATION_SOURCE,
                grounding_status=declaration["grounding_status"],
            )
        self._model_declared_observations.append(declaration)
        return dict(declaration)

    def _normalized_visual_candidate(
        self,
        *,
        raw_observation: dict[str, Any],
        candidate: dict[str, Any],
        producer_type: str,
        producer_id: str,
    ) -> dict[str, Any]:
        image_region = _normalize_image_region(candidate.get("image_region"))
        category = str(candidate.get("category") or "object").strip() or "object"
        target_fixture_id = str(candidate.get("target_fixture_id") or "")
        target_resolution_source = "model_declared_target_fixture"
        if not target_fixture_id:
            target_fixture_id = self._resolve_runtime_anchor_target_fixture_id(category)
            if target_fixture_id:
                target_resolution_source = "runtime_metric_map_public_semantic_anchor"
        target_fixture = self._fixtures.get(
            self.internal_fixture_id_for_public_reference(target_fixture_id) or target_fixture_id,
            {},
        )
        confidence = candidate.get("confidence")
        try:
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_value = None
        return {
            "source_observation_id": str(raw_observation["observation_id"]),
            "waypoint_id": str(raw_observation["waypoint_id"]),
            "room_id": str(raw_observation["room_id"]),
            "category": category,
            "target_fixture_id": target_fixture_id,
            "target_fixture_category": str(
                target_fixture.get("category") or target_fixture.get("name") or ""
            ),
            "target_fixture_resolution_source": target_resolution_source
            if target_fixture_id
            else "unresolved",
            "source_fixture_id": str(candidate.get("source_fixture_id") or ""),
            "evidence_note": str(candidate.get("evidence_note") or ""),
            "image_region": image_region,
            "confidence": confidence_value,
            "producer_type": str(candidate.get("producer_type") or producer_type),
            "producer_id": str(candidate.get("producer_id") or producer_id),
            "supersedes_observation_id": str(candidate.get("supersedes_observation_id") or ""),
            "visual_grounding_pipeline": candidate.get("visual_grounding_pipeline") or {},
            "visual_grounding_stage_provenance": list(
                candidate.get("visual_grounding_stage_provenance") or []
            ),
            "visual_grounding_destination_hint": candidate.get("visual_grounding_destination_hint")
            or {},
            "tracking": candidate.get("tracking") or {},
            "image_dimensions": candidate.get("image_dimensions") or {},
            "visual_grounding_overlay": str(candidate.get("visual_grounding_overlay") or ""),
        }

    def _resolve_visual_candidate(
        self,
        waypoint: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        category_norm = _norm(candidate.get("category"))
        source_fixture_id = str(candidate.get("source_fixture_id") or "")
        match = self._visual_candidate_match_for_source(
            waypoint,
            category_norm=category_norm,
            source_fixture_id=source_fixture_id,
            restrict_to_waypoint_fixtures=True,
        )
        match["locality_status"] = (
            "exact_source_fixture_in_source_observation"
            if source_fixture_id and match["status"] != "unresolved"
            else "same_waypoint_source_observation"
            if match["status"] != "unresolved"
            else "source_observation_locality_unresolved"
        )
        if source_fixture_id and match["status"] == "unresolved":
            match["requested_source_fixture_id"] = source_fixture_id
        return match

    def _visual_candidate_match_for_source(
        self,
        waypoint: dict[str, Any],
        *,
        category_norm: str,
        source_fixture_id: str,
        restrict_to_waypoint_fixtures: bool,
    ) -> dict[str, Any]:
        candidates = []
        location_ids = []
        handled_candidates = []
        handled_location_ids = []
        visible = (
            self._objects_visible_from_waypoint(waypoint)
            if restrict_to_waypoint_fixtures
            else self._objects_visible_from_room(waypoint)
        )
        for obj, location_id in visible:
            if category_norm and not _declared_category_matches_object(category_norm, obj):
                continue
            if source_fixture_id and location_id != source_fixture_id:
                continue
            existing_handle = self._observed_handles_by_object_id.get(obj.object_id)
            if existing_handle and self._handle_is_non_actionable(existing_handle):
                handled_candidates.append(obj)
                handled_location_ids.append(location_id)
                continue
            candidates.append(obj)
            location_ids.append(location_id)
        if len(candidates) == 1:
            return {"status": "resolved", "objects": candidates, "location_ids": location_ids}
        if len(candidates) > 1:
            return {"status": "ambiguous", "objects": candidates, "location_ids": location_ids}
        if handled_candidates:
            return {
                "status": "already_handled",
                "objects": handled_candidates,
                "location_ids": handled_location_ids,
            }
        return {"status": "unresolved", "objects": [], "location_ids": []}

    def _declaration_from_resolution(
        self,
        candidate: dict[str, Any],
        match: dict[str, Any],
    ) -> dict[str, Any]:
        status = str(match["status"])
        objects = match.get("objects") or []
        if status == "resolved":
            handle = self._handle_for_object(objects[0].object_id)
            basis = "single public camera-context object matched exact source observation locality"
            confidence = _grounding_confidence(candidate, "resolved")
            recovery_hint = ""
            grounding_status = "resolved"
            actionability_status = "actionable"
        elif status == "already_handled":
            handle = self._handle_for_object(objects[0].object_id)
            lifecycle = self._object_lifecycle.get(handle, {})
            basis = "only matching public camera-context object was already handled"
            confidence = _grounding_confidence(candidate, "unresolved")
            recovery_hint = (
                "The matching observed handle has already been placed or otherwise "
                "handled. Continue the waypoint sweep and observe for other objects."
            )
            grounding_status = "unresolved"
            actionability_status = "already_handled"
        else:
            handle = self._new_unresolved_handle()
            basis = (
                "multiple public camera-context objects matched"
                if status == "ambiguous"
                else "no public camera-context object matched"
            )
            confidence = _grounding_confidence(candidate, status)
            recovery_hint = (
                "Provide a tighter bbox/point or source_fixture_id before picking."
                if status == "ambiguous"
                else (
                    "No public actionable object matched this declaration. Retry at most once "
                    "with a tighter image_region or clearer category, then continue the "
                    "waypoint sweep instead of looping on this visible item."
                )
            )
            grounding_status = status
            actionability_status = "needs_clarification"
        target_fixture_id = str(candidate.get("target_fixture_id") or "")
        internal_target_fixture_id = (
            self.internal_fixture_id_for_public_reference(target_fixture_id) or target_fixture_id
        )
        target_fixture = self._fixtures.get(internal_target_fixture_id, {})
        visual_grounding_evidence = _visual_grounding_evidence_for_candidate(
            {**candidate, "locality_status": match.get("locality_status", "")},
            fallback_image_bbox=candidate.get("image_bbox"),
            grounding_status=grounding_status,
        )
        if actionability_status == "actionable":
            actionability_status = _candidate_actionability_status(
                {
                    "visual_grounding_evidence": visual_grounding_evidence,
                    "grounding_status": grounding_status,
                }
            )
            if actionability_status != "actionable":
                recovery_hint = visual_evidence_recovery_hint()
        target_plausibility = self._target_plausibility(
            category=str(candidate.get("category") or ""),
            target_fixture_id=target_fixture_id,
        )
        declaration = {
            "schema": MODEL_DECLARED_OBSERVATION_SCHEMA,
            "declaration_id": f"declared_{len(self._model_declared_observations) + 1:03d}",
            "object_id": handle,
            "source_observation_id": str(candidate["source_observation_id"]),
            "waypoint_id": str(candidate["waypoint_id"]),
            "room_id": str(candidate["room_id"]),
            "category": str(candidate["category"]),
            "target_fixture_id": target_fixture_id,
            "target_fixture_category": str(
                target_fixture.get("category") or target_fixture.get("name") or ""
            ),
            "source_fixture_id": str(candidate.get("source_fixture_id") or ""),
            "evidence_note": str(candidate.get("evidence_note") or ""),
            "image_region": candidate["image_region"],
            "confidence": candidate.get("confidence"),
            "producer_type": str(candidate["producer_type"]),
            "producer_id": str(candidate["producer_id"]),
            "supersedes_observation_id": str(candidate.get("supersedes_observation_id") or ""),
            "grounding_status": grounding_status,
            "grounding_confidence": confidence,
            "grounding_basis": basis,
            "recovery_hint": recovery_hint,
            "target_plausibility": target_plausibility,
            "actionability_status": actionability_status,
            "candidate_state": _candidate_state(
                {
                    **candidate,
                    "visual_grounding_evidence": visual_grounding_evidence,
                    "grounding_status": grounding_status,
                    "actionability_status": actionability_status,
                    "candidate_fixture_id": target_fixture_id,
                    "recommended_tool": _recommended_place_tool(
                        internal_target_fixture_id,
                        self._fixtures,
                    )
                    if target_fixture_id
                    else "",
                }
            ),
            "visual_grounding_evidence": visual_grounding_evidence,
            "private_truth_included": False,
        }
        declaration["candidate_state_history"] = _candidate_state_history(
            str(declaration["candidate_state"])
        )
        declaration["visual_grounding_evidence"]["candidate_state"] = declaration["candidate_state"]
        declaration["visual_grounding_evidence"]["actionability_status"] = declaration[
            "actionability_status"
        ]
        for key in (
            "visual_grounding_pipeline",
            "visual_grounding_stage_provenance",
            "visual_grounding_destination_hint",
            "tracking",
            "image_dimensions",
            "visual_grounding_overlay",
        ):
            value = candidate.get(key)
            if value:
                declaration[key] = value
        if status == "already_handled":
            declaration["handled_state"] = str(lifecycle.get("state") or "handled")
        _assert_no_forbidden_agent_view_keys(declaration)
        return declaration

    def _target_plausibility(self, *, category: str, target_fixture_id: str) -> dict[str, Any]:
        internal_target_fixture_id = (
            self.internal_fixture_id_for_public_reference(target_fixture_id) or target_fixture_id
        )
        fixture = self._fixtures.get(internal_target_fixture_id)
        if fixture is None:
            return {
                "status": "unknown_fixture",
                "basis": "target fixture id is not in public fixture hints",
            }
        pseudo_detection = {
            "category": category,
            "name": category,
            "support_estimate": {"fixture_id": ""},
        }
        public_target = self.target_fixture_for_detection(pseudo_detection, self.fixture_hints())
        expected = str((public_target or {}).get("fixture_id") or "")
        return {
            "status": "plausible" if not expected or expected == target_fixture_id else "weak",
            "basis": "public category/fixture affordance",
            "expected_fixture_id": expected,
        }

    def _detection_for_object_at_location(
        self,
        obj: Any,
        *,
        location_id: str,
        handle: str,
        waypoint: dict[str, Any],
        perception_source: str,
        producer_type: str,
        source_observation_id: str,
    ) -> dict[str, Any]:
        fixture = self._fixtures.get(location_id, {})
        room_id = _room_id(str(fixture.get("room_area", waypoint["room_id"])))
        detection = {
            "object_id": handle,
            "category": obj.category,
            "name": obj.name,
            "current_room_id": room_id,
            "visibility_confidence": _visibility_confidence(handle),
            "image_bbox": _image_bbox(handle),
            "image_region": {"type": "bbox", "value": _image_bbox(handle)},
            "perception_source": perception_source,
            "producer_type": producer_type,
            "source_observation_id": source_observation_id,
            "candidate_source": MODEL_DECLARED_OBSERVATION_SOURCE
            if perception_source == MODEL_DECLARED_OBSERVATION_SOURCE
            else "raw_fpv_observation",
            "candidate_state": CANDIDATE_STATE_NAVIGATION_AUTHORIZED,
            "candidate_state_history": _candidate_state_history(
                CANDIDATE_STATE_NAVIGATION_AUTHORIZED
            ),
            "locality_status": "same_waypoint_source_observation",
            "support_estimate": {
                "fixture_id": location_id,
                "relation": _location_relation(obj.object_id, self.backend),
                "confidence": 0.68,
                "source": perception_source,
                "perception_source": perception_source,
                "producer_type": producer_type,
                "source_observation_id": source_observation_id,
            },
        }
        detection["model_provenance"] = producer_type
        detection["support_estimate"]["model_provenance"] = producer_type
        detection["visual_grounding_evidence"] = _visual_grounding_evidence_for_candidate(detection)
        detection["candidate_state"] = _candidate_state(detection)
        detection["candidate_state_history"] = _candidate_state_history(
            detection["candidate_state"]
        )
        detection["actionability_status"] = _candidate_actionability_status(detection)
        detection.update(self._public_candidate_hint(detection))
        _assert_no_forbidden_agent_view_keys(detection)
        return detection

    def _objects_visible_from_waypoint(self, waypoint: dict[str, Any]) -> list[tuple[Any, str]]:
        waypoint = self._private_waypoint_for_public_waypoint(waypoint)
        locations = self.backend.object_locations()
        fixture_ids = set(waypoint.get("fixture_ids") or [])
        visible = []
        for obj in self.scenario.objects:
            location_id = locations.get(obj.object_id)
            if not location_id or location_id == "held_by_agent":
                continue
            fixture = self._fixtures.get(location_id)
            if fixture is None:
                continue
            room_id = _room_id(str(fixture.get("room_area", "unknown")))
            if self.map_mode != MINIMAL_MAP_MODE and room_id != waypoint["room_id"]:
                continue
            if fixture_ids and location_id not in fixture_ids:
                continue
            visible.append((obj, str(location_id)))
        return visible

    def _objects_visible_from_room(self, waypoint: dict[str, Any]) -> list[tuple[Any, str]]:
        waypoint = self._private_waypoint_for_public_waypoint(waypoint)
        locations = self.backend.object_locations()
        visible = []
        for obj in self.scenario.objects:
            location_id = locations.get(obj.object_id)
            if not location_id or location_id == "held_by_agent":
                continue
            fixture = self._fixtures.get(location_id)
            if fixture is None:
                continue
            room_id = _room_id(str(fixture.get("room_area", "unknown")))
            if self.map_mode != MINIMAL_MAP_MODE and room_id != waypoint["room_id"]:
                continue
            visible.append((obj, str(location_id)))
        return visible

    def _unresolved_visual_candidate_error(
        self,
        tool: str,
        object_id: str,
    ) -> dict[str, Any] | None:
        detection = self._detections_by_handle.get(object_id)
        if not detection:
            return None
        declaration = detection.get("model_declared_observation") or {}
        status = declaration.get("grounding_status") or detection.get("grounding_status")
        if status not in {"ambiguous", "unresolved"}:
            return None
        return self._error(
            tool,
            "visual_candidate_not_resolved",
            object_id=object_id,
            grounding_status=status,
            grounding_confidence=declaration.get(
                "grounding_confidence",
                detection.get("grounding_confidence", 0.0),
            ),
            grounding_basis=declaration.get(
                "grounding_basis",
                detection.get("grounding_basis", ""),
            ),
            recovery_hint=declaration.get(
                "recovery_hint",
                detection.get(
                    "recovery_hint",
                    "Declare a tighter image_region or source_fixture_id before picking.",
                ),
            ),
        )

    def _visual_evidence_for_handle(self, handle: str) -> dict[str, Any]:
        detection = self._detections_by_handle.get(handle) or {}
        evidence = detection.get("visual_grounding_evidence")
        if isinstance(evidence, dict) and evidence:
            return copy.deepcopy(evidence)
        declaration = detection.get("model_declared_observation") or {}
        return _visual_grounding_evidence_for_candidate(
            {
                **detection,
                "image_region": detection.get("image_region") or declaration.get("image_region"),
                "producer_type": detection.get("producer_type") or declaration.get("producer_type"),
                "producer_id": detection.get("producer_id") or declaration.get("producer_id"),
                "source_observation_id": detection.get("source_observation_id")
                or declaration.get("source_observation_id"),
                "grounding_status": detection.get("grounding_status")
                or declaration.get("grounding_status"),
            }
        )

    def _visual_evidence_actionability_error(
        self,
        tool: str,
        object_id: str,
    ) -> dict[str, Any] | None:
        detection = self._detections_by_handle.get(object_id)
        if not detection:
            return None
        if self._handle_is_non_actionable(object_id):
            return None
        status = _candidate_actionability_status(detection)
        candidate_state = _candidate_state(detection)
        if status == "actionable" and candidate_state == CANDIDATE_STATE_NAVIGATION_AUTHORIZED:
            return None
        evidence = self._visual_evidence_for_handle(object_id)
        declaration = detection.get("model_declared_observation") or {}
        return self._error(
            tool,
            "visual_evidence_not_reviewable",
            object_id=object_id,
            required_next_tool="adjust_camera"
            if candidate_state == CANDIDATE_STATE_VISUAL_SCAN_REQUIRED
            else "observe",
            recovery_tool_options=["observe", "adjust_camera"],
            actionability_status=status,
            candidate_state=candidate_state,
            visual_grounding_evidence=evidence,
            grounding_status=detection.get("grounding_status")
            or declaration.get("grounding_status")
            or "resolved",
            grounding_confidence=detection.get("grounding_confidence")
            or declaration.get("grounding_confidence")
            or 0.0,
            source_observation_id=evidence.get("source_observation_id", ""),
            recovery_hint=visual_evidence_recovery_hint(),
        )

    def _next_visible_observation_id(self) -> str:
        self._visible_observation_count += 1
        return f"world_label_fpv_{self._visible_observation_count:03d}"

    def _camera_scan_confirmed(self) -> bool:
        offset = self._camera_offset()
        waypoint = self._waypoint_by_id(self._current_waypoint_id) or {}
        return bool(
            offset.get("yaw_delta_deg")
            or offset.get("pitch_delta_deg")
            or waypoint.get("waypoint_source") == "generated_target_inspection_candidate"
        )

    def _raw_fpv_observation_by_id(self, observation_id: str | None) -> dict[str, Any] | None:
        if observation_id:
            for item in self._raw_fpv_observations:
                if item.get("observation_id") == observation_id:
                    return item
            return None
        return self._raw_fpv_observations[-1] if self._raw_fpv_observations else None

    def _camera_offset(self) -> dict[str, float]:
        return {
            "yaw_delta_deg": round(self._camera_yaw_offset_deg, 3),
            "pitch_delta_deg": round(self._camera_pitch_offset_deg, 3),
        }

    def _reset_camera_adjustment(self) -> None:
        self._camera_yaw_offset_deg = 0.0
        self._camera_pitch_offset_deg = 0.0

    def _public_navigation_waypoints(self) -> list[dict[str, Any]]:
        return [*self._public_waypoints, *self._generated_inspection_waypoints.values()]

    def _realworld_metrics(
        self,
        score: dict[str, Any],
        final_locations: dict[str, str],
    ) -> dict[str, Any]:
        total_targets = int(score.get("total_targets") or 0)
        restored_count = int(score.get("restored_count") or 0)
        mess_rate = restored_count / total_targets if total_targets else 0.0
        total_waypoints = len(self._waypoints)
        coverage = len(self._observed_waypoint_ids) / total_waypoints if total_waypoints else 1.0
        target_ids = {target.object_id for target in self.scenario.private_manifest.targets}
        disturbance_count = sum(
            1
            for object_id, start in self._initial_locations.items()
            if object_id not in target_ids and final_locations.get(object_id) not in {None, start}
        )
        completion_status = (
            "success"
            if mess_rate >= 0.70 and coverage >= 0.90 and disturbance_count <= 2
            else "partial_success"
            if restored_count
            else "failed"
        )
        return {
            "mess_restoration_rate": round(mess_rate, 6),
            "sweep_coverage_rate": round(coverage, 6),
            "disturbance_count": disturbance_count,
            "completion_status": completion_status,
        }

    def _public_manipulation_response(
        self,
        tool: str,
        handle: str,
        response: dict[str, Any],
        *,
        fixture_id: str | None = None,
        navigate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "object_id": handle,
            "primitive_provenance": response.get("primitive_provenance", API_SEMANTIC_PROVENANCE),
            "state_mutation": response.get("state_mutation"),
        }
        if fixture_id is not None:
            payload["fixture_id"] = fixture_id
            payload["receptacle_id"] = fixture_id
        if navigate is not None:
            payload["navigation_status"] = navigate.get("status")
        if response.get("location_relation") is not None:
            payload["location_relation"] = response.get("location_relation")
        if response.get("previous_location_id") is not None:
            payload["previous_location_id"] = response.get("previous_location_id")
            payload["source_receptacle_id"] = response.get("previous_location_id")
        if response.get("location_id") is not None:
            payload["location_id"] = response.get("location_id")
        if response.get("contained_in") is not None:
            payload["contained_in"] = response.get("contained_in")
        if response.get("placement_diagnostic") is not None:
            payload["placement_diagnostic"] = response.get("placement_diagnostic")
        return (
            self._ok(tool, **payload)
            if response.get("ok")
            else self._error(
                tool,
                str(response.get("error_reason", "error")),
                object_id=handle,
            )
        )

    def _public_fixture_response(
        self,
        tool: str,
        fixture_id: str,
        response: dict[str, Any],
        *,
        object_id: str | None = None,
    ) -> dict[str, Any]:
        if not response.get("ok"):
            return self._error(
                tool, str(response.get("error_reason", "error")), fixture_id=fixture_id
            )
        return self._ok(
            tool,
            fixture_id=fixture_id,
            receptacle_id=fixture_id,
            object_id=object_id if object_id is not None else self._held_handle,
            primitive_provenance=response.get("primitive_provenance", API_SEMANTIC_PROVENANCE),
            opened=response.get("opened"),
            closed=response.get("closed"),
            state_mutation=response.get("state_mutation"),
        )

    def _public_error_from_private(
        self,
        tool: str,
        handle: str,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return self._error(
            tool,
            str(response.get("error_reason", "error")),
            object_id=handle,
        )

    def _current_room_id(self) -> str:
        waypoint = self._waypoint_by_id(self._current_waypoint_id)
        return str(waypoint["room_id"]) if waypoint is not None else ""

    def _fallback_metric_map_template(self) -> dict[str, Any]:
        frame_id = "map"
        map_id = f"{self.scenario.scenario_id}_minimal_map"
        map_version = "minimal-navigation-map-v1"
        return {
            "ok": True,
            "tool": "metric_map",
            "status": "ok",
            "contract": REALWORLD_CONTRACT,
            "schema": REAL_ROBOT_MAP_BUNDLE_SCHEMA,
            "frame_id": frame_id,
            "map_id": map_id,
            "map_version": map_version,
            "resolution_m": 0.05,
            "origin": {"x": 0.0, "y": 0.0, "yaw": 0.0},
            "width": 240,
            "height": 180,
            "occupancy_values": {"unknown": -1, "free": 0, "occupied": 100},
            "occupancy_grid_artifact": None,
            "map_bundle": metric_map_bundle_metadata(
                environment_id=self.scenario.scenario_id,
                map_id=map_id,
                map_version=map_version,
            ),
            "rooms": [_metric_map_room_payload(room) for room in self._rooms],
            "driveable_ways": _driveable_ways(self._rooms),
            "inspection_waypoints": [
                {
                    "waypoint_id": item["waypoint_id"],
                    "frame_id": frame_id,
                    "x": item["x"],
                    "y": item["y"],
                    "yaw": item["yaw"],
                    "room_id": item["room_id"],
                    "label": item["label"],
                    "purpose": item["purpose"],
                    "waypoint_source": item["waypoint_source"],
                    "coverage_estimate": item["coverage_estimate"],
                    "fixture_ids": list(item.get("fixture_ids") or []),
                }
                for item in self._waypoints
            ],
        }

    def _current_pose(self) -> dict[str, float]:
        waypoint = self._waypoint_by_id(self._current_waypoint_id)
        if waypoint is None:
            return {"x": 0.0, "y": 0.0, "yaw": 0.0}
        return self._waypoint_pose(waypoint)

    @staticmethod
    def _waypoint_pose(waypoint: dict[str, Any]) -> dict[str, float]:
        return {
            "x": float(waypoint.get("x", 0.0)),
            "y": float(waypoint.get("y", 0.0)),
            "yaw": float(waypoint.get("yaw", 0.0)),
        }

    def _fixture_pose(self, fixture_id: str) -> dict[str, Any]:
        fixture = self._fixtures.get(fixture_id) or {}
        pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
        if pose:
            return {
                "frame_id": str(pose.get("frame_id") or "map"),
                "x": float(pose.get("x", 0.0)),
                "y": float(pose.get("y", 0.0)),
                "yaw": float(pose.get("yaw", 0.0)),
            }
        room = next((item for item in self._rooms if fixture_id in item["fixture_ids"]), None)
        if room is None:
            waypoint = self._waypoint_by_id(self._preferred_waypoint_for_fixture(fixture_id))
            pose = self._waypoint_pose(waypoint or {})
            return {"frame_id": "map", **pose}
        polygon = room.get("polygon") or []
        xs = [float(point.get("x", 0.0)) for point in polygon] or [0.0, 2.0]
        ys = [float(point.get("y", 0.0)) for point in polygon] or [0.0, 2.0]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        fixture_ids = sorted(str(item) for item in room["fixture_ids"])
        index = fixture_ids.index(fixture_id) if fixture_id in fixture_ids else 0
        slots = (
            (min_x + 0.35, min_y + 0.35),
            (max_x - 0.35, min_y + 0.35),
            (min_x + 0.35, max_y - 0.35),
            (max_x - 0.35, max_y - 0.35),
            (min_x + 0.35, (min_y + max_y) / 2.0),
            (max_x - 0.35, (min_y + max_y) / 2.0),
        )
        x, y = slots[index % len(slots)]
        pose = {"x": round(x, 3), "y": round(y, 3), "yaw": 0.0}
        return {"frame_id": "map", **pose}

    def _object_goal_pose(self, handle: str) -> dict[str, Any]:
        detection = self._detections_by_handle.get(handle) or {}
        support = detection.get("support_estimate") or {}
        fixture_id = str(support.get("fixture_id") or "")
        if fixture_id:
            pose = self._fixture_pose(fixture_id)
        else:
            pose = {"frame_id": "map", **self._current_pose()}
        return pose

    def _object_pose_confidence(self, handle: str) -> float:
        detection = self._detections_by_handle.get(handle) or {}
        confidence = detection.get("visibility_confidence")
        try:
            return float(confidence)
        except (TypeError, ValueError):
            return 0.5

    def _handle_is_non_actionable(self, handle: str) -> bool:
        if handle in self._handled_handles:
            return True
        state = str((self._object_lifecycle.get(handle) or {}).get("state") or "")
        return state in _NON_ACTIONABLE_HANDLE_STATES

    def _preferred_waypoint_for_fixture(self, fixture_id: str) -> str:
        fixture = self._fixtures.get(fixture_id) or {}
        for key in ("preferred_inspection_waypoint_id", "preferred_manipulation_waypoint_id"):
            preferred = str(fixture.get(key) or "")
            if preferred and self._waypoint_by_id(preferred) is not None:
                return preferred
        for waypoint in self._waypoints:
            if fixture_id in set(waypoint.get("fixture_ids") or []):
                return str(waypoint["waypoint_id"])
        return self._current_waypoint_id

    def _record_detection_lifecycle(
        self,
        handle: str,
        detection: dict[str, Any],
        waypoint: dict[str, Any],
    ) -> None:
        state = "placed" if handle in self._handled_handles else "pending"
        if handle == self._held_handle:
            state = "held"
        elif handle == self._current_object_handle:
            state = "navigating_to_object"
        self._set_handle_state(
            handle,
            state,
            tool="observe",
            waypoint_id=str(waypoint["waypoint_id"]),
            room_id=str(waypoint["room_id"]),
            source_fixture_id=str((detection.get("support_estimate") or {}).get("fixture_id", "")),
            category=str(detection.get("category", "")),
            grounding_status=str(detection.get("grounding_status") or ""),
            perception_source=str(
                detection.get("perception_source")
                or detection.get("support_estimate", {}).get("source")
                or "visible_detection"
            ),
        )

    def _set_handle_state(self, handle: str, state: str, **updates: Any) -> None:
        lifecycle = getattr(self, "_object_lifecycle", None)
        if lifecycle is None:
            lifecycle = {}
            self._object_lifecycle = lifecycle
        item = dict(lifecycle.get(handle, {}))
        item.setdefault("object_id", handle)
        item["state"] = state
        item.update({key: value for key, value in updates.items() if value is not None})
        lifecycle[handle] = item

    def _waypoint_by_id(self, waypoint_id: str) -> dict[str, Any] | None:
        generated = self._generated_inspection_waypoints.get(str(waypoint_id))
        if generated is not None:
            return generated
        if self.map_mode == MINIMAL_MAP_MODE:
            public_waypoint = next(
                (item for item in self._public_waypoints if item["waypoint_id"] == waypoint_id),
                None,
            )
            if public_waypoint is not None:
                return public_waypoint
        return next((item for item in self._waypoints if item["waypoint_id"] == waypoint_id), None)

    def _private_waypoint_for_public_waypoint(self, waypoint: dict[str, Any]) -> dict[str, Any]:
        if str(waypoint.get("waypoint_source") or "") == "generated_target_inspection_candidate":
            mapped = self._private_waypoint_by_public_id.get(str(waypoint.get("waypoint_id") or ""))
            return mapped or waypoint
        if self.map_mode != MINIMAL_MAP_MODE:
            return waypoint
        return (
            self._private_waypoint_by_public_id.get(str(waypoint.get("waypoint_id") or ""))
            or waypoint
        )

    def _backend_navigation_waypoint(self, waypoint: dict[str, Any]) -> dict[str, Any]:
        navigation_waypoint = dict(waypoint)
        room = next(
            (
                item
                for item in self._rooms
                if str(item.get("room_id") or "") == str(waypoint.get("room_id") or "")
            ),
            None,
        )
        bounds = _room_polygon_bounds(room) if room is not None else None
        if bounds is not None:
            navigation_waypoint["source_room_bounds"] = bounds
        return navigation_waypoint

    def _handle_for_object(self, object_id: str) -> str:
        existing = self._observed_handles_by_object_id.get(object_id)
        if existing is not None:
            return existing
        handle = self._new_observed_handle()
        self._observed_handles_by_object_id[object_id] = handle
        self._object_ids_by_handle[handle] = object_id
        return handle

    def _ensure_generated_inspection_waypoint_for_detection(
        self,
        handle: str,
        detection: dict[str, Any],
    ) -> dict[str, Any]:
        existing = self._generated_inspection_waypoint_for_object(handle)
        if existing:
            return existing
        source_waypoint_id = str(detection.get("waypoint_id") or self._current_waypoint_id)
        source_waypoint = self._waypoint_by_id(source_waypoint_id) or {}
        if not source_waypoint:
            return {}
        index = len(self._generated_inspection_waypoints) + 1
        waypoint_id = f"generated_inspection_{index:03d}"
        pose = self._waypoint_pose(source_waypoint)
        waypoint = {
            "waypoint_id": waypoint_id,
            "frame_id": str(source_waypoint.get("frame_id") or "map"),
            "x": pose["x"],
            "y": pose["y"],
            "yaw": round(pose["yaw"] + 15.0, 3),
            "room_id": str(source_waypoint.get("room_id") or self._current_room_id()),
            "label": f"Generated inspection candidate {index}",
            "purpose": "target_inspection",
            "waypoint_source": "generated_target_inspection_candidate",
            "coverage_estimate": 0.0,
            "source_observation_id": str(detection.get("source_observation_id") or ""),
            "source_target_candidate_id": f"target_candidate_object_{_safe_anchor_id(handle)}",
            "source_object_id": handle,
            "verified_navigation": True,
            "candidate_provenance": {
                "source": "server_verified_standoff_from_visible_evidence",
                "source_waypoint_id": source_waypoint_id,
                "source_observation_id": str(detection.get("source_observation_id") or ""),
                "visible_candidate_state": str(detection.get("candidate_state") or ""),
                "backend_verification": "same_public_waypoint_standoff_pose",
            },
            "public_contract_note": (
                "Generated Target Inspection Candidate was produced by the server from "
                "public visible evidence and projected as a bounded waypoint for "
                "navigate_to_waypoint."
            ),
        }
        _assert_no_forbidden_agent_view_keys(waypoint)
        self._generated_inspection_waypoints[waypoint_id] = waypoint
        private_source = self._private_waypoint_for_public_waypoint(source_waypoint)
        self._private_waypoint_by_public_id[waypoint_id] = private_source
        return dict(waypoint)

    def _generated_inspection_waypoint_for_object(self, handle: str) -> dict[str, Any]:
        for waypoint in self._generated_inspection_waypoints.values():
            if str(waypoint.get("source_object_id") or "") == handle:
                return dict(waypoint)
        return {}

    def _internal_object_id(self, handle: str) -> str | None:
        return self._object_ids_by_handle.get(handle)

    def _new_unresolved_handle(self) -> str:
        return self._new_observed_handle()

    def _new_observed_handle(self) -> str:
        used = set(self._observed_handles_by_object_id.values()) | set(self._detections_by_handle)
        index = 1
        while True:
            handle = f"observed_{index:03d}"
            if handle not in used:
                return handle
            index += 1

    @staticmethod
    def _ok(tool: str, **payload: Any) -> dict[str, Any]:
        result = {"ok": True, "tool": tool, "status": "ok", **payload}
        _assert_no_forbidden_agent_view_keys(result)
        return result

    @staticmethod
    def _error(tool: str, error_reason: str, **payload: Any) -> dict[str, Any]:
        result = {
            "ok": False,
            "tool": tool,
            "status": "error",
            "error_reason": error_reason,
            **payload,
        }
        _assert_no_forbidden_agent_view_keys(result)
        return result

    def _semantic_order_error(
        self,
        tool: str,
        *,
        required_tool: str,
        recovery_hint: str,
        object_id: str | None = None,
        fixture_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "required_tool": required_tool,
            "semantic_loop_variant": SEMANTIC_LOOP_VARIANT,
            "recovery_hint": recovery_hint,
        }
        if object_id is not None:
            payload["object_id"] = object_id
        if fixture_id is not None:
            payload["fixture_id"] = fixture_id
            payload["receptacle_id"] = fixture_id
        return self._error(tool, "semantic_order", **payload)


def _target_candidate_type_for_waypoint(waypoint: dict[str, Any]) -> str:
    source = str(waypoint.get("waypoint_source") or "")
    if source == "generated_exploration_candidate":
        return "generated_exploration_candidate"
    if source == "generated_target_inspection_candidate":
        return "generated_target_inspection_candidate"
    return "public_inspection_waypoint"


def _runtime_map_producer_summary(
    observed_objects: list[dict[str, Any]],
    *,
    public_semantic_anchors: list[dict[str, Any]] | None = None,
    map_update_candidates: list[dict[str, Any]] | None = None,
    target_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    producers: dict[str, int] = {}
    for item in observed_objects:
        producer_type = str(item.get("producer_type") or "unknown")
        producers[producer_type] = producers.get(producer_type, 0) + 1
    anchors = public_semantic_anchors or []
    anchor_producers: dict[str, int] = {}
    for item in anchors:
        producer_type = str(item.get("producer_type") or "unknown")
        anchor_producers[producer_type] = anchor_producers.get(producer_type, 0) + 1
    return {
        "observed_object_count": len(observed_objects),
        "producer_types": producers,
        "public_semantic_anchor_count": len(anchors),
        "public_semantic_anchor_producer_types": anchor_producers,
        "target_candidate_count": len(target_candidates or []),
        "map_update_candidate_count": len(map_update_candidates or []),
    }


def _runtime_observed_confidence(
    detection: dict[str, Any],
    declaration: dict[str, Any],
) -> float:
    for key in ("visibility_confidence", "grounding_confidence", "confidence"):
        value = detection.get(key)
        if value is None:
            value = declaration.get(key)
        try:
            return round(float(value), 6)
        except (TypeError, ValueError):
            continue
    return 0.0


def _runtime_actionability(
    *,
    state: str,
    grounding_status: str,
    cleanup_recommended: bool,
) -> str:
    if state in {"held", "placed", "placed_closed", "stale", "skipped"}:
        return state
    if state in {"prior", "needs_confirm"}:
        return "needs_confirm"
    if grounding_status in {"ambiguous", "unresolved"}:
        return "needs_confirm"
    if cleanup_recommended and state in {"pending", "navigating_to_object"}:
        return "actionable"
    return state or "pending"


def _visual_grounding_evidence_for_candidate(
    candidate: dict[str, Any],
    *,
    fallback_image_bbox: Any = None,
    grounding_status: str = "",
) -> dict[str, Any]:
    image_region = candidate.get("image_region")
    if not image_region and candidate.get("image_bbox"):
        image_region = {"type": "bbox", "value": candidate.get("image_bbox")}
    image_region = _normalize_image_region(image_region)
    bbox = image_region.get("value") if image_region.get("type") == "bbox" else fallback_image_bbox
    if bbox is None:
        bbox = candidate.get("image_bbox")
    image_dimensions = candidate.get("image_dimensions") or {}
    review = _bbox_reviewability(bbox, image_dimensions=image_dimensions)
    if (
        review["reviewability_status"] != VISUAL_EVIDENCE_REVIEWABLE_STATUS
        and image_region.get("type") == "verbal_region"
        and str(candidate.get("producer_type") or "") == TEST_AGENT_PRODUCER
    ):
        review = {
            "reviewability_status": VISUAL_EVIDENCE_REVIEWABLE_STATUS,
            "reviewability_reason": "test_agent_verbal_region",
            "bbox_coordinate_space": "",
            "image_bbox": [],
        }
    pipeline = candidate.get("visual_grounding_pipeline") or {}
    evidence = {
        "schema": VISUAL_GROUNDING_EVIDENCE_SCHEMA,
        "camera_frame": "agent_facing_fpv",
        "source_observation_id": str(candidate.get("source_observation_id") or ""),
        "producer_type": str(candidate.get("producer_type") or ""),
        "producer_id": str(candidate.get("producer_id") or ""),
        "image_region": image_region,
        "image_bbox": review["image_bbox"],
        "bbox_coordinate_space": review["bbox_coordinate_space"],
        "reviewability_status": review["reviewability_status"],
        "reviewability_reason": review["reviewability_reason"],
        "grounding_status": str(grounding_status or candidate.get("grounding_status") or ""),
        "locality_status": str(candidate.get("locality_status") or ""),
        "actionability_status": "actionable"
        if review["reviewability_status"] == VISUAL_EVIDENCE_REVIEWABLE_STATUS
        else VISUAL_EVIDENCE_REQUIRED_ACTIONABILITY,
        "candidate_state": _candidate_state(
            {
                **candidate,
                "grounding_status": str(
                    grounding_status or candidate.get("grounding_status") or ""
                ),
                "reviewability_status": review["reviewability_status"],
            }
        ),
        "private_truth_included": False,
    }
    if candidate.get("visual_grounding_overlay"):
        evidence["visual_grounding_overlay"] = str(candidate["visual_grounding_overlay"])
    if pipeline:
        evidence["visual_grounding_pipeline_id"] = str(pipeline.get("pipeline_id") or "")
        evidence["visual_grounding_pipeline_status"] = str(pipeline.get("status") or "")
    _assert_no_forbidden_agent_view_keys(evidence)
    return evidence


def _bbox_reviewability(
    value: Any,
    *,
    image_dimensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    numbers = _numeric_bbox(value)
    if numbers is None:
        return {
            "reviewability_status": VISUAL_EVIDENCE_NOT_REVIEWABLE_STATUS,
            "reviewability_reason": "missing_bbox",
            "bbox_coordinate_space": "",
            "image_bbox": [],
        }
    x, y, width, height = numbers
    if width <= 0 or height <= 0:
        return {
            "reviewability_status": VISUAL_EVIDENCE_NOT_REVIEWABLE_STATUS,
            "reviewability_reason": "non_positive_bbox_extent",
            "bbox_coordinate_space": "",
            "image_bbox": numbers,
        }
    if x < 0 or y < 0:
        return {
            "reviewability_status": VISUAL_EVIDENCE_NOT_REVIEWABLE_STATUS,
            "reviewability_reason": "bbox_origin_outside_frame",
            "bbox_coordinate_space": "",
            "image_bbox": numbers,
        }
    if all(0.0 <= item <= 1.0 for item in numbers):
        if x + width <= 1.0 and y + height <= 1.0:
            return {
                "reviewability_status": VISUAL_EVIDENCE_REVIEWABLE_STATUS,
                "reviewability_reason": "normalized_bbox_inside_agent_fpv",
                "bbox_coordinate_space": "normalized_xywh",
                "image_bbox": numbers,
            }
        return {
            "reviewability_status": VISUAL_EVIDENCE_NOT_REVIEWABLE_STATUS,
            "reviewability_reason": "normalized_bbox_outside_frame",
            "bbox_coordinate_space": "normalized_xywh",
            "image_bbox": numbers,
        }
    dimensions = image_dimensions or {}
    frame_width = _positive_int(dimensions.get("width"))
    frame_height = _positive_int(dimensions.get("height"))
    if frame_width is not None and frame_height is not None:
        if x >= frame_width or y >= frame_height:
            return {
                "reviewability_status": VISUAL_EVIDENCE_NOT_REVIEWABLE_STATUS,
                "reviewability_reason": "pixel_bbox_outside_frame",
                "bbox_coordinate_space": "pixel_xywh",
                "image_bbox": numbers,
            }
    return {
        "reviewability_status": VISUAL_EVIDENCE_REVIEWABLE_STATUS,
        "reviewability_reason": "pixel_bbox_present_on_agent_fpv",
        "bbox_coordinate_space": "pixel_xywh",
        "image_bbox": numbers,
    }


def _numeric_bbox(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    numbers = [_float_or_none(item) for item in value]
    if any(number is None or not math.isfinite(number) for number in numbers):
        return None
    return [round(float(number), 6) for number in numbers if number is not None]


def _candidate_actionability_status(candidate: dict[str, Any]) -> str:
    declaration = candidate.get("model_declared_observation") or {}
    existing = str(
        candidate.get("actionability_status") or declaration.get("actionability_status") or ""
    )
    if existing == "already_handled":
        return existing
    grounding_status = str(
        candidate.get("grounding_status") or declaration.get("grounding_status") or "resolved"
    )
    if grounding_status in {"ambiguous", "unresolved"}:
        return "needs_clarification"
    evidence = candidate.get("visual_grounding_evidence")
    if not isinstance(evidence, dict) or not evidence:
        evidence = _visual_grounding_evidence_for_candidate(candidate)
    if evidence.get("reviewability_status") != VISUAL_EVIDENCE_REVIEWABLE_STATUS:
        return VISUAL_EVIDENCE_REQUIRED_ACTIONABILITY
    if existing and existing != VISUAL_EVIDENCE_REQUIRED_ACTIONABILITY:
        return existing
    return "actionable"


def _candidate_state(candidate: dict[str, Any]) -> str:
    declaration = candidate.get("model_declared_observation") or {}
    existing = str(candidate.get("candidate_state") or declaration.get("candidate_state") or "")
    if existing == "already_handled":
        return existing
    actionability_status = str(
        candidate.get("actionability_status") or declaration.get("actionability_status") or ""
    )
    if actionability_status == "already_handled":
        return "already_handled"
    if existing == CANDIDATE_STATE_VISUAL_SCAN_REQUIRED:
        return existing
    grounding_status = str(
        candidate.get("grounding_status") or declaration.get("grounding_status") or "resolved"
    )
    if grounding_status in {"ambiguous", "unresolved"}:
        return CANDIDATE_STATE_SEMANTIC
    evidence = candidate.get("visual_grounding_evidence")
    reviewability_status = (
        str(evidence.get("reviewability_status") or "")
        if isinstance(evidence, dict)
        else str(candidate.get("reviewability_status") or "")
    )
    if reviewability_status != VISUAL_EVIDENCE_REVIEWABLE_STATUS:
        return CANDIDATE_STATE_VISUAL_SCAN_REQUIRED
    if existing == CANDIDATE_STATE_NAVIGATION_AUTHORIZED:
        return existing
    cleanup_recommended = bool(candidate.get("cleanup_recommended"))
    candidate_fixture_id = str(candidate.get("candidate_fixture_id") or "")
    recommended_tool = str(candidate.get("recommended_tool") or "")
    if cleanup_recommended or (candidate_fixture_id and recommended_tool):
        return CANDIDATE_STATE_NAVIGATION_AUTHORIZED
    return CANDIDATE_STATE_VISUALLY_CONFIRMED


def _candidate_state_history(candidate_state: str) -> list[str]:
    state = str(candidate_state or "")
    ordered = [
        CANDIDATE_STATE_SEMANTIC,
        CANDIDATE_STATE_VISUAL_SCAN_REQUIRED,
        CANDIDATE_STATE_VISUALLY_CONFIRMED,
        CANDIDATE_STATE_NAVIGATION_AUTHORIZED,
    ]
    if state in ordered:
        return ordered[: ordered.index(state) + 1]
    if state == "already_handled":
        return ordered + ["already_handled"]
    return [CANDIDATE_STATE_SEMANTIC]


def _required_tool_for_candidate_state(candidate_state: str) -> str:
    if candidate_state == CANDIDATE_STATE_NAVIGATION_AUTHORIZED:
        return "navigate_to_object"
    if candidate_state == CANDIDATE_STATE_VISUALLY_CONFIRMED:
        return "navigate_to_object"
    if candidate_state == CANDIDATE_STATE_VISUAL_SCAN_REQUIRED:
        return "adjust_camera"
    return "observe"


def _synthetic_observation_id(handle: str, waypoint_id: Any) -> str:
    waypoint = str(waypoint_id or "")
    if waypoint:
        return f"visible_detection:{waypoint}:{handle}"
    return f"visible_detection:{handle}"


def _runtime_map_priors_from_snapshot(
    snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    priors = []
    for index, item in enumerate(snapshot.get("observed_objects") or [], start=1):
        if not isinstance(item, dict):
            continue
        prior_object_id = str(item.get("object_id") or f"prior_{index:03d}")
        prior = {
            "object_id": prior_object_id,
            "prior_row_id": f"prior_{index:03d}",
            "prior_object_id": prior_object_id,
            "snapshot_object_id": prior_object_id,
            "category": str(item.get("category") or ""),
            "room_id": str(item.get("room_id") or ""),
            "waypoint_id": str(item.get("waypoint_id") or ""),
            "source_fixture_id": str(item.get("source_fixture_id") or ""),
            "source_observation_id": str(item.get("source_observation_id") or ""),
            "image_region": item.get("image_region") or {},
            "producer_type": str(item.get("producer_type") or ""),
            "producer_id": str(item.get("producer_id") or ""),
            "confidence": _float_or_zero(item.get("confidence")),
            "freshness": "prior",
            "actionability": "needs_confirm",
            "state": "prior",
            "grounding_status": str(item.get("grounding_status") or "prior"),
            "candidate_fixture_id": str(item.get("candidate_fixture_id") or ""),
            "candidate_source": str(item.get("candidate_source") or "runtime_metric_map_snapshot"),
        }
        _assert_no_forbidden_agent_view_keys(prior)
        priors.append(prior)
    return priors


def _runtime_map_anchor_priors_from_snapshot(
    snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    anchors = []
    for index, item in enumerate(snapshot.get("public_semantic_anchors") or [], start=1):
        if not isinstance(item, dict):
            continue
        anchor = {
            "anchor_id": str(item.get("anchor_id") or f"prior_anchor_{index:03d}"),
            "prior_anchor_id": str(item.get("anchor_id") or f"prior_anchor_{index:03d}"),
            "anchor_type": str(item.get("anchor_type") or ""),
            "category": str(item.get("category") or ""),
            "label": str(item.get("label") or ""),
            "room_id": str(item.get("room_id") or ""),
            "waypoint_id": str(item.get("waypoint_id") or ""),
            "pose": dict(item.get("pose") or {}),
            "affordances": list(item.get("affordances") or []),
            "producer_type": str(item.get("producer_type") or ""),
            "producer_id": str(item.get("producer_id") or ""),
            "confidence": _float_or_zero(item.get("confidence")),
            "freshness": "prior",
            "actionability": str(item.get("actionability") or ""),
            "reachability_status": str(item.get("reachability_status") or ""),
            "classification_status": str(item.get("classification_status") or ""),
            "source_observation_id": str(item.get("source_observation_id") or ""),
            "promotion_status": "prior_runtime_snapshot",
            "evidence": dict(item.get("evidence") or {}),
        }
        _assert_no_forbidden_agent_view_keys(anchor)
        anchors.append(anchor)
    return anchors


def _runtime_map_room_priors_from_snapshot(
    snapshot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    rooms = []
    for item in snapshot.get("rooms") or []:
        if not isinstance(item, dict):
            continue
        room = _public_room_hint_payload(item)
        _assert_no_forbidden_agent_view_keys(room)
        rooms.append(room)
    return rooms


def infer_target_fixture_for_detection(
    detection: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> dict[str, Any] | None:
    direct_candidate = _target_fixture_from_detection_anchor(detection)
    if direct_candidate is not None:
        return direct_candidate
    fixture_candidates = [
        fixture
        for room in fixture_hints.get("rooms", [])
        for fixture in room.get("fixtures", [])
        if isinstance(fixture, dict)
    ]
    object_terms = {
        _norm(detection.get("category")),
        _norm(detection.get("name")),
    }
    for object_aliases, fixture_aliases in _OBJECT_CATEGORY_TARGETS:
        if not any(alias in term for alias in object_aliases for term in object_terms):
            continue
        for fixture_alias in fixture_aliases:
            match = _first_matching_fixture(fixture_candidates, fixture_alias)
            if match is not None:
                return match
    return None


def _target_fixture_from_detection_anchor(detection: dict[str, Any]) -> dict[str, Any] | None:
    fixture_id = str(detection.get("candidate_fixture_id") or "")
    if not fixture_id.startswith("anchor_fixture_"):
        return None
    category = str(detection.get("candidate_fixture_category") or "")
    tool = str(detection.get("recommended_tool") or "")
    affordances = ["observe", "place"]
    if tool == "place_inside" or _fixture_requires_open({"category": category}):
        affordances.append("place_inside")
    if _fixture_requires_open({"category": category}):
        affordances.extend(["open", "close"])
    waypoint_id = str(detection.get("waypoint_id") or "")
    return {
        "fixture_id": fixture_id,
        "receptacle_id": fixture_id,
        "category": category,
        "name": category or fixture_id,
        "room_id": str(detection.get("current_room_id") or ""),
        "affordances": affordances,
        "preferred_inspection_waypoint_id": waypoint_id,
        "preferred_manipulation_waypoint_id": waypoint_id,
        "public_fixture_source": "runtime_semantic_anchor",
    }


def forbidden_agent_view_keys() -> set[str]:
    return set(_FORBIDDEN_AGENT_VIEW_KEYS)


def cleanup_policy_trace_from_events(
    trace_events: list[dict[str, Any]],
    agent_view: dict[str, Any],
) -> dict[str, Any]:
    return _cleanup_policy_trace_from_events(
        trace_events,
        agent_view,
        schema=CLEANUP_POLICY_TRACE_SCHEMA,
        minimal_map_mode=MINIMAL_MAP_MODE,
    )


def real_robot_readiness_from_events(
    *,
    agent_view: dict[str, Any],
    trace_events: list[dict[str, Any]],
    robot_view_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    metric_map = agent_view.get("metric_map") or {}
    fixture_hints = agent_view.get("fixture_hints") or {}
    policy_view = agent_view.get("policy_view") or {}
    navigation_backends: dict[str, int] = {}
    pose_sources: dict[str, int] = {}
    for raw in trace_events:
        if raw.get("event") != "response":
            continue
        response = raw.get("response") if isinstance(raw.get("response"), dict) else {}
        backend = response.get("navigation_backend")
        if backend:
            navigation_backends[str(backend)] = navigation_backends.get(str(backend), 0) + 1
        pose_source = response.get("pose_source")
        if pose_source:
            pose_sources[str(pose_source)] = pose_sources.get(str(pose_source), 0) + 1
    report_only_count = sum(
        1 for step in robot_view_steps if (step.get("views") or {}).get("chase")
    )
    evidence = {
        "schema": REAL_ROBOT_READINESS_SCHEMA,
        "status": "simulation_semantic_not_real_robot_ready",
        "real_robot_ready": False,
        "map_bundle_schema": metric_map.get("schema", ""),
        "map_bundle_fields_present": _map_bundle_fields_present(metric_map),
        "pose_stamped_waypoints": _pose_stamped_waypoints_present(metric_map),
        "static_fixture_semantic_map": (
            fixture_hints.get("schema") == "static_fixture_semantic_map_v1"
            and fixture_hints.get("contains_runtime_observations") is False
        ),
        "policy_view_chase_excluded": policy_view.get("chase_camera_policy_input") is False,
        "report_only_simulation_view_count": report_only_count,
        "report_only_simulation_view_label": "report_only_simulation_view",
        "navigation_backend_summary": navigation_backends,
        "pose_source_summary": pose_sources,
        "semantic_navigation_only": set(navigation_backends)
        <= {
            API_SEMANTIC_PROVENANCE,
            SIM_COSTMAP_PLANNER,
        },
        "sim_costmap_route_validation": navigation_backends.get(SIM_COSTMAP_PLANNER, 0) > 0,
        "physical_navigation_pilot": False,
        "physical_cleanup_ready": False,
        "blocked_capabilities": [
            "nav2_action_backend",
            "live_ros_graph",
            "planner_backed_cleanup_primitives",
        ],
        "public_contract_note": (
            "This artifact aligns data boundaries with a real robot contract, but "
            "semantic simulator navigation remains labelled api_semantic."
        ),
    }
    evidence["readiness_sections_complete"] = bool(
        evidence["map_bundle_fields_present"]
        and evidence["pose_stamped_waypoints"]
        and evidence["static_fixture_semantic_map"]
        and evidence["policy_view_chase_excluded"]
        and navigation_backends
    )
    _assert_no_forbidden_agent_view_keys(evidence)
    return evidence


def _map_bundle_fields_present(metric_map: dict[str, Any]) -> bool:
    required = {
        "schema",
        "frame_id",
        "map_id",
        "map_version",
        "resolution_m",
        "origin",
        "width",
        "height",
        "occupancy_values",
        "map_bundle",
        "robot_pose",
        "inspection_waypoints",
    }
    return required <= set(metric_map)


def _pose_stamped_waypoints_present(metric_map: dict[str, Any]) -> bool:
    waypoints = metric_map.get("inspection_waypoints") or []
    required = {
        "waypoint_id",
        "frame_id",
        "x",
        "y",
        "yaw",
        "room_id",
        "label",
        "visited",
        "purpose",
    }
    return bool(waypoints) and all(required <= set(item) for item in waypoints)


def _fixtures_from_bundle_fixture_hints(fixture_hints: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}
    for room in fixture_hints.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        room_id = str(room.get("room_id") or "")
        room_label = str(room.get("room_label") or room_id)
        for raw_fixture in room.get("fixtures") or []:
            if not isinstance(raw_fixture, dict):
                continue
            fixture = dict(raw_fixture)
            fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
            if not fixture_id:
                continue
            fixture.setdefault("fixture_id", fixture_id)
            fixture.setdefault("receptacle_id", fixture_id)
            fixture.setdefault("room_id", room_id)
            fixture.setdefault("room_area", room_label or room_id)
            fixture.setdefault("kind", "receptacle")
            fixture.setdefault("name", fixture_id)
            fixture.setdefault("category", fixture.get("name", fixture_id))
            fixtures[fixture_id] = fixture
    return fixtures


def _scene_index_public_fixture_overlay(
    *,
    backend: Any,
    scenario: CleanupScenario,
    existing_fixtures: dict[str, dict[str, Any]],
    fallback_waypoint_id: str,
) -> dict[str, dict[str, Any]]:
    if str(getattr(backend, "scenario_source", "")) != "isaac_scene_index":
        return {}

    overlay: dict[str, dict[str, Any]] = {}
    for receptacle in scenario.receptacles:
        fixture_id = str(receptacle.receptacle_id)
        if not fixture_id:
            continue
        fixture = dict(existing_fixtures.get(fixture_id, {}))
        fixture["fixture_id"] = fixture_id
        fixture["receptacle_id"] = fixture_id
        fixture["category"] = str(
            receptacle.category or fixture.get("category") or receptacle.name or fixture_id
        )
        fixture["name"] = str(receptacle.name or fixture.get("name") or fixture_id)
        fixture.setdefault("kind", receptacle.kind)
        fixture.setdefault("room_area", receptacle.room_area)
        fixture.setdefault("room_id", _room_id(str(receptacle.room_area)))
        fixture.setdefault("preferred_inspection_waypoint_id", fallback_waypoint_id)
        fixture.setdefault("preferred_manipulation_waypoint_id", fallback_waypoint_id)
        fixture["public_fixture_source"] = "isaac_scene_index"
        overlay[fixture_id] = fixture
    return overlay


def _metric_map_room_payload(room: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "room_id": room["room_id"],
        "room_label": room["room_label"],
        "fixture_count": len(room["fixture_ids"]),
        "polygon": room.get("polygon", []),
    }
    if isinstance(room.get("scene_room_outline"), dict):
        payload["scene_room_outline"] = dict(room["scene_room_outline"])
    return payload


def _public_room_hints_from_metric_map(
    metric_map: dict[str, Any],
    *,
    fallback_rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_rooms = [item for item in metric_map.get("rooms") or [] if isinstance(item, dict)] or [
        item for item in fallback_rooms if isinstance(item, dict)
    ]
    rooms: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_room in source_rooms:
        room = _public_room_hint_payload(raw_room)
        room_id = str(room.get("room_id") or "")
        if not room_id or room_id in seen:
            continue
        rooms.append(room)
        seen.add(room_id)
    return rooms


def _public_room_hint_payload(room: dict[str, Any]) -> dict[str, Any]:
    room_id = str(room.get("room_id") or _room_id(str(room.get("room_label") or "room_area")))
    room_label = str(room.get("room_label") or room_id.replace("_", " "))
    polygon = [dict(point) for point in room.get("polygon") or [] if isinstance(point, dict)]
    map_center = (
        dict(room.get("map_center") or {})
        if isinstance(room.get("map_center"), dict)
        else _polygon_center_world(polygon)
    )
    payload: dict[str, Any] = {
        "room_id": room_id,
        "room_label": room_label,
        "category": str(room.get("category") or _room_category_from_label(room_label, room_id)),
        "polygon": polygon,
        "map_center": map_center,
        "public_room_source": "base_navigation_map",
    }
    if isinstance(room.get("scene_room_outline"), dict):
        payload["scene_room_outline"] = dict(room["scene_room_outline"])
    return payload


def _room_category_hints_from_public_rooms(
    rooms: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    waypoint_by_room: dict[str, str] = {}
    for waypoint in waypoints:
        room_id = str(waypoint.get("room_id") or "")
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if room_id and waypoint_id:
            waypoint_by_room.setdefault(room_id, waypoint_id)
    hints = []
    for room in rooms:
        room_id = str(room.get("room_id") or "")
        room_label = str(room.get("room_label") or room_id.replace("_", " "))
        if not room_id:
            continue
        hint = {
            "anchor_type": "room_area",
            "category": str(room.get("category") or _room_category_from_label(room_label, room_id)),
            "label": room_label,
            "room_id": room_id,
            "room_label": room_label,
            "waypoint_id": waypoint_by_room.get(room_id, ""),
            "affordances": ["navigate", "observe"],
            "classification_status": "map_prior",
            "confidence": 0.8,
            "aliases": [room_id, room_label],
            "producer_type": "base_navigation_map",
        }
        _assert_no_forbidden_agent_view_keys(hint)
        hints.append(hint)
    return hints


def _merge_public_rooms(
    base_rooms: list[dict[str, Any]],
    prior_rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_room in [*base_rooms, *prior_rooms]:
        if not isinstance(raw_room, dict):
            continue
        room = _public_room_hint_payload(raw_room)
        room_id = str(room.get("room_id") or "")
        if not room_id or room_id in seen:
            continue
        merged.append(room)
        seen.add(room_id)
    return merged


def _public_driveable_ways(
    metric_map: dict[str, Any],
    rooms: list[dict[str, Any]],
) -> list[dict[str, str]]:
    public_room_ids = {str(room.get("room_id") or "") for room in rooms}
    ways = []
    for way in metric_map.get("driveable_ways") or []:
        if not isinstance(way, dict):
            continue
        start = str(way.get("from_room_id") or "")
        goal = str(way.get("to_room_id") or "")
        if start in public_room_ids and goal in public_room_ids:
            ways.append({"from_room_id": start, "to_room_id": goal})
    if ways:
        return ways
    return _driveable_ways(rooms)


def _room_label_by_id(rooms: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(room.get("room_id") or ""): str(room.get("room_label") or "")
        for room in rooms
        if str(room.get("room_id") or "")
    }


def _room_category_from_label(room_label: str, room_id: str = "") -> str:
    text = f"{room_label} {room_id}".lower()
    if any(term in text for term in ("kitchen", "dining", "bar", "counter", "厨房", "吧台")):
        return "kitchen"
    if any(term in text for term in ("living", "sofa", "lounge", "客厅", "沙发")):
        return "living_room"
    if any(term in text for term in ("storage", "store", "utility", "储藏", "库房")):
        return "storage_room"
    if any(term in text for term in ("meeting", "conference", "会议")):
        return "meeting_room"
    if any(term in text for term in ("bed", "卧室")):
        return "bedroom"
    if any(term in text for term in ("bath", "toilet", "卫生间")):
        return "bathroom"
    return "room_area"


def _scene_room_outlines_from_backend(backend: Any) -> list[dict[str, Any]]:
    if str(getattr(backend, "scenario_source", "")) != "isaac_scene_index":
        return []
    outlines = getattr(backend, "room_outlines", None)
    if outlines is None:
        diagnostics = getattr(backend, "scene_index_diagnostics", {})
        if isinstance(diagnostics, dict):
            outlines = diagnostics.get("room_outlines")
    return [
        dict(item)
        for item in (outlines or [])
        if isinstance(item, dict) and item.get("center") and item.get("half_extents")
    ]


def _scene_index_fixture_pose(backend: Any, fixture_id: str) -> list[float] | None:
    receptacle_index = getattr(backend, "receptacle_index", {})
    if not isinstance(receptacle_index, dict):
        return None
    entry = receptacle_index.get(fixture_id)
    if not isinstance(entry, dict):
        return None
    support_pose = entry.get("support_pose")
    if isinstance(support_pose, dict):
        position = support_pose.get("position")
        pose = _vec3(position)
        if pose is not None:
            return pose
    bounds = entry.get("usd_world_bounds")
    if isinstance(bounds, dict):
        pose = _vec3(bounds.get("center"))
        if pose is not None:
            return pose
    return None


def _room_outline_by_id(
    room_outlines: list[dict[str, Any]],
    room_id: str,
) -> dict[str, Any] | None:
    return next((item for item in room_outlines if str(item.get("room_id") or "") == room_id), None)


def _fixture_hints_with_scene_index_overlay(
    rooms: list[Any],
    overlay_fixtures: dict[str, dict[str, Any]],
    *,
    fixture_hint_mode: str,
) -> list[dict[str, Any]]:
    overlay_room = {
        "room_id": "isaac_scene_index",
        "room_label": "Isaac scene index fixtures",
        "fixture_source": "isaac_scene_index",
        "fixtures": [
            _scene_index_fixture_hint_row(fixture_id, fixture, fixture_hint_mode)
            for fixture_id, fixture in sorted(overlay_fixtures.items())
        ],
    }
    return [overlay_room] + [dict(room) for room in rooms if isinstance(room, dict)]


def _scene_index_fixture_hint_row(
    fixture_id: str,
    fixture: dict[str, Any],
    fixture_hint_mode: str,
) -> dict[str, Any]:
    pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
    return {
        "fixture_id": fixture_id,
        "category": str(fixture.get("category") or fixture.get("name") or fixture_id),
        "name": str(fixture.get("name") or fixture_id),
        "room_id": "isaac_scene_index",
        "affordances": _fixture_affordances(fixture),
        "footprint": _fixture_footprint(fixture_id),
        "pose": {
            "frame_id": str(pose.get("frame_id") or "map"),
            "x": float(pose.get("x", 0.0)),
            "y": float(pose.get("y", 0.0)),
            "yaw": float(pose.get("yaw", 0.0)),
        },
        "manipulation_frame": f"{fixture_id}_manipulation",
        "preferred_inspection_waypoint_id": str(
            fixture.get("preferred_inspection_waypoint_id") or ""
        ),
        "preferred_manipulation_waypoint_id": str(
            fixture.get("preferred_manipulation_waypoint_id") or ""
        ),
        "position_detail": fixture_hint_mode,
        "public_fixture_source": "isaac_scene_index",
    }


def _first_waypoint_id(waypoints: list[dict[str, Any]]) -> str:
    if not waypoints:
        return ""
    return str(waypoints[0].get("waypoint_id") or "")


def _rooms_from_bundle_projection(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> list[dict[str, Any]]:
    fixture_ids_by_room: dict[str, list[str]] = defaultdict(list)
    for room in fixture_hints.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        room_id = str(room.get("room_id") or "")
        for fixture in room.get("fixtures") or []:
            if not isinstance(fixture, dict):
                continue
            fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
            if fixture_id:
                fixture_ids_by_room[room_id].append(fixture_id)

    rooms = []
    for raw_room in metric_map.get("rooms") or []:
        if not isinstance(raw_room, dict):
            continue
        room = dict(raw_room)
        room_id = str(room.get("room_id") or "")
        room["fixture_ids"] = sorted(fixture_ids_by_room.get(room_id, []))
        room.setdefault("room_label", room_id.replace("_", " "))
        room.setdefault("map_center", _polygon_center_world(room.get("polygon") or []))
        rooms.append(room)
    return rooms


def _inspection_waypoints_from_bundle_projection(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> list[dict[str, Any]]:
    fixture_waypoint_ids: dict[str, list[str]] = defaultdict(list)
    room_fixture_ids: dict[str, list[str]] = defaultdict(list)
    for room in fixture_hints.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        room_id = str(room.get("room_id") or "")
        for fixture in room.get("fixtures") or []:
            if not isinstance(fixture, dict):
                continue
            fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
            if not fixture_id:
                continue
            room_fixture_ids[room_id].append(fixture_id)
            for key in ("preferred_inspection_waypoint_id", "preferred_manipulation_waypoint_id"):
                waypoint_id = str(fixture.get(key) or "")
                if waypoint_id and fixture_id not in fixture_waypoint_ids[waypoint_id]:
                    fixture_waypoint_ids[waypoint_id].append(fixture_id)

    waypoints = []
    frame_id = str(metric_map.get("frame_id") or "map")
    for raw_waypoint in metric_map.get("inspection_waypoints") or []:
        if not isinstance(raw_waypoint, dict):
            continue
        waypoint = dict(raw_waypoint)
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        room_id = str(waypoint.get("room_id") or "")
        waypoint.setdefault("frame_id", frame_id)
        waypoint["visited"] = False
        if not waypoint.get("fixture_ids"):
            waypoint["fixture_ids"] = sorted(
                fixture_waypoint_ids.get(waypoint_id) or room_fixture_ids.get(room_id, [])
            )
        waypoints.append(waypoint)
    return waypoints


def _minimal_generated_exploration_waypoints(
    metric_map: dict[str, Any],
    *,
    fallback_waypoints: list[dict[str, Any]],
    public_rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_waypoints = [
        item for item in metric_map.get("inspection_waypoints") or [] if isinstance(item, dict)
    ] or [item for item in fallback_waypoints if isinstance(item, dict)]
    frame_id = str(metric_map.get("frame_id") or "map")
    room_labels = _room_label_by_id(public_rooms)
    generated = []
    for index, source in enumerate(source_waypoints, start=1):
        waypoint_id = f"generated_exploration_{index:03d}"
        room_id = str(source.get("room_id") or "generated_area")
        room_label = str(room_labels.get(room_id) or source.get("room_label") or "")
        generated.append(
            {
                "waypoint_id": waypoint_id,
                "frame_id": frame_id,
                "x": float(source.get("x", 0.0)),
                "y": float(source.get("y", 0.0)),
                "yaw": float(source.get("yaw", 0.0)),
                "room_id": room_id,
                "room_label": room_label,
                "label": f"Generated exploration candidate {index}",
                "purpose": "minimal_map_exploration",
                "waypoint_source": "generated_exploration_candidate",
                "coverage_estimate": round(1.0 / max(len(source_waypoints), 1), 6),
                "candidate_provenance": {
                    "source": "public_occupancy_free_space",
                    "candidate_index": index,
                    "source_pose": "free_space_sample",
                    "source_room_hidden": False,
                    "source_room_label_available": bool(room_label),
                    "source_fixtures_hidden": True,
                    "source_waypoint_hidden": True,
                },
            }
        )
    return generated


def _private_waypoint_map_for_generated_candidates(
    generated_waypoints: list[dict[str, Any]],
    private_waypoints: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result = {}
    for generated, private in zip(generated_waypoints, private_waypoints, strict=False):
        result[str(generated.get("waypoint_id") or "")] = private
    return result


def _polygon_center_world(polygon: list[Any]) -> dict[str, float]:
    points = [point for point in polygon if isinstance(point, dict)]
    if not points:
        return {"x": 0.0, "y": 0.0}
    return {
        "x": round(sum(float(point.get("x", 0.0)) for point in points) / len(points), 3),
        "y": round(sum(float(point.get("y", 0.0)) for point in points) / len(points), 3),
    }


def _rooms_from_fixtures(fixtures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_room: dict[str, list[str]] = defaultdict(list)
    labels: dict[str, str] = {}
    for fixture_id, fixture in fixtures.items():
        raw_room = str(fixture.get("room_area", "unknown"))
        room_id = _room_id(raw_room)
        by_room[room_id].append(fixture_id)
        labels[room_id] = raw_room.replace("_", " ")
    rooms = []
    for index, (room_id, fixture_ids) in enumerate(sorted(by_room.items())):
        outline = _room_outline_by_id_from_fixtures(fixtures, room_id, fixture_ids)
        if outline is not None:
            polygon = _polygon_from_room_outline(outline)
            center_xy = _room_outline_center(outline)
            room_label = str(outline.get("label") or labels[room_id])
            map_center = {"x": center_xy[0], "y": center_xy[1]}
        else:
            x0 = float(index * 3)
            polygon = [
                {"x": x0, "y": 0.0},
                {"x": x0 + 2.0, "y": 0.0},
                {"x": x0 + 2.0, "y": 2.0},
                {"x": x0, "y": 2.0},
            ]
            room_label = labels[room_id]
            map_center = {"x": x0 + 1.0, "y": 1.0}
        rooms.append(
            {
                "room_id": room_id,
                "room_label": room_label,
                "fixture_ids": sorted(fixture_ids),
                "polygon": polygon,
                "map_center": map_center,
                "fixture_navigation_obstacles": _fixture_navigation_obstacles(
                    fixtures,
                    fixture_ids,
                ),
                **_room_outline_metadata(outline),
            }
        )
    return rooms


def _inspection_waypoints(rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    waypoints = []
    for room in rooms:
        fixture_ids = list(room["fixture_ids"])
        groups = _split_fixture_groups(fixture_ids)
        slots = _waypoint_slots_for_room(room, len(groups))
        for index, group in enumerate(groups, start=1):
            x, y = slots[index - 1]
            waypoints.append(
                {
                    "waypoint_id": f"{room['room_id']}_scan_{index}",
                    "room_id": room["room_id"],
                    "label": f"{room['room_label']} scan {index}",
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "yaw": 0.0,
                    "fixture_ids": group,
                    "purpose": "fixture_coverage",
                    "waypoint_source": "static_map_coverage",
                    "coverage_estimate": round(1.0 / max(len(groups), 1), 2),
                }
            )
    return waypoints


def _room_outline_by_id_from_fixtures(
    fixtures: dict[str, dict[str, Any]],
    room_id: str,
    fixture_ids: list[str],
) -> dict[str, Any] | None:
    for fixture_id in fixture_ids:
        outline = fixtures.get(fixture_id, {}).get("scene_room_outline")
        if isinstance(outline, dict) and str(outline.get("room_id") or "") == room_id:
            return dict(outline)
    return None


def _polygon_from_room_outline(outline: dict[str, Any]) -> list[dict[str, float]]:
    center = _vec2(outline.get("center"))
    half_extents = _vec2(outline.get("half_extents"))
    if center is None or half_extents is None:
        return []
    cx, cy = center
    hx, hy = abs(half_extents[0]), abs(half_extents[1])
    return [
        {"x": round(cx - hx, 6), "y": round(cy - hy, 6)},
        {"x": round(cx + hx, 6), "y": round(cy - hy, 6)},
        {"x": round(cx + hx, 6), "y": round(cy + hy, 6)},
        {"x": round(cx - hx, 6), "y": round(cy + hy, 6)},
    ]


def _room_outline_center(outline: dict[str, Any]) -> tuple[float, float]:
    center = _vec2(outline.get("center"))
    if center is None:
        return (0.0, 0.0)
    return (round(center[0], 6), round(center[1], 6))


def _room_outline_metadata(outline: dict[str, Any] | None) -> dict[str, Any]:
    if outline is None:
        return {}
    return {
        "scene_room_outline": {
            "room_id": str(outline.get("room_id") or ""),
            "center": list(_room_outline_center(outline)),
            "half_extents": list(_vec2(outline.get("half_extents")) or (0.0, 0.0)),
            "provenance": str(outline.get("provenance") or "scene_room_outline"),
            "usd_prim_path": str(outline.get("usd_prim_path") or ""),
        }
    }


def _room_polygon_bounds(room: dict[str, Any] | None) -> dict[str, float] | None:
    if room is None:
        return None
    polygon = room.get("polygon") or []
    xs = [float(point.get("x", 0.0)) for point in polygon if isinstance(point, dict)]
    ys = [float(point.get("y", 0.0)) for point in polygon if isinstance(point, dict)]
    if not xs or not ys:
        center = room.get("map_center") or {}
        if "x" not in center or "y" not in center:
            return None
        x = float(center.get("x", 0.0))
        y = float(center.get("y", 0.0))
        return {"min_x": x - 1.0, "max_x": x + 1.0, "min_y": y - 1.0, "max_y": y + 1.0}
    return {
        "min_x": round(min(xs), 6),
        "max_x": round(max(xs), 6),
        "min_y": round(min(ys), 6),
        "max_y": round(max(ys), 6),
    }


def _waypoint_slots_for_room(
    room: dict[str, Any],
    count: int,
) -> list[tuple[float, float]]:
    count = max(1, int(count))
    polygon = room.get("polygon") or []
    xs = [float(point.get("x", 0.0)) for point in polygon if isinstance(point, dict)]
    ys = [float(point.get("y", 0.0)) for point in polygon if isinstance(point, dict)]
    if not xs or not ys:
        center = room.get("map_center") or {}
        x = float(center.get("x", 0.0))
        y = float(center.get("y", 0.0))
        return [(x, y + index * 0.45) for index in range(count)]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    center = room.get("map_center") or {}
    x = float(center.get("x", (min_x + max_x) / 2.0))
    y = float(center.get("y", (min_y + max_y) / 2.0))
    if isinstance(room.get("scene_room_outline"), dict):
        return _scene_outline_waypoint_slots_for_room(
            room,
            count=count,
            center=(x, y),
            bounds=(min_x, max_x, min_y, max_y),
        )
    if count == 1:
        return [(round(x, 3), round(y, 3))]
    margin = min(0.75, max((max_y - min_y) * 0.15, 0.25))
    start_y = min_y + margin
    end_y = max_y - margin
    if end_y < start_y:
        start_y = end_y = y
    step = (end_y - start_y) / max(count - 1, 1)
    return [(round(x, 3), round(start_y + step * index, 3)) for index in range(count)]


def _scene_outline_waypoint_slots_for_room(
    room: dict[str, Any],
    *,
    count: int,
    center: tuple[float, float],
    bounds: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    min_x, max_x, min_y, max_y = bounds
    width = max_x - min_x
    depth = max_y - min_y
    radius = min(0.8, max(min(width, depth) * 0.12, 0.35))
    candidates = _scene_outline_waypoint_candidates(center, radius)
    obstacles = [
        item for item in room.get("fixture_navigation_obstacles") or [] if isinstance(item, dict)
    ]
    slots: list[tuple[float, float]] = []
    for raw_x, raw_y in candidates:
        x = _clamp(raw_x, min_x + 0.35, max_x - 0.35)
        y = _clamp(raw_y, min_y + 0.35, max_y - 0.35)
        if _point_overlaps_fixture_obstacle(x, y, obstacles):
            continue
        point = (round(x, 3), round(y, 3))
        if point not in slots:
            slots.append(point)
        if len(slots) >= count:
            return slots
    fallback = (round(center[0], 3), round(center[1], 3))
    if not slots:
        slots.append(fallback)
    while len(slots) < count:
        slots.append(slots[len(slots) % len(slots)])
    return slots[:count]


def _scene_outline_waypoint_candidates(
    center: tuple[float, float],
    radius: float,
) -> list[tuple[float, float]]:
    cx, cy = center
    return [
        (cx, cy),
        (cx, cy - radius),
        (cx, cy + radius),
        (cx - radius, cy),
        (cx + radius, cy),
        (cx - radius, cy - radius),
        (cx + radius, cy - radius),
        (cx - radius, cy + radius),
        (cx + radius, cy + radius),
        (cx, cy - radius * 1.6),
        (cx, cy + radius * 1.6),
        (cx - radius * 1.6, cy),
        (cx + radius * 1.6, cy),
    ]


def _fixture_navigation_obstacles(
    fixtures: dict[str, dict[str, Any]],
    fixture_ids: list[str],
) -> list[dict[str, float]]:
    obstacles = []
    for fixture_id in fixture_ids:
        fixture = fixtures.get(fixture_id, {})
        pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
        if not pose:
            continue
        footprint = _fixture_footprint(fixture_id)
        obstacles.append(
            {
                "x": float(pose.get("x", 0.0)),
                "y": float(pose.get("y", 0.0)),
                "half_width": float(footprint.get("width_m") or 0.45) / 2.0,
                "half_depth": float(footprint.get("depth_m") or 0.35) / 2.0,
            }
        )
    return obstacles


def _point_overlaps_fixture_obstacle(
    x: float,
    y: float,
    obstacles: list[dict[str, float]],
) -> bool:
    clearance_m = 0.2
    for obstacle in obstacles:
        if (
            abs(x - obstacle["x"]) <= obstacle["half_width"] + clearance_m
            and abs(y - obstacle["y"]) <= obstacle["half_depth"] + clearance_m
        ):
            return True
    return False


def _split_fixture_groups(fixture_ids: list[str]) -> list[list[str]]:
    if len(fixture_ids) <= 1:
        return [fixture_ids, fixture_ids]
    return [fixture_ids[::2], fixture_ids[1::2]]


def _driveable_ways(rooms: list[dict[str, Any]]) -> list[dict[str, str]]:
    ways = []
    for previous, current in zip(rooms, rooms[1:]):
        ways.append(
            {
                "from_room_id": str(previous["room_id"]),
                "to_room_id": str(current["room_id"]),
                "kind": "doorway",
            }
        )
    return ways


def _fixture_affordances(fixture: dict[str, Any]) -> list[str]:
    affordances = ["place"]
    if _fixture_requires_open(fixture):
        affordances.extend(["open", "place_inside", "close"])
    elif _fixture_is_open_container(fixture):
        affordances.append("place_inside")
    return affordances


def _recommended_place_tool(fixture_id: str, fixtures: dict[str, dict[str, Any]]) -> str:
    fixture = fixtures.get(fixture_id, {})
    return "place_inside" if _fixture_prefers_inside(fixture) else "place"


def _public_destination_policy_for_category(category: Any) -> dict[str, Any]:
    category_norm = _norm(category)
    preferred: tuple[str, ...] = ()
    for object_aliases, fixture_aliases in _OBJECT_CATEGORY_TARGETS:
        if any(_norm(alias) and _norm(alias) in category_norm for alias in object_aliases):
            preferred = fixture_aliases
            break
    if not preferred:
        preferred = (
            "countertop",
            "table",
            "desk",
        )
    normalized = [_normalize_fixture_category_label(item) for item in preferred]
    normalized = [
        item for index, item in enumerate(normalized) if item and item not in normalized[:index]
    ]
    placement_tool_by_category = {
        item: _public_destination_policy_tool_for_fixture_category(item) for item in normalized
    }
    placement_tool = (
        placement_tool_by_category.get(normalized[0], "place") if normalized else "place"
    )
    return {
        "schema": "public_cleanup_destination_policy_v1",
        "source": "public_category_fixture_affordance",
        "preferred_fixture_categories": normalized,
        "acceptable_fixture_categories": normalized,
        "placement_tool": placement_tool,
        "placement_tool_by_fixture_category": placement_tool_by_category,
        "requires_public_anchor_selection": True,
        "private_truth_included": False,
        "instruction": (
            "Select a public semantic anchor or fixture whose category matches one of "
            "preferred_fixture_categories; do not infer or request private destination ids."
        ),
    }


def _public_destination_policy_tool_for_fixture_category(category: Any) -> str:
    return "place_inside" if _norm(category) in _INSIDE_DESTINATION_CATEGORY_TERMS else "place"


def _normalize_fixture_category_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    compact = _norm(text)
    aliases = {
        "tvstand": "tvstand",
        "tv stand": "tvstand",
        "shelvingunit": "shelvingunit",
        "shelving unit": "shelvingunit",
        "book shelf": "bookshelf",
        "laundry hamper": "laundryhamper",
        "toy bin": "toybin",
    }
    if text in aliases:
        return aliases[text]
    if compact in aliases:
        return aliases[compact]
    return compact or text


def _fixture_footprint(fixture_id: str) -> dict[str, Any]:
    suffix = sum(ord(ch) for ch in fixture_id) % 7
    width = round(0.45 + suffix * 0.03, 3)
    depth = round(0.35 + suffix * 0.02, 3)
    return {"shape": "rectangle", "width_m": width, "depth_m": depth}


def _fixture_requires_open(fixture: dict[str, Any]) -> bool:
    text = _fixture_text(fixture)
    return "fridge" in text or "refrigerator" in text


def _fixture_prefers_inside(fixture: dict[str, Any]) -> bool:
    return _fixture_requires_open(fixture) or _fixture_is_open_container(fixture)


def _fixture_is_open_container(fixture: dict[str, Any]) -> bool:
    text = _fixture_text(fixture)
    return any(term in text for term in ("shelvingunit", "bookshelf", "bookcase", "shelf"))


def _semantic_anchor_type_for_fixture(fixture: dict[str, Any]) -> str:
    text = _fixture_text(fixture)
    if any(
        term in text
        for term in (
            "sink",
            "fridge",
            "refrigerator",
            "cabinet",
            "drawer",
            "hamper",
            "bin",
            "shelvingunit",
            "bookshelf",
            "bookcase",
            "shelf",
        )
    ):
        return "receptacle"
    if any(term in text for term in ("table", "counter", "desk", "stand", "sofa", "bed")):
        return "surface"
    return "fixture"


def _is_place_anchor(anchor: dict[str, Any]) -> bool:
    actionability = str(anchor.get("actionability") or "actionable")
    if actionability != "actionable":
        return False
    anchor_type = str(anchor.get("anchor_type") or "")
    if anchor_type not in {"surface", "receptacle", "fixture"}:
        return False
    affordances = {str(item).lower() for item in anchor.get("affordances") or []}
    return bool({"place", "place_inside", "open"}.intersection(affordances))


def _anchor_affordances_for_fixture(fixture: dict[str, Any]) -> list[str]:
    affordances = ["observe"]
    for affordance in _fixture_affordances(fixture):
        if affordance not in affordances:
            affordances.append(affordance)
    return affordances


def _fixture_text(fixture: dict[str, Any]) -> str:
    return f"{fixture.get('name', '')} {fixture.get('category', '')}".lower()


def _first_fixture_for_waypoint(waypoint: dict[str, Any]) -> str | None:
    fixture_ids = waypoint.get("fixture_ids") or []
    return str(fixture_ids[0]) if fixture_ids else None


def _first_matching_fixture(
    fixtures: list[dict[str, Any]],
    alias: str,
) -> dict[str, Any] | None:
    alias_norm = _norm(alias)
    for fixture in fixtures:
        text = _norm(
            " ".join(str(fixture.get(key, "")) for key in ("fixture_id", "category", "name"))
        )
        if alias_norm in text:
            return fixture
    return None


def _location_relation(object_id: str, backend: Any) -> str:
    containment = getattr(backend, "_containment", {})
    relation = containment.get(object_id, {}).get("location_relation")
    return str(relation or "on")


def _visibility_confidence(handle: str) -> float:
    suffix = int(handle.rsplit("_", 1)[-1])
    return round(0.78 + (suffix % 5) * 0.03, 2)


def _image_bbox(handle: str) -> list[int]:
    suffix = int(handle.rsplit("_", 1)[-1])
    return [72 + suffix * 9, 58 + suffix * 7, 42, 31]


def _safe_anchor_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")
    return safe or "unknown"


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or_zero(value: Any) -> float:
    number = _float_or_none(value)
    return number if number is not None else 0.0


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_image_region(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        region_type = str(value.get("type") or "verbal_region")
        raw_region_value = value.get("value")
    else:
        region_type = "verbal_region"
        raw_region_value = str(value or "unspecified")
    if region_type == "bbox" and isinstance(raw_region_value, (list, tuple)):
        numbers = [_float_or_none(item) for item in raw_region_value[:4]]
        if len(numbers) == 4 and all(number is not None for number in numbers):
            return {"type": "bbox", "value": numbers}
    if region_type == "point" and isinstance(raw_region_value, (list, tuple)):
        numbers = [_float_or_none(item) for item in raw_region_value[:2]]
        if len(numbers) == 2 and all(number is not None for number in numbers):
            return {"type": "point", "value": numbers}
    return {"type": "verbal_region", "value": str(raw_region_value or "unspecified")}


def _manual_visual_grounding_pipeline(
    *,
    candidate_count: int,
    producer_type: str,
    producer_id: str,
) -> dict[str, Any]:
    if producer_type == SIMULATED_CAMERA_MODEL_PROVENANCE:
        return sim_visual_grounding_pipeline(candidate_count=candidate_count)
    return {
        "schema": "visual_grounding_pipeline_v1",
        "pipeline_id": "manual",
        "status": "ok",
        "stages": [
            {
                "stage": "manual_declaration",
                "producer_id": producer_id,
                "model_id": producer_type,
                "status": "ok",
                "latency_ms": 0,
            }
        ],
        "candidate_count": candidate_count,
        "unresolved_count": 0,
        "duplicate_rate": 0.0,
    }


def _average_duplicate_rate(events: list[dict[str, Any]]) -> float:
    rates = []
    for item in events:
        pipeline = item.get("visual_grounding_pipeline") or {}
        rate = _float_or_none(pipeline.get("duplicate_rate"))
        if rate is not None:
            rates.append(rate)
    if not rates:
        return 0.0
    return round(sum(rates) / len(rates), 6)


def _visual_candidate_validation_error(
    candidate: Any,
    *,
    require_target_fixture_id: bool = True,
    map_mode: str = MINIMAL_MAP_MODE,
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    producer_type: str = "",
) -> dict[str, str] | None:
    if not isinstance(candidate, dict):
        return {"field": "candidate", "reason": "candidate must be an object"}
    for field in ("category", "evidence_note"):
        if not str(candidate.get(field) or "").strip():
            return {"field": field, "reason": f"{field} is required"}
    target_fixture_id = str(candidate.get("target_fixture_id") or "").strip()
    if (
        require_target_fixture_id
        and str(candidate.get("producer_type") or "") != EXTERNAL_VISUAL_GROUNDING_PROVENANCE
        and not target_fixture_id
    ):
        return {"field": "target_fixture_id", "reason": "target_fixture_id is required"}
    region_error = _image_region_validation_error(candidate.get("image_region"))
    if region_error is not None:
        return region_error
    if (
        map_mode == MINIMAL_MAP_MODE
        and perception_mode == RAW_FPV_ONLY_MODE
        and str(producer_type or "") == MAIN_CLEANUP_AGENT_PRODUCER
        and target_fixture_id
    ):
        return {
            "field": "target_fixture_id",
            "reason": (
                "target_fixture_id must be omitted in minimal map RAW_FPV; use the "
                "candidate_fixture_id returned by navigate_to_visual_candidate"
            ),
        }
    return None


def _image_region_validation_error(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        if str(value or "").strip():
            return None
        return {"field": "image_region", "reason": "image_region is required"}
    region_type = str(value.get("type") or "")
    raw_region_value = value.get("value")
    if region_type not in {"bbox", "point", "verbal_region"}:
        return {
            "field": "image_region.type",
            "reason": "image_region.type must be bbox, point, or verbal_region",
        }
    if region_type == "verbal_region":
        if str(raw_region_value or "").strip():
            return None
        return {"field": "image_region.value", "reason": "verbal_region value is required"}
    if not isinstance(raw_region_value, (list, tuple)):
        return {"field": "image_region.value", "reason": f"{region_type} value must be a list"}
    expected = 4 if region_type == "bbox" else 2
    if len(raw_region_value) != expected:
        return {
            "field": "image_region.value",
            "reason": f"{region_type} value must contain {expected} numbers",
        }
    if any(_float_or_none(item) is None for item in raw_region_value):
        return {"field": "image_region.value", "reason": f"{region_type} values must be numbers"}
    return None


def _raw_fpv_artifact_path(
    raw_observation: dict[str, Any],
    *,
    base_dir: Path,
) -> Path | None:
    image_artifacts = raw_observation.get("image_artifacts") or {}
    value = image_artifacts.get("fpv") or raw_observation.get("fpv_image")
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else base_dir / path


def _normalized_bbox_pixels(value: Any, *, width: int, height: int) -> tuple[int, int, int, int]:
    numbers = [float(item) for item in value]
    return (
        round(numbers[0] * width),
        round(numbers[1] * height),
        round(numbers[2] * width),
        round(numbers[3] * height),
    )


def _safe_artifact_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return cleaned or "artifact"


def _grounding_confidence(candidate: dict[str, Any], status: str) -> float:
    base = candidate.get("confidence")
    try:
        score = float(base) if base is not None else 0.72
    except (TypeError, ValueError):
        score = 0.72
    region = candidate.get("image_region") or {}
    if region.get("type") == "verbal_region":
        score -= 0.12
    if status == "ambiguous":
        score -= 0.24
    elif status == "unresolved":
        score -= 0.38
    return round(_clamp(score, 0.05, 0.99), 3)


def _declared_category_matches_object(category_norm: str, obj: Any) -> bool:
    object_norm = _norm(f"{getattr(obj, 'category', '')} {getattr(obj, 'name', '')}")
    if not category_norm or category_norm in object_norm or object_norm in category_norm:
        return True
    if category_norm in _EXACT_VISUAL_CATEGORY_ALIASES:
        return False
    declared_families = _category_alias_families(category_norm)
    object_families = _category_alias_families(object_norm)
    return bool(declared_families.intersection(object_families))


def _category_alias_family(text_norm: str) -> str:
    families = _category_alias_families(text_norm)
    return next(iter(families), "")


def _category_alias_families(text_norm: str) -> set[str]:
    families = set()
    for aliases, _targets in _OBJECT_CATEGORY_TARGETS:
        for alias in aliases:
            alias_norm = _norm(alias)
            if alias_norm and (alias_norm in text_norm or text_norm in alias_norm):
                families.add(aliases[0])
    return families


def _room_id(room_area: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", room_area.strip().lower()).strip("_")
    return slug or "unknown"


def _vec2(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        return (float(value[0]), float(value[1]))
    except (TypeError, ValueError):
        return None


def _vec3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _assert_no_forbidden_agent_view_keys(payload: Any) -> None:
    if isinstance(payload, dict):
        forbidden = _FORBIDDEN_AGENT_VIEW_KEYS.intersection(payload)
        if forbidden:
            raise AssertionError(f"forbidden agent-view keys present: {sorted(forbidden)}")
        for value in payload.values():
            _assert_no_forbidden_agent_view_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_no_forbidden_agent_view_keys(value)


def _strip_forbidden_agent_view_keys(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: _strip_forbidden_agent_view_keys(value)
            for key, value in payload.items()
            if key not in _FORBIDDEN_AGENT_VIEW_KEYS
        }
    if isinstance(payload, list):
        return [_strip_forbidden_agent_view_keys(value) for value in payload]
    return payload


def _public_acceptance_config(config: dict[str, Any] | None) -> dict[str, Any]:
    source = dict(config or {})
    accepted: dict[str, Any] = {}
    for key in (
        "requested_run_size",
        "required_grounded_cleanup_chains",
        "required_model_declared_observations",
    ):
        value = _positive_int(source.get(key))
        if value is not None:
            accepted[key] = value
    policy = str(source.get("done_readiness_policy") or "").strip()
    if policy:
        accepted["done_readiness_policy"] = policy
    task_intent = str(source.get("task_intent") or "").strip()
    if task_intent:
        accepted["task_intent"] = normalize_household_intent(task_intent)
    task_intent_mode = normalize_task_intent_mode(source.get("task_intent_mode"))
    if task_intent_mode != TASK_INTENT_MODE_DEFAULT:
        accepted["task_intent_mode"] = task_intent_mode
    _assert_no_forbidden_agent_view_keys(accepted)
    return accepted


def _public_success_threshold(count: int | None) -> int:
    if count is None or count <= 0:
        return 0
    return max(1, math.ceil(count * 0.70))


def _positive_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def _nonnegative_int(value: Any) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, result)
