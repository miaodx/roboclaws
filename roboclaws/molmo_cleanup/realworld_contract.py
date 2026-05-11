from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.planner_observed_binding import (
    observed_handle_planner_binding,
)
from roboclaws.molmo_cleanup.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)
from roboclaws.molmo_cleanup.types import CleanupScenario

REALWORLD_CONTRACT = "realworld_cleanup_v1"
DETERMINISTIC_SWEEP_POLICY = "deterministic_sweep_baseline"
DEFAULT_REALWORLD_TASK = "帮我收拾这个房间"
VISIBLE_OBJECT_DETECTIONS_MODE = "visible_object_detections"
RAW_FPV_ONLY_MODE = "raw_fpv_only"
CAMERA_MODEL_POLICY_MODE = "camera_model_policy"
CAMERA_MODEL_POLICY_SCHEMA = "camera_model_policy_v1"
CAMERA_MODEL_POLICY_NAME = "camera_model_policy_baseline"
SIMULATED_CAMERA_MODEL_PROVENANCE = "simulated_camera_model"
REALWORLD_PERCEPTION_MODES = frozenset(
    {
        VISIBLE_OBJECT_DETECTIONS_MODE,
        RAW_FPV_ONLY_MODE,
        CAMERA_MODEL_POLICY_MODE,
    }
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
    (("dish", "cup", "mug", "plate", "bowl"), ("sink", "countertop")),
    (("book", "newspaper"), ("shelvingunit", "bookshelf", "shelf", "desk")),
    (("food", "apple", "bread", "egg", "potato", "lettuce"), ("fridge", "refrigerator")),
    (("remotecontrol", "remote", "electronics"), ("tvstand", "tv stand")),
    (("pillow", "teddybear", "teddy"), ("bed", "sofa")),
    (("linen", "towel"), ("laundryhamper", "laundry hamper", "hamper")),
    (("toy", "toycar"), ("toybin", "toy bin")),
)


class RealWorldCleanupContract:
    """ADR-0003 public/private cleanup contract.

    The wrapped ``MolmoCleanupToolContract`` still owns state mutation and
    deterministic private scoring. This contract is the public agent boundary:
    it exposes metric navigation, room-level fixture hints, and robot-local
    observed object handles instead of the current-contract global inventory.
    """

    def __init__(
        self,
        contract: MolmoCleanupToolContract,
        *,
        task_prompt: str = DEFAULT_REALWORLD_TASK,
        fixture_hint_mode: str = "room_only",
        perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
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
        self._raw_fpv_observations: list[dict[str, Any]] = []
        self._camera_model_policy_events: list[dict[str, Any]] = []
        self._handled_handles: set[str] = set()
        self._held_handle: str | None = None
        self._current_object_handle: str | None = None
        self._current_receptacle_for_handle: tuple[str, str] | None = None
        self._opened_receptacle_for_handle: tuple[str, str] | None = None
        self._initial_locations = self.backend.object_locations()

    def public_tool_names(self) -> list[str]:
        return [
            "metric_map",
            "fixture_hints",
            "navigate_to_room",
            "navigate_to_waypoint",
            "observe",
            "infer_camera_model_candidates",
            "inspect_visible_object",
            "navigate_to_object",
            "pick",
            "navigate_to_receptacle",
            "open_receptacle",
            "place",
            "place_inside",
            "done",
        ]

    def public_receptacles_by_id(self) -> dict[str, dict[str, Any]]:
        return {fixture_id: dict(fixture) for fixture_id, fixture in self._fixtures.items()}

    def metric_map(self) -> dict[str, Any]:
        return self._ok(
            "metric_map",
            contract=REALWORLD_CONTRACT,
            rooms=[
                {
                    "room_id": room["room_id"],
                    "room_label": room["room_label"],
                    "fixture_count": len(room["fixture_ids"]),
                }
                for room in self._rooms
            ],
            driveable_ways=_driveable_ways(self._rooms),
            robot_pose={
                "room_id": self._current_room_id(),
                "waypoint_id": self._current_waypoint_id,
                "pose_source": "metric_map_semantic_waypoint",
            },
            inspection_waypoints=[
                {
                    "waypoint_id": item["waypoint_id"],
                    "room_id": item["room_id"],
                    "label": item["label"],
                    "coverage_estimate": item["coverage_estimate"],
                    "visited": item["waypoint_id"] in self._observed_waypoint_ids,
                }
                for item in self._waypoints
            ],
            public_contract_note=(
                "No movable-object locations, generated mess set, target count, "
                "or acceptable destination sets are included."
            ),
        )

    def fixture_hints(self) -> dict[str, Any]:
        rooms = []
        for room in self._rooms:
            fixtures = []
            for fixture_id in room["fixture_ids"]:
                fixture = self._fixtures[fixture_id]
                item = {
                    "fixture_id": fixture_id,
                    "category": fixture.get("category") or fixture.get("name", ""),
                    "name": fixture.get("name", fixture_id),
                    "affordances": _fixture_affordances(fixture),
                    "position_detail": self.fixture_hint_mode,
                }
                if self.fixture_hint_mode == "exact_fixtures":
                    item["room_position"] = "operator_selected_exact_fixture_hint"
                fixtures.append(item)
            rooms.append(
                {
                    "room_id": room["room_id"],
                    "room_label": room["room_label"],
                    "fixtures": fixtures,
                }
            )
        return self._ok(
            "fixture_hints",
            contract=REALWORLD_CONTRACT,
            fixture_hint_mode=self.fixture_hint_mode,
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
        self._current_waypoint_id = waypoint_id
        fixture_id = _first_fixture_for_waypoint(waypoint)
        navigation = None
        if fixture_id is not None:
            navigation = self.contract.navigate_to_receptacle(fixture_id)
        return self._ok(
            "navigate_to_waypoint",
            primitive_provenance=API_SEMANTIC_PROVENANCE,
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
                    "Camera model policy mode: call infer_camera_model_candidates "
                    "with this observation_id to register model-labelled cleanup "
                    "candidates. Built-in visible_object_detections remain empty."
                )
                perception_source = CAMERA_MODEL_POLICY_MODE
                camera_model_available = True
            else:
                instruction = (
                    "Raw FPV-only mode: infer any cleanup candidates from the FPV image. "
                    "No structured movable-object detections, categories, support estimates, "
                    "target labels, or generated mess truth are provided."
                )
                perception_source = RAW_FPV_ONLY_MODE
                camera_model_available = False
            return self._ok(
                "observe",
                contract=REALWORLD_CONTRACT,
                current_room_id=waypoint["room_id"],
                waypoint_id=waypoint["waypoint_id"],
                perception_mode=self.perception_mode,
                perception_source=perception_source,
                structured_detections_available=False,
                visible_object_detections=[],
                raw_fpv_observation=raw_observation,
                camera_model_policy_available=camera_model_available,
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
            perception_mode=self.perception_mode,
            structured_detections_available=True,
            visible_object_detections=detections,
            held_object_id=self._held_handle,
            perception_source="robot_local_visible_object_detections",
            private_target_truth_included=False,
        )

    def infer_camera_model_candidates(
        self,
        observation_id: str | None = None,
        *,
        model_provenance: str = SIMULATED_CAMERA_MODEL_PROVENANCE,
    ) -> dict[str, Any]:
        if self.perception_mode != CAMERA_MODEL_POLICY_MODE:
            return self._error(
                "infer_camera_model_candidates",
                "unsupported_perception_mode",
                perception_mode=self.perception_mode,
            )
        raw_observation = self._raw_fpv_observation_by_id(observation_id)
        if raw_observation is None:
            return self._error(
                "infer_camera_model_candidates",
                "missing_raw_fpv_observation",
                observation_id=observation_id or "",
            )
        waypoint = self._waypoint_by_id(str(raw_observation["waypoint_id"]))
        if waypoint is None:
            return self._error(
                "infer_camera_model_candidates",
                "missing_waypoint",
                observation_id=str(raw_observation["observation_id"]),
            )
        candidates = self._camera_model_candidates_for_waypoint(
            waypoint,
            observation_id=str(raw_observation["observation_id"]),
            model_provenance=model_provenance,
        )
        evidence = {
            "schema": CAMERA_MODEL_POLICY_SCHEMA,
            "perception_mode": CAMERA_MODEL_POLICY_MODE,
            "observation_id": str(raw_observation["observation_id"]),
            "waypoint_id": str(raw_observation["waypoint_id"]),
            "room_id": str(raw_observation["room_id"]),
            "model_provenance": model_provenance,
            "candidate_count": len(candidates),
            "registered_observed_handles": [str(item["object_id"]) for item in candidates],
            "private_truth_included": False,
            "policy_note": (
                "Deterministic simulated camera-model evidence derived from the "
                "current public raw FPV observation; not real VLM pixel inference."
            ),
        }
        _assert_no_forbidden_agent_view_keys(evidence)
        self._camera_model_policy_events.append(evidence)
        return self._ok(
            "infer_camera_model_candidates",
            contract=REALWORLD_CONTRACT,
            camera_model_policy=evidence,
            camera_model_candidates=candidates,
            visible_object_detections=[],
            private_target_truth_included=False,
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
            return self._error("navigate_to_object", "stale_reference", object_id=object_id)
        response = self.contract.navigate_to_object(internal_id)
        if not response.get("ok"):
            return self._public_error_from_private("navigate_to_object", object_id, response)
        self._current_object_handle = object_id
        return self._ok(
            "navigate_to_object",
            object_id=object_id,
            primitive_provenance=response.get(
                "primitive_provenance",
                API_SEMANTIC_PROVENANCE,
            ),
            source_receptacle_id=response.get("source_receptacle_id"),
            previous_receptacle_id=response.get("previous_receptacle_id"),
            location_id=response.get("location_id"),
            state_mutation=response.get("state_mutation"),
            navigation_status=response.get("status"),
        )

    def pick(self, object_id: str) -> dict[str, Any]:
        internal_id = self._internal_object_id(object_id)
        if internal_id is None:
            return self._error("pick", "stale_reference", object_id=object_id)
        if getattr(self, "_current_object_handle", None) != object_id:
            return self._semantic_order_error(
                "pick",
                required_tool="navigate_to_object",
                object_id=object_id,
                recovery_hint=(
                    "Call navigate_to_object with this observed object handle before pick. "
                    "The ADR-0003 clean loop is navigate_to_object -> pick -> "
                    "navigate_to_receptacle -> open_receptacle? -> place/place_inside."
                ),
            )
        picked = self.contract.pick(internal_id)
        if picked.get("ok"):
            self._held_handle = object_id
            self._current_object_handle = None
            self._current_receptacle_for_handle = None
            self._opened_receptacle_for_handle = None
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
        self._current_receptacle_for_handle = (self._held_handle, fixture_id)
        self._opened_receptacle_for_handle = None
        return self._ok(
            "navigate_to_receptacle",
            object_id=self._held_handle,
            receptacle_id=fixture_id,
            fixture_id=fixture_id,
            primitive_provenance=response.get(
                "primitive_provenance",
                API_SEMANTIC_PROVENANCE,
            ),
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
                    "Fridge-like cleanup must be nav -> open -> place_inside."
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

    def done(self, reason: str = "") -> dict[str, Any]:
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

    def agent_view_payload(self) -> dict[str, Any]:
        observed_objects = [
            dict(self._detections_by_handle[handle])
            for handle in sorted(self._detections_by_handle)
        ]
        payload = {
            "contract": REALWORLD_CONTRACT,
            "perception_mode": self.perception_mode,
            "structured_detections_available": self.perception_mode
            == VISIBLE_OBJECT_DETECTIONS_MODE,
            "metric_map": self.metric_map(),
            "fixture_hints": self.fixture_hints(),
            "observed_objects": observed_objects,
            "raw_fpv_observations": [dict(item) for item in self._raw_fpv_observations],
            "camera_model_policy_evidence": self.camera_model_policy_payload(),
            "observed_waypoint_ids": sorted(self._observed_waypoint_ids),
            "public_tool_names": self.public_tool_names(),
            "forbidden_private_fields_absent": True,
        }
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

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
            self._detections_by_handle[handle] = detection
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
            _assert_no_forbidden_agent_view_keys(detection)
            self._detections_by_handle[handle] = detection
            candidates.append(dict(detection))
        return sorted(candidates, key=lambda item: str(item["object_id"]))

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
            "image_artifacts": {},
            "artifact_status": "pending_robot_view_capture",
            "public_contract_note": (
                "No structured movable-object detections, categories, support estimates, "
                "target labels, or private scoring truth are included."
            ),
        }
        self._raw_fpv_observations.append(item)
        return dict(item)

    def _raw_fpv_observation_by_id(self, observation_id: str | None) -> dict[str, Any] | None:
        if observation_id:
            for item in self._raw_fpv_observations:
                if item.get("observation_id") == observation_id:
                    return item
            return None
        return self._raw_fpv_observations[-1] if self._raw_fpv_observations else None

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
    ) -> dict[str, Any]:
        if not response.get("ok"):
            return self._error(
                tool, str(response.get("error_reason", "error")), fixture_id=fixture_id
            )
        return self._ok(
            tool,
            fixture_id=fixture_id,
            receptacle_id=fixture_id,
            object_id=self._held_handle,
            primitive_provenance=response.get("primitive_provenance", API_SEMANTIC_PROVENANCE),
            opened=response.get("opened"),
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

    def _waypoint_by_id(self, waypoint_id: str) -> dict[str, Any] | None:
        return next((item for item in self._waypoints if item["waypoint_id"] == waypoint_id), None)

    def _handle_for_object(self, object_id: str) -> str:
        existing = self._observed_handles_by_object_id.get(object_id)
        if existing is not None:
            return existing
        handle = f"observed_{len(self._observed_handles_by_object_id) + 1:03d}"
        self._observed_handles_by_object_id[object_id] = handle
        self._object_ids_by_handle[handle] = object_id
        return handle

    def _internal_object_id(self, handle: str) -> str | None:
        return self._object_ids_by_handle.get(handle)

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
            "semantic_loop_variant": "navigate-pick-navigate-open-place",
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


def _rooms_from_fixtures(fixtures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_room: dict[str, list[str]] = defaultdict(list)
    labels: dict[str, str] = {}
    for fixture_id, fixture in fixtures.items():
        raw_room = str(fixture.get("room_area", "unknown"))
        room_id = _room_id(raw_room)
        by_room[room_id].append(fixture_id)
        labels[room_id] = raw_room.replace("_", " ")
    return [
        {
            "room_id": room_id,
            "room_label": labels[room_id],
            "fixture_ids": sorted(fixture_ids),
        }
        for room_id, fixture_ids in sorted(by_room.items())
    ]


def _inspection_waypoints(rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    waypoints = []
    for room in rooms:
        fixture_ids = list(room["fixture_ids"])
        groups = _split_fixture_groups(fixture_ids)
        for index, group in enumerate(groups, start=1):
            waypoints.append(
                {
                    "waypoint_id": f"{room['room_id']}_scan_{index}",
                    "room_id": room["room_id"],
                    "label": f"{room['room_label']} scan {index}",
                    "fixture_ids": group,
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
    name = f"{fixture.get('name', '')} {fixture.get('category', '')}".lower()
    affordances = ["place"]
    if "fridge" in name or "refrigerator" in name:
        affordances.extend(["open", "place_inside"])
    return affordances


def _fixture_requires_open(fixture: dict[str, Any]) -> bool:
    return {"open", "place_inside"}.issubset(set(_fixture_affordances(fixture)))


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
