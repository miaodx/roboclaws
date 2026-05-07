from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from ai2thor.controller import Controller

from roboclaws.core.scene_grid import SceneGrid

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
        platform: Any | None = None,
    ) -> None:
        self.agent_count = agent_count
        self._scene = scene
        self._grid_size = grid_size
        self._scene_grid = SceneGrid(grid_size=grid_size)
        self.field_of_view = field_of_view
        self.server_timeout = server_timeout
        self.server_start_timeout = server_start_timeout
        self._reachable_positions: set[tuple[int, int]] | None = None
        self._overhead_camera_pose: dict[str, Any] | None = None
        self._overhead_camera_id = 0
        self._chase_camera_ids: dict[int, int] = {}
        controller_kwargs: dict[str, Any] = {}
        if platform is not None:
            controller_kwargs["platform"] = platform
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
            **controller_kwargs,
        )
        self._last_event = self._controller.last_event
        self._setup_overhead_camera()

    def _setup_overhead_camera(self) -> None:
        """Add a top-down orthographic third-party camera to the scene."""
        event = self._controller.step(action="GetMapViewCameraProperties", raise_for_failure=True)
        pose = copy.deepcopy(event.metadata["actionReturn"])
        pose["orthographic"] = True
        self._overhead_camera_pose = copy.deepcopy(pose)
        self._controller.step(action="AddThirdPartyCamera", **pose, skyboxColor="white")
        self._last_event = self._controller.last_event
        self._overhead_camera_id = len(self._last_event.events[0].third_party_camera_frames) - 1

    def reset(self) -> None:
        """Reload the current scene from scratch and rebuild engine-side caches.

        AI2-THOR's ``controller.reset()`` drops third-party cameras and resets
        every object/agent pose. The engine caches that go stale must be
        cleared in the same call so callers see a consistent post-reset state:
        reachable positions, the overhead camera, and per-agent chase cameras.
        Chase cameras are re-registered lazily by ``add_chase_cam``.
        """
        self._last_event = self._controller.reset(scene=self._scene)
        self._reachable_positions = None
        self._chase_camera_ids = {}
        self._overhead_camera_pose = None
        self._overhead_camera_id = 0
        self._setup_overhead_camera()

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

    @property
    def grid_size(self) -> float:
        """Public read-only view of the grid size used by AI2-THOR snapping.

        Server-side helpers (``goto``, route planning) need this to convert
        between grid-index tuples returned by ``get_reachable_positions`` and
        world coordinates.
        """
        return self._grid_size

    def get_all_objects(self, agent_id: int = 0) -> list[dict[str, Any]]:
        """Return ALL scene objects (visible or not) from the last event.

        AI2-THOR streams the full object list in every event's metadata; this
        is the cheap counterpart to ``get_agent_state`` whose ``visible_objects``
        only reflects what is currently in the camera cone. Used by the MCP
        ``scene_objects`` tool so an agent can inventory the room before any
        move instead of discovering targets by collision.
        """
        return list(self._last_event.events[agent_id].metadata.get("objects", []))

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
            self._reachable_positions = self._scene_grid.normalize_reachable_positions(positions)
        return self._reachable_positions

    def get_overhead_frame(self) -> np.ndarray:
        """Return the most-recent top-down overhead camera frame as (H, W, 3) uint8."""
        return self._last_event.events[0].third_party_camera_frames[self._overhead_camera_id]

    def get_overhead_camera_properties(self) -> dict[str, Any]:
        """Return the top-down camera pose used to render the overhead frame."""
        if self._overhead_camera_pose is None:
            raise RuntimeError("Overhead camera not initialized")
        return copy.deepcopy(self._overhead_camera_pose)

    def add_chase_cam(self, agent_id: int) -> int:
        """Register a third-party chase camera for an agent and return its camera id."""
        if agent_id in self._chase_camera_ids:
            return self._chase_camera_ids[agent_id]

        pose = self._compute_chase_cam_pose(agent_id)
        self._controller.step(
            action="AddThirdPartyCamera",
            position=pose["position"],
            rotation=pose["rotation"],
            fieldOfView=self.field_of_view,
        )
        self._last_event = self._controller.last_event
        camera_id = len(self._last_event.events[0].third_party_camera_frames) - 1
        self._chase_camera_ids[agent_id] = camera_id
        return camera_id

    def update_chase_cam(self, agent_id: int) -> None:
        """Update an existing chase camera to the agent's current pose."""
        camera_id = self._chase_camera_ids[agent_id]
        pose = self._compute_chase_cam_pose(agent_id)
        self._last_event = self._controller.step(
            action="UpdateThirdPartyCamera",
            thirdPartyCameraId=camera_id,
            position=pose["position"],
            rotation=pose["rotation"],
            fieldOfView=self.field_of_view,
        )

    def get_chase_cam_frame(self, agent_id: int) -> np.ndarray:
        """Return the latest chase-camera frame for an agent."""
        if agent_id not in self._chase_camera_ids:
            raise ValueError(f"No chase camera registered for agent {agent_id}")
        camera_id = self._chase_camera_ids[agent_id]
        return self._last_event.events[0].third_party_camera_frames[camera_id]

    def _compute_chase_cam_pose(self, agent_id: int) -> dict[str, dict[str, float]]:
        state = self.get_agent_state(agent_id)
        yaw_rad = math.radians(float(state.rotation["y"]))
        return {
            "position": {
                "x": float(state.position["x"]) - math.sin(yaw_rad) * 1.0,
                "y": float(state.position["y"]) + 1.5,
                "z": float(state.position["z"]) - math.cos(yaw_rad) * 1.0,
            },
            "rotation": {
                "x": 20.0,
                "y": float(state.rotation["y"]),
                "z": 0.0,
            },
        }

    def close(self) -> None:
        """Stop the AI2-THOR Unity process."""
        self._controller.stop()
