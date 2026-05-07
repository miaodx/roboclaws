from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.vlm import VLMProvider
from roboclaws.games.common import (
    _DECISION_ACTIONS,
    _MOVE_ACTIONS,
    _move_target_cell,
    _pos_to_cell,
    _rotation_after_turn,
)
from roboclaws.games.turns import (
    decide_turn,
    execute_control_turn,
    normalize_navigation_action,
)

_MOVE_ACTION_ORDER: tuple[str, ...] = ("MoveAhead", "MoveBack", "MoveLeft", "MoveRight")


@dataclass
class CoverageResult:
    """Final outcome of a cooperative coverage game."""

    cells_covered: int  # total unique cells covered by all agents
    coverage_pct: float  # cells_covered / total_cells * 100 (0.0 if total_cells unknown)
    contribution: dict[int, int]  # agent_id → cells first covered by this agent
    contribution_ratio: dict[int, float]  # agent_id → contribution / cells_covered
    work_balance: float  # min_contribution / max_contribution; 1.0 if single agent or all equal
    total_steps: int
    termination_reason: str  # "coverage_reached" | "max_steps" | "time_limit"


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
    STALL_RECOVERY_NO_PROGRESS_FACTOR: int = 2

    def __init__(
        self,
        engine: MultiAgentEngine,
        provider: VLMProvider,
        max_steps: int = 200,
        grid_size: float = 0.25,
        total_cells: int | None = None,
        reachable_cells: set[tuple[int, int]] | None = None,
        max_wall_seconds: float | None = 1200.0,
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
        # 20-minute default wallclock budget — caps total game runtime even
        # when provider retries stretch individual steps.  Set to None to
        # disable.
        self.max_wall_seconds = max_wall_seconds
        self._wall_started_at: float | None = None
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
        half_fov = float(self.engine.field_of_view) / 2.0

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

    def _nearest_uncovered_distance(self, start_cell: tuple[int, int]) -> int | None:
        """Return shortest grid distance to an uncovered reachable cell."""
        if not self._reachable_cells or start_cell not in self._reachable_cells:
            return None

        uncovered = self._reachable_cells.difference(self._covered)
        if not uncovered:
            return None
        if start_cell in uncovered:
            return 0

        queue: deque[tuple[tuple[int, int], int]] = deque([(start_cell, 0)])
        visited = {start_cell}

        while queue:
            cell, distance = queue.popleft()
            for dx, dz in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                neighbor = (cell[0] + dx, cell[1] + dz)
                if neighbor in visited or neighbor not in self._reachable_cells:
                    continue
                if neighbor in uncovered:
                    return distance + 1
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))

        return None

    def _normalize_action(self, agent_id: int, action: Any) -> str:
        """Clamp a raw model action to the safe game-local action space."""
        return normalize_navigation_action(
            action=action,
            action_space=self.ACTION_SPACE,
            safe_fallback_action=self.SAFE_FALLBACK_ACTION,
            current_state=self.engine.get_agent_state(agent_id),
            last_action_by_agent=self._last_action_by_agent,
            agent_id=agent_id,
        )

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

    def _cell_status(
        self,
        *,
        cell: tuple[int, int],
        agent_id: int,
        occupied_cells: dict[tuple[int, int], int],
    ) -> str:
        """Classify a target cell from the current agent's perspective."""
        occupant = occupied_cells.get(cell)
        if occupant is not None and occupant != agent_id:
            return f"occupied_by_agent_{occupant}"
        if self._reachable_cells is not None and cell not in self._reachable_cells:
            return "blocked_unreachable"

        owner = self._covered.get(cell)
        if owner is None:
            return "uncovered"
        if owner == agent_id:
            return "covered_by_self"
        return f"covered_by_agent_{owner}"

    def _estimate_new_cells(
        self,
        *,
        position: dict[str, float],
        rotation: dict[str, float],
    ) -> int:
        """Estimate how many currently uncovered cells would be seen next."""
        return len(self._cells_in_view(position, rotation) - set(self._covered))

    def _build_action_hints(
        self,
        *,
        agent_id: int,
        current_state: Any,
    ) -> dict[str, dict[str, Any]]:
        """Return per-action coverage estimates for the current local state."""
        current_cell = _pos_to_cell(current_state.position, self.grid_size)
        current_frontier_distance = self._nearest_uncovered_distance(current_cell)
        occupied_cells = {
            _pos_to_cell(state.position, self.grid_size): state.agent_id
            for state in self.engine.get_all_agent_states()
        }
        action_hints: dict[str, dict[str, Any]] = {}

        for action in self.ACTION_SPACE:
            if action in _MOVE_ACTIONS:
                target_cell = _move_target_cell(current_cell, current_state.rotation, action)
                target_status = self._cell_status(
                    cell=target_cell,
                    agent_id=agent_id,
                    occupied_cells=occupied_cells,
                )
                estimated_new_cells = 0
                frontier_distance: int | None = None
                if (
                    not target_status.startswith("occupied_by_agent_")
                    and target_status != "blocked_unreachable"
                ):
                    estimated_new_cells = self._estimate_new_cells(
                        position={
                            "x": target_cell[0] * self.grid_size,
                            "y": float(current_state.position.get("y", 0.0)),
                            "z": target_cell[1] * self.grid_size,
                        },
                        rotation=current_state.rotation,
                    )
                    frontier_distance = self._nearest_uncovered_distance(target_cell)
                action_hints[action] = {
                    "kind": "move",
                    "target_cell": list(target_cell),
                    "target_status": target_status,
                    "estimated_new_cells": estimated_new_cells,
                    "nearest_uncovered_distance": frontier_distance,
                    "improves_frontier_distance": (
                        current_frontier_distance is not None
                        and frontier_distance is not None
                        and frontier_distance < current_frontier_distance
                    ),
                }
                continue

            facing_after = _rotation_after_turn(current_state.rotation, action)
            front_cell = _move_target_cell(current_cell, facing_after, "MoveAhead")
            front_status = self._cell_status(
                cell=front_cell,
                agent_id=agent_id,
                occupied_cells=occupied_cells,
            )
            action_hints[action] = {
                "kind": "rotate",
                "facing_after_degrees": int(round(float(facing_after.get("y", 0.0)))) % 360,
                "front_cell_after_turn": list(front_cell),
                "front_cell_status": front_status,
                "estimated_new_cells": self._estimate_new_cells(
                    position=current_state.position,
                    rotation=facing_after,
                ),
                "nearest_uncovered_distance": current_frontier_distance,
                "improves_frontier_distance": False,
            }

        return action_hints

    def _stall_recovery(
        self,
        *,
        current_state: Any,
        action_hints: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Return frontier-based recovery guidance when coverage progress stalls."""
        if not self._reachable_cells:
            return None

        current_cell = _pos_to_cell(current_state.position, self.grid_size)
        current_frontier_distance = self._nearest_uncovered_distance(current_cell)
        if current_frontier_distance is None:
            return None

        best_action: str | None = None
        best_distance: int | None = None
        best_estimated_new_cells = -1

        for action in _MOVE_ACTION_ORDER:
            hint = action_hints[action]
            if hint["target_status"].startswith("occupied_by_agent_"):
                continue
            if hint["target_status"] == "blocked_unreachable":
                continue
            frontier_distance = hint["nearest_uncovered_distance"]
            if frontier_distance is None:
                continue
            estimated_new_cells = int(hint["estimated_new_cells"])
            if (
                best_action is None
                or frontier_distance < best_distance
                or (
                    frontier_distance == best_distance
                    and estimated_new_cells > best_estimated_new_cells
                )
            ):
                best_action = action
                best_distance = frontier_distance
                best_estimated_new_cells = estimated_new_cells

        if (
            best_action is None
            or best_distance is None
            or best_distance >= current_frontier_distance
        ):
            return {
                "active": False,
                "current_frontier_distance": current_frontier_distance,
            }

        no_progress_threshold = self.engine.agent_count * self.STALL_RECOVERY_NO_PROGRESS_FACTOR
        return {
            "active": self._no_progress_steps >= no_progress_threshold,
            "current_frontier_distance": current_frontier_distance,
            "recommended_move": best_action,
            "recommended_move_frontier_distance": best_distance,
            "recommended_move_estimated_new_cells": best_estimated_new_cells,
            "no_progress_threshold": no_progress_threshold,
        }

    def _override_with_stall_recovery(
        self,
        *,
        action_name: str,
        prompt_state: dict[str, Any],
    ) -> tuple[str, str | None]:
        """Apply a conservative frontier-seeking override when stalled."""
        recovery = prompt_state.get("stall_recovery")
        if not isinstance(recovery, dict) or not recovery.get("active"):
            return action_name, None

        recommended_move = recovery.get("recommended_move")
        if recommended_move not in _MOVE_ACTIONS or action_name == recommended_move:
            return action_name, None

        action_hints = prompt_state.get("action_hints", {})
        chosen_hint = action_hints.get(action_name, {})
        if action_name in _MOVE_ACTIONS and (
            chosen_hint.get("estimated_new_cells", 0) > 0
            or chosen_hint.get("improves_frontier_distance")
        ):
            return action_name, None

        return str(recommended_move), "stall_recovery_frontier_move"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def cells_covered(self) -> int:
        """Return total unique cells covered so far."""
        return len(self._covered)

    def get_coverage_pct(self) -> float:
        """Return coverage percentage (0–100). Requires total_cells to be set."""
        return self._coverage_fraction() * 100.0

    def _coverage_reached(self) -> bool:
        return self._total_cells is not None and self._coverage_fraction() >= self.COVERAGE_TARGET

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
        state["action_hints"] = self._build_action_hints(
            agent_id=agent_id,
            current_state=current_state,
        )
        stall_recovery = self._stall_recovery(
            current_state=current_state,
            action_hints=state["action_hints"],
        )
        if stall_recovery is not None:
            state["stall_recovery"] = stall_recovery
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
        # Prime the wall-clock the same way step() does so callers that drive
        # the game via decide()+execute_action() (the example harnesses) get
        # max_wall_seconds enforcement.  Otherwise _wall_started_at stays
        # None and _wall_exceeded() is dead code.
        if self._wall_started_at is None:
            self._wall_started_at = time.monotonic()
        agent_id = self._current_agent
        prompt_state = prompt_state or self.get_prompt_state(agent_id)
        return decide_turn(
            provider=self.provider,
            images=images or [],
            prompt_state=prompt_state,
            normalize_action=lambda action: self._normalize_action(agent_id, action),
            override_action=lambda action_name, state: self._override_with_stall_recovery(
                action_name=action_name,
                prompt_state=state,
            ),
        )

    def execute_action(self, action: Any) -> str:
        """Apply one action for the current agent and update coverage state."""
        agent_id = self._current_agent

        def after_step(agent_id: int, action_name: str, new_state: Any) -> None:
            self._last_action_by_agent[agent_id] = action_name
            new_cells = (
                self._mark_covered(agent_id, new_state.position, new_state.rotation)
                if new_state.last_action_success
                else 0
            )
            self._no_progress_steps = 0 if new_cells > 0 else self._no_progress_steps + 1
            self._step_count += 1

        action_name, self._current_agent = execute_control_turn(
            engine=self.engine,
            agent_count=self.engine.agent_count,
            current_agent=agent_id,
            action=action,
            normalize_action=lambda raw_action: self._normalize_action(agent_id, raw_action),
            after_step=after_step,
        )
        return action_name

    def _wall_exceeded(self) -> bool:
        """Return True if the wallclock budget has elapsed."""
        if self.max_wall_seconds is None or self._wall_started_at is None:
            return False
        return (time.monotonic() - self._wall_started_at) >= self.max_wall_seconds

    def is_over(self) -> bool:
        """Return True if the game has ended."""
        if self._step_count >= self.max_steps:
            return True
        if self._wall_exceeded():
            return True
        if self._coverage_reached():
            return True
        return False

    def step(self) -> bool:
        """Execute one step for the current agent.

        Returns True if the game continues, False if it is already over.
        """
        if self._wall_started_at is None:
            self._wall_started_at = time.monotonic()
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

        if self._coverage_reached():
            termination_reason = "coverage_reached"
        elif self._wall_exceeded() and self._step_count < self.max_steps:
            termination_reason = "time_limit"
        else:
            termination_reason = "max_steps"

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
