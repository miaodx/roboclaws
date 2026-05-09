from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)
from roboclaws.molmo_cleanup.types import CleanupScenario

REALWORLD_CONTRACT = "realworld_cleanup_v1"
DETERMINISTIC_SWEEP_POLICY = "deterministic_sweep_baseline"
DEFAULT_REALWORLD_TASK = "帮我收拾这个房间"

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
    ) -> None:
        if fixture_hint_mode not in {"room_only", "exact_fixtures"}:
            raise ValueError("fixture_hint_mode must be room_only or exact_fixtures")
        self.contract = contract
        self.backend = contract.backend
        self.scenario: CleanupScenario = contract.backend.scenario
        self.task_prompt = task_prompt
        self.fixture_hint_mode = fixture_hint_mode
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
        self._handled_handles: set[str] = set()
        self._held_handle: str | None = None
        self._current_object_handle: str | None = None
        self._current_receptacle_id: str | None = None
        self._initial_locations = self.backend.object_locations()

    def public_tool_names(self) -> list[str]:
        return [
            "metric_map",
            "fixture_hints",
            "navigate_to_room",
            "navigate_to_waypoint",
            "observe",
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
        detections = self._visible_detections_for_waypoint(waypoint)
        return self._ok(
            "observe",
            contract=REALWORLD_CONTRACT,
            current_room_id=waypoint["room_id"],
            waypoint_id=waypoint["waypoint_id"],
            visible_object_detections=detections,
            held_object_id=self._held_handle,
            perception_source="robot_local_visible_object_detections",
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
        navigate = None
        if getattr(self, "_current_object_handle", None) != object_id:
            navigate = self.contract.navigate_to_object(internal_id)
            if not navigate.get("ok"):
                return self._public_error_from_private("pick", object_id, navigate)
        picked = self.contract.pick(internal_id)
        if picked.get("ok"):
            self._held_handle = object_id
            self._current_object_handle = None
        return self._public_manipulation_response("pick", object_id, picked, navigate=navigate)

    def navigate_to_receptacle(self, fixture_id: str) -> dict[str, Any]:
        if fixture_id not in self._fixtures:
            return self._error("navigate_to_receptacle", "stale_reference", fixture_id=fixture_id)
        response = self.contract.navigate_to_receptacle(fixture_id)
        if not response.get("ok"):
            return self._public_error_from_private(
                "navigate_to_receptacle",
                self._held_handle or "",
                response,
            )
        self._current_receptacle_id = fixture_id
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
        opened = self.contract.open_receptacle(fixture_id)
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
            "metric_map": self.metric_map(),
            "fixture_hints": self.fixture_hints(),
            "observed_objects": observed_objects,
            "observed_waypoint_ids": sorted(self._observed_waypoint_ids),
            "public_tool_names": self.public_tool_names(),
            "forbidden_private_fields_absent": True,
        }
        _assert_no_forbidden_agent_view_keys(payload)
        return payload

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

    def _place(self, fixture_id: str, *, inside: bool) -> dict[str, Any]:
        if fixture_id not in self._fixtures:
            return self._error(
                "place_inside" if inside else "place", "stale_reference", fixture_id=fixture_id
            )
        handle = self._held_handle
        if handle is None:
            return self._error("place_inside" if inside else "place", "not_holding")
        navigate = None
        if getattr(self, "_current_receptacle_id", None) != fixture_id:
            navigate = self.contract.navigate_to_receptacle(fixture_id)
            if not navigate.get("ok"):
                return self._public_error_from_private(
                    "place_inside" if inside else "place", handle, navigate
                )
        placed = (
            self.contract.place_inside(fixture_id) if inside else self.contract.place(fixture_id)
        )
        if placed.get("ok"):
            self._handled_handles.add(handle)
            self._held_handle = None
            self._current_receptacle_id = fixture_id
        return self._public_manipulation_response(
            "place_inside" if inside else "place",
            handle,
            placed,
            fixture_id=fixture_id,
            navigate=navigate,
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
