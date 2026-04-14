from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roboclaws.core.engine import NAVIGATION_ACTIONS, MultiAgentEngine
from roboclaws.core.vlm import VLMProvider


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
    * A cell is "covered" the first time any agent visits it.
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
        if total_cells is None and reachable_cells is not None:
            total_cells = len(reachable_cells)
        self._total_cells = total_cells

        # covered[cell] = agent_id of first visitor
        self._covered: dict[tuple[int, int], int] = {}
        # per-agent count of cells first covered by that agent
        self._contribution: dict[int, int] = {i: 0 for i in range(engine.agent_count)}

        self._step_count: int = 0
        self._current_agent: int = 0

        # Register each agent's starting position
        for state in engine.get_all_agent_states():
            self._mark_covered(state.agent_id, state.position)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mark_covered(self, agent_id: int, position: dict[str, float]) -> bool:
        """Mark the cell at *position* as covered by *agent_id*.

        Returns True if this is a newly covered cell.
        """
        cell = _pos_to_cell(position, self.grid_size)
        if cell not in self._covered:
            self._covered[cell] = agent_id
            self._contribution[agent_id] += 1
            return True
        return False

    def _coverage_fraction(self) -> float:
        """Return fraction of total_cells covered; 0.0 if total_cells is unknown."""
        if self._total_cells is None or self._total_cells == 0:
            return 0.0
        return len(self._covered) / self._total_cells

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

        agent_id = self._current_agent

        game_state = self.get_state()
        game_state["my_agent_id"] = agent_id

        response = self.provider.get_action(images=[], state=game_state)
        action = response.get("action", "MoveAhead")
        if action not in NAVIGATION_ACTIONS:
            action = "MoveAhead"

        new_state = self.engine.step(agent_id=agent_id, action=action)

        if new_state.last_action_success:
            self._mark_covered(agent_id, new_state.position)

        self._step_count += 1
        self._current_agent = (self._current_agent + 1) % self.engine.agent_count
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
