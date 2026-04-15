from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.vlm import VLMProvider

# Movement actions that advance the agent's position (not rotation/look)
_MOVE_ACTIONS: frozenset[str] = frozenset({"MoveAhead", "MoveBack", "MoveLeft", "MoveRight"})
_DECISION_ACTIONS: tuple[str, ...] = (
    "MoveAhead",
    "MoveBack",
    "MoveLeft",
    "MoveRight",
    "RotateLeft",
    "RotateRight",
)


def _heading_index(rotation: dict[str, float]) -> int:
    """Return the nearest 90-degree heading bucket as 0/1/2/3."""
    return int(round(float(rotation.get("y", 0.0)) / 90.0)) % 4


def _forward_delta(rotation: dict[str, float]) -> tuple[int, int]:
    """Return the discrete forward delta for the given rotation."""
    return (
        (0, 1),
        (1, 0),
        (0, -1),
        (-1, 0),
    )[_heading_index(rotation)]


def _rotation_after_turn(rotation: dict[str, float], action: str) -> dict[str, float]:
    """Return the rotation after applying a 90-degree turn action."""
    delta = -90.0 if action == "RotateLeft" else 90.0
    new_rotation = dict(rotation)
    new_rotation["y"] = (float(rotation.get("y", 0.0)) + delta) % 360.0
    return new_rotation


def _move_target_cell(
    cell: tuple[int, int],
    rotation: dict[str, float],
    action: str,
) -> tuple[int, int]:
    """Return the destination cell for a discrete movement action."""
    dx, dz = _forward_delta(rotation)
    if action == "MoveAhead":
        delta = (dx, dz)
    elif action == "MoveBack":
        delta = (-dx, -dz)
    elif action == "MoveLeft":
        delta = (-dz, dx)
    else:
        delta = (dz, -dx)
    return (cell[0] + delta[0], cell[1] + delta[1])


def _pos_to_cell(pos: dict[str, float], grid_size: float) -> tuple[int, int]:
    """Convert a continuous (x, z) position to a discrete grid cell index."""
    return (round(pos["x"] / grid_size), round(pos["z"] / grid_size))


def _largest_connected_component(cells: set[tuple[int, int]]) -> int:
    """Return the size of the largest 4-connected component in *cells*."""
    if not cells:
        return 0
    remaining = set(cells)
    best = 0
    while remaining:
        start = next(iter(remaining))
        queue: deque[tuple[int, int]] = deque([start])
        visited = {start}
        while queue:
            cx, cz = queue.popleft()
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (cx + dx, cz + dz)
                if nb in remaining and nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        remaining -= visited
        best = max(best, len(visited))
    return best


@dataclass
class TerritoryResult:
    """Final outcome of a territory game."""

    cells_claimed: dict[int, int]  # agent_id → cell count
    connectivity_ratio: dict[int, float]  # agent_id → largest_component / total_claimed
    blocking_events: int
    total_steps: int
    termination_reason: str  # "all_cells_claimed" | "stale" | "max_steps"


class TerritoryGame:
    """Adversarial territory claiming game.

    Rules
    -----
    * Each agent claims the grid cell it currently occupies.
    * A cell is permanently locked to the first agent that visits it.
    * Agents take turns in round-robin order (one step per agent per round).
    * The game ends when all reachable cells are claimed or *max_steps* is reached.

    Metrics
    -------
    * Cells claimed per agent.
    * Territory connectivity ratio: largest contiguous region / total cells claimed.
    * Blocking events: failed movement actions (opponent or wall occupies the target cell).
    """

    ACTION_SPACE: tuple[str, ...] = _DECISION_ACTIONS
    SAFE_FALLBACK_ACTION: str = "RotateRight"

    def __init__(
        self,
        engine: MultiAgentEngine,
        provider: VLMProvider,
        max_steps: int = 200,
        grid_size: float = 0.25,
        reachable_cells: set[tuple[int, int]] | None = None,
    ) -> None:
        self.engine = engine
        self.provider = provider
        self.max_steps = max_steps
        self.grid_size = grid_size

        # Ground-truth reachable cells from AI2-THOR (None → use _all_seen fallback)
        self._reachable_cells = reachable_cells

        # claimed[cell] = agent_id of first claimer
        self._claimed: dict[tuple[int, int], int] = {}
        # per-agent set of owned cells
        self._agent_cells: dict[int, set[tuple[int, int]]] = {
            i: set() for i in range(engine.agent_count)
        }
        # all cells ever visited — approximates the set of reachable cells
        self._all_seen: set[tuple[int, int]] = set()

        self._blocking_events: int = 0
        self._step_count: int = 0
        self._current_agent: int = 0
        self._last_action_by_agent: dict[int, str | None] = {
            i: None for i in range(engine.agent_count)
        }
        # consecutive steps without any new cell being claimed
        self._stale_steps: int = 0

        # Claim each agent's starting position
        for state in engine.get_all_agent_states():
            self._try_claim(state.agent_id, state.position)

    @property
    def current_agent_id(self) -> int:
        """Return the agent index whose turn it is."""
        return self._current_agent

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_claim(self, agent_id: int, position: dict[str, float]) -> bool:
        """Try to claim the cell at *position* for *agent_id*.

        Returns True if the cell was newly claimed.
        """
        cell = _pos_to_cell(position, self.grid_size)
        self._all_seen.add(cell)
        if cell not in self._claimed:
            self._claimed[cell] = agent_id
            self._agent_cells[agent_id].add(cell)
            return True
        return False

    def _connectivity_ratio(self, agent_id: int) -> float:
        """Largest contiguous region / total cells claimed for *agent_id*."""
        cells = self._agent_cells[agent_id]
        if not cells:
            return 0.0
        return _largest_connected_component(cells) / len(cells)

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

    def _cell_status(
        self,
        *,
        cell: tuple[int, int],
        agent_id: int,
        occupied_cells: dict[tuple[int, int], int],
    ) -> str:
        """Classify a cell from the current agent's perspective."""
        occupant = occupied_cells.get(cell)
        if occupant is not None and occupant != agent_id:
            return f"occupied_by_agent_{occupant}"
        if self._reachable_cells is not None and cell not in self._reachable_cells:
            return "blocked_unreachable"

        owner = self._claimed.get(cell)
        if owner is None:
            return "unclaimed"
        if owner == agent_id:
            return "claimed_by_self"
        return f"claimed_by_agent_{owner}"

    def _build_action_hints(
        self,
        *,
        agent_id: int,
        current_state: Any,
    ) -> dict[str, dict[str, Any]]:
        """Return per-action guidance for the current local navigation state."""
        current_cell = _pos_to_cell(current_state.position, self.grid_size)
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
                action_hints[action] = {
                    "kind": "move",
                    "target_cell": list(target_cell),
                    "target_status": target_status,
                    "would_claim_new_cell": target_status == "unclaimed",
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
            }

        return action_hints

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return a structured state dict suitable for VLM prompts."""
        agents_info = {
            s.agent_id: {
                "position": s.position,
                "rotation": s.rotation,
                "cells_claimed": len(self._agent_cells[s.agent_id]),
            }
            for s in self.engine.get_all_agent_states()
        }
        state: dict[str, Any] = {
            "game": "territory",
            "step": self._step_count,
            "remaining_steps": self.max_steps - self._step_count,
            "current_agent": self._current_agent,
            "agents": agents_info,
            "total_claimed": len(self._claimed),
            "blocking_events": self._blocking_events,
        }
        if self._reachable_cells is not None:
            state["total_reachable"] = len(self._reachable_cells)
        return state

    def get_prompt_state(self, agent_id: int | None = None) -> dict[str, Any]:
        """Return the agent-specific prompt payload used for a VLM decision."""
        agent_id = self._current_agent if agent_id is None else agent_id
        current_state = self.engine.get_agent_state(agent_id)
        state = self.get_state()
        state["my_agent_id"] = agent_id
        state["available_actions"] = list(self.ACTION_SPACE)
        state["stale_steps"] = self._stale_steps
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
        if self._reachable_cells is not None:
            state["reachable_remaining"] = max(0, len(self._reachable_cells) - len(self._claimed))
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
        """Apply one action for the current agent and update game state."""
        agent_id = self._current_agent
        action_name = self._normalize_action(agent_id, action)
        new_state = self.engine.step(agent_id=agent_id, action=action_name)
        self._last_action_by_agent[agent_id] = action_name

        # Detect blocking: a movement action that failed
        if not new_state.last_action_success and action_name in _MOVE_ACTIONS:
            self._blocking_events += 1

        # Claim new position on success; track stale progress
        newly_claimed = False
        if new_state.last_action_success:
            newly_claimed = self._try_claim(agent_id, new_state.position)

        if newly_claimed:
            self._stale_steps = 0
        else:
            self._stale_steps += 1

        self._step_count += 1
        self._current_agent = (self._current_agent + 1) % self.engine.agent_count
        return action_name

    def get_scores(self) -> dict[int, int]:
        """Return cells claimed per agent."""
        return {agent_id: len(cells) for agent_id, cells in self._agent_cells.items()}

    def is_over(self) -> bool:
        """Return True if the game has ended."""
        if self._step_count >= self.max_steps:
            return True
        if self._reachable_cells is not None:
            # Ground-truth available: terminate when every reachable cell is claimed
            if self._reachable_cells and len(self._claimed) >= len(self._reachable_cells):
                return True
            # Also terminate if agents are stuck for 2 full rounds
            if self._stale_steps >= 2 * self.engine.agent_count:
                return True
        else:
            # Fallback: terminate when all seen cells claimed and stale for one round
            if (
                self._all_seen
                and len(self._claimed) >= len(self._all_seen)
                and self._stale_steps >= self.engine.agent_count
            ):
                return True
        return False

    def step(self) -> bool:
        """Execute one step for the current agent.

        Returns True if the game should continue, False if it is already over.
        """
        if self.is_over():
            return False

        response = self.decide()
        self.execute_action(response["action"])
        return True

    def get_result(self) -> TerritoryResult:
        """Compute and return the final game result."""
        if self._step_count >= self.max_steps:
            reason = "max_steps"
        elif self._reachable_cells is not None and len(self._claimed) >= len(self._reachable_cells):
            reason = "all_cells_claimed"
        elif (
            self._reachable_cells is None
            and self._all_seen
            and len(self._claimed) >= len(self._all_seen)
        ):
            reason = "all_cells_claimed"
        else:
            reason = "stale"
        return TerritoryResult(
            cells_claimed=self.get_scores(),
            connectivity_ratio={
                i: self._connectivity_ratio(i) for i in range(self.engine.agent_count)
            },
            blocking_events=self._blocking_events,
            total_steps=self._step_count,
            termination_reason=reason,
        )

    def run(self) -> TerritoryResult:
        """Run the full game to completion and return the result."""
        while not self.is_over():
            self.step()
        return self.get_result()
