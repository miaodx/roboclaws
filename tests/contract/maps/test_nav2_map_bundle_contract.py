from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from roboclaws.maps.bundle import validate_nav2_map_bundle, write_nav2_map_bundle
from roboclaws.maps.project import fixture_hints_from_bundle, metric_map_from_bundle
from roboclaws.maps.route import SIM_COSTMAP_PLANNER, validate_metric_map_route
from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.realworld_contract import RICH_MAP_MODE, RealWorldCleanupContract
from roboclaws.household.scenario import build_cleanup_scenario

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
        fixture_hints=agent_view["fixture_hints"],
    )

    validation = validate_nav2_map_bundle(bundle_dir)
    projected_map = metric_map_from_bundle(bundle_dir)
    projected_hints = fixture_hints_from_bundle(bundle_dir)
    waypoints = projected_map["inspection_waypoints"]
    route = validate_metric_map_route(
        projected_map,
        projected_hints,
        start_waypoint_id=str(waypoints[0]["waypoint_id"]),
        goal_waypoint_id=str(waypoints[-1]["waypoint_id"]),
    )

    assert snapshot["snapshot_complete"] is True
    assert validation.ok, validation.as_dict()
    assert projected_map["schema"] == "real_robot_map_bundle_v1"
    assert projected_map["map_bundle"]["schema"] == "nav2_map_bundle_v1"
    assert projected_hints["schema"] == "static_fixture_semantic_map_v1"
    assert projected_hints["contains_runtime_observations"] is False
    assert route.ok is True
    assert route.navigation_backend == SIM_COSTMAP_PLANNER
    assert route.path_length_m > 0


def test_nav2_bundle_validation_rejects_private_cleanup_truth(tmp_path: Path) -> None:
    agent_view = _agent_view()
    bundle_dir = tmp_path / "bundle"
    write_nav2_map_bundle(
        bundle_dir,
        metric_map=agent_view["metric_map"],
        fixture_hints=agent_view["fixture_hints"],
    )
    semantics_path = bundle_dir / "semantics.json"
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    semantics["generated_mess_set"] = [{"object_id": "private"}]
    semantics_path.write_text(json.dumps(semantics), encoding="utf-8")

    validation = validate_nav2_map_bundle(bundle_dir)

    assert validation.ok is False
    assert any("private cleanup truth" in error for error in validation.errors)


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


def test_bundle_writer_normalizes_wide_room_only_fixture_hints(tmp_path: Path) -> None:
    agent_view = _wide_room_only_agent_view()
    bundle_dir = tmp_path / "molmospaces-procthor-val-0-7"

    write_nav2_map_bundle(
        bundle_dir,
        metric_map=agent_view["metric_map"],
        fixture_hints=agent_view["fixture_hints"],
    )

    validation = validate_nav2_map_bundle(bundle_dir)
    projected_map = metric_map_from_bundle(bundle_dir)
    projected_hints = fixture_hints_from_bundle(bundle_dir)
    waypoints = projected_map["inspection_waypoints"]
    route = validate_metric_map_route(
        projected_map,
        projected_hints,
        start_waypoint_id=str(waypoints[0]["waypoint_id"]),
        goal_waypoint_id=str(waypoints[-1]["waypoint_id"]),
    )
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))
    waypoint_by_id = {item["waypoint_id"]: item for item in semantics["inspection_waypoints"]}

    assert validation.ok, validation.as_dict()
    assert projected_map["width"] > agent_view["metric_map"]["width"]
    assert route.ok is True
    for fixture in semantics["fixtures"]:
        waypoint = waypoint_by_id[fixture["preferred_inspection_waypoint_id"]]
        pose = fixture["pose"]
        assert (pose["x"], pose["y"]) != (waypoint["x"], waypoint["y"])


def test_route_validation_blocks_occupied_goal(tmp_path: Path) -> None:
    agent_view = _agent_view()
    metric_map = agent_view["metric_map"]
    fixture_hints = agent_view["fixture_hints"]
    first_fixture = fixture_hints["rooms"][0]["fixtures"][0]
    blocked_waypoint = dict(metric_map["inspection_waypoints"][0])
    blocked_waypoint["waypoint_id"] = "blocked_goal"
    blocked_waypoint["x"] = first_fixture["pose"]["x"]
    blocked_waypoint["y"] = first_fixture["pose"]["y"]
    metric_map = dict(metric_map)
    metric_map["inspection_waypoints"] = [*metric_map["inspection_waypoints"], blocked_waypoint]

    result = validate_metric_map_route(
        metric_map,
        fixture_hints,
        start_waypoint_id=str(metric_map["inspection_waypoints"][0]["waypoint_id"]),
        goal_waypoint_id="blocked_goal",
    )

    assert result.ok is False
    assert result.status == "blocked_capability"
    assert result.failure_type == "goal_occupied"


def test_realworld_contract_projects_from_selected_prebuilt_bundle() -> None:
    contract = RealWorldCleanupContract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        map_bundle_dir=PREBUILT_BUNDLE,
        map_mode=RICH_MAP_MODE,
    )

    metric_map = contract.metric_map()
    fixture_hints = contract.fixture_hints()
    waypoints = metric_map["inspection_waypoints"]
    navigation = contract.navigate_to_waypoint(str(waypoints[-1]["waypoint_id"]))

    assert metric_map["map_bundle"]["environment_id"] == "molmo-cleanup-default-7"
    assert metric_map["map_id"] == "molmo-cleanup-default-7_semantic_map"
    assert all(item["visited"] is False for item in waypoints)
    assert fixture_hints["rooms"][0]["fixtures"][0]["fixture_id"] == "laundry_hamper_01"
    assert navigation["navigation_backend"] == SIM_COSTMAP_PLANNER
    assert navigation["route_validation"]["ok"] is True
    assert navigation["route_validation"]["goal_waypoint_id"] == str(waypoints[-1]["waypoint_id"])


def _agent_view() -> dict:
    contract = RealWorldCleanupContract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        map_mode=RICH_MAP_MODE,
    )
    return {
        "metric_map": contract.metric_map(),
        "fixture_hints": contract.fixture_hints(),
    }


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
            "map_id": "molmospaces-procthor-val-0-7_semantic_map",
            "map_version": "static-fixture-map-v1",
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
        "fixture_hints": {
            "schema": "static_fixture_semantic_map_v1",
            "fixture_hint_mode": "room_only",
            "rooms": fixture_rooms,
        },
    }
