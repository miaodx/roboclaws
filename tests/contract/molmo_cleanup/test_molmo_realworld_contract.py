from __future__ import annotations

from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_SCHEMA,
    CLEANUP_WORKLIST_SCHEMA,
    RAW_FPV_ONLY_MODE,
    REAL_ROBOT_MAP_BUNDLE_SCHEMA,
    REALWORLD_CONTRACT,
    SIMULATED_CAMERA_MODEL_PROVENANCE,
    RealWorldCleanupContract,
    forbidden_agent_view_keys,
    infer_target_fixture_for_detection,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario


def test_realworld_public_tools_do_not_expose_private_targets_or_global_inventory() -> None:
    contract = RealWorldCleanupContract(MolmoCleanupToolContract(build_cleanup_scenario(seed=7)))

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
        assert "target_receptacle_id" not in detection
        assert "is_misplaced" not in detection
    _assert_no_forbidden_keys(metric_map)
    _assert_no_forbidden_keys(fixture_hints)
    _assert_no_forbidden_keys(observation)


def test_realworld_contract_exposes_nav2_shaped_public_map_and_provenance() -> None:
    contract = RealWorldCleanupContract(MolmoCleanupToolContract(build_cleanup_scenario(seed=7)))

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

    assert metric_map["schema"] == REAL_ROBOT_MAP_BUNDLE_SCHEMA
    assert metric_map["frame_id"] == "map"
    assert metric_map["origin"] == {"x": 0.0, "y": 0.0, "yaw": 0.0}
    assert metric_map["occupancy_values"] == {"unknown": -1, "free": 0, "occupied": 100}
    assert waypoint["frame_id"] == "map"
    assert waypoint["purpose"] == "fixture_coverage"
    assert waypoint["waypoint_source"] == "static_map_coverage"
    assert fixture_hints["schema"] == "static_fixture_semantic_map_v1"
    assert fixture_hints["contains_runtime_observations"] is False
    assert "observations" not in fixture_hints
    assert waypoint_nav["navigation_backend"] == "api_semantic"
    assert waypoint_nav["pose_source"] == "inspection_waypoint"
    assert object_nav["navigation_backend"] == "api_semantic"
    assert object_nav["pose_source"] == "latest_observation"
    assert object_nav["requires_reobserve"] is False
    assert receptacle_nav["navigation_backend"] == "api_semantic"
    assert receptacle_nav["pose_source"] == "fixture_semantic_map"
    assert agent_view["policy_view"]["chase_camera_policy_input"] is False
    assert agent_view["cleanup_worklist"]["schema"] == CLEANUP_WORKLIST_SCHEMA
    assert agent_view["cleanup_worklist"]["objects"][0]["state"] == "held"
    _assert_no_forbidden_keys(agent_view)


def test_realworld_detected_handle_can_be_cleaned_without_private_manifest() -> None:
    contract = RealWorldCleanupContract(MolmoCleanupToolContract(build_cleanup_scenario(seed=7)))
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
    contract = RealWorldCleanupContract(MolmoCleanupToolContract(build_cleanup_scenario(seed=7)))
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


def test_realworld_contract_rejects_place_inside_before_opening_fridge() -> None:
    contract = RealWorldCleanupContract(MolmoCleanupToolContract(build_cleanup_scenario(seed=7)))
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
    assert contract.place_inside(fixture_id)["ok"] is True


def test_realworld_agent_view_payload_keeps_private_evaluation_out() -> None:
    contract = RealWorldCleanupContract(MolmoCleanupToolContract(build_cleanup_scenario(seed=7)))

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
    contract = RealWorldCleanupContract(
        MolmoCleanupToolContract(build_cleanup_scenario(seed=7)),
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
    assert agent_view["perception_mode"] == RAW_FPV_ONLY_MODE
    assert agent_view["structured_detections_available"] is False
    assert agent_view["observed_objects"] == []
    assert agent_view["raw_fpv_observations"]
    assert "support_estimate" not in str(agent_view["raw_fpv_observations"])
    assert "target_receptacle_id" not in str(agent_view["raw_fpv_observations"])
    _assert_no_forbidden_keys(observation)
    _assert_no_forbidden_keys(agent_view)


def test_realworld_camera_model_policy_registers_model_labelled_candidates() -> None:
    contract = RealWorldCleanupContract(
        MolmoCleanupToolContract(build_cleanup_scenario(seed=7)),
        perception_mode=CAMERA_MODEL_POLICY_MODE,
    )

    observation = {}
    candidate_response = {}
    for waypoint in contract.metric_map()["inspection_waypoints"]:
        contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        observation = contract.observe()
        candidate_response = contract.infer_camera_model_candidates(
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
    candidate = candidate_response["camera_model_candidates"][0]
    assert candidate["object_id"].startswith("observed_")
    assert candidate["perception_source"] == CAMERA_MODEL_POLICY_MODE
    assert candidate["model_provenance"] == SIMULATED_CAMERA_MODEL_PROVENANCE
    assert candidate["source_observation_id"].startswith("raw_fpv_")
    assert candidate["support_estimate"]["source"] == CAMERA_MODEL_POLICY_MODE
    evidence = agent_view["camera_model_policy_evidence"]
    assert evidence["schema"] == CAMERA_MODEL_POLICY_SCHEMA
    assert evidence["enabled"] is True
    assert evidence["event_count"] >= 1
    assert evidence["candidate_count"] >= len(candidate_response["camera_model_candidates"])
    assert agent_view["observed_objects"]
    _assert_no_forbidden_keys(observation)
    _assert_no_forbidden_keys(candidate_response)
    _assert_no_forbidden_keys(agent_view)


def _assert_no_forbidden_keys(payload: object) -> None:
    if isinstance(payload, dict):
        forbidden = forbidden_agent_view_keys().intersection(payload)
        assert not forbidden
        for value in payload.values():
            _assert_no_forbidden_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_no_forbidden_keys(value)


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
