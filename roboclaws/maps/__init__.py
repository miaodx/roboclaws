"""Reusable map artifact utilities for robot cleanup contracts."""

from roboclaws.maps.bundle import (
    DEFAULT_COSTMAP_PARAMETERS,
    DEFAULT_COSTMAP_PROFILE_ID,
    DEFAULT_ROBOT_PROFILE,
    DEFAULT_ROBOT_PROFILE_ID,
    NAV2_MAP_BUNDLE_SCHEMA,
    NAV2_MAP_BUNDLE_SNAPSHOT_SCHEMA,
    RUNTIME_COSTMAP_GAPS,
    MapBundleValidation,
    metric_map_bundle_metadata,
    validate_base_navigation_map_v1_bundle,
    validate_nav2_map_bundle,
    write_nav2_map_bundle,
    write_nav2_map_bundle_snapshot,
)
from roboclaws.maps.route import SIM_COSTMAP_PLANNER, validate_metric_map_route
from roboclaws.maps.runtime_prior_snapshot import (
    RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
    materialize_runtime_prior_targets,
    runtime_metric_map_from_prior_artifact,
    runtime_prior_snapshot_from_agibot_navigation_memory,
    runtime_prior_snapshot_from_runtime_metric_map,
)

__all__ = [
    "RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA",
    "DEFAULT_COSTMAP_PARAMETERS",
    "DEFAULT_COSTMAP_PROFILE_ID",
    "DEFAULT_ROBOT_PROFILE",
    "DEFAULT_ROBOT_PROFILE_ID",
    "NAV2_MAP_BUNDLE_SCHEMA",
    "NAV2_MAP_BUNDLE_SNAPSHOT_SCHEMA",
    "RUNTIME_COSTMAP_GAPS",
    "SIM_COSTMAP_PLANNER",
    "MapBundleValidation",
    "runtime_prior_snapshot_from_agibot_navigation_memory",
    "runtime_prior_snapshot_from_runtime_metric_map",
    "materialize_runtime_prior_targets",
    "metric_map_bundle_metadata",
    "runtime_metric_map_from_prior_artifact",
    "validate_base_navigation_map_v1_bundle",
    "validate_metric_map_route",
    "validate_nav2_map_bundle",
    "write_nav2_map_bundle",
    "write_nav2_map_bundle_snapshot",
]
