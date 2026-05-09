#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract  # noqa: E402
from roboclaws.molmo_cleanup.mcp_server import make_molmo_cleanup_mcp  # noqa: E402
from roboclaws.molmo_cleanup.policy import build_public_cleanup_plan  # noqa: E402
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario  # noqa: E402
from roboclaws.molmo_cleanup.subprocess_backend import (  # noqa: E402
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
)

DEFAULT_TASK = "帮我整理这个房间"
SYNTHETIC_BACKEND = "api_semantic_synthetic"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a cheap current-contract Molmo MCP bridge smoke."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--restore-count", type=int, default=5)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--policy", default="contract_smoke_agent")
    parser.add_argument(
        "--backend",
        choices=(SYNTHETIC_BACKEND, MOLMOSPACES_SUBPROCESS_BACKEND),
        default=SYNTHETIC_BACKEND,
    )
    parser.add_argument("--include-robot", action="store_true")
    parser.add_argument("--robot-name", default="rby1m")
    parser.add_argument("--record-robot-views", action="store_true")
    return parser.parse_args(argv)


def run_smoke(
    *,
    output_dir: Path,
    seed: int = 7,
    task: str = DEFAULT_TASK,
    policy: str = "contract_smoke_agent",
    restore_count: int = 5,
    backend: str = SYNTHETIC_BACKEND,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    record_robot_views: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
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
        )
        scenario = backend_instance.scenario
        contract = MolmoCleanupToolContract(scenario, backend=backend_instance)
    else:
        scenario = build_cleanup_scenario(seed=seed)
        contract = None
    server = make_molmo_cleanup_mcp(
        run_dir=output_dir,
        scenario=scenario,
        contract=contract,
        port=0,
        policy=policy,
        agent_driven=True,
        task_prompt=task,
        record_robot_views=record_robot_views,
    )
    try:
        server.call_tool("observe")
        scene_objects = server.call_tool("scene_objects")
        actions = build_public_cleanup_plan(task_prompt=task, scene_payload=scene_objects)[
            :restore_count
        ]
        for action in actions:
            object_id = action.object_id
            receptacle_id = action.receptacle_id
            server.call_tool("navigate_to_object", object_id=object_id)
            server.call_tool("pick", object_id=object_id)
            server.call_tool("navigate_to_receptacle", receptacle_id=receptacle_id)
            if _requires_inside_place(scene_objects, receptacle_id):
                server.call_tool("open_receptacle", receptacle_id=receptacle_id)
                server.call_tool("place_inside", receptacle_id=receptacle_id)
            else:
                server.call_tool("place", receptacle_id=receptacle_id)
            server.call_tool("object_done", object_id=object_id, receptacle_id=receptacle_id)
        done = server.call_tool("done", reason=f"{policy} cleanup complete")
    finally:
        server.close()

    run_result_path = Path(done["run_result"])
    return json.loads(run_result_path.read_text(encoding="utf-8"))


def _requires_inside_place(scene_objects: dict[str, Any], receptacle_id: str) -> bool:
    receptacle = next(
        (
            item
            for item in scene_objects.get("receptacles", [])
            if item.get("receptacle_id") == receptacle_id
        ),
        {},
    )
    name = str(receptacle.get("name", "")).lower()
    return "fridge" in name or "refrigerator" in name


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_smoke(
        output_dir=args.output_dir,
        seed=args.seed,
        task=args.task,
        policy=args.policy,
        restore_count=args.restore_count,
        backend=args.backend,
        include_robot=args.include_robot,
        robot_name=args.robot_name,
        record_robot_views=args.record_robot_views,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
