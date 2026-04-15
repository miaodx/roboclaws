from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.vlm import VLMProvider

_MOVE_ACTIONS: frozenset[str] = frozenset({"MoveAhead", "MoveBack", "MoveLeft", "MoveRight"})
_DECISION_ACTIONS: tuple[str, ...] = (
    "MoveAhead",
    "MoveBack",
    "MoveLeft",
    "MoveRight",
    "RotateLeft",
    "RotateRight",
)


def _pos_to_cell(pos: dict[str, float], grid_size: float) -> tuple[int, int]:
    """Convert a continuous (x, z) position to a discrete grid cell index."""
    return (round(pos["x"] / grid_size), round(pos["z"] / grid_size))


@dataclass
class CoverageResult:
    """Final outcome of a cooperative coverage game."""

    cells_covered: int  # total unique cells covered by all agents
    coverage_pct: float  # cells_covered / total_cells * 100 (0.0 if total_cells unknown)
    contribution: dict[int, int]  # agent_id → cells first covered by this agent
    contribution_ratio: dict[int, float]  # agent_id → contribution / cells_covered
    work_balance: float  # min_contribution / max_contribution; 1.0 if single agent or all equal
    total_steps: int
    termination_reason: str  # "coverage_reached" | "max_steps"


class CoverageGame:
    """Cooperative area coverage game.

    Rules
    -----
    * Agents cooperate to cover as much of the environment as possible.
    * When ground-truth reachable cells are available, a cell is "covered" once it
      falls inside any agent's view cone.
    * Without reachable cells, coverage falls back to the current occupied cell so
      mock/unit-test flows remain deterministic.
    * Agents take turns in round-robin order (one step per agent per round).
    * The game ends when coverage reaches COVERAGE_TARGET (95 %) or max_steps is reached.

    Metrics
    -------
    * Total cells covered and coverage percentage (if total_cells is known).
    * Per-agent contribution: cells first covered by each agent.
    * Contribution ratio: each agent's share of total covered cells.
    * Work balance: min_contribution / max_contribution (1.0 = perfectly even workload).
    """

    COVERAGE_TARGET: float = 0.95
    VIEW_DISTANCE_METRES: float = 1.5
    ACTION_SPACE: tuple[str, ...] = _DECISION_ACTIONS
    SAFE_FALLBACK_ACTION: str = "RotateRight"

    def __init__(
        self,
        engine: MultiAgentEngine,
        provider: VLMProvider,
        max_steps: int = 200,
        grid_size: float = 0.25,
        total_cells: int | None = None,
        reachable_cells: set[tuple[int, int]] | None = None,
    ) -> None:
        """Initialise the game.

        Args:
            engine: MultiAgentEngine wrapping the AI2-THOR scene.
            provider: VLMProvider used for agent decisions.
            max_steps: Maximum number of individual agent steps before the game ends.
            grid_size: Grid cell edge length in metres (must match engine's gridSize).
            total_cells: Known count of reachable floor cells; enables the 95% termination
                condition.  Pass None to derive from reachable_cells or disable termination.
            reachable_cells: Ground-truth set of reachable grid cells from AI2-THOR's
                GetReachablePositions.  When provided and total_cells is None, total_cells
                defaults to len(reachable_cells), enabling real coverage fractions.
        """
        self.engine = engine
        self.provider = provider
        self.max_steps = max_steps
        self.grid_size = grid_size
        self._reachable_cells = reachable_cells
        if total_cells is None and reachable_cells is not None:
            total_cells = len(reachable_cells)
        self._total_cells = total_cells

        # covered[cell] = agent_id of first visitor
        self._covered: dict[tuple[int, int], int] = {}
        # per-agent count of cells first covered by that agent
        self._contribution: dict[int, int] = {i: 0 for i in range(engine.agent_count)}

        self._step_count: int = 0
        self._current_agent: int = 0
        self._last_action_by_agent: dict[int, str | None] = {
            i: None for i in range(engine.agent_count)
        }
        self._no_progress_steps: int = 0

        # Register each agent's starting position
        for state in engine.get_all_agent_states():
            self._mark_covered(state.agent_id, state.position, state.rotation)

    @property
    def current_agent_id(self) -> int:
        """Return the agent index whose turn it is."""
        return self._current_agent

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cells_in_view(
        self,
        position: dict[str, float],
        rotation: dict[str, float],
    ) -> set[tuple[int, int]]:
        """Return the set of currently visible cells for one agent.

        When reachable cells are unavailable, fall back to the current occupied cell.
        """
        origin = _pos_to_cell(position, self.grid_size)
        if not self._reachable_cells:
            return {origin}

        visible = {origin}
        max_distance_cells = self.VIEW_DISTANCE_METRES / self.grid_size
        yaw = math.radians(float(rotation.get("y", 0.0)) % 360.0)
        forward_x = math.sin(yaw)
        forward_z = math.cos(yaw)
        half_fov = float(getattr(self.engine, "field_of_view", 90)) / 2.0

        for cell in self._reachable_cells:
            dx = cell[0] - origin[0]
            dz = cell[1] - origin[1]
            if dx == 0 and dz == 0:
                continue

            distance = math.hypot(dx, dz)
            if distance > max_distance_cells:
                continue

            dot = forward_x * dx + forward_z * dz
            if dot <= 0:
                continue

            cos_theta = max(-1.0, min(1.0, dot / distance))
            angle = math.degrees(math.acos(cos_theta))
            if angle <= half_fov:
                visible.add(cell)

        return visible

    def _mark_covered(
        self,
        agent_id: int,
        position: dict[str, float],
        rotation: dict[str, float] | None = None,
    ) -> int:
        """Mark the currently visible cells as covered by *agent_id*.

        Returns the number of newly covered cells.
        """
        rotation = rotation or {"y": 0.0}
        new_cells = 0
        for cell in self._cells_in_view(position, rotation):
            if cell not in self._covered:
                self._covered[cell] = agent_id
                self._contribution[agent_id] += 1
                new_cells += 1
        return new_cells

    def _coverage_fraction(self) -> float:
        """Return fraction of total_cells covered; 0.0 if total_cells is unknown."""
        if self._total_cells is None or self._total_cells == 0:
            return 0.0
        return len(self._covered) / self._total_cells

    def _normalize_action(self, agent_id: int, action: Any) -> str:
        """Clamp a raw model action to the safe game-local action space."""
        action_name = str(action or "").strip()
        if action_name not in self.ACTION_SPACE:
            return self.SAFE_FALLBACK_ACTION

        current_state = self.engine.get_agent_state(agent_id)
        if (
            not current_state.last_action_success
            and action_name in _MOVE_ACTIONS
            and self._last_action_by_agent.get(agent_id) == action_name
        ):
            return self.SAFE_FALLBACK_ACTION
        return action_name

    @staticmethod
    def _visible_object_names(visible_objects: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for obj in visible_objects:
            name = str(obj.get("objectType") or obj.get("name") or "").strip()
            if name and name not in names:
                names.append(name)
            if len(names) >= 12:
                break
        return names

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def cells_covered(self) -> int:
        """Return total unique cells covered so far."""
        return len(self._covered)

    def get_coverage_pct(self) -> float:
        """Return coverage percentage (0–100). Requires total_cells to be set."""
        return self._coverage_fraction() * 100.0

    def get_state(self) -> dict[str, Any]:
        """Return a structured state dict suitable for VLM prompts.

        Includes teammate positions and a coverage summary for every agent.
        """
        agents_info = {
            s.agent_id: {
                "position": s.position,
                "rotation": s.rotation,
                "cells_covered": self._contribution[s.agent_id],
            }
            for s in self.engine.get_all_agent_states()
        }
        state: dict[str, Any] = {
            "game": "coverage",
            "step": self._step_count,
            "remaining_steps": self.max_steps - self._step_count,
            "current_agent": self._current_agent,
            "agents": agents_info,
            "total_covered": len(self._covered),
            "coverage_pct": round(self.get_coverage_pct(), 1),
        }
        if self._total_cells is not None:
            state["total_cells"] = self._total_cells
            state["target_pct"] = round(self.COVERAGE_TARGET * 100, 1)
        return state

    def get_prompt_state(self, agent_id: int | None = None) -> dict[str, Any]:
        """Return the agent-specific prompt payload used for a VLM decision."""
        agent_id = self._current_agent if agent_id is None else agent_id
        current_state = self.engine.get_agent_state(agent_id)
        state = self.get_state()
        state["my_agent_id"] = agent_id
        state["available_actions"] = list(self.ACTION_SPACE)
        state["no_progress_steps"] = self._no_progress_steps
        state["last_attempted_action"] = self._last_action_by_agent.get(agent_id)
        state["last_action_success"] = current_state.last_action_success
        if current_state.last_action_error:
            state["last_action_error"] = current_state.last_action_error
        visible_names = self._visible_object_names(current_state.visible_objects)
        if visible_names:
            state["visible_objects"] = visible_names
        if self._total_cells is not None:
            state["cells_remaining"] = max(0, self._total_cells - len(self._covered))
        return state

    def decide(
        self,
        *,
        images: list[str] | None = None,
        prompt_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query the provider and return a sanitized response for the current agent."""
        agent_id = self._current_agent
        prompt_state = prompt_state or self.get_prompt_state(agent_id)
        raw_response = self.provider.get_action(images=images or [], state=prompt_state)
        raw_action = raw_response.get("action", self.SAFE_FALLBACK_ACTION)
        return {
            "reasoning": str(raw_response.get("reasoning", "")),
            "action": self._normalize_action(agent_id, raw_action),
            "raw_action": raw_action,
        }

    def execute_action(self, action: Any) -> str:
        """Apply one action for the current agent and update coverage state."""
        agent_id = self._current_agent
        action_name = self._normalize_action(agent_id, action)
        new_state = self.engine.step(agent_id=agent_id, action=action_name)
        self._last_action_by_agent[agent_id] = action_name

        new_cells = 0
        if new_state.last_action_success:
            new_cells = self._mark_covered(agent_id, new_state.position, new_state.rotation)

        if new_cells > 0:
            self._no_progress_steps = 0
        else:
            self._no_progress_steps += 1

        self._step_count += 1
        self._current_agent = (self._current_agent + 1) % self.engine.agent_count
        return action_name

    def is_over(self) -> bool:
        """Return True if the game has ended."""
        if self._step_count >= self.max_steps:
            return True
        if self._total_cells is not None and self._coverage_fraction() >= self.COVERAGE_TARGET:
            return True
        return False

    def step(self) -> bool:
        """Execute one step for the current agent.

        Returns True if the game continues, False if it is already over.
        """
        if self.is_over():
            return False

        response = self.decide()
        self.execute_action(response["action"])
        return True

    def get_result(self) -> CoverageResult:
        """Compute and return the final game result."""
        cells = len(self._covered)
        pct = self.get_coverage_pct()

        if cells > 0:
            contribution_ratio = {i: c / cells for i, c in self._contribution.items()}
        else:
            contribution_ratio = {i: 0.0 for i in self._contribution}

        contributions = list(self._contribution.values())
        if len(contributions) <= 1 or max(contributions) == 0:
            work_balance = 1.0
        else:
            work_balance = min(contributions) / max(contributions)

        coverage_reached = (
            self._total_cells is not None and self._coverage_fraction() >= self.COVERAGE_TARGET
        )
        termination_reason = "coverage_reached" if coverage_reached else "max_steps"

        return CoverageResult(
            cells_covered=cells,
            coverage_pct=pct,
            contribution=dict(self._contribution),
            contribution_ratio=contribution_ratio,
            work_balance=work_balance,
            total_steps=self._step_count,
            termination_reason=termination_reason,
        )

    def run(self) -> CoverageResult:
        """Run the full game to completion and return the result."""
        while not self.is_over():
            self.step()
        return self.get_result()
