from __future__ import annotations

from roboclaws.molmo_cleanup.backend_contract import CleanupBackendSession
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
from roboclaws.molmo_cleanup.types import (
    CleanupObject,
    CleanupReceptacle,
    CleanupScenario,
    PrivateScoringManifest,
    TargetRule,
)


def test_realworld_public_tools_do_not_expose_private_targets_or_global_inventory() -> None:
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))

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


def test_realworld_contract_exposes_nav2_shaped_public_map_and_provenance() -> None:
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))

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
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
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
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
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
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
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
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
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
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))
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
    contract = RealWorldCleanupContract(CleanupBackendSession(build_cleanup_scenario(seed=7)))

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


def test_realworld_raw_fpv_camera_adjustment_is_bounded_and_resets() -> None:
    contract = RealWorldCleanupContract(
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
    contract = RealWorldCleanupContract(
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
    contract = RealWorldCleanupContract(
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


def test_realworld_navigate_to_visual_candidate_returns_grounded_handle() -> None:
    contract = RealWorldCleanupContract(
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


def test_realworld_rejects_malformed_model_declared_candidate() -> None:
    contract = RealWorldCleanupContract(
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


def test_realworld_model_declared_grounding_accepts_public_category_families() -> None:
    contract = RealWorldCleanupContract(
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
    contract = RealWorldCleanupContract(
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
    contract = RealWorldCleanupContract(
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


def test_realworld_camera_model_policy_registers_model_labelled_candidates() -> None:
    contract = RealWorldCleanupContract(
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
