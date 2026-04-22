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
from roboclaws.core.views import VIEW_VARIANTS
from roboclaws.openclaw.bridge import OpenClawBridge, OpenClawUnavailable, RunResult
from roboclaws.openclaw.mcp_server import RoboclawsMCPServer, make_roboclaws_mcp

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
        "--views",
        choices=VIEW_VARIANTS,
        default="map-v2+chase",
        help="Prompt image bundle variant returned by roboclaws__observe.",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Reuse an already-running Gateway instead of bootstrapping/removing the container.",
    )
    parser.add_argument(
        "--transcript-mode",
        choices=("stream", "terminal-body"),
        default=None,
        help="Optional override for transcript capture mode; omit to use the bridge default.",
    )
    return parser.parse_args(argv)


def _default_output_dir() -> Path:
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return Path(f"output/openclaw-autonomous/{stamp}")


def _kickoff_prompt(max_moves: int) -> str:
    # MCP-era kickoff (phase 02.6 D-07): delegate the loop mechanics to
    # skills/ai2thor-navigator/SKILL.md and name the three roboclaws MCP
    # tools directly. Under profile: minimal the agent has exactly
    # session_status + roboclaws__{observe,move,done} — no fallbacks to
    # mention, no curl/exec/image escape hatches to warn against.
    return (
        "You are navigating an indoor room. Read skills/ai2thor-navigator/SKILL.md "
        "and follow it exactly.\n"
        "Use the observe / move / done tools exposed by the `roboclaws` MCP server "
        "(roboclaws__observe, roboclaws__move, roboclaws__done). Call "
        "roboclaws__observe before any other action.\n"
        f"Budget: up to {max_moves} physical moves plus the wall-clock set by the "
        "caller; pace yourself against both.\n"
        "Use observe.state.view_variant and observe.state.image_labels to interpret "
        "the returned image bundle before deciding.\n"
        "Loop observe -> think -> move until you are stuck, the budget is nearly "
        "exhausted, or you have a concrete reason to stop; then call "
        "roboclaws__done with a short reason.\n"
        "If an observe or move response includes a non-null human_message, "
        "acknowledge it in your next move.reason and take at least one follow-up "
        "action before calling done."
    )


def _start_stdin_thread(
    mcp_server: RoboclawsMCPServer,
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
                mcp_server.enqueue_human_message(message)
                log.info("queued human message: %s", message[:80])

    thread = threading.Thread(target=_stdin_pump, daemon=True, name="stdin-pump")
    thread.start()
    log.info("stdin reader thread started (type a line then Enter to interject)")
    return thread


def _metrics_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


_DIAGNOSTIC_CAPTURE_TIMEOUT_S = 15.0


def _run_capture(
    cmd: list[str],
    *,
    timeout: float = _DIAGNOSTIC_CAPTURE_TIMEOUT_S,
) -> tuple[int, str, str]:
    """Run `cmd` capturing stdout/stderr, with a hard wall-clock cap.

    WR-02 fix: diagnostics fire on the wall_clock / error termination paths
    (see `_capture_gateway_diagnostics`). If the Gateway container is wedged
    — often the reason we got there — an un-timed `docker exec` would hang
    indefinitely during teardown, turning a budget-enforced termination into
    an unbounded stall. A 15s cap per call bounds worst-case cleanup to
    ~1 minute across the four diagnostic commands.
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raw_stdout = exc.stdout or ""
        raw_stderr = exc.stderr or ""
        stdout = (
            raw_stdout if isinstance(raw_stdout, str) else raw_stdout.decode("utf-8", "replace")
        )
        stderr_base = (
            raw_stderr if isinstance(raw_stderr, str) else raw_stderr.decode("utf-8", "replace")
        )
        stderr = stderr_base + f"\n<diagnostic command timed out after {timeout:.0f}s>"
        # 124 matches coreutils `timeout(1)` so operators grepping logs
        # recognize the failure mode.
        return (124, stdout, stderr)
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
    mcp_server: RoboclawsMCPServer,
    stop_event: threading.Event,
    *,
    interval_s: float = _WATCHDOG_INTERVAL_S,
) -> threading.Thread:
    def _watchdog() -> None:
        while not stop_event.wait(interval_s):
            mcp_server.write_runtime_event("watchdog", metrics=mcp_server.snapshot_metrics())

    thread = threading.Thread(target=_watchdog, daemon=True, name="autonomous-watchdog")
    thread.start()
    return thread


def run_autonomous_navigation(
    *,
    scene: str,
    max_moves: int,
    wall_budget: float,
    output_dir: Path,
    views: str = "map-v2+chase",
    skip_bootstrap: bool = False,
    transcript_mode: str | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    engine: MultiAgentEngine | None = None
    mcp_server: RoboclawsMCPServer | None = None
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

        mcp_server = make_roboclaws_mcp(
            engine,
            agent_id=0,
            run_dir=output_dir,
            # Linux Docker-bridge reality check (probe gate 02.6-06, Rule 1 fix):
            # plan 01's threat model T-02.6-01 assumed 127.0.0.1 was reachable via
            # `host.docker.internal` → host-gateway on Linux. That's false on
            # 6.x kernels with Docker 29.x — the bridge routes to 172.17.0.1,
            # which cannot reach host loopback. `0.0.0.0` matches the spike +
            # Phase 2.5 retros + docs/openclaw-local.md. LAN-exposure risk is
            # accepted: single-operator local-dev on a trusted workstation.
            host="0.0.0.0",
            port=18788,
            view_variant=views,
        )
        mcp_server.run_in_thread()
        # Runtime-event key 'sim_server_metrics' is frozen for schema compat with
        # tests/test_openclaw_nav_autonomous.py and scripts/render_autonomous_replay.py.
        # The underlying server is now MCP, not HTTP.
        mcp_server.write_runtime_event(
            "run_started",
            scene=scene,
            max_moves=max_moves,
            wall_budget_s=wall_budget,
            view_variant=views,
            skip_bootstrap=skip_bootstrap,
        )
        log.info(
            "Roboclaws MCP server listening on %s:%s "
            "(Gateway route http://host.docker.internal:%s/mcp)",
            mcp_server.host,
            mcp_server.port,
            mcp_server.port,
        )
        watchdog_thread = _start_watchdog_thread(mcp_server, watchdog_stop)

        if skip_bootstrap:
            token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "").strip()
            if not token:
                raise RuntimeError(
                    "--skip-bootstrap requires OPENCLAW_GATEWAY_TOKEN for the running Gateway"
                )
            mcp_server.write_runtime_event("gateway_bootstrap_skipped", container=gateway_container)
            log.info("reusing existing Gateway from OPENCLAW_GATEWAY_TOKEN")
        else:
            env = dict(os.environ)
            env["TIMEOUT_SECONDS"] = str(int(wall_budget + 60))
            # Honor operator-supplied ROBOCLAWS_MCP_URL (e.g. local-probe runs) by
            # using setdefault; fall back to the container->host loopback URL. This
            # is what plan 02 Task 3's test_mcp_url_env_override_honored exercises.
            env.setdefault("ROBOCLAWS_MCP_URL", "http://host.docker.internal:18788/mcp")
            mcp_server.write_runtime_event(
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
            mcp_server.write_runtime_event("gateway_bootstrap_done", container=gateway_container)
            log.info("Gateway started, bearer token captured")

        stdin_thread = _start_stdin_thread(mcp_server, stdin_stop)

        bridge_kwargs: dict[str, Any] = {
            "gateway_url": "http://127.0.0.1:18789",
            "token": token,
        }
        if transcript_mode is not None:
            bridge_kwargs["transcript_mode"] = transcript_mode
        bridge = OpenClawBridge(**bridge_kwargs)
        kickoff_prompt = _kickoff_prompt(max_moves)
        mcp_server.write_runtime_event(
            "start_run_begin",
            prompt_chars=len(kickoff_prompt),
            prompt_lines=kickoff_prompt.count("\n") + 1,
            bridge_timeout_s=wall_budget + 60.0,
            transcript_mode=transcript_mode,
        )
        run_started = time.monotonic()
        try:
            run_result = bridge.start_run(
                agent_id=0,
                prompt=kickoff_prompt,
                wall_budget_s=wall_budget,
                done_event=mcp_server.done_event,
            )
        except OpenClawUnavailable as exc:
            run_result = RunResult(
                final_message=str(exc),
                wallclock_s=round(time.monotonic() - run_started, 3),
                terminated_by="error",
                transcript_capture_mode=transcript_mode or "terminal-body",
            )
        for entry in run_result.transcript_messages:
            mcp_server.write_trace_event(
                tool="assistant",
                event="assistant_transcript",
                source=entry.source,
                content=entry.content,
                message_index=entry.message_index,
                chunk_index=entry.chunk_index,
                is_final=entry.is_final,
                wallclock_elapsed=entry.wallclock_s,
            )
        bridge_metrics = _metrics_dict(bridge.get_last_run_metrics())
        mcp_server.write_runtime_event(
            "start_run_end",
            terminated_by=run_result.terminated_by,
            wallclock_s=run_result.wallclock_s,
            bridge_metrics=bridge_metrics,
            sim_server_metrics=mcp_server.snapshot_metrics(),
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
                "view_variant": views,
                "bridge_metrics": bridge_metrics,
                # Key 'sim_server_metrics' kept verbatim for report.html +
                # render_autonomous_replay.py schema compat; backing data
                # comes from mcp_server.snapshot_metrics() (same 8-key contract).
                "sim_server_metrics": mcp_server.snapshot_metrics(),
                "transcript_capture_mode": run_result.transcript_capture_mode,
                "transcript_source": run_result.transcript_source,
                "transcript_messages": [
                    entry.to_dict() for entry in run_result.transcript_messages
                ],
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
        if mcp_server is not None:
            log.info("teardown: stopping MCP server")
            mcp_server.close()
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
        views=args.views,
        skip_bootstrap=args.skip_bootstrap,
        transcript_mode=args.transcript_mode,
    )
    print(f"terminated_by: {result['terminated_by']}")
    print(f"wallclock_s: {result['wallclock_s']:.1f}")
    print(f"artifacts at {result['output_dir']}")


if __name__ == "__main__":
    main()
