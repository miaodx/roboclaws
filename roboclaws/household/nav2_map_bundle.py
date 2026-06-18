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
    copy_nav2_map_bundle_snapshot,
    metric_map_bundle_metadata,
    static_landmarks_from_fixture_projection,
    validate_nav2_map_bundle,
    write_nav2_map_bundle_snapshot,
)

DEFAULT_MAP_ASSET_ROOT = Path("assets") / "maps"


def selected_nav2_map_bundle_dir(
    map_bundle_dir: str | Path | None,
    *,
    required: bool = False,
    asset_root: Path = DEFAULT_MAP_ASSET_ROOT,
) -> Path | None:
    """Resolve and validate a selected prebuilt Nav2 map bundle.

    ``map_bundle_dir`` may be either a filesystem path or a checked-in
    environment id under ``assets/maps``.
    """
    if map_bundle_dir is None or str(map_bundle_dir).strip() == "":
        if required:
            raise ValueError("map_bundle_dir is required for this cleanup run")
        return None

    raw = Path(str(map_bundle_dir))
    candidates = [raw]
    if not raw.is_absolute() and len(raw.parts) == 1:
        candidates.append(asset_root / raw)
    bundle_dir = next((candidate for candidate in candidates if candidate.exists()), candidates[-1])
    validation = validate_nav2_map_bundle(bundle_dir)
    if not validation.ok:
        raise ValueError(f"invalid Nav2 map bundle {bundle_dir}: {'; '.join(validation.errors)}")
    return bundle_dir


def attach_nav2_map_bundle_snapshot(
    *,
    run_result: dict[str, Any],
    run_dir: Path,
    source_bundle_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Write a run-local Nav2-shaped map bundle and attach evidence to ``run_result``."""
    if source_bundle_dir is not None:
        snapshot = copy_nav2_map_bundle_snapshot(
            source_bundle_dir=Path(source_bundle_dir),
            run_dir=run_dir,
        )
    else:
        agent_view = (
            run_result.get("agent_view") if isinstance(run_result.get("agent_view"), dict) else {}
        )
        metric_map = (
            agent_view.get("metric_map") if isinstance(agent_view.get("metric_map"), dict) else {}
        )
        static_fixture_projection = (
            agent_view.get("static_fixture_projection")
            if isinstance(agent_view.get("static_fixture_projection"), dict)
            else {}
        )
        snapshot = write_nav2_map_bundle_snapshot(
            run_dir=run_dir,
            metric_map=metric_map,
            static_landmarks=static_landmarks_from_fixture_projection(static_fixture_projection),
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
    "selected_nav2_map_bundle_dir",
    "write_nav2_map_bundle_snapshot",
]
