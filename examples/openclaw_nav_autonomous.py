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
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.openclaw.bridge import OpenClawBridge, OpenClawUnavailable, RunResult
from roboclaws.openclaw.sim_server import SimHTTPServer

log = logging.getLogger("openclaw-nav-autonomous")
_WATCHDOG_INTERVAL_S = 15.0
_DEFAULT_GATEWAY_CONTAINER = "openclaw-gateway"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the autonomous single-agent OpenClaw navigation demo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--scene", default="FloorPlan201")
    parser.add_argument("--max-moves", type=int, default=200)
    parser.add_argument("--wall-budget", type=float, default=600.0)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Reuse an already-running Gateway instead of bootstrapping/removing the container.",
    )
    return parser.parse_args(argv)


def _default_output_dir() -> Path:
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return Path(f"output/openclaw-autonomous/{stamp}")


def _kickoff_prompt(max_moves: int) -> str:
    return (
        "You are navigating a simulated indoor room through tool calls.\n\n"
        f"Your target budget is {max_moves} physical moves for this run. Treat that as the "
        "intended horizon, not merely a ceiling: keep working until you are stuck, the budget "
        "is nearly exhausted, or you have a concrete reason to stop.\n"
        "Before acting, use the read tool to read "
        "skills/ai2thor-navigator/SKILL.md and follow it exactly.\n"
        "The local execution environment is already live. Do not claim that paired nodes, "
        "companion apps, or execution environments are missing unless the exact curl commands "
        "below fail in exec.\n"
        "In this Gateway runtime, observe/move/done are plain HTTP endpoints that you call "
        "from the exec tool with curl; they are not native OpenClaw tool slots.\n"
        "Use these exact forms from exec:\n"
        "- observe: curl -sS http://host.docker.internal:18788/observe\n"
        "- move: curl -sS -X POST http://host.docker.internal:18788/move "
        '-H "Content-Type: application/json" '
        '-d \'{"direction":"MoveAhead","reason":"clear hallway continues"}\'\n'
        "- done: curl -sS -X POST http://host.docker.internal:18788/done "
        '-H "Content-Type: application/json" '
        '-d \'{"reason":"<short reason>"}\'\n'
        "Start by calling observe through exec before any analysis. Parse the JSON responses, "
        "then decide the next step. Default behavior is observe -> think -> move. You may take a "
        "short burst of repeated moves only when you have a concrete local reason such as a clear "
        "hallway, a safe backtrack, or following a human-directed maneuver; when you do, include "
        "a brief natural-language reason in the move payload.\n"
        "Do not detour through OpenClaw's generic image tool for observe frames unless you are "
        "truly blocked on the JSON response. If you absolutely must use the image tool, pass "
        "base64 data:image URLs directly or write files under the current workspace/media roots; "
        "do not use /tmp paths because the Gateway rejects them.\n"
        "Be agentic: choose the exploration strategy that fits the room, even if it departs from "
        "a narrow implied checklist, but keep every choice grounded in what you actually "
        "observed. If a tool response includes human_message, acknowledge it, use the overhead "
        "map to address the request, and do not call done until you have taken at least one "
        "follow-up action after receiving the message. When you eventually call done, explicitly "
        "mention the human_message and what you did about it in the done reason.\n\n"
        "Avoid ending early just because the room looks quiet. Prefer a sustained exploration "
        "within the move budget. Call done only when you are stuck, the budget is nearly "
        "exhausted, or you have clearly completed what seems worthwhile from the current run."
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


def _metrics_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _run_capture(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return (
        int(getattr(result, "returncode", 1)),
        str(getattr(result, "stdout", "")),
        str(getattr(result, "stderr", "")),
    )


def _write_capture(path: Path, cmd: list[str]) -> bool:
    returncode, stdout, stderr = _run_capture(cmd)
    text = stdout if stdout.strip() else stderr
    if not text:
        text = f"<no output> (returncode={returncode})\n"
    path.write_text(text, encoding="utf-8")
    return returncode == 0


def _capture_gateway_diagnostics(
    *,
    output_dir: Path,
    container_name: str,
    agent_id: int,
) -> dict[str, Any]:
    diagnostics_dir = output_dir / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    inspect_path = diagnostics_dir / "gateway.inspect.json"
    if _write_capture(inspect_path, ["docker", "inspect", container_name]):
        files["gateway_inspect"] = inspect_path.name

    outer_log_path = diagnostics_dir / "gateway.docker.log"
    if _write_capture(outer_log_path, ["docker", "logs", "--tail", "200", container_name]):
        files["gateway_docker_log"] = outer_log_path.name

    inner_log_path = diagnostics_dir / "gateway.inner.log"
    inner_log_cmd = [
        "docker",
        "exec",
        container_name,
        "sh",
        "-lc",
        "LATEST=$(ls -1 /tmp/openclaw/openclaw-*.log 2>/dev/null | tail -n 1); "
        'if [ -n "$LATEST" ]; then tail -n 200 "$LATEST"; else echo "<no inner log>"; fi',
    ]
    if _write_capture(inner_log_path, inner_log_cmd):
        files["gateway_inner_log"] = inner_log_path.name

    workspace_state_path = diagnostics_dir / "gateway.workspace-state.txt"
    workspace_state_cmd = [
        "docker",
        "exec",
        container_name,
        "sh",
        "-lc",
        f"ls -R /home/node/.openclaw/workspaces/agent-{agent_id}/state 2>&1 || true",
    ]
    _write_capture(workspace_state_path, workspace_state_cmd)
    files["gateway_workspace_state"] = workspace_state_path.name

    return files


def _start_watchdog_thread(
    sim_server: SimHTTPServer,
    stop_event: threading.Event,
    *,
    interval_s: float = _WATCHDOG_INTERVAL_S,
) -> threading.Thread:
    def _watchdog() -> None:
        while not stop_event.wait(interval_s):
            sim_server.write_runtime_event("watchdog", metrics=sim_server.snapshot_metrics())

    thread = threading.Thread(target=_watchdog, daemon=True, name="autonomous-watchdog")
    thread.start()
    return thread


def run_autonomous_navigation(
    *,
    scene: str,
    max_moves: int,
    wall_budget: float,
    output_dir: Path,
    skip_bootstrap: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    engine: MultiAgentEngine | None = None
    sim_server: SimHTTPServer | None = None
    bridge: OpenClawBridge | None = None
    stdin_thread: threading.Thread | None = None
    watchdog_thread: threading.Thread | None = None
    stdin_stop = threading.Event()
    watchdog_stop = threading.Event()
    gateway_started = False
    run_result: RunResult | None = None
    diagnostics_files: dict[str, str] = {}
    gateway_container = os.environ.get("OPENCLAW_GATEWAY_CONTAINER", _DEFAULT_GATEWAY_CONTAINER)

    try:
        log.info("starting MultiAgentEngine(scene=%s, agent_count=1)", scene)
        engine = MultiAgentEngine(scene=scene, agent_count=1)

        sim_server = SimHTTPServer(engine, agent_id=0, run_dir=output_dir, port=18788)
        sim_server.write_runtime_event(
            "run_started",
            scene=scene,
            max_moves=max_moves,
            wall_budget_s=wall_budget,
            skip_bootstrap=skip_bootstrap,
        )
        log.info(
            "SimHTTPServer listening on %s:%s (Gateway route http://host.docker.internal:%s)",
            sim_server.host,
            sim_server.port,
            sim_server.port,
        )
        watchdog_thread = _start_watchdog_thread(sim_server, watchdog_stop)

        if skip_bootstrap:
            token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "").strip()
            if not token:
                raise RuntimeError(
                    "--skip-bootstrap requires OPENCLAW_GATEWAY_TOKEN for the running Gateway"
                )
            sim_server.write_runtime_event("gateway_bootstrap_skipped", container=gateway_container)
            log.info("reusing existing Gateway from OPENCLAW_GATEWAY_TOKEN")
        else:
            env = dict(os.environ)
            env["TIMEOUT_SECONDS"] = str(int(wall_budget + 60))
            env["SIM_SERVER_URL"] = "http://host.docker.internal:18788"
            sim_server.write_runtime_event(
                "gateway_bootstrap_begin",
                timeout_seconds=env["TIMEOUT_SECONDS"],
                container=gateway_container,
            )
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
            sim_server.write_runtime_event("gateway_bootstrap_done", container=gateway_container)
            log.info("Gateway started, bearer token captured")

        stdin_thread = _start_stdin_thread(sim_server, stdin_stop)

        bridge = OpenClawBridge(
            gateway_url="http://127.0.0.1:18789",
            token=token,
        )
        kickoff_prompt = _kickoff_prompt(max_moves)
        sim_server.write_runtime_event(
            "start_run_begin",
            prompt_chars=len(kickoff_prompt),
            prompt_lines=kickoff_prompt.count("\n") + 1,
            bridge_timeout_s=wall_budget + 60.0,
        )
        run_started = time.monotonic()
        try:
            run_result = bridge.start_run(
                agent_id=0,
                prompt=kickoff_prompt,
                wall_budget_s=wall_budget,
                done_event=sim_server.done_event,
            )
        except OpenClawUnavailable as exc:
            run_result = RunResult(
                final_message=str(exc),
                wallclock_s=round(time.monotonic() - run_started, 3),
                terminated_by="error",
            )
        bridge_metrics = _metrics_dict(bridge.get_last_run_metrics())
        sim_server.write_runtime_event(
            "start_run_end",
            terminated_by=run_result.terminated_by,
            wallclock_s=run_result.wallclock_s,
            bridge_metrics=bridge_metrics,
            sim_server_metrics=sim_server.snapshot_metrics(),
        )
        log.info(
            "start_run returned: terminated_by=%s wallclock=%.1fs",
            run_result.terminated_by,
            run_result.wallclock_s,
        )

        _write_json(output_dir / "start_run_metrics.json", bridge_metrics)

        if run_result.terminated_by in {"wall_clock", "error"}:
            diagnostics_files = _capture_gateway_diagnostics(
                output_dir=output_dir,
                container_name=gateway_container,
                agent_id=0,
            )

        _write_json(
            output_dir / "run_result.json",
            {
                "terminated_by": run_result.terminated_by,
                "wallclock_s": run_result.wallclock_s,
                "final_message": run_result.final_message,
                "bridge_metrics": bridge_metrics,
                "sim_server_metrics": sim_server.snapshot_metrics(),
                "diagnostics_files": diagnostics_files,
            },
        )

        log.info("rendering replay.gif + report.html")
        subprocess.run(
            [sys.executable, "scripts/render_autonomous_replay.py", "--run-dir", str(output_dir)],
            check=False,
        )
        log.info("artifacts at %s", output_dir)
    finally:
        watchdog_stop.set()
        if watchdog_thread is not None:
            log.info("teardown: stopping watchdog thread")
            watchdog_thread.join(timeout=0.2)
        if sim_server is not None:
            log.info("teardown: stopping sim server")
            sim_server.close()
        if gateway_started:
            log.info("teardown: removing openclaw-gateway container")
            subprocess.run(
                ["docker", "rm", "-f", gateway_container],
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
        skip_bootstrap=args.skip_bootstrap,
    )
    print(f"terminated_by: {result['terminated_by']}")
    print(f"wallclock_s: {result['wallclock_s']:.1f}")
    print(f"artifacts at {result['output_dir']}")


if __name__ == "__main__":
    main()
