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

    # OpenClaw backend (requires a running Gateway; set OPENCLAW_GATEWAY_TOKEN):
    python examples/territory_game.py --backend openclaw --agents 2 --steps 60
"""

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
from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.turn_metrics import (
    encode_frame_to_b64_jpeg,
    get_provider_turn_metrics,
    round_seconds,
    serialize_prompt_state,
    summarize_payload_metrics,
)
from roboclaws.core.views import (
    VIEW_VARIANTS,
    build_prompt_images,
    compute_world_bbox,
    encode_prompt_images,
    image_labels_for_variant,
)
from roboclaws.core.visualizer import GameVisualizer
from roboclaws.core.vlm import (
    ProviderHealthError,
    create_provider,
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
    p.add_argument(
        "--views",
        choices=VIEW_VARIANTS,
        default="baseline",
        help="Prompt image variant to use for each agent decision.",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


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
    views: str = "baseline",
) -> dict[str, object]:
    """Run a multi-agent territory control episode and save results to *output_dir*.

    Args:
        scene: AI2-THOR scene name.
        agent_count: Number of competing agents (2 or 3).
        steps: Maximum number of game steps.
        model: VLM model alias (used when ``backend="vlm"``).
        output_dir: Directory for replay files, GIF, and territory map.
        backend: Transport backend — ``"vlm"`` (direct cloud API) or
                 ``"openclaw"`` (local Gateway via :mod:`roboclaws.openclaw.bridge`).
                 ``"direct"`` is a deprecated alias for ``"vlm"``.
        gateway_url: Override the Gateway base URL (debug only).
        thor_server_timeout: AI2-THOR backend action timeout for slow local runs.
        thor_server_start_timeout: AI2-THOR Unity startup timeout.

    Returns:
        Summary dict with keys ``cells_claimed``, ``blocking_events``,
        ``termination_reason``, ``vlm_cost_usd``, and ``output_dir``.
    """
    from roboclaws.openclaw.bridge import OpenClawUnavailable, build_openclaw_provider_or_die

    # SIGTERM → raise KeyboardInterrupt so the try/finally below flushes a
    # partial replay (including any report.html) before exit.  Matches how
    # the run already handles Ctrl-C.
    def _sigterm(signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt(f"Stopped by signal {signum}")

    signal.signal(signal.SIGTERM, _sigterm)

    # "direct" is a deprecated alias for "vlm"
    effective_backend = "vlm" if backend == "direct" else backend

    # AGENT_SOULS drives both viz tinting and per-agent system-prompt injection
    # (the latter is how the VLM backend mirrors the Gateway's per-agent state).
    souls_env = os.environ.get("AGENT_SOULS", "")
    souls_dir = os.environ.get("SOULS_DIR", _DEFAULT_SOULS_DIR)
    agent_labels, agent_soul_content = load_agent_souls(souls_env, agent_count, souls_dir)

    if effective_backend == "openclaw":
        provider = build_openclaw_provider_or_die(gateway_url=gateway_url, agent_count=agent_count)
    else:
        # Pass soul content only to providers that support per-agent SOULs.
        # KimiProvider + AnthropicProvider both accept ``agent_souls``; others
        # silently ignore the kwarg.
        kwargs = {"agent_souls": agent_soul_content} if agent_soul_content else {}
        try:
            provider = create_provider(model, **kwargs)
        except TypeError:
            provider = create_provider(model)
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
    # origin_ix/origin_iz initialised inside try so KeyboardInterrupt is always caught
    origin_ix: int = 0
    origin_iz: int = 0
    # AI2-THOR's third-party overhead camera is static, so capture the frame
    # once and reuse it as the map background for every step.
    overhead_bg: np.ndarray | None = None
    termination_reason_override: str | None = None
    final_provider_status: dict[str, Any] = provider_status_snapshot(provider)
    final_agent_positions_world: list[tuple[int, int]] = []
    final_agent_rotations: list[dict[str, float]] = []

    try:
        # Record starting position of agent 0 as the map origin for centring
        initial_states = engine.get_all_agent_states()
        origin_ix, origin_iz = _pos_to_world_idx(initial_states[0].position)
        try:
            overhead_bg = engine.get_overhead_frame()
        except Exception:  # noqa: BLE001 - mock engines may omit this
            overhead_bg = None

        while not game.is_over():
            step_started = time.perf_counter()
            turn_metrics: dict[str, Any] = {"timings": {}, "payload": {}}
            # ----------------------------------------------------------------
            # Capture state BEFORE this step for recording and visualisation
            # ----------------------------------------------------------------
            state_capture_started = time.perf_counter()
            agent_states = engine.get_all_agent_states()
            agent_frames = [s.frame for s in agent_states]
            agent_positions_world = [_pos_to_world_idx(state.position) for state in agent_states]
            final_agent_positions_world = agent_positions_world
            final_agent_rotations = [state.rotation for state in agent_states]
            turn_metrics["timings"]["state_capture_seconds"] = round_seconds(
                time.perf_counter() - state_capture_started
            )

            # Build per-agent claimed-cell dicts in visualiser coordinates
            map_render_started = time.perf_counter()
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
            for wx, wz in agent_positions_world:
                rc = _world_to_viz(wx, wz, origin_ix, origin_iz)
                agent_positions_viz.append(rc if _in_bounds(*rc) else (_CENTER_ROW, _CENTER_COL))

            map_img = viz.render_overhead_map(
                agent_positions=agent_positions_viz,
                claimed_cells=claimed_cells_viz,
                base_frame=overhead_bg,
            )
            map_frame = np.asarray(map_img.convert("RGB"), dtype=np.uint8)
            structured_map_frame: np.ndarray | None = None
            if views != "baseline":
                structured_img = viz.render_structured_map(
                    agent_positions=agent_positions_world,
                    agent_rotations=final_agent_rotations,
                    reachable_cells=reachable_cells,
                    claimed_cells={
                        agent_id: list(cells) for agent_id, cells in game._agent_cells.items()
                    },
                    world_bbox=world_bbox,
                )
                structured_map_frame = np.asarray(structured_img.convert("RGB"), dtype=np.uint8)
            turn_metrics["timings"]["map_render_seconds"] = round_seconds(
                time.perf_counter() - map_render_started
            )

            game_state = game.get_state()
            current_agent = game.current_agent_id
            prompt_state_started = time.perf_counter()
            prompt_state = game.get_prompt_state(current_agent)
            prompt_state["views"] = views
            turn_metrics["timings"]["prompt_state_seconds"] = round_seconds(
                time.perf_counter() - prompt_state_started
            )
            prompt_state_text, prompt_state_metrics = serialize_prompt_state(prompt_state)
            turn_metrics["timings"]["prompt_state_json_seconds"] = prompt_state_metrics[
                "serialize_seconds"
            ]
            chase_cam_frame: np.ndarray | None = None
            if views == "map-v2+chase":
                engine.add_chase_cam(current_agent)
                engine.update_chase_cam(current_agent)
                chase_cam_frame = engine.get_chase_cam_frame(current_agent)

            prompt_image_frames = build_prompt_images(
                variant=views,
                fpv_frame=agent_states[current_agent].frame,
                baseline_overhead_frame=map_frame,
                structured_overhead_frame=structured_map_frame,
                chase_cam_frame=chase_cam_frame,
            )
            replay_overhead = (
                structured_map_frame if structured_map_frame is not None else map_frame
            )
            payload_metrics: dict[str, Any]
            if effective_backend == "openclaw":
                prompt_images: list[Any] = list(prompt_image_frames)
                payload_metrics = summarize_payload_metrics(
                    transport="openclaw_ndarray",
                    prompt_state_chars=prompt_state_metrics["chars"],
                    image_metrics=[{"label": label} for label in image_labels_for_variant(views)],
                )
                turn_metrics["timings"]["image_encode_seconds"] = 0.0
            else:
                prompt_images, image_metrics, encode_seconds = encode_prompt_images(
                    variant=views,
                    image_frames=prompt_image_frames,
                    encoder=encode_frame_to_b64_jpeg,
                )
                payload_metrics = summarize_payload_metrics(
                    transport="vlm_base64_jpeg",
                    prompt_state_chars=prompt_state_metrics["chars"],
                    image_metrics=image_metrics,
                    extra={"prompt_state_preview": prompt_state_text[:120]},
                )
                turn_metrics["timings"]["image_encode_seconds"] = round_seconds(encode_seconds)
            turn_metrics["payload"] = payload_metrics

            # ----------------------------------------------------------------
            # Execute one game step (VLM decision + engine action internally)
            # ----------------------------------------------------------------
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
                # Kimi quota exhaustion, instructor retry wrappers, HTTP 4xx/5xx
                # from upstream: none of these are transient (so the circuit
                # breaker doesn't fire) but we still want a usable report for
                # the steps completed so far.
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

            record_started = time.perf_counter()
            recorder.record_step(
                step=step_num,
                agent_id=current_agent,
                agent_frames=agent_frames,
                overhead_frame=replay_overhead,
                game_state=game_state,
                vlm_prompt_state=prompt_state,
                vlm_response=response,
                provider_status=provider_status,
                turn_metrics=turn_metrics,
            )
            turn_metrics["timings"]["record_step_seconds"] = round_seconds(
                time.perf_counter() - record_started
            )
            turn_metrics["timings"]["step_loop_seconds"] = round_seconds(
                time.perf_counter() - step_started
            )
            recorder._steps[-1].turn_metrics = dict(turn_metrics)

            step_num += 1

    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        engine.close()

    result = game.get_result()
    termination_reason = termination_reason_override or result.termination_reason
    final_provider_status = (
        provider_status_snapshot(provider) if not final_provider_status else final_provider_status
    )

    # Save replay (GIF + JSON + self-contained HTML report)
    out_path = recorder.save(
        output_dir,
        vlm_cost_usd=provider.cumulative_cost,
        final_scores={f"agent_{a}": c for a, c in result.cells_claimed.items()},
        termination_reason=termination_reason,
        generate_gif=True,
        generate_report=True,
        provider_status=final_provider_status,
    )

    # Save final territory map as a standalone PNG
    if views == "baseline":
        final_claimed_viz: dict[int, list[tuple[int, int]]] = {}
        for agent_id, cells in game._agent_cells.items():
            final_claimed_viz[agent_id] = [
                rc
                for wx, wz in cells
                if _in_bounds(*(rc := _world_to_viz(wx, wz, origin_ix, origin_iz)))
            ]
        final_map = viz.render_overhead_map(
            agent_positions=[(_CENTER_ROW, _CENTER_COL)] * agent_count,
            claimed_cells=final_claimed_viz,
            base_frame=overhead_bg,
        )
    else:
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = _parse_args()

    effective_backend = "vlm" if args.backend == "direct" else args.backend
    if args.backend == "direct":
        print("Warning: --backend direct is deprecated; use --backend vlm")

    print(f"Scene      : {args.scene}")
    print(f"Agents     : {args.agents}")
    print(f"Steps      : {args.steps}")
    print(f"Model      : {args.model}")
    print(f"Backend    : {effective_backend}")
    print(f"THOR step timeout  : {args.thor_server_timeout}")
    print(f"THOR start timeout : {args.thor_server_start_timeout}")
    wall_budget = args.max_wall_seconds if args.max_wall_seconds > 0 else None
    print(f"Wallclock budget   : {wall_budget if wall_budget else 'disabled'}")
    print(f"Views             : {args.views}")
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
        views=args.views,
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
