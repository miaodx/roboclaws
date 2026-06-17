from __future__ import annotations

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
    fixture_hints: dict[str, Any],
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
        for room in fixture_hints.get("rooms", [])
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
