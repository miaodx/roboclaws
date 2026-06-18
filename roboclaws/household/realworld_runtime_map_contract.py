from __future__ import annotations

import copy
from typing import Any


def target_candidate_type_for_waypoint(waypoint: dict[str, Any]) -> str:
    source = str(waypoint.get("waypoint_source") or "")
    if source == "generated_exploration_candidate":
        return "generated_exploration_candidate"
    if source == "generated_target_inspection_candidate":
        return "generated_target_inspection_candidate"
    return "public_inspection_waypoint"


def runtime_map_producer_summary(
    observed_objects: list[dict[str, Any]],
    *,
    public_semantic_anchors: list[dict[str, Any]] | None = None,
    map_update_candidates: list[dict[str, Any]] | None = None,
    target_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    producers: dict[str, int] = {}
    for item in observed_objects:
        producer_type = str(item.get("producer_type") or "unknown")
        producers[producer_type] = producers.get(producer_type, 0) + 1
    anchors = public_semantic_anchors or []
    anchor_producers: dict[str, int] = {}
    for item in anchors:
        producer_type = str(item.get("producer_type") or "unknown")
        anchor_producers[producer_type] = anchor_producers.get(producer_type, 0) + 1
    return {
        "observed_object_count": len(observed_objects),
        "producer_types": producers,
        "public_semantic_anchor_count": len(anchors),
        "public_semantic_anchor_producer_types": anchor_producers,
        "target_candidate_count": len(target_candidates or []),
        "map_update_candidate_count": len(map_update_candidates or []),
    }


def runtime_observed_confidence(
    detection: dict[str, Any],
    declaration: dict[str, Any],
) -> float:
    for key in ("visibility_confidence", "grounding_confidence", "confidence"):
        value = detection.get(key)
        if value is None:
            value = declaration.get(key)
        try:
            return round(float(value), 6)
        except (TypeError, ValueError):
            continue
    return 0.0


def runtime_actionability(
    *,
    state: str,
    grounding_status: str,
    cleanup_recommended: bool,
) -> str:
    if state in {"held", "placed", "placed_closed", "stale", "skipped"}:
        return state
    if state in {"prior", "needs_confirm"}:
        return "needs_confirm"
    if grounding_status in {"ambiguous", "unresolved"}:
        return "needs_confirm"
    if cleanup_recommended and state in {"pending", "navigating_to_object"}:
        return "actionable"
    return state or "pending"


def synthetic_observation_id(handle: str, waypoint_id: Any) -> str:
    waypoint = str(waypoint_id or "")
    if waypoint:
        return f"visible_detection:{waypoint}:{handle}"
    return f"visible_detection:{handle}"


def runtime_static_map_payload(
    *,
    metric_map: dict[str, Any],
    static_fixture_projection: dict[str, Any],
    map_mode: str,
    minimal_map_mode: str,
    assert_no_forbidden_agent_view_keys: Any,
) -> dict[str, Any]:
    fixtures = []
    for room in static_fixture_projection.get("rooms") or []:
        room_id = str(room.get("room_id") or "")
        for fixture in room.get("fixtures") or []:
            item = {
                "fixture_id": str(fixture.get("fixture_id") or ""),
                "category": str(fixture.get("category") or ""),
                "name": str(fixture.get("name") or fixture.get("fixture_id") or ""),
                "room_id": str(fixture.get("room_id") or room_id),
                "affordances": list(fixture.get("affordances") or []),
                "pose": dict(fixture.get("pose") or {}),
                "preferred_inspection_waypoint_id": str(
                    fixture.get("preferred_inspection_waypoint_id") or ""
                ),
                "preferred_manipulation_waypoint_id": str(
                    fixture.get("preferred_manipulation_waypoint_id") or ""
                ),
            }
            assert_no_forbidden_agent_view_keys(item)
            fixtures.append(item)
    return {
        "rooms": [dict(item) for item in metric_map.get("rooms") or []],
        "fixtures": fixtures,
        "inspection_waypoints": [
            dict(item) for item in metric_map.get("inspection_waypoints") or []
        ],
        "driveable_ways": [dict(item) for item in metric_map.get("driveable_ways") or []],
        "map_bundle": dict(metric_map.get("map_bundle") or {}),
        "contains_runtime_observations": False,
        "map_mode": map_mode,
        "minimal_map_mode": map_mode == minimal_map_mode,
        "generated_exploration_candidates": [
            dict(item) for item in metric_map.get("generated_exploration_candidates") or []
        ],
    }


def runtime_prior_digital_twin_capabilities(
    snapshot: dict[str, Any] | None,
    *,
    assert_no_forbidden_agent_view_keys: Any,
) -> dict[str, Any]:
    if not snapshot:
        return {}
    runtime_map = snapshot if isinstance(snapshot.get("digital_twin_capabilities"), dict) else {}
    runtime_map = (
        snapshot.get("runtime_metric_map")
        if isinstance(snapshot.get("runtime_metric_map"), dict)
        else runtime_map
    )
    source_map = (
        snapshot.get("source_navigation_map")
        if isinstance(snapshot.get("source_navigation_map"), dict)
        else {}
    )
    capabilities = runtime_map.get("digital_twin_capabilities")
    if not isinstance(capabilities, dict):
        capabilities = source_map.get("digital_twin_capabilities")
    if not isinstance(capabilities, dict):
        return {}
    payload = copy.deepcopy(capabilities)
    assert_no_forbidden_agent_view_keys(payload)
    return payload


def digital_twin_capability_summary(capabilities: dict[str, Any]) -> dict[str, Any]:
    robot_proof = _capability_block(capabilities, "robot_consumption_proof")
    room_proof = _capability_block(capabilities, "room_semantic_projection_proof")
    render_proof = _capability_block(capabilities, "render_observation_proof")
    visual_route = _capability_block(render_proof, "default_visual_route")
    return {
        "robot_navigation_supported": bool(robot_proof.get("robot_navigation_supported")),
        "robot_consumption_status": str(robot_proof.get("status") or ""),
        "planner_backed_navigation_supported": bool(robot_proof.get("planner_backed")),
        "physical_robot_supported": bool(robot_proof.get("physical_robot")),
        "room_semantics_supported": bool(room_proof.get("room_semantics_supported")),
        "room_semantics_status": str(room_proof.get("status") or ""),
        "object_semantics_supported": bool(room_proof.get("object_semantics_supported")),
        "object_projection_status": str(room_proof.get("object_projection_status") or ""),
        "manipulation_supported": bool(robot_proof.get("manipulation_supported")),
        "render_observation_supported": bool(render_proof.get("render_observation_supported")),
        "render_observation_status": str(render_proof.get("status") or ""),
        "same_pose_fpv_supported": bool(render_proof.get("same_pose_fpv_supported")),
        "same_pose_chase_supported": bool(render_proof.get("same_pose_chase_supported")),
        "same_pose_topdown_supported": bool(render_proof.get("same_pose_topdown_supported")),
        "default_visual_route_status": str(visual_route.get("status") or ""),
        "default_visual_route_scene": str(visual_route.get("scene_root") or ""),
        "default_visual_route_selected": bool(visual_route.get("selected")),
    }


def _capability_block(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key) if isinstance(payload, dict) else {}
    return value if isinstance(value, dict) else {}


def runtime_observed_object_payload(
    *,
    handle: str,
    detection: dict[str, Any],
    worklist_item: dict[str, Any],
    object_lifecycle: dict[str, Any],
    sanitize_world_labels: bool,
    perception_mode: str,
    visible_object_detections_mode: str,
    sanitized_visible_object_detections_provenance: str,
    runtime_map_priors: list[dict[str, Any]],
    public_fixture_reference_id: Any,
    visual_evidence_for_handle: Any,
    candidate_actionability_status: Any,
    candidate_state: Any,
    public_destination_policy_for_category: Any,
    assert_no_forbidden_agent_view_keys: Any,
    norm: Any,
) -> dict[str, Any]:
    support = detection.get("support_estimate") or {}
    declaration = detection.get("model_declared_observation") or {}
    source_observation_id = str(
        detection.get("source_observation_id")
        or declaration.get("source_observation_id")
        or object_lifecycle.get("source_observation_id")
        or synthetic_observation_id(handle, object_lifecycle.get("waypoint_id", ""))
    )
    waypoint_id = str(
        worklist_item.get("last_waypoint_id")
        or declaration.get("waypoint_id")
        or object_lifecycle.get("waypoint_id")
        or ""
    )
    room_id = str(
        worklist_item.get("room_id")
        or declaration.get("room_id")
        or detection.get("current_room_id")
        or object_lifecycle.get("room_id")
        or ""
    )
    state = str(worklist_item.get("state") or object_lifecycle.get("state") or "pending")
    grounding_status = str(
        worklist_item.get("grounding_status")
        or detection.get("grounding_status")
        or declaration.get("grounding_status")
        or "resolved"
    )
    confidence = runtime_observed_confidence(detection, declaration)
    image_region = (
        detection.get("image_region")
        or declaration.get("image_region")
        or {"type": "bbox", "value": detection.get("image_bbox") or []}
    )
    producer_type = str(
        detection.get("producer_type")
        or declaration.get("producer_type")
        or detection.get("model_provenance")
        or detection.get("perception_source")
        or "visible_object_detections"
    )
    producer_id = str(
        detection.get("producer_id")
        or declaration.get("producer_id")
        or detection.get("model_provenance")
        or producer_type
    )
    actionability = runtime_actionability(
        state=state,
        grounding_status=grounding_status,
        cleanup_recommended=bool(worklist_item.get("cleanup_recommended"))
        and not sanitize_world_labels,
    )
    evidence = visual_evidence_for_handle(handle)
    candidate_input = {
        **detection,
        "visual_grounding_evidence": evidence,
        "grounding_status": grounding_status,
    }
    candidate_actionability = candidate_actionability_status(candidate_input)
    if actionability == "actionable" and candidate_actionability != "actionable":
        actionability = candidate_actionability
    candidate_fixture_id = ""
    candidate_source = "policy_required_destination_selection"
    producer_type = (
        sanitized_visible_object_detections_provenance
        if sanitize_world_labels and perception_mode == visible_object_detections_mode
        else producer_type
    )
    producer_id = (
        sanitized_visible_object_detections_provenance
        if sanitize_world_labels and perception_mode == visible_object_detections_mode
        else producer_id
    )
    if not sanitize_world_labels:
        candidate_fixture_id = str(
            public_fixture_reference_id(str(worklist_item.get("candidate_fixture_id") or ""))
        )
        candidate_source = str(
            worklist_item.get("candidate_source")
            or detection.get("candidate_source")
            or "public_category_fixture_affordance"
        )
    payload = {
        "object_id": handle,
        "category": str(detection.get("category") or worklist_item.get("category") or ""),
        "room_id": room_id,
        "waypoint_id": waypoint_id,
        "source_fixture_id": str(
            public_fixture_reference_id(
                str(worklist_item.get("source_fixture_id") or support.get("fixture_id") or "")
            )
        ),
        "source_observation_id": source_observation_id,
        "image_region": image_region,
        "visual_grounding_evidence": evidence,
        "producer_type": producer_type,
        "producer_id": producer_id,
        "confidence": confidence,
        "freshness": str(detection.get("freshness") or "current_run"),
        "actionability": actionability,
        "actionability_status": candidate_actionability,
        "candidate_state": candidate_state(candidate_input),
        "state": state,
        "grounding_status": grounding_status,
        "candidate_fixture_id": candidate_fixture_id,
        "candidate_source": candidate_source,
    }
    if sanitize_world_labels:
        payload["destination_policy_status"] = "policy_required"
        payload["destination_policy"] = public_destination_policy_for_category(
            payload.get("category")
        )
    if detection.get("prior_object_id"):
        payload["prior_object_id"] = str(detection["prior_object_id"])
    if detection.get("snapshot_object_id"):
        payload["snapshot_object_id"] = str(detection["snapshot_object_id"])
    prior = matching_runtime_map_prior(payload, runtime_map_priors, norm=norm)
    if prior is not None:
        payload["prior_object_id"] = str(prior.get("prior_object_id") or "")
        payload["snapshot_object_id"] = str(prior.get("snapshot_object_id") or "")
        payload["prior_match_basis"] = "category_room_source_fixture"
    assert_no_forbidden_agent_view_keys(payload)
    return payload


def matching_runtime_map_prior(
    current: dict[str, Any],
    runtime_map_priors: list[dict[str, Any]],
    *,
    norm: Any,
) -> dict[str, Any] | None:
    category = norm(current.get("category"))
    room_id = str(current.get("room_id") or "")
    source_fixture_id = str(current.get("source_fixture_id") or "")
    for prior in runtime_map_priors:
        if norm(prior.get("category")) != category:
            continue
        if str(prior.get("room_id") or "") != room_id:
            continue
        if str(prior.get("source_fixture_id") or "") != source_fixture_id:
            continue
        return prior
    return None


def runtime_map_priors_from_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    float_or_zero: Any,
    assert_no_forbidden_agent_view_keys: Any,
) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    priors = []
    for index, item in enumerate(snapshot.get("observed_objects") or [], start=1):
        if not isinstance(item, dict):
            continue
        prior_object_id = str(item.get("object_id") or f"prior_{index:03d}")
        prior = {
            "object_id": prior_object_id,
            "prior_row_id": f"prior_{index:03d}",
            "prior_object_id": prior_object_id,
            "snapshot_object_id": prior_object_id,
            "category": str(item.get("category") or ""),
            "room_id": str(item.get("room_id") or ""),
            "waypoint_id": str(item.get("waypoint_id") or ""),
            "source_fixture_id": str(item.get("source_fixture_id") or ""),
            "source_observation_id": str(item.get("source_observation_id") or ""),
            "image_region": item.get("image_region") or {},
            "producer_type": str(item.get("producer_type") or ""),
            "producer_id": str(item.get("producer_id") or ""),
            "confidence": float_or_zero(item.get("confidence")),
            "freshness": "prior",
            "actionability": "needs_confirm",
            "state": "prior",
            "grounding_status": str(item.get("grounding_status") or "prior"),
            "candidate_fixture_id": str(item.get("candidate_fixture_id") or ""),
            "candidate_source": str(item.get("candidate_source") or "runtime_metric_map_snapshot"),
        }
        assert_no_forbidden_agent_view_keys(prior)
        priors.append(prior)
    return priors


def runtime_map_anchor_priors_from_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    float_or_zero: Any,
    assert_no_forbidden_agent_view_keys: Any,
) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    anchors = []
    for index, item in enumerate(snapshot.get("public_semantic_anchors") or [], start=1):
        if not isinstance(item, dict):
            continue
        anchor = {
            "anchor_id": str(item.get("anchor_id") or f"prior_anchor_{index:03d}"),
            "prior_anchor_id": str(item.get("anchor_id") or f"prior_anchor_{index:03d}"),
            "anchor_type": str(item.get("anchor_type") or ""),
            "category": str(item.get("category") or ""),
            "label": str(item.get("label") or ""),
            "room_id": str(item.get("room_id") or ""),
            "waypoint_id": str(item.get("waypoint_id") or ""),
            "pose": dict(item.get("pose") or {}),
            "affordances": list(item.get("affordances") or []),
            "producer_type": str(item.get("producer_type") or ""),
            "producer_id": str(item.get("producer_id") or ""),
            "confidence": float_or_zero(item.get("confidence")),
            "freshness": "prior",
            "actionability": str(item.get("actionability") or ""),
            "reachability_status": str(item.get("reachability_status") or ""),
            "classification_status": str(item.get("classification_status") or ""),
            "source_observation_id": str(item.get("source_observation_id") or ""),
            "promotion_status": "prior_runtime_snapshot",
            "evidence": dict(item.get("evidence") or {}),
        }
        assert_no_forbidden_agent_view_keys(anchor)
        anchors.append(anchor)
    return anchors


def runtime_map_room_priors_from_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    public_room_hint_payload: Any,
    assert_no_forbidden_agent_view_keys: Any,
) -> list[dict[str, Any]]:
    if not snapshot:
        return []
    rooms = []
    for item in snapshot.get("rooms") or []:
        if not isinstance(item, dict):
            continue
        room = public_room_hint_payload(item)
        assert_no_forbidden_agent_view_keys(room)
        rooms.append(room)
    return rooms


def infer_target_fixture_for_detection(
    detection: dict[str, Any],
    static_fixture_projection: dict[str, Any],
    *,
    norm: Any,
    object_category_targets: Any,
    first_matching_fixture: Any,
    fixture_requires_open: Any,
) -> dict[str, Any] | None:
    direct_candidate = target_fixture_from_detection_anchor(
        detection,
        fixture_requires_open=fixture_requires_open,
    )
    if direct_candidate is not None:
        return direct_candidate
    fixture_candidates = [
        fixture
        for room in static_fixture_projection.get("rooms", [])
        for fixture in room.get("fixtures", [])
        if isinstance(fixture, dict)
    ]
    object_terms = {
        norm(detection.get("category")),
        norm(detection.get("name")),
    }
    for object_aliases, fixture_aliases in object_category_targets:
        if not any(alias in term for alias in object_aliases for term in object_terms):
            continue
        for fixture_alias in fixture_aliases:
            match = first_matching_fixture(fixture_candidates, fixture_alias)
            if match is not None:
                return match
    return None


def target_fixture_from_detection_anchor(
    detection: dict[str, Any],
    *,
    fixture_requires_open: Any,
) -> dict[str, Any] | None:
    fixture_id = str(detection.get("candidate_fixture_id") or "")
    if not fixture_id.startswith("anchor_fixture_"):
        return None
    category = str(detection.get("candidate_fixture_category") or "")
    tool = str(detection.get("recommended_tool") or "")
    affordances = ["observe", "place"]
    if tool == "place_inside" or fixture_requires_open({"category": category}):
        affordances.append("place_inside")
    if fixture_requires_open({"category": category}):
        affordances.extend(["open", "close"])
    waypoint_id = str(detection.get("waypoint_id") or "")
    return {
        "fixture_id": fixture_id,
        "receptacle_id": fixture_id,
        "category": category,
        "name": category or fixture_id,
        "room_id": str(detection.get("current_room_id") or ""),
        "affordances": affordances,
        "preferred_inspection_waypoint_id": waypoint_id,
        "preferred_manipulation_waypoint_id": waypoint_id,
        "public_fixture_source": "runtime_semantic_anchor",
    }
