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

CLI flags (all optional)::

    --provider {mimo,kimi,nvidia}   Gateway provider          (default: mimo)
    --model TEXT                    Model ID                  (default: provider default)
    --image-model TEXT              Bridge model for text-only mains
    --observe-mode TEXT             'text-bridge' for split-model setups
    --plugin                        Anthropic/plugin API path
    --clean                         Wipe Gateway config volume first
    --skip-bootstrap                Reuse an already-running Gateway
    --keep-gateway                  Don't tear down on Ctrl-C

    python examples/openclaw_interactive.py --help   # full flag list
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import quote

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.openclaw.mcp_server import RoboclawsMCPServer, make_roboclaws_mcp
from roboclaws.openclaw.reset_server import ResetServer
from roboclaws.openclaw.vision_bridge import observe_runtime_config

log = logging.getLogger("openclaw-interactive")
_DEFAULT_GATEWAY_CONTAINER = "openclaw-gateway"
_DEFAULT_GATEWAY_URL = "http://127.0.0.1:18789"
_DEFAULT_TAIL_HINT = "just chat::tail"
_DEFAULT_VIEWER_HINT = "just chat::view     → http://127.0.0.1:8787"


@dataclass
class Args:
    """Boot AI2-THOR + Roboclaws MCP + Gateway, then hold everything open for chat."""

    # Engine
    scene: str = "FloorPlan201"
    """AI2-THOR floor plan scene."""

    agent_id: int = 0
    """AI2-THOR agent index bound to MCP tools (matches Gateway agent-<id>)."""

    output_dir: Path | None = None
    """Output directory for trace.jsonl and snapshots. Defaults to output/openclaw-interactive/<stamp>."""  # noqa: E501

    # Provider / model
    provider: Literal["mimo", "kimi", "nvidia"] = "mimo"
    """Gateway provider."""

    model: str | None = None
    """Gateway model ID (e.g. mimo_openai/mimo-v2-omni). Uses provider default if omitted."""

    image_model: str | None = None
    """Bridge model for text-only main models (e.g. mimo_openai/mimo-v2-omni)."""

    observe_mode: str | None = None
    """Observe delivery mode. Use 'text-bridge' for split-model setups."""

    plugin: bool = False
    """Use Anthropic/plugin API path (sets KIMI_PROVIDER_MODE=plugin, MIMO_PROVIDER_MODE=anthropic)."""  # noqa: E501

    # Session management
    clean: bool = False
    """Wipe Gateway config volume before bootstrapping (clears chat session history)."""

    volume: str = "openclaw-gateway-config"
    """Docker volume name for Gateway config (used with --clean)."""

    # Gateway lifecycle
    skip_bootstrap: bool = False
    """Reuse an already-running Gateway. Requires OPENCLAW_GATEWAY_TOKEN env var."""

    keep_gateway: bool = False
    """Don't tear down the Gateway container on Ctrl-C."""


def _parse_args(argv: list[str] | None = None) -> Args:
    return tyro.cli(Args, args=argv)


def _default_output_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M")
    return Path(f"output/openclaw-interactive/{stamp}")


def _wipe_volume(volume: str) -> None:
    log.info("wiping Gateway config volume '%s' (--clean)", volume)
    subprocess.run(["docker", "volume", "rm", volume], check=False, capture_output=True)


def _bootstrap_gateway(agent_id: int, extra_env: dict[str, str] | None = None) -> str:
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    env.setdefault("AGENTS", str(max(1, agent_id + 1)))
    env.setdefault("ROBOCLAWS_MCP_URL", "http://host.docker.internal:18788/mcp")
    env.setdefault("TIMEOUT_SECONDS", "7200")
    env.setdefault("READY_TIMEOUT", "180")
    log.info(
        "bootstrapping Gateway (TIMEOUT_SECONDS=%s READY_TIMEOUT=%s)",
        env["TIMEOUT_SECONDS"],
        env["READY_TIMEOUT"],
    )
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


def _print_banner(
    *,
    url: str,
    agent_name: str,
    token: str,
    output_dir: Path,
    runtime_config: dict[str, str | None],
    tail_hint: str = _DEFAULT_TAIL_HINT,
    viewer_hint: str = _DEFAULT_VIEWER_HINT,
    public_url: str | None = None,
) -> None:
    bar = "=" * 72
    print()
    print(bar)
    print("  OpenClaw interactive — ready. Open the Control UI in a browser:")
    print()
    print(f"    URL   : {url}")
    if public_url and public_url != url:
        print(f"    Appliance: {public_url}")
        if token:
            tokenized_url = f"{public_url.rstrip('/')}/#token={quote(token, safe='')}"
            print(f"    Appliance auth URL: {tokenized_url}")
    print(f"    Token : {token}")
    print(f"    Agent : {agent_name}")
    print(f"    Model : {runtime_config['model_name'] or '<gateway default>'}")
    print(f"    Image : {runtime_config['image_model'] or '<main-model>'}")
    print(f"    Observe: {runtime_config['observe_mode']} -> {runtime_config['observe_delivery']}")
    if runtime_config["vision_bridge_model"]:
        print(f"    Bridge: {runtime_config['vision_bridge_model']}")
    print()
    print("  Tips:")
    print("    - An AI2-THOR Unity window should be open on your desktop —")
    print("      watch the robot move there as you chat.")
    print("    - Paste the bearer token on the Overview tab to connect.")
    print("    - Switch to the Chat tab, pick the agent above, and talk.")
    print("    - Ask the agent to 'show me what you see' and it will call")
    print("      roboclaws__observe with a label — the labeled archive writes")
    print("      PNGs to the workspace and replies with MEDIA: lines that")
    print("      render inline in the chat tab.")
    print("    - Typing in this terminal queues a human_message that the")
    print("      agent's next observe/move call will see (bounded deque, 10).")
    print(f"    - Trace: {output_dir / 'trace.jsonl'}")
    print("    - For a live mirror of the chat-tab transcript, run in another")
    print(f"      terminal:    {tail_hint}")
    print("    - For live frame-by-frame snapshots (every step visible,")
    print("      bypassing the chat MEDIA final-message-only limit),")
    print(f"      open/run:    {viewer_hint}")
    print("    - Ctrl-C to shut down AI2-THOR + the MCP server.")
    print(bar)
    print(flush=True)


def _env_hint(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _start_stdin_thread(
    mcp_server: RoboclawsMCPServer,
    stop_event: threading.Event,
) -> None:
    if not sys.stdin.isatty():
        return

    def _pump() -> None:
        while not stop_event.is_set():
            line = sys.stdin.readline()
            if not line:
                break
            message = line.strip()
            if message:
                mcp_server.enqueue_human_message(message)
                log.info("queued human message (%d chars)", len(message))

    threading.Thread(target=_pump, daemon=True, name="stdin-pump").start()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    output_dir = args.output_dir or _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    engine: MultiAgentEngine | None = None
    mcp_server: RoboclawsMCPServer | None = None
    reset_server: ResetServer | None = None
    stdin_stop = threading.Event()
    gateway_started_by_us = False
    gateway_container = os.environ.get("OPENCLAW_GATEWAY_CONTAINER", _DEFAULT_GATEWAY_CONTAINER)
    shutdown_event = threading.Event()

    # Build bootstrap env from CLI args; CLI wins over inherited os.environ.
    bootstrap_env: dict[str, str] = {"PROVIDER": args.provider}
    bootstrap_env.update(
        {
            key: value
            for key, value in {
                "MODEL": args.model,
                "IMAGE_MODEL": args.image_model,
                "ROBOCLAWS_OBSERVE_MODE": args.observe_mode,
            }.items()
            if value
        }
    )
    if args.plugin:
        bootstrap_env["KIMI_PROVIDER_MODE"] = "plugin"
        bootstrap_env["MIMO_PROVIDER_MODE"] = "anthropic"

    runtime_config = observe_runtime_config(
        model_name=args.model or os.environ.get("MODEL"),
        image_model=args.image_model or os.environ.get("IMAGE_MODEL"),
        observe_mode=args.observe_mode or os.environ.get("ROBOCLAWS_OBSERVE_MODE"),
        vision_bridge_model=os.environ.get("ROBOCLAWS_VISION_BRIDGE_MODEL"),
    )

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

        # Snapshots dir — host/container path agreement.
        #
        # `ROBOCLAWS_SNAPSHOTS_DIR` is the **root**; bootstrap bind-mounts
        # `${root}/<agent>/` at `/home/node/.openclaw/workspaces/<agent>/snapshots`
        # inside the container (per-agent subdir so multi-agent runs don't
        # share an attachment pile). The MCP tool must write into the same
        # per-agent subdir, otherwise PNGs land at the root and the container
        # sees an empty bind mount.
        #
        # Bug history: the first cut passed snapshots_root as-is to the MCP
        # factory; tool wrote `./snapshots/foo.png` flat at the root while
        # the container's bind was `${root}/agent-0/`. Files existed on host
        # but `MEDIA:./snapshots/foo.png` came back "Attachment unavailable"
        # inside the chat because the container couldn't see them. Fix: the
        # MCP tool's snapshots_dir is the per-agent subdir.
        snapshots_root = Path(
            os.environ.get("ROBOCLAWS_SNAPSHOTS_DIR") or output_dir / "snapshots"
        ).resolve()
        snapshots_root.mkdir(parents=True, exist_ok=True)
        os.environ["ROBOCLAWS_SNAPSHOTS_DIR"] = str(snapshots_root)
        agent_snapshots_dir = snapshots_root / f"agent-{args.agent_id}"
        agent_snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Linux Docker-bridge reality: 0.0.0.0 is what Phase 2.6 landed on for
        # host.docker.internal routing. See openclaw_nav_autonomous.py for the
        # full rationale (threat model + retro).
        mcp_server = make_roboclaws_mcp(
            engine,
            agent_id=args.agent_id,
            run_dir=output_dir,
            host="0.0.0.0",
            port=18788,
            snapshots_dir=agent_snapshots_dir,
            model_name=runtime_config["model_name"],
            image_model=runtime_config["image_model"],
            observe_mode=runtime_config["observe_mode"],
            vision_bridge_model=runtime_config["vision_bridge_model"],
        )
        mcp_server.run_in_thread()
        # Loopback HTTP /reset endpoint — the appliance's nginx routes
        # /reset here so a browser tab can wipe scene + snapshots without
        # restarting the supervisord container. Best-effort: if the port is
        # busy (e.g. another runner already bound it), log and skip — the
        # interactive session itself doesn't need this to function.
        try:
            rs = ResetServer(mcp_server)
            rs.run_in_thread()
            log.info("reset endpoint listening on %s:%s", rs.host, rs.port)
            reset_server = rs
        except OSError as exc:
            log.warning("reset endpoint disabled (%s)", exc)
        mcp_server.write_runtime_event(
            "interactive_started",
            scene=args.scene,
            agent_id=args.agent_id,
            skip_bootstrap=args.skip_bootstrap,
            model=runtime_config["model_name"],
            image_model=runtime_config["image_model"],
            observe_mode=runtime_config["observe_mode"],
            observe_delivery=runtime_config["observe_delivery"],
            vision_bridge_model=runtime_config["vision_bridge_model"],
        )
        log.info(
            "MCP server listening on %s:%s → Gateway reaches it via "
            "http://host.docker.internal:%s/mcp",
            mcp_server.host,
            mcp_server.port,
            mcp_server.port,
        )

        if args.skip_bootstrap:
            token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "").strip() or (
                _existing_gateway_token(gateway_container) or ""
            )
            if not token:
                raise RuntimeError(
                    "--skip-bootstrap but no token: set OPENCLAW_GATEWAY_TOKEN "
                    f"or ensure container '{gateway_container}' is running."
                )
            log.info("reusing existing Gateway '%s'", gateway_container)
        else:
            if args.clean:
                _wipe_volume(args.volume)
            token = _bootstrap_gateway(args.agent_id, extra_env=bootstrap_env)
            gateway_started_by_us = True
            log.info("Gateway bootstrapped, bearer token captured")

        _start_stdin_thread(mcp_server, stdin_stop)
        _print_banner(
            url=_DEFAULT_GATEWAY_URL,
            agent_name=f"agent-{args.agent_id}",
            token=token,
            output_dir=output_dir,
            runtime_config=runtime_config,
            tail_hint=_env_hint("ROBOCLAWS_TAIL_HINT", _DEFAULT_TAIL_HINT),
            viewer_hint=_env_hint("ROBOCLAWS_VIEWER_HINT", _DEFAULT_VIEWER_HINT),
            public_url=_env_hint("ROBOCLAWS_PUBLIC_URL", ""),
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
        if reset_server is not None:
            try:
                reset_server.shutdown()
            except Exception:
                log.exception("reset_server.shutdown() failed")
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
