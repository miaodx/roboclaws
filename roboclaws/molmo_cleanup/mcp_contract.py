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
                "description": (
                    "Call first. Return current public room state without private scoring targets."
                ),
            },
            {
                "name": "scene_objects",
                "description": (
                    "List global public objects and receptacles with current semantic locations. "
                    "Current-contract shortcut; use it to choose the cleanup sequence yourself."
                ),
            },
            {
                "name": "goto",
                "description": "Move the agent to a known receptacle ID.",
            },
            {
                "name": "navigate_to_object",
                "description": (
                    "First semantic substep per object: navigate to the object before pick."
                ),
            },
            {
                "name": "navigate_to_receptacle",
                "description": (
                    "After pick, navigate to the chosen target receptacle before placing."
                ),
            },
            {
                "name": "pick",
                "description": "Pick up one known pickupable object by stable object ID.",
            },
            {
                "name": "open_receptacle",
                "description": (
                    "Open fridge-like targets before place_inside; do this before placing food."
                ),
            },
            {
                "name": "place",
                "description": "Place the held object into a known receptacle ID.",
            },
            {
                "name": "place_inside",
                "description": "Place the held object inside an opened fridge-like receptacle.",
            },
            {
                "name": "object_done",
                "description": (
                    "Call after each object is placed to record public completion readback."
                ),
            },
            {
                "name": "done",
                "description": "Call only after all intended objects have object_done readback.",
            },
        ]

    def observe(self) -> dict[str, Any]:
        return self.backend.observe()

    def scene_objects(self, category: str | None = None) -> dict[str, Any]:
        return self.backend.scene_objects(category=category)

    def goto(self, receptacle_id: str) -> dict[str, Any]:
        return self.backend.goto(receptacle_id=receptacle_id)

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        return self.backend.navigate_to_object(object_id=object_id)

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

    def object_done(self, object_id: str, receptacle_id: str) -> dict[str, Any]:
        return self.backend.object_done(object_id=object_id, receptacle_id=receptacle_id)

    def done(self, reason: str = "") -> dict[str, Any]:
        return self.backend.done(reason=reason)
