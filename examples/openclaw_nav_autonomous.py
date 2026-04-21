#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.openclaw.bridge import OpenClawBridge, RunResult
from roboclaws.openclaw.sim_server import SimHTTPServer

log = logging.getLogger("openclaw-nav-autonomous")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the autonomous single-agent OpenClaw navigation demo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--scene", default="FloorPlan201")
    parser.add_argument("--max-moves", type=int, default=200)
    parser.add_argument("--wall-budget", type=float, default=600.0)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args(argv)


def _default_output_dir() -> Path:
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return Path(f"output/openclaw-autonomous/{stamp}")


def _kickoff_prompt(max_moves: int) -> str:
    return (
        "You are navigating a simulated indoor room through tool calls.\n\n"
        f"You may take up to {max_moves} physical moves before the run ends.\n"
        "Use the observe, move, and done tools declared in "
        "skills/ai2thor-navigator/SKILL.md. Follow the Human messages contract "
        "documented there too — if a tool response includes human_message, acknowledge it in "
        "your reasoning and decide whether to follow it.\n\n"
        "Start by calling observe. Then explore the room methodically. Call done when you are "
        "finished or stuck."
    )


def _start_stdin_thread(
    sim_server: SimHTTPServer,
    stop_event: threading.Event,
) -> threading.Thread | None:
    if not sys.stdin.isatty():
        log.info("interjection disabled (no TTY)")
        return None

    def _stdin_pump() -> None:
        while not stop_event.is_set():
            line = sys.stdin.readline()
            if not line:
                break
            message = line.strip()
            if message:
                sim_server.enqueue_human_message(message)
                log.info("queued human message: %s", message[:80])

    thread = threading.Thread(target=_stdin_pump, daemon=True, name="stdin-pump")
    thread.start()
    log.info("stdin reader thread started (type a line then Enter to interject)")
    return thread


def run_autonomous_navigation(
    *,
    scene: str,
    max_moves: int,
    wall_budget: float,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    engine: MultiAgentEngine | None = None
    sim_server: SimHTTPServer | None = None
    bridge: OpenClawBridge | None = None
    stdin_thread: threading.Thread | None = None
    stdin_stop = threading.Event()
    gateway_started = False
    run_result: RunResult | None = None

    try:
        log.info("starting MultiAgentEngine(scene=%s, agent_count=1)", scene)
        engine = MultiAgentEngine(scene=scene, agent_count=1)

        sim_server = SimHTTPServer(engine, agent_id=0, run_dir=output_dir, port=18788)
        log.info("SimHTTPServer listening on http://127.0.0.1:%s", sim_server.port)

        env = dict(os.environ)
        env["TIMEOUT_SECONDS"] = str(int(wall_budget + 60))
        env["SIM_SERVER_URL"] = "http://host.docker.internal:18788"
        log.info("bootstrapping Gateway (TIMEOUT_SECONDS=%s)", env["TIMEOUT_SECONDS"])
        bootstrap = subprocess.run(
            ["./scripts/openclaw-bootstrap.sh"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        token = bootstrap.stdout.strip()
        gateway_started = True
        log.info("Gateway started, bearer token captured")

        stdin_thread = _start_stdin_thread(sim_server, stdin_stop)

        bridge = OpenClawBridge(
            gateway_url="http://127.0.0.1:18789",
            token=token,
        )
        run_result = bridge.start_run(
            agent_id=0,
            prompt=_kickoff_prompt(max_moves),
            wall_budget_s=wall_budget,
            done_event=sim_server.done_event,
        )
        log.info(
            "start_run returned: terminated_by=%s wallclock=%.1fs",
            run_result.terminated_by,
            run_result.wallclock_s,
        )

        (output_dir / "run_result.json").write_text(
            json.dumps(
                {
                    "terminated_by": run_result.terminated_by,
                    "wallclock_s": run_result.wallclock_s,
                    "final_message": run_result.final_message,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        log.info("rendering replay.gif + report.html")
        subprocess.run(
            [sys.executable, "scripts/render_autonomous_replay.py", "--run-dir", str(output_dir)],
            check=False,
        )
        log.info("artifacts at %s", output_dir)
    finally:
        if sim_server is not None:
            log.info("teardown: stopping sim server")
            sim_server.close()
        if gateway_started:
            log.info("teardown: removing openclaw-gateway container")
            subprocess.run(
                ["docker", "rm", "-f", "openclaw-gateway"],
                check=False,
                capture_output=True,
                text=True,
            )
        stdin_stop.set()
        if stdin_thread is not None:
            log.info("teardown: stopping stdin reader thread")
            stdin_thread.join(timeout=0.2)
        if bridge is not None:
            bridge.close()
        if engine is not None:
            log.info("teardown: stopping MultiAgentEngine")
            engine.close()

    assert run_result is not None
    return {
        "output_dir": str(output_dir),
        "terminated_by": run_result.terminated_by,
        "wallclock_s": run_result.wallclock_s,
        "final_message": run_result.final_message,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    args = _parse_args()
    output_dir = args.output_dir or _default_output_dir()
    result = run_autonomous_navigation(
        scene=args.scene,
        max_moves=args.max_moves,
        wall_budget=args.wall_budget,
        output_dir=output_dir,
    )
    print(f"terminated_by: {result['terminated_by']}")
    print(f"wallclock_s: {result['wallclock_s']:.1f}")
    print(f"artifacts at {result['output_dir']}")


if __name__ == "__main__":
    main()
