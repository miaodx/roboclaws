from __future__ import annotations

from pathlib import Path
from typing import Any

from roboclaws.maps.bundle import (
    DEFAULT_COSTMAP_PARAMETERS,
    DEFAULT_COSTMAP_PROFILE_ID,
    DEFAULT_ROBOT_PROFILE,
    DEFAULT_ROBOT_PROFILE_ID,
    NAV2_MAP_BUNDLE_SCHEMA,
    NAV2_MAP_BUNDLE_SNAPSHOT_SCHEMA,
    RUNTIME_COSTMAP_GAPS,
    metric_map_bundle_metadata,
    write_nav2_map_bundle_snapshot,
)


def attach_nav2_map_bundle_snapshot(*, run_result: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    """Write a run-local Nav2-shaped map bundle and attach evidence to ``run_result``."""
    agent_view = (
        run_result.get("agent_view") if isinstance(run_result.get("agent_view"), dict) else {}
    )
    metric_map = (
        agent_view.get("metric_map") if isinstance(agent_view.get("metric_map"), dict) else {}
    )
    fixture_hints = (
        agent_view.get("fixture_hints") if isinstance(agent_view.get("fixture_hints"), dict) else {}
    )
    snapshot = write_nav2_map_bundle_snapshot(
        run_dir=run_dir,
        metric_map=metric_map,
        fixture_hints=fixture_hints,
    )
    run_result["nav2_map_bundle"] = snapshot
    artifacts = run_result.setdefault("artifacts", {})
    artifacts["map_bundle"] = str(run_dir / "map_bundle")
    artifacts["nav2_map_yaml"] = str(run_dir / "map_bundle" / "map.yaml")
    artifacts["nav2_occupancy_image"] = str(run_dir / "map_bundle" / "map.pgm")
    artifacts["nav2_map_preview"] = str(run_dir / "map_bundle" / "preview.png")
    readiness = run_result.get("real_robot_readiness")
    if isinstance(readiness, dict):
        readiness["map_bundle_snapshot_present"] = snapshot["snapshot_complete"]
        readiness["map_bundle_artifact_count"] = len(snapshot["artifact_hashes"])
        readiness["map_bundle_parameter_hash"] = snapshot["parameter_hash"]
        readiness["map_bundle_snapshot_root"] = snapshot["snapshot_root"]
        readiness["runtime_costmap_gaps"] = list(RUNTIME_COSTMAP_GAPS)
        readiness["readiness_sections_complete"] = bool(
            readiness.get("readiness_sections_complete") and snapshot["snapshot_complete"]
        )
    return snapshot


__all__ = [
    "DEFAULT_COSTMAP_PARAMETERS",
    "DEFAULT_COSTMAP_PROFILE_ID",
    "DEFAULT_ROBOT_PROFILE",
    "DEFAULT_ROBOT_PROFILE_ID",
    "NAV2_MAP_BUNDLE_SCHEMA",
    "NAV2_MAP_BUNDLE_SNAPSHOT_SCHEMA",
    "RUNTIME_COSTMAP_GAPS",
    "attach_nav2_map_bundle_snapshot",
    "metric_map_bundle_metadata",
    "write_nav2_map_bundle_snapshot",
]
