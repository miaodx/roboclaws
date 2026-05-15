from __future__ import annotations

from typing import Any

from roboclaws.molmo_cleanup.backend import ApiSemanticCleanupBackend
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.types import CleanupScenario


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
