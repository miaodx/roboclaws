#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.navigation_lifecycle import NavigationRunLifecycle
from roboclaws.core.run_artifacts import build_run_result
from roboclaws.mcp.server import RoboclawsMCPServer, make_roboclaws_mcp
from roboclaws.openclaw.bridge import OpenClawBridge, OpenClawUnavailable, RunResult

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
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M")
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
        "Use observe.state.view_variant and image_labels to interpret the observe "
        "result; the image content blocks are the raw camera views.\n"
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
    docker_exec = ["docker", "exec", container_name, "sh", "-lc"]

    capture_specs = [
        ("gateway_inspect", "gateway.inspect.json", ["docker", "inspect", container_name], True),
        (
            "gateway_docker_log",
            "gateway.docker.log",
            ["docker", "logs", "--tail", "200", container_name],
            True,
        ),
        (
            "gateway_inner_log",
            "gateway.inner.log",
            docker_exec
            + [
                "LATEST=$(ls -1 /tmp/openclaw/openclaw-*.log 2>/dev/null | tail -n 1); "
                'if [ -n "$LATEST" ]; then tail -n 200 "$LATEST"; else echo "<no inner log>"; fi'
            ],
            True,
        ),
        (
            "gateway_workspace_state",
            "gateway.workspace-state.txt",
            docker_exec
            + [f"ls -R /home/node/.openclaw/workspaces/agent-{agent_id}/state 2>&1 || true"],
            False,
        ),
    ]
    for key, filename, cmd, require_success in capture_specs:
        path = diagnostics_dir / filename
        if _write_capture(path, cmd) or not require_success:
            files[key] = path.name

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
    skip_bootstrap: bool = False,
    kickoff_prompt_builder: Callable[[int], str] | None = None,
    allow_privileged_tools: bool = False,
) -> dict[str, Any]:
    """Run the autonomous loop end-to-end.

    ``kickoff_prompt_builder`` defaults to :func:`_kickoff_prompt` (generic
    nav). Pass an alternate ``Callable[[int], str]`` (max_moves -> prompt)
    to swap in a task-specific kickoff (e.g. photo-task) without forking
    this module's bootstrap / engine / MCP / bridge wiring.
    """
    builder: Callable[[int], str] = kickoff_prompt_builder or _kickoff_prompt
    lifecycle = NavigationRunLifecycle(
        scene=scene,
        output_dir=output_dir,
        # Linux Docker bridge requires binding the MCP server to all interfaces;
        # the Gateway reaches it via host.docker.internal.
        host="0.0.0.0",
        port=18788,
        agent_id=0,
    )
    lifecycle.prepare_output_dir()

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
    model_name = os.environ.get("MODEL")

    try:
        log.info("starting MultiAgentEngine(scene=%s, agent_count=1)", scene)
        engine = MultiAgentEngine(scene=scene, agent_count=1)

        mcp_server = make_roboclaws_mcp(
            engine,
            agent_id=lifecycle.agent_id,
            run_dir=lifecycle.output_dir,
            host=lifecycle.host,
            port=lifecycle.port,
            model_name=model_name,
            allow_privileged_tools=allow_privileged_tools,
        )
        mcp_server.run_in_thread()
        # 'sim_server_metrics' stays frozen for report/tests schema compat.
        mcp_server.write_runtime_event(
            "run_started",
            scene=scene,
            max_moves=max_moves,
            wall_budget_s=wall_budget,
            skip_bootstrap=skip_bootstrap,
            model=model_name,
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
            env.setdefault("READY_TIMEOUT", "180")
            # Honor operator-supplied ROBOCLAWS_MCP_URL (e.g. local-probe runs) by
            # using setdefault; fall back to the container->host loopback URL. This
            # is what plan 02 Task 3's test_mcp_url_env_override_honored exercises.
            env.setdefault("ROBOCLAWS_MCP_URL", f"http://host.docker.internal:{lifecycle.port}/mcp")
            mcp_server.write_runtime_event(
                "gateway_bootstrap_begin",
                timeout_seconds=env["TIMEOUT_SECONDS"],
                container=gateway_container,
            )
            log.info("bootstrapping Gateway (TIMEOUT_SECONDS=%s)", env["TIMEOUT_SECONDS"])
            bootstrap = subprocess.run(
                ["./scripts/openclaw/openclaw-bootstrap.sh"],
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

        bridge = OpenClawBridge(gateway_url="http://127.0.0.1:18789", token=token)
        kickoff_prompt = builder(max_moves)
        mcp_server.write_runtime_event(
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
            )
        except OpenClawUnavailable as exc:
            run_result = RunResult(
                final_message=str(exc),
                wallclock_s=round(time.monotonic() - run_started, 3),
                terminated_by="error",
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
        sim_server_metrics = mcp_server.snapshot_metrics()
        mcp_server.write_runtime_event(
            "start_run_end",
            terminated_by=run_result.terminated_by,
            wallclock_s=run_result.wallclock_s,
            bridge_metrics=bridge_metrics,
            sim_server_metrics=sim_server_metrics,
        )
        log.info(
            "start_run returned: terminated_by=%s wallclock=%.1fs",
            run_result.terminated_by,
            run_result.wallclock_s,
        )

        lifecycle.write_json("start_run_metrics.json", bridge_metrics)

        if run_result.terminated_by in {"wall_clock", "error"}:
            diagnostics_files = _capture_gateway_diagnostics(
                output_dir=lifecycle.output_dir,
                container_name=gateway_container,
                agent_id=lifecycle.agent_id,
            )

        lifecycle.write_json(
            "run_result.json",
            build_run_result(
                terminated_by=run_result.terminated_by,
                wallclock_s=run_result.wallclock_s,
                final_message=run_result.final_message,
                view_variant="map-v2+chase",
                model=model_name,
                bridge_metrics=bridge_metrics,
                # Key kept verbatim for report/schema compat; backing data is MCP metrics.
                sim_server_metrics=sim_server_metrics,
                transcript_source=run_result.transcript_source,
                transcript_messages=[entry.to_dict() for entry in run_result.transcript_messages],
                diagnostics_files=diagnostics_files,
            ),
        )

        log.info("rendering report.html")
        subprocess.run(
            [
                sys.executable,
                "scripts/reports/render_autonomous_replay.py",
                "--run-dir",
                str(lifecycle.output_dir),
            ],
            check=False,
        )
        log.info("artifacts at %s", lifecycle.output_dir)
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
        "output_dir": str(lifecycle.output_dir),
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
