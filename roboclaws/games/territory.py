from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from roboclaws.core.engine import NAVIGATION_ACTIONS, MultiAgentEngine
from roboclaws.core.vlm import VLMProvider

# Movement actions that advance the agent's position (not rotation/look)
_MOVE_ACTIONS: frozenset[str] = frozenset({"MoveAhead", "MoveBack", "MoveLeft", "MoveRight"})


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
    termination_reason: str  # "all_cells_claimed" | "max_steps"


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

    def __init__(
        self,
        engine: MultiAgentEngine,
        provider: VLMProvider,
        max_steps: int = 200,
        grid_size: float = 0.25,
    ) -> None:
        self.engine = engine
        self.provider = provider
        self.max_steps = max_steps
        self.grid_size = grid_size

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
        # consecutive steps without any new cell being claimed
        self._stale_steps: int = 0

        # Claim each agent's starting position
        for state in engine.get_all_agent_states():
            self._try_claim(state.agent_id, state.position)

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
        return {
            "game": "territory",
            "step": self._step_count,
            "remaining_steps": self.max_steps - self._step_count,
            "current_agent": self._current_agent,
            "agents": agents_info,
            "total_claimed": len(self._claimed),
            "blocking_events": self._blocking_events,
        }

    def get_scores(self) -> dict[int, int]:
        """Return cells claimed per agent."""
        return {agent_id: len(cells) for agent_id, cells in self._agent_cells.items()}

    def is_over(self) -> bool:
        """Return True if the game has ended."""
        if self._step_count >= self.max_steps:
            return True
        # All reachable cells claimed: no new discovery for a full agent round
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

        agent_id = self._current_agent

        # Build VLM prompt state
        game_state = self.get_state()
        game_state["my_agent_id"] = agent_id

        response = self.provider.get_action(images=[], state=game_state)
        action = response.get("action", "MoveAhead")
        if action not in NAVIGATION_ACTIONS:
            action = "MoveAhead"

        new_state = self.engine.step(agent_id=agent_id, action=action)

        # Detect blocking: a movement action that failed
        if not new_state.last_action_success and action in _MOVE_ACTIONS:
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
        return True

    def get_result(self) -> TerritoryResult:
        """Compute and return the final game result."""
        reason = "max_steps" if self._step_count >= self.max_steps else "all_cells_claimed"
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
