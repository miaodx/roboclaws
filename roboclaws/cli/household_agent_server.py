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

from roboclaws.household.agibot_cleanup_contract import (
    AgibotCleanupMCPContract,
)
from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.isaac_lab_backend import (
    ISAACLAB_SUBPROCESS_BACKEND,
    IsaacLabSubprocessBackend,
)
from roboclaws.household.nav2_map_bundle import selected_nav2_map_bundle_dir
from roboclaws.household.profiles import cleanup_profile_names
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    DEFAULT_MAP_MODE,
    DEFAULT_REALWORLD_TASK,
    RAW_FPV_ONLY_MODE,
    REALWORLD_MAP_MODES,
    VISIBLE_OBJECT_DETECTIONS_MODE,
)
from roboclaws.household.realworld_mcp_server import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    MCP_SERVER_NAME,
    RealWorldMolmoCleanupMCPServer,
    make_molmo_realworld_cleanup_mcp,
)
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.subprocess_backend import (
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
)
from roboclaws.household.visual_grounding import (
    SIM_VISUAL_GROUNDING_PIPELINE_ID,
)
from roboclaws.maps.actionable_snapshot import runtime_metric_map_from_prior_artifact

log = logging.getLogger("molmo-realworld-cleanup-agent-server")
SYNTHETIC_BACKEND = "api_semantic_synthetic"
AGIBOT_GDK_BACKEND = "agibot_gdk"


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
    parser.add_argument("--task-name", default="household-cleanup")
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument(
        "--backend",
        choices=(
            SYNTHETIC_BACKEND,
            MOLMOSPACES_SUBPROCESS_BACKEND,
            ISAACLAB_SUBPROCESS_BACKEND,
            AGIBOT_GDK_BACKEND,
        ),
        default=SYNTHETIC_BACKEND,
    )
    parser.add_argument(
        "--context-json",
        type=Path,
        help="Agibot map context JSON, required when --backend=agibot_gdk.",
    )
    parser.add_argument("--runner-python", help="Python executable for the Agibot SDK runner.")
    parser.add_argument("--runner-script", type=Path, help="Override Agibot SDK runner path.")
    parser.add_argument("--agibot-map-artifact-dir", type=Path)
    parser.add_argument("--real-movement-enabled", action="store_true")
    parser.add_argument("--generated-mess-count", type=int, default=10)
    parser.add_argument(
        "--generated-mess-object-id",
        action="append",
        help="Private run-control object id to include in the generated mess set. Repeatable.",
    )
    parser.add_argument(
        "--map-bundle-dir",
        type=Path,
        help="Prebuilt Nav2 map bundle path, or environment id under assets/maps.",
    )
    parser.add_argument("--require-map-bundle", action="store_true")
    parser.add_argument(
        "--perception-mode",
        choices=(VISIBLE_OBJECT_DETECTIONS_MODE, RAW_FPV_ONLY_MODE, CAMERA_MODEL_POLICY_MODE),
        default=VISIBLE_OBJECT_DETECTIONS_MODE,
    )
    parser.add_argument(
        "--cleanup-profile",
        choices=cleanup_profile_names(),
        help="Public Molmo cleanup profile selected by the command facade.",
    )
    parser.add_argument(
        "--runtime-map-prior",
        type=Path,
        help="Prior runtime_metric_map.json snapshot to seed as non-actionable priors.",
    )
    parser.add_argument(
        "--map-mode",
        choices=tuple(sorted(REALWORLD_MAP_MODES)),
        default=DEFAULT_MAP_MODE,
        help=(
            "Agent-facing map projection. Default minimal exposes occupancy geometry and "
            "generated exploration candidates; rich is an explicit legacy/debug projection "
            "with authored public semantics."
        ),
    )
    parser.add_argument("--include-robot", action="store_true")
    parser.add_argument("--robot-name", default="rby1m")
    parser.add_argument("--record-robot-views", action="store_true")
    parser.add_argument("--scene-source", default="procthor-10k-val")
    parser.add_argument("--scene-index", type=int, default=0)
    parser.add_argument(
        "--isaac-scene-usd-path",
        type=Path,
        help="Prepared local USD/USDA scene for backend=isaaclab_subprocess real-mode runs.",
    )
    parser.add_argument("--visual-grounding", default=SIM_VISUAL_GROUNDING_PIPELINE_ID)
    parser.add_argument("--visual-grounding-base-url")
    parser.add_argument("--visual-grounding-timeout-s", type=float)
    parser.add_argument(
        "--rerun-command",
        help="Exact public command that launched this run, shown in report.html.",
    )
    return parser.parse_args(argv)


def default_output_dir(policy: str) -> Path:
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M%S")
    return Path("output") / "molmo-realworld-agent-dogfood" / policy / stamp


def mcp_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/mcp"


def client_setup_commands(url: str) -> dict[str, str]:
    port = url.rsplit(":", 1)[-1].split("/", 1)[0]
    return {
        "Codex": f"scripts/dev/coding_agent_docker.sh run codex mcp add roboclaws --url {url}",
        "Claude Code": (
            f"scripts/dev/coding_agent_docker.sh run claude mcp add --transport http "
            f"roboclaws {url}"
        ),
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
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    record_robot_views: bool = False,
    cleanup_profile: str | None = None,
) -> None:
    commands = client_setup_commands(url)
    print("\nMolmo real-world cleanup MCP server is ready.")
    print(f"MCP URL       : {url}")
    print(f"Artifacts     : {output_dir}")
    print(f"Policy label  : {policy}")
    print("Contract      : realworld_cleanup_v1")
    print(f"MCP server    : {MCP_SERVER_NAME}")
    print(f"Backend       : {backend}")
    print(f"Perception    : {perception_mode}")
    if cleanup_profile:
        print(f"Profile       : {cleanup_profile}")
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
    if perception_mode == RAW_FPV_ONLY_MODE:
        print("  Raw FPV mode returns camera observations, not observed_* detections.")
        print("  Inspect image blocks and call navigate_to_visual_candidate before pick.")
    elif perception_mode == CAMERA_MODEL_POLICY_MODE:
        print("  Observe returns raw FPV evidence first; call declare_visual_candidates.")
        print("  Candidates come from the configured server-side visual-grounding pipeline.")
        print("  Clean plausible observed_* camera candidates with the semantic cleanup loop.")
    else:
        print("  Clean plausible observed_* objects with navigate->pick->navigate->open?->place.")
    print("  The server rejects skipped semantic phases; follow required_tool if returned.")
    print("  Do not call scene_objects or read private scoring artifacts.")
    print("\nThis server exits when the agent calls roboclaws__done or you press Ctrl-C.\n")
    sys.stdout.flush()


def _is_loopback_url(url: str) -> bool:
    hostname = urlparse(url).hostname
    return hostname in {"127.0.0.1", "localhost"}


def _load_runtime_map_prior(path: str | Path | None) -> dict[str, Any] | None:
    if path is None or str(path) == "":
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return runtime_metric_map_from_prior_artifact(payload)


def run_molmo_realworld_cleanup_agent_server(
    *,
    output_dir: Path,
    seed: int = 7,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    policy: str = "codex_agent",
    task_name: str = "household-cleanup",
    task_prompt: str = DEFAULT_REALWORLD_TASK,
    backend: str = SYNTHETIC_BACKEND,
    generated_mess_count: int = 10,
    generated_mess_object_ids: tuple[str, ...] = (),
    map_bundle_dir: str | Path | None = None,
    require_map_bundle: bool = False,
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    record_robot_views: bool = False,
    scene_source: str = "procthor-10k-val",
    scene_index: int = 0,
    isaac_scene_usd_path: str | Path | None = None,
    cleanup_profile: str | None = None,
    runtime_map_prior_path: str | Path | None = None,
    map_mode: str = DEFAULT_MAP_MODE,
    visual_grounding: str = SIM_VISUAL_GROUNDING_PIPELINE_ID,
    visual_grounding_base_url: str | None = None,
    visual_grounding_timeout_s: float | None = None,
    context_json: str | Path | None = None,
    runner_python: str | Path | None = None,
    runner_script: str | Path | None = None,
    agibot_map_artifact_dir: str | Path | None = None,
    real_movement_enabled: bool = False,
    rerun_command: str | None = None,
    poll_interval_s: float = 0.25,
    print_setup_text: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if backend == AGIBOT_GDK_BACKEND:
        generated_mess_count = 0
    if generated_mess_count < 1 and backend != AGIBOT_GDK_BACKEND:
        raise ValueError("generated_mess_count must be >= 1")
    selected_bundle_dir = selected_nav2_map_bundle_dir(
        map_bundle_dir,
        required=require_map_bundle,
    )
    runtime_map_prior = _load_runtime_map_prior(runtime_map_prior_path)
    visual_backends = {MOLMOSPACES_SUBPROCESS_BACKEND, ISAACLAB_SUBPROCESS_BACKEND}
    if include_robot and backend not in visual_backends:
        raise ValueError("robot inclusion requires a visual subprocess backend")
    if record_robot_views and (backend not in visual_backends or not include_robot):
        raise ValueError(
            "record_robot_views requires a visual subprocess backend and include_robot"
        )
    agibot_contract: AgibotCleanupMCPContract | None = None
    if backend == AGIBOT_GDK_BACKEND:
        if context_json is None or str(context_json) == "":
            raise ValueError("backend=agibot_gdk requires --context-json")
        scenario = build_cleanup_scenario(seed=seed)
        agibot_contract = AgibotCleanupMCPContract(
            run_dir=output_dir,
            context_json=Path(context_json),
            runner_script=Path(runner_script) if runner_script is not None else None,
            runner_python=runner_python,
            real_movement_enabled=real_movement_enabled,
            agibot_map_artifact_dir=Path(agibot_map_artifact_dir)
            if agibot_map_artifact_dir is not None
            else None,
            scenario=scenario,
            task_prompt=task_prompt,
        )
        base_contract = agibot_contract.contract
        perception_mode = agibot_contract.perception_mode
        map_mode = agibot_contract.map_mode
        cleanup_profile = None
    elif backend == MOLMOSPACES_SUBPROCESS_BACKEND:
        backend_instance = MolmoSpacesSubprocessBackend(
            run_dir=output_dir,
            seed=seed,
            include_robot=include_robot,
            robot_name=robot_name,
            generated_mess_count=generated_mess_count,
            generated_mess_object_ids=generated_mess_object_ids,
            scene_source=scene_source,
            scene_index=scene_index,
        )
        scenario = backend_instance.scenario
        base_contract = CleanupBackendSession(scenario, backend=backend_instance)
    elif backend == ISAACLAB_SUBPROCESS_BACKEND:
        backend_instance = IsaacLabSubprocessBackend(
            run_dir=output_dir,
            seed=seed,
            include_robot=include_robot,
            robot_name=robot_name,
            generated_mess_count=generated_mess_count,
            generated_mess_object_ids=generated_mess_object_ids,
            scene_source=scene_source,
            scene_index=scene_index,
            map_bundle_dir=selected_bundle_dir,
            scene_usd_path=Path(isaac_scene_usd_path) if isaac_scene_usd_path else None,
        )
        scenario = backend_instance.scenario
        base_contract = CleanupBackendSession(scenario, backend=backend_instance)
    else:
        scenario = build_cleanup_scenario(seed=seed)
        base_contract = CleanupBackendSession(scenario)

    server: RealWorldMolmoCleanupMCPServer | None = None
    terminated_by = "unknown"
    error: str | None = None
    url = mcp_url(host, port)

    try:
        server = make_molmo_realworld_cleanup_mcp(
            run_dir=output_dir,
            scenario=scenario,
            base_contract=base_contract,
            contract=agibot_contract,
            host=host,
            port=port,
            policy=policy,
            task_name=task_name,
            task_prompt=task_prompt,
            fixture_hint_mode="room_only",
            perception_mode=perception_mode,
            map_bundle_dir=selected_bundle_dir,
            record_robot_views=record_robot_views,
            cleanup_profile=cleanup_profile,
            runtime_map_prior=runtime_map_prior,
            runtime_map_prior_source=str(runtime_map_prior_path or ""),
            map_mode=map_mode,
            visual_grounding=visual_grounding,
            visual_grounding_base_url=visual_grounding_base_url,
            visual_grounding_timeout_s=visual_grounding_timeout_s,
            rerun_command=rerun_command,
        )
        server.run_in_thread()
        server.write_runtime_event("direct_molmo_realworld_cleanup_server_started", mcp_url=url)
        if print_setup_text:
            print_setup(
                output_dir,
                url,
                policy,
                backend=backend,
                perception_mode=perception_mode,
                record_robot_views=record_robot_views,
                cleanup_profile=cleanup_profile,
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
            task_name=args.task_name,
            task_prompt=args.task,
            backend=args.backend,
            generated_mess_count=args.generated_mess_count,
            generated_mess_object_ids=tuple(args.generated_mess_object_id or ()),
            map_bundle_dir=args.map_bundle_dir,
            require_map_bundle=args.require_map_bundle,
            perception_mode=args.perception_mode,
            include_robot=args.include_robot,
            robot_name=args.robot_name,
            record_robot_views=args.record_robot_views,
            scene_source=args.scene_source,
            scene_index=args.scene_index,
            isaac_scene_usd_path=args.isaac_scene_usd_path,
            cleanup_profile=args.cleanup_profile,
            runtime_map_prior_path=args.runtime_map_prior,
            map_mode=args.map_mode,
            visual_grounding=args.visual_grounding,
            visual_grounding_base_url=args.visual_grounding_base_url,
            visual_grounding_timeout_s=args.visual_grounding_timeout_s,
            context_json=args.context_json,
            runner_python=args.runner_python,
            runner_script=args.runner_script,
            agibot_map_artifact_dir=args.agibot_map_artifact_dir,
            real_movement_enabled=args.real_movement_enabled,
            rerun_command=args.rerun_command,
        )
    except Exception as exc:
        print(f"Molmo real-world cleanup agent server failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
