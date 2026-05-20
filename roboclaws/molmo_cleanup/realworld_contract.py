from __future__ import annotations

import copy
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from roboclaws.maps.bundle import metric_map_bundle_metadata, validate_nav2_map_bundle
from roboclaws.maps.project import fixture_hints_from_bundle, metric_map_from_bundle
from roboclaws.maps.route import SIM_COSTMAP_PLANNER, validate_metric_map_route
from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.backend_contract import CleanupBackendSession
from roboclaws.molmo_cleanup.planner_observed_binding import (
    observed_handle_planner_binding,
)
from roboclaws.molmo_cleanup.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)
from roboclaws.molmo_cleanup.semantic_timeline import (
    CLEAN_OBSERVED_OBJECT_TOOL,
    CLOSE_RECEPTACLE_PHASE,
    NAVIGATE_TO_OBJECT_PHASE,
    NAVIGATE_TO_RECEPTACLE_PHASE,
    OPEN_RECEPTACLE_PHASE,
    PICK_PHASE,
    PLACE_INSIDE_PHASE,
    PLACE_PHASE,
    SEMANTIC_LOOP_VARIANT,
)
from roboclaws.molmo_cleanup.types import CleanupScenario

REALWORLD_CONTRACT = "realworld_cleanup_v1"
REAL_ROBOT_MAP_BUNDLE_SCHEMA = "real_robot_map_bundle_v1"
CLEANUP_WORKLIST_SCHEMA = "cleanup_worklist_v1"
CLEANUP_POLICY_TRACE_SCHEMA = "cleanup_policy_trace_v1"
REAL_ROBOT_READINESS_SCHEMA = "real_robot_readiness_v1"
DETERMINISTIC_SWEEP_POLICY = "deterministic_sweep_baseline"
DEFAULT_REALWORLD_TASK = "帮我收拾这个房间"
VISIBLE_OBJECT_DETECTIONS_MODE = "visible_object_detections"
RAW_FPV_ONLY_MODE = "raw_fpv_only"
CAMERA_MODEL_POLICY_MODE = "camera_model_policy"
CAMERA_MODEL_POLICY_SCHEMA = "camera_model_policy_v1"
CAMERA_MODEL_POLICY_NAME = "camera_model_policy_baseline"
MODEL_DECLARED_OBSERVATION_SCHEMA = "model_declared_observation_v1"
MODEL_DECLARED_OBSERVATIONS_SCHEMA = "model_declared_observations_v1"
MODEL_DECLARED_OBSERVATION_SOURCE = "model_declared_observation"
RAW_FPV_DECLARATION_STRATEGY = "inline_on_navigate"
RAW_FPV_CATEGORY_HINT = "food, dish, book, linen, toy, electronics, or pillow"
MAIN_CLEANUP_AGENT_PRODUCER = "main_cleanup_agent"
SIMULATED_CAMERA_MODEL_PROVENANCE = "simulated_camera_model"
VISUAL_CANDIDATE_ALREADY_HANDLED_REASON = "visual_candidate_already_handled"
REALWORLD_PERCEPTION_MODES = frozenset(
    {
        VISIBLE_OBJECT_DETECTIONS_MODE,
        RAW_FPV_ONLY_MODE,
        CAMERA_MODEL_POLICY_MODE,
    }
)
_NON_ACTIONABLE_HANDLE_STATES = frozenset({"placed", "placed_closed", "skipped", "stale"})


def raw_fpv_inline_candidate_instruction(observation_id: str | None = None) -> str:
    subject = (
        f"observation_id={observation_id}" if observation_id else "the current raw FPV observation"
    )
    return (
        f"Raw FPV-only mode uses {RAW_FPV_DECLARATION_STRATEGY}: inspect the FPV "
        f"image block for {subject}, do not batch-register candidates first, "
        "and call navigate_to_visual_candidate only when acting on a plausible "
        "cleanup object. Use broad cleanup categories such as "
        f"{RAW_FPV_CATEGORY_HINT} when the exact object class is uncertain. "
        "After a successful pick/place for an observed handle, do not act on "
        "that same handle again; if grounding resolves to an already-handled "
        "object, continue the waypoint sweep."
    )


_FORBIDDEN_AGENT_VIEW_KEYS = frozenset(
    {
        "generated_mess_set",
        "generated_mess_count",
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
    ) -> None:
        if fixture_hint_mode not in {"room_only", "exact_fixtures"}:
            raise ValueError("fixture_hint_mode must be room_only or exact_fixtures")
        if perception_mode not in REALWORLD_PERCEPTION_MODES:
            allowed = ", ".join(sorted(REALWORLD_PERCEPTION_MODES))
            raise ValueError(f"perception_mode must be one of: {allowed}")
        self.contract = contract
        self.backend = contract.backend
        self.scenario: CleanupScenario = contract.backend.scenario
        self.task_prompt = task_prompt
        self.fixture_hint_mode = fixture_hint_mode
        self.perception_mode = perception_mode
        self.map_bundle_dir = Path(map_bundle_dir) if map_bundle_dir is not None else None
        self.map_bundle_validation: dict[str, Any] | None = None
        self._bundle_metric_map_template: dict[str, Any] | None = None
        self._bundle_fixture_hints_template: dict[str, Any] | None = None
        if self.map_bundle_dir is not None:
            validation = validate_nav2_map_bundle(self.map_bundle_dir)
            validation.raise_for_errors()
            self.map_bundle_validation = validation.as_dict()
            self._bundle_metric_map_template = metric_map_from_bundle(self.map_bundle_dir)
            self._bundle_fixture_hints_template = fixture_hints_from_bundle(
                self.map_bundle_dir,
                fixture_hint_mode=fixture_hint_mode,
            )
            self._fixtures = _fixtures_from_bundle_fixture_hints(
                self._bundle_fixture_hints_template
            )
            self._rooms = _rooms_from_bundle_projection(
                self._bundle_metric_map_template,
                self._bundle_fixture_hints_template,
            )
            self._waypoints = _inspection_waypoints_from_bundle_projection(
                self._bundle_metric_map_template,
                self._bundle_fixture_hints_template,
            )
        else:
            self._fixtures = {
                item.receptacle_id: item.to_public_dict() for item in self.scenario.receptacles
            }
            self._rooms = _rooms_from_fixtures(self._fixtures)
            self._waypoints = _inspection_waypoints(self._rooms)
        first_waypoint = self._waypoints[0]["waypoint_id"] if self._waypoints else ""
        self._current_waypoint_id = first_waypoint
        self._observed_waypoint_ids: set[str] = set()
        self._observed_handles_by_object_id: dict[str, str] = {}
        self._object_ids_by_handle: dict[str, str] = {}
        self._detections_by_handle: dict[str, dict[str, Any]] = {}
        self._object_lifecycle: dict[str, dict[str, Any]] = {}
        self._raw_fpv_observations: list[dict[str, Any]] = []
        self._camera_model_policy_events: list[dict[str, Any]] = []
        self._model_declared_observations: list[dict[str, Any]] = []
        self._camera_yaw_offset_deg = 0.0
        self._camera_pitch_offset_deg = 0.0
        self._handled_handles: set[str] = set()
        self._held_handle: str | None = None
        self._current_object_handle: str | None = None
        self._current_receptacle_for_handle: tuple[str, str] | None = None
        self._opened_receptacle_for_handle: tuple[str, str] | None = None
        self._pending_close_receptacle_for_handle: tuple[str, str] | None = None
        self._initial_locations = self.backend.object_locations()

    def public_tool_names(self) -> list[str]:
        return [
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
            "pick",
            "navigate_to_receptacle",
            "open_receptacle",
            "place",
            "place_inside",
            "close_receptacle",
            "done",
        ]

    def public_receptacles_by_id(self) -> dict[str, dict[str, Any]]:
        return {fixture_id: dict(fixture) for fixture_id, fixture in self._fixtures.items()}

    def metric_map(self) -> dict[str, Any]:
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
                for item in metric_map.get("inspection_waypoints") or []
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
            _assert_no_forbidden_agent_view_keys(metric_map)
            return metric_map

        frame_id = "map"
        map_id = f"{self.scenario.scenario_id}_semantic_map"
        map_version = "static-fixture-map-v1"
        return self._ok(
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
            rooms=[
                {
                    "room_id": room["room_id"],
                    "room_label": room["room_label"],
                    "fixture_count": len(room["fixture_ids"]),
                    "polygon": room.get("polygon", []),
                }
                for room in self._rooms
            ],
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
                for item in self._waypoints
            ],
            public_contract_note=(
                "Inspection waypoints are static map/fixture coverage candidates, "
                "not generated from movable-object locations, generated mess set, "
                "target count, or acceptable destination sets."
            ),
        )

    def fixture_hints(self) -> dict[str, Any]:
        if self._bundle_fixture_hints_template is not None:
            fixture_hints = copy.deepcopy(self._bundle_fixture_hints_template)
            fixture_hints["contract"] = REALWORLD_CONTRACT
            fixture_hints["tool"] = "fixture_hints"
            fixture_hints["status"] = "ok"
            fixture_hints["ok"] = True
            fixture_hints["fixture_hint_mode"] = self.fixture_hint_mode
            fixture_hints["public_contract_note"] = (
                "Static fixture hints are projected from the selected prebuilt Nav2 "
                "map bundle. Runtime movable-object observations remain separate "
                "observed_* handles."
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
        fixture_id = _first_fixture_for_waypoint(waypoint)
        navigation = None
        if fixture_id is not None:
            navigation = self.contract.navigate_to_receptacle(fixture_id)
        return self._ok(
            "navigate_to_waypoint",
            navigation_backend=SIM_COSTMAP_PLANNER,
            primitive_provenance=API_SEMANTIC_PROVENANCE,
            route_validation=route.as_dict(),
            goal_pose={"frame_id": "map", **self._waypoint_pose(waypoint)},
            pose_source="inspection_waypoint",
            staleness_s=0.0,
            pose_confidence=1.0,
            pose_covariance=[0.0, 0.0, 0.0],
            requires_reobserve=False,
            waypoint_id=waypoint_id,
            room_id=waypoint["room_id"],
            coverage_estimate=waypoint["coverage_estimate"],
            navigation_status=(navigation or {}).get("status", "ok"),
        )

    def observe(self) -> dict[str, Any]:
        waypoint = self._waypoint_by_id(self._current_waypoint_id)
        if waypoint is None:
            return self._error("observe", "missing_waypoint")
        self._observed_waypoint_ids.add(str(waypoint["waypoint_id"]))
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
            return self._ok(
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
        detections = self._visible_detections_for_waypoint(waypoint)
        return self._ok(
            "observe",
            contract=REALWORLD_CONTRACT,
            current_room_id=waypoint["room_id"],
            waypoint_id=waypoint["waypoint_id"],
            observation_role="coverage_scan"
            if self._held_handle is None
            else "held_object_area_check",
            waypoint_source=waypoint.get("waypoint_source", "static_map_coverage"),
            perception_mode=self.perception_mode,
            structured_detections_available=True,
            visible_object_detections=detections,
            held_object_id=self._held_handle,
            perception_source="robot_local_visible_object_detections",
            private_target_truth_included=False,
        )

    def adjust_camera(
        self,
        yaw_delta_deg: float = 0.0,
        pitch_delta_deg: float = 0.0,
    ) -> dict[str, Any]:
        previous = self._camera_offset()
        self._camera_yaw_offset_deg = _clamp(
            self._camera_yaw_offset_deg + _float_or_zero(yaw_delta_deg),
            -45.0,
            45.0,
        )
        self._camera_pitch_offset_deg = _clamp(
            self._camera_pitch_offset_deg + _float_or_zero(pitch_delta_deg),
            -20.0,
            20.0,
        )
        current = self._camera_offset()
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
        if not candidate_inputs:
            candidate_inputs = self._simulated_declaration_inputs_for_waypoint(
                waypoint,
                observation_id=str(raw_observation["observation_id"]),
            )
        declared = []
        for index, candidate in enumerate(candidate_inputs):
            candidate_error = _visual_candidate_validation_error(candidate)
            if candidate_error is not None:
                return self._error(
                    "declare_visual_candidates",
                    "invalid_visual_candidate",
                    observation_id=str(raw_observation["observation_id"]),
                    candidate_index=index,
                    candidate_error=candidate_error,
                    recovery_hint=(
                        "Declare category, target_fixture_id, evidence_note, and a valid "
                        "bbox, point, or verbal_region image_region from public FPV evidence."
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
        evidence = {
            "schema": MODEL_DECLARED_OBSERVATIONS_SCHEMA,
            "perception_mode": self.perception_mode,
            "observation_id": str(raw_observation["observation_id"]),
            "waypoint_id": str(raw_observation["waypoint_id"]),
            "room_id": str(raw_observation["room_id"]),
            "producer_type": producer_type,
            "producer_id": producer_id,
            "candidate_count": len(declared),
            "registered_observed_handles": [str(item["object_id"]) for item in declared],
            "private_truth_included": False,
            "policy_note": (
                "Model-declared observations are derived from public camera evidence "
                "and public fixture metadata; private scoring truth is not exposed."
            ),
        }
        _assert_no_forbidden_agent_view_keys(evidence)
        if producer_type == SIMULATED_CAMERA_MODEL_PROVENANCE:
            self._camera_model_policy_events.append(evidence)
        return self._ok(
            "declare_visual_candidates",
            contract=REALWORLD_CONTRACT,
            model_declared_observation_evidence=evidence,
            model_declared_observations=declared,
            camera_model_candidates=resolved_candidates,
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
                recovery_hint=declaration_response.get("recovery_hint", ""),
            )
        declarations = declaration_response.get("model_declared_observations") or []
        declaration = declarations[0] if declarations else {}
        handle = str(declaration.get("object_id") or "")
        if declaration.get("actionability_status") == "already_handled":
            return self._error(
                "navigate_to_visual_candidate",
                VISUAL_CANDIDATE_ALREADY_HANDLED_REASON,
                model_declared_observation=declaration,
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
                model_declared_observation=declaration,
                object_id=handle,
                grounding_status=declaration.get("grounding_status", "unresolved"),
                grounding_confidence=declaration.get("grounding_confidence", 0.0),
                recovery_hint=declaration.get(
                    "recovery_hint",
                    "Declare a tighter image_region or include a source_fixture_id.",
                ),
            )
        navigation = self.navigate_to_object(handle)
        if not navigation.get("ok"):
            return self._error(
                "navigate_to_visual_candidate",
                str(navigation.get("error_reason") or "navigation_failed"),
                model_declared_observation=declaration,
                object_id=handle,
                recovery_hint=navigation.get("recovery_hint", ""),
            )
        payload = {
            key: value
            for key, value in navigation.items()
            if key not in {"tool", "ok", "status", "object_id"}
        }
        detection = self._detections_by_handle.get(handle, {})
        return self._ok(
            "navigate_to_visual_candidate",
            **payload,
            object_id=handle,
            model_declared_observation=declaration,
            candidate_fixture_id=detection.get("candidate_fixture_id", ""),
            candidate_fixture_category=detection.get("candidate_fixture_category", ""),
            cleanup_recommended=bool(detection.get("cleanup_recommended", False)),
            recommended_tool=detection.get("recommended_tool", ""),
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
            detection=dict(detection),
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
        return observed_handle_planner_binding(
            self,
            object_id=object_id,
            target_receptacle_id=target_receptacle_id,
            source_receptacle_id=source_receptacle_id,
            tools=tools,
        )

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        internal_id = self._internal_object_id(object_id)
        if internal_id is None:
            grounding_error = self._unresolved_visual_candidate_error(
                "navigate_to_object", object_id
            )
            if grounding_error is not None:
                return grounding_error
            return self._error("navigate_to_object", "stale_reference", object_id=object_id)
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
            source_receptacle_id=response.get("source_receptacle_id"),
            previous_receptacle_id=response.get("previous_receptacle_id"),
            location_id=response.get("location_id"),
            state_mutation=response.get("state_mutation"),
            navigation_status=response.get("status"),
        )

    def pick(self, object_id: str) -> dict[str, Any]:
        internal_id = self._internal_object_id(object_id)
        if internal_id is None:
            grounding_error = self._unresolved_visual_candidate_error("pick", object_id)
            if grounding_error is not None:
                return grounding_error
            return self._error("pick", "stale_reference", object_id=object_id)
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
        if fixture_id not in self._fixtures:
            return self._error("navigate_to_receptacle", "stale_reference", fixture_id=fixture_id)
        if self._held_handle is None:
            return self._semantic_order_error(
                "navigate_to_receptacle",
                required_tool="pick",
                fixture_id=fixture_id,
                recovery_hint=(
                    "Pick an observed object before navigating to a cleanup fixture. "
                    "Use navigate_to_object -> pick first."
                ),
            )
        response = self.contract.navigate_to_receptacle(fixture_id)
        if not response.get("ok"):
            return self._public_error_from_private(
                "navigate_to_receptacle",
                self._held_handle or "",
                response,
            )
        self._current_waypoint_id = self._preferred_waypoint_for_fixture(fixture_id)
        self._reset_camera_adjustment()
        self._current_receptacle_for_handle = (self._held_handle, fixture_id)
        self._opened_receptacle_for_handle = None
        return self._ok(
            "navigate_to_receptacle",
            object_id=self._held_handle,
            receptacle_id=fixture_id,
            fixture_id=fixture_id,
            navigation_backend=response.get("navigation_backend", API_SEMANTIC_PROVENANCE),
            primitive_provenance=response.get(
                "primitive_provenance",
                API_SEMANTIC_PROVENANCE,
            ),
            goal_pose=self._fixture_pose(fixture_id),
            pose_source="fixture_semantic_map",
            staleness_s=0.0,
            pose_confidence=1.0,
            pose_covariance=[0.0, 0.0, 0.0],
            requires_reobserve=False,
            previous_receptacle_id=response.get("previous_receptacle_id"),
            state_mutation=response.get("state_mutation"),
            navigation_status=response.get("status"),
        )

    def open_receptacle(self, fixture_id: str) -> dict[str, Any]:
        if fixture_id not in self._fixtures:
            return self._error("open_receptacle", "stale_reference", fixture_id=fixture_id)
        if self._held_handle is None:
            return self._semantic_order_error(
                "open_receptacle",
                required_tool="pick",
                fixture_id=fixture_id,
                recovery_hint="Pick an observed object before opening a cleanup fixture.",
            )
        if self._current_receptacle_for_handle != (self._held_handle, fixture_id):
            return self._semantic_order_error(
                "open_receptacle",
                required_tool="navigate_to_receptacle",
                object_id=self._held_handle,
                fixture_id=fixture_id,
                recovery_hint=(
                    "Call navigate_to_receptacle for this fixture before open_receptacle. "
                    "Fridge-like cleanup must be nav -> open -> place_inside -> close."
                ),
            )
        opened = self.contract.open_receptacle(fixture_id)
        if opened.get("ok"):
            self._opened_receptacle_for_handle = (self._held_handle, fixture_id)
        return self._public_fixture_response("open_receptacle", fixture_id, opened)

    def place(self, fixture_id: str) -> dict[str, Any]:
        return self._place(fixture_id, inside=False)

    def place_inside(self, fixture_id: str) -> dict[str, Any]:
        return self._place(fixture_id, inside=True)

    def close_receptacle(self, fixture_id: str) -> dict[str, Any]:
        if fixture_id not in self._fixtures:
            return self._error("close_receptacle", "stale_reference", fixture_id=fixture_id)
        pending = self._pending_close_receptacle_for_handle
        if pending is None or pending[1] != fixture_id:
            return self._semantic_order_error(
                "close_receptacle",
                required_tool="place_inside",
                object_id=pending[0] if pending is not None else None,
                fixture_id=fixture_id,
                recovery_hint=(
                    "Call close_receptacle only after place_inside for the same fridge-like "
                    "fixture."
                ),
            )
        handle, _ = pending
        closed = self.contract.close_receptacle(fixture_id)
        if closed.get("ok"):
            self._pending_close_receptacle_for_handle = None
            self._set_handle_state(
                handle,
                "placed_closed",
                tool="close_receptacle",
                fixture_id=fixture_id,
            )
        return self._public_fixture_response(
            "close_receptacle",
            fixture_id,
            closed,
            object_id=handle,
        )

    def clean_observed_object(
        self,
        object_id: str,
        fixture_id: str,
        *,
        placement_tool: str = "auto",
        step_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Run one perf-lane promoted-candidate cleanup sequence with public substeps."""
        if fixture_id not in self._fixtures:
            return self._error(
                CLEAN_OBSERVED_OBJECT_TOOL,
                "stale_reference",
                object_id=object_id,
                fixture_id=fixture_id,
            )
        if placement_tool not in {"", "auto", PLACE_PHASE, PLACE_INSIDE_PHASE}:
            return self._error(
                CLEAN_OBSERVED_OBJECT_TOOL,
                "unsupported_placement_tool",
                object_id=object_id,
                fixture_id=fixture_id,
                placement_tool=placement_tool,
                recovery_hint="Use placement_tool=auto, place, or place_inside.",
            )

        steps: list[dict[str, Any]] = []

        def append_step(phase: str, response: dict[str, Any]) -> None:
            step = dict(response)
            step["phase"] = phase
            step.setdefault("tool", phase)
            step.setdefault("object_id", object_id)
            steps.append(step)
            if step_callback is not None:
                step_callback(phase, dict(step))

        navigate_object = self.navigate_to_object(object_id)
        append_step(NAVIGATE_TO_OBJECT_PHASE, navigate_object)
        if not navigate_object.get("ok"):
            return self._composite_cleanup_response(
                object_id=object_id,
                fixture_id=fixture_id,
                steps=steps,
                error_reason=str(navigate_object.get("error_reason") or "navigate_failed"),
                recovery_hint=str(navigate_object.get("recovery_hint") or ""),
            )

        picked = self.pick(object_id)
        append_step(PICK_PHASE, picked)
        if not picked.get("ok"):
            return self._composite_cleanup_response(
                object_id=object_id,
                fixture_id=fixture_id,
                steps=steps,
                error_reason=str(picked.get("error_reason") or "pick_failed"),
                recovery_hint=str(picked.get("recovery_hint") or ""),
            )

        navigate_receptacle = self.navigate_to_receptacle(fixture_id)
        append_step(NAVIGATE_TO_RECEPTACLE_PHASE, navigate_receptacle)
        if not navigate_receptacle.get("ok"):
            return self._composite_cleanup_response(
                object_id=object_id,
                fixture_id=fixture_id,
                steps=steps,
                error_reason=str(
                    navigate_receptacle.get("error_reason") or "navigate_receptacle_failed"
                ),
                recovery_hint=str(navigate_receptacle.get("recovery_hint") or ""),
            )

        fixture = self._fixtures[fixture_id]
        selected_tool = (
            _recommended_place_tool(fixture_id, self._fixtures)
            if placement_tool in {"", "auto"}
            else placement_tool
        )
        if selected_tool == PLACE_PHASE and _fixture_prefers_inside(fixture):
            selected_tool = PLACE_INSIDE_PHASE

        if selected_tool == PLACE_INSIDE_PHASE and _fixture_requires_open(fixture):
            opened = self.open_receptacle(fixture_id)
            append_step(OPEN_RECEPTACLE_PHASE, opened)
            if not opened.get("ok"):
                return self._composite_cleanup_response(
                    object_id=object_id,
                    fixture_id=fixture_id,
                    steps=steps,
                    error_reason=str(opened.get("error_reason") or "open_receptacle_failed"),
                    recovery_hint=str(opened.get("recovery_hint") or ""),
                )

        placed = (
            self.place_inside(fixture_id)
            if selected_tool == PLACE_INSIDE_PHASE
            else self.place(fixture_id)
        )
        append_step(selected_tool, placed)
        if not placed.get("ok"):
            return self._composite_cleanup_response(
                object_id=object_id,
                fixture_id=fixture_id,
                steps=steps,
                error_reason=str(placed.get("error_reason") or "place_failed"),
                recovery_hint=str(placed.get("recovery_hint") or ""),
            )

        if selected_tool == PLACE_INSIDE_PHASE and _fixture_requires_open(fixture):
            closed = self.close_receptacle(fixture_id)
            append_step(CLOSE_RECEPTACLE_PHASE, closed)
            if not closed.get("ok"):
                return self._composite_cleanup_response(
                    object_id=object_id,
                    fixture_id=fixture_id,
                    steps=steps,
                    error_reason=str(closed.get("error_reason") or "close_receptacle_failed"),
                    recovery_hint=str(closed.get("recovery_hint") or ""),
                )

        return self._composite_cleanup_response(
            object_id=object_id,
            fixture_id=fixture_id,
            steps=steps,
            placement_tool=selected_tool,
        )

    def done(self, reason: str = "") -> dict[str, Any]:
        pending = self._pending_cleanup_candidates()
        if pending:
            return self._error(
                "done",
                "pending_cleanup_candidates",
                required_tool="navigate_to_object",
                pending_observed_handles=[str(item["object_id"]) for item in pending],
                pending_cleanup_candidates=pending,
                recovery_hint=(
                    "Clean pending observed handles before done: navigate_to_object -> pick -> "
                    "navigate_to_receptacle(candidate_fixture_id) -> place/place_inside, using "
                    "open_receptacle/close_receptacle for fridge-like fixtures."
                ),
            )
        coverage = self._sweep_coverage()
        if coverage["sweep_coverage_rate"] < 0.90:
            next_waypoint_id = coverage["unvisited_waypoint_ids"][0]
            return self._error(
                "done",
                "insufficient_sweep_coverage",
                required_tool="navigate_to_waypoint",
                next_waypoint_id=next_waypoint_id,
                sweep_coverage_rate=coverage["sweep_coverage_rate"],
                observed_waypoint_count=coverage["observed_waypoint_count"],
                total_waypoints=coverage["total_waypoints"],
                unvisited_waypoint_ids=coverage["unvisited_waypoint_ids"],
                recovery_hint=(
                    "Continue the public sweep before done: call navigate_to_waypoint("
                    f"{next_waypoint_id}) and observe. Do not use done as a system "
                    "assessment while static-map inspection waypoints remain unvisited."
                ),
            )
        if self.perception_mode == RAW_FPV_ONLY_MODE:
            declaration_count = len(self._model_declared_observations)
            if declaration_count < 7:
                return self._error(
                    "done",
                    "insufficient_model_declared_observations",
                    model_declared_observations=declaration_count,
                    raw_fpv_observations=len(self._raw_fpv_observations),
                    required_model_declared_observations=7,
                    recovery_hint=(
                        "Continue sweeping public waypoints and use "
                        "navigate_to_visual_candidate for plausible cleanup objects "
                        "seen in raw FPV images before calling done."
                    ),
                )
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

    def _sweep_coverage(self) -> dict[str, Any]:
        total_waypoints = len(self._waypoints)
        unvisited = [
            str(item["waypoint_id"])
            for item in self._waypoints
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

    def agent_view_payload(self) -> dict[str, Any]:
        observed_objects = [
            dict(self._detections_by_handle[handle])
            for handle in sorted(self._detections_by_handle)
        ]
        metric_map = self.metric_map()
        fixture_hints = self.fixture_hints()
        payload = {
            "contract": REALWORLD_CONTRACT,
            "perception_mode": self.perception_mode,
            "structured_detections_available": self.perception_mode
            == VISIBLE_OBJECT_DETECTIONS_MODE,
            "metric_map": metric_map,
            "fixture_hints": fixture_hints,
            "observed_objects": observed_objects,
            "raw_fpv_observations": [dict(item) for item in self._raw_fpv_observations],
            "camera_model_policy_evidence": self.camera_model_policy_payload(),
            "model_declared_observations": self.model_declared_observations_payload()[
                "observations"
            ],
            "model_declared_observation_evidence": (self.model_declared_observations_payload()),
            "policy_view": self.policy_view_payload(),
            "cleanup_worklist": self.cleanup_worklist_payload(fixture_hints=fixture_hints),
            "observed_waypoint_ids": sorted(self._observed_waypoint_ids),
            "public_tool_names": self.public_tool_names(),
            "forbidden_private_fields_absent": True,
        }
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

    def policy_view_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "realworld_cleanup_policy_view_v1",
            "allowed_inputs": [
                "metric_map",
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

    def cleanup_worklist_payload(
        self,
        *,
        fixture_hints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        public_fixtures = fixture_hints if fixture_hints is not None else self.fixture_hints()
        lifecycle_rows = []
        for handle in sorted(self._detections_by_handle):
            detection = self._detections_by_handle[handle]
            lifecycle = dict(self._object_lifecycle.get(handle, {}))
            support = detection.get("support_estimate") or {}
            declaration = detection.get("model_declared_observation") or {}
            grounding_status = str(
                detection.get("grounding_status") or declaration.get("grounding_status") or ""
            )
            public_candidate = infer_target_fixture_for_detection(detection, public_fixtures)
            candidate_fixture_id = (public_candidate or {}).get("fixture_id", "")
            source_fixture_id = str(support.get("fixture_id") or "")
            cleanup_recommended = bool(
                grounding_status not in {"ambiguous", "unresolved"}
                and candidate_fixture_id
                and candidate_fixture_id != source_fixture_id
            )
            lifecycle_rows.append(
                {
                    "object_id": handle,
                    "state": lifecycle.get("state", "pending"),
                    "category": detection.get("category", ""),
                    "room_id": detection.get("current_room_id", lifecycle.get("room_id", "")),
                    "source_fixture_id": source_fixture_id,
                    "candidate_fixture_id": candidate_fixture_id,
                    "cleanup_recommended": cleanup_recommended,
                    "grounding_status": grounding_status,
                    "candidate_source": "public_category_fixture_affordance",
                    "last_waypoint_id": lifecycle.get("waypoint_id", ""),
                    "perception_source": lifecycle.get("perception_source", "visible_detection"),
                }
            )
        waypoint_rows = []
        for waypoint in self._waypoints:
            waypoint_id = str(waypoint["waypoint_id"])
            waypoint_rows.append(
                {
                    "waypoint_id": waypoint_id,
                    "room_id": waypoint["room_id"],
                    "state": "visited"
                    if waypoint_id in self._observed_waypoint_ids
                    else "unvisited",
                    "purpose": waypoint.get("purpose", "fixture_coverage"),
                    "waypoint_source": waypoint.get("waypoint_source", "static_map_coverage"),
                }
            )
        rooms = []
        for room in self._rooms:
            room_waypoints = [
                item for item in waypoint_rows if item.get("room_id") == room["room_id"]
            ]
            visited = sum(1 for item in room_waypoints if item.get("state") == "visited")
            pending = [
                item
                for item in lifecycle_rows
                if item.get("room_id") == room["room_id"] and item.get("state") == "pending"
            ]
            rooms.append(
                {
                    "room_id": room["room_id"],
                    "scan_state": "scanned"
                    if room_waypoints and visited == len(room_waypoints)
                    else "partially_scanned"
                    if visited
                    else "unvisited",
                    "visited_waypoints": visited,
                    "total_waypoints": len(room_waypoints),
                    "pending_observed_handles": [item["object_id"] for item in pending],
                }
            )
        payload = {
            "schema": CLEANUP_WORKLIST_SCHEMA,
            "waypoint_source": "static_map_fixture_coverage",
            "held_object_id": self._held_handle,
            "objects": lifecycle_rows,
            "waypoints": waypoint_rows,
            "rooms": rooms,
            "public_policy_note": (
                "Observed handles come from observe or model-declared camera evidence. "
                "Candidate fixtures are public category/fixture-affordance guesses, "
                "not private acceptable-destination truth."
            ),
        }
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

    def _pending_cleanup_candidates(self) -> list[dict[str, Any]]:
        worklist = self.cleanup_worklist_payload(fixture_hints=self.fixture_hints())
        pending = []
        for item in worklist.get("objects", []):
            if item.get("state") != "pending":
                continue
            if item.get("grounding_status") in {"ambiguous", "unresolved"}:
                continue
            candidate_fixture_id = str(item.get("candidate_fixture_id") or "")
            source_fixture_id = str(item.get("source_fixture_id") or "")
            if not candidate_fixture_id or candidate_fixture_id == source_fixture_id:
                continue
            pending.append(
                {
                    "object_id": str(item.get("object_id") or ""),
                    "category": str(item.get("category") or ""),
                    "source_fixture_id": source_fixture_id,
                    "candidate_fixture_id": candidate_fixture_id,
                    "recommended_tool": _recommended_place_tool(
                        candidate_fixture_id, self._fixtures
                    ),
                }
            )
        return pending

    def camera_model_policy_payload(self) -> dict[str, Any]:
        events = [dict(item) for item in self._camera_model_policy_events]
        return {
            "schema": CAMERA_MODEL_POLICY_SCHEMA,
            "perception_mode": self.perception_mode,
            "enabled": self.perception_mode == CAMERA_MODEL_POLICY_MODE,
            "model_provenance": SIMULATED_CAMERA_MODEL_PROVENANCE
            if self.perception_mode == CAMERA_MODEL_POLICY_MODE
            else "",
            "event_count": len(events),
            "candidate_count": sum(int(item.get("candidate_count") or 0) for item in events),
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
            if lifecycle.get("state") not in {None, "pending"}
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
        return infer_target_fixture_for_detection(detection, fixture_hints)

    def attach_raw_fpv_observation_artifact(
        self,
        observation_id: str,
        *,
        views: dict[str, Any],
        robot_view_label: str | None = None,
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
            _assert_no_forbidden_agent_view_keys(item)
            return dict(item)
        return None

    def _place(self, fixture_id: str, *, inside: bool) -> dict[str, Any]:
        if fixture_id not in self._fixtures:
            return self._error(
                "place_inside" if inside else "place", "stale_reference", fixture_id=fixture_id
            )
        handle = self._held_handle
        if handle is None:
            return self._error("place_inside" if inside else "place", "not_holding")
        tool = "place_inside" if inside else "place"
        if self._current_receptacle_for_handle != (handle, fixture_id):
            return self._semantic_order_error(
                tool,
                required_tool="navigate_to_receptacle",
                object_id=handle,
                fixture_id=fixture_id,
                recovery_hint=(
                    "Call navigate_to_receptacle for this fixture after pick and before "
                    "placing the held object."
                ),
            )
        if not inside and _fixture_prefers_inside(self._fixtures[fixture_id]):
            requires_open = _fixture_requires_open(self._fixtures[fixture_id])
            needs_open = requires_open and self._opened_receptacle_for_handle != (
                handle,
                fixture_id,
            )
            required_tool = "open_receptacle" if needs_open else "place_inside"
            return self._semantic_order_error(
                "place",
                required_tool=required_tool,
                object_id=handle,
                fixture_id=fixture_id,
                recovery_hint=(
                    "Use place_inside for fridge-like or shelf-like fixtures; "
                    "fridge-like fixtures must be opened first."
                ),
            )
        if inside and _fixture_requires_open(self._fixtures[fixture_id]):
            if self._opened_receptacle_for_handle != (handle, fixture_id):
                return self._semantic_order_error(
                    "place_inside",
                    required_tool="open_receptacle",
                    object_id=handle,
                    fixture_id=fixture_id,
                    recovery_hint=(
                        "Call open_receptacle for this fridge-like fixture before place_inside."
                    ),
                )
        placed = (
            self.contract.place_inside(fixture_id) if inside else self.contract.place(fixture_id)
        )
        if placed.get("ok"):
            self._handled_handles.add(handle)
            self._set_handle_state(
                handle,
                "placed",
                tool=tool,
                fixture_id=fixture_id,
            )
            if inside and _fixture_requires_open(self._fixtures[fixture_id]):
                self._pending_close_receptacle_for_handle = (handle, fixture_id)
            else:
                self._pending_close_receptacle_for_handle = None
            self._held_handle = None
            self._current_receptacle_for_handle = None
            self._opened_receptacle_for_handle = None
        return self._public_manipulation_response(
            tool,
            handle,
            placed,
            fixture_id=fixture_id,
        )

    def _visible_detections_for_waypoint(self, waypoint: dict[str, Any]) -> list[dict[str, Any]]:
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
            if room_id != waypoint["room_id"]:
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
                "support_estimate": {
                    "fixture_id": location_id,
                    "relation": _location_relation(obj.object_id, self.backend),
                    "confidence": 0.74,
                    "source": "visible_detection",
                },
            }
            detection.update(self._public_candidate_hint(detection))
            self._detections_by_handle[handle] = detection
            self._record_detection_lifecycle(handle, detection, waypoint)
            detections.append(dict(detection))
        return sorted(detections, key=lambda item: str(item["object_id"]))

    def _camera_model_candidates_for_waypoint(
        self,
        waypoint: dict[str, Any],
        *,
        observation_id: str,
        model_provenance: str,
    ) -> list[dict[str, Any]]:
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
            if room_id != waypoint["room_id"]:
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
                "perception_source": CAMERA_MODEL_POLICY_MODE,
                "model_provenance": model_provenance,
                "source_observation_id": observation_id,
                "candidate_source": "raw_fpv_observation",
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
            detection.update(self._public_candidate_hint(detection))
            _assert_no_forbidden_agent_view_keys(detection)
            self._detections_by_handle[handle] = detection
            self._record_detection_lifecycle(handle, detection, waypoint)
            candidates.append(dict(detection))
        return sorted(candidates, key=lambda item: str(item["object_id"]))

    def _public_candidate_hint(self, detection: dict[str, Any]) -> dict[str, Any]:
        candidate = infer_target_fixture_for_detection(detection, self.fixture_hints())
        if candidate is None:
            return {
                "candidate_fixture_id": "",
                "candidate_fixture_category": "",
                "cleanup_recommended": False,
                "candidate_source": "public_category_fixture_affordance",
            }
        candidate_fixture_id = str(candidate.get("fixture_id") or "")
        source_fixture_id = str((detection.get("support_estimate") or {}).get("fixture_id") or "")
        return {
            "candidate_fixture_id": candidate_fixture_id,
            "candidate_fixture_category": str(candidate.get("category") or ""),
            "cleanup_recommended": bool(
                candidate_fixture_id and candidate_fixture_id != source_fixture_id
            ),
            "candidate_source": "public_category_fixture_affordance",
            "recommended_tool": _recommended_place_tool(candidate_fixture_id, self._fixtures),
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
            target = infer_target_fixture_for_detection(detection, self.fixture_hints())
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
            self._model_declared_observations.append(declaration)
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
                }
            )
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
        target_fixture_id = str(candidate.get("target_fixture_id") or "")
        target_fixture = self._fixtures.get(target_fixture_id, {})
        category = str(candidate.get("category") or "object").strip() or "object"
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
            "target_fixture_category": str(target_fixture.get("category") or ""),
            "source_fixture_id": str(candidate.get("source_fixture_id") or ""),
            "evidence_note": str(candidate.get("evidence_note") or ""),
            "image_region": image_region,
            "confidence": confidence_value,
            "producer_type": str(candidate.get("producer_type") or producer_type),
            "producer_id": str(candidate.get("producer_id") or producer_id),
            "supersedes_observation_id": str(candidate.get("supersedes_observation_id") or ""),
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
        if match["status"] != "unresolved" or not source_fixture_id:
            if match["status"] != "unresolved":
                return match
        if source_fixture_id:
            fallback = self._visual_candidate_match_for_source(
                waypoint,
                category_norm=category_norm,
                source_fixture_id="",
                restrict_to_waypoint_fixtures=True,
            )
            if fallback["status"] != "unresolved":
                fallback["source_fixture_fallback"] = True
                fallback["requested_source_fixture_id"] = source_fixture_id
                return fallback
        room_match = self._visual_candidate_match_for_source(
            waypoint,
            category_norm=category_norm,
            source_fixture_id=source_fixture_id,
            restrict_to_waypoint_fixtures=False,
        )
        if room_match["status"] != "unresolved":
            room_match["room_fallback"] = True
            if source_fixture_id:
                room_match["requested_source_fixture_id"] = source_fixture_id
            return room_match
        if not source_fixture_id:
            return match
        fallback = self._visual_candidate_match_for_source(
            waypoint,
            category_norm=category_norm,
            source_fixture_id="",
            restrict_to_waypoint_fixtures=False,
        )
        if fallback["status"] != "unresolved":
            fallback["source_fixture_fallback"] = True
            fallback["requested_source_fixture_id"] = source_fixture_id
            fallback["room_fallback"] = True
        return fallback

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
            if match.get("room_fallback") and match.get("source_fixture_fallback"):
                basis = (
                    "single public same-room object matched category after source fixture "
                    "and waypoint fixture hints did not match"
                )
            elif match.get("room_fallback"):
                basis = (
                    "single public same-room object matched category after waypoint "
                    "fixture hint did not match"
                )
            elif match.get("source_fixture_fallback"):
                basis = (
                    "single public camera-context object matched category after "
                    "source fixture hint did not match"
                )
            else:
                basis = "single public camera-context object matched category/source/target hints"
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
                else "Reobserve from another waypoint or declare a clearer category/source fixture."
            )
            grounding_status = status
            actionability_status = "needs_clarification"
        target_fixture_id = str(candidate.get("target_fixture_id") or "")
        target_fixture = self._fixtures.get(target_fixture_id, {})
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
            "target_fixture_category": str(target_fixture.get("category") or ""),
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
            "private_truth_included": False,
        }
        if status == "already_handled":
            declaration["handled_state"] = str(lifecycle.get("state") or "handled")
        _assert_no_forbidden_agent_view_keys(declaration)
        return declaration

    def _target_plausibility(self, *, category: str, target_fixture_id: str) -> dict[str, Any]:
        fixture = self._fixtures.get(target_fixture_id)
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
        public_target = infer_target_fixture_for_detection(pseudo_detection, self.fixture_hints())
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
            "perception_source": perception_source,
            "producer_type": producer_type,
            "source_observation_id": source_observation_id,
            "candidate_source": MODEL_DECLARED_OBSERVATION_SOURCE
            if perception_source == MODEL_DECLARED_OBSERVATION_SOURCE
            else "raw_fpv_observation",
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
        if producer_type == SIMULATED_CAMERA_MODEL_PROVENANCE:
            detection["model_provenance"] = producer_type
            detection["support_estimate"]["model_provenance"] = producer_type
        detection.update(self._public_candidate_hint(detection))
        _assert_no_forbidden_agent_view_keys(detection)
        return detection

    def _objects_visible_from_waypoint(self, waypoint: dict[str, Any]) -> list[tuple[Any, str]]:
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
            if room_id != waypoint["room_id"]:
                continue
            if fixture_ids and location_id not in fixture_ids:
                continue
            visible.append((obj, str(location_id)))
        return visible

    def _objects_visible_from_room(self, waypoint: dict[str, Any]) -> list[tuple[Any, str]]:
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
            if room_id != waypoint["room_id"]:
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

    def _composite_cleanup_response(
        self,
        *,
        object_id: str,
        fixture_id: str,
        steps: list[dict[str, Any]],
        placement_tool: str = "",
        error_reason: str = "",
        recovery_hint: str = "",
    ) -> dict[str, Any]:
        source_receptacle_id = ""
        location_id = ""
        contained_in = None
        location_relation = None
        placement_diagnostic = None
        for step in steps:
            if not source_receptacle_id and step.get("source_receptacle_id"):
                source_receptacle_id = str(step["source_receptacle_id"])
            if step.get("location_id"):
                location_id = str(step["location_id"])
            if step.get("contained_in") is not None:
                contained_in = step.get("contained_in")
            if step.get("location_relation") is not None:
                location_relation = step.get("location_relation")
            if step.get("placement_diagnostic") is not None:
                placement_diagnostic = step.get("placement_diagnostic")
        payload = {
            "object_id": object_id,
            "fixture_id": fixture_id,
            "receptacle_id": fixture_id,
            "source_receptacle_id": source_receptacle_id,
            "semantic_steps": steps,
            "semantic_step_count": len(steps),
            "composite_action": CLEAN_OBSERVED_OBJECT_TOOL,
            "composite_preserves_semantic_substeps": True,
            "primitive_provenance": API_SEMANTIC_PROVENANCE,
            "navigation_backend": API_SEMANTIC_PROVENANCE,
            "instruction": (
                "Composite cleanup completed the canonical semantic substeps. "
                "Call observe once in the current room/fixture area before choosing "
                "the next object or waypoint."
            ),
        }
        if placement_tool:
            payload["placement_tool"] = placement_tool
        if location_id:
            payload["location_id"] = location_id
        if contained_in is not None:
            payload["contained_in"] = contained_in
        if location_relation is not None:
            payload["location_relation"] = location_relation
        if placement_diagnostic is not None:
            payload["placement_diagnostic"] = placement_diagnostic
        if not error_reason:
            return self._ok(CLEAN_OBSERVED_OBJECT_TOOL, **payload)
        payload["recovery_hint"] = recovery_hint
        return self._error(CLEAN_OBSERVED_OBJECT_TOOL, error_reason, **payload)

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
        return next((item for item in self._waypoints if item["waypoint_id"] == waypoint_id), None)

    def _handle_for_object(self, object_id: str) -> str:
        existing = self._observed_handles_by_object_id.get(object_id)
        if existing is not None:
            return existing
        handle = self._new_observed_handle()
        self._observed_handles_by_object_id[object_id] = handle
        self._object_ids_by_handle[handle] = object_id
        return handle

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


def infer_target_fixture_for_detection(
    detection: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> dict[str, Any] | None:
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


def forbidden_agent_view_keys() -> set[str]:
    return set(_FORBIDDEN_AGENT_VIEW_KEYS)


def cleanup_policy_trace_from_events(
    trace_events: list[dict[str, Any]],
    agent_view: dict[str, Any],
) -> dict[str, Any]:
    metric_map = agent_view.get("metric_map") or {}
    total_waypoints = len(metric_map.get("inspection_waypoints") or [])
    visited_waypoints: set[str] = set()
    events = []
    previous_success_tool = ""
    first_cleanup_index: int | None = None
    observed_waypoints_at_first_cleanup = 0
    scan_observe_count = 0
    post_place_observe_count = 0
    cleanup_action_count = 0
    placed_object_count = 0
    for raw in trace_events:
        if raw.get("event") != "response":
            continue
        tool = str(raw.get("tool") or "")
        response = raw.get("response") if isinstance(raw.get("response"), dict) else {}
        if not response.get("ok"):
            continue
        role = _policy_event_role(tool, previous_success_tool)
        waypoint_id = str(response.get("waypoint_id") or "")
        if waypoint_id:
            visited_waypoints.add(waypoint_id)
        if role == "coverage_scan_observe":
            scan_observe_count += 1
        if role == "post_place_observe":
            post_place_observe_count += 1
        if role == "cleanup_action":
            if tool == CLEAN_OBSERVED_OBJECT_TOOL:
                semantic_steps = [
                    step
                    for step in response.get("semantic_steps") or []
                    if isinstance(step, dict) and step.get("ok")
                ]
                cleanup_action_count += max(1, len(semantic_steps))
                if any(
                    str(step.get("phase") or "") in {PLACE_PHASE, PLACE_INSIDE_PHASE}
                    for step in semantic_steps
                ):
                    placed_object_count += 1
            else:
                cleanup_action_count += 1
                if tool in {PLACE_PHASE, PLACE_INSIDE_PHASE}:
                    placed_object_count += 1
            if first_cleanup_index is None:
                first_cleanup_index = len(events)
                observed_waypoints_at_first_cleanup = len(visited_waypoints)
        events.append(
            {
                "index": len(events) + 1,
                "tool": tool,
                "role": role,
                "waypoint_id": waypoint_id,
                "object_id": response.get("object_id", ""),
                "fixture_id": response.get("fixture_id", response.get("receptacle_id", "")),
            }
        )
        previous_success_tool = _terminal_policy_tool(tool, response)
    if cleanup_action_count == 0:
        loop_style = "scan_only"
    elif observed_waypoints_at_first_cleanup < total_waypoints:
        loop_style = "interleaved_cleanup_loop"
    else:
        loop_style = "survey_first_cleanup_loop"
    return {
        "schema": CLEANUP_POLICY_TRACE_SCHEMA,
        "waypoint_source": "static_map_fixture_coverage",
        "loop_style": loop_style,
        "total_waypoints": total_waypoints,
        "observed_waypoint_count": len(visited_waypoints),
        "scan_observe_count": scan_observe_count,
        "cleanup_action_count": cleanup_action_count,
        "placed_object_count": placed_object_count,
        "post_place_observe_count": post_place_observe_count,
        "post_place_observe_complete": post_place_observe_count >= placed_object_count,
        "first_cleanup_before_full_survey": (
            cleanup_action_count > 0 and observed_waypoints_at_first_cleanup < total_waypoints
        ),
        "events": events,
        "public_contract_note": (
            "Waypoint scans are static-map coverage checks. Cleanup actions use "
            "observed_* handles discovered by observe or camera-model policy."
        ),
    }


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


def _policy_event_role(tool: str, previous_success_tool: str) -> str:
    if tool == "navigate_to_waypoint":
        return "coverage_scan_navigation"
    if tool == "observe":
        return (
            "post_place_observe"
            if previous_success_tool
            in {PLACE_PHASE, PLACE_INSIDE_PHASE, CLOSE_RECEPTACLE_PHASE, CLEAN_OBSERVED_OBJECT_TOOL}
            else ("coverage_scan_observe")
        )
    if tool in {
        "navigate_to_object",
        "navigate_to_visual_candidate",
        "pick",
        "navigate_to_receptacle",
        "open_receptacle",
        "place",
        "place_inside",
        "close_receptacle",
        CLEAN_OBSERVED_OBJECT_TOOL,
    }:
        return "cleanup_action"
    return "setup_or_completion"


def _terminal_policy_tool(tool: str, response: dict[str, Any]) -> str:
    if tool != CLEAN_OBSERVED_OBJECT_TOOL:
        return tool
    terminal = CLEAN_OBSERVED_OBJECT_TOOL
    for step in response.get("semantic_steps") or []:
        if not isinstance(step, dict) or not step.get("ok"):
            continue
        phase = str(step.get("phase") or "")
        if phase:
            terminal = phase
    return terminal


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
        x0 = float(index * 3)
        rooms.append(
            {
                "room_id": room_id,
                "room_label": labels[room_id],
                "fixture_ids": sorted(fixture_ids),
                "polygon": [
                    {"x": x0, "y": 0.0},
                    {"x": x0 + 2.0, "y": 0.0},
                    {"x": x0 + 2.0, "y": 2.0},
                    {"x": x0, "y": 2.0},
                ],
                "map_center": {"x": x0 + 1.0, "y": 1.0},
            }
        )
    return rooms


def _inspection_waypoints(rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    waypoints = []
    for room in rooms:
        fixture_ids = list(room["fixture_ids"])
        groups = _split_fixture_groups(fixture_ids)
        for index, group in enumerate(groups, start=1):
            center = room.get("map_center") or {}
            x = float(center.get("x", 0.0))
            y = float(center.get("y", 0.0)) + (index - 1) * 0.45
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


def _visual_candidate_validation_error(candidate: Any) -> dict[str, str] | None:
    if not isinstance(candidate, dict):
        return {"field": "candidate", "reason": "candidate must be an object"}
    for field in ("category", "target_fixture_id", "evidence_note"):
        if not str(candidate.get(field) or "").strip():
            return {"field": field, "reason": f"{field} is required"}
    region_error = _image_region_validation_error(candidate.get("image_region"))
    if region_error is not None:
        return region_error
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
