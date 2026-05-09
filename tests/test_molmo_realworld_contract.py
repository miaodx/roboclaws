from __future__ import annotations

from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.realworld_contract import (
    REALWORLD_CONTRACT,
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


def test_realworld_detected_handle_can_be_cleaned_without_private_manifest() -> None:
    contract = RealWorldCleanupContract(MolmoCleanupToolContract(build_cleanup_scenario(seed=7)))
    fixture_hints = contract.fixture_hints()
    detection = _first_detection_by_category(contract, "dish")
    target_fixture = infer_target_fixture_for_detection(detection, fixture_hints)

    assert target_fixture is not None
    picked = contract.pick(detection["object_id"])
    placed = contract.place(str(target_fixture["fixture_id"]))

    assert picked["ok"] is True
    assert picked["object_id"].startswith("observed_")
    assert placed["ok"] is True
    assert placed["fixture_id"] == "sink_01"


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
