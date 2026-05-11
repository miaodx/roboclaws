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
from roboclaws.molmo_cleanup.realworld_contract import (  # noqa: E402
    DEFAULT_REALWORLD_TASK,
    infer_target_fixture_for_detection,
)
from roboclaws.molmo_cleanup.realworld_mcp_server import (  # noqa: E402
    make_molmo_realworld_cleanup_mcp,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario  # noqa: E402
from roboclaws.molmo_cleanup.subprocess_backend import (  # noqa: E402
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
)

SYNTHETIC_BACKEND = "api_semantic_synthetic"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a deterministic smoke agent through the ADR-0003 Molmo MCP surface."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument("--policy", default="realworld_contract_smoke_agent")
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


def run_smoke(
    *,
    output_dir: Path,
    seed: int = 1,
    task: str = DEFAULT_REALWORLD_TASK,
    policy: str = "realworld_contract_smoke_agent",
    backend: str = SYNTHETIC_BACKEND,
    generated_mess_count: int = 10,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    record_robot_views: bool = False,
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

    server = make_molmo_realworld_cleanup_mcp(
        run_dir=output_dir,
        scenario=scenario,
        base_contract=base_contract,
        port=0,
        policy=policy,
        agent_driven=True,
        task_prompt=task,
        fixture_hint_mode="room_only",
        record_robot_views=record_robot_views,
    )
    try:
        _drive_public_sweep(server, policy=policy)
        done = server.call_tool("done", reason=f"{policy} cleanup complete")
    finally:
        server.close()

    return json.loads(Path(done["run_result"]).read_text(encoding="utf-8"))


def _drive_public_sweep(server: Any, *, policy: str) -> None:
    metric_map = server.call_tool("metric_map")
    fixture_hints = server.call_tool("fixture_hints")
    handled_handles: set[str] = set()
    for waypoint in metric_map["inspection_waypoints"]:
        waypoint_id = str(waypoint["waypoint_id"])
        server.call_tool("navigate_to_waypoint", waypoint_id=waypoint_id)
        observation = server.call_tool("observe")
        for detection in observation.get("visible_object_detections", []):
            handle = str(detection["object_id"])
            if handle in handled_handles:
                continue
            target_fixture = infer_target_fixture_for_detection(detection, fixture_hints)
            if target_fixture is None:
                continue
            fixture_id = str(target_fixture["fixture_id"])
            support = detection.get("support_estimate") or {}
            if support.get("fixture_id") == fixture_id:
                continue
            _clean_handle(server, handle=handle, fixture=target_fixture)
            handled_handles.add(handle)


def _clean_handle(server: Any, *, handle: str, fixture: dict[str, Any]) -> None:
    fixture_id = str(fixture["fixture_id"])
    server.call_tool("navigate_to_object", object_id=handle)
    server.call_tool("pick", object_id=handle)
    server.call_tool("navigate_to_receptacle", fixture_id=fixture_id)
    if _requires_inside_place(fixture):
        server.call_tool("open_receptacle", fixture_id=fixture_id)
        server.call_tool("place_inside", fixture_id=fixture_id)
    else:
        server.call_tool("place", fixture_id=fixture_id)


def _requires_inside_place(fixture: dict[str, Any]) -> bool:
    text = f"{fixture.get('category', '')} {fixture.get('name', '')}".lower()
    return "fridge" in text or "refrigerator" in text


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_smoke(
        output_dir=args.output_dir,
        seed=args.seed,
        task=args.task,
        policy=args.policy,
        backend=args.backend,
        generated_mess_count=args.generated_mess_count,
        include_robot=args.include_robot,
        robot_name=args.robot_name,
        record_robot_views=args.record_robot_views,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
