#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]

from roboclaws.maps.bundle import (
    DEFAULT_COSTMAP_PARAMETERS,
    DEFAULT_ROBOT_PROFILE,
    validate_nav2_map_bundle,
    write_source_frame_bundle_preview,
)
from roboclaws.maps.bundle_validation import parse_map_yaml
from roboclaws.maps.rasterize import OccupancyGrid, load_pgm
from roboclaws.maps.spatial_contract import (
    ALIGNMENT_STATUS_CANDIDATE,
    ALIGNMENT_STATUS_VERIFIED,
    GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
    POLYGON_ROLE_NAVIGATION_AREA,
    normalize_spatial_rooms,
    source_frame_spatial_contract,
)
from scripts.isaac_lab_cleanup.check_b1_map12_readiness import (  # noqa: E402
    DEFAULT_B1_VISUAL_ROUTE_SCENE_USD,
    NAVIGATION_PROVENANCE,
    validate_alignment_residual_artifact,
    validate_navigation_smoke_artifact,
)
from scripts.maps.build_b1_map12_semantic_projection import (  # noqa: E402
    SEMANTIC_PROJECTION_SCHEMA,
)

B1_MAP12_ALIGNMENT_REVIEW_SCHEMA = "b1_map12_alignment_review_v1"
B1_MAP12_RUNTIME_PROVENANCE_SCHEMA = "b1_map12_runtime_bundle_provenance_v1"
B1_ROBOT_CONSUMPTION_MANIFEST_SCHEMA = "b1_map12_robot_consumption_manifest_v1"
ACCEPTED_REVIEW_STATUS = "accepted"
RUNTIME_LABEL_STATUSES = frozenset({ACCEPTED_REVIEW_STATUS})
REVIEW_ONLY_STATUSES = frozenset({"draft", "proposed", "blocked_shared_area"})
EXPLICIT_SHARED_AREA_POLICIES = frozenset({"composite_area"})
DEFAULT_MAP12_ROOT = Path("vendors/agibot_sdk/artifacts/maps/robot_map_12")
DEFAULT_MAP_BUNDLE = DEFAULT_MAP12_ROOT / "agibot"
DEFAULT_NAVIGATION_MEMORY = DEFAULT_MAP12_ROOT / "navigation_memory.json"
DEFAULT_SCENE_ROOT = Path("data/robot-data-lab/scene-engine/data/2rd_floor_seperated")
DEFAULT_REVIEW_MANIFEST = Path("assets/maps/b1-map12-alignment-review.json")
DEFAULT_OUTPUT_DIR = Path("output/b1-map12/digital-twin-runtime")


def _repo_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a generated B1 / Map 12 digital-twin runtime map bundle."
    )
    parser.add_argument("--map-bundle", type=Path, default=DEFAULT_MAP_BUNDLE)
    parser.add_argument("--navigation-memory", type=Path, default=DEFAULT_NAVIGATION_MEMORY)
    parser.add_argument("--scene-root", type=Path, default=DEFAULT_SCENE_ROOT)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_MANIFEST)
    parser.add_argument("--alignment-artifact", type=Path)
    parser.add_argument("--navigation-artifact", type=Path)
    parser.add_argument("--semantic-projection-artifact", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--include-draft-labels",
        action="store_true",
        help="Debug only: include non-accepted labels in the generated semantic label layer.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = compile_runtime_bundle(
        map_bundle=args.map_bundle,
        scene_root=args.scene_root,
        review_manifest_path=args.review_manifest,
        alignment_artifact_path=args.alignment_artifact,
        navigation_artifact_path=args.navigation_artifact,
        semantic_projection_artifact_path=args.semantic_projection_artifact,
        navigation_memory_path=args.navigation_memory,
        output_dir=args.output_dir,
        include_draft_labels=args.include_draft_labels,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def compile_runtime_bundle(
    *,
    map_bundle: Path,
    scene_root: Path,
    review_manifest_path: Path,
    alignment_artifact_path: Path | None = None,
    navigation_artifact_path: Path | None = None,
    semantic_projection_artifact_path: Path | None = None,
    navigation_memory_path: Path = DEFAULT_NAVIGATION_MEMORY,
    output_dir: Path,
    include_draft_labels: bool = False,
) -> dict[str, Any]:
    map_bundle = Path(map_bundle)
    scene_root = Path(scene_root)
    review_manifest_path = Path(review_manifest_path)
    navigation_memory_path = Path(navigation_memory_path)
    output_dir = Path(output_dir)
    if not review_manifest_path.is_file():
        raise ValueError(f"review manifest missing: {review_manifest_path}")
    review = json.loads(review_manifest_path.read_text(encoding="utf-8"))
    validate_review_manifest(
        review,
        map_bundle=map_bundle,
        scene_root=scene_root,
        review_manifest_path=review_manifest_path,
    )
    if not scene_root.is_dir():
        raise ValueError(f"scene root does not exist: {scene_root}")
    if not navigation_memory_path.is_file():
        raise ValueError(f"navigation memory missing: {navigation_memory_path}")
    proof = verified_robot_consumption_proof(
        alignment_artifact_path=alignment_artifact_path,
        navigation_artifact_path=navigation_artifact_path,
    )
    room_semantics = verified_room_semantic_projection(
        semantic_projection_artifact_path=semantic_projection_artifact_path,
        review_manifest_path=review_manifest_path,
        review_manifest=review,
    )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _copy_vendor_map12_source(map_bundle, output_dir)

    map_yaml = parse_map_yaml((output_dir / "map.yaml").read_text(encoding="utf-8"))
    origin = _origin_payload(map_yaml)
    grid = load_pgm(
        output_dir / "map.pgm",
        resolution_m=float(map_yaml.get("resolution") or 0.05),
        origin_x=origin["x"],
        origin_y=origin["y"],
    )
    frame_id = "map"
    runtime_labels = runtime_labels_from_review(
        review,
        frame_id=frame_id,
        include_draft_labels=include_draft_labels,
    )
    review_summary = review_validation_summary(review, include_draft_labels=include_draft_labels)
    navigation_memory = json.loads(navigation_memory_path.read_text(encoding="utf-8"))
    waypoints = _inspection_waypoints_from_navigation_memory(
        navigation_memory,
        frame_id=frame_id,
        grid=grid,
    )
    navigation_memory_anchors = _navigation_memory_anchors(navigation_memory, frame_id=frame_id)
    semantics = _runtime_semantics_payload(
        map_bundle=map_bundle,
        review_manifest_path=review_manifest_path,
        navigation_memory_path=navigation_memory_path,
        map_yaml=map_yaml,
        runtime_labels=runtime_labels,
        waypoints=waypoints,
        navigation_memory_anchors=navigation_memory_anchors,
        robot_consumption_proof=proof,
        room_semantic_projection=room_semantics,
        frame_id=frame_id,
    )
    (output_dir / "semantics.json").write_text(
        json.dumps(semantics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_source_frame_bundle_preview(output_dir)
    provenance = runtime_provenance(
        map_bundle=map_bundle,
        scene_root=scene_root,
        review_manifest_path=review_manifest_path,
        navigation_memory_path=navigation_memory_path,
        output_dir=output_dir,
        review=review,
        runtime_labels=runtime_labels,
        review_summary=review_summary,
        robot_consumption_proof=proof,
        room_semantic_projection_proof=room_semantics["proof"],
        include_draft_labels=include_draft_labels,
    )
    (output_dir / "b1_runtime_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    robot_consumption_manifest = b1_robot_consumption_manifest(
        output_dir=output_dir,
        robot_consumption_proof=proof,
        room_semantic_projection_proof=room_semantics["proof"],
        runtime_label_count=len(runtime_labels),
        inspection_waypoint_count=len(semantics["inspection_waypoints"]),
    )
    (output_dir / "b1_robot_consumption_manifest.json").write_text(
        json.dumps(robot_consumption_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    runtime_validation = validate_nav2_map_bundle(output_dir)
    runtime_validation.raise_for_errors()
    return {
        "schema": B1_MAP12_RUNTIME_PROVENANCE_SCHEMA,
        "status": "compiled",
        "output_dir": str(output_dir),
        "robot_consumption_manifest": str(output_dir / "b1_robot_consumption_manifest.json"),
        "runtime_label_count": len(runtime_labels),
        "robot_navigation_supported": proof["robot_navigation_supported"],
        "room_semantics_supported": room_semantics["proof"]["room_semantics_supported"],
        "excluded_label_count": review_summary["excluded_label_count"],
        "validation": runtime_validation.as_dict(),
        "provenance": str(output_dir / "b1_runtime_provenance.json"),
    }


def b1_robot_consumption_manifest(
    *,
    output_dir: Path,
    robot_consumption_proof: dict[str, Any],
    room_semantic_projection_proof: dict[str, Any],
    runtime_label_count: int,
    inspection_waypoint_count: int,
) -> dict[str, Any]:
    navigation_ready = bool(robot_consumption_proof.get("robot_navigation_supported"))
    room_semantics_ready = bool(room_semantic_projection_proof.get("room_semantics_supported"))
    object_semantics_ready = bool(room_semantic_projection_proof.get("object_semantics_supported"))
    return {
        "schema": B1_ROBOT_CONSUMPTION_MANIFEST_SCHEMA,
        "status": "robot_navigation_ready" if navigation_ready else "blocked",
        "map_bundle": str(output_dir),
        "consumer_contract": "nav2_cleanup_bundle_plus_runtime_map_prior_snapshot_v1",
        "required_primary_artifacts": {
            "map_yaml": "map.yaml",
            "occupancy_image": "map.pgm",
            "semantics": "semantics.json",
            "robot_profile": "profiles/rby1m.yaml",
            "costmap_params": "costmaps/rby1m.costmap_params.yaml",
        },
        "optional_product_artifacts": {
            "runtime_map_prior_snapshot": "../runtime_map_prior_snapshot.json",
            "runtime_map_prior_targets": "../runtime_map_prior_targets.json",
        },
        "navigation": {
            "status": robot_consumption_proof.get("status"),
            "ready": navigation_ready,
            "alignment_status": robot_consumption_proof.get("alignment_status"),
            "navigation_status": robot_consumption_proof.get("navigation_status"),
            "alignment_artifact": robot_consumption_proof.get("alignment_artifact"),
            "navigation_artifact": robot_consumption_proof.get("navigation_artifact"),
            "robot_navigation_provenance": robot_consumption_proof.get(
                "robot_navigation_provenance"
            ),
            "navigation_waypoint_count": robot_consumption_proof.get("navigation_waypoint_count"),
            "waypoint_ids": list(robot_consumption_proof.get("waypoint_ids") or []),
        },
        "semantics": {
            "runtime_label_count": int(runtime_label_count),
            "room_semantics_ready": room_semantics_ready,
            "room_semantic_projection_status": room_semantic_projection_proof.get("status"),
            "semantic_projection_artifact": room_semantic_projection_proof.get(
                "semantic_projection_artifact"
            ),
            "room_projection_count": room_semantic_projection_proof.get("room_projection_count"),
            "object_semantics_ready": object_semantics_ready,
            "object_projection_status": room_semantic_projection_proof.get(
                "object_projection_status"
            ),
        },
        "capabilities": {
            "robot_navigation": navigation_ready,
            "room_semantics": room_semantics_ready,
            "object_semantics": object_semantics_ready,
            "manipulation": bool(robot_consumption_proof.get("manipulation_supported")),
        },
        "blocked_capabilities": _blocked_consumption_capabilities(
            robot_consumption_proof=robot_consumption_proof,
            room_semantic_projection_proof=room_semantic_projection_proof,
        ),
        "inspection_waypoint_count": int(inspection_waypoint_count),
        "policy": {
            "explicit_alignment_artifact_required": True,
            "explicit_navigation_artifact_required": True,
            "explicit_semantic_projection_artifact_required_for_room_semantics": True,
            "no_output_directory_autodiscovery": True,
            "object_labels_are_not_inferred_from_room_anchors": True,
        },
    }


def _blocked_consumption_capabilities(
    *,
    robot_consumption_proof: dict[str, Any],
    room_semantic_projection_proof: dict[str, Any],
) -> list[dict[str, Any]]:
    blocked = []
    if not robot_consumption_proof.get("robot_navigation_supported"):
        blocked.append(
            {
                "capability": "robot_navigation",
                "status": robot_consumption_proof.get("status"),
            }
        )
    if not room_semantic_projection_proof.get("room_semantics_supported"):
        blocked.append(
            {
                "capability": "room_semantics",
                "status": room_semantic_projection_proof.get("status"),
            }
        )
    if not room_semantic_projection_proof.get("object_semantics_supported"):
        blocked.append(
            {
                "capability": "object_semantics",
                "status": room_semantic_projection_proof.get("object_projection_status"),
            }
        )
    if not robot_consumption_proof.get("manipulation_supported"):
        blocked.append(
            {
                "capability": "manipulation",
                "status": robot_consumption_proof.get("object_receptacle_usd_binding_status"),
            }
        )
    return blocked


def validate_review_manifest(
    payload: dict[str, Any],
    *,
    map_bundle: Path,
    scene_root: Path,
    review_manifest_path: Path,
) -> list[str]:
    errors = review_manifest_errors(
        payload,
        map_bundle=map_bundle,
        scene_root=scene_root,
        review_manifest_path=review_manifest_path,
    )
    if errors:
        raise ValueError("invalid B1 / Map 12 review manifest: " + "; ".join(errors))
    return []


def review_manifest_errors(
    payload: dict[str, Any],
    *,
    map_bundle: Path,
    scene_root: Path,
    review_manifest_path: Path,
) -> list[str]:
    errors: list[str] = []
    errors.extend(
        _review_manifest_header_errors(
            payload,
            map_bundle=map_bundle,
            scene_root=scene_root,
            review_manifest_path=review_manifest_path,
        )
    )
    labels = payload.get("labels") if isinstance(payload.get("labels"), list) else []
    if not labels:
        errors.append("labels must not be empty")
        return errors
    label_review = _review_manifest_label_review(labels)
    errors.extend(label_review["errors"])
    errors.extend(
        _shared_accepted_label_errors(
            labels,
            accepted_signatures=label_review["accepted_signatures"],
            accepted_map_areas=label_review["accepted_map_areas"],
        )
    )
    return errors


def _review_manifest_header_errors(
    payload: dict[str, Any],
    *,
    map_bundle: Path,
    scene_root: Path,
    review_manifest_path: Path,
) -> list[str]:
    errors = []
    if payload.get("schema") != B1_MAP12_ALIGNMENT_REVIEW_SCHEMA:
        errors.append(f"schema must be {B1_MAP12_ALIGNMENT_REVIEW_SCHEMA}")
    source_assets = (
        payload.get("source_assets") if isinstance(payload.get("source_assets"), dict) else {}
    )
    if not _path_matches(source_assets.get("map_bundle"), map_bundle):
        errors.append("source_assets.map_bundle must match --map-bundle")
    if not _path_matches(source_assets.get("scene_root"), scene_root):
        errors.append("source_assets.scene_root must match --scene-root")
    if not Path(review_manifest_path).is_file():
        errors.append(f"review manifest missing: {review_manifest_path}")
    return errors


def _review_manifest_label_review(labels: list[Any]) -> dict[str, Any]:
    errors = []
    seen_label_ids: set[str] = set()
    accepted_signatures: dict[str, list[str]] = defaultdict(list)
    accepted_map_areas: dict[str, list[str]] = defaultdict(list)
    for index, raw_label in enumerate(labels, start=1):
        label = raw_label if isinstance(raw_label, dict) else {}
        label_id = str(label.get("label_id") or "")
        label_id = _review_manifest_label_id(
            label_id,
            index=index,
            seen_label_ids=seen_label_ids,
            errors=errors,
        )
        label_result = _review_manifest_label_errors(label, label_id=label_id)
        errors.extend(label_result["errors"])
        if label_result["status"] == ACCEPTED_REVIEW_STATUS:
            points = label_result["points"]
            accepted_signatures[_polygon_signature(points)].append(label_id)
            accepted_map_areas[str(label.get("map_area_id") or "")].append(label_id)
    return {
        "errors": errors,
        "accepted_signatures": accepted_signatures,
        "accepted_map_areas": accepted_map_areas,
    }


def _review_manifest_label_id(
    label_id: str,
    *,
    index: int,
    seen_label_ids: set[str],
    errors: list[str],
) -> str:
    if not label_id:
        errors.append(f"labels[{index}] missing label_id")
        label_id = f"labels[{index}]"
    if label_id in seen_label_ids:
        errors.append(f"duplicate label_id: {label_id}")
    seen_label_ids.add(label_id)
    return label_id


def _review_manifest_label_errors(label: dict[str, Any], *, label_id: str) -> dict[str, Any]:
    errors = []
    status = str(label.get("review_status") or "")
    if status not in RUNTIME_LABEL_STATUSES | REVIEW_ONLY_STATUSES:
        errors.append(f"label {label_id} has unsupported review_status {status!r}")
    geometry = label.get("geometry") if isinstance(label.get("geometry"), dict) else {}
    points = _geometry_points(geometry)
    if status == ACCEPTED_REVIEW_STATUS:
        if not str(label.get("scene_partition_id") or ""):
            errors.append(f"accepted label {label_id} missing scene_partition_id")
        if not str(label.get("map_area_id") or ""):
            errors.append(f"accepted label {label_id} missing map_area_id")
        if geometry.get("type") != "map_polygon":
            errors.append(f"accepted label {label_id} geometry.type must be map_polygon")
        if str(geometry.get("frame_id") or "") != "map":
            errors.append(f"accepted label {label_id} geometry.frame_id must be map")
        if len(points) < 3:
            errors.append(f"accepted label {label_id} needs at least three map points")
    return {"errors": errors, "status": status, "points": points}


def _shared_accepted_label_errors(
    labels: list[Any],
    *,
    accepted_signatures: dict[str, list[str]],
    accepted_map_areas: dict[str, list[str]],
) -> list[str]:
    errors = []
    for signature, label_ids in accepted_signatures.items():
        if not signature or len(label_ids) < 2:
            continue
        if not _accepted_labels_have_explicit_shared_policy(labels, label_ids):
            errors.append(
                "accepted labels share geometry without shared_area_policy=composite_area: "
                + ", ".join(label_ids)
            )
    for area_id, label_ids in accepted_map_areas.items():
        if not area_id or len(label_ids) < 2:
            continue
        if not _accepted_labels_have_explicit_shared_policy(labels, label_ids):
            errors.append(
                "accepted labels share map_area_id without shared_area_policy=composite_area: "
                + ", ".join(label_ids)
            )
    return errors


def _accepted_labels_have_explicit_shared_policy(
    labels: list[Any],
    label_ids: list[str],
) -> bool:
    policies = {
        str(label.get("shared_area_policy") or "")
        for label in labels
        if isinstance(label, dict) and str(label.get("label_id") or "") in label_ids
    }
    return bool(policies) and policies <= EXPLICIT_SHARED_AREA_POLICIES


def runtime_labels_from_review(
    payload: dict[str, Any],
    *,
    frame_id: str,
    include_draft_labels: bool = False,
) -> list[dict[str, Any]]:
    labels = []
    for raw_label in payload.get("labels") or []:
        if not isinstance(raw_label, dict):
            continue
        status = str(raw_label.get("review_status") or "")
        if status != ACCEPTED_REVIEW_STATUS and not include_draft_labels:
            continue
        geometry = raw_label.get("geometry") if isinstance(raw_label.get("geometry"), dict) else {}
        points = _geometry_points(geometry)
        if len(points) < 3:
            continue
        label_id = str(raw_label.get("label_id") or "")
        labels.append(
            {
                "label_id": label_id,
                "room_label": str(raw_label.get("room_label") or label_id),
                "category": str(raw_label.get("category") or ""),
                "scene_partition_id": str(raw_label.get("scene_partition_id") or ""),
                "map_area_id": str(raw_label.get("map_area_id") or ""),
                "review_status": status,
                "alignment_status": ALIGNMENT_STATUS_CANDIDATE,
                "source_map_frame_id": frame_id,
                "geometry_source": str(
                    geometry.get("source") or GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE
                ),
                "polygon_role": POLYGON_ROLE_NAVIGATION_AREA,
                "polygon": points,
                "map_center": _polygon_center(points),
                "operator_note": str(raw_label.get("operator_note") or ""),
                "shared_area_policy": str(raw_label.get("shared_area_policy") or ""),
            }
        )
    return labels


def review_validation_summary(
    payload: dict[str, Any],
    *,
    include_draft_labels: bool,
) -> dict[str, Any]:
    statuses = Counter(
        str(label.get("review_status") or "")
        for label in payload.get("labels") or []
        if isinstance(label, dict)
    )
    included = [
        label
        for label in payload.get("labels") or []
        if isinstance(label, dict)
        and (
            str(label.get("review_status") or "") == ACCEPTED_REVIEW_STATUS or include_draft_labels
        )
    ]
    return {
        "status_counts": dict(sorted(statuses.items())),
        "included_label_count": len(included),
        "excluded_label_count": max(0, sum(statuses.values()) - len(included)),
        "draft_label_policy": (
            "included_for_debug_only" if include_draft_labels else "excluded_by_default"
        ),
        "duplicate_shared_area_policy": "accepted labels require shared_area_policy=composite_area",
    }


def verified_robot_consumption_proof(
    *,
    alignment_artifact_path: Path | None,
    navigation_artifact_path: Path | None,
) -> dict[str, Any]:
    if alignment_artifact_path is None and navigation_artifact_path is not None:
        raise ValueError("navigation artifact requires --alignment-artifact")
    proof = _blocked_robot_consumption_proof()
    if alignment_artifact_path is None:
        return proof

    alignment_artifact_path, alignment = _verified_alignment_artifact(alignment_artifact_path)
    proof.update(_verified_alignment_proof(alignment_artifact_path, alignment))
    if navigation_artifact_path is None:
        return proof

    navigation_artifact_path, navigation = _verified_navigation_artifact(
        navigation_artifact_path,
        alignment_artifact_path=alignment_artifact_path,
    )
    proof.update(_verified_navigation_proof(navigation_artifact_path, navigation))
    return proof


def _blocked_robot_consumption_proof() -> dict[str, Any]:
    return {
        "schema": "b1_map12_robot_consumption_proof_v1",
        "status": "blocked_missing_verified_alignment",
        "alignment_status": "not_provided",
        "navigation_status": "not_provided",
        "alignment_artifact": "",
        "navigation_artifact": "",
        "robot_navigation_supported": False,
        "robot_navigation_provenance": "pending_local_isaac_b1_map12_navigation_smoke",
        "navigation_waypoint_count": 0,
        "robot_view_evidence_status": "not_available",
        "planner_backed": False,
        "physical_robot": False,
        "manipulation_supported": False,
        "object_receptacle_usd_binding_status": "blocked_out_of_scope",
        "policy": {
            "requires_explicit_alignment_artifact": True,
            "requires_explicit_navigation_artifact": True,
            "rejects_missing_or_invalid_artifacts": True,
            "no_output_directory_autodiscovery": True,
        },
    }


def _verified_alignment_artifact(alignment_artifact_path: Path) -> tuple[Path, dict[str, Any]]:
    alignment_artifact_path = Path(alignment_artifact_path)
    if not alignment_artifact_path.is_file():
        raise ValueError(f"alignment artifact missing: {alignment_artifact_path}")
    alignment = json.loads(alignment_artifact_path.read_text(encoding="utf-8"))
    alignment_errors = validate_alignment_residual_artifact(alignment)
    if alignment_errors:
        raise ValueError("invalid alignment artifact: " + "; ".join(alignment_errors))
    if alignment.get("global_alignment_status") != "verified":
        raise ValueError("alignment artifact must be globally verified")
    return alignment_artifact_path, alignment


def _verified_alignment_proof(
    alignment_artifact_path: Path,
    alignment: dict[str, Any],
) -> dict[str, Any]:
    residual = _dict(alignment.get("residual_evidence"))
    return {
        "status": "verified_alignment_navigation_pending",
        "alignment_status": "verified",
        "alignment_artifact": str(alignment_artifact_path),
        "alignment_transform_source": str(residual.get("transform_source") or ""),
        "selected_transform_type": str(alignment.get("selected_transform_type") or ""),
        "matched_anchor_count": int(residual.get("matched_anchor_count") or 0),
        "mean_residual_m": residual.get("mean_residual_m"),
        "p90_residual_m": residual.get("p90_residual_m"),
        "max_residual_m": residual.get("max_residual_m"),
    }


def _verified_navigation_artifact(
    navigation_artifact_path: Path,
    *,
    alignment_artifact_path: Path,
) -> tuple[Path, dict[str, Any]]:
    navigation_artifact_path = Path(navigation_artifact_path)
    if not navigation_artifact_path.is_file():
        raise ValueError(f"navigation artifact missing: {navigation_artifact_path}")
    navigation = json.loads(navigation_artifact_path.read_text(encoding="utf-8"))
    navigation_errors = validate_navigation_smoke_artifact(navigation, require_files=True)
    if navigation_errors:
        raise ValueError("invalid navigation artifact: " + "; ".join(navigation_errors))
    if str(navigation.get("alignment_artifact") or "") != str(alignment_artifact_path):
        raise ValueError("navigation artifact alignment_artifact must match --alignment-artifact")
    if navigation.get("robot_navigation_supported") is not True:
        raise ValueError("navigation artifact must claim robot_navigation_supported=true")
    return navigation_artifact_path, navigation


def _verified_navigation_proof(
    navigation_artifact_path: Path,
    navigation: dict[str, Any],
) -> dict[str, Any]:
    waypoint_evidence = [
        item for item in navigation.get("waypoint_evidence") or [] if isinstance(item, dict)
    ]
    return {
        "status": "robot_navigation_verified",
        "navigation_status": "verified",
        "navigation_artifact": str(navigation_artifact_path),
        "render_scene_usd": str(navigation.get("b1_scene_usd") or ""),
        "visual_route": _dict(navigation.get("visual_route")),
        "robot_navigation_supported": True,
        "robot_navigation_provenance": NAVIGATION_PROVENANCE,
        "navigation_waypoint_count": int(navigation.get("navigation_waypoint_count") or 0),
        "robot_view_evidence_status": str(navigation.get("robot_view_evidence_status") or ""),
        "navigation_provenance": str(navigation.get("navigation_provenance") or ""),
        "same_pose_views": _same_pose_view_support(waypoint_evidence),
        "waypoint_ids": [str(item.get("waypoint_id") or "") for item in waypoint_evidence],
    }


def _same_pose_view_support(waypoint_evidence: list[dict[str, Any]]) -> dict[str, bool]:
    if not waypoint_evidence:
        return {"fpv": False, "chase": False, "topdown": False}

    def has_view(item: dict[str, Any], *view_names: str) -> bool:
        views = item.get("views") if isinstance(item.get("views"), dict) else {}
        return any(bool(views.get(view_name)) for view_name in view_names)

    return {
        "fpv": all(has_view(item, "fpv") for item in waypoint_evidence),
        "chase": all(has_view(item, "chase") for item in waypoint_evidence),
        "topdown": all(has_view(item, "topdown", "map") for item in waypoint_evidence),
    }


def render_observation_proof(robot_consumption_proof: dict[str, Any]) -> dict[str, Any]:
    navigation_ready = bool(robot_consumption_proof.get("robot_navigation_supported"))
    robot_view_ready = (
        str(robot_consumption_proof.get("robot_view_evidence_status") or "") == "available"
    )
    same_pose_views = (
        robot_consumption_proof.get("same_pose_views")
        if isinstance(robot_consumption_proof.get("same_pose_views"), dict)
        else {}
    )
    render_ready = navigation_ready and robot_view_ready
    render_scene_usd = str(robot_consumption_proof.get("render_scene_usd") or "")
    selected_v1_route = render_ready and render_scene_usd == str(DEFAULT_B1_VISUAL_ROUTE_SCENE_USD)
    return {
        "schema": "b1_map12_render_observation_proof_v1",
        "status": "same_pose_render_observation_verified"
        if render_ready
        else "blocked_missing_verified_same_pose_render_evidence",
        "render_observation_supported": render_ready,
        "render_provenance": str(robot_consumption_proof.get("robot_navigation_provenance") or ""),
        "navigation_artifact": str(robot_consumption_proof.get("navigation_artifact") or ""),
        "alignment_artifact": str(robot_consumption_proof.get("alignment_artifact") or ""),
        "same_pose_fpv_supported": render_ready and bool(same_pose_views.get("fpv")),
        "same_pose_chase_supported": render_ready and bool(same_pose_views.get("chase")),
        "same_pose_topdown_supported": render_ready and bool(same_pose_views.get("topdown")),
        "view_evidence_status": str(
            robot_consumption_proof.get("robot_view_evidence_status") or ""
        ),
        "default_visual_route": {
            "scene_id": "B1_floor2_slow",
            "scene_root": "data/robot-data-lab/scene-engine/data/B1_floor2_slow",
            "scene_usd": str(DEFAULT_B1_VISUAL_ROUTE_SCENE_USD),
            "selected": selected_v1_route,
            "status": "selected_verified_same_pose_render_route"
            if selected_v1_route
            else "blocked_missing_verified_b1_floor2_slow_render_proof",
            "reason": (
                "B1_floor2_slow has verified same-pose FPV/Chase/topdown render evidence "
                "for the accepted Map12 frame."
                if selected_v1_route
                else (
                    "B1_floor2_slow has not been verified against the accepted Map12 "
                    "frame with same-pose FPV/Chase/topdown render evidence."
                )
            ),
        },
        "fallback_visual_route": {
            "scene_id": "2rd_floor_seperated",
            "scene_root": "data/robot-data-lab/scene-engine/data/2rd_floor_seperated",
            "selected_as_default": False,
            "status": "registration_source_only_for_p0",
        },
        "policy": {
            "requires_explicit_same_pose_render_artifact": True,
            "does_not_select_unverified_b1_floor2_slow": True,
            "no_output_directory_autodiscovery": True,
        },
    }


def verified_room_semantic_projection(
    *,
    semantic_projection_artifact_path: Path | None,
    review_manifest_path: Path,
    review_manifest: dict[str, Any],
) -> dict[str, Any]:
    proof = {
        "schema": "b1_map12_room_semantics_proof_v1",
        "status": "blocked_missing_accepted_semantic_anchors",
        "semantic_projection_artifact": "",
        "room_semantics_supported": False,
        "room_projection_count": 0,
        "semantic_anchor_count": 0,
        "object_projection_status": "blocked_until_object_semantic_anchors",
        "object_semantics_supported": False,
        "policy": {
            "requires_explicit_semantic_projection_artifact": True,
            "rejects_missing_or_invalid_artifacts": True,
            "no_output_directory_autodiscovery": True,
            "object_labels_are_not_inferred_from_room_anchors": True,
        },
    }
    if semantic_projection_artifact_path is None:
        return {"proof": proof, "rooms": None}

    semantic_projection_artifact_path = Path(semantic_projection_artifact_path)
    if not semantic_projection_artifact_path.is_file():
        raise ValueError(
            f"semantic projection artifact missing: {semantic_projection_artifact_path}"
        )
    projection = json.loads(semantic_projection_artifact_path.read_text(encoding="utf-8"))
    errors = semantic_projection_errors(
        projection,
        review_manifest_path=review_manifest_path,
        review_manifest=review_manifest,
    )
    if errors:
        raise ValueError("invalid semantic projection artifact: " + "; ".join(errors))
    rooms = semantic_projection_rooms(projection)
    proof.update(
        {
            "status": "verified_room_semantics",
            "semantic_projection_artifact": str(semantic_projection_artifact_path),
            "room_semantics_supported": True,
            "room_projection_count": len(rooms),
            "semantic_anchor_count": int(projection.get("semantic_anchor_count") or 0),
            "object_projection_status": str(projection.get("object_projection_status") or ""),
            "source_correspondences": str(projection.get("source_correspondences") or ""),
            "source_review_manifest": str(projection.get("source_review_manifest") or ""),
        }
    )
    return {"proof": proof, "rooms": rooms}


def semantic_projection_errors(
    projection: dict[str, Any],
    *,
    review_manifest_path: Path,
    review_manifest: dict[str, Any],
) -> list[str]:
    rooms = _semantic_projection_room_rows(projection)
    errors = _semantic_projection_header_errors(
        projection,
        review_manifest_path=review_manifest_path,
        rooms=rooms,
    )
    accepted_labels = _accepted_review_labels_by_id(review_manifest)
    seen_room_ids: set[str] = set()
    for index, room in enumerate(rooms, start=1):
        room_errors = semantic_projection_room_errors(
            room,
            accepted_labels=accepted_labels,
        )
        errors.extend(f"rooms[{index}]: {error}" for error in room_errors)
        room_id = _semantic_projection_room_id(room)
        if room_id in seen_room_ids:
            errors.append(f"duplicate room_id: {room_id}")
        seen_room_ids.add(room_id)
    return errors


def _semantic_projection_header_errors(
    projection: dict[str, Any],
    *,
    review_manifest_path: Path,
    rooms: list[Any],
) -> list[str]:
    errors = []
    if projection.get("schema") != SEMANTIC_PROJECTION_SCHEMA:
        errors.append(f"schema must be {SEMANTIC_PROJECTION_SCHEMA}")
    if projection.get("status") != "verified_room_semantics":
        errors.append("status must be verified_room_semantics")
    if not _path_matches(projection.get("source_review_manifest"), review_manifest_path):
        errors.append("source_review_manifest must match --review-manifest")
    errors.extend(_semantic_projection_object_policy_errors(projection))
    if not rooms:
        errors.append("rooms must not be empty")
    if int(projection.get("room_projection_count") or 0) != len(rooms):
        errors.append("room_projection_count must match rooms")
    if int(projection.get("semantic_anchor_count") or 0) < len(rooms):
        errors.append("semantic_anchor_count must cover projected rooms")
    return errors


def _semantic_projection_object_policy_errors(projection: dict[str, Any]) -> list[str]:
    errors = []
    if projection.get("object_projection_status") != "blocked_until_object_semantic_anchors":
        errors.append("object_projection_status must remain blocked_until_object_semantic_anchors")
    if projection.get("objects"):
        errors.append("objects must stay empty until object semantic anchors exist")
    policy = _dict(projection.get("policy"))
    if policy.get("requires_accepted_semantic_anchors") is not True:
        errors.append("policy.requires_accepted_semantic_anchors must be true")
    if policy.get("object_labels_are_not_inferred_from_room_anchors") is not True:
        errors.append("policy.object_labels_are_not_inferred_from_room_anchors must be true")
    return errors


def _semantic_projection_room_rows(projection: dict[str, Any]) -> list[Any]:
    rooms = projection.get("rooms")
    return rooms if isinstance(rooms, list) else []


def _accepted_review_labels_by_id(review_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(label.get("label_id") or ""): label
        for label in review_manifest.get("labels") or []
        if isinstance(label, dict) and label.get("review_status") == ACCEPTED_REVIEW_STATUS
    }


def _semantic_projection_room_id(room: Any) -> str:
    return str(room.get("room_id") or "") if isinstance(room, dict) else ""


def semantic_projection_room_errors(
    room: Any,
    *,
    accepted_labels: dict[str, dict[str, Any]],
) -> list[str]:
    if not isinstance(room, dict):
        return ["room must be an object"]
    errors = []
    room_id = str(room.get("room_id") or "")
    source_label_id = str(room.get("source_label_id") or room_id)
    label = accepted_labels.get(source_label_id)
    if label is None:
        errors.append(f"source_label_id {source_label_id!r} is not an accepted review label")
    else:
        errors.extend(_semantic_projection_label_binding_errors(room, label))
    errors.extend(_semantic_projection_room_contract_errors(room_id, room))
    errors.extend(_semantic_projection_room_geometry_errors(room))
    return errors


def _semantic_projection_label_binding_errors(
    room: dict[str, Any],
    label: dict[str, Any],
) -> list[str]:
    errors = []
    if str(room.get("navigation_area_id") or "") != str(label.get("map_area_id") or ""):
        errors.append("navigation_area_id must match accepted review label map_area_id")
    if str(room.get("asset_partition_id") or "") != str(label.get("scene_partition_id") or ""):
        errors.append("asset_partition_id must match accepted review label scene_partition_id")
    return errors


def _semantic_projection_room_contract_errors(
    room_id: str,
    room: dict[str, Any],
) -> list[str]:
    expected_values = {
        "review_status": ACCEPTED_REVIEW_STATUS,
        "semantic_source": "reviewed_b1_map12_semantic_anchor",
        "alignment_status": "accepted_semantic_anchor",
    }
    errors = ["room_id is required"] if not room_id else []
    for field_name, expected in expected_values.items():
        if str(room.get(field_name) or "") != expected:
            errors.append(f"{field_name} must be {expected}")
    anchors = room.get("semantic_anchors")
    if not isinstance(anchors, list) or not anchors:
        errors.append("semantic_anchors must not be empty")
    return errors


def _semantic_projection_room_geometry_errors(room: dict[str, Any]) -> list[str]:
    polygon = room.get("map_polygon")
    if not isinstance(polygon, list) or len(polygon) < 3:
        return ["map_polygon must contain at least three points"]
    if any(
        not isinstance(point, dict) or "x" not in point or "y" not in point for point in polygon
    ):
        return ["map_polygon points must contain x/y"]
    return []


def semantic_projection_rooms(projection: dict[str, Any]) -> list[dict[str, Any]]:
    rooms = []
    for room in projection.get("rooms") or []:
        map_polygon = [
            {"x": float(point["x"]), "y": float(point["y"])}
            for point in room.get("map_polygon") or []
        ]
        rooms.append(
            {
                "room_id": str(room.get("room_id") or ""),
                "room_label": str(room.get("room_label") or room.get("room_id") or ""),
                "category": str(room.get("category") or ""),
                "polygon": map_polygon,
                "review_status": ACCEPTED_REVIEW_STATUS,
                "map_area_id": str(room.get("navigation_area_id") or ""),
                "scene_partition_id": str(room.get("asset_partition_id") or ""),
                "semantic_anchor_count": int(room.get("semantic_anchor_count") or 0),
                "semantic_anchors": list(room.get("semantic_anchors") or []),
                "semantic_source": str(room.get("semantic_source") or ""),
                "source_label_id": str(room.get("source_label_id") or ""),
                "source_anchor_ids": list(room.get("source_anchor_ids") or []),
            }
        )
    return rooms


def runtime_provenance(
    *,
    map_bundle: Path,
    scene_root: Path,
    review_manifest_path: Path,
    navigation_memory_path: Path,
    output_dir: Path,
    review: dict[str, Any],
    runtime_labels: list[dict[str, Any]],
    review_summary: dict[str, Any],
    robot_consumption_proof: dict[str, Any],
    room_semantic_projection_proof: dict[str, Any],
    include_draft_labels: bool,
) -> dict[str, Any]:
    source_files = [
        map_bundle / "nav2.yaml",
        map_bundle / "occupancy.pgm",
        map_bundle / "raw_map.json.gz",
        map_bundle / "source.json",
        navigation_memory_path,
        review_manifest_path,
    ]
    semantic_projection_artifact = str(
        room_semantic_projection_proof["semantic_projection_artifact"]
    )
    if semantic_projection_artifact:
        source_files.append(Path(semantic_projection_artifact))
    return {
        "schema": B1_MAP12_RUNTIME_PROVENANCE_SCHEMA,
        "generated_from_review_manifest": True,
        "generated_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "compiler": _repo_relative_path(Path(__file__)),
        "source_assets": {
            "map_bundle": str(map_bundle),
            "scene_root": str(scene_root),
            "review_manifest": str(review_manifest_path),
            "navigation_memory": str(navigation_memory_path),
            "review_schema": str(review.get("schema") or ""),
        },
        "output_dir": str(output_dir),
        "source_file_hashes": {
            str(path): _file_sha256(path) for path in source_files if path.is_file()
        },
        "include_draft_labels": include_draft_labels,
        "runtime_label_count": len(runtime_labels),
        "robot_consumption_proof": {
            "status": robot_consumption_proof["status"],
            "alignment_artifact": robot_consumption_proof["alignment_artifact"],
            "navigation_artifact": robot_consumption_proof["navigation_artifact"],
            "robot_navigation_supported": robot_consumption_proof["robot_navigation_supported"],
        },
        "room_semantic_projection_proof": {
            "status": room_semantic_projection_proof["status"],
            "semantic_projection_artifact": room_semantic_projection_proof[
                "semantic_projection_artifact"
            ],
            "room_semantics_supported": room_semantic_projection_proof["room_semantics_supported"],
            "object_projection_status": room_semantic_projection_proof["object_projection_status"],
        },
        "review_validation": review_summary,
        "public_contract_note": (
            "This generated bundle preserves raw Map12 navigation layers. Human review "
            "labels are compiled as a semantic label layer and do not retarget waypoints "
            "or rebuild driveable ways."
        ),
    }


def _copy_vendor_map12_source(source: Path, output_dir: Path) -> None:
    required = {
        "nav2.yaml": source / "nav2.yaml",
        "occupancy.pgm": source / "occupancy.pgm",
        "source.json": source / "source.json",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise ValueError("raw Map12 source is incomplete: " + ", ".join(missing))
    (output_dir / "map.yaml").write_text(
        _runtime_map_yaml(parse_map_yaml(required["nav2.yaml"].read_text(encoding="utf-8"))),
        encoding="utf-8",
    )
    shutil.copy2(required["occupancy.pgm"], output_dir / "map.pgm")
    shutil.copy2(required["source.json"], output_dir / "source.json")
    if (source / "raw_map.json.gz").is_file():
        shutil.copy2(source / "raw_map.json.gz", output_dir / "raw_map.json.gz")
    profiles_dir = output_dir / "profiles"
    costmaps_dir = output_dir / "costmaps"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    costmaps_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "rby1m.yaml").write_text(
        _simple_yaml(DEFAULT_ROBOT_PROFILE),
        encoding="utf-8",
    )
    (costmaps_dir / "rby1m.costmap_params.yaml").write_text(
        _costmap_yaml(),
        encoding="utf-8",
    )


def _runtime_semantics_payload(
    *,
    map_bundle: Path,
    review_manifest_path: Path,
    navigation_memory_path: Path,
    map_yaml: dict[str, Any],
    runtime_labels: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
    navigation_memory_anchors: list[dict[str, Any]],
    robot_consumption_proof: dict[str, Any],
    room_semantic_projection: dict[str, Any],
    frame_id: str,
) -> dict[str, Any]:
    projected_rooms = room_semantic_projection["rooms"]
    rooms = (
        _rooms_from_verified_semantic_projection(projected_rooms, frame_id=frame_id)
        if projected_rooms is not None
        else _rooms_from_review_labels(runtime_labels, frame_id=frame_id)
    )
    room_waypoints = _room_waypoints_from_rooms(rooms, frame_id=frame_id)
    alignment_status = (
        ALIGNMENT_STATUS_VERIFIED
        if robot_consumption_proof["alignment_status"] == "verified"
        else ALIGNMENT_STATUS_CANDIDATE
    )
    return {
        "schema": "nav2_cleanup_semantics_v1",
        "environment_id": "agibot-robot-map-12",
        "frame_ids": {
            "map": frame_id,
            "base": DEFAULT_ROBOT_PROFILE["base_frame_id"],
            "camera": DEFAULT_ROBOT_PROFILE["camera"]["frame_id"],
        },
        "spatial_contract": source_frame_spatial_contract(
            frame_id=frame_id,
            alignment_status=alignment_status,
        ),
        "display_frame": None,
        "map_id": "agibot-robot-map-12_base_navigation_map",
        "map_version": "robot_map_12_vendor_review_v1",
        "resolution_m": float(map_yaml.get("resolution") or 0.05),
        "origin": _origin_payload(map_yaml),
        "rooms": rooms,
        "fixtures": [],
        "inspection_waypoints": [*room_waypoints, *waypoints],
        "driveable_ways": _driveable_ways_from_rooms(rooms),
        "navigation_memory_anchors": navigation_memory_anchors,
        "digital_twin_capabilities": {
            "robot_consumption_proof": robot_consumption_proof,
            "render_observation_proof": render_observation_proof(robot_consumption_proof),
            "room_semantic_projection_proof": room_semantic_projection["proof"],
        },
        "review_labels": runtime_labels,
        "room_category_hints": _room_category_hints_from_review(runtime_labels),
        "provenance": {
            "source": "vendor_robot_map_12_plus_review_manifest",
            "raw_map_bundle": str(map_bundle),
            "navigation_memory": str(navigation_memory_path),
            "generated_from_review_manifest": True,
            "b1_alignment_review_schema": B1_MAP12_ALIGNMENT_REVIEW_SCHEMA,
            "b1_alignment_review_source": str(review_manifest_path),
            "b1_runtime_compiler": _repo_relative_path(Path(__file__)),
            "contains_private_scoring_truth": False,
            "contains_runtime_observations": False,
            "contains_verified_robot_consumption_proof": bool(
                robot_consumption_proof["robot_navigation_supported"]
            ),
            "contains_verified_room_semantics": bool(
                room_semantic_projection["proof"]["room_semantics_supported"]
            ),
        },
    }


def _rooms_from_review_labels(
    labels: list[dict[str, Any]],
    *,
    frame_id: str,
) -> list[dict[str, Any]]:
    rooms = []
    for label in labels:
        label_id = str(label.get("label_id") or "")
        rooms.append(
            {
                "room_id": label_id,
                "room_label": str(label.get("room_label") or label_id),
                "category": str(label.get("category") or ""),
                "polygon": [dict(point) for point in label.get("polygon") or []],
                "review_status": str(label.get("review_status") or ""),
                "map_area_id": str(label.get("map_area_id") or ""),
                "scene_partition_id": str(label.get("scene_partition_id") or ""),
            }
        )
    return normalize_spatial_rooms(
        rooms,
        frame_id=frame_id,
        polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
        geometry_source=GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
        alignment_status=ALIGNMENT_STATUS_CANDIDATE,
        semantic_label_status=ALIGNMENT_STATUS_CANDIDATE,
    )


def _rooms_from_verified_semantic_projection(
    rooms: list[dict[str, Any]],
    *,
    frame_id: str,
) -> list[dict[str, Any]]:
    return normalize_spatial_rooms(
        rooms,
        frame_id=frame_id,
        polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
        geometry_source=GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
        alignment_status=ALIGNMENT_STATUS_VERIFIED,
        semantic_label_status=ALIGNMENT_STATUS_VERIFIED,
    )


def _inspection_waypoints_from_navigation_memory(
    payload: dict[str, Any],
    *,
    frame_id: str,
    grid: OccupancyGrid,
) -> list[dict[str, Any]]:
    waypoints = []
    for index, item in enumerate(_navigation_memory_items(payload), start=1):
        if not isinstance(item, dict):
            continue
        nav_goal = item.get("nav_goal") if isinstance(item.get("nav_goal"), dict) else {}
        pose = item.get("pose") if isinstance(item.get("pose"), dict) else {}
        source_name, source = _first_free_navigation_memory_point(
            nav_goal=nav_goal,
            pose=pose,
            grid=grid,
        )
        if source is None:
            continue
        try:
            x = float(source["x"])
            y = float(source["y"])
        except (KeyError, TypeError, ValueError):
            continue
        item_id = str(item.get("id") or f"navigation_memory_{index:03d}")
        waypoints.append(
            {
                "waypoint_id": f"navmem_{item_id}",
                "frame_id": frame_id,
                "x": x,
                "y": y,
                "yaw": float(source.get("yaw") or 0.0),
                "room_id": "",
                "label": str(item.get("label") or item_id),
                "purpose": str(item.get("kind") or "navigation_memory_anchor"),
                "waypoint_source": "generated_exploration_candidate",
                "source_navigation_memory_id": item_id,
                "source_navigation_memory_point": source_name,
            }
        )
    if not waypoints:
        raise ValueError("navigation_memory.json did not yield any waypoints")
    return waypoints


def _first_free_navigation_memory_point(
    *,
    nav_goal: dict[str, Any],
    pose: dict[str, Any],
    grid: OccupancyGrid,
) -> tuple[str, dict[str, Any] | None]:
    for source_name, source in (("nav_goal", nav_goal), ("pose", pose)):
        if not source:
            continue
        try:
            x = float(source["x"])
            y = float(source["y"])
        except (KeyError, TypeError, ValueError):
            continue
        if grid.is_free_world(x, y):
            return source_name, source
    return "", None


def _navigation_memory_anchors(payload: dict[str, Any], *, frame_id: str) -> list[dict[str, Any]]:
    anchors = []
    for index, item in enumerate(_navigation_memory_items(payload), start=1):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or f"navigation_memory_{index:03d}")
        anchors.append(
            {
                "id": item_id,
                "label": str(item.get("label") or item_id),
                "kind": str(item.get("kind") or ""),
                "scene_id": str(item.get("scene_id") or ""),
                "pose": _navigation_memory_point(item.get("pose"), frame_id=frame_id),
                "nav_goal": _navigation_memory_point(item.get("nav_goal"), frame_id=frame_id),
                "source": str(item.get("source") or ""),
                "confidence": _optional_float(item.get("confidence")),
                "provenance": "navigation_memory.json",
            }
        )
    return anchors


def _navigation_memory_point(payload: Any, *, frame_id: str) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or "x" not in payload or "y" not in payload:
        return None
    try:
        x = float(payload["x"])
        y = float(payload["y"])
    except (TypeError, ValueError):
        return None
    return {
        "frame_id": frame_id,
        "x": x,
        "y": y,
        "z": _optional_float(payload.get("z")),
        "yaw": _optional_float(payload.get("yaw")),
    }


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _room_waypoints_from_review_labels(
    labels: list[dict[str, Any]],
    *,
    frame_id: str,
) -> list[dict[str, Any]]:
    waypoints = []
    for label in labels:
        label_id = str(label.get("label_id") or "")
        center = label.get("map_center") if isinstance(label.get("map_center"), dict) else {}
        if not label_id or not center:
            continue
        waypoints.append(
            {
                "waypoint_id": f"{label_id}_center",
                "frame_id": frame_id,
                "x": float(center.get("x") or 0.0),
                "y": float(center.get("y") or 0.0),
                "yaw": 0.0,
                "room_id": label_id,
                "label": str(label.get("room_label") or label_id),
                "purpose": "reviewed_room_center",
                "waypoint_source": "generated_exploration_candidate",
            }
        )
    return waypoints


def _room_waypoints_from_rooms(
    rooms: list[dict[str, Any]],
    *,
    frame_id: str,
) -> list[dict[str, Any]]:
    waypoints = []
    for room in rooms:
        room_id = str(room.get("room_id") or "")
        polygon = room.get("polygon") if isinstance(room.get("polygon"), list) else []
        points = [
            {"x": float(point["x"]), "y": float(point["y"])}
            for point in polygon
            if isinstance(point, dict) and "x" in point and "y" in point
        ]
        if not room_id or len(points) < 3:
            continue
        center = _polygon_center(points)
        waypoints.append(
            {
                "waypoint_id": f"{room_id}_center",
                "frame_id": frame_id,
                "x": center["x"],
                "y": center["y"],
                "yaw": 0.0,
                "room_id": room_id,
                "label": str(room.get("room_label") or room_id),
                "purpose": "reviewed_room_center",
                "waypoint_source": "generated_exploration_candidate",
            }
        )
    return waypoints


def _navigation_memory_items(payload: dict[str, Any]) -> list[Any]:
    if isinstance(payload.get("items"), list):
        return list(payload["items"])
    catalog = payload.get("catalog") if isinstance(payload.get("catalog"), dict) else {}
    memory = catalog.get("navigation_memory")
    return list(memory) if isinstance(memory, list) else []


def _driveable_ways_from_rooms(rooms: list[dict[str, Any]]) -> list[dict[str, str]]:
    room_ids = [str(room.get("room_id") or "") for room in rooms if room.get("room_id")]
    return [{"from_room_id": room_id, "to_room_id": room_id} for room_id in room_ids]


def _origin_payload(map_yaml: dict[str, Any]) -> dict[str, float]:
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else []
    origin = (origin + [0.0, 0.0, 0.0])[:3]
    return {
        "x": float(origin[0]),
        "y": float(origin[1]),
        "yaw": float(origin[2]),
    }


def _runtime_map_yaml(map_yaml: dict[str, Any]) -> str:
    origin = _origin_payload(map_yaml)
    return "\n".join(
        [
            "image: map.pgm",
            f"resolution: {float(map_yaml.get('resolution') or 0.05):.12g}",
            f"origin: [{origin['x']:.12g}, {origin['y']:.12g}, {origin['yaw']:.12g}]",
            f"negate: {int(map_yaml.get('negate') or 0)}",
            f"occupied_thresh: {float(map_yaml.get('occupied_thresh') or 0.65):.12g}",
            f"free_thresh: {float(map_yaml.get('free_thresh') or 0.196):.12g}",
            "",
        ]
    )


def _costmap_yaml() -> str:
    payload = {
        "global_costmap": {
            "global_costmap": {
                "ros__parameters": {
                    "global_frame": "map",
                    "robot_base_frame": DEFAULT_ROBOT_PROFILE["base_frame_id"],
                    "resolution": DEFAULT_COSTMAP_PARAMETERS["resolution_m"],
                    "footprint_padding": 0.01,
                    "plugins": ["static_layer", "inflation_layer"],
                    "static_layer": {
                        "plugin": "nav2_costmap_2d::StaticLayer",
                        "map_subscribe_transient_local": True,
                    },
                    "inflation_layer": {
                        "plugin": "nav2_costmap_2d::InflationLayer",
                        "inflation_radius": DEFAULT_COSTMAP_PARAMETERS["inflation_radius_m"],
                        "cost_scaling_factor": DEFAULT_COSTMAP_PARAMETERS["cost_scaling_factor"],
                    },
                }
            }
        }
    }
    return _simple_yaml(payload)


def _simple_yaml(value: Any, *, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(_simple_yaml(item, indent=indent + 2).rstrip())
            elif isinstance(item, list):
                lines.append(f"{prefix}{key}:")
                for entry in item:
                    lines.append(f"{prefix}  - {entry}")
            else:
                lines.append(f"{prefix}{key}: {item}")
        return "\n".join(lines) + "\n"
    return f"{prefix}{value}\n"


def _room_category_hints_from_review(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hints = []
    for label in labels:
        hints.append(
            {
                "room_id": str(label.get("label_id") or ""),
                "room_label": str(label.get("room_label") or label.get("label_id") or ""),
                "category": str(label.get("category") or ""),
                "source": "b1_map12_alignment_review",
                "review_status": str(label.get("review_status") or ""),
                "map_area_id": str(label.get("map_area_id") or ""),
            }
        )
    return hints


def _source_map_frame_id(semantics: dict[str, Any]) -> str:
    frame_ids = semantics.get("frame_ids") if isinstance(semantics.get("frame_ids"), dict) else {}
    return str(frame_ids.get("map") or "map")


def _geometry_points(geometry: dict[str, Any]) -> list[dict[str, float]]:
    points = []
    for raw_point in geometry.get("points") or geometry.get("polygon") or []:
        if not isinstance(raw_point, dict):
            continue
        try:
            points.append({"x": float(raw_point["x"]), "y": float(raw_point["y"])})
        except (KeyError, TypeError, ValueError):
            continue
    return points


def _polygon_center(points: list[dict[str, float]]) -> dict[str, float]:
    return {
        "x": sum(point["x"] for point in points) / len(points),
        "y": sum(point["y"] for point in points) / len(points),
    }


def _polygon_signature(points: list[dict[str, float]]) -> str:
    if len(points) < 3:
        return ""
    normalized = sorted((round(point["x"], 4), round(point["y"], 4)) for point in points)
    return "|".join(f"{x:.4f},{y:.4f}" for x, y in normalized)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_matches(declared: object, actual: Path) -> bool:
    if not declared:
        return False
    declared_path = Path(str(declared))
    actual_path = Path(actual)
    if declared_path == actual_path:
        return True
    repo_root = Path(__file__).resolve().parents[2]
    declared_abs = declared_path if declared_path.is_absolute() else repo_root / declared_path
    actual_abs = actual_path if actual_path.is_absolute() else repo_root / actual_path
    return declared_abs.resolve(strict=False) == actual_abs.resolve(strict=False)


if __name__ == "__main__":
    raise SystemExit(main())
