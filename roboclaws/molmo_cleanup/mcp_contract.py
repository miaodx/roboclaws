from __future__ import annotations

from typing import Any

from roboclaws.molmo_cleanup.backend import ApiSemanticCleanupBackend
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.types import CleanupScenario


class MolmoCleanupToolContract:
    """Direct-call MCP-style contract for the cleanup backend.

    The methods intentionally mirror tool names, but this phase does not bind a
    network server. Tests and demos call the contract in process.
    """

    def __init__(self, scenario: CleanupScenario | None = None, backend: Any | None = None):
        self.backend = backend or ApiSemanticCleanupBackend(scenario or build_cleanup_scenario())

    def tool_specs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "observe",
                "description": "Return current public room state without private scoring targets.",
            },
            {
                "name": "scene_objects",
                "description": "List objects and receptacles with current semantic locations.",
            },
            {
                "name": "goto",
                "description": "Move the agent to a known receptacle ID.",
            },
            {
                "name": "pick",
                "description": "Pick up one known pickupable object by stable object ID.",
            },
            {
                "name": "place",
                "description": "Place the held object into a known receptacle ID.",
            },
            {
                "name": "done",
                "description": "Terminate the cleanup and return the private score.",
            },
        ]

    def observe(self) -> dict[str, Any]:
        return self.backend.observe()

    def scene_objects(self, category: str | None = None) -> dict[str, Any]:
        return self.backend.scene_objects(category=category)

    def goto(self, receptacle_id: str) -> dict[str, Any]:
        return self.backend.goto(receptacle_id=receptacle_id)

    def pick(self, object_id: str) -> dict[str, Any]:
        return self.backend.pick(object_id=object_id)

    def place(self, receptacle_id: str) -> dict[str, Any]:
        return self.backend.place(receptacle_id=receptacle_id)

    def done(self, reason: str = "") -> dict[str, Any]:
        return self.backend.done(reason=reason)
