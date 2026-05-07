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
            objects.append(item)
        return self._ok(
            "scene_objects",
            objects=objects,
            receptacles=[item.to_public_dict() for item in self.scenario.receptacles],
        )

    def goto(self, receptacle_id: str) -> dict[str, Any]:
        self._count("goto")
        if receptacle_id not in self._known_receptacles:
            return self._stale_reference("goto", receptacle_id=receptacle_id)
        previous = self._current_receptacle_id
        self._current_receptacle_id = receptacle_id
        return self._ok(
            "goto",
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

    def place(self, receptacle_id: str) -> dict[str, Any]:
        self._count("place")
        if receptacle_id not in self._known_receptacles:
            return self._stale_reference("place", receptacle_id=receptacle_id)
        if self._held_object_id is None:
            return self._error("place", "not_holding")
        object_id = self._held_object_id
        self._locations[object_id] = receptacle_id
        self._held_object_id = None
        self._current_receptacle_id = receptacle_id
        return self._ok(
            "place",
            primitive_provenance=API_SEMANTIC_PROVENANCE,
            object_id=object_id,
            receptacle_id=receptacle_id,
            location_id=receptacle_id,
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
            tool_event_counts=dict(self.tool_event_counts),
        )

    def _public_state(self) -> dict[str, Any]:
        state = self.scenario.public_payload()
        by_id = {obj["object_id"]: obj for obj in state["objects"]}
        for object_id, location_id in self._locations.items():
            by_id[object_id]["location_id"] = location_id
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
