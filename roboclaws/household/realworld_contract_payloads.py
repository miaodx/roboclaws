from __future__ import annotations

from collections.abc import Callable, Collection, Iterable, Mapping
from typing import Any, Protocol

from roboclaws.household import realworld_runtime_map_contract


class RealWorldPayloadContract(Protocol):
    map_mode: str
    perception_mode: str
    sanitize_world_labels: bool
    _detections_by_handle: Mapping[str, dict[str, Any]]
    _fixtures: dict[str, dict[str, Any]]
    _generated_inspection_waypoints: Mapping[str, dict[str, Any]]
    _held_handle: str
    _object_lifecycle: Mapping[str, dict[str, Any]]
    _observed_waypoint_ids: Collection[str]
    _public_rooms: Iterable[dict[str, Any]]
    _public_waypoints: Iterable[dict[str, Any]]
    _runtime_map_priors: Iterable[dict[str, Any]]
    _runtime_map_room_priors: Iterable[dict[str, Any]]

    def metric_map(self) -> dict[str, Any]: ...
    def fixture_hints(self) -> dict[str, Any]: ...
    def cleanup_worklist_payload(
        self,
        *,
        fixture_hints: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    def _runtime_public_semantic_anchors(self) -> list[dict[str, Any]]: ...
    def _runtime_target_candidates(
        self,
        *,
        public_semantic_anchors: list[dict[str, Any]],
        observed_objects: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...
    def _target_search_summary(
        self,
        target_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]: ...
    def _target_query_recovery_summary(
        self,
        target_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]: ...
    def _visual_evidence_for_handle(self, handle: str) -> dict[str, Any]: ...
    def target_fixture_for_detection(
        self,
        detection: dict[str, Any],
        fixture_hints: dict[str, Any],
    ) -> dict[str, Any] | None: ...
    def _public_fixture_reference_id(self, fixture_id: str) -> str: ...
    def internal_fixture_id_for_public_reference(self, fixture_id: str) -> str | None: ...
    def _public_navigation_waypoints(self) -> list[dict[str, Any]]: ...


def runtime_metric_map_payload(
    contract: RealWorldPayloadContract,
    *,
    metric_map: dict[str, Any] | None = None,
    fixture_hints: dict[str, Any] | None = None,
    cleanup_worklist: dict[str, Any] | None = None,
    realworld_contract: str,
    runtime_metric_map_schema: str,
    cleanup_worklist_schema: str,
    minimal_map_mode: str,
    visible_object_detections_mode: str,
    sanitized_visible_object_detections_provenance: str,
    runtime_map_producer_summary: Callable[..., dict[str, Any]],
    merge_public_rooms: Callable[[Any, Any], list[dict[str, Any]]],
    room_category_hints_from_public_rooms: Callable[[Any, Any], list[dict[str, Any]]],
    candidate_actionability_status: Callable[[dict[str, Any]], str],
    candidate_state: Callable[[dict[str, Any]], str],
    public_destination_policy_for_category: Callable[[Any], dict[str, Any]],
    norm: Callable[[Any], str],
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any]:
    """Build the current-run map view from public map and observation evidence."""

    public_metric_map = metric_map if metric_map is not None else contract.metric_map()
    public_fixture_hints = fixture_hints if fixture_hints is not None else contract.fixture_hints()
    public_worklist = (
        cleanup_worklist
        if cleanup_worklist is not None
        else contract.cleanup_worklist_payload(fixture_hints=public_fixture_hints)
    )
    worklist_by_handle = {
        str(item.get("object_id") or ""): dict(item)
        for item in public_worklist.get("objects") or []
    }
    runtime_map_priors = [dict(item) for item in contract._runtime_map_priors]
    observed_objects = [
        realworld_runtime_map_contract.runtime_observed_object_payload(
            handle=handle,
            detection=dict(contract._detections_by_handle[handle]),
            worklist_item=worklist_by_handle.get(handle, {}),
            object_lifecycle=dict(contract._object_lifecycle.get(handle, {})),
            sanitize_world_labels=contract.sanitize_world_labels,
            perception_mode=contract.perception_mode,
            visible_object_detections_mode=visible_object_detections_mode,
            sanitized_visible_object_detections_provenance=(
                sanitized_visible_object_detections_provenance
            ),
            runtime_map_priors=runtime_map_priors,
            public_fixture_reference_id=contract._public_fixture_reference_id,
            visual_evidence_for_handle=contract._visual_evidence_for_handle,
            candidate_actionability_status=candidate_actionability_status,
            candidate_state=candidate_state,
            public_destination_policy_for_category=public_destination_policy_for_category,
            assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
            norm=norm,
        )
        for handle in sorted(contract._detections_by_handle)
    ]
    runtime_observed_objects = [
        *[dict(item) for item in contract._runtime_map_priors],
        *observed_objects,
    ]
    public_semantic_anchors = contract._runtime_public_semantic_anchors()
    map_update_candidates: list[dict[str, Any]] = []
    target_candidates = contract._runtime_target_candidates(
        public_semantic_anchors=public_semantic_anchors,
        observed_objects=runtime_observed_objects,
    )
    payload = {
        "schema": runtime_metric_map_schema,
        "contract": realworld_contract,
        "freshness": "current_run",
        "map_mode": contract.map_mode,
        "minimal_map_mode": contract.map_mode == minimal_map_mode,
        "source_map_mutated": False,
        "private_truth_included": False,
        "static_map": realworld_runtime_map_contract.runtime_static_map_payload(
            metric_map=public_metric_map,
            fixture_hints=public_fixture_hints,
            map_mode=contract.map_mode,
            minimal_map_mode=minimal_map_mode,
            assert_no_forbidden_agent_view_keys=assert_no_forbidden_agent_view_keys,
        ),
        "rooms": [dict(item) for item in public_metric_map.get("rooms") or []],
        "room_category_hints": [
            dict(item) for item in public_metric_map.get("room_category_hints") or []
        ],
        "driveable_ways": [dict(item) for item in public_metric_map.get("driveable_ways") or []],
        "public_semantic_anchors": public_semantic_anchors,
        "observed_objects": runtime_observed_objects,
        "target_candidates": target_candidates,
        "target_search_summary": contract._target_search_summary(target_candidates),
        "target_query_recovery": contract._target_query_recovery_summary(
            target_candidates,
        ),
        "map_update_candidates": map_update_candidates,
        "producer_summary": runtime_map_producer_summary(
            runtime_observed_objects,
            public_semantic_anchors=public_semantic_anchors,
            map_update_candidates=map_update_candidates,
            target_candidates=target_candidates,
        ),
        "cleanup_worklist_summary": {
            "schema": cleanup_worklist_schema,
            "object_count": len(public_worklist.get("objects") or []),
            "pending_count": sum(
                1 for item in public_worklist.get("objects") or [] if item.get("state") == "pending"
            ),
            "held_object_id": public_worklist.get("held_object_id"),
            "prior_count": len(contract._runtime_map_priors),
        },
        "public_contract_note": (
            "Runtime Metric Map enriches the current run with public observed "
            "handles, public semantic anchors, and map-update candidates. It "
            "does not mutate the source Navigation Map Artifact or include "
            "private scoring truth."
        ),
        "generated_target_inspection_candidates": [
            {
                **dict(item),
                "visited": str(item.get("waypoint_id") or "") in contract._observed_waypoint_ids,
            }
            for item in contract._generated_inspection_waypoints.values()
        ],
    }
    if contract._runtime_map_room_priors:
        payload["rooms"] = merge_public_rooms(
            payload.get("rooms") or [],
            contract._runtime_map_room_priors,
        )
        payload["room_category_hints"] = room_category_hints_from_public_rooms(
            payload["rooms"],
            public_metric_map.get("inspection_waypoints") or [],
        )
        payload["static_map"]["rooms"] = [dict(item) for item in payload["rooms"]]
    if contract.map_mode == minimal_map_mode:
        payload["generated_exploration_candidates"] = [
            {
                **dict(item),
                "visited": str(item.get("waypoint_id") or "") in contract._observed_waypoint_ids,
            }
            for item in contract._public_waypoints
        ]
        payload["public_contract_note"] = (
            "Minimal-map Runtime Metric Map starts from public occupancy/free-space "
            "geometry and generated exploration candidates, then enriches the run "
            "with public observations and run-local semantic anchors without "
            "mutating source-map semantics."
        )
    assert_no_forbidden_agent_view_keys(payload)
    return payload


def cleanup_worklist_payload(
    contract: RealWorldPayloadContract,
    *,
    fixture_hints: dict[str, Any] | None = None,
    cleanup_worklist_schema: str,
    minimal_map_mode: str,
    non_actionable_handle_states: Collection[str],
    candidate_actionability_status: Callable[[dict[str, Any]], str],
    candidate_state: Callable[[dict[str, Any]], str],
    public_destination_policy_for_category: Callable[[Any], dict[str, Any]],
    recommended_place_tool: Callable[[str, dict[str, dict[str, Any]]], str],
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any]:
    public_fixtures = fixture_hints if fixture_hints is not None else contract.fixture_hints()
    lifecycle_rows = []
    for handle in sorted(contract._detections_by_handle):
        detection = contract._detections_by_handle[handle]
        lifecycle = dict(contract._object_lifecycle.get(handle, {}))
        support = detection.get("support_estimate") or {}
        declaration = detection.get("model_declared_observation") or {}
        grounding_status = str(
            detection.get("grounding_status") or declaration.get("grounding_status") or ""
        )
        visual_grounding_evidence = contract._visual_evidence_for_handle(handle)
        actionability_status = candidate_actionability_status(
            {
                **detection,
                "visual_grounding_evidence": visual_grounding_evidence,
                "grounding_status": grounding_status,
            }
        )
        public_candidate = contract.target_fixture_for_detection(detection, public_fixtures)
        candidate_fixture_id = (public_candidate or {}).get("fixture_id", "")
        source_fixture_id = str(support.get("fixture_id") or "")
        public_candidate_fixture_id = contract._public_fixture_reference_id(
            str(candidate_fixture_id)
        )
        public_source_fixture_id = contract._public_fixture_reference_id(source_fixture_id)
        state = str(lifecycle.get("state", "pending"))
        cleanup_recommended = bool(
            grounding_status not in {"ambiguous", "unresolved"}
            and actionability_status == "actionable"
            and public_candidate_fixture_id
            and public_candidate_fixture_id != public_source_fixture_id
            and state not in non_actionable_handle_states
        )
        candidate_source = (
            "public_semantic_anchor"
            if contract.map_mode == minimal_map_mode and candidate_fixture_id
            else "public_category_fixture_affordance"
        )
        destination_policy_status = "candidate_inferred"
        if contract.sanitize_world_labels:
            public_candidate_fixture_id = ""
            cleanup_recommended = False
            candidate_source = "policy_required_destination_selection"
            destination_policy_status = "policy_required"
        destination_policy = public_destination_policy_for_category(detection.get("category"))
        row = {
            "object_id": handle,
            "state": state,
            "category": detection.get("category", ""),
            "room_id": detection.get("current_room_id", lifecycle.get("room_id", "")),
            "source_fixture_id": public_source_fixture_id,
            "candidate_fixture_id": public_candidate_fixture_id,
            "grounding_status": grounding_status,
            "actionability_status": actionability_status,
            "candidate_state": candidate_state(
                {
                    **detection,
                    "visual_grounding_evidence": visual_grounding_evidence,
                    "grounding_status": grounding_status,
                }
            ),
            "visual_grounding_evidence": visual_grounding_evidence,
            "candidate_source": candidate_source,
            "last_waypoint_id": lifecycle.get("waypoint_id", ""),
            "perception_source": lifecycle.get("perception_source", "visible_detection"),
            "destination_policy_status": destination_policy_status,
        }
        if contract.sanitize_world_labels:
            row["destination_policy"] = destination_policy
        if not contract.sanitize_world_labels:
            row["cleanup_recommended"] = cleanup_recommended
            internal_candidate_fixture_id = contract.internal_fixture_id_for_public_reference(
                public_candidate_fixture_id
            ) or str(candidate_fixture_id)
            row["recommended_tool"] = (
                recommended_place_tool(
                    internal_candidate_fixture_id,
                    contract._fixtures,
                )
                if public_candidate_fixture_id
                else ""
            )
        lifecycle_rows.append(row)
    waypoint_rows = []
    for waypoint in contract._public_navigation_waypoints():
        waypoint_id = str(waypoint["waypoint_id"])
        waypoint_rows.append(
            {
                "waypoint_id": waypoint_id,
                "room_id": waypoint["room_id"],
                "state": "visited"
                if waypoint_id in contract._observed_waypoint_ids
                else "unvisited",
                "purpose": waypoint.get("purpose", "fixture_coverage"),
                "waypoint_source": waypoint.get("waypoint_source", "static_map_coverage"),
            }
        )
    rooms = []
    for room in contract._public_rooms:
        room_waypoints = [item for item in waypoint_rows if item.get("room_id") == room["room_id"]]
        visited = sum(1 for item in room_waypoints if item.get("state") == "visited")
        pending = [
            item
            for item in lifecycle_rows
            if item.get("room_id") == room["room_id"] and item.get("state") == "pending"
        ]
        rooms.append(
            {
                "room_id": room["room_id"],
                "scan_state": "scanned"
                if room_waypoints and visited == len(room_waypoints)
                else "partially_scanned"
                if visited
                else "unvisited",
                "visited_waypoints": visited,
                "total_waypoints": len(room_waypoints),
                "pending_observed_handles": [item["object_id"] for item in pending],
            }
        )
    payload = {
        "schema": cleanup_worklist_schema,
        "waypoint_source": "generated_exploration_candidate"
        if contract.map_mode == minimal_map_mode
        else "static_map_fixture_coverage",
        "held_object_id": contract._held_handle,
        "objects": lifecycle_rows,
        "waypoints": waypoint_rows,
        "rooms": rooms,
        "public_policy_note": (
            "Observed handles come from observe or model-declared camera evidence. "
            "Candidate fixtures are public category/fixture-affordance guesses, "
            "not private acceptable-destination truth."
        ),
    }
    assert_no_forbidden_agent_view_keys(payload)
    return payload
