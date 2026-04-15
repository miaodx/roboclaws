from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from ai2thor.controller import Controller

NAVIGATION_ACTIONS: list[str] = [
    "MoveAhead",
    "MoveBack",
    "MoveLeft",
    "MoveRight",
    "RotateLeft",
    "RotateRight",
    "LookUp",
    "LookDown",
    "Teleport",
    "Done",
]


@dataclass
class AgentState:
    """Snapshot of a single agent's state after a step."""

    agent_id: int
    frame: np.ndarray  # (H, W, 3) uint8 RGB
    position: dict[str, float]  # {"x": ..., "y": ..., "z": ...}
    rotation: dict[str, float]  # {"x": ..., "y": ..., "z": ...}
    camera_horizon: float
    visible_objects: list[dict[str, Any]] = field(default_factory=list)
    last_action_success: bool = True
    last_action_error: str = ""


class MultiAgentEngine:
    """AI2-THOR Controller wrapper for multi-agent management.

    Supports iTHOR scenes (FloorPlan1-30, 201-230, 301-330, 401-430).
    Turn-based stepping: one agent per step() call.
    """

    def __init__(
        self,
        scene: str = "FloorPlan201",
        agent_count: int = 2,
        grid_size: float = 0.25,
        rotate_step_degrees: int = 90,
        field_of_view: int = 90,
        width: int = 640,
        height: int = 480,
        server_timeout: float = 100.0,
        server_start_timeout: float = 300.0,
    ) -> None:
        self.agent_count = agent_count
        self._grid_size = grid_size
        self.field_of_view = field_of_view
        self.server_timeout = server_timeout
        self.server_start_timeout = server_start_timeout
        self._reachable_positions: set[tuple[int, int]] | None = None
        self._controller = Controller(
            scene=scene,
            agentCount=agent_count,
            gridSize=grid_size,
            snapToGrid=True,
            rotateStepDegrees=rotate_step_degrees,
            fieldOfView=field_of_view,
            width=width,
            height=height,
            server_timeout=server_timeout,
            server_start_timeout=server_start_timeout,
        )
        self._last_event = self._controller.last_event
        self._setup_overhead_camera()

    def _setup_overhead_camera(self) -> None:
        """Add a top-down orthographic third-party camera to the scene."""
        event = self._controller.step(action="GetMapViewCameraProperties", raise_for_failure=True)
        pose = copy.deepcopy(event.metadata["actionReturn"])
        pose["orthographic"] = True
        self._controller.step(action="AddThirdPartyCamera", **pose, skyboxColor="white")
        self._last_event = self._controller.last_event

    def get_agent_state(self, agent_id: int) -> AgentState:
        """Return the current state for a single agent from the last event."""
        agent_event = self._last_event.events[agent_id]
        metadata = agent_event.metadata
        agent_meta = metadata["agent"]
        return AgentState(
            agent_id=agent_id,
            frame=agent_event.frame,
            position=agent_meta["position"],
            rotation=agent_meta["rotation"],
            camera_horizon=agent_meta["cameraHorizon"],
            visible_objects=[o for o in metadata.get("objects", []) if o.get("visible")],
            last_action_success=metadata["lastActionSuccess"],
            last_action_error=metadata.get("errorMessage", "") or "",
        )

    def get_all_agent_states(self) -> list[AgentState]:
        """Return current state for every agent."""
        return [self.get_agent_state(i) for i in range(self.agent_count)]

    def step(self, agent_id: int, action: str, **kwargs: Any) -> AgentState:
        """Execute an action for one agent; return that agent's updated state.

        Args:
            agent_id: Zero-based agent index.
            action: One of NAVIGATION_ACTIONS (or any valid AI2-THOR action name).
            **kwargs: Extra keyword arguments forwarded to controller.step().

        Returns:
            AgentState reflecting the result of the action.
        """
        self._last_event = self._controller.step(action=action, agentId=agent_id, **kwargs)
        return self.get_agent_state(agent_id)

    def get_reachable_positions(self) -> set[tuple[int, int]]:
        """Return the cached set of reachable grid cells as (ix, iz) tuples.

        Calls AI2-THOR's GetReachablePositions once after scene reset and caches the result.
        Cell indices use the same world→grid projection as the game modules:
        ix = round(x / grid_size), iz = round(z / grid_size).
        """
        if self._reachable_positions is None:
            event = self._controller.step(action="GetReachablePositions")
            positions = event.metadata.get("actionReturn", []) or []
            self._reachable_positions = {
                (round(p["x"] / self._grid_size), round(p["z"] / self._grid_size))
                for p in positions
            }
        return self._reachable_positions

    def get_overhead_frame(self) -> np.ndarray:
        """Return the most-recent top-down overhead camera frame as (H, W, 3) uint8."""
        return self._last_event.events[0].third_party_camera_frames[-1]

    def close(self) -> None:
        """Stop the AI2-THOR Unity process."""
        self._controller.stop()
