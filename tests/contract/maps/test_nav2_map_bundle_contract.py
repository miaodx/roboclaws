from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.realworld_contract import RealWorldCleanupContract
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.maps.bundle import (
    static_landmarks_from_fixture_projection,
    validate_nav2_map_bundle,
    write_nav2_map_bundle,
)
from roboclaws.maps.project import metric_map_from_bundle, static_landmarks_from_bundle
from roboclaws.maps.route import SIM_COSTMAP_PLANNER, validate_metric_map_route

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPORTER_PATH = REPO_ROOT / "scripts" / "maps" / "export_bundle.py"
CHECKER_PATH = REPO_ROOT / "scripts" / "maps" / "check_bundle.py"
PREBUILT_BUNDLE = REPO_ROOT / "assets" / "maps" / "molmo-cleanup-default-7"


def test_nav2_bundle_writer_exports_valid_projection_and_static_route(tmp_path: Path) -> None:
    agent_view = _agent_view()
    bundle_dir = tmp_path / "molmo-cleanup-default-7"

    snapshot = write_nav2_map_bundle(
        bundle_dir,
        metric_map=agent_view["metric_map"],
        static_landmarks=_static_landmarks(agent_view),
    )

    validation = validate_nav2_map_bundle(bundle_dir)
    projected_map = metric_map_from_bundle(bundle_dir)
    static_landmarks = static_landmarks_from_bundle(bundle_dir)
    waypoints = projected_map["inspection_waypoints"]
    route = validate_metric_map_route(
        projected_map,
        static_landmarks,
        start_waypoint_id=str(waypoints[0]["waypoint_id"]),
        goal_waypoint_id=str(waypoints[-1]["waypoint_id"]),
    )

    assert snapshot["snapshot_complete"] is True
    assert validation.ok, validation.as_dict()
    assert projected_map["schema"] == "real_robot_map_bundle_v1"
    assert projected_map["map_bundle"]["schema"] == "nav2_map_bundle_v1"
    assert static_landmarks == []
    assert route.ok is True
    assert route.navigation_backend == SIM_COSTMAP_PLANNER
    assert route.path_length_m > 0


def test_nav2_bundle_validation_rejects_private_cleanup_truth(tmp_path: Path) -> None:
    agent_view = _agent_view()
    bundle_dir = tmp_path / "bundle"
    write_nav2_map_bundle(
        bundle_dir,
        metric_map=agent_view["metric_map"],
        static_landmarks=_static_landmarks(agent_view),
    )
    semantics_path = bundle_dir / "semantics.json"
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    semantics["generated_mess_set"] = [{"object_id": "private"}]
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")

    validation = validate_nav2_map_bundle(bundle_dir)

    assert validation.ok is False
    assert any("private cleanup truth" in error for error in validation.errors)


def test_nav2_projection_rejects_map_yaml_without_image(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    agent_view = _agent_view()
    write_nav2_map_bundle(
        bundle_dir,
        metric_map=agent_view["metric_map"],
        static_landmarks=_static_landmarks(agent_view),
    )
    map_yaml_path = bundle_dir / "map.yaml"
    map_yaml = "\n".join(
        line
        for line in map_yaml_path.read_text(encoding="utf-8").splitlines()
        if line != "image: map.pgm"
    )
    map_yaml_path.write_text(map_yaml + "\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="map.yaml image must resolve to map.pgm"):
        metric_map_from_bundle(bundle_dir)


def test_nav2_projection_rejects_semantics_without_waypoints(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    agent_view = _agent_view()
    write_nav2_map_bundle(
        bundle_dir,
        metric_map=agent_view["metric_map"],
        static_landmarks=_static_landmarks(agent_view),
    )
    semantics_path = bundle_dir / "semantics.json"
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    semantics["inspection_waypoints"] = []
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")

    with pytest.raises(AssertionError, match="semantics.json must contain inspection_waypoints"):
        static_landmarks_from_bundle(bundle_dir)


def test_exporter_and_checker_accept_public_agent_view(tmp_path: Path) -> None:
    exporter = _load_module(EXPORTER_PATH, "export_bundle")
    checker = _load_module(CHECKER_PATH, "check_bundle")
    agent_view_path = tmp_path / "agent_view.json"
    bundle_dir = tmp_path / "exported"
    agent_view_path.write_text(json.dumps(_agent_view()), encoding="utf-8")

    exporter.main(["--agent-view", str(agent_view_path), "--output-dir", str(bundle_dir)])
    checker.main([str(bundle_dir)])

    assert (bundle_dir / "map.yaml").is_file()
    assert (bundle_dir / "semantics.json").is_file()


def test_exporter_writes_canonical_molmospaces_scene_bundle(tmp_path: Path) -> None:
    exporter = _load_module(EXPORTER_PATH, "export_bundle")
    checker = _load_module(CHECKER_PATH, "check_bundle")
    agent_view_path = tmp_path / "agent_view.json"
    asset_root = tmp_path / "assets" / "maps"
    bundle_dir = asset_root / "molmospaces" / "procthor-objaverse-val" / "10"
    agent_view_path.write_text(json.dumps(_agent_view()), encoding="utf-8")

    exporter.main(
        [
            "--agent-view",
            str(agent_view_path),
            "--molmospaces-scene-source",
            "procthor-objaverse-val",
            "--molmospaces-scene-index",
            "10",
            "--map-asset-root",
            str(asset_root),
        ]
    )
    checker.main([str(bundle_dir)])

    assert (bundle_dir / "map.yaml").is_file()
    assert (bundle_dir / "semantics.json").is_file()


def test_checker_cli_reports_invalid_bundle_without_traceback(tmp_path: Path) -> None:
    invalid_bundle = tmp_path / "missing-scene-bundle"
    invalid_bundle.mkdir()

    result = subprocess.run(
        [str(REPO_ROOT / ".venv" / "bin" / "python"), str(CHECKER_PATH), str(invalid_bundle)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "nav2-map-bundle invalid" in result.stderr
    assert "missing required artifact: map.yaml" in result.stderr
    assert "Traceback" not in result.stderr


def test_bundle_writer_normalizes_wide_room_only_static_landmarks(tmp_path: Path) -> None:
    agent_view = _wide_room_only_agent_view()
    bundle_dir = tmp_path / "molmospaces-procthor-val-0-7"

    write_nav2_map_bundle(
        bundle_dir,
        metric_map=agent_view["metric_map"],
        static_landmarks=_static_landmarks(agent_view),
    )

    validation = validate_nav2_map_bundle(bundle_dir)
    projected_map = metric_map_from_bundle(bundle_dir)
    static_landmarks = static_landmarks_from_bundle(bundle_dir)
    waypoints = projected_map["inspection_waypoints"]
    route = validate_metric_map_route(
        projected_map,
        static_landmarks,
        start_waypoint_id=str(waypoints[0]["waypoint_id"]),
        goal_waypoint_id=str(waypoints[-1]["waypoint_id"]),
    )
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))
    waypoint_by_id = {item["waypoint_id"]: item for item in semantics["inspection_waypoints"]}

    assert validation.ok, validation.as_dict()
    assert projected_map["width"] > agent_view["metric_map"]["width"]
    assert route.ok is True
    for fixture in semantics["static_landmarks"]:
        waypoint = waypoint_by_id[fixture["preferred_inspection_waypoint_id"]]
        pose = fixture["pose"]
        assert (pose["x"], pose["y"]) != (waypoint["x"], waypoint["y"])


def test_route_validation_blocks_occupied_goal(tmp_path: Path) -> None:
    agent_view = _wide_room_only_agent_view()
    metric_map = agent_view["metric_map"]
    static_landmarks = _static_landmarks(agent_view)
    first_fixture = static_landmarks[0]
    start_waypoint = dict(metric_map["inspection_waypoints"][0])
    start_waypoint["x"] = 1.5
    metric_map = dict(metric_map)
    metric_map["inspection_waypoints"] = [
        start_waypoint,
        *metric_map["inspection_waypoints"][1:],
    ]
    blocked_waypoint = dict(start_waypoint)
    blocked_waypoint["waypoint_id"] = "blocked_goal"
    blocked_waypoint["x"] = first_fixture["pose"]["x"]
    blocked_waypoint["y"] = first_fixture["pose"]["y"]
    metric_map["inspection_waypoints"] = [*metric_map["inspection_waypoints"], blocked_waypoint]

    result = validate_metric_map_route(
        metric_map,
        static_landmarks,
        start_waypoint_id=str(metric_map["inspection_waypoints"][0]["waypoint_id"]),
        goal_waypoint_id="blocked_goal",
    )

    assert result.ok is False
    assert result.status == "blocked_capability"
    assert result.failure_type == "goal_occupied"


def test_route_validation_rejects_invalid_metric_map_width() -> None:
    agent_view = _wide_room_only_agent_view()
    metric_map = dict(agent_view["metric_map"])
    metric_map["width"] = "wide"
    waypoints = metric_map["inspection_waypoints"]

    with pytest.raises(ValueError, match="metric_map.width must be an integer"):
        validate_metric_map_route(
            metric_map,
            _static_landmarks(agent_view),
            start_waypoint_id=str(waypoints[0]["waypoint_id"]),
            goal_waypoint_id=str(waypoints[-1]["waypoint_id"]),
        )


def test_nav2_bundle_writer_rejects_missing_metric_map_height(tmp_path: Path) -> None:
    agent_view = _agent_view()
    metric_map = dict(agent_view["metric_map"])
    metric_map.pop("height")

    with pytest.raises(ValueError, match="metric_map.height is required"):
        write_nav2_map_bundle(
            tmp_path / "bundle",
            metric_map=metric_map,
            static_landmarks=_static_landmarks(agent_view),
        )


def test_realworld_contract_projects_from_selected_prebuilt_bundle() -> None:
    contract = RealWorldCleanupContract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        map_bundle_dir=PREBUILT_BUNDLE,
    )

    metric_map = contract.metric_map()
    static_fixture_projection = contract.static_fixture_projection()
    waypoints = metric_map["inspection_waypoints"]
    navigation = contract.navigate_to_waypoint(str(waypoints[-1]["waypoint_id"]))

    assert metric_map["map_bundle"]["environment_id"] == "molmo-cleanup-default-7"
    assert metric_map["map_id"] == "molmo-cleanup-default-7_base_navigation_map"
    assert metric_map["rooms"]
    assert all(room["room_label"] for room in metric_map["rooms"])
    assert all(item["visited"] is False for item in waypoints)
    assert static_fixture_projection["rooms"] == []
    assert waypoints[0]["waypoint_source"] == "generated_exploration_candidate"
    assert navigation["navigation_backend"] == SIM_COSTMAP_PLANNER
    assert navigation["route_validation"]["ok"] is True
    assert navigation["route_validation"]["goal_waypoint_id"] == str(waypoints[-1]["waypoint_id"])


def _agent_view() -> dict:
    contract = RealWorldCleanupContract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
    )
    return {
        "metric_map": contract.metric_map(),
        "static_fixture_projection": contract.static_fixture_projection(),
    }


def _static_landmarks(agent_view: dict) -> list[dict]:
    return static_landmarks_from_fixture_projection(agent_view["static_fixture_projection"])


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _wide_room_only_agent_view() -> dict:
    rooms = []
    waypoints = []
    fixture_rooms = []
    room_count = 7
    for index in range(room_count):
        room_number = index + 2
        room_id = f"room_{room_number}"
        x0 = float(index * 3)
        room = {
            "room_id": room_id,
            "room_label": f"room {room_number}",
            "fixture_count": 1,
            "polygon": [
                {"x": x0, "y": 0.0},
                {"x": x0 + 2.0, "y": 0.0},
                {"x": x0 + 2.0, "y": 2.0},
                {"x": x0, "y": 2.0},
            ],
        }
        waypoint = {
            "waypoint_id": f"{room_id}_scan_1",
            "frame_id": "map",
            "x": x0 + 1.0,
            "y": 1.0,
            "yaw": 0.0,
            "room_id": room_id,
            "label": f"room {room_number} scan 1",
            "visited": False,
            "purpose": "fixture_coverage",
            "waypoint_source": "static_map_coverage",
            "coverage_estimate": 1.0,
        }
        rooms.append(room)
        waypoints.append(waypoint)
        fixture_rooms.append(
            {
                "room_id": room_id,
                "room_label": f"room {room_number}",
                "polygon": room["polygon"],
                "fixtures": [
                    {
                        "fixture_id": f"fixture_{room_number}",
                        "category": "CounterTop",
                        "name": f"Fixture {room_number}",
                        "room_id": room_id,
                        "affordances": ["place"],
                        "footprint": {"shape": "rectangle", "width_m": 0.55, "depth_m": 0.45},
                        "pose": {
                            "frame_id": "map",
                            "x": waypoint["x"],
                            "y": waypoint["y"],
                            "yaw": 0.0,
                        },
                        "preferred_inspection_waypoint_id": waypoint["waypoint_id"],
                        "preferred_manipulation_waypoint_id": waypoint["waypoint_id"],
                        "position_detail": "room_only",
                    }
                ],
            }
        )
    return {
        "metric_map": {
            "schema": "real_robot_map_bundle_v1",
            "frame_id": "map",
            "map_id": "molmospaces-procthor-val-0-7_base_navigation_map",
            "map_version": "base-navigation-map-v1",
            "resolution_m": 0.05,
            "origin": {"x": 0.0, "y": 0.0, "yaw": 0.0},
            "width": 240,
            "height": 180,
            "rooms": rooms,
            "inspection_waypoints": waypoints,
            "driveable_ways": [
                {
                    "from_room_id": f"room_{index + 2}",
                    "kind": "doorway",
                    "to_room_id": f"room_{index + 3}",
                }
                for index in range(room_count - 1)
            ],
        },
        "static_fixture_projection": {
            "schema": "static_fixture_projection_v1",
            "static_fixture_projection_mode": "room_only",
            "rooms": fixture_rooms,
        },
    }
