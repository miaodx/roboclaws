"""Single-agent exploration example.

Run a single VLM-controlled agent in an AI2-THOR living room scene.
The agent explores the room for a fixed number of steps, with its
trajectory visualised on an overhead grid map.  Outputs a replay GIF
showing the agent's first-person view alongside the cumulative
exploration trail, and prints the total VLM cost at the end.

Usage::

    python examples/single_agent_explore.py
    python examples/single_agent_explore.py --scene FloorPlan201 --steps 50
    python examples/single_agent_explore.py --model gpt-4o-mini --output-dir out/explore
    python examples/single_agent_explore.py --model mock --steps 10 --output-dir /tmp/explore
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import NAVIGATION_ACTIONS, MultiAgentEngine
from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.turn_metrics import encode_frame_to_b64_jpeg
from roboclaws.core.views import (
    in_bounds as shared_in_bounds,
)
from roboclaws.core.views import (
    pos_to_world_idx as shared_pos_to_world_idx,
)
from roboclaws.core.views import (
    world_to_viz as shared_world_to_viz,
)
from roboclaws.core.visualizer import GameVisualizer
from roboclaws.core.vlm import (
    ProviderHealthError,
    create_provider,
    format_provider_status,
    provider_status_snapshot,
)

# ---------------------------------------------------------------------------
# Grid constants
# ---------------------------------------------------------------------------

_GRID_SIZE: float = 0.25  # metres — must match MultiAgentEngine grid_size
_GRID_ROWS: int = 40
_GRID_COLS: int = 40
_CENTER_ROW: int = _GRID_ROWS // 2
_CENTER_COL: int = _GRID_COLS // 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pos_to_world_idx(pos: dict[str, float]) -> tuple[int, int]:
    """Convert a continuous AI2-THOR (x, z) position to a discrete world index."""
    return shared_pos_to_world_idx(pos, grid_size=_GRID_SIZE)


def _world_to_viz(ix: int, iz: int, origin_ix: int, origin_iz: int) -> tuple[int, int]:
    """Map a world grid index to a visualiser (row, col) centred at *origin*."""
    return shared_world_to_viz(
        ix, iz, origin_ix, origin_iz, grid_rows=_GRID_ROWS, grid_cols=_GRID_COLS
    )


def _in_bounds(row: int, col: int) -> bool:
    return shared_in_bounds(row, col, grid_rows=_GRID_ROWS, grid_cols=_GRID_COLS)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run a single VLM-controlled agent exploring an AI2-THOR scene.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--scene",
        default="FloorPlan201",
        help="AI2-THOR scene name (living-room range: FloorPlan201-230)",
    )
    p.add_argument("--steps", type=int, default=50, help="Number of exploration steps")
    p.add_argument(
        "--model",
        default="mock",
        help="VLM model alias: mock | gpt-4o | gpt-4o-mini | kimi | anthropic",
    )
    p.add_argument(
        "--output-dir",
        default="output/explore",
        dest="output_dir",
        help="Directory to write replay files and GIF",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


def run_exploration(
    scene: str,
    steps: int,
    model: str,
    output_dir: str,
    provider_seed: int | None = None,
) -> dict[str, object]:
    """Run a single-agent exploration episode and save results to *output_dir*.

    Args:
        scene: AI2-THOR scene name.
        steps: Maximum number of exploration steps.
        model: VLM model alias passed to :func:`~roboclaws.core.vlm.create_provider`.
        output_dir: Directory for replay files and GIF output.

    Returns:
        Summary dict with keys ``cells_visited``, ``vlm_cost_usd``, ``output_dir``.
    """
    provider_kwargs = (
        {"seed": provider_seed} if model == "mock" and provider_seed is not None else {}
    )
    provider = create_provider(model, **provider_kwargs)
    engine = MultiAgentEngine(scene=scene, agent_count=1, grid_size=_GRID_SIZE)
    viz = GameVisualizer(grid_rows=_GRID_ROWS, grid_cols=_GRID_COLS, cell_px=15, agent_count=1)
    recorder = ReplayRecorder(agent_count=1, game="explore")

    # Record starting origin for map centring
    initial = engine.get_agent_state(0)
    origin_ix, origin_iz = _pos_to_world_idx(initial.position)

    visited_world: set[tuple[int, int]] = set()
    termination_reason = "max_steps"
    final_provider_status: dict[str, object] = provider_status_snapshot(provider)

    try:
        for step in range(steps):
            state = engine.get_agent_state(0)
            ix, iz = _pos_to_world_idx(state.position)
            visited_world.add((ix, iz))

            # Map world positions to visualiser grid
            agent_viz = _world_to_viz(ix, iz, origin_ix, origin_iz)
            covered_viz = [
                rc
                for x, z in visited_world
                if _in_bounds(*(rc := _world_to_viz(x, z, origin_ix, origin_iz)))
            ]

            # Render grid map with exploration trail
            map_img = viz.render_overhead_map(
                agent_positions=[agent_viz],
                covered_cells=covered_viz,
            )
            map_frame = np.asarray(map_img.convert("RGB"), dtype=np.uint8)

            # Build VLM prompt state
            vlm_state: dict[str, object] = {
                "game": "explore",
                "step": step,
                "remaining_steps": steps - step,
                "position": state.position,
                "rotation": state.rotation,
                "cells_visited": len(visited_world),
                "available_actions": NAVIGATION_ACTIONS,
            }

            # Query VLM with agent FPV + overhead trail map
            agent_b64 = encode_frame_to_b64_jpeg(state.frame)[0]
            map_b64 = encode_frame_to_b64_jpeg(map_frame)[0]
            try:
                response = provider.get_action(images=[agent_b64, map_b64], state=vlm_state)
            except ProviderHealthError as exc:
                termination_reason = "provider_unstable"
                final_provider_status = exc.status or provider_status_snapshot(provider)
                print(
                    f"  step {step:4d}/{steps}  |  provider stop: {exc}\n"
                    f"  provider: {format_provider_status(final_provider_status)}"
                )
                break

            action = response.get("action", "MoveAhead")
            if action not in NAVIGATION_ACTIONS:
                action = "MoveAhead"
            provider_status = provider_status_snapshot(provider)
            final_provider_status = provider_status

            if step % 10 == 0:
                print(
                    f"  step {step:4d}/{steps}  |  "
                    f"cells visited: {len(visited_world):3d}  |  "
                    f"action: {action}  |  provider: {format_provider_status(provider_status)}"
                )

            # Record: use the rendered map frame as overhead so the GIF shows the trail
            recorder.record_step(
                step=step,
                agent_id=0,
                agent_frames=[state.frame],
                overhead_frame=map_frame,
                game_state=vlm_state,
                vlm_prompt_state=vlm_state,
                vlm_response=response,
                provider_status=provider_status,
            )

            # Execute chosen action
            engine.step(agent_id=0, action=action)

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        engine.close()

    out_path = recorder.save(
        output_dir,
        vlm_cost_usd=provider.cumulative_cost,
        final_scores={"cells_visited": len(visited_world)},
        termination_reason=termination_reason,
        generate_gif=True,
        provider_status=final_provider_status,
    )

    return {
        "cells_visited": len(visited_world),
        "vlm_cost_usd": provider.cumulative_cost,
        "output_dir": str(out_path),
        "termination_reason": termination_reason,
        "provider_status": final_provider_status,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = _parse_args()

    print(f"Scene      : {args.scene}")
    print(f"Steps      : {args.steps}")
    print(f"Model      : {args.model}")
    print(f"Output dir : {args.output_dir}")
    print()

    result = run_exploration(
        scene=args.scene,
        steps=args.steps,
        model=args.model,
        output_dir=args.output_dir,
    )

    print()
    print(f"Replay saved to : {result['output_dir']}")
    print(f"Cells visited   : {result['cells_visited']}")
    print(f"VLM cost        : ${result['vlm_cost_usd']:.6f}")
    print(f"Provider        : {format_provider_status(result['provider_status'])}")


if __name__ == "__main__":
    main()
