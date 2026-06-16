from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from roboclaws.household import realworld_contract_projection, realworld_visual_candidates
from roboclaws.household.visual_scan_guidance import visual_evidence_recovery_hint

MINIMAL_MAP_MODE = "minimal"
MODEL_DECLARED_OBSERVATION_SCHEMA = "model_declared_observation_v1"
MODEL_DECLARED_OBSERVATION_SOURCE = "model_declared_observation"
CANDIDATE_STATE_NAVIGATION_AUTHORIZED = (
    realworld_visual_candidates.CANDIDATE_STATE_NAVIGATION_AUTHORIZED
)
CANDIDATE_STATE_VISUAL_SCAN_REQUIRED = (
    realworld_visual_candidates.CANDIDATE_STATE_VISUAL_SCAN_REQUIRED
)
VISUAL_EVIDENCE_REQUIRED_ACTIONABILITY = (
    realworld_visual_candidates.VISUAL_EVIDENCE_REQUIRED_ACTIONABILITY
)
_NON_ACTIONABLE_HANDLE_STATES = frozenset({"placed", "placed_closed", "skipped", "stale"})
_recommended_place_tool = realworld_contract_projection._recommended_place_tool
_room_id = realworld_contract_projection._room_id


def register_model_declared_candidate(
    contract: Any,
    *,
    raw_observation: dict[str, Any],
    waypoint: dict[str, Any],
    candidate: dict[str, Any],
    producer_type: str,
    producer_id: str,
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any]:
    normalized = normalized_visual_candidate(
        contract,
        raw_observation=raw_observation,
        candidate=candidate,
        producer_type=producer_type,
        producer_id=producer_id,
    )
    match = resolve_visual_candidate(contract, waypoint, normalized)
    declaration = declaration_from_resolution(
        contract,
        normalized,
        match,
        assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
    )
    handle = str(declaration["object_id"])
    if match["status"] == "already_handled":
        return dict(declaration)
    if match["status"] == "resolved":
        _register_resolved_detection(
            contract,
            raw_observation=raw_observation,
            waypoint=waypoint,
            declaration=declaration,
            match=match,
            handle=handle,
            producer_type=producer_type,
            producer_id=producer_id,
            assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
        )
    else:
        _register_unresolved_detection(contract, waypoint=waypoint, declaration=declaration)
    contract._model_declared_observations.append(declaration)
    return dict(declaration)


def _register_resolved_detection(
    contract: Any,
    *,
    raw_observation: dict[str, Any],
    waypoint: dict[str, Any],
    declaration: dict[str, Any],
    match: dict[str, Any],
    handle: str,
    producer_type: str,
    producer_id: str,
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> None:
    obj = match["objects"][0]
    location_id = str(match["location_ids"][0])
    detection = detection_for_object_at_location(
        contract,
        obj,
        location_id=location_id,
        handle=handle,
        waypoint=waypoint,
        perception_source=MODEL_DECLARED_OBSERVATION_SOURCE,
        producer_type=producer_type,
        source_observation_id=str(raw_observation["observation_id"]),
        assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
    )
    detection.update(
        {
            "model_declared_observation": declaration,
            "model_declared_observation_id": declaration["declaration_id"],
            "producer_type": producer_type,
            "producer_id": producer_id,
            "image_region": declaration["image_region"],
            "evidence_note": declaration["evidence_note"],
            "grounding_status": declaration["grounding_status"],
            "grounding_confidence": declaration["grounding_confidence"],
            "grounding_basis": declaration["grounding_basis"],
            "visual_grounding_evidence": declaration["visual_grounding_evidence"],
        }
    )
    evidence = declaration["visual_grounding_evidence"]
    if isinstance(evidence, dict):
        detection["image_bbox"] = list(evidence.get("image_bbox") or [])
        detection["locality_status"] = str(
            evidence.get("locality_status") or "same_waypoint_source_observation"
        )
    _refresh_candidate_state(detection)
    detection.update(contract._public_candidate_hint(detection))
    _refresh_candidate_state(detection)
    if isinstance(detection.get("visual_grounding_evidence"), dict):
        detection["visual_grounding_evidence"]["candidate_state"] = detection["candidate_state"]
        detection["visual_grounding_evidence"]["actionability_status"] = detection[
            "actionability_status"
        ]
    assert_no_forbidden_agent_view_keys(detection)
    contract._detections_by_handle[handle] = detection
    contract._record_detection_lifecycle(handle, detection, waypoint)


def _refresh_candidate_state(detection: dict[str, Any]) -> None:
    detection["candidate_state"] = realworld_visual_candidates._candidate_state(detection)
    detection["candidate_state_history"] = realworld_visual_candidates._candidate_state_history(
        detection["candidate_state"]
    )
    detection["actionability_status"] = candidate_actionability_status(detection)


def _register_unresolved_detection(
    contract: Any,
    *,
    waypoint: dict[str, Any],
    declaration: dict[str, Any],
) -> None:
    handle = str(declaration["object_id"])
    contract._detections_by_handle[handle] = {
        "object_id": handle,
        "category": declaration["category"],
        "current_room_id": declaration["room_id"],
        "perception_source": MODEL_DECLARED_OBSERVATION_SOURCE,
        "model_declared_observation": declaration,
        "model_declared_observation_id": declaration["declaration_id"],
        "producer_type": declaration["producer_type"],
        "producer_id": declaration["producer_id"],
        "source_observation_id": declaration["source_observation_id"],
        "image_region": declaration["image_region"],
        "evidence_note": declaration["evidence_note"],
        "grounding_status": declaration["grounding_status"],
        "grounding_confidence": declaration["grounding_confidence"],
        "grounding_basis": declaration["grounding_basis"],
        "recovery_hint": declaration["recovery_hint"],
        "target_fixture_id": declaration["target_fixture_id"],
        "target_fixture_category": declaration["target_fixture_category"],
        "target_plausibility": declaration["target_plausibility"],
        "visual_grounding_evidence": declaration["visual_grounding_evidence"],
        "actionability_status": declaration["actionability_status"],
        "candidate_state": declaration["candidate_state"],
        "candidate_state_history": declaration["candidate_state_history"],
    }
    contract._set_handle_state(
        handle,
        f"grounding_{declaration['grounding_status']}",
        tool="declare_visual_candidates",
        waypoint_id=str(waypoint["waypoint_id"]),
        room_id=str(waypoint["room_id"]),
        source_fixture_id=declaration.get("source_fixture_id", ""),
        category=declaration["category"],
        perception_source=MODEL_DECLARED_OBSERVATION_SOURCE,
        grounding_status=declaration["grounding_status"],
    )


def normalized_visual_candidate(
    contract: Any,
    *,
    raw_observation: dict[str, Any],
    candidate: dict[str, Any],
    producer_type: str,
    producer_id: str,
) -> dict[str, Any]:
    image_region = realworld_visual_candidates._normalize_image_region(
        candidate.get("image_region")
    )
    category = str(candidate.get("category") or "object").strip() or "object"
    target_fixture_id = str(candidate.get("target_fixture_id") or "")
    target_resolution_source = "model_declared_target_fixture"
    if not target_fixture_id:
        target_fixture_id = contract._resolve_runtime_anchor_target_fixture_id(category)
        if target_fixture_id:
            target_resolution_source = "runtime_metric_map_public_semantic_anchor"
    target_fixture = contract._fixtures.get(
        contract.internal_fixture_id_for_public_reference(target_fixture_id) or target_fixture_id,
        {},
    )
    confidence = candidate.get("confidence")
    try:
        confidence_value = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence_value = None
    return {
        "source_observation_id": str(raw_observation["observation_id"]),
        "waypoint_id": str(raw_observation["waypoint_id"]),
        "room_id": str(raw_observation["room_id"]),
        "category": category,
        "target_fixture_id": target_fixture_id,
        "target_fixture_category": str(
            target_fixture.get("category") or target_fixture.get("name") or ""
        ),
        "target_fixture_resolution_source": target_resolution_source
        if target_fixture_id
        else "unresolved",
        "source_fixture_id": str(candidate.get("source_fixture_id") or ""),
        "evidence_note": str(candidate.get("evidence_note") or ""),
        "image_region": image_region,
        "confidence": confidence_value,
        "producer_type": str(candidate.get("producer_type") or producer_type),
        "producer_id": str(candidate.get("producer_id") or producer_id),
        "supersedes_observation_id": str(candidate.get("supersedes_observation_id") or ""),
        "visual_grounding_pipeline": candidate.get("visual_grounding_pipeline") or {},
        "visual_grounding_stage_provenance": list(
            candidate.get("visual_grounding_stage_provenance") or []
        ),
        "visual_grounding_destination_hint": candidate.get("visual_grounding_destination_hint")
        or {},
        "tracking": candidate.get("tracking") or {},
        "image_dimensions": candidate.get("image_dimensions") or {},
        "visual_grounding_overlay": str(candidate.get("visual_grounding_overlay") or ""),
    }


def resolve_visual_candidate(
    contract: Any,
    waypoint: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    category_norm = _norm(candidate.get("category"))
    source_fixture_id = str(candidate.get("source_fixture_id") or "")
    match = visual_candidate_match_for_source(
        contract,
        waypoint,
        category_norm=category_norm,
        source_fixture_id=source_fixture_id,
        restrict_to_waypoint_fixtures=True,
    )
    match["locality_status"] = (
        "exact_source_fixture_in_source_observation"
        if source_fixture_id and match["status"] != "unresolved"
        else "same_waypoint_source_observation"
        if match["status"] != "unresolved"
        else "source_observation_locality_unresolved"
    )
    if source_fixture_id and match["status"] == "unresolved":
        match["requested_source_fixture_id"] = source_fixture_id
    return match


def visual_candidate_match_for_source(
    contract: Any,
    waypoint: dict[str, Any],
    *,
    category_norm: str,
    source_fixture_id: str,
    restrict_to_waypoint_fixtures: bool,
) -> dict[str, Any]:
    candidates = []
    location_ids = []
    handled_candidates = []
    handled_location_ids = []
    visible = (
        objects_visible_from_waypoint(contract, waypoint)
        if restrict_to_waypoint_fixtures
        else objects_visible_from_room(contract, waypoint)
    )
    for obj, location_id in visible:
        if category_norm and not realworld_visual_candidates._declared_category_matches_object(
            category_norm,
            obj,
        ):
            continue
        if source_fixture_id and location_id != source_fixture_id:
            continue
        existing_handle = contract._observed_handles_by_object_id.get(obj.object_id)
        if existing_handle and handle_is_non_actionable(contract, existing_handle):
            handled_candidates.append(obj)
            handled_location_ids.append(location_id)
            continue
        candidates.append(obj)
        location_ids.append(location_id)
    if len(candidates) == 1:
        return {"status": "resolved", "objects": candidates, "location_ids": location_ids}
    if len(candidates) > 1:
        return {"status": "ambiguous", "objects": candidates, "location_ids": location_ids}
    if handled_candidates:
        return {
            "status": "already_handled",
            "objects": handled_candidates,
            "location_ids": handled_location_ids,
        }
    return {"status": "unresolved", "objects": [], "location_ids": []}


def declaration_from_resolution(
    contract: Any,
    candidate: dict[str, Any],
    match: dict[str, Any],
    *,
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any]:
    status = str(match["status"])
    objects = match.get("objects") or []
    if status == "resolved":
        handle = contract._handle_for_object(objects[0].object_id)
        basis = "single public camera-context object matched exact source observation locality"
        confidence = realworld_visual_candidates._grounding_confidence(candidate, "resolved")
        recovery_hint = ""
        grounding_status = "resolved"
        actionability_status = "actionable"
    elif status == "already_handled":
        handle = contract._handle_for_object(objects[0].object_id)
        lifecycle = contract._object_lifecycle.get(handle, {})
        basis = "only matching public camera-context object was already handled"
        confidence = realworld_visual_candidates._grounding_confidence(candidate, "unresolved")
        recovery_hint = (
            "The matching observed handle has already been placed or otherwise "
            "handled. Continue the waypoint sweep and observe for other objects."
        )
        grounding_status = "unresolved"
        actionability_status = "already_handled"
    else:
        handle = contract._new_unresolved_handle()
        basis = (
            "multiple public camera-context objects matched"
            if status == "ambiguous"
            else "no public camera-context object matched"
        )
        confidence = realworld_visual_candidates._grounding_confidence(candidate, status)
        recovery_hint = (
            "Provide a tighter bbox/point or source_fixture_id before picking."
            if status == "ambiguous"
            else (
                "No public actionable object matched this declaration. Retry at most once "
                "with a tighter image_region or clearer category, then continue the "
                "waypoint sweep instead of looping on this visible item."
            )
        )
        grounding_status = status
        actionability_status = "needs_clarification"
    target_fixture_id = str(candidate.get("target_fixture_id") or "")
    internal_target_fixture_id = (
        contract.internal_fixture_id_for_public_reference(target_fixture_id) or target_fixture_id
    )
    target_fixture = contract._fixtures.get(internal_target_fixture_id, {})
    visual_grounding_evidence = visual_grounding_evidence_for_candidate(
        {**candidate, "locality_status": match.get("locality_status", "")},
        fallback_image_bbox=candidate.get("image_bbox"),
        grounding_status=grounding_status,
        assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
    )
    if actionability_status == "actionable":
        actionability_status = candidate_actionability_status(
            {
                "visual_grounding_evidence": visual_grounding_evidence,
                "grounding_status": grounding_status,
            },
            assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
        )
        if actionability_status != "actionable":
            recovery_hint = visual_evidence_recovery_hint()
    target_plausibility = target_plausibility_for_candidate(
        contract,
        category=str(candidate.get("category") or ""),
        target_fixture_id=target_fixture_id,
    )
    declaration = {
        "schema": MODEL_DECLARED_OBSERVATION_SCHEMA,
        "declaration_id": f"declared_{len(contract._model_declared_observations) + 1:03d}",
        "object_id": handle,
        "source_observation_id": str(candidate["source_observation_id"]),
        "waypoint_id": str(candidate["waypoint_id"]),
        "room_id": str(candidate["room_id"]),
        "category": str(candidate["category"]),
        "target_fixture_id": target_fixture_id,
        "target_fixture_category": str(
            target_fixture.get("category") or target_fixture.get("name") or ""
        ),
        "source_fixture_id": str(candidate.get("source_fixture_id") or ""),
        "evidence_note": str(candidate.get("evidence_note") or ""),
        "image_region": candidate["image_region"],
        "confidence": candidate.get("confidence"),
        "producer_type": str(candidate["producer_type"]),
        "producer_id": str(candidate["producer_id"]),
        "supersedes_observation_id": str(candidate.get("supersedes_observation_id") or ""),
        "grounding_status": grounding_status,
        "grounding_confidence": confidence,
        "grounding_basis": basis,
        "recovery_hint": recovery_hint,
        "target_plausibility": target_plausibility,
        "actionability_status": actionability_status,
        "candidate_state": realworld_visual_candidates._candidate_state(
            {
                **candidate,
                "visual_grounding_evidence": visual_grounding_evidence,
                "grounding_status": grounding_status,
                "actionability_status": actionability_status,
                "candidate_fixture_id": target_fixture_id,
                "recommended_tool": _recommended_place_tool(
                    internal_target_fixture_id,
                    contract._fixtures,
                )
                if target_fixture_id
                else "",
            }
        ),
        "visual_grounding_evidence": visual_grounding_evidence,
        "private_truth_included": False,
    }
    declaration["candidate_state_history"] = realworld_visual_candidates._candidate_state_history(
        str(declaration["candidate_state"])
    )
    declaration["visual_grounding_evidence"]["candidate_state"] = declaration["candidate_state"]
    declaration["visual_grounding_evidence"]["actionability_status"] = declaration[
        "actionability_status"
    ]
    for key in (
        "visual_grounding_pipeline",
        "visual_grounding_stage_provenance",
        "visual_grounding_destination_hint",
        "tracking",
        "image_dimensions",
        "visual_grounding_overlay",
    ):
        value = candidate.get(key)
        if value:
            declaration[key] = value
    if status == "already_handled":
        declaration["handled_state"] = str(lifecycle.get("state") or "handled")
    assert_no_forbidden_agent_view_keys(declaration)
    return declaration


def target_plausibility_for_candidate(
    contract: Any,
    *,
    category: str,
    target_fixture_id: str,
) -> dict[str, Any]:
    internal_target_fixture_id = (
        contract.internal_fixture_id_for_public_reference(target_fixture_id) or target_fixture_id
    )
    fixture = contract._fixtures.get(internal_target_fixture_id)
    if fixture is None:
        return {
            "status": "unknown_fixture",
            "basis": "target fixture id is not in public fixture hints",
        }
    pseudo_detection = {
        "category": category,
        "name": category,
        "support_estimate": {"fixture_id": ""},
    }
    public_target = contract.target_fixture_for_detection(
        pseudo_detection,
        contract.fixture_hints(),
    )
    expected = str((public_target or {}).get("fixture_id") or "")
    return {
        "status": "plausible" if not expected or expected == target_fixture_id else "weak",
        "basis": "public category/fixture affordance",
        "expected_fixture_id": expected,
    }


def detection_for_object_at_location(
    contract: Any,
    obj: Any,
    *,
    location_id: str,
    handle: str,
    waypoint: dict[str, Any],
    perception_source: str,
    producer_type: str,
    source_observation_id: str,
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any]:
    fixture = contract._fixtures.get(location_id, {})
    room_id = _room_id(str(fixture.get("room_area", waypoint["room_id"])))
    detection = {
        "object_id": handle,
        "category": obj.category,
        "name": obj.name,
        "current_room_id": room_id,
        "visibility_confidence": visibility_confidence(handle),
        "image_bbox": image_bbox(handle),
        "image_region": {"type": "bbox", "value": image_bbox(handle)},
        "perception_source": perception_source,
        "producer_type": producer_type,
        "source_observation_id": source_observation_id,
        "candidate_source": MODEL_DECLARED_OBSERVATION_SOURCE
        if perception_source == MODEL_DECLARED_OBSERVATION_SOURCE
        else "raw_fpv_observation",
        "candidate_state": CANDIDATE_STATE_NAVIGATION_AUTHORIZED,
        "candidate_state_history": realworld_visual_candidates._candidate_state_history(
            CANDIDATE_STATE_NAVIGATION_AUTHORIZED
        ),
        "locality_status": "same_waypoint_source_observation",
        "support_estimate": {
            "fixture_id": location_id,
            "relation": location_relation(obj.object_id, contract.backend),
            "confidence": 0.68,
            "source": perception_source,
            "perception_source": perception_source,
            "producer_type": producer_type,
            "source_observation_id": source_observation_id,
        },
    }
    detection["model_provenance"] = producer_type
    detection["support_estimate"]["model_provenance"] = producer_type
    detection["visual_grounding_evidence"] = visual_grounding_evidence_for_candidate(
        detection,
        assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
    )
    _refresh_candidate_state(detection)
    detection.update(contract._public_candidate_hint(detection))
    assert_no_forbidden_agent_view_keys(detection)
    return detection


def objects_visible_from_waypoint(contract: Any, waypoint: dict[str, Any]) -> list[tuple[Any, str]]:
    waypoint = contract._private_waypoint_for_public_waypoint(waypoint)
    locations = contract.backend.object_locations()
    fixture_ids = set(waypoint.get("fixture_ids") or [])
    visible = []
    for obj in contract.scenario.objects:
        location_id = locations.get(obj.object_id)
        if not location_id or location_id == "held_by_agent":
            continue
        fixture = contract._fixtures.get(location_id)
        if fixture is None:
            continue
        room_id = _room_id(str(fixture.get("room_area", "unknown")))
        if contract.map_mode != MINIMAL_MAP_MODE and room_id != waypoint["room_id"]:
            continue
        if fixture_ids and location_id not in fixture_ids:
            continue
        visible.append((obj, str(location_id)))
    return visible


def objects_visible_from_room(contract: Any, waypoint: dict[str, Any]) -> list[tuple[Any, str]]:
    waypoint = contract._private_waypoint_for_public_waypoint(waypoint)
    locations = contract.backend.object_locations()
    visible = []
    for obj in contract.scenario.objects:
        location_id = locations.get(obj.object_id)
        if not location_id or location_id == "held_by_agent":
            continue
        fixture = contract._fixtures.get(location_id)
        if fixture is None:
            continue
        room_id = _room_id(str(fixture.get("room_area", "unknown")))
        if contract.map_mode != MINIMAL_MAP_MODE and room_id != waypoint["room_id"]:
            continue
        visible.append((obj, str(location_id)))
    return visible


def unresolved_visual_candidate_error(
    contract: Any,
    tool: str,
    object_id: str,
) -> dict[str, Any] | None:
    detection = contract._detections_by_handle.get(object_id)
    if not detection:
        return None
    declaration = detection.get("model_declared_observation") or {}
    status = declaration.get("grounding_status") or detection.get("grounding_status")
    if status not in {"ambiguous", "unresolved"}:
        return None
    return contract._error(
        tool,
        "visual_candidate_not_resolved",
        object_id=object_id,
        grounding_status=status,
        grounding_confidence=declaration.get(
            "grounding_confidence",
            detection.get("grounding_confidence", 0.0),
        ),
        grounding_basis=declaration.get(
            "grounding_basis",
            detection.get("grounding_basis", ""),
        ),
        recovery_hint=declaration.get(
            "recovery_hint",
            detection.get(
                "recovery_hint",
                "Declare a tighter image_region or source_fixture_id before picking.",
            ),
        ),
    )


def visual_evidence_for_handle(
    contract: Any,
    handle: str,
    *,
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any]:
    detection = contract._detections_by_handle.get(handle) or {}
    evidence = detection.get("visual_grounding_evidence")
    if isinstance(evidence, dict) and evidence:
        return copy.deepcopy(evidence)
    declaration = detection.get("model_declared_observation") or {}
    return visual_grounding_evidence_for_candidate(
        {
            **detection,
            "image_region": detection.get("image_region") or declaration.get("image_region"),
            "producer_type": detection.get("producer_type") or declaration.get("producer_type"),
            "producer_id": detection.get("producer_id") or declaration.get("producer_id"),
            "source_observation_id": detection.get("source_observation_id")
            or declaration.get("source_observation_id"),
            "grounding_status": detection.get("grounding_status")
            or declaration.get("grounding_status"),
        },
        assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
    )


def visual_evidence_actionability_error(
    contract: Any,
    tool: str,
    object_id: str,
    *,
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any] | None:
    detection = contract._detections_by_handle.get(object_id)
    if not detection:
        return None
    if handle_is_non_actionable(contract, object_id):
        return None
    status = candidate_actionability_status(
        detection,
        assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
    )
    candidate_state = realworld_visual_candidates._candidate_state(detection)
    if status == "actionable" and candidate_state == CANDIDATE_STATE_NAVIGATION_AUTHORIZED:
        return None
    evidence = visual_evidence_for_handle(
        contract,
        object_id,
        assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
    )
    declaration = detection.get("model_declared_observation") or {}
    return contract._error(
        tool,
        "visual_evidence_not_reviewable",
        object_id=object_id,
        required_next_tool="adjust_camera"
        if candidate_state == CANDIDATE_STATE_VISUAL_SCAN_REQUIRED
        else "observe",
        recovery_tool_options=["observe", "adjust_camera"],
        actionability_status=status,
        candidate_state=candidate_state,
        visual_grounding_evidence=evidence,
        grounding_status=detection.get("grounding_status")
        or declaration.get("grounding_status")
        or "resolved",
        grounding_confidence=detection.get("grounding_confidence")
        or declaration.get("grounding_confidence")
        or 0.0,
        source_observation_id=evidence.get("source_observation_id", ""),
        recovery_hint=visual_evidence_recovery_hint(),
    )


def handle_is_non_actionable(contract: Any, handle: str) -> bool:
    if handle in contract._handled_handles:
        return True
    state = str((contract._object_lifecycle.get(handle) or {}).get("state") or "")
    return state in _NON_ACTIONABLE_HANDLE_STATES


def visual_grounding_evidence_for_candidate(
    candidate: dict[str, Any],
    *,
    fallback_image_bbox: Any = None,
    grounding_status: str = "",
    assert_no_forbidden_agent_view_keys: Callable[[Any], None] | None = None,
) -> dict[str, Any]:
    return realworld_visual_candidates._visual_grounding_evidence_for_candidate(
        candidate,
        fallback_image_bbox=fallback_image_bbox,
        grounding_status=grounding_status,
        assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
    )


def candidate_actionability_status(
    candidate: dict[str, Any],
    *,
    assert_no_forbidden_agent_view_keys: Callable[[Any], None] | None = None,
) -> str:
    return realworld_visual_candidates._candidate_actionability_status(
        candidate,
        visual_grounding_evidence_builder=lambda value: visual_grounding_evidence_for_candidate(
            value,
            assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
        ),
    )


def location_relation(object_id: str, backend: Any) -> str:
    containment = getattr(backend, "_containment", {})
    relation = containment.get(object_id, {}).get("location_relation")
    return str(relation or "on")


def visibility_confidence(handle: str) -> float:
    suffix = int(handle.rsplit("_", 1)[-1])
    return round(0.78 + (suffix % 5) * 0.03, 2)


def image_bbox(handle: str) -> list[int]:
    suffix = int(handle.rsplit("_", 1)[-1])
    return [72 + suffix * 9, 58 + suffix * 7, 42, 31]


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()
