#!/usr/bin/env python3
"""Hold an AI2-THOR engine + Roboclaws MCP server open for interactive use.

Pairs with the OpenClaw Gateway's built-in Control UI (served at the
Gateway's root URL, e.g. ``http://127.0.0.1:18789/``). The UI ships a full
chat tab with agent selection and tool-call rendering; this script is the
"everything it needs on the host side" — no autonomous driver loop, no
``/v1/chat/completions`` kickoff, no bridge.

Typical flow::

    python examples/openclaw_interactive.py
    # → prints Control UI URL + bearer token + agent name
    # → open the URL in your browser, paste the token, pick agent-0,
    #   and chat. Your messages drive observe/move/done tool calls on the
    #   MCP server this script holds open.
    # → Ctrl-C to shut everything down.

Env overrides mirror ``examples/openclaw_nav_autonomous.py``:

* ``OPENCLAW_GATEWAY_TOKEN`` + ``--skip-bootstrap`` — reuse an existing
  Gateway instead of bootstrapping one (bootstrap force-recreates the
  container).
* ``OPENCLAW_GATEWAY_CONTAINER`` — override the container name used for
  teardown.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.views import VIEW_VARIANTS
from roboclaws.openclaw.mcp_server import RoboclawsMCPServer, make_roboclaws_mcp

log = logging.getLogger("openclaw-interactive")
_DEFAULT_GATEWAY_CONTAINER = "openclaw-gateway"
_DEFAULT_GATEWAY_URL = "http://127.0.0.1:18789"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Boot AI2-THOR + Roboclaws MCP + Gateway, then hold "
        "everything open so you can chat with the agent via the OpenClaw "
        "Control UI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--scene", default="FloorPlan201")
    parser.add_argument(
        "--views",
        choices=VIEW_VARIANTS,
        default="map-v2+chase",
        help="Prompt image bundle variant returned by roboclaws__observe.",
    )
    parser.add_argument(
        "--agent-id",
        type=int,
        default=0,
        help="AI2-THOR agent index bound to the MCP tools (matches Gateway agent name agent-<id>).",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Reuse an already-running Gateway. Requires OPENCLAW_GATEWAY_TOKEN.",
    )
    parser.add_argument(
        "--keep-gateway",
        action="store_true",
        help="Don't tear down the Gateway on Ctrl-C (useful for iterating).",
    )
    return parser.parse_args(argv)


def _default_output_dir() -> Path:
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return Path(f"output/openclaw-interactive/{stamp}")


def _bootstrap_gateway(agent_id: int) -> str:
    env = dict(os.environ)
    env.setdefault("AGENTS", str(max(1, agent_id + 1)))
    env.setdefault("ROBOCLAWS_MCP_URL", "http://host.docker.internal:18788/mcp")
    env.setdefault("TIMEOUT_SECONDS", "600")
    log.info("bootstrapping Gateway (TIMEOUT_SECONDS=%s)", env["TIMEOUT_SECONDS"])
    result = subprocess.run(
        ["./scripts/openclaw-bootstrap.sh"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return result.stdout.strip()


def _existing_gateway_token(container: str) -> str | None:
    try:
        out = subprocess.run(
            [
                "docker",
                "exec",
                container,
                "sh",
                "-lc",
                'grep -oE \'"token" *: *"[^"]+"\' /home/node/.openclaw/openclaw.json '
                '| head -n1 | sed -E \'s/.*"token" *: *"([^"]+)".*/\\1/\'',
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    token = out.stdout.strip()
    return token or None


def _print_banner(*, url: str, agent_name: str, token: str, output_dir: Path) -> None:
    bar = "=" * 72
    print()
    print(bar)
    print("  OpenClaw interactive — ready. Open the Control UI in a browser:")
    print()
    print(f"    URL   : {url}")
    print(f"    Token : {token}")
    print(f"    Agent : {agent_name}")
    print()
    print("  Tips:")
    print("    - An AI2-THOR Unity window should be open on your desktop —")
    print("      watch the robot move there as you chat.")
    print("    - Paste the bearer token on the Overview tab to connect.")
    print("    - Switch to the Chat tab, pick the agent above, and talk.")
    print("    - Ask the agent to 'show me what you see' to trigger the")
    print("      roboclaws__snapshot tool — it writes PNGs to the workspace")
    print("      and replies with MEDIA: lines that render inline.")
    print("    - Typing in this terminal queues a human_message that the")
    print("      agent's next observe/move call will see (bounded deque, 10).")
    print(f"    - Trace: {output_dir / 'trace.jsonl'}")
    print("    - For a live mirror of the chat-tab transcript, run in another")
    print("      terminal:    make chat-tail")
    print("    - Ctrl-C to shut down AI2-THOR + the MCP server.")
    print(bar)
    print(flush=True)


def _start_stdin_thread(
    mcp_server: RoboclawsMCPServer,
    stop_event: threading.Event,
) -> threading.Thread | None:
    if not sys.stdin.isatty():
        return None

    def _pump() -> None:
        while not stop_event.is_set():
            line = sys.stdin.readline()
            if not line:
                break
            message = line.strip()
            if message:
                mcp_server.enqueue_human_message(message)
                log.info("queued human message (%d chars)", len(message))

    thread = threading.Thread(target=_pump, daemon=True, name="stdin-pump")
    thread.start()
    return thread


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    output_dir = args.output_dir or _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    engine: MultiAgentEngine | None = None
    mcp_server: RoboclawsMCPServer | None = None
    stdin_stop = threading.Event()
    gateway_started_by_us = False
    gateway_container = os.environ.get("OPENCLAW_GATEWAY_CONTAINER", _DEFAULT_GATEWAY_CONTAINER)
    shutdown_event = threading.Event()

    def _handle_signal(signum: int, _frame: object) -> None:
        log.info("received signal %s; shutting down", signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        log.info(
            "starting MultiAgentEngine(scene=%s, agent_count=%d)", args.scene, args.agent_id + 1
        )
        engine = MultiAgentEngine(scene=args.scene, agent_count=args.agent_id + 1)

        # Snapshots dir: host-side path the `snapshot` MCP tool writes PNGs to.
        # Bootstrap bind-mounts the same absolute path at
        # `/home/node/.openclaw/workspaces/<agent>/snapshots` inside the
        # container, so the agent can reference `./snapshots/<file>.png` in a
        # MEDIA: directive. Exporting the env here lets _bootstrap_gateway
        # pass it through to the openclaw-bootstrap.sh subprocess.
        snapshots_dir = Path(
            os.environ.get("ROBOCLAWS_SNAPSHOTS_DIR", str(output_dir / "snapshots"))
        ).resolve()
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        os.environ["ROBOCLAWS_SNAPSHOTS_DIR"] = str(snapshots_dir)

        # Linux Docker-bridge reality: 0.0.0.0 is what Phase 2.6 landed on for
        # host.docker.internal routing. See openclaw_nav_autonomous.py for the
        # full rationale (threat model + retro).
        mcp_server = make_roboclaws_mcp(
            engine,
            agent_id=args.agent_id,
            run_dir=output_dir,
            host="0.0.0.0",
            port=18788,
            view_variant=args.views,
            snapshots_dir=snapshots_dir,
        )
        mcp_server.run_in_thread()
        mcp_server.write_runtime_event(
            "interactive_started",
            scene=args.scene,
            agent_id=args.agent_id,
            view_variant=args.views,
            skip_bootstrap=args.skip_bootstrap,
        )
        log.info(
            "MCP server listening on %s:%s → Gateway reaches it via "
            "http://host.docker.internal:%s/mcp",
            mcp_server.host,
            mcp_server.port,
            mcp_server.port,
        )

        if args.skip_bootstrap:
            token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "").strip()
            if not token:
                token = _existing_gateway_token(gateway_container) or ""
            if not token:
                raise RuntimeError(
                    "--skip-bootstrap but no token: set OPENCLAW_GATEWAY_TOKEN "
                    f"or ensure container '{gateway_container}' is running."
                )
            log.info("reusing existing Gateway '%s'", gateway_container)
        else:
            token = _bootstrap_gateway(args.agent_id)
            gateway_started_by_us = True
            log.info("Gateway bootstrapped, bearer token captured")

        _start_stdin_thread(mcp_server, stdin_stop)
        _print_banner(
            url=_DEFAULT_GATEWAY_URL,
            agent_name=f"agent-{args.agent_id}",
            token=token,
            output_dir=output_dir,
        )

        # Block until Ctrl-C / SIGTERM, OR the agent flips done via the
        # roboclaws__done MCP tool (nice: lets an agent hang up cleanly).
        while not shutdown_event.is_set() and not mcp_server.done_event.is_set():
            time.sleep(0.5)

        if mcp_server.done_event.is_set():
            log.info("agent called roboclaws__done; holding for 2s then exiting")
            time.sleep(2.0)

    except Exception as exc:
        log.exception("interactive session failed: %s", exc)
        return 1
    finally:
        stdin_stop.set()
        if mcp_server is not None:
            try:
                mcp_server.write_runtime_event("interactive_stopped")
            except Exception:
                pass
            mcp_server.close()
        if engine is not None:
            try:
                engine.close()
            except Exception:
                log.exception("engine.close() failed")
        if gateway_started_by_us and not args.keep_gateway:
            log.info("stopping Gateway container '%s'", gateway_container)
            subprocess.run(
                ["docker", "rm", "-f", gateway_container],
                check=False,
                capture_output=True,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
