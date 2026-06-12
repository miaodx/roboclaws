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

from roboclaws.household.backend_contract import CleanupBackendSession  # noqa: E402
from roboclaws.household.nav2_map_bundle import selected_nav2_map_bundle_dir  # noqa: E402
from roboclaws.household.profiles import (  # noqa: E402
    cleanup_profile_names,
)
from roboclaws.household.realworld_contract import (  # noqa: E402
    CAMERA_MODEL_POLICY_MODE,
    DEFAULT_REALWORLD_TASK,
    RAW_FPV_ONLY_MODE,
    VISIBLE_OBJECT_DETECTIONS_MODE,
)
from roboclaws.household.realworld_mcp_server import (  # noqa: E402
    make_molmo_realworld_cleanup_mcp,
)
from roboclaws.household.scenario import build_cleanup_scenario  # noqa: E402
from roboclaws.household.semantic_cleanup_loop import (  # noqa: E402
    run_semantic_cleanup_loop,
)
from roboclaws.household.subprocess_backend import (  # noqa: E402
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
)
from roboclaws.household.task_intent import (  # noqa: E402
    TASK_INTENT_MODE_CUSTOM,
    TASK_INTENT_MODE_DEFAULT,
    normalize_task_intent_mode,
)
from roboclaws.household.types import CleanupScenario, PrivateScoringManifest  # noqa: E402
from roboclaws.household.visual_grounding import (  # noqa: E402
    SIM_VISUAL_GROUNDING_PIPELINE_ID,
)
from roboclaws.launch.goals import goal_contract_from_file, goal_contract_from_json  # noqa: E402
from roboclaws.maps.actionable_snapshot import runtime_metric_map_from_prior_artifact  # noqa: E402

SYNTHETIC_BACKEND = "api_semantic_synthetic"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a deterministic smoke agent through the ADR-0003 Molmo MCP surface."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument("--task-intent-mode", default=TASK_INTENT_MODE_DEFAULT)
    parser.add_argument("--goal-contract", type=Path)
    parser.add_argument("--goal-contract-json")
    parser.add_argument("--policy", default="realworld_contract_smoke_agent")
    parser.add_argument(
        "--backend",
        choices=(SYNTHETIC_BACKEND, MOLMOSPACES_SUBPROCESS_BACKEND),
        default=SYNTHETIC_BACKEND,
    )
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
    parser.add_argument("--visual-grounding", default=SIM_VISUAL_GROUNDING_PIPELINE_ID)
    parser.add_argument("--visual-grounding-base-url")
    parser.add_argument("--visual-grounding-timeout-s", type=float)
    parser.add_argument(
        "--cleanup-profile",
        choices=cleanup_profile_names(),
        help="Public cleanup evidence lane or smoke preset selected by the command facade.",
    )
    parser.add_argument(
        "--runtime-map-prior",
        type=Path,
        help="Prior runtime_metric_map.json snapshot to seed as non-actionable priors.",
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
    generated_mess_object_ids: tuple[str, ...] = (),
    map_bundle_dir: str | Path | None = None,
    require_map_bundle: bool = False,
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    record_robot_views: bool = False,
    cleanup_profile: str | None = None,
    runtime_map_prior_path: str | Path | None = None,
    visual_grounding: str = SIM_VISUAL_GROUNDING_PIPELINE_ID,
    visual_grounding_base_url: str | None = None,
    visual_grounding_timeout_s: float | None = None,
    task_intent_mode: str = TASK_INTENT_MODE_DEFAULT,
    goal_contract_json: str | None = None,
    goal_contract_path: str | Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if generated_mess_count < 0:
        raise ValueError("generated_mess_count must be >= 0")
    selected_bundle_dir = selected_nav2_map_bundle_dir(
        map_bundle_dir,
        required=require_map_bundle,
    )
    runtime_map_prior = _load_runtime_map_prior(runtime_map_prior_path)
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
            generated_mess_object_ids=generated_mess_object_ids,
        )
        scenario = backend_instance.scenario
        base_contract = CleanupBackendSession(scenario, backend=backend_instance)
    else:
        scenario = build_cleanup_scenario(seed=seed)
        if generated_mess_count == 0:
            scenario = _scenario_without_private_targets(scenario)
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
        runtime_map_prior=runtime_map_prior,
        runtime_map_prior_source=str(runtime_map_prior_path or ""),
        visual_grounding=visual_grounding,
        visual_grounding_base_url=visual_grounding_base_url,
        visual_grounding_timeout_s=visual_grounding_timeout_s,
        task_intent_mode=task_intent_mode,
        goal_contract=goal_contract_from_json(goal_contract_json)
        or goal_contract_from_file(goal_contract_path),
    )
    try:
        if normalize_task_intent_mode(task_intent_mode) == TASK_INTENT_MODE_CUSTOM:
            _drive_open_ended_probe(server)
            done = server.call_tool("done", reason=f"{policy} open-ended smoke task complete")
        else:
            _drive_public_sweep(server)
            done = server.call_tool("done", reason=f"{policy} cleanup complete")
    finally:
        server.close()

    return json.loads(Path(done["run_result"]).read_text(encoding="utf-8"))


def _load_runtime_map_prior(path: str | Path | None) -> dict[str, Any] | None:
    if path is None or str(path) == "":
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return runtime_metric_map_from_prior_artifact(payload)


def _drive_public_sweep(
    server: Any,
) -> None:
    metric_map = server.call_tool("metric_map")
    server.call_tool("fixture_hints")
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
            detection = _confirm_visual_scan_if_needed(server, detection)
            target_fixture = _target_fixture_for_detection(server, detection)
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
            )
            server.call_tool("observe")
            handled_handles.add(handle)
        _clean_pending_worklist(server, handled_handles)
    _clean_pending_worklist(server, handled_handles)


def _drive_open_ended_probe(server: Any) -> None:
    metric_map = server.call_tool("metric_map")
    server.call_tool("fixture_hints")
    waypoints = metric_map.get("inspection_waypoints") or []
    if not waypoints:
        server.call_tool("observe")
        return
    for waypoint in waypoints:
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if waypoint_id:
            server.call_tool("navigate_to_waypoint", waypoint_id=waypoint_id)
        observation = server.call_tool("observe")
        if _detections_for_observation(server, observation):
            return


def _clean_pending_worklist(server: Any, handled_handles: set[str]) -> None:
    while True:
        agent_view = server._agent_view_payload()
        pending = [
            dict(item)
            for item in agent_view.get("cleanup_worklist", {}).get("objects", [])
            if item.get("cleanup_recommended") and str(item.get("state") or "") == "pending"
        ]
        next_item = next(
            (item for item in pending if str(item.get("object_id") or "") not in handled_handles),
            None,
        )
        if next_item is None:
            return
        handle = str(next_item.get("object_id") or "")
        next_item = _confirm_visual_scan_if_needed(server, next_item)
        fixture = _target_fixture_for_detection(server, next_item)
        if fixture is None:
            handled_handles.add(handle)
            continue
        _clean_handle(server, handle=handle, fixture=fixture)
        server.call_tool("observe")
        handled_handles.add(handle)


def _target_fixture_for_detection(server: Any, detection: dict[str, Any]) -> dict[str, Any] | None:
    fixture_id = str(detection.get("candidate_fixture_id") or "")
    if not fixture_id:
        return None
    fixtures = server.contract.public_receptacles_by_id()
    fixture = fixtures.get(fixture_id)
    if fixture is None:
        return None
    return dict(fixture)


def _detections_for_observation(server: Any, observation: dict[str, Any]) -> list[dict[str, Any]]:
    detections = list(observation.get("visible_object_detections", []))
    if detections or not observation.get("camera_model_policy_available"):
        return detections
    raw = observation.get("raw_fpv_observation") or {}
    observation_id = str(raw.get("observation_id") or "")
    response = server.call_tool("declare_visual_candidates", observation_id=observation_id)
    return list(response.get("camera_model_candidates", []))


def _confirm_visual_scan_if_needed(server: Any, detection: dict[str, Any]) -> dict[str, Any]:
    if str(detection.get("candidate_state") or "") != "visual_scan_required":
        return detection
    waypoint_id = str(detection.get("waypoint_id") or detection.get("last_waypoint_id") or "")
    if waypoint_id:
        server.call_tool("navigate_to_waypoint", waypoint_id=waypoint_id)
    server.call_tool("adjust_camera", yaw_delta_deg=15.0, pitch_delta_deg=0.0)
    observation = server.call_tool("observe")
    handle = str(detection.get("object_id") or "")
    return next(
        (
            dict(item)
            for item in observation.get("visible_object_detections", [])
            if str(item.get("object_id") or "") == handle
        ),
        detection,
    )


def _clean_handle(
    server: Any,
    *,
    handle: str,
    fixture: dict[str, Any],
) -> None:
    fixture_id = str(fixture["fixture_id"])
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
        generated_mess_object_ids=tuple(args.generated_mess_object_id or ()),
        map_bundle_dir=args.map_bundle_dir,
        require_map_bundle=args.require_map_bundle,
        perception_mode=args.perception_mode,
        include_robot=args.include_robot,
        robot_name=args.robot_name,
        record_robot_views=args.record_robot_views,
        cleanup_profile=args.cleanup_profile,
        runtime_map_prior_path=args.runtime_map_prior,
        visual_grounding=args.visual_grounding,
        visual_grounding_base_url=args.visual_grounding_base_url,
        visual_grounding_timeout_s=args.visual_grounding_timeout_s,
        task_intent_mode=args.task_intent_mode,
        goal_contract_json=args.goal_contract_json,
        goal_contract_path=args.goal_contract,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _scenario_without_private_targets(scenario: CleanupScenario) -> CleanupScenario:
    scenario_id = f"{scenario.scenario_id}-baseline"
    return CleanupScenario(
        scenario_id=scenario_id,
        task=scenario.task,
        seed=scenario.seed,
        objects=scenario.objects,
        receptacles=scenario.receptacles,
        private_manifest=PrivateScoringManifest(
            scenario_id=scenario_id,
            targets=(),
            success_threshold=0,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
