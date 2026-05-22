from __future__ import annotations

import copy
import html
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from roboclaws.molmo_cleanup.agibot_sdk_runner import BLOCKED_MANIPULATION_TOOLS
from roboclaws.molmo_cleanup.backend_contract import CleanupBackendSession
from roboclaws.molmo_cleanup.nav2_adapter import BLOCKED_CAPABILITY_PROVENANCE
from roboclaws.molmo_cleanup.profiles import MOLMOSPACES_SIM_BACKEND
from roboclaws.molmo_cleanup.realworld_contract import (
    REALWORLD_CONTRACT,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    RealWorldCleanupContract,
)
from roboclaws.molmo_cleanup.report import (
    render_cleanup_report,
    write_state_snapshot,
    write_trace_jsonl,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.subprocess_backend import MolmoSpacesSubprocessBackend
from roboclaws.molmo_cleanup.types import CleanupScenario

REHEARSAL_SCHEMA = "molmospaces_agibot_contract_rehearsal_v1"
CONFIDENCE_LAYER = "MolmoSpaces Agibot Contract Rehearsal"
EXECUTION_BACKEND = MOLMOSPACES_SIM_BACKEND
NAVIGATION_BACKEND = MOLMOSPACES_SIM_BACKEND
RUNTIME_FIXTURE = "fixture"
RUNTIME_MOLMOSPACES_SUBPROCESS = "molmospaces-subprocess"
NAVIGATION_PROVENANCE = "agibot_shaped_molmospaces_sim_normal_navi"
OBSERVATION_PROVENANCE = "agibot_shaped_molmospaces_sim_policy_observation"
AGIBOT_SHAPED_SIM_BACKEND = "agibot_shaped_molmospaces_sim_backend"


def run_molmospaces_agibot_contract_rehearsal(
    *,
    run_dir: Path,
    seed: int = 7,
    generated_mess_count: int = 5,
    runtime: str = RUNTIME_FIXTURE,
    waypoint_id: str | None = None,
    molmospaces_python: Path | None = None,
    include_robot: bool = False,
    robot_name: str = "rby1m",
) -> dict[str, Any]:
    """Run the Agibot-shaped cleanup contract against simulated MolmoSpaces semantics."""

    if runtime not in {RUNTIME_FIXTURE, RUNTIME_MOLMOSPACES_SUBPROCESS}:
        expected = f"{RUNTIME_FIXTURE}|{RUNTIME_MOLMOSPACES_SUBPROCESS}"
        raise ValueError(f"unsupported rehearsal runtime {runtime!r} (expected {expected})")

    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.time()
    trace_events: list[dict[str, Any]] = []
    policy_events: list[dict[str, Any]] = []
    backend_instance: MolmoSpacesSubprocessBackend | None = None

    try:
        if runtime == RUNTIME_MOLMOSPACES_SUBPROCESS:
            backend_instance = MolmoSpacesSubprocessBackend(
                run_dir=run_dir,
                seed=seed,
                python_executable=molmospaces_python,
                include_robot=include_robot,
                robot_name=robot_name,
                generated_mess_count=generated_mess_count,
            )
            scenario = backend_instance.scenario
            base_contract = CleanupBackendSession(scenario, backend=backend_instance)
        else:
            scenario = build_cleanup_scenario(seed=seed)
            base_contract = CleanupBackendSession(scenario)

        contract = RealWorldCleanupContract(
            base_contract,
            task_prompt=scenario.task,
            fixture_hint_mode="exact_fixtures",
            perception_mode=VISIBLE_OBJECT_DETECTIONS_MODE,
        )

        before_snapshot = _write_snapshot(
            runtime=runtime,
            contract=base_contract,
            scenario=scenario,
            output_path=run_dir / "before.png",
            title="Before MolmoSpaces Agibot contract rehearsal",
        )

        metric_map = _agibot_shaped_metric_map(contract.metric_map(), seed=seed)
        fixture_hints = _agibot_shaped_fixture_hints(contract.fixture_hints())
        preflight = _write_preflight_artifacts(
            run_dir=run_dir,
            scenario=scenario,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
            runtime=runtime,
            seed=seed,
            generated_mess_count=generated_mess_count,
            backend_instance=backend_instance,
        )
        preflight_agent_view = _load_json(preflight["agent_view"])
        waypoint_sequence = _load_json(preflight["waypoint_sequence"])
        metric_map = dict(preflight_agent_view["metric_map"])
        fixture_hints = dict(preflight_agent_view["fixture_hints"])
        subphase_reports = [
            _write_stage_artifact(
                run_dir=run_dir,
                stage_dir=run_dir / "subphases" / "01-agent-view",
                stage="agent_view_export",
                status="ok",
                ok=True,
                tool_response=metric_map,
                artifacts={
                    "metric_map": _relpath(preflight["metric_map"], run_dir),
                    "fixture_hints": _relpath(preflight["fixture_hints"], run_dir),
                    "agent_view": _relpath(preflight["agent_view"], run_dir),
                    "scene_identity": _relpath(preflight["scene_identity"], run_dir),
                    "map_preview": _relpath(preflight["map_preview"], run_dir),
                    "waypoint_sequence": _relpath(preflight["waypoint_sequence"], run_dir),
                    "runner_task_input": _relpath(preflight["runner_task_input"], run_dir),
                },
                note=(
                    "Generated Agibot-shaped preflight artifacts from the simulated "
                    "MolmoSpaces cleanup scene. No real Agibot map or GDK artifact "
                    "was consumed."
                ),
            )
        ]
        _record(trace_events, started_at, "metric_map", {}, metric_map)
        _record(trace_events, started_at, "fixture_hints", {}, fixture_hints)

        runtime_dir = run_dir / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        selected_waypoint_id = waypoint_id or _first_waypoint_id_from_sequence(waypoint_sequence)

        observation_image = _write_snapshot(
            runtime=runtime,
            contract=base_contract,
            scenario=scenario,
            output_path=runtime_dir / "policy_observation.png",
            title="Simulated policy observation",
        )
        observation = _simulated_observation(
            contract.observe(),
            observation_image=observation_image,
            run_dir=run_dir,
            runtime=runtime,
            metric_map=metric_map,
            waypoint_id=selected_waypoint_id,
        )
        (runtime_dir / "observation.json").write_text(
            json.dumps(observation, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        subphase_reports.append(
            _write_stage_artifact(
                run_dir=run_dir,
                stage_dir=run_dir / "subphases" / "02-observe",
                stage="observe",
                status="ok",
                ok=True,
                tool_response=observation,
                artifacts={"observation": "runtime/observation.json"},
                note=(
                    "Simulated policy-camera observe evidence. This validates the "
                    "public observe result shape, not a head_color GDK camera capture."
                ),
            )
        )
        policy_events.append(_policy_event(len(policy_events), observation, "observe"))
        _record(trace_events, started_at, "observe", {"label": "pre_navigation"}, observation)

        navigation = _simulated_navigation(
            contract.navigate_to_waypoint(selected_waypoint_id),
            metric_map=metric_map,
            waypoint_id=selected_waypoint_id,
            runtime=runtime,
        )
        (runtime_dir / "navigation.json").write_text(
            json.dumps(navigation, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        subphase_reports.append(
            _write_stage_artifact(
                run_dir=run_dir,
                stage_dir=run_dir / "subphases" / "03-navigate-waypoint",
                stage="navigate_waypoint",
                status="ok",
                ok=True,
                tool_response=navigation,
                artifacts={"navigation": "runtime/navigation.json"},
                note=(
                    "Simulated waypoint navigation evidence with Agibot-shaped "
                    "runner fields and MolmoSpaces simulation provenance."
                ),
            )
        )
        policy_events.append(_policy_event(len(policy_events), navigation, "navigate_waypoint"))
        _record(
            trace_events,
            started_at,
            "navigate_to_waypoint",
            {"waypoint_id": selected_waypoint_id},
            navigation,
        )

        manipulation_results = []
        for tool in BLOCKED_MANIPULATION_TOOLS:
            result = _blocked_manipulation(tool)
            manipulation_results.append(result)
            policy_events.append(_policy_event(len(policy_events), result, "blocked_manipulation"))
            _record(trace_events, started_at, tool, {}, result)
        subphase_reports.append(
            _write_stage_artifact(
                run_dir=run_dir,
                stage_dir=run_dir / "subphases" / "04-blocked-manipulation",
                stage="blocked_manipulation",
                status="blocked_capability",
                ok=False,
                tool_response={"blocked_tools": manipulation_results},
                artifacts={"blocked_manipulation": "runtime/blocked_manipulation.json"},
                note=(
                    "Manipulation tools are intentionally visible but blocked in this "
                    "contract rehearsal."
                ),
            )
        )
        (runtime_dir / "blocked_manipulation.json").write_text(
            json.dumps(manipulation_results, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        after_snapshot = _write_snapshot(
            runtime=runtime,
            contract=base_contract,
            scenario=scenario,
            output_path=run_dir / "after.png",
            title="After MolmoSpaces Agibot contract rehearsal",
        )

        top_level_agent_view = _agent_view_with_runtime_observation(
            metric_map=metric_map,
            fixture_hints=fixture_hints,
            observation=observation,
        )
        runtime_export = _runtime_export(
            observation=observation,
            navigation=navigation,
            manipulation_results=manipulation_results,
            subphase_reports=subphase_reports,
            runtime=runtime,
        )
        (runtime_dir / "runtime_export.json").write_text(
            json.dumps(runtime_export, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (run_dir / "agent_view.json").write_text(
            json.dumps(top_level_agent_view, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        trace_path = run_dir / "trace.jsonl"
        write_trace_jsonl(trace_path, trace_events)

        run_result = _run_result(
            run_dir=run_dir,
            scenario=scenario,
            runtime=runtime,
            seed=seed,
            generated_mess_count=generated_mess_count,
            started_at=started_at,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
            observation=observation,
            navigation=navigation,
            manipulation_results=manipulation_results,
            agent_view=top_level_agent_view,
            runtime_export=runtime_export,
            subphase_reports=subphase_reports,
            trace_path=trace_path,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            policy_events=policy_events,
            backend_instance=backend_instance,
            scene_identity_path=preflight["scene_identity"],
            map_preview_path=preflight["map_preview"],
        )
        (run_dir / "run_result.json").write_text(
            json.dumps(run_result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        render_cleanup_report(
            run_dir=run_dir,
            scenario=scenario,
            run_result=run_result,
            trace_events=trace_events,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            robot_view_steps=[],
        )
        return run_result
    finally:
        if backend_instance is not None:
            backend_instance.close()


def _agibot_shaped_metric_map(metric_map: dict[str, Any], *, seed: int) -> dict[str, Any]:
    payload = copy.deepcopy(metric_map)
    payload["map_id"] = f"molmospaces-agibot-contract-rehearsal-{seed}"
    payload["map_version"] = "molmospaces-sim-agibot-shaped-v1"
    payload["execution_backend"] = EXECUTION_BACKEND
    payload["simulated"] = True
    payload["physical_robot"] = False
    payload["public_contract_note"] = (
        "Agibot-shaped preflight metric_map generated from a MolmoSpaces cleanup "
        "scene. This is simulated contract-shape evidence, not a real Agibot map "
        "fetch or GDK current-map export."
    )
    for waypoint in payload.get("inspection_waypoints") or []:
        waypoint["reachability_status"] = "verified"
        waypoint["waypoint_source"] = "molmospaces_sim_agibot_shaped_preflight"
        waypoint["verification"] = {
            "schema": "agibot_shaped_molmospaces_waypoint_verification_v1",
            "reachability_status": "verified",
            "navigation_backend": NAVIGATION_BACKEND,
            "primitive_provenance": NAVIGATION_PROVENANCE,
            "simulated": True,
            "physical_robot": False,
        }
    return payload


def _agibot_shaped_fixture_hints(fixture_hints: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(fixture_hints)
    payload["fixture_hint_mode"] = "molmospaces_sim_static_fixture_map"
    payload["execution_backend"] = EXECUTION_BACKEND
    payload["simulated"] = True
    payload["physical_robot"] = False
    payload["public_contract_note"] = (
        "Agibot-shaped fixture_hints generated from public MolmoSpaces static "
        "fixture semantics. No private cleanup target truth or real GDK map state "
        "is exposed."
    )
    return payload


def _write_preflight_artifacts(
    *,
    run_dir: Path,
    scenario: CleanupScenario,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    runtime: str,
    seed: int,
    generated_mess_count: int,
    backend_instance: MolmoSpacesSubprocessBackend | None,
) -> dict[str, Path]:
    preflight_dir = run_dir / "preflight"
    preflight_dir.mkdir(parents=True, exist_ok=True)
    scene_identity = _scene_identity(
        scenario=scenario,
        runtime=runtime,
        seed=seed,
        generated_mess_count=generated_mess_count,
        backend_instance=backend_instance,
    )
    map_preview = _write_metric_map_preview(
        output_path=preflight_dir / "molmospaces_metric_map.png",
        metric_map=metric_map,
        fixture_hints=fixture_hints,
        scene_identity=scene_identity,
    )
    agent_view = {
        "schema": "agibot_shaped_agent_view_v1",
        "metric_map": metric_map,
        "fixture_hints": fixture_hints,
        "observed_objects": [],
        "raw_fpv_observations": [],
        "perception_mode": "robot_policy_camera",
        "structured_detections_available": False,
        "policy_view": {"policy_observation_camera": "molmospaces_sim_policy_camera"},
        "cleanup_worklist": {"schema": "cleanup_worklist_v1", "objects": []},
        "forbidden_private_fields_absent": True,
        "simulated": True,
        "physical_robot": False,
        "execution_backend": EXECUTION_BACKEND,
    }
    waypoint_sequence = {
        "schema": "agibot_shaped_waypoint_sequence_v1",
        "simulated": True,
        "physical_robot": False,
        "execution_backend": EXECUTION_BACKEND,
        "waypoints": [
            {
                "waypoint_id": str(item.get("waypoint_id") or ""),
                "room_id": str(item.get("room_id") or ""),
                "fixture_id": str(item.get("fixture_id") or ""),
                "purpose": str(item.get("purpose") or ""),
                "navigation_backend": NAVIGATION_BACKEND,
                "primitive_provenance": NAVIGATION_PROVENANCE,
            }
            for item in metric_map.get("inspection_waypoints") or []
        ],
    }
    runner_task_input = {
        "schema": "agibot_shaped_cleanup_runner_task_input_v1",
        "contract": REALWORLD_CONTRACT,
        "cleanup_profile": "real_robot_cleanup_v1",
        "task_prompt": scenario.task,
        "seed": seed,
        "requested_generated_mess_count": generated_mess_count,
        "runtime": runtime,
        "simulated": True,
        "physical_robot": False,
        "execution_backend": EXECUTION_BACKEND,
        "public_tool_sequence": [
            "metric_map",
            "fixture_hints",
            "observe",
            "navigate_to_waypoint",
            *BLOCKED_MANIPULATION_TOOLS,
        ],
        "stage_mapping": {
            "agent_view_export": ["metric_map", "fixture_hints"],
            "observe": ["observe"],
            "navigate_waypoint": ["navigate_to_waypoint"],
            "blocked_manipulation": list(BLOCKED_MANIPULATION_TOOLS),
        },
        "evidence_note": (
            "This input is Agibot-shaped for runner-contract rehearsal, but it is "
            "not a real Agibot SDK task input and does not enable GDK movement."
        ),
    }
    paths = {
        "metric_map": preflight_dir / "metric_map.json",
        "fixture_hints": preflight_dir / "fixture_hints.json",
        "agent_view": preflight_dir / "agent_view.json",
        "scene_identity": preflight_dir / "scene_identity.json",
        "map_preview": map_preview,
        "waypoint_sequence": preflight_dir / "waypoint_sequence.json",
        "runner_task_input": preflight_dir / "runner_task_input.json",
    }
    values = {
        "metric_map": metric_map,
        "fixture_hints": fixture_hints,
        "agent_view": agent_view,
        "scene_identity": scene_identity,
        "waypoint_sequence": waypoint_sequence,
        "runner_task_input": runner_task_input,
    }
    for key, path in paths.items():
        if key == "map_preview":
            continue
        path.write_text(json.dumps(values[key], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return paths


def _scene_identity(
    *,
    scenario: CleanupScenario,
    runtime: str,
    seed: int,
    generated_mess_count: int,
    backend_instance: MolmoSpacesSubprocessBackend | None,
) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "schema": "molmospaces_agibot_rehearsal_scene_identity_v1",
        "scenario_id": scenario.scenario_id,
        "task_prompt": scenario.task,
        "seed": seed,
        "requested_generated_mess_count": generated_mess_count,
        "runtime": runtime,
        "execution_backend": EXECUTION_BACKEND,
        "navigation_backend": NAVIGATION_BACKEND,
        "simulated": True,
        "physical_robot": False,
        "scene_source": "deterministic_fixture_projection"
        if runtime == RUNTIME_FIXTURE
        else "molmospaces_subprocess",
        "scene_source_note": (
            "CI-safe fixture projection of the MolmoSpaces cleanup contract. "
            "No MuJoCo scene_xml was loaded in this run."
            if runtime == RUNTIME_FIXTURE
            else "Live MolmoSpaces subprocess scene evidence from the optional runtime."
        ),
        "object_count": len(scenario.objects),
        "fixture_count": len(scenario.receptacles),
    }
    if backend_instance is not None:
        identity.update(
            {
                "scene_xml": backend_instance.scene_xml,
                "molmospaces_runtime": backend_instance.runtime,
                "model_stats": backend_instance.model_stats,
                "metadata_object_count": backend_instance.metadata_object_count,
                "actual_generated_mess_count": backend_instance.generated_mess_count,
                "robot": backend_instance.robot,
            }
        )
    return identity


def _write_metric_map_preview(
    *,
    output_path: Path,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    scene_identity: dict[str, Any],
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1080, 620
    margin = 58
    image = Image.new("RGB", (width, height), (246, 248, 251))
    draw = ImageDraw.Draw(image)
    rooms = [room for room in metric_map.get("rooms") or [] if isinstance(room, dict)]
    fixtures = _fixtures(fixture_hints)
    waypoints = [item for item in metric_map.get("inspection_waypoints") or []]
    bounds = _map_bounds(rooms=rooms, fixtures=fixtures, waypoints=waypoints)

    def xy(x_value: Any, y_value: Any) -> tuple[float, float]:
        x = float(x_value)
        y = float(y_value)
        span_x = max(bounds["max_x"] - bounds["min_x"], 1.0)
        span_y = max(bounds["max_y"] - bounds["min_y"], 1.0)
        px = margin + ((x - bounds["min_x"]) / span_x) * (width - margin * 2)
        py = height - margin - ((y - bounds["min_y"]) / span_y) * (height - margin * 2)
        return px, py

    draw.text((24, 20), "MolmoSpaces Agibot Contract Rehearsal Map", fill=(26, 36, 54))
    subtitle = (
        f"runtime={scene_identity.get('runtime')} | scenario={scene_identity.get('scenario_id')} | "
        f"source={scene_identity.get('scene_source')}"
    )
    draw.text((24, 42), subtitle, fill=(84, 96, 116))

    palette = [
        (222, 237, 253),
        (227, 242, 230),
        (250, 238, 218),
        (238, 231, 248),
        (244, 229, 232),
    ]
    for index, room in enumerate(rooms):
        polygon = room.get("polygon") or []
        points = [xy(point["x"], point["y"]) for point in polygon if {"x", "y"} <= set(point)]
        if len(points) < 3:
            continue
        fill = palette[index % len(palette)]
        draw.polygon(points, fill=fill, outline=(112, 128, 149))
        label_x = sum(point[0] for point in points) / len(points)
        label_y = sum(point[1] for point in points) / len(points)
        draw.text(
            (label_x - 36, label_y - 8),
            str(room.get("room_label") or room.get("room_id") or "room"),
            fill=(39, 52, 74),
        )

    for fixture in fixtures:
        pose = fixture.get("pose") or {}
        if "x" not in pose or "y" not in pose:
            continue
        x, y = xy(pose["x"], pose["y"])
        draw.rounded_rectangle((x - 8, y - 8, x + 8, y + 8), radius=3, fill=(48, 86, 154))
        draw.text(
            (x + 10, y - 7),
            str(fixture.get("name") or fixture.get("fixture_id")),
            fill=(29, 44, 68),
        )

    for waypoint in waypoints:
        if "x" not in waypoint or "y" not in waypoint:
            continue
        x, y = xy(waypoint["x"], waypoint["y"])
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(210, 90, 55))
        draw.text((x + 8, y + 4), str(waypoint.get("waypoint_id") or ""), fill=(110, 57, 42))

    legend_y = height - 34
    draw.rounded_rectangle((24, legend_y - 8, 40, legend_y + 8), radius=3, fill=(48, 86, 154))
    draw.text((48, legend_y - 8), "fixture", fill=(65, 76, 96))
    draw.ellipse((126, legend_y - 8, 142, legend_y + 8), fill=(210, 90, 55))
    draw.text((150, legend_y - 8), "inspection waypoint", fill=(65, 76, 96))
    image.save(output_path, format="PNG")
    return output_path


def _map_bounds(
    *,
    rooms: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []
    for room in rooms:
        for point in room.get("polygon") or []:
            if "x" in point and "y" in point:
                xs.append(float(point["x"]))
                ys.append(float(point["y"]))
    for fixture in fixtures:
        pose = fixture.get("pose") or {}
        if "x" in pose and "y" in pose:
            xs.append(float(pose["x"]))
            ys.append(float(pose["y"]))
    for waypoint in waypoints:
        if "x" in waypoint and "y" in waypoint:
            xs.append(float(waypoint["x"]))
            ys.append(float(waypoint["y"]))
    if not xs or not ys:
        return {"min_x": 0.0, "max_x": 1.0, "min_y": 0.0, "max_y": 1.0}
    pad_x = max((max(xs) - min(xs)) * 0.08, 0.5)
    pad_y = max((max(ys) - min(ys)) * 0.18, 0.5)
    return {
        "min_x": min(xs) - pad_x,
        "max_x": max(xs) + pad_x,
        "min_y": min(ys) - pad_y,
        "max_y": max(ys) + pad_y,
    }


def _simulated_observation(
    response: dict[str, Any],
    *,
    observation_image: Path,
    run_dir: Path,
    runtime: str,
    metric_map: dict[str, Any],
    waypoint_id: str,
) -> dict[str, Any]:
    detections = list(response.get("visible_object_detections") or [])
    waypoint = _waypoint_by_id(metric_map, waypoint_id) or {}
    room_id = str(response.get("room_id") or waypoint.get("room_id") or "")
    return {
        "ok": True,
        "tool": "observe",
        "status": "ok",
        "contract": REALWORLD_CONTRACT,
        "observation_id": f"molmospaces_sim_observe_{int(time.time_ns())}",
        "room_id": room_id,
        "waypoint_id": waypoint_id,
        "policy_observation_camera": "molmospaces_sim_policy_camera",
        "primitive_provenance": OBSERVATION_PROVENANCE,
        "execution_backend": EXECUTION_BACKEND,
        "simulated": True,
        "physical_robot": False,
        "runtime": runtime,
        "camera_artifact": _relpath(observation_image, run_dir),
        "raw_fpv_observation": {
            "observation_id": "molmospaces_sim_policy_observation",
            "room_id": room_id,
            "waypoint_id": waypoint_id,
            "artifact_status": "simulated_policy_observation",
            "image_artifacts": {"fpv": _relpath(observation_image, run_dir)},
            "camera_offset": {"yaw_delta_deg": 0, "pitch_delta_deg": 0},
        },
        "visible_object_detections": detections,
        "private_target_truth_included": False,
        "physical_cleanup_ready": False,
        "public_contract_note": (
            "Simulated policy observation from MolmoSpaces contract rehearsal. "
            "This is not an Agibot head_color camera capture."
        ),
    }


def _simulated_navigation(
    response: dict[str, Any],
    *,
    metric_map: dict[str, Any],
    waypoint_id: str,
    runtime: str,
) -> dict[str, Any]:
    waypoint = _waypoint_by_id(metric_map, waypoint_id) or {}
    ok = bool(response.get("ok", True))
    return {
        "ok": ok,
        "tool": "navigate_to_waypoint",
        "status": "ok" if ok else "blocked_capability",
        "contract": REALWORLD_CONTRACT,
        "waypoint_id": waypoint_id,
        "navigation_backend": NAVIGATION_BACKEND,
        "execution_backend": EXECUTION_BACKEND,
        "primitive_provenance": NAVIGATION_PROVENANCE if ok else BLOCKED_CAPABILITY_PROVENANCE,
        "navigation_status": "succeeded" if ok else "blocked",
        "goal_source": "inspection_waypoint",
        "goal_pose": {
            "frame_id": waypoint.get("frame_id", metric_map.get("frame_id", "map")),
            "x": waypoint.get("x", 0.0),
            "y": waypoint.get("y", 0.0),
            "yaw": waypoint.get("yaw", 0.0),
        },
        "current_pose": {
            "frame_id": waypoint.get("frame_id", metric_map.get("frame_id", "map")),
            "x": waypoint.get("x", 0.0),
            "y": waypoint.get("y", 0.0),
            "yaw": waypoint.get("yaw", 0.0),
        },
        "pose_source": "molmospaces_sim_waypoint_arrival",
        "route_validation": response.get("route_validation", {"ok": ok}),
        "simulated": True,
        "physical_robot": False,
        "runtime": runtime,
        "physical_cleanup_ready": False,
        "manipulation_ready": False,
        "public_contract_note": (
            "Simulated waypoint navigation through the Agibot-shaped runner "
            "contract. This is not Pnc.normal_navi or physical arrival evidence."
        ),
    }


def _blocked_manipulation(tool: str) -> dict[str, Any]:
    return {
        "ok": False,
        "tool": tool,
        "status": "blocked_capability",
        "contract": REALWORLD_CONTRACT,
        "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
        "error_reason": "blocked_capability",
        "failure_type": "simulated_contract_rehearsal_manipulation_blocked",
        "backend_error_summary": (
            "MolmoSpaces Agibot Contract Rehearsal validates observe and waypoint "
            "navigation only; manipulation remains blocked."
        ),
        "execution_backend": EXECUTION_BACKEND,
        "simulated": True,
        "physical_robot": False,
        "physical_cleanup_ready": False,
        "manipulation_ready": False,
    }


def _agent_view_with_runtime_observation(
    *,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    detections = [
        {
            "object_id": str(item.get("object_id") or ""),
            "category": str(item.get("category") or ""),
            "current_room_id": str(item.get("room_id") or observation.get("room_id") or ""),
            "support_estimate": item.get("support_estimate") or {},
            "source_observation_id": observation.get("observation_id", ""),
        }
        for item in observation.get("visible_object_detections") or []
    ]
    return {
        "schema": "agibot_shaped_agent_view_v1",
        "metric_map": metric_map,
        "fixture_hints": fixture_hints,
        "observed_objects": detections,
        "raw_fpv_observations": [observation["raw_fpv_observation"]],
        "perception_mode": "robot_policy_camera",
        "structured_detections_available": True,
        "policy_view": {"policy_observation_camera": "molmospaces_sim_policy_camera"},
        "cleanup_worklist": {"schema": "cleanup_worklist_v1", "objects": []},
        "forbidden_private_fields_absent": True,
        "simulated": True,
        "physical_robot": False,
        "execution_backend": EXECUTION_BACKEND,
    }


def _runtime_export(
    *,
    observation: dict[str, Any],
    navigation: dict[str, Any],
    manipulation_results: list[dict[str, Any]],
    subphase_reports: list[dict[str, Any]],
    runtime: str,
) -> dict[str, Any]:
    return {
        "schema": "agibot_shaped_runtime_export_v1",
        "confidence_layer": CONFIDENCE_LAYER,
        "runtime": runtime,
        "simulated": True,
        "physical_robot": False,
        "execution_backend": EXECUTION_BACKEND,
        "navigation_backend": NAVIGATION_BACKEND,
        "stages": ["agent_view_export", "observe", "navigate_waypoint", "blocked_manipulation"],
        "observation": observation,
        "navigation": navigation,
        "blocked_manipulation_results": manipulation_results,
        "subphase_reports": subphase_reports,
        "gdk_imported_by_roboclaws": False,
    }


def _run_result(
    *,
    run_dir: Path,
    scenario: CleanupScenario,
    runtime: str,
    seed: int,
    generated_mess_count: int,
    started_at: float,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    observation: dict[str, Any],
    navigation: dict[str, Any],
    manipulation_results: list[dict[str, Any]],
    agent_view: dict[str, Any],
    runtime_export: dict[str, Any],
    subphase_reports: list[dict[str, Any]],
    trace_path: Path,
    before_snapshot: Path,
    after_snapshot: Path,
    policy_events: list[dict[str, Any]],
    backend_instance: MolmoSpacesSubprocessBackend | None,
    scene_identity_path: Path,
    map_preview_path: Path,
) -> dict[str, Any]:
    score = _empty_score()
    readiness = _readiness_payload(
        metric_map=metric_map,
        fixture_hints=fixture_hints,
        observation=observation,
        navigation=navigation,
        manipulation_results=manipulation_results,
        runtime=runtime,
    )
    run_result: dict[str, Any] = {
        "schema": REHEARSAL_SCHEMA,
        "report_eyebrow": "Agibot-shaped simulated evidence",
        "report_title": CONFIDENCE_LAYER,
        "confidence_layer": CONFIDENCE_LAYER,
        "confidence_layer_summary": (
            "Validates real_robot_cleanup_v1 contract shape, Agibot-shaped stage "
            "sequencing, and report evidence plumbing through a simulated "
            "MolmoSpaces backend. It is not Agibot Map Visual Dry Run, not Agibot "
            "SDK Dry Run, not semantic cleanup mock evidence, and not real Agibot "
            "GDK execution."
        ),
        "next_confidence_layer": "Optional real Agibot G2 validation",
        "contract": REALWORLD_CONTRACT,
        "cleanup_profile": "real_robot_cleanup_v1",
        "backend": AGIBOT_SHAPED_SIM_BACKEND,
        "backend_variant": EXECUTION_BACKEND,
        "execution_backend": EXECUTION_BACKEND,
        "navigation_backend": NAVIGATION_BACKEND,
        "runtime": runtime,
        "simulated": True,
        "physical_robot": False,
        "agent_driven": False,
        "mcp_server": "roboclaws_real_robot_cleanup_v1_agibot_shaped_sim",
        "scenario_id": scenario.scenario_id,
        "task_prompt": scenario.task,
        "seed": seed,
        "cleanup_status": "molmospaces_agibot_contract_rehearsal_complete",
        "final_status": "molmospaces_agibot_contract_rehearsal_complete",
        "terminate_reason": "contract rehearsal complete",
        "primitive_provenance": NAVIGATION_PROVENANCE,
        "generated_mess_count": 0,
        "requested_generated_mess_count": generated_mess_count,
        "sweep_coverage_rate": 1.0 if observation.get("ok") else 0.0,
        "disturbance_count": 0,
        "score": score,
        "private_evaluation": {
            "generated_mess_count": 0,
            "generated_mess_set": [],
            "acceptable_destination_sets": {},
            "mess_restoration_rate": 0.0,
            "sweep_coverage_rate": 1.0 if observation.get("ok") else 0.0,
            "disturbance_count": 0,
            "public_contract_note": ("Contract rehearsal does not run private cleanup scoring."),
        },
        "agent_view": agent_view,
        "raw_fpv_observations": agent_view.get("raw_fpv_observations", []),
        "cleanup_policy_trace": {
            "schema": "cleanup_policy_trace_v1",
            "waypoint_source": "agibot_shaped_molmospaces_sim_preflight",
            "loop_style": "molmospaces_agibot_contract_rehearsal",
            "total_waypoints": len(metric_map.get("inspection_waypoints") or []),
            "observed_waypoint_count": 1 if observation.get("ok") else 0,
            "scan_observe_count": 1,
            "cleanup_action_count": 0,
            "placed_object_count": 0,
            "post_place_observe_count": 0,
            "post_place_observe_complete": True,
            "first_cleanup_before_full_survey": False,
            "events": policy_events,
            "public_contract_note": (
                "This trace validates observe and waypoint navigation sequencing only. "
                "Manipulation tools remain blocked_capability."
            ),
        },
        "semantic_substeps": [],
        "real_robot_readiness": readiness,
        "agibot_sdk_runner": {
            "schema": "agibot_shaped_sim_runner_boundary_v1",
            "rehearsal_kind": "molmospaces_agibot_contract_rehearsal",
            "backend_variant": EXECUTION_BACKEND,
            "runtime": runtime,
            "simulated": True,
            "physical_robot": False,
            "execution_backend": EXECUTION_BACKEND,
            "navigation_backend": NAVIGATION_BACKEND,
            "real_movement_enabled": False,
            "next_confidence_layer": "Optional real Agibot G2 validation",
            "subphase_reports": subphase_reports,
            "gdk_imported_by_roboclaws": False,
            "public_tool_boundary": [
                "metric_map",
                "fixture_hints",
                "observe",
                "navigate_to_waypoint",
                *BLOCKED_MANIPULATION_TOOLS,
                "done",
            ],
        },
        "molmospaces_agibot_contract_rehearsal": {
            "schema": REHEARSAL_SCHEMA,
            "confidence_layer": CONFIDENCE_LAYER,
            "runtime": runtime,
            "simulated": True,
            "physical_robot": False,
            "execution_backend": EXECUTION_BACKEND,
            "navigation_backend": NAVIGATION_BACKEND,
            "navigation_primitive_provenance": NAVIGATION_PROVENANCE,
            "observation_primitive_provenance": OBSERVATION_PROVENANCE,
            "agent_view_preflight": "preflight/agent_view.json",
            "scene_identity": _relpath(scene_identity_path, run_dir),
            "map_preview": _relpath(map_preview_path, run_dir),
            "waypoint_sequence": "preflight/waypoint_sequence.json",
            "runner_task_input": "preflight/runner_task_input.json",
            "runtime_export": "runtime/runtime_export.json",
            "blocked_manipulation_tools": list(BLOCKED_MANIPULATION_TOOLS),
            "layer_distinction": [
                "not Agibot Map Visual Dry Run",
                "not Agibot SDK Dry Run",
                "not semantic cleanup mock evidence",
                "not real Agibot GDK execution",
            ],
        },
        "manipulation_evidence": {
            "schema": "molmospaces_agibot_contract_rehearsal_manipulation_block_v1",
            "status": "blocked_capability",
            "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
            "planner_backed": False,
            "strict_proof_eligible": False,
            "api_semantic_state_edits": 0,
            "evidence_note": (
                "MolmoSpaces Agibot Contract Rehearsal intentionally blocks "
                "pick/place/open/close manipulation."
            ),
            "blockers": [str(item["tool"]) for item in manipulation_results],
            "strict_proof_requirements": [
                "planner-backed manipulation binding",
                "real hardware safety approval",
                "Agibot manipulation validation",
            ],
        },
        "artifacts": {
            "run_result": "run_result.json",
            "trace": _relpath(trace_path, run_dir),
            "before_snapshot": _relpath(before_snapshot, run_dir),
            "after_snapshot": _relpath(after_snapshot, run_dir),
            "agent_view": "agent_view.json",
            "preflight": "preflight",
            "molmospaces_scene_identity": _relpath(scene_identity_path, run_dir),
            "molmospaces_metric_map_preview": _relpath(map_preview_path, run_dir),
            "runtime_export": "runtime/runtime_export.json",
            "agibot_shaped_subphases": "subphases",
            "report": "report.html",
        },
        "runtime_timing": {
            "total_elapsed_s": time.time() - started_at,
            "tool_handler_s": 0.0,
            "robot_view_capture_s": 0.0,
            "between_tool_gap_s": 0.0,
            "tool_call_count": len(trace_path.read_text(encoding="utf-8").splitlines()) // 2
            if trace_path.is_file()
            else 0,
        },
    }
    run_result["molmospaces_scene"] = _load_json(scene_identity_path)
    if backend_instance is not None:
        run_result["molmospaces_runtime"] = {
            "python_executable": str(backend_instance.python_executable),
            "runtime": backend_instance.runtime,
            "model_stats": backend_instance.model_stats,
            "scene_xml": backend_instance.scene_xml,
            "metadata_object_count": backend_instance.metadata_object_count,
            "requested_generated_mess_count": backend_instance.requested_generated_mess_count,
            "generated_mess_count": backend_instance.generated_mess_count,
        }
    return run_result


def _readiness_payload(
    *,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    observation: dict[str, Any],
    navigation: dict[str, Any],
    manipulation_results: list[dict[str, Any]],
    runtime: str,
) -> dict[str, Any]:
    all_manipulation_blocked = all(
        item.get("primitive_provenance") == BLOCKED_CAPABILITY_PROVENANCE
        for item in manipulation_results
    )
    complete = bool(observation.get("ok") and navigation.get("ok") and all_manipulation_blocked)
    return {
        "schema": "real_robot_readiness_v1",
        "status": "molmospaces_agibot_contract_rehearsal_complete"
        if complete
        else "molmospaces_agibot_contract_rehearsal_blocked",
        "real_robot_ready": False,
        "navigation_perception_ready": complete,
        "backend_variant": EXECUTION_BACKEND,
        "runtime": runtime,
        "simulated": True,
        "physical_robot": False,
        "movement_enabled": False,
        "map_bundle_schema": metric_map.get("schema", ""),
        "map_bundle_fields_present": _map_fields_present(metric_map),
        "pose_stamped_waypoints": _pose_stamped_waypoints_present(metric_map),
        "static_fixture_semantic_map": (
            fixture_hints.get("schema") == "static_fixture_semantic_map_v1"
            and fixture_hints.get("contains_runtime_observations") is False
        ),
        "policy_view_chase_excluded": True,
        "report_only_simulation_view_count": 1,
        "report_only_simulation_view_label": "molmospaces_sim_policy_observation",
        "navigation_backend_summary": {NAVIGATION_BACKEND: 1},
        "pose_source_summary": {"molmospaces_sim_waypoint_arrival": 1},
        "semantic_navigation_only": False,
        "sim_costmap_route_validation": True,
        "physical_navigation_pilot": False,
        "physical_cleanup_ready": False,
        "inspection_waypoint_attempt_count": 1,
        "inspection_waypoint_total": len(metric_map.get("inspection_waypoints") or []),
        "fixture_preferred_waypoint_attempt_count": 0,
        "fixture_total": len(_fixtures(fixture_hints)),
        "reached_waypoint_count": 1 if navigation.get("ok") else 0,
        "observed_reached_waypoint_count": 1 if observation.get("ok") else 0,
        "observed_reached_waypoint_rate": 1.0 if complete else 0.0,
        "observed_waypoint_ids": [str(navigation.get("waypoint_id") or "")]
        if observation.get("ok")
        else [],
        "manipulation_blocked": all_manipulation_blocked,
        "blocked_capabilities": list(BLOCKED_MANIPULATION_TOOLS),
        "operator_run_enablement_gate": {
            "movement_enabled": False,
            "scope": "not_applicable_simulated_contract_rehearsal",
        },
        "public_contract_note": (
            "MolmoSpaces Agibot Contract Rehearsal validates public contract shape "
            "and Agibot-shaped evidence plumbing. It is simulated and is not real "
            "Agibot GDK execution."
        ),
    }


def _write_stage_artifact(
    *,
    run_dir: Path,
    stage_dir: Path,
    stage: str,
    status: str,
    ok: bool,
    tool_response: dict[str, Any],
    artifacts: dict[str, str],
    note: str,
) -> dict[str, Any]:
    stage_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": "agibot_shaped_sim_stage_result_v1",
        "stage": stage,
        "status": status,
        "ok": ok,
        "contract": REALWORLD_CONTRACT,
        "cleanup_profile": "real_robot_cleanup_v1",
        "backend": AGIBOT_SHAPED_SIM_BACKEND,
        "execution_backend": EXECUTION_BACKEND,
        "navigation_backend": NAVIGATION_BACKEND,
        "simulated": True,
        "physical_robot": False,
        "artifacts": artifacts,
        "tool_response": tool_response,
        "evidence_note": note,
        "gdk_imported_by_roboclaws": False,
    }
    (stage_dir / "run_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (stage_dir / "report.html").write_text(_stage_report_html(result), encoding="utf-8")
    return {
        "stage": stage,
        "status": status,
        "ok": ok,
        "report": _relpath(stage_dir / "report.html", run_dir),
        "run_result": _relpath(stage_dir / "run_result.json", run_dir),
    }


def _stage_report_html(result: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(key))}</td><td>{html.escape(str(value))}</td></tr>"
        for key, value in (result.get("artifacts") or {}).items()
    )
    stage_title = html.escape(str(result.get("stage", "stage")).replace("_", " ").title())
    status = html.escape(str(result.get("status", "")))
    execution_backend = html.escape(str(result.get("execution_backend", "")))
    simulated = html.escape(str(result.get("simulated", "")))
    physical_robot = html.escape(str(result.get("physical_robot", "")))
    note = html.escape(str(result.get("evidence_note", "")))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(str(result.get("stage", "stage")))}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #172033; }}
    .metric {{
      display: inline-block;
      margin: 0 12px 12px 0;
      padding: 10px 12px;
      border: 1px solid #d8dee9;
      border-radius: 6px;
    }}
    .metric span {{ display: block; color: #61708a; font-size: 12px; }}
    .metric strong {{ display: block; margin-top: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px; text-align: left; }}
  </style>
</head>
<body>
  <p>MolmoSpaces Agibot Contract Rehearsal</p>
  <h1>{stage_title}</h1>
  <div class="metric"><span>Status</span><strong>{status}</strong></div>
  <div class="metric"><span>Execution backend</span><strong>{execution_backend}</strong></div>
  <div class="metric"><span>Simulated</span><strong>{simulated}</strong></div>
  <div class="metric"><span>Physical robot</span><strong>{physical_robot}</strong></div>
  <p>{note}</p>
  <table><thead><tr><th>Artifact</th><th>Path</th></tr></thead><tbody>{rows}</tbody></table>
</body>
</html>
"""


def _write_snapshot(
    *,
    runtime: str,
    contract: CleanupBackendSession,
    scenario: CleanupScenario,
    output_path: Path,
    title: str,
) -> Path:
    if runtime == RUNTIME_MOLMOSPACES_SUBPROCESS:
        return contract.backend.write_snapshot(output_path, title=title)
    return write_state_snapshot(
        scenario,
        contract.backend.object_locations(),
        output_path,
        title=title,
    )


def _record(
    trace_events: list[dict[str, Any]],
    started_at: float,
    tool: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    trace_events.append(
        {
            "tool": tool,
            "event": "request",
            "arguments": arguments,
            "wallclock_elapsed": time.time() - started_at,
        }
    )
    trace_events.append(
        {
            "tool": tool,
            "event": "response",
            "response": response,
            "wallclock_elapsed": time.time() - started_at,
        }
    )


def _policy_event(index: int, response: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "index": index + 1,
        "tool": response.get("tool", ""),
        "role": role,
        "waypoint_id": response.get("waypoint_id", ""),
        "fixture_id": response.get("fixture_id", ""),
        "navigation_backend": response.get("navigation_backend", ""),
        "status": response.get("status") or response.get("navigation_status", ""),
    }


def _map_fields_present(metric_map: dict[str, Any]) -> bool:
    required = {
        "schema",
        "frame_id",
        "resolution_m",
        "origin",
        "width",
        "height",
        "rooms",
        "driveable_ways",
        "inspection_waypoints",
    }
    return required <= set(metric_map)


def _pose_stamped_waypoints_present(metric_map: dict[str, Any]) -> bool:
    waypoints = metric_map.get("inspection_waypoints") or []
    return bool(waypoints) and all(
        {"x", "y", "yaw", "waypoint_id"} <= set(item) for item in waypoints
    )


def _fixtures(fixture_hints: dict[str, Any]) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            if isinstance(fixture, dict):
                fixtures.append(fixture)
    return fixtures


def _first_waypoint_id(metric_map: dict[str, Any]) -> str:
    waypoints = metric_map.get("inspection_waypoints") or []
    if not waypoints:
        raise ValueError("MolmoSpaces Agibot rehearsal metric_map has no inspection waypoints")
    return str(waypoints[0].get("waypoint_id") or "")


def _first_waypoint_id_from_sequence(waypoint_sequence: dict[str, Any]) -> str:
    waypoints = waypoint_sequence.get("waypoints") or []
    if not waypoints:
        raise ValueError("MolmoSpaces Agibot rehearsal waypoint_sequence has no waypoints")
    return str(waypoints[0].get("waypoint_id") or "")


def _waypoint_by_id(metric_map: dict[str, Any], waypoint_id: str) -> dict[str, Any] | None:
    for waypoint in metric_map.get("inspection_waypoints") or []:
        if str(waypoint.get("waypoint_id") or "") == waypoint_id:
            return waypoint
    return None


def _empty_score() -> dict[str, Any]:
    return {
        "restored_count": 0,
        "total_targets": 0,
        "object_results": [],
        "semantic_acceptability": {
            "accepted_count": 0,
            "total_targets": 0,
            "acceptance_rate": 0.0,
            "counts": {},
        },
    }


def _relpath(path: Path | str, root: Path) -> str:
    path = Path(path)
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data
