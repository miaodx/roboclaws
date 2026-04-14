"""Multi-agent cooperative coverage game example.

Two or three VLM-controlled agents cooperate in an AI2-THOR living-room scene
to cover as much floor area as possible.  Each new cell visited by any agent
adds to the shared coverage count.  Agents take turns in round-robin order.

Outputs a replay GIF, coverage progression chart, final coverage map, and a
work-balance report.

Usage::

    python examples/coverage_game.py
    python examples/coverage_game.py --agents 3 --scene FloorPlan201 --steps 200
    python examples/coverage_game.py --model gpt-4o-mini --output-dir out/coverage
    python examples/coverage_game.py --model mock --steps 20 --output-dir /tmp/coverage
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.visualizer import GameVisualizer
from roboclaws.core.vlm import create_provider
from roboclaws.games.coverage import CoverageGame

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
    """Map a world grid index to a visualiser (row, col) centred at origin."""
    return (_CENTER_ROW + (iz - origin_iz), _CENTER_COL + (ix - origin_ix))


def _in_bounds(row: int, col: int) -> bool:
    return 0 <= row < _GRID_ROWS and 0 <= col < _GRID_COLS


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run a multi-agent cooperative coverage game in AI2-THOR.",
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
        default="output/coverage",
        dest="output_dir",
        help="Directory to write replay files, GIF, progression chart, and final coverage map",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------


def _draw_progression_chart(cells_history: list[int], out_path: Path) -> None:
    """Save a coverage progression PNG (cells covered vs step) using Pillow."""
    W, H = 600, 300
    pad_l, pad_r, pad_t, pad_b = 55, 20, 20, 40
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    ax_x0, ax_x1 = pad_l, W - pad_r
    ax_y0, ax_y1 = pad_t, H - pad_b

    draw.rectangle([ax_x0, ax_y0, ax_x1, ax_y1], outline="black")
    draw.text((W // 2 - 20, H - pad_b + 6), "Step", fill="black")
    draw.text((4, H // 2 - 6), "Cells", fill="black")
    draw.text((4, H // 2 + 6), "covered", fill="black")

    if len(cells_history) < 2:
        img.save(out_path)
        return

    n = len(cells_history)
    max_val = max(cells_history) or 1
    plot_w = ax_x1 - ax_x0
    plot_h = ax_y1 - ax_y0

    def to_px(i: int, v: int) -> tuple[int, int]:
        x = ax_x0 + int(i / (n - 1) * plot_w)
        y = ax_y1 - int(v / max_val * plot_h)
        return x, y

    pts = [to_px(i, v) for i, v in enumerate(cells_history)]
    for a, b in zip(pts[:-1], pts[1:]):
        draw.line([a, b], fill=(70, 130, 180), width=2)

    for tick in range(0, max_val + 1, max(1, max_val // 4)):
        y = ax_y1 - int(tick / max_val * plot_h)
        draw.line([(ax_x0 - 4, y), (ax_x0, y)], fill="black")
        draw.text((2, y - 5), str(tick), fill="gray")

    img.save(out_path)


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


def run_coverage_game(
    scene: str,
    agent_count: int,
    steps: int,
    model: str,
    output_dir: str,
) -> dict[str, Any]:
    """Run a multi-agent cooperative coverage episode and save results to output_dir.

    Args:
        scene: AI2-THOR scene name.
        agent_count: Number of cooperating agents (2 or 3).
        steps: Maximum number of game steps.
        model: VLM model alias passed to :func:`~roboclaws.core.vlm.create_provider`.
        output_dir: Directory for replay files, GIF, and coverage outputs.

    Returns:
        Summary dict with keys ``cells_covered``, ``contribution``,
        ``work_balance``, ``termination_reason``, ``vlm_cost_usd``, and ``output_dir``.
    """
    provider = create_provider(model)
    engine = MultiAgentEngine(scene=scene, agent_count=agent_count, grid_size=_GRID_SIZE)
    viz = GameVisualizer(
        grid_rows=_GRID_ROWS, grid_cols=_GRID_COLS, cell_px=15, agent_count=agent_count
    )
    recorder = ReplayRecorder(agent_count=agent_count, game="coverage")
    game = CoverageGame(engine=engine, provider=provider, max_steps=steps, grid_size=_GRID_SIZE)

    step_num = 0
    origin_ix: int = 0
    origin_iz: int = 0
    cells_history: list[int] = []
    # AI2-THOR's third-party overhead camera is static, so capture the frame
    # once and reuse it as the map background for every step.
    overhead_bg: np.ndarray | None = None

    try:
        initial_states = engine.get_all_agent_states()
        origin_ix, origin_iz = _pos_to_world_idx(initial_states[0].position)
        try:
            overhead_bg = engine.get_overhead_frame()
        except Exception:  # noqa: BLE001 - mock engines may omit this
            overhead_bg = None

        while not game.is_over():
            # ----------------------------------------------------------------
            # Capture state BEFORE this step for recording and visualisation
            # ----------------------------------------------------------------
            agent_states = engine.get_all_agent_states()
            agent_frames = [s.frame for s in agent_states]

            # Build per-agent covered-cell dicts in visualiser coordinates
            covered_cells_viz: dict[int, list[tuple[int, int]]] = {
                i: [] for i in range(agent_count)
            }
            for (wx, wz), agent_id in game._covered.items():
                rc = _world_to_viz(wx, wz, origin_ix, origin_iz)
                if _in_bounds(*rc):
                    covered_cells_viz[agent_id].append(rc)

            # Agent positions in visualiser coordinates
            agent_positions_viz: list[tuple[int, int]] = []
            for s in agent_states:
                wx, wz = _pos_to_world_idx(s.position)
                rc = _world_to_viz(wx, wz, origin_ix, origin_iz)
                agent_positions_viz.append(rc if _in_bounds(*rc) else (_CENTER_ROW, _CENTER_COL))

            map_img = viz.render_overhead_map(
                agent_positions=agent_positions_viz,
                claimed_cells=covered_cells_viz,
                base_frame=overhead_bg,
            )
            map_frame = np.asarray(map_img.convert("RGB"), dtype=np.uint8)

            game_state = game.get_state()
            current_agent = game_state["current_agent"]

            # Track coverage progression (cells covered before this step)
            cells_history.append(game.cells_covered())

            # ----------------------------------------------------------------
            # Execute one game step (VLM decision + engine action internally)
            # ----------------------------------------------------------------
            game.step()

            if step_num % 10 == 0:
                print(
                    f"  step {step_num:4d}/{steps}  |  "
                    f"covered: {game.cells_covered()} cells  |  "
                    f"agents: {agent_count}"
                )

            recorder.record_step(
                step=step_num,
                agent_id=current_agent,
                agent_frames=agent_frames,
                overhead_frame=map_frame,
                game_state=game_state,
                vlm_prompt_state=game_state,
                vlm_response={"action": "unknown", "reasoning": "handled by CoverageGame"},
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
        final_scores={f"agent_{a}": c for a, c in result.contribution.items()},
        termination_reason=result.termination_reason,
        generate_gif=True,
    )

    # Save final coverage map
    final_covered_viz: dict[int, list[tuple[int, int]]] = {i: [] for i in range(agent_count)}
    for (wx, wz), agent_id in game._covered.items():
        rc = _world_to_viz(wx, wz, origin_ix, origin_iz)
        if _in_bounds(*rc):
            final_covered_viz[agent_id].append(rc)

    final_map = viz.render_overhead_map(
        agent_positions=[(_CENTER_ROW, _CENTER_COL)] * agent_count,
        claimed_cells=final_covered_viz,
        base_frame=overhead_bg,
    )
    GameVisualizer.save_png(final_map, out_path / "coverage_final.png")

    # Save coverage progression chart
    _draw_progression_chart(cells_history, out_path / "coverage_progression.png")

    # Save work balance report
    work_balance_data: dict[str, Any] = {
        "cells_covered": result.cells_covered,
        "coverage_pct": result.coverage_pct,
        "contribution": result.contribution,
        "contribution_ratio": result.contribution_ratio,
        "work_balance": result.work_balance,
        "total_steps": result.total_steps,
        "termination_reason": result.termination_reason,
    }
    (out_path / "work_balance.json").write_text(json.dumps(work_balance_data, indent=2))

    return {
        "cells_covered": result.cells_covered,
        "contribution": result.contribution,
        "work_balance": result.work_balance,
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

    result = run_coverage_game(
        scene=args.scene,
        agent_count=args.agents,
        steps=args.steps,
        model=args.model,
        output_dir=args.output_dir,
    )

    print()
    print(f"Game over  : {result['termination_reason']}")
    print(f"Cells      : {result['cells_covered']} covered")
    print(f"Work bal.  : {result['work_balance']:.2f} (1.0 = perfectly even)")
    for agent_id, count in sorted(result["contribution"].items()):
        print(f"  Agent {agent_id} : {count} cells first covered")
    print(f"Replay     : {result['output_dir']}")
    print(f"VLM cost   : ${result['vlm_cost_usd']:.6f}")


if __name__ == "__main__":
    main()
