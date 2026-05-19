#!/usr/bin/env python3
"""Run the roboclaws MCP tools directly for Codex or Claude Code.

This path keeps AI2-THOR local and exposes the existing observe/move/done
FastMCP tools to a coding agent over streamable HTTP. It deliberately skips the
OpenClaw Gateway: start this script in one terminal, add the printed MCP server
to Codex or Claude Code in another terminal, then ask the coding agent to drive
the robot normally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from roboclaws.core.engine import MultiAgentEngine
from roboclaws.core.navigation_lifecycle import NavigationRunLifecycle
from roboclaws.mcp.server import RoboclawsMCPServer, make_roboclaws_mcp

log = logging.getLogger("coding-agent-nav-server")
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 18788
_AGENT_ID = 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expose AI2-THOR navigation tools directly to Codex or Claude Code.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--scene", default="FloorPlan201")
    parser.add_argument("--host", default=_DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--allow-privileged-tools",
        action="store_true",
        help="Opt into AI2-THOR demo helpers such as scene_objects and goto.",
    )
    return parser.parse_args(argv)


def _default_output_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M")
    return Path("output") / "runs" / stamp


def _snapshots_dir(output_dir: Path, agent_id: int = _AGENT_ID) -> Path:
    return output_dir / "snapshots" / f"agent-{agent_id}"


def _mcp_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/mcp"


def _client_setup_commands(url: str) -> dict[str, str]:
    return {
        "Codex": f"scripts/dev/coding_agent_docker.sh run codex mcp add roboclaws --url {url}",
        "Claude Code": (
            f"scripts/dev/coding_agent_docker.sh run claude mcp add --transport http "
            f"roboclaws {url}"
        ),
    }


def _print_setup(output_dir: Path, snapshots_dir: Path, url: str) -> None:
    commands = _client_setup_commands(url)
    print("\nRoboclaws direct MCP server is ready.")
    print(f"MCP URL       : {url}")
    print(f"Artifacts     : {output_dir}")
    print(f"Snapshots     : {snapshots_dir}")
    print("\nIn another terminal from this repo, run one of:")
    print(f"  {commands['Codex']}")
    print(f"  {commands['Claude Code']}")
    print("\nThen start Codex or Claude Code and ask it to drive the robot, for example:")
    print("  Read skills/ai2thor-navigator/SKILL.md, then use roboclaws__observe first.")
    print(
        "  For photo tasks, restart this server with --allow-privileged-tools and "
        "read skills/capture-object-photo/SKILL.md."
    )
    print("  麻烦给这个屋子里面的每个沙发以及椅子拍个照片...")
    print("\nThis server exits when the agent calls roboclaws__done or you press Ctrl-C.\n")
    sys.stdout.flush()


def run_coding_agent_nav_server(
    *,
    scene: str,
    output_dir: Path,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    poll_interval_s: float = 0.25,
    print_setup: bool = True,
    allow_privileged_tools: bool = False,
) -> dict[str, Any]:
    """Start the direct MCP server and block until done or Ctrl-C."""
    lifecycle = NavigationRunLifecycle(
        scene=scene,
        output_dir=output_dir,
        host=host,
        port=port,
        agent_id=_AGENT_ID,
    )
    lifecycle.prepare_output_dir()
    snapshots_dir = lifecycle.snapshots_dir
    url = lifecycle.mcp_url
    engine: MultiAgentEngine | None = None
    mcp_server: RoboclawsMCPServer | None = None
    terminated_by = "unknown"
    error: str | None = None

    try:
        log.info("starting MultiAgentEngine(scene=%s, agent_count=1)", scene)
        engine = MultiAgentEngine(scene=scene, agent_count=1)
        mcp_server = make_roboclaws_mcp(
            engine,
            agent_id=_AGENT_ID,
            run_dir=output_dir,
            host=host,
            port=port,
            snapshots_dir=snapshots_dir,
            allow_privileged_tools=allow_privileged_tools,
        )
        mcp_server.run_in_thread()
        mcp_server.write_runtime_event(
            "direct_server_started",
            scene=scene,
            mcp_url=url,
            snapshots_dir=str(snapshots_dir),
        )
        if print_setup:
            _print_setup(output_dir, snapshots_dir, url)

        while not mcp_server.done_event.wait(poll_interval_s):
            pass
        terminated_by = "agent_done"
    except KeyboardInterrupt:
        terminated_by = "keyboard_interrupt"
        if mcp_server is not None:
            mcp_server.write_runtime_event("keyboard_interrupt")
    except Exception as exc:
        terminated_by = "error"
        error = str(exc)
        if mcp_server is not None:
            mcp_server.write_runtime_event("direct_server_error", error=error)
        raise
    finally:
        snapshot_metrics = mcp_server.snapshot_metrics() if mcp_server is not None else {}
        if mcp_server is not None:
            mcp_server.write_runtime_event("direct_server_finished", terminated_by=terminated_by)
        result = lifecycle.write_direct_run_result(
            terminated_by=terminated_by,
            snapshot_metrics=snapshot_metrics,
            error=error,
        )
        if mcp_server is not None:
            mcp_server.close()
        if engine is not None:
            engine.close()

    return result


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    args = _parse_args(argv)
    output_dir = args.output_dir or _default_output_dir()
    try:
        result = run_coding_agent_nav_server(
            scene=args.scene,
            output_dir=output_dir,
            host=args.host,
            port=args.port,
            allow_privileged_tools=args.allow_privileged_tools,
        )
    except Exception as exc:
        print(f"coding-agent nav server failed: {exc}", file=sys.stderr)
        return 1

    print(f"terminated_by: {result['terminated_by']}")
    print(f"artifacts at {result['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
