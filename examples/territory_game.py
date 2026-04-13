"""Multi-agent territory control game example.

Two or three VLM-controlled agents compete in an AI2-THOR living-room scene.
Each agent claims the grid cell it currently occupies; cells are permanently
locked to the first claimer.  Agents take turns in round-robin order.

Outputs a replay GIF, a per-agent score summary, and a final overhead
territory map saved as a PNG.

Usage::

    python examples/territory_game.py
    python examples/territory_game.py --agents 3 --scene FloorPlan201 --steps 200
    python examples/territory_game.py --model gpt-4o-mini --output-dir out/territory
    python examples/territory_game.py --model mock --steps 20 --output-dir /tmp/territory
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.visualizer import GameVisualizer
from roboclaws.core.vlm import create_provider
from roboclaws.games.territory import TerritoryGame

# ---------------------------------------------------------------------------
# Grid constants — must match MultiAgentEngine grid_size
# ---------------------------------------------------------------------------

_GRID_SIZE: float = 0.25  # metres
_GRID_ROWS: int = 40
_GRID_COLS: int = 40
_CENTER_ROW: int = _GRID_ROWS // 2
_CENTER_COL: int = _GRID_COLS // 2


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------


def _pos_to_world_idx(pos: dict[str, float]) -> tuple[int, int]:
    """Convert a continuous AI2-THOR (x, z) position to a discrete world index."""
    return (round(pos["x"] / _GRID_SIZE), round(pos["z"] / _GRID_SIZE))


def _world_to_viz(ix: int, iz: int, origin_ix: int, origin_iz: int) -> tuple[int, int]:
    """Map a world grid index to a visualiser (row, col) centred at *origin*."""
    return (_CENTER_ROW + (iz - origin_iz), _CENTER_COL + (ix - origin_ix))


def _in_bounds(row: int, col: int) -> bool:
    return 0 <= row < _GRID_ROWS and 0 <= col < _GRID_COLS


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run a multi-agent territory control game in AI2-THOR.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--scene",
        default="FloorPlan201",
        help="AI2-THOR scene name (living-room range: FloorPlan201-230)",
    )
    p.add_argument("--agents", type=int, default=2, help="Number of agents (2 or 3)")
    p.add_argument("--steps", type=int, default=200, help="Maximum game steps")
    p.add_argument(
        "--model",
        default="mock",
        help="VLM model alias: mock | gpt-4o | gpt-4o-mini | kimi | anthropic",
    )
    p.add_argument(
        "--output-dir",
        default="output/territory",
        dest="output_dir",
        help="Directory to write replay files, GIF, and final territory map",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


def run_territory_game(
    scene: str,
    agent_count: int,
    steps: int,
    model: str,
    output_dir: str,
) -> dict[str, object]:
    """Run a multi-agent territory control episode and save results to *output_dir*.

    Args:
        scene: AI2-THOR scene name.
        agent_count: Number of competing agents (2 or 3).
        steps: Maximum number of game steps.
        model: VLM model alias passed to :func:`~roboclaws.core.vlm.create_provider`.
        output_dir: Directory for replay files, GIF, and territory map.

    Returns:
        Summary dict with keys ``cells_claimed``, ``blocking_events``,
        ``termination_reason``, ``vlm_cost_usd``, and ``output_dir``.
    """
    provider = create_provider(model)
    engine = MultiAgentEngine(scene=scene, agent_count=agent_count, grid_size=_GRID_SIZE)
    viz = GameVisualizer(
        grid_rows=_GRID_ROWS, grid_cols=_GRID_COLS, cell_px=15, agent_count=agent_count
    )
    recorder = ReplayRecorder(agent_count=agent_count, game="territory")
    game = TerritoryGame(engine=engine, provider=provider, max_steps=steps, grid_size=_GRID_SIZE)

    step_num = 0
    # origin_ix/origin_iz initialised inside try so KeyboardInterrupt is always caught
    origin_ix: int = 0
    origin_iz: int = 0
    try:
        # Record starting position of agent 0 as the map origin for centring
        initial_states = engine.get_all_agent_states()
        origin_ix, origin_iz = _pos_to_world_idx(initial_states[0].position)

        while not game.is_over():
            # ----------------------------------------------------------------
            # Capture state BEFORE this step for recording and visualisation
            # ----------------------------------------------------------------
            agent_states = engine.get_all_agent_states()
            agent_frames = [s.frame for s in agent_states]

            # Build per-agent claimed-cell dicts in visualiser coordinates
            claimed_cells_viz: dict[int, list[tuple[int, int]]] = {}
            for agent_id, cells in game._agent_cells.items():
                viz_cells = [
                    rc
                    for wx, wz in cells
                    if _in_bounds(*(rc := _world_to_viz(wx, wz, origin_ix, origin_iz)))
                ]
                claimed_cells_viz[agent_id] = viz_cells

            # Agent positions in visualiser coordinates
            agent_positions_viz: list[tuple[int, int]] = []
            for s in agent_states:
                wx, wz = _pos_to_world_idx(s.position)
                rc = _world_to_viz(wx, wz, origin_ix, origin_iz)
                agent_positions_viz.append(rc if _in_bounds(*rc) else (_CENTER_ROW, _CENTER_COL))

            map_img = viz.render_overhead_map(
                agent_positions=agent_positions_viz,
                claimed_cells=claimed_cells_viz,
            )
            map_frame = np.asarray(map_img.convert("RGB"), dtype=np.uint8)

            game_state = game.get_state()
            current_agent = game_state["current_agent"]

            # ----------------------------------------------------------------
            # Execute one game step (VLM decision + engine action internally)
            # ----------------------------------------------------------------
            game.step()

            if step_num % 10 == 0:
                scores = game.get_scores()
                scores_str = "  ".join(f"A{a}:{c}" for a, c in sorted(scores.items()))
                print(f"  step {step_num:4d}/{steps}  |  claimed: {scores_str}")

            recorder.record_step(
                step=step_num,
                agent_id=current_agent,
                agent_frames=agent_frames,
                overhead_frame=map_frame,
                game_state=game_state,
                vlm_prompt_state=game_state,
                vlm_response={"action": "unknown", "reasoning": "handled by TerritoryGame"},
            )

            step_num += 1

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        engine.close()

    result = game.get_result()

    # Save replay (GIF + JSON)
    out_path = recorder.save(
        output_dir,
        vlm_cost_usd=provider.cumulative_cost,
        final_scores={f"agent_{a}": c for a, c in result.cells_claimed.items()},
        termination_reason=result.termination_reason,
        generate_gif=True,
    )

    # Save final territory map as a standalone PNG
    final_claimed_viz: dict[int, list[tuple[int, int]]] = {}
    for agent_id, cells in game._agent_cells.items():
        final_claimed_viz[agent_id] = [
            rc
            for wx, wz in cells
            if _in_bounds(*(rc := _world_to_viz(wx, wz, origin_ix, origin_iz)))
        ]
    # Use dummy positions for the final map (game is over, no active agents)
    final_map = viz.render_overhead_map(
        agent_positions=[(_CENTER_ROW, _CENTER_COL)] * agent_count,
        claimed_cells=final_claimed_viz,
    )
    GameVisualizer.save_png(final_map, out_path / "territory_final.png")

    return {
        "cells_claimed": result.cells_claimed,
        "blocking_events": result.blocking_events,
        "termination_reason": result.termination_reason,
        "vlm_cost_usd": provider.cumulative_cost,
        "output_dir": str(out_path),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = _parse_args()

    print(f"Scene      : {args.scene}")
    print(f"Agents     : {args.agents}")
    print(f"Steps      : {args.steps}")
    print(f"Model      : {args.model}")
    print(f"Output dir : {args.output_dir}")
    print()

    result = run_territory_game(
        scene=args.scene,
        agent_count=args.agents,
        steps=args.steps,
        model=args.model,
        output_dir=args.output_dir,
    )

    print()
    print(f"Game over  : {result['termination_reason']}")
    print(f"Blocking   : {result['blocking_events']}")
    for agent_id, count in sorted(result["cells_claimed"].items()):
        print(f"  Agent {agent_id} : {count} cells claimed")
    print(f"Replay     : {result['output_dir']}")
    print(f"VLM cost   : ${result['vlm_cost_usd']:.6f}")


if __name__ == "__main__":
    main()
