#!/usr/bin/env python3
"""Expose the ADR-0003 Molmo real-world cleanup contract to external agents."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract  # noqa: E402
from roboclaws.molmo_cleanup.realworld_contract import DEFAULT_REALWORLD_TASK  # noqa: E402
from roboclaws.molmo_cleanup.realworld_mcp_server import (  # noqa: E402
    DEFAULT_HOST,
    DEFAULT_PORT,
    MCP_SERVER_NAME,
    RealWorldMolmoCleanupMCPServer,
    make_molmo_realworld_cleanup_mcp,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario  # noqa: E402
from roboclaws.molmo_cleanup.subprocess_backend import (  # noqa: E402
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
)

log = logging.getLogger("molmo-realworld-cleanup-agent-server")
SYNTHETIC_BACKEND = "api_semantic_synthetic"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expose ADR-0003 Molmo cleanup tools to Codex, Claude Code, or OpenClaw.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--policy", default="codex_agent")
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument(
        "--backend",
        choices=(SYNTHETIC_BACKEND, MOLMOSPACES_SUBPROCESS_BACKEND),
        default=SYNTHETIC_BACKEND,
    )
    parser.add_argument("--generated-mess-count", type=int, default=10)
    parser.add_argument("--include-robot", action="store_true")
    parser.add_argument("--robot-name", default="rby1m")
    parser.add_argument("--record-robot-views", action="store_true")
    return parser.parse_args(argv)


def default_output_dir(policy: str) -> Path:
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M%S")
    return Path("output") / "molmo-realworld-agent-dogfood" / policy / stamp


def mcp_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/mcp"


def client_setup_commands(url: str) -> dict[str, str]:
    port = url.rsplit(":", 1)[-1].split("/", 1)[0]
    return {
        "Codex": f"codex mcp add roboclaws --url {url}",
        "Claude Code": f"claude mcp add --transport http roboclaws {url}",
        "OpenClaw": (
            "SKILLS_DIR=$PWD/skills/molmo-realworld-cleanup "
            f"ROBOCLAWS_MCP_URL=http://host.docker.internal:{port}/mcp "
            "just chat::run"
        ),
    }


def print_setup(
    output_dir: Path,
    url: str,
    policy: str,
    *,
    backend: str = SYNTHETIC_BACKEND,
    record_robot_views: bool = False,
) -> None:
    commands = client_setup_commands(url)
    print("\nMolmo real-world cleanup MCP server is ready.")
    print(f"MCP URL       : {url}")
    print(f"Artifacts     : {output_dir}")
    print(f"Policy label  : {policy}")
    print("Contract      : realworld_cleanup_v1")
    print(f"MCP server    : {MCP_SERVER_NAME}")
    print(f"Backend       : {backend}")
    print(f"Visual report : {'enabled' if record_robot_views else 'disabled'}")
    print("\nIn another terminal from this repo, run one of:")
    print(f"  {commands['Codex']}")
    print(f"  {commands['Claude Code']}")
    print("\nFor OpenClaw, start the Gateway with the same MCP URL, for example:")
    if _is_loopback_url(url):
        print(
            "  Docker note: restart this server with --host 0.0.0.0 for OpenClaw; "
            "the Gateway container cannot reach a host-only 127.0.0.1 bind."
        )
    print(f"  {commands['OpenClaw']}")
    print("\nThen start the agent and use this kickoff:")
    print("  Read skills/molmo-realworld-cleanup/SKILL.md.")
    print("  Call roboclaws__metric_map and roboclaws__fixture_hints first.")
    print("  Sweep waypoints with roboclaws__navigate_to_waypoint then roboclaws__observe.")
    print("  Clean plausible observed_* objects, then call roboclaws__done last.")
    print("  Do not call scene_objects or read private scoring artifacts.")
    print("\nThis server exits when the agent calls roboclaws__done or you press Ctrl-C.\n")
    sys.stdout.flush()


def _is_loopback_url(url: str) -> bool:
    hostname = urlparse(url).hostname
    return hostname in {"127.0.0.1", "localhost"}


def run_molmo_realworld_cleanup_agent_server(
    *,
    output_dir: Path,
    seed: int = 7,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    policy: str = "codex_agent",
    task_prompt: str = DEFAULT_REALWORLD_TASK,
    backend: str = SYNTHETIC_BACKEND,
    generated_mess_count: int = 10,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    record_robot_views: bool = False,
    poll_interval_s: float = 0.25,
    print_setup_text: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if generated_mess_count < 1:
        raise ValueError("generated_mess_count must be >= 1")
    if include_robot and backend != MOLMOSPACES_SUBPROCESS_BACKEND:
        raise ValueError("robot inclusion requires backend=molmospaces_subprocess")
    if record_robot_views and (backend != MOLMOSPACES_SUBPROCESS_BACKEND or not include_robot):
        raise ValueError(
            "record_robot_views requires backend=molmospaces_subprocess and include_robot"
        )
    if backend == MOLMOSPACES_SUBPROCESS_BACKEND:
        backend_instance = MolmoSpacesSubprocessBackend(
            run_dir=output_dir,
            seed=seed,
            include_robot=include_robot,
            robot_name=robot_name,
            generated_mess_count=generated_mess_count,
        )
        scenario = backend_instance.scenario
        base_contract = MolmoCleanupToolContract(scenario, backend=backend_instance)
    else:
        scenario = build_cleanup_scenario(seed=seed)
        base_contract = MolmoCleanupToolContract(scenario)

    server: RealWorldMolmoCleanupMCPServer | None = None
    terminated_by = "unknown"
    error: str | None = None
    url = mcp_url(host, port)

    try:
        server = make_molmo_realworld_cleanup_mcp(
            run_dir=output_dir,
            scenario=scenario,
            base_contract=base_contract,
            host=host,
            port=port,
            policy=policy,
            task_prompt=task_prompt,
            fixture_hint_mode="room_only",
            record_robot_views=record_robot_views,
        )
        server.run_in_thread()
        server.write_runtime_event("direct_molmo_realworld_cleanup_server_started", mcp_url=url)
        if print_setup_text:
            print_setup(
                output_dir,
                url,
                policy,
                backend=backend,
                record_robot_views=record_robot_views,
            )
        while not server.done_event.wait(poll_interval_s):
            pass
        terminated_by = "agent_done"
    except KeyboardInterrupt:
        terminated_by = "keyboard_interrupt"
        if server is not None:
            server.write_runtime_event("keyboard_interrupt")
    except Exception as exc:
        terminated_by = "error"
        error = str(exc)
        if server is not None:
            server.write_runtime_event("direct_molmo_realworld_cleanup_server_error", error=error)
        raise
    finally:
        result = {
            "terminated_by": terminated_by,
            "output_dir": str(output_dir),
            "run_result": str(output_dir / "run_result.json"),
            "error": error,
        }
        if server is not None:
            server.write_runtime_event(
                "direct_molmo_realworld_cleanup_server_finished",
                terminated_by=terminated_by,
                error=error,
            )
            server.close()
    return result


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    args = parse_args(argv)
    output_dir = args.output_dir or default_output_dir(args.policy)
    try:
        result = run_molmo_realworld_cleanup_agent_server(
            output_dir=output_dir,
            seed=args.seed,
            host=args.host,
            port=args.port,
            policy=args.policy,
            task_prompt=args.task,
            backend=args.backend,
            generated_mess_count=args.generated_mess_count,
            include_robot=args.include_robot,
            robot_name=args.robot_name,
            record_robot_views=args.record_robot_views,
        )
    except Exception as exc:
        print(f"Molmo real-world cleanup agent server failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
