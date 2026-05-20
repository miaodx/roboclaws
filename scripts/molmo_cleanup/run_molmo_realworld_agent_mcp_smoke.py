#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.backend_contract import CleanupBackendSession  # noqa: E402
from roboclaws.molmo_cleanup.nav2_map_bundle import selected_nav2_map_bundle_dir  # noqa: E402
from roboclaws.molmo_cleanup.profiles import (  # noqa: E402
    WORLD_LABELS_PERF_PROFILE,
    cleanup_profile_names,
)
from roboclaws.molmo_cleanup.realworld_contract import (  # noqa: E402
    CAMERA_MODEL_POLICY_MODE,
    DEFAULT_REALWORLD_TASK,
    RAW_FPV_ONLY_MODE,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    infer_target_fixture_for_detection,
)
from roboclaws.molmo_cleanup.realworld_mcp_server import (  # noqa: E402
    make_molmo_realworld_cleanup_mcp,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario  # noqa: E402
from roboclaws.molmo_cleanup.semantic_cleanup_loop import (  # noqa: E402
    run_semantic_cleanup_loop,
)
from roboclaws.molmo_cleanup.semantic_timeline import CLEAN_OBSERVED_OBJECT_TOOL  # noqa: E402
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
        "--enable-promoted-cleanup-tools",
        action="store_true",
        help="Expose promoted-candidate composite cleanup tools for explicit comparison runs.",
    )
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
    map_bundle_dir: str | Path | None = None,
    require_map_bundle: bool = False,
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    record_robot_views: bool = False,
    cleanup_profile: str | None = None,
    enable_promoted_cleanup_tools: bool | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if generated_mess_count < 1:
        raise ValueError("generated_mess_count must be >= 1")
    selected_bundle_dir = selected_nav2_map_bundle_dir(
        map_bundle_dir,
        required=require_map_bundle,
    )
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
        base_contract = CleanupBackendSession(scenario, backend=backend_instance)
    else:
        scenario = build_cleanup_scenario(seed=seed)
        base_contract = CleanupBackendSession(scenario)

    server = make_molmo_realworld_cleanup_mcp(
        run_dir=output_dir,
        scenario=scenario,
        base_contract=base_contract,
        port=0,
        policy=policy,
        agent_driven=True,
        task_prompt=task,
        fixture_hint_mode="room_only",
        perception_mode=perception_mode,
        map_bundle_dir=selected_bundle_dir,
        record_robot_views=record_robot_views,
        cleanup_profile=cleanup_profile,
        enable_promoted_cleanup_tools=enable_promoted_cleanup_tools,
    )
    try:
        _drive_public_sweep(
            server,
            policy=policy,
            use_composite_cleanup=server.enable_promoted_cleanup_tools,
        )
        done = server.call_tool("done", reason=f"{policy} cleanup complete")
    finally:
        server.close()

    return json.loads(Path(done["run_result"]).read_text(encoding="utf-8"))


def _drive_public_sweep(
    server: Any,
    *,
    policy: str,
    use_composite_cleanup: bool = False,
) -> None:
    metric_map = server.call_tool("metric_map")
    fixture_hints = server.call_tool("fixture_hints")
    handled_handles: set[str] = set()
    for waypoint in metric_map["inspection_waypoints"]:
        waypoint_id = str(waypoint["waypoint_id"])
        server.call_tool("navigate_to_waypoint", waypoint_id=waypoint_id)
        observation = server.call_tool("observe")
        detections = _detections_for_observation(server, observation)
        for detection in detections:
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
            _clean_handle(
                server,
                handle=handle,
                fixture=target_fixture,
                detection=detection,
                use_composite_cleanup=use_composite_cleanup,
            )
            server.call_tool("observe")
            handled_handles.add(handle)


def _detections_for_observation(server: Any, observation: dict[str, Any]) -> list[dict[str, Any]]:
    detections = list(observation.get("visible_object_detections", []))
    if detections or not observation.get("camera_model_policy_available"):
        return detections
    raw = observation.get("raw_fpv_observation") or {}
    observation_id = str(raw.get("observation_id") or "")
    response = server.call_tool("declare_visual_candidates", observation_id=observation_id)
    return list(response.get("camera_model_candidates", []))


def _clean_handle(
    server: Any,
    *,
    handle: str,
    fixture: dict[str, Any],
    detection: dict[str, Any] | None = None,
    use_composite_cleanup: bool = False,
) -> None:
    fixture_id = str(fixture["fixture_id"])
    if use_composite_cleanup:
        response = server.call_tool(
            CLEAN_OBSERVED_OBJECT_TOOL,
            object_id=handle,
            fixture_id=fixture_id,
            placement_tool=str((detection or {}).get("recommended_tool") or "auto"),
        )
        if not response.get("ok"):
            raise RuntimeError(response)
        return
    run_semantic_cleanup_loop(
        targets=[
            {
                "object_id": handle,
                "target_receptacle_id": fixture_id,
                "target_receptacle": fixture,
            }
        ],
        contract=_RealWorldMcpLoop(server),
        call_tool=_invoke_shared_loop_tool,
        target_request_key="fixture_id",
        include_object_id_in_receptacle_request=False,
        include_object_id_in_target_requests=False,
    )


def _invoke_shared_loop_tool(
    _tool: str,
    _request: dict[str, Any],
    fn: Any,
) -> dict[str, Any]:
    return fn()


class _RealWorldMcpLoop:
    def __init__(self, server: Any) -> None:
        self._server = server

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        return self._server.call_tool("navigate_to_object", object_id=object_id)

    def pick(self, object_id: str) -> dict[str, Any]:
        return self._server.call_tool("pick", object_id=object_id)

    def navigate_to_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self._server.call_tool("navigate_to_receptacle", fixture_id=receptacle_id)

    def open_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self._server.call_tool("open_receptacle", fixture_id=receptacle_id)

    def place(self, receptacle_id: str) -> dict[str, Any]:
        return self._server.call_tool("place", fixture_id=receptacle_id)

    def place_inside(self, receptacle_id: str) -> dict[str, Any]:
        return self._server.call_tool("place_inside", fixture_id=receptacle_id)

    def close_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self._server.call_tool("close_receptacle", fixture_id=receptacle_id)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_smoke(
        output_dir=args.output_dir,
        seed=args.seed,
        task=args.task,
        policy=args.policy,
        backend=args.backend,
        generated_mess_count=args.generated_mess_count,
        map_bundle_dir=args.map_bundle_dir,
        require_map_bundle=args.require_map_bundle,
        perception_mode=args.perception_mode,
        include_robot=args.include_robot,
        robot_name=args.robot_name,
        record_robot_views=args.record_robot_views,
        cleanup_profile=args.cleanup_profile,
        enable_promoted_cleanup_tools=(
            args.enable_promoted_cleanup_tools or args.cleanup_profile == WORLD_LABELS_PERF_PROFILE
        ),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
