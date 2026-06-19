from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.realworld_cleanup import _load_runtime_map_prior, run_realworld_cleanup
from roboclaws.household.realworld_contract import (
    RAW_FPV_ONLY_MODE,
    RealWorldCleanupContract,
)
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.maps.runtime_prior_snapshot import (
    RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
    materialize_runtime_prior_targets,
    runtime_metric_map_from_prior_artifact,
    runtime_prior_snapshot_from_agibot_navigation_memory,
    runtime_prior_snapshot_from_nav2_cleanup_bundle,
    runtime_prior_snapshot_from_runtime_metric_map,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ROBOT_MAP_12_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "runtime_map_prior" / "robot_map_12"
CONVERTER_PATH = REPO_ROOT / "scripts" / "maps" / "convert_agibot_navigation_memory.py"
NAV2_BUNDLE_CONVERTER_PATH = REPO_ROOT / "scripts" / "maps" / "convert_nav2_cleanup_bundle.py"
FORBIDDEN_PRIVATE_KEYS = {
    "acceptable_destination_sets",
    "generated_mess_set",
    "global_movable_object_inventory",
    "is_misplaced",
    "private_manifest",
    "target_count",
    "target_receptacle_id",
    "valid_receptacle_ids",
}


def test_agibot_navigation_memory_converts_to_runtime_prior_snapshot_shape() -> None:
    snapshot = runtime_prior_snapshot_from_agibot_navigation_memory(ROBOT_MAP_12_FIXTURE)
    anchors = {item["source_anchor_id"]: item for item in snapshot["public_semantic_anchors"]}
    targets = materialize_runtime_prior_targets(snapshot)

    assert snapshot["schema"] == RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA
    assert snapshot["runtime_metric_map"]["schema"] == "runtime_metric_map_v1"
    assert snapshot["producer"]["type"] == "offline_navigation_memory_conversion"
    assert snapshot["contract"]["online_offline_equivalent_shape"] is True
    assert snapshot["contract"]["private_truth_included"] is False
    assert snapshot["contract"]["source_map_mutated"] is False
    assert len(anchors) == 9
    assert set(anchors) == {
        "plastic_bottle_table_1",
        "long_table",
        "computer_monitor_1",
        "sink_kitchen_1",
        "fridge_main",
        "coffee_table_1",
        "kitchen_center",
        "large_white_sofa_1",
        "stone_book_decor_1",
    }
    assert len(snapshot["inspection_waypoints"]) == len(anchors)
    assert "anchor_sink_kitchen_1" in targets["actionable_fixture_ids"]
    assert "anchor_coffee_table_1" in targets["actionable_fixture_ids"]
    assert "anchor_fridge_main" not in targets["actionable_fixture_ids"]

    assert anchors["sink_kitchen_1"]["anchor_type"] == "receptacle"
    assert anchors["sink_kitchen_1"]["actionability"] == "actionable"
    assert "place_inside" in anchors["sink_kitchen_1"]["affordances"]
    assert anchors["coffee_table_1"]["anchor_type"] == "surface"
    assert anchors["coffee_table_1"]["actionability"] == "actionable"
    assert anchors["large_white_sofa_1"]["anchor_type"] == "surface"
    assert anchors["kitchen_center"]["anchor_type"] == "room_area"
    assert anchors["kitchen_center"]["room_label"] == "厨房/吧台区域"
    assert anchors["kitchen_center"]["materialization"]["waypoint"]["room_label"] == (
        "厨房/吧台区域"
    )
    rooms = {item["room_id"]: item for item in snapshot["runtime_metric_map"]["rooms"]}
    assert rooms["kitchen_center"]["room_label"] == "厨房/吧台区域"
    assert rooms["kitchen_center"]["category"] == "kitchen"
    assert snapshot["runtime_metric_map"]["room_category_hints"][0]["label"] == "厨房/吧台区域"
    assert snapshot["source_navigation_map"]["room_category_hints"][0]["label"] == ("厨房/吧台区域")
    assert anchors["stone_book_decor_1"]["anchor_type"] == "landmark"
    assert anchors["stone_book_decor_1"]["actionability"] == "needs_review"

    fridge = anchors["fridge_main"]
    assert fridge["anchor_type"] == "receptacle"
    assert fridge["reachability_status"] == "costmap_disagrees"
    assert fridge["actionability"] == "costmap_disagrees"
    assert fridge["materialization"]["waypoint"]["costmap_value"] == 0

    bottle = anchors["plastic_bottle_table_1"]
    assert bottle["anchor_type"] == "movable_object"
    assert bottle["actionability"] == "needs_confirm"
    assert bottle["promotion_status"] == "movable_prior_needs_current_run_confirmation"
    assert "anchor_plastic_bottle_table_1" not in targets["actionable_fixture_ids"]
    observed = {
        item["object_id"]: item for item in snapshot["runtime_metric_map"]["observed_objects"]
    }
    assert observed["plastic_bottle_table_1"]["actionability"] == "needs_confirm"
    assert observed["plastic_bottle_table_1"]["state"] == "prior"
    assert observed["plastic_bottle_table_1"]["candidate_fixture_id"] == ""
    _assert_no_forbidden_keys(snapshot)


def test_online_and_offline_snapshots_share_consumer_contract_shape() -> None:
    online_snapshot = _online_minimal_snapshot()
    offline_snapshot = runtime_prior_snapshot_from_agibot_navigation_memory(ROBOT_MAP_12_FIXTURE)

    for snapshot in (online_snapshot, offline_snapshot):
        assert snapshot["schema"] == RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA
        assert set(snapshot) >= {
            "source_navigation_map",
            "runtime_metric_map",
            "public_semantic_anchors",
            "inspection_waypoints",
            "fixture_candidates",
            "producer",
            "contract",
        }
        assert snapshot["runtime_metric_map"]["schema"] == "runtime_metric_map_v1"
        assert snapshot["contract"]["private_truth_included"] is False
        assert snapshot["contract"]["source_map_mutated"] is False
        materialized = materialize_runtime_prior_targets(snapshot)
        assert materialized["schema"] == "runtime_map_prior_materialized_targets_v1"
        assert materialized["inspection_waypoints"]
        assert materialized["fixture_candidates"]
        assert materialized["actionable_waypoint_ids"]

    assert online_snapshot["producer"]["type"] == "online_map_build"
    assert offline_snapshot["producer"]["type"] == "offline_navigation_memory_conversion"


def test_materialized_online_snapshot_targets_are_valid_cleanup_targets() -> None:
    contract = RealWorldCleanupContract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
        allow_synthetic_map_projection=True,
    )
    _observe_until_anchor(contract, anchor_category="fridge", anchor_type="receptacle")
    online_snapshot = runtime_prior_snapshot_from_runtime_metric_map(
        contract.agent_view_payload()["runtime_metric_map"]
    )
    targets = materialize_runtime_prior_targets(online_snapshot)
    fridge_fixture = next(
        item
        for item in targets["fixture_candidates"]
        if item["category"] == "fridge" and item["actionability"] == "actionable"
    )

    work_waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["waypoint_id"] == "generated_exploration_007"
    )
    contract.navigate_to_waypoint(str(work_waypoint["waypoint_id"]))
    observation = contract.observe()
    candidate = contract.navigate_to_visual_candidate(
        observation["raw_fpv_observation"]["observation_id"],
        category="tomato",
        target_fixture_id=str(fridge_fixture["fixture_id"]),
        evidence_note="round produce item on the desk",
        image_region={"type": "verbal_region", "value": "front of desk"},
        producer_type="test_agent",
        producer_id="test_agent",
    )

    assert candidate["ok"] is True
    assert candidate["candidate_fixture_id"] == fridge_fixture["fixture_id"]
    assert contract.pick(candidate["object_id"])["ok"] is True
    assert contract.navigate_to_receptacle(str(fridge_fixture["fixture_id"]))["ok"] is True


def test_converted_snapshot_targets_are_exposed_through_cleanup_receptacle_path() -> None:
    snapshot = runtime_prior_snapshot_from_agibot_navigation_memory(ROBOT_MAP_12_FIXTURE)
    contract = RealWorldCleanupContract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
        runtime_map_prior=snapshot["runtime_metric_map"],
        allow_synthetic_map_projection=True,
    )
    public_receptacles = contract.public_receptacles_by_id()

    assert "anchor_sink_kitchen_1" in public_receptacles
    assert "anchor_fridge_main" not in public_receptacles
    assert public_receptacles["anchor_sink_kitchen_1"]["public_fixture_source"] == (
        "runtime_semantic_anchor"
    )
    runtime_rooms = {
        item["room_id"]: item
        for item in contract.agent_view_payload()["runtime_metric_map"]["rooms"]
    }
    assert runtime_rooms["kitchen_center"]["room_label"] == "厨房/吧台区域"

    work_waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["waypoint_id"] == "generated_exploration_007"
    )
    contract.navigate_to_waypoint(str(work_waypoint["waypoint_id"]))
    observation = contract.observe()
    candidate = contract.navigate_to_visual_candidate(
        observation["raw_fpv_observation"]["observation_id"],
        category="tomato",
        target_fixture_id="anchor_sink_kitchen_1",
        evidence_note="round produce item on the desk",
        image_region={"type": "verbal_region", "value": "front of desk"},
        producer_type="test_agent",
        producer_id="test_agent",
    )

    assert candidate["ok"] is True
    assert contract.pick(candidate["object_id"])["ok"] is True
    assert contract.navigate_to_receptacle("anchor_sink_kitchen_1")["ok"] is True
    assert contract.navigate_to_receptacle("anchor_fridge_main")["error_reason"] == (
        "stale_reference"
    )


def test_runtime_prior_snapshot_rejects_private_truth_keys() -> None:
    runtime_map = _online_minimal_snapshot()["runtime_metric_map"]
    runtime_map["private_manifest"] = {"target_count": 1}

    with pytest.raises(ValueError, match="private truth keys"):
        runtime_prior_snapshot_from_runtime_metric_map(runtime_map)


def test_runtime_map_prior_loader_accepts_raw_runtime_map_and_snapshot(tmp_path: Path) -> None:
    online_snapshot = _online_minimal_snapshot()
    raw_path = tmp_path / "runtime_metric_map.json"
    snapshot_path = tmp_path / "runtime_map_prior_snapshot.json"
    raw_path.write_text(json.dumps(online_snapshot["runtime_metric_map"]), encoding="utf-8")
    snapshot_path.write_text(json.dumps(online_snapshot), encoding="utf-8")

    raw_loaded = _load_runtime_map_prior(raw_path)
    snapshot_loaded = _load_runtime_map_prior(snapshot_path)

    assert raw_loaded == online_snapshot["runtime_metric_map"]
    assert snapshot_loaded == online_snapshot["runtime_metric_map"]
    assert (
        runtime_metric_map_from_prior_artifact(online_snapshot)
        == (online_snapshot["runtime_metric_map"])
    )


def test_runtime_map_prior_loader_rejects_unknown_raw_schema(tmp_path: Path) -> None:
    prior_path = tmp_path / "runtime_metric_map.json"
    prior_path.write_text('{"schema": "wrong"}\n', encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="runtime map prior artifact must be raw runtime_metric_map_v1",
    ):
        _load_runtime_map_prior(prior_path)


def test_runtime_map_prior_loader_rejects_snapshot_with_invalid_runtime_map() -> None:
    with pytest.raises(
        ValueError,
        match="runtime map prior snapshot runtime_metric_map must use schema runtime_metric_map_v1",
    ):
        runtime_metric_map_from_prior_artifact(
            {
                "schema": RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
                "runtime_metric_map": {"schema": "wrong"},
            }
        )


def test_agibot_navigation_memory_converter_script_writes_snapshot_and_summary(
    tmp_path: Path,
) -> None:
    converter = _load_module(CONVERTER_PATH, "convert_agibot_navigation_memory")
    output = tmp_path / "runtime_map_prior_snapshot.json"
    summary = tmp_path / "materialized_targets.json"

    converter.main(
        [str(ROBOT_MAP_12_FIXTURE), "--output", str(output), "--summary-json", str(summary)]
    )

    snapshot = json.loads(output.read_text(encoding="utf-8"))
    targets = json.loads(summary.read_text(encoding="utf-8"))

    assert snapshot["schema"] == RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA
    assert snapshot["producer"]["type"] == "offline_navigation_memory_conversion"
    assert "anchor_sink_kitchen_1" in targets["actionable_fixture_ids"]
    assert "anchor_plastic_bottle_table_1" not in targets["actionable_fixture_ids"]


def test_nav2_cleanup_bundle_converts_to_runtime_prior_snapshot_shape(tmp_path: Path) -> None:
    bundle_dir = _write_minimal_nav2_cleanup_bundle(tmp_path / "bundle")

    snapshot = runtime_prior_snapshot_from_nav2_cleanup_bundle(bundle_dir)
    targets = materialize_runtime_prior_targets(snapshot)

    assert snapshot["schema"] == RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA
    assert snapshot["producer"]["type"] == "offline_nav2_cleanup_bundle_conversion"
    assert snapshot["source_navigation_map"]["source_type"] == "nav2_cleanup_bundle"
    assert snapshot["runtime_metric_map"]["schema"] == "runtime_metric_map_v1"
    assert (
        snapshot["runtime_metric_map"]["digital_twin_capabilities"]["robot_consumption_proof"][
            "robot_navigation_supported"
        ]
        is True
    )
    assert snapshot["contract"]["online_offline_equivalent_shape"] is True
    assert snapshot["contract"]["private_truth_included"] is False
    assert targets["actionable_waypoint_ids"] == ["room_a_center"]
    assert targets["fixture_candidates"] == []
    assert (
        targets["digital_twin_capabilities"]["robot_consumption_proof"][
            "robot_navigation_supported"
        ]
        is True
    )
    assert (
        targets["digital_twin_capabilities"]["render_observation_proof"][
            "render_observation_supported"
        ]
        is True
    )
    assert targets["capability_summary"]["robot_navigation_supported"] is True
    assert targets["capability_summary"]["render_observation_supported"] is True
    assert targets["capability_summary"]["same_pose_fpv_supported"] is True
    assert targets["capability_summary"]["same_pose_chase_supported"] is True
    assert targets["capability_summary"]["same_pose_topdown_supported"] is True
    assert targets["capability_summary"]["default_visual_route_status"] == (
        "blocked_missing_verified_b1_floor2_slow_render_proof"
    )
    assert targets["capability_summary"]["default_visual_route_selected"] is False
    assert targets["capability_summary"]["room_semantics_supported"] is False
    assert runtime_metric_map_from_prior_artifact(snapshot) == snapshot["runtime_metric_map"]
    _assert_no_forbidden_keys(snapshot)


def test_nav2_cleanup_bundle_converter_script_writes_snapshot_and_summary(
    tmp_path: Path,
) -> None:
    converter = _load_module(NAV2_BUNDLE_CONVERTER_PATH, "convert_nav2_cleanup_bundle")
    bundle_dir = _write_minimal_nav2_cleanup_bundle(tmp_path / "bundle")
    output = tmp_path / "runtime_map_prior_snapshot.json"
    summary = tmp_path / "materialized_targets.json"

    converter.main([str(bundle_dir), "--output", str(output), "--summary-json", str(summary)])

    snapshot = json.loads(output.read_text(encoding="utf-8"))
    targets = json.loads(summary.read_text(encoding="utf-8"))
    assert snapshot["schema"] == RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA
    assert snapshot["producer"]["type"] == "offline_nav2_cleanup_bundle_conversion"
    assert targets["actionable_waypoint_ids"] == ["room_a_center"]


def test_synthetic_cleanup_consumes_converted_snapshot_through_runtime_prior(
    tmp_path: Path,
) -> None:
    snapshot = runtime_prior_snapshot_from_agibot_navigation_memory(ROBOT_MAP_12_FIXTURE)
    prior_path = tmp_path / "runtime_map_prior_snapshot.json"
    prior_path.write_text(json.dumps(snapshot), encoding="utf-8")

    result = run_realworld_cleanup(
        output_dir=tmp_path / "cleanup",
        seed=7,
        runtime_map_prior_path=prior_path,
        allow_synthetic_map_projection=True,
    )

    prior_rows = [
        item
        for item in result["runtime_metric_map"]["observed_objects"]
        if item["freshness"] == "prior"
    ]
    assert result["runtime_metric_map_prior"]["loaded"] is True
    assert result["runtime_metric_map_prior"]["source"] == str(prior_path)
    assert result["runtime_metric_map_prior"]["observed_object_count"] == 1
    assert {item["object_id"] for item in prior_rows} == {"plastic_bottle_table_1"}
    assert all(item["actionability"] == "needs_confirm" for item in prior_rows)
    assert all(item["state"] == "prior" for item in prior_rows)
    assert result["policy_uses_private_truth"] is False
    assert result["planner_uses_private_manifest"] is False
    _assert_no_forbidden_keys(result["agent_view"])


def _online_minimal_snapshot() -> dict:
    contract = RealWorldCleanupContract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        allow_synthetic_map_projection=True,
    )
    _observe_until_anchor(contract, anchor_category="fridge", anchor_type="receptacle")
    return runtime_prior_snapshot_from_runtime_metric_map(
        contract.agent_view_payload()["runtime_metric_map"],
        source_navigation_map=contract.metric_map(),
    )


def _write_minimal_nav2_cleanup_bundle(bundle_dir: Path) -> Path:
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "map.yaml").write_text(
        "\n".join(
            [
                "image: map.pgm",
                "resolution: 0.05",
                "origin: [0, 0, 0]",
                "negate: 0",
                "occupied_thresh: 0.65",
                "free_thresh: 0.196",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (bundle_dir / "map.pgm").write_text(
        "\n".join(["P2", "2 2", "255", "0 0", "0 0", ""]),
        encoding="ascii",
    )
    semantics = {
        "schema": "nav2_cleanup_semantics_v1",
        "environment_id": "test-b1-map12",
        "map_id": "test-b1-map12_base_navigation_map",
        "frame_ids": {"map": "map", "base": "base_link", "camera": "camera"},
        "rooms": [
            {
                "room_id": "room_a",
                "room_label": "Room A",
                "category": "meeting_room",
                "polygon": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 1.0, "y": 0.0},
                    {"x": 1.0, "y": 1.0},
                ],
            }
        ],
        "room_category_hints": [
            {
                "room_id": "room_a",
                "room_label": "Room A",
                "category": "meeting_room",
            }
        ],
        "inspection_waypoints": [
            {
                "waypoint_id": "room_a_center",
                "frame_id": "map",
                "x": 0.5,
                "y": 0.5,
                "yaw": 0.0,
                "room_id": "room_a",
                "label": "Room A",
                "waypoint_source": "generated_exploration_candidate",
            }
        ],
        "driveable_ways": [{"from_room_id": "room_a", "to_room_id": "room_a"}],
        "digital_twin_capabilities": {
            "robot_consumption_proof": {
                "status": "robot_navigation_verified",
                "robot_navigation_supported": True,
                "manipulation_supported": False,
            },
            "room_semantic_projection_proof": {
                "status": "blocked_missing_accepted_semantic_anchors",
                "room_semantics_supported": False,
                "object_semantics_supported": False,
                "object_projection_status": "blocked_until_object_semantic_anchors",
            },
            "render_observation_proof": {
                "status": "same_pose_render_observation_verified",
                "render_observation_supported": True,
                "same_pose_fpv_supported": True,
                "same_pose_chase_supported": True,
                "same_pose_topdown_supported": True,
                "default_visual_route": {
                    "scene_id": "B1_floor2_slow",
                    "scene_root": "data/robot-data-lab/scene-engine/data/B1_floor2_slow",
                    "selected": False,
                    "status": "blocked_missing_verified_b1_floor2_slow_render_proof",
                },
            },
        },
        "provenance": {
            "source": "test_nav2_cleanup_bundle",
            "contains_private_scoring_truth": False,
            "contains_runtime_observations": False,
        },
    }
    (bundle_dir / "semantics.json").write_text(json.dumps(semantics), encoding="utf-8")
    return bundle_dir


def _observe_until_anchor(
    contract: RealWorldCleanupContract,
    *,
    anchor_category: str,
    anchor_type: str,
) -> None:
    for waypoint in contract.metric_map()["inspection_waypoints"]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        contract.observe()
        anchors = contract.agent_view_payload()["runtime_metric_map"]["public_semantic_anchors"]
        if any(
            item.get("category") == anchor_category and item.get("anchor_type") == anchor_type
            for item in anchors
        ):
            return
    raise AssertionError(f"missing {anchor_category} {anchor_type} anchor")


def _assert_no_forbidden_keys(value: object) -> None:
    hits: set[str] = set()
    _collect_forbidden_keys(value, hits)
    assert hits == set()


def _collect_forbidden_keys(value: object, hits: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in FORBIDDEN_PRIVATE_KEYS:
                hits.add(str(key))
            _collect_forbidden_keys(item, hits)
    elif isinstance(value, list):
        for item in value:
            _collect_forbidden_keys(item, hits)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
