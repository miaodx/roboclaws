"""Run a multi-agent territory control game in AI2-THOR."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.game_run import (
    create_game_provider,
    prepare_prompt_payload,
    record_game_turn,
)
from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.turn_metrics import (
    get_provider_turn_metrics,
    round_seconds,
    serialize_prompt_state,
)
from roboclaws.core.views import (
    compute_world_bbox,
    render_game_prompt_bundle,
)
from roboclaws.core.views import (
    pos_to_world_idx as shared_pos_to_world_idx,
)
from roboclaws.core.visualizer import GameVisualizer
from roboclaws.core.vlm import (
    ProviderHealthError,
    format_provider_status,
    load_agent_souls,
    provider_status_snapshot,
)
from roboclaws.games.territory import TerritoryGame

_DEFAULT_SOULS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
    "ai2thor-navigator",
    "souls",
)

_GRID_SIZE: float = 0.25  # metres
_GRID_ROWS: int = 40
_GRID_COLS: int = 40
_VIEW_VARIANT = "map-v2+chase"


def _pos_to_world_idx(pos: dict[str, float]) -> tuple[int, int]:
    """Convert a continuous AI2-THOR (x, z) position to a discrete world index."""
    return shared_pos_to_world_idx(pos, grid_size=_GRID_SIZE)


def _normalize_backend(backend: str) -> str:
    return "vlm" if backend == "direct" else backend


def _resolve_wall_budget(max_wall_seconds: float) -> float | None:
    return max_wall_seconds if max_wall_seconds > 0 else None


def _install_sigterm_handler() -> None:
    """Convert SIGTERM into KeyboardInterrupt for partial-save handling."""

    def _sigterm(signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt(f"Stopped by signal {signum}")

    signal.signal(signal.SIGTERM, _sigterm)


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
    p.add_argument(
        "--thor-server-timeout",
        dest="thor_server_timeout",
        type=float,
        default=100.0,
        help="AI2-THOR backend action timeout in seconds for slow local runs",
    )
    p.add_argument(
        "--thor-server-start-timeout",
        dest="thor_server_start_timeout",
        type=float,
        default=300.0,
        help="AI2-THOR Unity startup timeout in seconds",
    )
    p.add_argument(
        "--max-wall-seconds",
        dest="max_wall_seconds",
        type=float,
        default=1200.0,
        help="Total game wallclock budget in seconds (default 1200 = 20 min). Pass 0 to disable.",
    )
    p.add_argument(
        "--backend",
        choices=["vlm", "openclaw", "direct"],  # "direct" is a deprecated alias for "vlm"
        default="vlm",
        dest="backend",
        help="VLM transport: 'vlm' (cloud API) or 'openclaw' (local Gateway). "
        "Token read from OPENCLAW_GATEWAY_TOKEN env var.",
    )
    p.add_argument(
        "--gateway-url",
        default=None,
        dest="gateway_url",
        help="OpenClaw Gateway base URL (debug override; default: http://localhost:18789)",
    )
    return p.parse_args(argv)


def run_territory_game(
    *,
    scene: str,
    agent_count: int,
    steps: int,
    model: str = "mock",
    output_dir: str,
    backend: str = "vlm",
    gateway_url: str | None = None,
    thor_server_timeout: float = 100.0,
    thor_server_start_timeout: float = 300.0,
    max_wall_seconds: float | None = 1200.0,
    provider_seed: int | None = None,
) -> dict[str, object]:
    """Run a territory episode and save replay/artifacts to ``output_dir``."""
    from roboclaws.openclaw.bridge import OpenClawUnavailable

    _install_sigterm_handler()
    effective_backend = _normalize_backend(backend)

    # AGENT_SOULS drives both viz tinting and per-agent system-prompt injection
    # (the latter is how the VLM backend mirrors the Gateway's per-agent state).
    souls_env = os.environ.get("AGENT_SOULS", "")
    souls_dir = os.environ.get("SOULS_DIR", _DEFAULT_SOULS_DIR)
    agent_labels, agent_soul_content = load_agent_souls(souls_env, agent_count, souls_dir)

    provider = create_game_provider(
        backend=effective_backend,
        gateway_url=gateway_url,
        agent_count=agent_count,
        model=model,
        agent_soul_content=agent_soul_content,
        provider_seed=provider_seed,
    )
    engine = MultiAgentEngine(
        scene=scene,
        agent_count=agent_count,
        grid_size=_GRID_SIZE,
        server_timeout=thor_server_timeout,
        server_start_timeout=thor_server_start_timeout,
    )
    reachable_cells = engine.get_reachable_positions()
    world_bbox = compute_world_bbox(reachable_cells)
    viz = GameVisualizer(
        grid_rows=_GRID_ROWS,
        grid_cols=_GRID_COLS,
        cell_px=15,
        agent_count=agent_count,
        agent_labels=agent_labels if agent_labels else None,
    )
    recorder = ReplayRecorder(agent_count=agent_count, game="territory")
    game = TerritoryGame(
        engine=engine,
        provider=provider,
        max_steps=steps,
        grid_size=_GRID_SIZE,
        reachable_cells=reachable_cells,
        max_wall_seconds=max_wall_seconds,
    )

    step_num = 0
    overhead_bg: np.ndarray | None = None
    overhead_camera_pose: dict[str, Any] | None = None
    termination_reason_override: str | None = None
    final_provider_status: dict[str, Any] = provider_status_snapshot(provider)
    final_agent_positions_world: list[tuple[int, int]] = []
    final_agent_rotations: list[dict[str, float]] = []

    try:
        try:
            overhead_bg = engine.get_overhead_frame()
        except Exception:  # noqa: BLE001 - mock engines may omit this
            overhead_bg = None
        try:
            overhead_camera_pose = engine.get_overhead_camera_properties()
        except Exception:  # noqa: BLE001 - mock engines may omit this
            overhead_camera_pose = None

        while not game.is_over():
            step_started = time.perf_counter()
            turn_metrics: dict[str, Any] = {"timings": {}, "payload": {}}
            state_capture_started = time.perf_counter()
            agent_states = engine.get_all_agent_states()
            agent_frames = [s.frame for s in agent_states]
            agent_positions_world = [_pos_to_world_idx(state.position) for state in agent_states]
            final_agent_positions_world = agent_positions_world
            final_agent_rotations = [state.rotation for state in agent_states]
            turn_metrics["timings"]["state_capture_seconds"] = round_seconds(
                time.perf_counter() - state_capture_started
            )

            map_render_started = time.perf_counter()
            claimed_cells = {agent_id: list(cells) for agent_id, cells in game._agent_cells.items()}
            current_agent = game.current_agent_id
            prompt_bundle = render_game_prompt_bundle(
                engine=engine,
                visualizer=viz,
                agent_states=agent_states,
                current_agent=current_agent,
                reachable_cells=reachable_cells,
                world_bbox=world_bbox,
                overhead_background=overhead_bg,
                overhead_camera_pose=overhead_camera_pose,
                claimed_cells=claimed_cells,
                grid_size=_GRID_SIZE,
            )
            structured_map_frame = prompt_bundle.trace_overhead_frame
            agent_positions_world = prompt_bundle.agent_positions_world
            final_agent_positions_world = agent_positions_world
            turn_metrics["timings"]["map_render_seconds"] = round_seconds(
                time.perf_counter() - map_render_started
            )

            game_state = game.get_state()
            prompt_state_started = time.perf_counter()
            prompt_state = game.get_prompt_state(current_agent)
            prompt_state["views"] = _VIEW_VARIANT
            turn_metrics["timings"]["prompt_state_seconds"] = round_seconds(
                time.perf_counter() - prompt_state_started
            )
            prompt_state_text, prompt_state_metrics = serialize_prompt_state(prompt_state)
            turn_metrics["timings"]["prompt_state_json_seconds"] = prompt_state_metrics[
                "serialize_seconds"
            ]
            (
                prompt_images,
                turn_metrics["payload"],
                turn_metrics["timings"]["image_encode_seconds"],
            ) = prepare_prompt_payload(
                backend=effective_backend,
                prompt_image_frames=prompt_bundle.prompt_images,
                prompt_state_text=prompt_state_text,
                prompt_state_metrics=prompt_state_metrics,
                view_variant=_VIEW_VARIANT,
            )

            provider_started = time.perf_counter()
            try:
                response = game.decide(images=prompt_images, prompt_state=prompt_state)
            except (ProviderHealthError, OpenClawUnavailable) as exc:
                termination_reason_override = "provider_unstable"
                final_provider_status = (
                    exc.status
                    if isinstance(exc, ProviderHealthError) and exc.status
                    else provider_status_snapshot(provider)
                )
                print(
                    f"  step {step_num:4d}/{steps}  |  provider stop: {exc}\n"
                    f"  provider: {format_provider_status(final_provider_status)}"
                )
                break
            except Exception as exc:  # noqa: BLE001 - ensure partial-save on any provider error
                termination_reason_override = "provider_error"
                final_provider_status = provider_status_snapshot(provider)
                exc_kind = exc.__class__.__name__
                print(
                    f"  step {step_num:4d}/{steps}  |  provider error "
                    f"({exc_kind}): {str(exc)[:240]}\n"
                    f"  provider: {format_provider_status(final_provider_status)}"
                )
                break
            turn_metrics["timings"]["provider_call_seconds"] = round_seconds(
                time.perf_counter() - provider_started
            )
            provider_turn_metrics = get_provider_turn_metrics(provider)
            if provider_turn_metrics:
                turn_metrics["timings"].update(provider_turn_metrics.get("timings", {}))
                if provider_turn_metrics.get("payload"):
                    turn_metrics["payload"] = provider_turn_metrics["payload"]
                if provider_turn_metrics.get("provider"):
                    turn_metrics["provider"] = provider_turn_metrics["provider"]

            execute_started = time.perf_counter()
            executed_action = game.execute_action(response["action"])
            response["executed_action"] = executed_action
            turn_metrics["timings"]["execute_action_seconds"] = round_seconds(
                time.perf_counter() - execute_started
            )
            provider_status = provider_status_snapshot(provider)
            final_provider_status = provider_status

            if step_num % 10 == 0:
                scores = game.get_scores()
                scores_str = "  ".join(f"A{a}:{c}" for a, c in sorted(scores.items()))
                print(
                    f"  step {step_num:4d}/{steps}  |  "
                    f"claimed: {scores_str}  |  action: {executed_action}  |  "
                    f"provider: {format_provider_status(provider_status)}"
                )

            record_game_turn(
                recorder=recorder,
                step=step_num,
                agent_id=current_agent,
                agent_frames=agent_frames,
                overhead_frame=structured_map_frame,
                game_state=game_state,
                prompt_state=prompt_state,
                response=response,
                provider_status=provider_status,
                turn_metrics=turn_metrics,
                step_started=step_started,
            )

            step_num += 1

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        engine.close()

    result = game.get_result()
    termination_reason = termination_reason_override or result.termination_reason
    final_provider_status = final_provider_status or provider_status_snapshot(provider)

    out_path = recorder.save(
        output_dir,
        vlm_cost_usd=provider.cumulative_cost,
        final_scores={f"agent_{a}": c for a, c in result.cells_claimed.items()},
        termination_reason=termination_reason,
        generate_gif=True,
        generate_report=True,
        provider_status=final_provider_status,
    )

    final_map = viz.render_structured_map(
        agent_positions=final_agent_positions_world or [(0, 0)] * agent_count,
        agent_rotations=final_agent_rotations or [{"y": 0.0}] * agent_count,
        reachable_cells=reachable_cells,
        claimed_cells={agent_id: list(cells) for agent_id, cells in game._agent_cells.items()},
        world_bbox=world_bbox,
    )
    GameVisualizer.save_png(final_map, out_path / "territory_final.png")

    return {
        "cells_claimed": result.cells_claimed,
        "total_steps": result.total_steps,
        "blocking_events": result.blocking_events,
        "termination_reason": termination_reason,
        "vlm_cost_usd": provider.cumulative_cost,
        "output_dir": str(out_path),
        "provider_status": final_provider_status,
    }


def main() -> None:
    args = _parse_args()

    effective_backend = _normalize_backend(args.backend)
    if args.backend == "direct":
        print("Warning: --backend direct is deprecated; use --backend vlm")

    print(f"Scene      : {args.scene}")
    print(f"Agents     : {args.agents}")
    print(f"Steps      : {args.steps}")
    print(f"Model      : {args.model}")
    print(f"Backend    : {effective_backend}")
    print(f"THOR step timeout  : {args.thor_server_timeout}")
    print(f"THOR start timeout : {args.thor_server_start_timeout}")
    wall_budget = _resolve_wall_budget(args.max_wall_seconds)
    print(f"Wallclock budget   : {wall_budget if wall_budget else 'disabled'}")
    print(f"Views      : {_VIEW_VARIANT}")
    print(f"Output dir : {args.output_dir}")
    print()

    result = run_territory_game(
        scene=args.scene,
        agent_count=args.agents,
        steps=args.steps,
        model=args.model,
        output_dir=args.output_dir,
        backend=args.backend,
        gateway_url=args.gateway_url,
        thor_server_timeout=args.thor_server_timeout,
        thor_server_start_timeout=args.thor_server_start_timeout,
        max_wall_seconds=wall_budget,
    )

    print()
    print(f"Game over  : {result['termination_reason']}")
    print(f"Blocking   : {result['blocking_events']}")
    for agent_id, count in sorted(result["cells_claimed"].items()):
        print(f"  Agent {agent_id} : {count} cells claimed")
    print(f"Replay     : {result['output_dir']}")
    print(f"VLM cost   : ${result['vlm_cost_usd']:.6f}")
    print(f"Provider   : {format_provider_status(result['provider_status'])}")


if __name__ == "__main__":
    main()
