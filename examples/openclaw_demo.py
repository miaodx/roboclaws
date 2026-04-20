"""OpenClaw Gateway navigation demo — Phase 2.1 transport.

Routes one or more AI2-THOR agents through a locally-running OpenClaw
Gateway via the :class:`roboclaws.openclaw.bridge.OpenClawProvider` adapter.
Pure navigation — no game logic, no territory, no coverage — so the focus
stays on "can OpenClaw actually control the robot?".

This is the shipping path for Phase 2. Game modes over OpenClaw come back
in a later phase when long-running Gateway instances land.

Prerequisites
-------------
A local OpenClaw Gateway must be running with **N named agents**
pre-registered (``agent-0``, ``agent-1``, ...).  Use
``scripts/openclaw-bootstrap.sh`` — see ``docs/openclaw-local.md`` for the
full recipe.  No bind mount is required; frames flow inline as base64 data
URLs over the OpenAI-compatible ``/v1/chat/completions`` endpoint.

Usage
-----
::

    # One-shot setup (creates agent-0..agent-(AGENTS-1)):
    export KIMI_API_KEY=sk-...
    TOKEN=$(AGENTS=2 ./scripts/openclaw-bootstrap.sh)

    OPENCLAW_GATEWAY_TOKEN=$TOKEN python examples/openclaw_demo.py --steps 20

    python examples/openclaw_demo.py \
        --scene FloorPlan201 --agents 2 --steps 20 \
        --output-dir output/openclaw-demo \
        --gateway-url http://localhost:18789 \
        --agent-prefix agent-
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import NAVIGATION_ACTIONS, MultiAgentEngine
from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.visualizer import GameVisualizer
from roboclaws.core.vlm import format_provider_status, provider_status_snapshot
from roboclaws.openclaw.bridge import OpenClawProvider, OpenClawUnavailable

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
        description="Route AI2-THOR agents through a local OpenClaw Gateway.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--scene",
        default="FloorPlan201",
        help="AI2-THOR scene name (living-room range: FloorPlan201-230)",
    )
    p.add_argument("--agents", type=int, default=2, help="Number of agents")
    p.add_argument("--steps", type=int, default=20, help="Total steps across all agents")
    p.add_argument(
        "--output-dir",
        default="output/openclaw-demo",
        dest="output_dir",
        help="Directory to write replay files, GIF, and report.html",
    )
    p.add_argument(
        "--gateway-url",
        default=None,
        dest="gateway_url",
        help="OpenClaw Gateway base URL (defaults to OPENCLAW_GATEWAY_URL env var or "
        "http://localhost:18789)",
    )
    p.add_argument(
        "--token",
        default=None,
        help="Bearer token for the Gateway (defaults to OPENCLAW_GATEWAY_TOKEN env var)",
    )
    p.add_argument(
        "--agent-prefix",
        default="agent-",
        dest="agent_prefix",
        help=(
            "Prefix applied to agent_id to derive the named Gateway agent "
            "(model=openclaw/<prefix><id>). Must match the bootstrap's AGENT_PREFIX."
        ),
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
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


def run_openclaw_demo(
    scene: str,
    agent_count: int,
    steps: int,
    output_dir: str,
    gateway_url: str | None = None,
    token: str | None = None,
    agent_prefix: str = "agent-",
    thor_server_timeout: float = 100.0,
    thor_server_start_timeout: float = 300.0,
) -> dict[str, Any]:
    """Run a multi-agent navigation demo driven by a local OpenClaw Gateway.

    Agents take turns (round-robin).  Each step queries the Gateway for an
    action and executes it in the simulator.  The Gateway sees per-agent
    first-person frames, the overhead map, and a compact state dict — same
    contract as the other examples, just routed via ``/v1/chat/completions``
    against a named agent per simulation agent.

    Returns:
        Summary dict with ``steps_executed``, ``output_dir``, and a
        ``provider_status`` snapshot.
    """
    agent_names = [f"{agent_prefix}{i}" for i in range(agent_count)]
    print(f"Gateway URL   : {gateway_url or '$OPENCLAW_GATEWAY_URL or default'}")
    print(f"Agent prefix  : {agent_prefix}")
    print(f"Agents        : {', '.join(agent_names)} (model=openclaw/<agentId>)")

    provider_kwargs: dict[str, Any] = {"agent_prefix": agent_prefix}
    if gateway_url is not None:
        provider_kwargs["gateway_url"] = gateway_url
    if token is not None:
        provider_kwargs["token"] = token

    provider = OpenClawProvider(**provider_kwargs)

    # Precondition: confirm the first named agent exists before spinning up
    # Unity for a ~19-step wasted run. The probe also fails fast on auth,
    # 404 (chatCompletions disabled), and 400 (agent not registered).
    try:
        probe_reply = provider.ping(agent_id=0)
    except OpenClawUnavailable as exc:
        provider.close()
        raise SystemExit(
            f"Gateway precondition check failed: {exc}\n"
            f"Hint: re-run `scripts/openclaw-bootstrap.sh AGENTS={agent_count}` "
            f"with AGENT_PREFIX={agent_prefix!r}."
        ) from exc
    print(f"Probe         : openclaw/{agent_prefix}0 → {probe_reply.strip()[:80]!r}")

    engine = MultiAgentEngine(
        scene=scene,
        agent_count=agent_count,
        grid_size=_GRID_SIZE,
        server_timeout=thor_server_timeout,
        server_start_timeout=thor_server_start_timeout,
    )
    viz = GameVisualizer(
        grid_rows=_GRID_ROWS, grid_cols=_GRID_COLS, cell_px=15, agent_count=agent_count
    )
    recorder = ReplayRecorder(agent_count=agent_count, game="openclaw-demo")

    final_provider_status: dict[str, Any] = provider_status_snapshot(provider)
    steps_executed = 0
    termination_reason = "max_steps"

    try:
        initial_states = engine.get_all_agent_states()
        origin_ix, origin_iz = _pos_to_world_idx(initial_states[0].position)

        try:
            overhead_bg: np.ndarray | None = engine.get_overhead_frame()
        except Exception:  # noqa: BLE001 - mock engines may omit this
            overhead_bg = None

        visited_world: set[tuple[int, int]] = set()

        for step in range(steps):
            current_agent = step % agent_count
            agent_states = engine.get_all_agent_states()
            agent_frames = [s.frame for s in agent_states]

            for s in agent_states:
                visited_world.add(_pos_to_world_idx(s.position))

            # Agent positions in visualiser coordinates
            agent_positions_viz: list[tuple[int, int]] = []
            for s in agent_states:
                wx, wz = _pos_to_world_idx(s.position)
                rc = _world_to_viz(wx, wz, origin_ix, origin_iz)
                agent_positions_viz.append(rc if _in_bounds(*rc) else (_CENTER_ROW, _CENTER_COL))

            covered_viz = [
                rc
                for wx, wz in visited_world
                if _in_bounds(*(rc := _world_to_viz(wx, wz, origin_ix, origin_iz)))
            ]

            map_img = viz.render_overhead_map(
                agent_positions=agent_positions_viz,
                covered_cells=covered_viz,
                base_frame=overhead_bg,
            )
            map_frame = np.asarray(map_img.convert("RGB"), dtype=np.uint8)

            active_state = agent_states[current_agent]
            prompt_state: dict[str, Any] = {
                "game": "openclaw-demo",
                "step": step,
                "remaining_steps": steps - step,
                "my_agent_id": current_agent,
                "current_agent": current_agent,
                "agent_count": agent_count,
                "position": active_state.position,
                "rotation": active_state.rotation,
                "available_actions": NAVIGATION_ACTIONS,
            }

            # Numpy frames flow inline — no filesystem / bind-mount hop.
            prompt_images = [active_state.frame, map_frame]

            response = provider.get_action(images=prompt_images, state=prompt_state)
            action = response.get("action", "MoveAhead")
            if action not in NAVIGATION_ACTIONS:
                action = "MoveAhead"

            provider_status = provider_status_snapshot(provider)
            final_provider_status = provider_status

            if step % 5 == 0 or step == steps - 1:
                print(
                    f"  step {step:4d}/{steps}  |  "
                    f"agent {current_agent} ({agent_prefix}{current_agent})  |  "
                    f"action: {action}  |  "
                    f"provider: {format_provider_status(provider_status)}"
                )

            recorder.record_step(
                step=step,
                agent_id=current_agent,
                agent_frames=agent_frames,
                overhead_frame=map_frame,
                game_state={
                    "visited_cells": len(visited_world),
                    "current_agent": current_agent,
                },
                vlm_prompt_state=prompt_state,
                vlm_response=response,
                provider_status=provider_status,
            )

            engine.step(agent_id=current_agent, action=action)
            steps_executed = step + 1

    except KeyboardInterrupt:
        termination_reason = "keyboard_interrupt"
        print("\nStopped early.")
    finally:
        engine.close()
        provider.close()

    out_path = recorder.save(
        output_dir,
        vlm_cost_usd=provider.cumulative_cost,
        final_scores={"steps_executed": steps_executed},
        termination_reason=termination_reason,
        generate_gif=True,
        generate_report=True,
        provider_status=final_provider_status,
    )

    return {
        "steps_executed": steps_executed,
        "termination_reason": termination_reason,
        "output_dir": str(out_path),
        "provider_status": final_provider_status,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = _parse_args()

    print(f"Scene         : {args.scene}")
    print(f"Agents        : {args.agents}")
    print(f"Steps         : {args.steps}")
    print(f"Output dir    : {args.output_dir}")
    print()

    result = run_openclaw_demo(
        scene=args.scene,
        agent_count=args.agents,
        steps=args.steps,
        output_dir=args.output_dir,
        gateway_url=args.gateway_url,
        token=args.token,
        agent_prefix=args.agent_prefix,
        thor_server_timeout=args.thor_server_timeout,
        thor_server_start_timeout=args.thor_server_start_timeout,
    )

    print()
    print(f"Steps run     : {result['steps_executed']}")
    print(f"Stopped       : {result['termination_reason']}")
    print(f"Replay        : {result['output_dir']}")
    print(f"Provider      : {format_provider_status(result['provider_status'])}")


if __name__ == "__main__":
    main()
