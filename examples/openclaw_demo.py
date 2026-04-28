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
``scripts/openclaw-bootstrap.sh`` — see ``docs/openclw/openclaw-local.md`` for the
full recipe.  No bind mount is required; frames flow inline as base64 data
URLs over the OpenAI-compatible ``/v1/chat/completions`` endpoint.

Usage
-----
::

    # One-shot setup (creates agent-0..agent-(AGENTS-1)):
    export KIMI_API_KEY=sk-...
    TOKEN=$(AGENTS=2 ./scripts/openclaw-bootstrap.sh)

    OPENCLAW_GATEWAY_TOKEN=$TOKEN python examples/openclaw_demo.py

    python examples/openclaw_demo.py \
        --scene FloorPlan201 --agents 2 --steps 200 \
        --output-dir output/openclaw-demo \
        --gateway-url http://localhost:18789 \
        --agent-prefix agent-

The loop auto-converges: when ``--max-stale-steps`` consecutive steps
yield no newly-visited grid cell, the demo exits early with
``termination_reason="stale"`` so it doesn't keep burning VLM tokens
after the agents have already explored the accessible area.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import NAVIGATION_ACTIONS, MultiAgentEngine
from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.views import (
    make_navigation_view_context,
    render_navigation_prompt_bundle,
)
from roboclaws.core.vlm import format_provider_status, provider_status_snapshot
from roboclaws.openclaw.bridge import OpenClawProvider, OpenClawUnavailable

# ---------------------------------------------------------------------------
# Grid constants — must match MultiAgentEngine grid_size
# ---------------------------------------------------------------------------

_GRID_SIZE: float = 0.25  # metres
_GRID_ROWS: int = 40
_GRID_COLS: int = 40
_VIEW_VARIANT = "map-v2+chase"


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
    p.add_argument(
        "--steps",
        type=int,
        default=200,
        help=(
            "Maximum total steps across all agents (auto-converges earlier; see --max-stale-steps)"
        ),
    )
    p.add_argument(
        "--max-stale-steps",
        dest="max_stale_steps",
        type=int,
        default=None,
        help="Stop once this many consecutive steps yield no newly-visited grid cell. "
        "Defaults to 3*agents (matches territory_game's stale-round heuristic). "
        "Pass 0 to disable auto-convergence and always run the full --steps budget.",
    )
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
    max_stale_steps: int | None = None,
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
    view_context = make_navigation_view_context(
        engine,
        agent_count=agent_count,
        grid_rows=_GRID_ROWS,
        grid_cols=_GRID_COLS,
        cell_px=15,
    )
    recorder = ReplayRecorder(agent_count=agent_count, game="openclaw-demo")

    final_provider_status: dict[str, Any] = provider_status_snapshot(provider)
    steps_executed = 0
    termination_reason = "max_steps"

    # Auto-convergence: stop once this many consecutive steps add no new grid
    # cell to visited_world.  Matches territory_game's "stuck for 2 rounds"
    # heuristic (2*agent_count) but a bit looser (3 rounds) because pure
    # navigation tends to burn turns on collision-induced rotations before
    # breaking out to new area.  Pass 0 to disable.
    stale_threshold = 3 * agent_count if max_stale_steps is None else max(0, max_stale_steps)
    stale_steps = 0

    try:
        for step in range(steps):
            current_agent = step % agent_count
            agent_states = engine.get_all_agent_states()
            agent_frames = [s.frame for s in agent_states]

            cells_before = len(view_context.visited_world)
            prompt_bundle = render_navigation_prompt_bundle(
                engine=engine,
                context=view_context,
                agent_states=agent_states,
                current_agent=current_agent,
            )
            if len(view_context.visited_world) > cells_before:
                stale_steps = 0
            else:
                stale_steps += 1

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
                "views": _VIEW_VARIANT,
                "image_labels": list(prompt_bundle.image_labels),
                "available_actions": NAVIGATION_ACTIONS,
            }

            response = provider.get_action(images=prompt_bundle.prompt_images, state=prompt_state)
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

            primary_view_label = (
                prompt_bundle.image_labels[1] if len(prompt_bundle.image_labels) > 1 else "overhead"
            )
            extra_views: list[tuple[str, Any]] = []
            if prompt_bundle.structured_overhead_frame is not None:
                extra_views.append(("overhead", prompt_bundle.raw_overhead_frame))
            if prompt_bundle.chase_cam_frame is not None:
                extra_views.append(("chase", prompt_bundle.chase_cam_frame))

            recorder.record_step(
                step=step,
                agent_id=current_agent,
                agent_frames=agent_frames,
                overhead_frame=prompt_bundle.trace_overhead_frame,
                overhead_label=primary_view_label,
                extra_views=extra_views,
                game_state={
                    "visited_cells": len(view_context.visited_world),
                    "current_agent": current_agent,
                },
                vlm_prompt_state=prompt_state,
                vlm_response=response,
                provider_status=provider_status,
            )

            engine.step(agent_id=current_agent, action=action)
            steps_executed = step + 1

            if stale_threshold > 0 and stale_steps >= stale_threshold:
                termination_reason = "stale"
                print(
                    f"  step {step:4d}/{steps}  |  "
                    f"auto-converged: {stale_steps} consecutive steps with no new cell "
                    f"(threshold={stale_threshold}, visited={len(view_context.visited_world)})"
                )
                break

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

    resolved_stale = args.max_stale_steps if args.max_stale_steps is not None else 3 * args.agents
    print(f"Scene         : {args.scene}")
    print(f"Agents        : {args.agents}")
    print(f"Steps (max)   : {args.steps}")
    print(f"Stale cutoff  : {resolved_stale if resolved_stale > 0 else 'disabled'}")
    print(f"Views         : {_VIEW_VARIANT}")
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
        max_stale_steps=args.max_stale_steps,
    )

    print()
    print(f"Steps run     : {result['steps_executed']}")
    print(f"Stopped       : {result['termination_reason']}")
    print(f"Replay        : {result['output_dir']}")
    print(f"Provider      : {format_provider_status(result['provider_status'])}")


if __name__ == "__main__":
    main()
