from __future__ import annotations

from pathlib import Path

from PIL import Image

from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_SCHEMA,
    CLEANUP_WORKLIST_SCHEMA,
    MINIMAL_MAP_MODE,
    RAW_FPV_ONLY_MODE,
    REAL_ROBOT_MAP_BUNDLE_SCHEMA,
    REALWORLD_CONTRACT,
    RICH_MAP_MODE,
    RUNTIME_METRIC_MAP_SCHEMA,
    SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY,
    SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE,
    SIMULATED_CAMERA_MODEL_PROVENANCE,
    VISUAL_CANDIDATE_ALREADY_HANDLED_REASON,
    VISUAL_GROUNDING_CATEGORY_HINTS,
    RealWorldCleanupContract,
    cleanup_policy_trace_from_events,
    forbidden_agent_view_keys,
    infer_target_fixture_for_detection,
)
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.types import (
    CleanupObject,
    CleanupReceptacle,
    CleanupScenario,
    PrivateScoringManifest,
    TargetRule,
)
from roboclaws.household.visual_grounding import VISUAL_GROUNDING_RESPONSE_SCHEMA
from roboclaws.maps.route import validate_metric_map_route


def _contract(
    session: CleanupBackendSession,
    **kwargs: object,
) -> RealWorldCleanupContract:
    kwargs.setdefault("map_mode", RICH_MAP_MODE)
    return RealWorldCleanupContract(session, **kwargs)


def test_realworld_contract_defaults_to_minimal_map_mode() -> None:
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))

    metric_map = contract.metric_map()
    fixture_hints = contract.fixture_hints()

    assert contract.map_mode == MINIMAL_MAP_MODE
    assert metric_map["mode"] == MINIMAL_MAP_MODE
    assert fixture_hints["rooms"] == []


def test_realworld_public_tools_do_not_expose_private_targets_or_global_inventory() -> None:
    contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))

    metric_map = contract.metric_map()
    fixture_hints = contract.fixture_hints()
    observation = _first_non_empty_observation(contract)

    assert metric_map["contract"] == REALWORLD_CONTRACT
    assert "objects" not in metric_map
    assert "objects" not in fixture_hints
    assert observation["private_target_truth_included"] is False
    assert observation["visible_object_detections"]
    for detection in observation["visible_object_detections"]:
        assert detection["object_id"].startswith("observed_")
        assert "support_estimate" in detection
        assert "candidate_fixture_id" in detection
        assert "cleanup_recommended" in detection
        assert "target_receptacle_id" not in detection
        assert "is_misplaced" not in detection
    _assert_no_forbidden_keys(metric_map)
    _assert_no_forbidden_keys(fixture_hints)
    _assert_no_forbidden_keys(observation)


def test_world_labels_sanitized_observations_omit_destination_oracle_fields() -> None:
    rich_contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
    rich_observation = _first_non_empty_observation(rich_contract)
    rich_detection = rich_observation["visible_object_detections"][0]

    sanitized_contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        cleanup_profile="world-labels-sanitized",
    )
    sanitized_observation = _first_non_empty_observation(sanitized_contract)
    detection = sanitized_observation["visible_object_detections"][0]

    assert "candidate_fixture_id" in rich_detection
    assert "recommended_tool" in rich_detection
    assert sanitized_observation["perception_source"] == (
        SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
    )
    assert sanitized_observation["detection_exposure_policy"] == (
        SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY
    )
    assert detection["object_id"].startswith("observed_")
    assert detection["category"]
    assert detection["image_region"]["type"] == "bbox"
    assert detection["source_observation_id"]
    assert detection["producer_type"] == SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
    assert detection["support_estimate"]
    assert "cleanup_recommended" not in detection
    assert detection["destination_policy_status"] == "policy_required"
    assert "candidate_fixture_id" not in detection
    assert "recommended_tool" not in detection
    _assert_no_forbidden_keys(sanitized_observation)


def test_realworld_contract_exposes_nav2_shaped_public_map_and_provenance() -> None:
    contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))

    metric_map = contract.metric_map()
    fixture_hints = contract.fixture_hints()
    waypoint = {}
    waypoint_nav = {}
    observation = {}
    detection = None
    for candidate in metric_map["inspection_waypoints"]:
        waypoint = candidate
        waypoint_nav = contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
        detections = observation["visible_object_detections"]
        if detections:
            detection = detections[0]
            break
    assert detection is not None
    fixture = infer_target_fixture_for_detection(detection, fixture_hints)
    assert fixture is not None
    object_nav = contract.navigate_to_object(detection["object_id"])
    assert contract.pick(detection["object_id"])["ok"] is True
    receptacle_nav = contract.navigate_to_receptacle(str(fixture["fixture_id"]))
    agent_view = contract.agent_view_payload()
    live_metric_map = contract.metric_map()

    assert metric_map["schema"] == REAL_ROBOT_MAP_BUNDLE_SCHEMA
    assert metric_map["frame_id"] == "map"
    assert metric_map["origin"] == {"x": 0.0, "y": 0.0, "yaw": 0.0}
    assert metric_map["occupancy_values"] == {"unknown": -1, "free": 0, "occupied": 100}
    assert metric_map["map_bundle"]["schema"] == "nav2_map_bundle_v1"
    assert metric_map["map_bundle"]["robot_profile_id"] == "rby1m"
    assert metric_map["map_bundle"]["artifact_paths"]["map_yaml"] == "map_bundle/map.yaml"
    assert metric_map["map_bundle"]["parameter_hash"]
    assert waypoint["frame_id"] == "map"
    assert waypoint["purpose"] == "fixture_coverage"
    assert waypoint["waypoint_source"] == "static_map_coverage"
    assert fixture_hints["schema"] == "static_fixture_semantic_map_v1"
    assert fixture_hints["contains_runtime_observations"] is False
    assert "observations" not in fixture_hints
    assert waypoint_nav["navigation_backend"] == "sim_costmap_planner"
    assert waypoint_nav["route_validation"]["ok"] is True
    assert waypoint_nav["pose_source"] == "inspection_waypoint"
    assert object_nav["navigation_backend"] == "api_semantic"
    assert object_nav["pose_source"] == "latest_observation"
    assert object_nav["requires_reobserve"] is False
    assert receptacle_nav["navigation_backend"] == "api_semantic"
    assert receptacle_nav["pose_source"] == "fixture_semantic_map"
    assert agent_view["policy_view"]["chase_camera_policy_input"] is False
    assert "runtime_metric_map" in agent_view["policy_view"]["allowed_inputs"]
    assert agent_view["runtime_metric_map"]["schema"] == RUNTIME_METRIC_MAP_SCHEMA
    assert live_metric_map["runtime_metric_map"]["schema"] == RUNTIME_METRIC_MAP_SCHEMA
    assert live_metric_map["runtime_metric_map"]["observed_objects"][0]["state"] == "held"
    assert agent_view["runtime_metric_map"]["source_map_mutated"] is False
    assert agent_view["runtime_metric_map"]["static_map"]["contains_runtime_observations"] is False
    assert agent_view["runtime_metric_map"]["observed_objects"][0]["state"] == "held"
    assert agent_view["cleanup_worklist"]["schema"] == CLEANUP_WORKLIST_SCHEMA
    assert agent_view["cleanup_worklist"]["objects"][0]["state"] == "held"
    _assert_no_forbidden_keys(agent_view)


def test_scene_index_backend_prefers_public_usd_fixture_overlay_over_stale_map_bundle() -> None:
    scenario = CleanupScenario(
        scenario_id="isaac-scene-index-procthor-10k-val-1-7-1",
        task="Clean up this loaded Isaac scene.",
        seed=7,
        objects=(
            CleanupObject(
                object_id="bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2",
                name="Bowl (Bowl_12)",
                category="Bowl",
                location_id="diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
            ),
        ),
        receptacles=(
            CleanupReceptacle(
                "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
                "DiningTable DiningTable|2|1|0 Dining_Table_203_1",
                "isaac_scene",
                category="DiningTable",
            ),
            CleanupReceptacle(
                "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",
                "Sink Sink|3|1|0 Sink_1",
                "isaac_scene",
                category="Sink",
            ),
        ),
        private_manifest=PrivateScoringManifest(
            scenario_id="isaac-scene-index-procthor-10k-val-1-7-1",
            targets=(
                TargetRule(
                    object_id="bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2",
                    valid_receptacle_ids=("sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",),
                ),
            ),
            success_threshold=1,
        ),
    )
    session = CleanupBackendSession(scenario)
    session.backend.scenario_source = "isaac_scene_index"
    contract = _contract(
        session,
        map_bundle_dir=Path("assets/maps/molmospaces-procthor-val-0-7"),
    )

    fixture_hints = contract.fixture_hints()
    detection = None
    inspection_waypoints = contract.metric_map()["inspection_waypoints"]
    for waypoint in inspection_waypoints:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
        if observation["visible_object_detections"]:
            detection = observation["visible_object_detections"][0]
            break

    assert detection is not None
    target_fixture = infer_target_fixture_for_detection(detection, fixture_hints)
    assert target_fixture is not None
    assert target_fixture["fixture_id"] == "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3"
    assert target_fixture["public_fixture_source"] == "isaac_scene_index"
    assert fixture_hints["scene_index_fixture_overlay"]["enabled"] is True

    assert contract.navigate_to_object(detection["object_id"])["ok"] is True
    assert contract.pick(detection["object_id"])["ok"] is True
    assert contract.navigate_to_receptacle(str(target_fixture["fixture_id"]))["ok"] is True
    assert contract.place(str(target_fixture["fixture_id"]))["ok"] is True
    for waypoint in inspection_waypoints:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        contract.observe()
    assert contract.done("scene-index overlay cleanup")["cleanup_status"] == "success"
    _assert_no_forbidden_keys(fixture_hints)


def test_scene_index_backend_public_map_uses_usd_room_outline_scale() -> None:
    scenario = CleanupScenario(
        scenario_id="isaac-scene-index-procthor-10k-val-1-7-1",
        task="Clean up this loaded Isaac scene.",
        seed=7,
        objects=(
            CleanupObject(
                object_id="bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2",
                name="Bowl (Bowl_12)",
                category="Bowl",
                location_id="diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
            ),
        ),
        receptacles=(
            CleanupReceptacle(
                "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
                "DiningTable DiningTable|2|1|0 Dining_Table_203_1",
                "isaac_scene",
                category="DiningTable",
            ),
            CleanupReceptacle(
                "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",
                "Sink Sink|3|1|0 Sink_1",
                "isaac_scene",
                category="Sink",
            ),
        ),
        private_manifest=PrivateScoringManifest(
            scenario_id="isaac-scene-index-procthor-10k-val-1-7-1",
            targets=(
                TargetRule(
                    object_id="bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2",
                    valid_receptacle_ids=("sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",),
                ),
            ),
            success_threshold=1,
        ),
    )
    session = CleanupBackendSession(scenario)
    session.backend.scenario_source = "isaac_scene_index"
    session.backend.room_outlines = [
        {
            "room_id": "room_2",
            "label": "Room 2",
            "center": [2.99, 4.983],
            "half_extents": [2.99, 4.983],
            "provenance": "isaac_usd_room_mesh_world_bounds",
            "usd_prim_path": "/val_1/Geometry/room_2_visual_0",
        },
        {
            "room_id": "room_3",
            "label": "Room 3",
            "center": [7.973, 2.99],
            "half_extents": [1.993, 2.99],
            "provenance": "isaac_usd_room_mesh_world_bounds",
            "usd_prim_path": "/val_1/Geometry/room_3_visual_0",
        },
    ]
    session.backend.receptacle_index = {
        "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2": {
            "usd_world_bounds": {"center": [2.717858, 5.93953, 0.374628]}
        },
        "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3": {
            "usd_world_bounds": {"center": [9.578895, 1.843155, 0.52296]}
        },
    }

    contract = _contract(session)
    metric_map = contract.metric_map()
    rooms = {room["room_id"]: room for room in metric_map["rooms"]}
    room_2 = rooms["room_2"]
    room_3 = rooms["room_3"]

    assert room_2["scene_room_outline"]["provenance"] == "isaac_usd_room_mesh_world_bounds"
    assert room_2["polygon"] == [
        {"x": 0.0, "y": 0.0},
        {"x": 5.98, "y": 0.0},
        {"x": 5.98, "y": 9.966},
        {"x": 0.0, "y": 9.966},
    ]
    assert room_3["polygon"] == [
        {"x": 5.98, "y": 0.0},
        {"x": 9.966, "y": 0.0},
        {"x": 9.966, "y": 5.98},
        {"x": 5.98, "y": 5.98},
    ]
    assert all(
        waypoint["x"] != 1.0 or waypoint["y"] != 1.0
        for waypoint in metric_map["inspection_waypoints"]
        if waypoint["room_id"] in {"room_2", "room_3"}
    )
    assert contract.fixture_hints()["rooms"][0]["fixtures"][0]["pose"]["x"] == 2.717858


def test_scene_index_backend_room_outline_waypoints_avoid_fixture_occupied_goals() -> None:
    scenario = CleanupScenario(
        scenario_id="isaac-scene-index-procthor-10k-val-1-7-1",
        task="Clean up this loaded Isaac scene.",
        seed=7,
        objects=(
            CleanupObject(
                object_id="bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2",
                name="Bowl (Bowl_12)",
                category="Bowl",
                location_id="diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
            ),
        ),
        receptacles=(
            CleanupReceptacle("bed_258d27d5fe50e324961c7a8698ace951_1_0_2", "Bed", "isaac_scene"),
            CleanupReceptacle(
                "bed_aed5602affd158c34e7eda83481af599_1_0_2",
                "Bed",
                "isaac_scene",
            ),
            CleanupReceptacle(
                "chair_bfd87bce6390b5a5bb5fcae097e899f7_1_0_2",
                "Chair",
                "isaac_scene",
            ),
            CleanupReceptacle(
                "chair_bfd87bce6390b5a5bb5fcae097e899f7_2_0_2",
                "Chair",
                "isaac_scene",
            ),
            CleanupReceptacle(
                "chair_bfd87bce6390b5a5bb5fcae097e899f7_3_0_2",
                "Chair",
                "isaac_scene",
            ),
            CleanupReceptacle(
                "chestofdrawers_7a2e462b2666d3558113b2d84da9dc74_1_0_2",
                "Dresser",
                "isaac_scene",
            ),
            CleanupReceptacle(
                "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
                "DiningTable",
                "isaac_scene",
            ),
            CleanupReceptacle(
                "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",
                "Sink",
                "isaac_scene",
            ),
        ),
        private_manifest=PrivateScoringManifest(
            scenario_id="isaac-scene-index-procthor-10k-val-1-7-1",
            targets=(
                TargetRule(
                    object_id="bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2",
                    valid_receptacle_ids=("sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",),
                ),
            ),
            success_threshold=1,
        ),
    )
    session = CleanupBackendSession(scenario)
    session.backend.scenario_source = "isaac_scene_index"
    session.backend.room_outlines = [
        {
            "room_id": "room_2",
            "label": "Room 2",
            "center": [2.99, 4.983],
            "half_extents": [2.99, 4.983],
            "provenance": "isaac_usd_room_mesh_world_bounds",
            "usd_prim_path": "/val_1/Geometry/room_2_visual_0",
        },
        {
            "room_id": "room_3",
            "label": "Room 3",
            "center": [7.973, 2.99],
            "half_extents": [1.993, 2.99],
            "provenance": "isaac_usd_room_mesh_world_bounds",
            "usd_prim_path": "/val_1/Geometry/room_3_visual_0",
        },
    ]
    session.backend.receptacle_index = {
        "bed_258d27d5fe50e324961c7a8698ace951_1_0_2": {
            "usd_world_bounds": {"center": [2.818349, 8.99204, 0.856923]}
        },
        "bed_aed5602affd158c34e7eda83481af599_1_0_2": {
            "usd_world_bounds": {"center": [2.809145, 1.200613, 0.5965]}
        },
        "chair_bfd87bce6390b5a5bb5fcae097e899f7_1_0_2": {
            "usd_world_bounds": {"center": [3.308217, 5.945434, 0.4]}
        },
        "chair_bfd87bce6390b5a5bb5fcae097e899f7_2_0_2": {
            "usd_world_bounds": {"center": [2.70468, 6.83613, 0.4]}
        },
        "chair_bfd87bce6390b5a5bb5fcae097e899f7_3_0_2": {
            "usd_world_bounds": {"center": [2.11708, 5.932897, 0.4]}
        },
        "chestofdrawers_7a2e462b2666d3558113b2d84da9dc74_1_0_2": {
            "usd_world_bounds": {"center": [5.716285, 0.639941, 0.5]}
        },
        "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2": {
            "usd_world_bounds": {"center": [2.717858, 5.93953, 0.374628]}
        },
        "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3": {
            "usd_world_bounds": {"center": [9.578895, 1.843155, 0.52296]}
        },
    }

    contract = _contract(session)
    metric_map = contract.metric_map()
    fixture_hints = contract.fixture_hints()
    waypoints = metric_map["inspection_waypoints"]
    routes = [
        validate_metric_map_route(
            metric_map,
            fixture_hints,
            start_waypoint_id=str(waypoints[0]["waypoint_id"]),
            goal_waypoint_id=str(waypoint["waypoint_id"]),
        )
        for waypoint in waypoints
    ]

    assert len(waypoints) == 4
    assert all(route.ok for route in routes), [route.as_dict() for route in routes]
    assert (waypoints[1]["x"], waypoints[1]["y"]) != (2.99, 9.216)
    for waypoint in waypoints:
        navigation = contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        assert navigation["ok"] is True, navigation


def test_cleanup_policy_trace_allows_public_map_query_before_post_place_observe() -> None:
    trace = cleanup_policy_trace_from_events(
        [
            _trace_response("navigate_to_waypoint", {"ok": True, "waypoint_id": "room_1_scan_1"}),
            _trace_response("observe", {"ok": True, "waypoint_id": "room_1_scan_1"}),
            _trace_response("navigate_to_object", {"ok": True, "object_id": "observed_001"}),
            _trace_response("pick", {"ok": True, "object_id": "observed_001"}),
            _trace_response(
                "navigate_to_receptacle",
                {
                    "ok": True,
                    "object_id": "observed_001",
                    "fixture_id": "sink_01",
                },
            ),
            _trace_response(
                "place",
                {
                    "ok": True,
                    "object_id": "observed_001",
                    "fixture_id": "sink_01",
                },
            ),
            _trace_response("metric_map", {"ok": True}),
            _trace_response("observe", {"ok": True, "waypoint_id": "room_1_scan_1"}),
        ],
        {"metric_map": {"inspection_waypoints": [{"waypoint_id": "room_1_scan_1"}]}},
    )

    assert trace["placed_object_count"] == 1
    assert trace["post_place_observe_count"] == 1
    assert trace["post_place_observe_complete"] is True
    assert trace["events"][-1]["role"] == "post_place_observe"


def test_cleanup_policy_trace_treats_last_waypoint_discovery_as_interleaved() -> None:
    trace = cleanup_policy_trace_from_events(
        [
            _trace_response("navigate_to_waypoint", {"ok": True, "waypoint_id": "room_1_scan_1"}),
            _trace_response(
                "observe",
                {
                    "ok": True,
                    "waypoint_id": "room_1_scan_1",
                    "visible_object_detections": [],
                },
            ),
            _trace_response("navigate_to_waypoint", {"ok": True, "waypoint_id": "room_1_scan_2"}),
            _trace_response(
                "observe",
                {
                    "ok": True,
                    "waypoint_id": "room_1_scan_2",
                    "visible_object_detections": [
                        {
                            "object_id": "observed_001",
                            "cleanup_recommended": True,
                        }
                    ],
                },
            ),
            _trace_response("navigate_to_object", {"ok": True, "object_id": "observed_001"}),
            _trace_response("pick", {"ok": True, "object_id": "observed_001"}),
            _trace_response(
                "navigate_to_receptacle",
                {"ok": True, "object_id": "observed_001", "fixture_id": "sink_01"},
            ),
            _trace_response(
                "place",
                {"ok": True, "object_id": "observed_001", "fixture_id": "sink_01"},
            ),
            _trace_response("observe", {"ok": True, "waypoint_id": "room_1_scan_2"}),
        ],
        {
            "metric_map": {
                "inspection_waypoints": [
                    {"waypoint_id": "room_1_scan_1"},
                    {"waypoint_id": "room_1_scan_2"},
                ]
            }
        },
    )

    assert trace["loop_style"] == "interleaved_cleanup_loop"
    assert trace["first_cleanup_before_full_survey"] is False
    assert trace["first_actionable_observation_index"] == 4
    assert trace["first_cleanup_index"] == 5


def test_cleanup_policy_trace_rejects_cached_cleanup_after_later_map_query() -> None:
    trace = cleanup_policy_trace_from_events(
        [
            _trace_response("navigate_to_waypoint", {"ok": True, "waypoint_id": "room_1_scan_1"}),
            _trace_response(
                "observe",
                {
                    "ok": True,
                    "waypoint_id": "room_1_scan_1",
                    "visible_object_detections": [
                        {
                            "object_id": "observed_001",
                            "cleanup_recommended": True,
                        }
                    ],
                },
            ),
            _trace_response("navigate_to_waypoint", {"ok": True, "waypoint_id": "room_1_scan_2"}),
            _trace_response("observe", {"ok": True, "waypoint_id": "room_1_scan_2"}),
            _trace_response("navigate_to_object", {"ok": True, "object_id": "observed_001"}),
        ],
        {
            "metric_map": {
                "inspection_waypoints": [
                    {"waypoint_id": "room_1_scan_1"},
                    {"waypoint_id": "room_1_scan_2"},
                ]
            }
        },
    )

    assert trace["loop_style"] == "survey_first_cleanup_loop"
    assert trace["first_actionable_observation_index"] == 2
    assert trace["first_cleanup_index"] == 5


def test_runtime_metric_map_keeps_static_and_dynamic_semantics_separate() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )

    observation = {}
    declared = {}
    for waypoint in contract.metric_map()["inspection_waypoints"]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
        declared = contract.declare_visual_candidates(
            observation["raw_fpv_observation"]["observation_id"]
        )
        if declared["model_declared_observations"]:
            break
    agent_view = contract.agent_view_payload()
    runtime_map = agent_view["runtime_metric_map"]

    assert declared["ok"] is True
    assert runtime_map["schema"] == RUNTIME_METRIC_MAP_SCHEMA
    assert runtime_map["private_truth_included"] is False
    assert runtime_map["source_map_mutated"] is False
    assert runtime_map["static_map"]["fixtures"]
    assert runtime_map["public_semantic_anchors"] == []
    assert runtime_map["map_update_candidates"] == []
    assert runtime_map["observed_objects"]
    observed = runtime_map["observed_objects"][0]
    assert observed["object_id"].startswith("observed_")
    assert observed["source_observation_id"] == observation["raw_fpv_observation"]["observation_id"]
    assert observed["producer_type"] == SIMULATED_CAMERA_MODEL_PROVENANCE
    assert observed["actionability"] in {"actionable", "pending"}
    for fixture in runtime_map["static_map"]["fixtures"]:
        assert "observed_objects" not in fixture
        assert not fixture["fixture_id"].startswith("observed_")
    _assert_no_forbidden_keys(runtime_map)


def test_world_labels_sanitized_runtime_map_keeps_detection_fields_without_destination() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        cleanup_profile="world-labels-sanitized",
    )

    _first_non_empty_observation(contract)
    agent_view = contract.agent_view_payload()
    runtime_map = agent_view["runtime_metric_map"]
    observed = runtime_map["observed_objects"][0]
    worklist_item = agent_view["cleanup_worklist"]["objects"][0]

    assert agent_view["detection_exposure_policy"] == SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY
    assert observed["producer_type"] == SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
    assert observed["source_observation_id"]
    assert observed["image_region"]["type"] == "bbox"
    assert observed["grounding_status"] == "resolved"
    assert observed["actionability"] == "pending"
    assert observed["candidate_fixture_id"] == ""
    assert observed["candidate_source"] == "policy_required_destination_selection"
    assert observed["destination_policy_status"] == "policy_required"
    assert "cleanup_recommended" not in worklist_item
    assert worklist_item["candidate_fixture_id"] == ""
    assert worklist_item["destination_policy_status"] == "policy_required"
    assert runtime_map["producer_summary"]["producer_types"][
        SANITIZED_VISIBLE_OBJECT_DETECTIONS_PROVENANCE
    ] >= 1
    _assert_no_forbidden_keys(runtime_map)


def test_runtime_metric_map_snapshot_priors_require_current_confirmation() -> None:
    sweep_contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )
    for waypoint in sweep_contract.metric_map()["inspection_waypoints"]:
        sweep_contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = sweep_contract.observe()
        declared = sweep_contract.declare_visual_candidates(
            observation["raw_fpv_observation"]["observation_id"]
        )
        if declared["model_declared_observations"]:
            break
    prior_snapshot = sweep_contract.agent_view_payload()["runtime_metric_map"]

    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
        runtime_map_prior=prior_snapshot,
    )
    prior_only_map = contract.agent_view_payload()["runtime_metric_map"]

    prior_rows = [
        item for item in prior_only_map["observed_objects"] if item["freshness"] == "prior"
    ]
    assert prior_rows
    assert all(item["actionability"] == "needs_confirm" for item in prior_rows)
    assert contract.agent_view_payload()["observed_objects"] == []

    for waypoint in contract.metric_map()["inspection_waypoints"]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
        declared = contract.declare_visual_candidates(
            observation["raw_fpv_observation"]["observation_id"]
        )
        if declared["model_declared_observations"]:
            break

    runtime_map = contract.agent_view_payload()["runtime_metric_map"]
    current_rows = [
        item for item in runtime_map["observed_objects"] if item["freshness"] == "current_run"
    ]
    assert current_rows
    assert current_rows[0]["prior_object_id"] == prior_rows[0]["prior_object_id"]
    assert current_rows[0]["snapshot_object_id"] == prior_rows[0]["snapshot_object_id"]
    _assert_no_forbidden_keys(runtime_map)


def test_minimal_map_mode_hides_authored_semantics_and_uses_generated_candidates() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        map_mode=MINIMAL_MAP_MODE,
    )

    metric_map = contract.metric_map()
    fixture_hints = contract.fixture_hints()
    waypoint = metric_map["inspection_waypoints"][0]
    navigation = contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    for candidate in metric_map["inspection_waypoints"][1:]:
        if observation["visible_object_detections"]:
            break
        waypoint = candidate
        navigation = contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
    agent_view = contract.agent_view_payload()
    runtime_map = agent_view["runtime_metric_map"]

    assert metric_map["mode"] == MINIMAL_MAP_MODE
    assert metric_map["rooms"] == []
    assert metric_map["driveable_ways"] == []
    assert fixture_hints["rooms"] == []
    assert waypoint["waypoint_id"].startswith("generated_")
    assert waypoint["waypoint_source"] == "generated_exploration_candidate"
    assert waypoint["candidate_provenance"]["source"] == "public_occupancy_free_space"
    assert waypoint["candidate_provenance"]["source_pose"] == "free_space_sample"
    assert waypoint["candidate_provenance"]["source_room_hidden"] is True
    assert waypoint["candidate_provenance"]["source_fixtures_hidden"] is True
    assert waypoint["candidate_provenance"]["source_waypoint_hidden"] is True
    assert "source_waypoint_id" not in waypoint["candidate_provenance"]
    assert navigation["ok"] is True
    assert observation["visible_object_detections"]
    assert runtime_map["map_mode"] == MINIMAL_MAP_MODE
    assert runtime_map["minimal_map_mode"] is True
    assert runtime_map["static_map"]["rooms"] == []
    assert runtime_map["static_map"]["fixtures"] == []
    assert runtime_map["static_map"]["driveable_ways"] == []
    assert runtime_map["generated_exploration_candidates"]
    assert runtime_map["public_semantic_anchors"]
    waypoint_anchor = next(
        item
        for item in runtime_map["public_semantic_anchors"]
        if item["anchor_type"] == "observation_waypoint"
        and item["waypoint_id"] == waypoint["waypoint_id"]
    )
    assert waypoint_anchor["anchor_id"].startswith("anchor_waypoint_generated_")
    assert waypoint_anchor["waypoint_id"] == waypoint["waypoint_id"]
    assert waypoint_anchor["producer_type"] == "generated_exploration_candidate"
    assert waypoint_anchor["promotion_status"] == "run_local"
    fixture_anchor = next(
        item
        for item in runtime_map["public_semantic_anchors"]
        if item["anchor_type"] in {"fixture", "receptacle"}
    )
    assert fixture_anchor["anchor_id"].startswith("anchor_fixture_")
    assert fixture_anchor["source_observation_id"]
    assert runtime_map["observed_objects"]
    assert runtime_map["observed_objects"][0]["source_fixture_id"].startswith("anchor_fixture_")
    assert agent_view["observed_objects"][0]["support_estimate"]["fixture_id"].startswith(
        "anchor_fixture_"
    )
    _assert_no_forbidden_keys(agent_view)


def test_minimal_map_mode_keeps_public_waypoint_after_receptacle_navigation() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        map_mode=MINIMAL_MAP_MODE,
    )

    observation = _first_non_empty_observation(contract)
    detection = next(
        item for item in observation["visible_object_detections"] if item["cleanup_recommended"]
    )
    fixture_id = str(detection["candidate_fixture_id"])

    assert contract.navigate_to_object(detection["object_id"])["ok"] is True
    assert contract.pick(detection["object_id"])["ok"] is True
    navigation = contract.navigate_to_receptacle(fixture_id)
    post_nav_map = contract.metric_map()

    assert navigation["ok"] is True
    assert post_nav_map["robot_pose"]["waypoint_id"].startswith("generated_exploration_")
    assert post_nav_map["robot_pose"]["room_id"] == "generated_area"
    assert post_nav_map["robot_pose"]["waypoint_id"] in {
        str(item["waypoint_id"]) for item in post_nav_map["inspection_waypoints"]
    }


def test_minimal_map_mode_observe_marks_placed_object_non_actionable() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        map_mode=MINIMAL_MAP_MODE,
    )

    observation = _first_non_empty_observation(contract)
    detection = next(
        item for item in observation["visible_object_detections"] if item["cleanup_recommended"]
    )
    fixture_id = str(detection["candidate_fixture_id"])

    assert contract.navigate_to_object(detection["object_id"])["ok"] is True
    assert contract.pick(detection["object_id"])["ok"] is True
    assert contract.navigate_to_receptacle(fixture_id)["ok"] is True
    if detection.get("recommended_tool") == "place_inside":
        opened = contract.open_receptacle(fixture_id)
        if opened["ok"]:
            assert contract.place_inside(fixture_id)["ok"] is True
            closed = contract.close_receptacle(fixture_id)
            if closed["ok"]:
                expected_state = "placed_closed"
            else:
                expected_state = "placed"
        else:
            assert contract.place_inside(fixture_id)["ok"] is True
            expected_state = "placed"
    else:
        assert contract.place(fixture_id)["ok"] is True
        expected_state = "placed"

    later = contract.observe()
    later_detection = next(
        item
        for item in later["visible_object_detections"]
        if item["object_id"] == detection["object_id"]
    )
    worklist_item = next(
        item
        for item in contract.cleanup_worklist_payload()["objects"]
        if item["object_id"] == detection["object_id"]
    )
    duplicate_nav = contract.navigate_to_object(detection["object_id"])
    duplicate_pick = contract.pick(detection["object_id"])

    assert later_detection["cleanup_recommended"] is False
    assert worklist_item["state"] == expected_state
    assert worklist_item["cleanup_recommended"] is False
    assert duplicate_nav["ok"] is False
    assert duplicate_nav["error_reason"] == "already_handled"
    assert duplicate_pick["ok"] is False
    assert duplicate_pick["error_reason"] == "already_handled"


def test_minimal_map_mode_done_uses_generated_candidate_coverage() -> None:
    contract = _contract(
        CleanupBackendSession(
            CleanupScenario(
                scenario_id="minimal-map-done-gate-test",
                task="build minimal map",
                seed=7,
                objects=(),
                receptacles=(
                    CleanupReceptacle("sink_01", "Sink", "kitchen", category="Sink"),
                    CleanupReceptacle("desk_01", "Desk", "office", category="Desk"),
                ),
                private_manifest=PrivateScoringManifest(
                    scenario_id="minimal-map-done-gate-test",
                    targets=(),
                    success_threshold=0,
                ),
            )
        ),
        map_mode=MINIMAL_MAP_MODE,
    )

    waypoints = contract.metric_map()["inspection_waypoints"]
    for waypoint in waypoints[:-1]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        contract.observe()

    early_done = contract.done("almost finished minimal sweep")

    assert early_done["ok"] is False
    assert early_done["error_reason"] == "insufficient_sweep_coverage"
    assert early_done["next_waypoint_id"] == waypoints[-1]["waypoint_id"]
    assert early_done["observed_waypoint_count"] == len(waypoints) - 1
    assert early_done["total_waypoints"] == len(waypoints)
    assert all(item.startswith("generated_") for item in early_done["unvisited_waypoint_ids"])

    contract.navigate_to_waypoint(str(waypoints[-1]["waypoint_id"]))
    contract.observe()
    done = contract.done("finished minimal sweep")

    assert done["ok"] is True


def test_realworld_detected_handle_can_be_cleaned_without_private_manifest() -> None:
    contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
    fixture_hints = contract.fixture_hints()
    detection = _first_detection_by_category(contract, "dish")
    target_fixture = infer_target_fixture_for_detection(detection, fixture_hints)

    assert target_fixture is not None
    navigated_object = contract.navigate_to_object(detection["object_id"])
    picked = contract.pick(detection["object_id"])
    navigated_target = contract.navigate_to_receptacle(str(target_fixture["fixture_id"]))
    placed = contract.place(str(target_fixture["fixture_id"]))

    assert navigated_object["ok"] is True
    assert picked["ok"] is True
    assert picked["object_id"].startswith("observed_")
    assert navigated_target["ok"] is True
    assert placed["ok"] is True
    assert placed["fixture_id"] == "sink_01"


def test_realworld_contract_rejects_skipped_semantic_phases_without_private_truth() -> None:
    contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
    fixture_hints = contract.fixture_hints()
    detection = _first_detection_by_category(contract, "dish")
    target_fixture = infer_target_fixture_for_detection(detection, fixture_hints)
    assert target_fixture is not None

    skipped_pick = contract.pick(detection["object_id"])
    assert skipped_pick["ok"] is False
    assert skipped_pick["error_reason"] == "semantic_order"
    assert skipped_pick["required_tool"] == "navigate_to_object"
    assert skipped_pick["object_id"] == detection["object_id"]
    _assert_no_forbidden_keys(skipped_pick)

    assert contract.navigate_to_object(detection["object_id"])["ok"] is True
    assert contract.pick(detection["object_id"])["ok"] is True

    skipped_place = contract.place(str(target_fixture["fixture_id"]))
    assert skipped_place["ok"] is False
    assert skipped_place["error_reason"] == "semantic_order"
    assert skipped_place["required_tool"] == "navigate_to_receptacle"
    assert skipped_place["fixture_id"] == target_fixture["fixture_id"]
    _assert_no_forbidden_keys(skipped_place)

    assert contract.navigate_to_receptacle(str(target_fixture["fixture_id"]))["ok"] is True
    assert contract.place(str(target_fixture["fixture_id"]))["ok"] is True


def test_realworld_contract_rejects_done_with_pending_public_candidates() -> None:
    contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
    observation = _first_non_empty_observation(contract)
    recommended = next(
        item for item in observation["visible_object_detections"] if item["cleanup_recommended"]
    )

    done = contract.done("finished sweep")

    assert done["ok"] is False
    assert done["error_reason"] == "pending_cleanup_candidates"
    assert done["required_tool"] == "navigate_to_object"
    assert recommended["object_id"] in done["pending_observed_handles"]
    assert done["pending_cleanup_candidates"][0]["candidate_fixture_id"]
    assert "target_receptacle_id" not in str(done)
    _assert_no_forbidden_keys(done)


def test_realworld_contract_rejects_place_inside_before_opening_fridge() -> None:
    contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
    fixture_hints = contract.fixture_hints()
    detection = _first_detection_by_category(contract, "food")
    target_fixture = infer_target_fixture_for_detection(detection, fixture_hints)
    assert target_fixture is not None
    fixture_id = str(target_fixture["fixture_id"])

    assert fixture_id == "fridge_01"
    assert contract.navigate_to_object(detection["object_id"])["ok"] is True
    assert contract.pick(detection["object_id"])["ok"] is True
    assert contract.navigate_to_receptacle(fixture_id)["ok"] is True

    skipped_open = contract.place_inside(fixture_id)
    assert skipped_open["ok"] is False
    assert skipped_open["error_reason"] == "semantic_order"
    assert skipped_open["required_tool"] == "open_receptacle"
    _assert_no_forbidden_keys(skipped_open)

    assert contract.open_receptacle(fixture_id)["ok"] is True
    placed = contract.place_inside(fixture_id)
    closed = contract.close_receptacle(fixture_id)

    assert placed["ok"] is True
    assert placed["object_id"] == detection["object_id"]
    assert placed["location_relation"] == "inside"
    assert placed["placement_diagnostic"]["relation"] == "inside"
    assert closed["ok"] is True
    assert closed["tool"] == "close_receptacle"
    assert closed["object_id"] == detection["object_id"]


def test_realworld_contract_routes_bookshelf_as_inside_without_close() -> None:
    contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
    fixture_hints = contract.fixture_hints()
    detection = _first_detection_by_category(contract, "book")
    target_fixture = infer_target_fixture_for_detection(detection, fixture_hints)
    assert target_fixture is not None
    fixture_id = str(target_fixture["fixture_id"])

    assert fixture_id == "bookshelf_01"
    assert "place_inside" in target_fixture["affordances"]
    assert "open" not in target_fixture["affordances"]
    assert "close" not in target_fixture["affordances"]
    assert contract.navigate_to_object(detection["object_id"])["ok"] is True
    assert contract.pick(detection["object_id"])["ok"] is True
    assert contract.navigate_to_receptacle(fixture_id)["ok"] is True

    surface_place = contract.place(fixture_id)
    assert surface_place["ok"] is False
    assert surface_place["error_reason"] == "semantic_order"
    assert surface_place["required_tool"] == "place_inside"

    placed = contract.place_inside(fixture_id)
    assert placed["ok"] is True
    assert placed["location_relation"] == "inside"
    assert placed["placement_diagnostic"]["relation"] == "inside"

    skipped_close = contract.close_receptacle(fixture_id)
    assert skipped_close["ok"] is False
    assert skipped_close["required_tool"] == "place_inside"


def test_realworld_agent_view_payload_keeps_private_evaluation_out() -> None:
    contract = _contract(CleanupBackendSession(build_cleanup_scenario(seed=7)))

    contract.metric_map()
    for waypoint in contract.metric_map()["inspection_waypoints"]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        contract.observe()
    agent_view = contract.agent_view_payload()

    assert agent_view["forbidden_private_fields_absent"] is True
    assert agent_view["observed_objects"]
    assert "generated_mess_set" not in agent_view
    assert "acceptable_destination_sets" not in agent_view
    _assert_no_forbidden_keys(agent_view)


def test_realworld_raw_fpv_mode_suppresses_structured_detections() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = contract.metric_map()["inspection_waypoints"][0]
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    agent_view = contract.agent_view_payload()

    assert observation["perception_mode"] == RAW_FPV_ONLY_MODE
    assert observation["structured_detections_available"] is False
    assert observation["visible_object_detections"] == []
    assert observation["raw_fpv_observation"]["observation_id"].startswith("raw_fpv_")
    assert observation["raw_fpv_observation"]["image_artifacts"] == {}
    assert "inline_on_navigate" in observation["instruction"]
    assert "navigate_to_visual_candidate" in observation["instruction"]
    assert "declare_visual_candidates" not in observation["instruction"]
    assert agent_view["perception_mode"] == RAW_FPV_ONLY_MODE
    assert agent_view["structured_detections_available"] is False
    assert agent_view["observed_objects"] == []
    assert agent_view["raw_fpv_observations"]
    assert "support_estimate" not in str(agent_view["raw_fpv_observations"])
    assert "target_receptacle_id" not in str(agent_view["raw_fpv_observations"])
    _assert_no_forbidden_keys(observation)
    _assert_no_forbidden_keys(agent_view)


def test_realworld_raw_fpv_done_gate_scales_to_small_generated_mess_count() -> None:
    scenario = CleanupScenario(
        scenario_id="small-raw-fpv-done-gate-test",
        task="clean a small room",
        seed=7,
        objects=(
            CleanupObject("mug_01", "mug", "dish", "sofa_01"),
            CleanupObject("book_01", "book", "book", "floor_01"),
            CleanupObject("apple_01", "apple", "food", "desk_01"),
        ),
        receptacles=(
            CleanupReceptacle("sofa_01", "Sofa", "living"),
            CleanupReceptacle("floor_01", "Floor", "living", kind="surface"),
            CleanupReceptacle("desk_01", "Desk", "office", kind="surface"),
            CleanupReceptacle("sink_01", "Sink", "kitchen"),
            CleanupReceptacle("bookshelf_01", "Bookshelf", "living"),
            CleanupReceptacle("fridge_01", "Fridge", "kitchen"),
        ),
        private_manifest=PrivateScoringManifest(
            scenario_id="small-raw-fpv-done-gate-test",
            targets=(
                TargetRule("mug_01", ("sink_01",)),
                TargetRule("book_01", ("bookshelf_01",)),
                TargetRule("apple_01", ("fridge_01",)),
            ),
            success_threshold=2,
        ),
    )
    contract = _contract(
        CleanupBackendSession(scenario),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoints = contract.metric_map()["inspection_waypoints"]
    for waypoint in waypoints:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        contract.observe()

    contract._model_declared_observations = [{}, {}]  # noqa: SLF001
    shortfall = contract.done("small raw-fpv rehearsal shortfall")
    contract._model_declared_observations.append({})  # noqa: SLF001
    done = contract.done("small raw-fpv rehearsal complete")

    assert shortfall["ok"] is False
    assert shortfall["error_reason"] == "insufficient_model_declared_observations"
    assert shortfall["required_model_declared_observations"] == 3
    assert done["ok"] is True
    assert done["cleanup_status"] == "failed"


def test_realworld_raw_fpv_camera_adjustment_is_bounded_and_resets() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoints = contract.metric_map()["inspection_waypoints"]
    contract.navigate_to_waypoint(str(waypoints[0]["waypoint_id"]))
    adjusted = contract.adjust_camera(yaw_delta_deg=90, pitch_delta_deg=-90)
    observation = contract.observe()
    contract.navigate_to_waypoint(str(waypoints[1]["waypoint_id"]))
    reset_observation = contract.observe()

    assert adjusted["camera_offset"] == {"yaw_delta_deg": 45.0, "pitch_delta_deg": -20.0}
    assert observation["raw_fpv_observation"]["camera_offset"] == adjusted["camera_offset"]
    assert reset_observation["raw_fpv_observation"]["camera_offset"] == {
        "yaw_delta_deg": 0.0,
        "pitch_delta_deg": 0.0,
    }


def test_realworld_unresolved_model_declared_candidate_is_unpickable() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = contract.metric_map()["inspection_waypoints"][0]
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    declared = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"],
        candidates=[
            {
                "category": "imaginary widget",
                "target_fixture_id": "sink_01",
                "evidence_note": "ambiguous tiny object in the far corner",
                "image_region": {"type": "verbal_region", "value": "far corner"},
            }
        ],
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )
    candidate = declared["model_declared_observations"][0]
    picked = contract.pick(candidate["object_id"])

    assert candidate["grounding_status"] == "unresolved"
    assert picked["ok"] is False
    assert picked["error_reason"] == "visual_candidate_not_resolved"
    worklist_item = next(
        item
        for item in contract.cleanup_worklist_payload()["objects"]
        if item["object_id"] == candidate["object_id"]
    )
    assert worklist_item["state"] == "grounding_unresolved"
    assert worklist_item["cleanup_recommended"] is False
    assert candidate["private_truth_included"] is False
    _assert_no_forbidden_keys(declared)
    _assert_no_forbidden_keys(picked)


def test_realworld_done_does_not_require_unresolved_visual_candidates() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = contract.metric_map()["inspection_waypoints"][0]
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    for index in range(7):
        declared = contract.declare_visual_candidates(
            observation["raw_fpv_observation"]["observation_id"],
            candidates=[
                {
                    "category": f"imaginary widget {index}",
                    "target_fixture_id": "sink_01",
                    "evidence_note": "unresolved visual guess",
                    "image_region": {"type": "verbal_region", "value": f"far corner {index}"},
                }
            ],
            producer_type="main_cleanup_agent",
            producer_id="test_agent",
        )
        assert declared["model_declared_observations"][0]["grounding_status"] == "unresolved"

    early_done = contract.done("finished with unresolved false positives")

    assert early_done["ok"] is False
    assert early_done["error_reason"] == "insufficient_sweep_coverage"
    assert early_done["required_tool"] == "navigate_to_waypoint"
    assert early_done["next_waypoint_id"]
    assert early_done["sweep_coverage_rate"] < 0.90

    for waypoint in contract.metric_map()["inspection_waypoints"]:
        if waypoint["visited"]:
            continue
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        contract.observe()

    done = contract.done("finished with unresolved false positives")

    assert done["ok"] is True
    assert done["tool"] == "done"
    _assert_no_forbidden_keys(done)


def test_realworld_done_rejects_one_missing_public_waypoint() -> None:
    contract = _contract(
        CleanupBackendSession(
            CleanupScenario(
                scenario_id="missing-waypoint-gate-test",
                task="check full public sweep",
                seed=7,
                objects=(),
                receptacles=(
                    CleanupReceptacle("sink_01", "Sink", "kitchen", category="Sink"),
                    CleanupReceptacle("desk_01", "Desk", "office", category="Desk"),
                ),
                private_manifest=PrivateScoringManifest(
                    scenario_id="missing-waypoint-gate-test",
                    targets=(),
                    success_threshold=0,
                ),
            )
        ),
    )

    waypoints = contract.metric_map()["inspection_waypoints"]
    for waypoint in waypoints[:-1]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        contract.observe()

    early_done = contract.done("finished after almost all waypoints")

    assert early_done["ok"] is False
    assert early_done["error_reason"] == "insufficient_sweep_coverage"
    assert early_done["required_tool"] == "navigate_to_waypoint"
    assert early_done["next_waypoint_id"] == waypoints[-1]["waypoint_id"]
    assert early_done["observed_waypoint_count"] == len(waypoints) - 1
    assert early_done["total_waypoints"] == len(waypoints)


def test_realworld_navigate_to_visual_candidate_returns_grounded_handle() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["room_id"] == "work_area"
    )
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    response = contract.navigate_to_visual_candidate(
        observation["raw_fpv_observation"]["observation_id"],
        category="tomato",
        target_fixture_id="fridge_01",
        evidence_note="round produce item on the desk",
        image_region={"type": "verbal_region", "value": "front of desk"},
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    assert response["ok"] is True
    assert response["tool"] == "navigate_to_visual_candidate"
    assert response["object_id"].startswith("observed_")
    assert response["declaration_strategy"] == "inline_on_navigate"
    assert response["required_next_tool"] == "pick"
    assert response["model_declared_observation"]["grounding_status"] == "resolved"
    assert contract.pick(response["object_id"])["ok"] is True
    _assert_no_forbidden_keys(response)


def test_minimal_raw_fpv_visual_candidate_can_omit_target_fixture_id() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
        map_mode=MINIMAL_MAP_MODE,
    )

    fridge_waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["waypoint_id"] == "generated_exploration_003"
    )
    contract.navigate_to_waypoint(str(fridge_waypoint["waypoint_id"]))
    contract.observe()
    target_anchor_id = next(
        item["anchor_id"]
        for item in contract.agent_view_payload()["runtime_metric_map"]["public_semantic_anchors"]
        if item["anchor_type"] == "receptacle" and item["category"] == "fridge"
    )

    tomato_waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["waypoint_id"] == "generated_exploration_007"
    )
    contract.navigate_to_waypoint(str(tomato_waypoint["waypoint_id"]))
    observation = contract.observe()
    response = contract.navigate_to_visual_candidate(
        observation["raw_fpv_observation"]["observation_id"],
        category="tomato",
        evidence_note="round produce item on the desk",
        image_region={"type": "verbal_region", "value": "front of desk"},
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    declaration = response["model_declared_observation"]
    assert response["ok"] is True
    assert response["candidate_fixture_id"] == target_anchor_id
    assert response["candidate_fixture_category"] == "fridge"
    assert response["recommended_tool"] == "place_inside"
    assert declaration["target_fixture_id"] == target_anchor_id
    assert declaration["target_fixture_category"] == "fridge"
    assert declaration["target_plausibility"]["status"] == "plausible"
    assert declaration["target_plausibility"]["expected_fixture_id"] == target_anchor_id
    assert contract.pick(response["object_id"])["ok"] is True
    _assert_no_forbidden_keys(response)


def test_realworld_raw_fpv_rejects_already_handled_visual_candidate_without_navigation() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    work_waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["room_id"] == "work_area"
    )
    contract.navigate_to_waypoint(str(work_waypoint["waypoint_id"]))
    observation = contract.observe()
    raw_observation_id = observation["raw_fpv_observation"]["observation_id"]
    first = contract.navigate_to_visual_candidate(
        raw_observation_id,
        category="tomato",
        target_fixture_id="fridge_01",
        evidence_note="round produce item on the desk",
        image_region={"type": "verbal_region", "value": "front of desk"},
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )
    retry_before_place = contract.navigate_to_visual_candidate(
        raw_observation_id,
        category="tomato",
        target_fixture_id="fridge_01",
        evidence_note="same produce item before pick",
        image_region={"type": "verbal_region", "value": "front of desk"},
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    handle = first["object_id"]
    assert first["ok"] is True
    assert retry_before_place["ok"] is True
    assert retry_before_place["object_id"] == handle
    assert contract.pick(handle)["ok"] is True
    assert contract.navigate_to_receptacle("fridge_01")["ok"] is True
    assert contract.open_receptacle("fridge_01")["ok"] is True
    assert contract.place_inside("fridge_01")["ok"] is True
    assert contract.close_receptacle("fridge_01")["ok"] is True

    contract.navigate_to_waypoint(contract._preferred_waypoint_for_fixture("fridge_01"))
    later_observation = contract.observe()
    lifecycle_before = dict(contract._object_lifecycle[handle])
    current_handle_before = contract._current_object_handle
    held_handle_before = contract._held_handle
    duplicate = contract.navigate_to_visual_candidate(
        later_observation["raw_fpv_observation"]["observation_id"],
        category="food",
        target_fixture_id="fridge_01",
        evidence_note="produce-like object already in the fridge area",
        image_region={"type": "verbal_region", "value": "inside fridge area"},
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    assert duplicate["ok"] is False
    assert duplicate["error_reason"] == VISUAL_CANDIDATE_ALREADY_HANDLED_REASON
    assert duplicate["object_id"] == handle
    assert duplicate["required_next_tool"] == "observe"
    assert duplicate["model_declared_observation"]["actionability_status"] == "already_handled"
    assert contract._current_object_handle == current_handle_before
    assert contract._held_handle == held_handle_before
    assert contract._object_lifecycle[handle] == lifecycle_before
    _assert_no_forbidden_keys(duplicate)


def test_realworld_rejects_malformed_model_declared_candidate() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = contract.metric_map()["inspection_waypoints"][0]
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    declared = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"],
        candidates=[
            {
                "category": "mug",
                "target_fixture_id": "sink_01",
                "evidence_note": "small item near the sink",
                "image_region": {"type": "polygon", "value": [1, 2, 3]},
            }
        ],
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    assert declared["ok"] is False
    assert declared["error_reason"] == "invalid_visual_candidate"
    assert declared["candidate_error"]["field"] == "image_region.type"
    assert (
        contract.agent_view_payload()["model_declared_observation_evidence"]["observation_count"]
        == 0
    )
    _assert_no_forbidden_keys(declared)

    missing_target = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"],
        candidates=[
            {
                "category": "mug",
                "evidence_note": "small item near the sink",
                "image_region": {"type": "bbox", "value": [0.1, 0.1, 0.2, 0.2]},
            }
        ],
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    assert missing_target["ok"] is False
    assert missing_target["error_reason"] == "invalid_visual_candidate"
    assert missing_target["candidate_error"]["field"] == "target_fixture_id"
    _assert_no_forbidden_keys(missing_target)


def test_realworld_model_declared_grounding_accepts_public_category_families() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["room_id"] == "work_area"
    )
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    declared = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"],
        candidates=[
            {
                "category": "tomato",
                "target_fixture_id": "fridge_01",
                "evidence_note": "round produce item on the desk",
                "image_region": {"type": "verbal_region", "value": "front of desk"},
            }
        ],
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    candidate = declared["model_declared_observations"][0]
    assert candidate["grounding_status"] == "resolved"
    assert candidate["target_plausibility"]["status"] == "plausible"
    _assert_no_forbidden_keys(declared)


def test_realworld_model_declared_grounding_keeps_target_mismatch_as_metadata() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["room_id"] == "living_area"
    )
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    declared = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"],
        candidates=[
            {
                "category": "toy",
                "target_fixture_id": "bookshelf_01",
                "evidence_note": "toy-like object on the coffee table",
                "image_region": {"type": "verbal_region", "value": "coffee table"},
            }
        ],
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    candidate = declared["model_declared_observations"][0]
    assert candidate["grounding_status"] == "resolved"
    assert candidate["target_plausibility"]["status"] == "weak"
    assert candidate["target_plausibility"]["expected_fixture_id"] == "toy_bin_01"
    _assert_no_forbidden_keys(declared)


def test_realworld_model_declared_grounding_accepts_live_broad_categories() -> None:
    contract = _contract(
        CleanupBackendSession(_live_style_alias_scenario()),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = contract.metric_map()["inspection_waypoints"][0]
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()

    electronics = contract.navigate_to_visual_candidate(
        observation["raw_fpv_observation"]["observation_id"],
        category="electronics",
        target_fixture_id="tvstand_01",
        source_fixture_id="tvstand_01",
        evidence_note="black laptop on the sofa cushion",
        image_region={"type": "point", "value": [390, 230]},
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )
    toy = contract.navigate_to_visual_candidate(
        observation["raw_fpv_observation"]["observation_id"],
        category="toy",
        target_fixture_id="toybin_01",
        evidence_note="teddy bear plush on the sofa",
        image_region={"type": "verbal_region", "value": "sofa cushion"},
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    assert electronics["ok"] is True
    assert electronics["model_declared_observation"]["grounding_status"] == "resolved"
    assert (
        "source fixture hint did not match"
        in electronics["model_declared_observation"]["grounding_basis"]
    )
    assert electronics["candidate_fixture_id"] == "tvstand_01"
    assert electronics["recommended_tool"] == "place"
    assert toy["ok"] is True
    assert toy["model_declared_observation"]["grounding_status"] == "resolved"
    assert toy["candidate_fixture_id"] == "sofa_01"
    _assert_no_forbidden_keys(electronics)
    _assert_no_forbidden_keys(toy)


def test_realworld_raw_fpv_grounding_uses_same_room_fallback() -> None:
    contract = _contract(
        CleanupBackendSession(_same_room_fallback_scenario()),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["waypoint_id"] == "living_area_scan_1"
    )
    internal_waypoint = next(
        item for item in contract._waypoints if item["waypoint_id"] == waypoint["waypoint_id"]
    )
    assert "desk_01" in internal_waypoint["fixture_ids"]
    assert "shelf_01" not in internal_waypoint["fixture_ids"]

    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
    observation = contract.observe()
    response = contract.navigate_to_visual_candidate(
        observation["raw_fpv_observation"]["observation_id"],
        category="book",
        target_fixture_id="shelf_01",
        evidence_note="book visible on a neighboring shelf in the same room",
        image_region={"type": "verbal_region", "value": "right side shelf"},
        producer_type="main_cleanup_agent",
        producer_id="test_agent",
    )

    assert response["ok"] is True
    assert response["object_id"].startswith("observed_")
    declaration = response["model_declared_observation"]
    assert declaration["grounding_status"] == "resolved"
    assert "same-room object matched category" in declaration["grounding_basis"]
    _assert_no_forbidden_keys(response)


def test_realworld_camera_model_policy_registers_model_labelled_candidates() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )

    observation = {}
    candidate_response = {}
    for waypoint in contract.metric_map()["inspection_waypoints"]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
        candidate_response = contract.declare_visual_candidates(
            observation["raw_fpv_observation"]["observation_id"]
        )
        if candidate_response["camera_model_candidates"]:
            break
    agent_view = contract.agent_view_payload()

    assert observation["perception_mode"] == CAMERA_MODEL_POLICY_MODE
    assert observation["structured_detections_available"] is False
    assert observation["visible_object_detections"] == []
    assert observation["raw_fpv_observation"]["perception_mode"] == CAMERA_MODEL_POLICY_MODE
    assert candidate_response["ok"] is True
    assert candidate_response["visible_object_detections"] == []
    assert candidate_response["camera_model_candidates"]
    assert candidate_response["model_declared_observations"]
    candidate = candidate_response["camera_model_candidates"][0]
    assert candidate["object_id"].startswith("observed_")
    assert candidate["perception_source"] == "model_declared_observation"
    assert candidate["model_provenance"] == SIMULATED_CAMERA_MODEL_PROVENANCE
    assert candidate["source_observation_id"].startswith("raw_fpv_")
    assert candidate["support_estimate"]["source"] == "model_declared_observation"
    declaration = candidate_response["model_declared_observations"][0]
    assert declaration["source_observation_id"].startswith("raw_fpv_")
    assert declaration["producer_type"] == SIMULATED_CAMERA_MODEL_PROVENANCE
    assert declaration["grounding_status"] == "resolved"
    assert declaration["target_plausibility"]["status"] in {"plausible", "weak"}
    evidence = agent_view["camera_model_policy_evidence"]
    assert evidence["schema"] == CAMERA_MODEL_POLICY_SCHEMA
    assert evidence["enabled"] is True
    assert evidence["event_count"] >= 1
    assert evidence["candidate_count"] >= len(candidate_response["camera_model_candidates"])
    assert evidence["events"][0]["schema"] == "model_declared_observations_v1"
    model_evidence = agent_view["model_declared_observation_evidence"]
    assert model_evidence["schema"] == "model_declared_observations_v1"
    assert model_evidence["resolved_count"] >= 1
    assert agent_view["observed_objects"]
    _assert_no_forbidden_keys(observation)
    _assert_no_forbidden_keys(candidate_response)
    _assert_no_forbidden_keys(agent_view)


def test_realworld_camera_raw_empty_declare_does_not_fall_back_to_sim_labels() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=RAW_FPV_ONLY_MODE,
    )

    observation = contract.observe()
    response = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"],
    )

    assert response["ok"] is False
    assert response["error_reason"] == "empty_raw_fpv_candidate_registration"
    assert contract.model_declared_observations_payload()["observation_count"] == 0
    assert contract.camera_model_policy_payload()["event_count"] == 0
    _assert_no_forbidden_keys(response)


def test_realworld_camera_model_policy_records_sim_pipeline_provenance() -> None:
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )

    observation = contract.observe()
    response = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"]
    )
    evidence = response["model_declared_observation_evidence"]
    pipeline = evidence["visual_grounding_pipeline"]

    assert pipeline["pipeline_id"] == "sim"
    assert pipeline["stages"][0]["stage"] == "simulated_camera_model"
    assert pipeline["candidate_count"] == evidence["candidate_count"]
    assert contract.camera_model_policy_payload()["visual_grounding_pipeline_id"] == "sim"
    _assert_no_forbidden_keys(response)


def test_realworld_camera_labels_http_failure_is_visible_without_sim_fallback() -> None:
    client = _StaticVisualGroundingClient(
        {
            "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
            "status": "failed",
            "pipeline": {
                "pipeline_id": "fake-http",
                "stages": [
                    {
                        "stage": "proposer",
                        "producer_id": "fake-http",
                        "model_id": "fake",
                        "status": "timeout",
                        "latency_ms": 20,
                    }
                ],
            },
            "candidates": [],
            "error": {"reason": "timeout", "message": "fake timeout"},
        }
    )
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
        visual_grounding_client=client,
        visual_grounding_pipeline_id="fake-http",
    )
    waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["room_id"] == "kitchen"
    )
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))

    observation = contract.observe()
    response = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"]
    )
    evidence = response["model_declared_observation_evidence"]
    policy = contract.camera_model_policy_payload()

    assert response["ok"] is True
    assert response["model_declared_observations"] == []
    assert response["camera_model_candidates"] == []
    assert evidence["visual_grounding_pipeline"]["status"] == "failed"
    assert evidence["visual_grounding_pipeline"]["failure_reason"] == "timeout"
    assert evidence["candidate_count"] == 0
    assert policy["model_provenance"] == "external_visual_grounding_service"
    assert policy["visual_grounding_failure_count"] == 1
    assert contract.model_declared_observations_payload()["observation_count"] == 0
    _assert_no_forbidden_keys(response)


def test_realworld_camera_labels_http_success_uses_destination_resolver(
    tmp_path: Path,
) -> None:
    client = _StaticVisualGroundingClient(
        {
            "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
            "status": "ok",
            "pipeline": {
                "pipeline_id": "fake-http",
                "stages": [
                    {
                        "stage": "proposer",
                        "producer_id": "fake-http",
                        "model_id": "fake",
                        "status": "ok",
                        "latency_ms": 4,
                    }
                ],
            },
            "candidates": [
                {
                    "category": "dish",
                    "image_region": {"type": "bbox", "value": [0.1, 0.2, 0.3, 0.4]},
                    "confidence": 0.8,
                    "evidence_note": "fake dish on public camera frame",
                    "source_fixture_id": "counter_01",
                    "destination_hint": {
                        "candidate_fixture_id": "bookshelf_01",
                        "confidence": 0.9,
                    },
                }
            ],
        }
    )
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
        visual_grounding_client=client,
        visual_grounding_pipeline_id="fake-http",
        visual_grounding_artifact_base_dir=tmp_path,
    )
    waypoint = next(
        item
        for item in contract.metric_map()["inspection_waypoints"]
        if item["room_id"] == "kitchen"
    )
    contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))

    observation = contract.observe()
    image_path = tmp_path / "robot_views" / "raw_fpv_001.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (20, 10), (240, 240, 240)).save(image_path)
    contract._raw_fpv_observations[-1]["image_artifacts"] = {  # noqa: SLF001
        "fpv": "robot_views/raw_fpv_001.png"
    }
    response = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"]
    )
    declaration = response["model_declared_observations"][0]

    assert client.last_request is not None
    assert client.last_request["category_hints"] == VISUAL_GROUNDING_CATEGORY_HINTS
    assert client.last_request["image"]["bytes_base64"]
    assert client.last_request["image"]["width"] == 20
    assert client.last_request["image"]["height"] == 10
    assert declaration["producer_type"] == "external_visual_grounding_service"
    assert declaration["visual_grounding_pipeline"]["pipeline_id"] == "fake-http"
    assert declaration["visual_grounding_destination_hint"]["candidate_fixture_id"] == (
        "bookshelf_01"
    )
    assert declaration["target_fixture_id"] == "sink_01"
    assert declaration["visual_grounding_overlay"] == (
        "visual_grounding/overlays/raw_fpv_001/candidate_001.jpg"
    )
    assert (tmp_path / declaration["visual_grounding_overlay"]).is_file()
    assert (
        response["model_declared_observation_evidence"]["visual_grounding_pipeline"][
            "candidate_count"
        ]
        == 1
    )
    runtime_observed = contract.agent_view_payload()["runtime_metric_map"]["observed_objects"][0]
    assert runtime_observed["producer_type"] == "external_visual_grounding_service"
    assert runtime_observed["producer_id"] == "fake-http"
    assert runtime_observed["source_observation_id"] == declaration["source_observation_id"]
    assert runtime_observed["image_region"]["type"] == "bbox"
    _assert_no_forbidden_keys(response)


def test_realworld_camera_labels_http_destination_hint_is_evidence_only() -> None:
    client = _StaticVisualGroundingClient(
        {
            "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
            "status": "ok",
            "pipeline": {
                "pipeline_id": "fake-http",
                "stages": [
                    {
                        "stage": "proposer",
                        "producer_id": "fake-http",
                        "model_id": "fake",
                        "status": "ok",
                        "latency_ms": 4,
                    }
                ],
            },
            "candidates": [
                {
                    "category": "unknown_movable",
                    "image_region": {"type": "bbox", "value": [0.1, 0.2, 0.3, 0.4]},
                    "confidence": 0.7,
                    "evidence_note": "fake unknown item with service-suggested destination",
                    "source_fixture_id": "",
                    "destination_hint": {
                        "candidate_fixture_id": "bookshelf_01",
                        "confidence": 0.9,
                    },
                }
            ],
        }
    )
    contract = _contract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
        visual_grounding_client=client,
        visual_grounding_pipeline_id="fake-http",
    )

    observation = contract.observe()
    response = contract.declare_visual_candidates(
        observation["raw_fpv_observation"]["observation_id"]
    )
    declaration = response["model_declared_observations"][0]

    assert declaration["visual_grounding_destination_hint"]["candidate_fixture_id"] == (
        "bookshelf_01"
    )
    assert declaration["target_fixture_id"] == ""
    assert declaration["target_plausibility"]["status"] == "unknown_fixture"
    assert declaration["grounding_status"] == "unresolved"
    _assert_no_forbidden_keys(response)


def _assert_no_forbidden_keys(payload: object) -> None:
    if isinstance(payload, dict):
        forbidden = forbidden_agent_view_keys().intersection(payload)
        assert not forbidden
        for value in payload.values():
            _assert_no_forbidden_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_no_forbidden_keys(value)


class _StaticVisualGroundingClient:
    pipeline_id = "fake-http"
    config = type(
        "Config",
        (),
        {
            "auth_mode": "none",
            "proposer_id": "fake-http",
            "proposer_model_id": "fake",
            "refiner_id": "",
            "refiner_model_id": "",
        },
    )()

    def __init__(self, response: dict) -> None:
        self.response = response
        self.last_request: dict | None = None

    def request_candidates(self, request: dict) -> dict:
        self.last_request = request
        return self.response


def _first_non_empty_observation(contract: RealWorldCleanupContract) -> dict:
    for waypoint in contract.metric_map()["inspection_waypoints"]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
        if observation["visible_object_detections"]:
            return observation
    raise AssertionError("expected at least one visible object detection")


def _first_detection_by_category(
    contract: RealWorldCleanupContract,
    category: str,
) -> dict:
    for waypoint in contract.metric_map()["inspection_waypoints"]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
        for detection in observation["visible_object_detections"]:
            if detection["category"] == category:
                return detection
    raise AssertionError(f"expected visible detection with category {category}")


def _live_style_alias_scenario() -> CleanupScenario:
    return CleanupScenario(
        scenario_id="live-style-alias-test",
        task="clean broad raw camera declarations",
        seed=7,
        objects=(
            CleanupObject(
                object_id="laptop_01",
                name="Laptop (Laptop|surface|3|39)",
                category="Laptop",
                location_id="sofa_01",
            ),
            CleanupObject(
                object_id="teddybear_01",
                name="TeddyBear (TeddyBear|surface|3|35)",
                category="TeddyBear",
                location_id="sofa_01",
            ),
        ),
        receptacles=(
            CleanupReceptacle(
                receptacle_id="sofa_01",
                name="Sofa (Sofa|3|0|1)",
                room_area="living_area",
                category="Sofa",
            ),
            CleanupReceptacle(
                receptacle_id="toybin_01",
                name="ToyBin (ToyBin|3|2)",
                room_area="living_area",
                category="ToyBin",
            ),
            CleanupReceptacle(
                receptacle_id="tvstand_01",
                name="TVStand (TVStand|3|0|0)",
                room_area="living_area",
                category="TVStand",
            ),
        ),
        private_manifest=PrivateScoringManifest(
            scenario_id="live-style-alias-test",
            targets=(
                TargetRule("laptop_01", ("tvstand_01",)),
                TargetRule("teddybear_01", ("toybin_01",)),
            ),
            success_threshold=2,
        ),
    )


def _same_room_fallback_scenario() -> CleanupScenario:
    return CleanupScenario(
        scenario_id="same-room-fallback-test",
        task="clean raw camera declaration from neighboring fixture",
        seed=7,
        objects=(
            CleanupObject(
                object_id="book_01",
                name="Paperback Book",
                category="Book",
                location_id="shelf_01",
            ),
        ),
        receptacles=(
            CleanupReceptacle(
                receptacle_id="desk_01",
                name="Desk",
                room_area="living_area",
                category="Desk",
            ),
            CleanupReceptacle(
                receptacle_id="shelf_01",
                name="ShelvingUnit",
                room_area="living_area",
                category="ShelvingUnit",
            ),
        ),
        private_manifest=PrivateScoringManifest(
            scenario_id="same-room-fallback-test",
            targets=(TargetRule("book_01", ("shelf_01",)),),
            success_threshold=1,
        ),
    )


def _trace_response(tool: str, response: dict[str, object]) -> dict[str, object]:
    return {"event": "response", "tool": tool, "response": response}
