from __future__ import annotations

from pathlib import Path
from typing import Any

from roboclaws.maps.bundle import validate_nav2_map_bundle
from roboclaws.maps.project import fixture_hints_from_bundle, metric_map_from_bundle


def validate_contract_options(
    *,
    fixture_hint_mode: str,
    perception_mode: str,
    map_mode: str,
) -> None:
    helpers = _contract_helpers()
    if fixture_hint_mode not in {"room_only", "exact_fixtures"}:
        raise ValueError("fixture_hint_mode must be room_only or exact_fixtures")
    if perception_mode not in helpers.REALWORLD_PERCEPTION_MODES:
        allowed = ", ".join(sorted(helpers.REALWORLD_PERCEPTION_MODES))
        raise ValueError(f"perception_mode must be one of: {allowed}")
    if map_mode not in helpers.REALWORLD_MAP_MODES:
        allowed = ", ".join(sorted(helpers.REALWORLD_MAP_MODES))
        raise ValueError(f"map_mode must be one of: {allowed}")


def init_profile_and_acceptance(
    target: Any,
    cleanup_profile: str | None,
    public_acceptance_config: dict[str, Any] | None,
) -> None:
    helpers = _contract_helpers()
    target.cleanup_profile = (
        str(cleanup_profile or "").strip().lower().replace("_", "-") if cleanup_profile else ""
    )
    target.public_acceptance_config = helpers._public_acceptance_config(public_acceptance_config)
    target.task_intent = helpers.normalize_household_intent(
        target.public_acceptance_config.get("task_intent")
    )
    target.task_intent_mode = helpers.normalize_task_intent_mode(
        target.public_acceptance_config.get("task_intent_mode")
    )
    target.sanitize_world_labels = target.cleanup_profile == helpers.WORLD_LABELS_SANITIZED_PROFILE
    target.visible_detection_exposure_policy = (
        helpers.SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY
        if target.sanitize_world_labels
        else helpers.WORLD_LABELS_DETECTION_POLICY
    )


def init_visual_grounding(
    target: Any,
    *,
    visual_grounding_client: Any,
    visual_grounding_pipeline_id: str,
    visual_grounding_artifact_base_dir: str | Path | None,
    visual_grounding_run_id: str,
) -> None:
    helpers = _contract_helpers()
    target.visual_grounding_client = visual_grounding_client
    target.visual_grounding_pipeline_id = str(
        visual_grounding_pipeline_id
        or getattr(visual_grounding_client, "pipeline_id", "")
        or helpers.SIM_VISUAL_GROUNDING_PIPELINE_ID
    )
    target.visual_grounding_artifact_base_dir = (
        Path(visual_grounding_artifact_base_dir)
        if visual_grounding_artifact_base_dir is not None
        else None
    )
    target.visual_grounding_run_id = visual_grounding_run_id


def init_map_projection(target: Any, map_bundle_dir: str | Path | None) -> None:
    target.map_bundle_dir = Path(map_bundle_dir) if map_bundle_dir is not None else None
    target.map_bundle_validation = None
    target._bundle_metric_map_template = None
    target._bundle_fixture_hints_template = None
    if target.map_bundle_dir is not None:
        _init_bundle_map_projection(target)
    else:
        _init_scenario_map_projection(target)


def init_public_map_projection(target: Any) -> None:
    helpers = _contract_helpers()
    if target.map_mode == helpers.MINIMAL_MAP_MODE:
        _init_minimal_public_map_projection(target)
        return
    target._public_rooms = target._rooms
    target._public_fixtures = target._fixtures
    target._public_waypoints = target._waypoints
    target._private_waypoint_by_public_id = {}


def initial_waypoint_id(target: Any) -> str:
    helpers = _contract_helpers()
    first_waypoint = target._waypoints[0]["waypoint_id"] if target._waypoints else ""
    if target.map_mode == helpers.MINIMAL_MAP_MODE and target._public_waypoints:
        return str(target._public_waypoints[0]["waypoint_id"])
    return str(first_waypoint)


def init_runtime_state(target: Any, runtime_map_prior: dict[str, Any] | None) -> None:
    helpers = _contract_helpers()
    target._observed_waypoint_ids = set()
    target._observed_handles_by_object_id = {}
    target._object_ids_by_handle = {}
    target._detections_by_handle = {}
    target._object_lifecycle = {}
    target._raw_fpv_observations = []
    target._visible_observation_count = 0
    target._camera_model_policy_events = []
    target._model_declared_observations = []
    target._runtime_map_priors = helpers._runtime_map_priors_from_snapshot(runtime_map_prior)
    target._runtime_map_anchor_priors = helpers._runtime_map_anchor_priors_from_snapshot(
        runtime_map_prior
    )
    target._runtime_map_room_priors = helpers._runtime_map_room_priors_from_snapshot(
        runtime_map_prior
    )
    target._public_anchor_ids_by_private_fixture_id = {}
    target._generated_inspection_waypoints = {}
    target._seed_public_fixture_anchor_ids_from_prior_anchors()
    target._camera_yaw_offset_deg = 0.0
    target._camera_pitch_offset_deg = 0.0
    target._camera_adjustment_events = []
    target._inspection_observations = []
    target._handled_handles = set()
    target._held_handle = None
    target._current_object_handle = None
    target._current_receptacle_for_handle = None
    target._opened_receptacle_for_handle = None
    target._pending_close_receptacle_for_handle = None
    target._initial_locations = target.backend.object_locations()


def _init_bundle_map_projection(target: Any) -> None:
    helpers = _contract_helpers()
    validation = validate_nav2_map_bundle(target.map_bundle_dir)
    validation.raise_for_errors()
    target.map_bundle_validation = validation.as_dict()
    target._bundle_metric_map_template = metric_map_from_bundle(target.map_bundle_dir)
    target._bundle_fixture_hints_template = fixture_hints_from_bundle(
        target.map_bundle_dir,
        fixture_hint_mode=target.fixture_hint_mode,
    )
    target._fixtures = helpers._fixtures_from_bundle_fixture_hints(
        target._bundle_fixture_hints_template
    )
    target._rooms = helpers._rooms_from_bundle_projection(
        target._bundle_metric_map_template,
        target._bundle_fixture_hints_template,
    )
    target._waypoints = helpers._inspection_waypoints_from_bundle_projection(
        target._bundle_metric_map_template,
        target._bundle_fixture_hints_template,
    )
    target._scene_index_fixture_overlay = helpers._scene_index_public_fixture_overlay(
        backend=target.backend,
        scenario=target.scenario,
        existing_fixtures=target._fixtures,
        fallback_waypoint_id=helpers._first_waypoint_id(target._waypoints),
    )
    target._fixtures.update(target._scene_index_fixture_overlay)


def _init_scenario_map_projection(target: Any) -> None:
    helpers = _contract_helpers()
    target._fixtures = {
        item.receptacle_id: item.to_public_dict() for item in target.scenario.receptacles
    }
    scene_room_outlines = helpers._scene_room_outlines_from_backend(target.backend)
    if scene_room_outlines:
        target._apply_scene_room_outlines_to_fixtures(scene_room_outlines)
    target._rooms = helpers._rooms_from_fixtures(target._fixtures)
    target._waypoints = helpers._inspection_waypoints(target._rooms)
    target._scene_index_fixture_overlay = {}


def _init_minimal_public_map_projection(target: Any) -> None:
    helpers = _contract_helpers()
    source_metric_map = (
        target._bundle_metric_map_template
        if target._bundle_metric_map_template is not None
        else target._fallback_metric_map_template()
    )
    target._public_rooms = helpers._public_room_hints_from_metric_map(
        source_metric_map,
        fallback_rooms=target._rooms,
    )
    target._public_fixtures = {}
    target._public_waypoints = helpers._minimal_generated_exploration_waypoints(
        source_metric_map,
        fallback_waypoints=target._waypoints,
        public_rooms=target._public_rooms,
    )
    target._private_waypoint_by_public_id = helpers._private_waypoint_map_for_generated_candidates(
        target._public_waypoints,
        target._waypoints,
    )


def _contract_helpers() -> Any:
    from roboclaws.household import realworld_contract

    return realworld_contract
