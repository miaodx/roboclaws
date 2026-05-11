from __future__ import annotations

from collections import Counter
from typing import Any

from roboclaws.molmo_cleanup.scoring import score_cleanup
from roboclaws.molmo_cleanup.types import CleanupScenario

API_SEMANTIC_PROVENANCE = "api_semantic"
HELD_LOCATION_ID = "held_by_agent"


class ApiSemanticCleanupBackend:
    """Small semantic cleanup backend with MolmoSpaces-shaped object effects."""

    def __init__(self, scenario: CleanupScenario):
        self.scenario = scenario
        self._locations = scenario.object_locations()
        self._known_objects = {obj.object_id: obj for obj in scenario.objects}
        self._known_receptacles = {item.receptacle_id: item for item in scenario.receptacles}
        self._held_object_id: str | None = None
        self._current_receptacle_id = "floor_01"
        self._open_receptacle_ids: set[str] = set()
        self._containment: dict[str, dict[str, str]] = {}
        self.tool_event_counts: Counter[str] = Counter()

    @property
    def held_object_id(self) -> str | None:
        return self._held_object_id

    @property
    def current_receptacle_id(self) -> str:
        return self._current_receptacle_id

    def object_locations(self) -> dict[str, str]:
        return dict(self._locations)

    def observe(self) -> dict[str, Any]:
        self._count("observe")
        return self._ok(
            "observe",
            scenario=self._public_state(),
            current_receptacle_id=self._current_receptacle_id,
            held_object_id=self._held_object_id,
        )

    def scene_objects(self, category: str | None = None) -> dict[str, Any]:
        self._count("scene_objects")
        objects = []
        for obj in self.scenario.objects:
            if category is not None and obj.category != category:
                continue
            item = obj.to_public_dict()
            item["location_id"] = self._locations[obj.object_id]
            containment = self._containment.get(obj.object_id)
            if containment is not None:
                item.update(containment)
            objects.append(item)
        return self._ok(
            "scene_objects",
            objects=objects,
            receptacles=[item.to_public_dict() for item in self.scenario.receptacles],
        )

    def goto(self, receptacle_id: str) -> dict[str, Any]:
        self._count("goto")
        return self._navigate_to_receptacle("goto", receptacle_id)

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        self._count("navigate_to_object")
        obj = self._known_objects.get(object_id)
        if obj is None:
            return self._stale_reference("navigate_to_object", object_id=object_id)
        location_id = self._locations.get(object_id)
        if location_id in {None, HELD_LOCATION_ID}:
            return self._error(
                "navigate_to_object",
                "object_not_at_public_location",
                object_id=object_id,
            )
        previous = self._current_receptacle_id
        self._current_receptacle_id = str(location_id)
        return self._ok(
            "navigate_to_object",
            primitive_provenance=API_SEMANTIC_PROVENANCE,
            object_id=object_id,
            source_receptacle_id=str(location_id),
            previous_receptacle_id=previous,
            location_id=str(location_id),
        )

    def navigate_to_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        self._count("navigate_to_receptacle")
        return self._navigate_to_receptacle("navigate_to_receptacle", receptacle_id)

    def _navigate_to_receptacle(self, tool: str, receptacle_id: str) -> dict[str, Any]:
        if receptacle_id not in self._known_receptacles:
            return self._stale_reference(tool, receptacle_id=receptacle_id)
        previous = self._current_receptacle_id
        self._current_receptacle_id = receptacle_id
        return self._ok(
            tool,
            primitive_provenance=API_SEMANTIC_PROVENANCE,
            receptacle_id=receptacle_id,
            previous_receptacle_id=previous,
        )

    def pick(self, object_id: str) -> dict[str, Any]:
        self._count("pick")
        obj = self._known_objects.get(object_id)
        if obj is None:
            return self._stale_reference("pick", object_id=object_id)
        if not obj.pickupable:
            return self._error("pick", "not_pickupable", object_id=object_id)
        if self._held_object_id is not None:
            return self._error("pick", "already_holding", held_object_id=self._held_object_id)
        previous_location_id = self._locations[object_id]
        self._held_object_id = object_id
        self._locations[object_id] = HELD_LOCATION_ID
        return self._ok(
            "pick",
            primitive_provenance=API_SEMANTIC_PROVENANCE,
            object_id=object_id,
            previous_location_id=previous_location_id,
            location_id=HELD_LOCATION_ID,
        )

    def open_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        self._count("open_receptacle")
        receptacle = self._known_receptacles.get(receptacle_id)
        if receptacle is None:
            return self._stale_reference("open_receptacle", receptacle_id=receptacle_id)
        opened = "fridge" in receptacle.name.lower() or "refrigerator" in receptacle.name.lower()
        if opened:
            self._open_receptacle_ids.add(receptacle_id)
        return self._ok(
            "open_receptacle",
            primitive_provenance=API_SEMANTIC_PROVENANCE,
            receptacle_id=receptacle_id,
            opened=opened,
            state_mutation="semantic_open_state",
        )

    def place(self, receptacle_id: str) -> dict[str, Any]:
        self._count("place")
        return self._place_at_receptacle("place", receptacle_id, relation="on")

    def place_inside(self, receptacle_id: str) -> dict[str, Any]:
        self._count("place_inside")
        return self._place_at_receptacle("place_inside", receptacle_id, relation="inside")

    def _place_at_receptacle(
        self,
        tool: str,
        receptacle_id: str,
        *,
        relation: str,
    ) -> dict[str, Any]:
        if receptacle_id not in self._known_receptacles:
            return self._stale_reference(tool, receptacle_id=receptacle_id)
        if self._held_object_id is None:
            return self._error(tool, "not_holding")
        object_id = self._held_object_id
        self._locations[object_id] = receptacle_id
        self._held_object_id = None
        self._current_receptacle_id = receptacle_id
        self._containment[object_id] = {
            "contained_in": receptacle_id if relation == "inside" else "",
            "location_relation": relation,
        }
        return self._ok(
            tool,
            primitive_provenance=API_SEMANTIC_PROVENANCE,
            object_id=object_id,
            receptacle_id=receptacle_id,
            location_id=receptacle_id,
            contained_in=receptacle_id if relation == "inside" else None,
            location_relation=relation,
        )

    def object_done(self, object_id: str, receptacle_id: str) -> dict[str, Any]:
        self._count("object_done")
        if object_id not in self._known_objects:
            return self._stale_reference("object_done", object_id=object_id)
        if receptacle_id not in self._known_receptacles:
            return self._stale_reference("object_done", receptacle_id=receptacle_id)
        containment = self._containment.get(object_id, {})
        actual_location = self._locations.get(object_id)
        return self._ok(
            "object_done",
            object_id=object_id,
            receptacle_id=receptacle_id,
            location_id=actual_location,
            contained_in=containment.get("contained_in") or None,
            location_relation=containment.get("location_relation") or "on",
            matches_expected_location=actual_location == receptacle_id,
        )

    def done(self, reason: str = "") -> dict[str, Any]:
        self._count("done")
        score = score_cleanup(self._locations, self.scenario.private_manifest)
        return self._ok(
            "done",
            reason=reason,
            cleanup_status=score.status,
            score=score.to_dict(),
            final_locations=self.object_locations(),
            final_containment=dict(self._containment),
            tool_event_counts=dict(self.tool_event_counts),
        )

    def _public_state(self) -> dict[str, Any]:
        state = self.scenario.public_payload()
        by_id = {obj["object_id"]: obj for obj in state["objects"]}
        for object_id, location_id in self._locations.items():
            by_id[object_id]["location_id"] = location_id
            containment = self._containment.get(object_id)
            if containment is not None:
                by_id[object_id].update(containment)
        return state

    def _count(self, tool: str) -> None:
        self.tool_event_counts[f"{tool}:request"] += 1

    @staticmethod
    def _ok(tool: str, **payload: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "tool": tool,
            "status": "ok",
            **payload,
        }

    @staticmethod
    def _error(tool: str, error_reason: str, **payload: Any) -> dict[str, Any]:
        return {
            "ok": False,
            "tool": tool,
            "status": "error",
            "error_reason": error_reason,
            **payload,
        }

    def _stale_reference(self, tool: str, **payload: Any) -> dict[str, Any]:
        return self._error(tool, "stale_reference", **payload)
