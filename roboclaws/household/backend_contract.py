from __future__ import annotations

from typing import Any

from roboclaws.household.backend import ApiSemanticCleanupBackend
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.types import CleanupScenario


class CleanupBackendSession:
    """Direct-call state mutation session for ADR-0003 cleanup surfaces.

    This is not an agent-facing MCP surface. It keeps the semantic cleanup
    backend callable by the ADR-0003 public/private contract without exposing
    legacy global-inventory helpers such as ``scene_objects`` or
    ``object_done``.
    """

    def __init__(self, scenario: CleanupScenario | None = None, backend: Any | None = None):
        self.backend = backend or ApiSemanticCleanupBackend(scenario or build_cleanup_scenario())

    def observe(self) -> dict[str, Any]:
        return self.backend.observe()

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        return self.backend.navigate_to_object(object_id=object_id)

    def navigate_to_waypoint(self, waypoint: dict[str, Any]) -> dict[str, Any]:
        navigator = getattr(self.backend, "navigate_to_waypoint", None)
        if callable(navigator):
            return navigator(waypoint=waypoint)
        fixture_ids = waypoint.get("fixture_ids") or []
        fixture_id = str(fixture_ids[0]) if fixture_ids else ""
        if not fixture_id:
            return {
                "ok": True,
                "tool": "navigate_to_waypoint",
                "status": "ok",
                "state_mutation": "agent_pose_semantic",
                "backend_pose_mutation_available": False,
            }
        navigation = dict(self.backend.navigate_to_receptacle(receptacle_id=fixture_id))
        navigation["tool"] = "navigate_to_waypoint"
        navigation["waypoint_id"] = str(waypoint.get("waypoint_id") or "")
        navigation["fallback_receptacle_id"] = fixture_id
        navigation["backend_pose_mutation_available"] = True
        return navigation

    def navigate_to_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self.backend.navigate_to_receptacle(receptacle_id=receptacle_id)

    def pick(self, object_id: str) -> dict[str, Any]:
        return self.backend.pick(object_id=object_id)

    def open_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self.backend.open_receptacle(receptacle_id=receptacle_id)

    def place(self, receptacle_id: str) -> dict[str, Any]:
        return self.backend.place(receptacle_id=receptacle_id)

    def place_inside(self, receptacle_id: str) -> dict[str, Any]:
        return self.backend.place_inside(receptacle_id=receptacle_id)

    def close_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self.backend.close_receptacle(receptacle_id=receptacle_id)

    def done(self, reason: str = "") -> dict[str, Any]:
        return self.backend.done(reason=reason)
