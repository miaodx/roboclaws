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

from PIL import Image, ImageDraw

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.maps.bundle import validate_nav2_map_bundle
from roboclaws.maps.spatial_contract import (
    ALIGNMENT_STATUS_CANDIDATE,
    GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
    POLYGON_ROLE_NAVIGATION_AREA,
    source_frame_spatial_contract,
)

B1_MAP12_ALIGNMENT_REVIEW_SCHEMA = "b1_map12_alignment_review_v1"
B1_MAP12_RUNTIME_PROVENANCE_SCHEMA = "b1_map12_runtime_bundle_provenance_v1"
ACCEPTED_REVIEW_STATUS = "accepted"
RUNTIME_LABEL_STATUSES = frozenset({ACCEPTED_REVIEW_STATUS})
REVIEW_ONLY_STATUSES = frozenset({"draft", "proposed", "blocked_shared_area"})
EXPLICIT_SHARED_AREA_POLICIES = frozenset({"composite_area"})
DEFAULT_MAP_BUNDLE = Path("assets/maps/agibot-robot-map-12")
DEFAULT_SCENE_ROOT = Path("data/robot-data-lab/scene-engine/data/2rd_floor_seperated")
DEFAULT_REVIEW_MANIFEST = Path("assets/maps/b1-map12-alignment-review.json")
DEFAULT_OUTPUT_DIR = Path("output/b1-map12/digital-twin-runtime")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a generated B1 / Map 12 digital-twin runtime map bundle."
    )
    parser.add_argument("--map-bundle", type=Path, default=DEFAULT_MAP_BUNDLE)
    parser.add_argument("--scene-root", type=Path, default=DEFAULT_SCENE_ROOT)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_MANIFEST)
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
    output_dir: Path,
    include_draft_labels: bool = False,
) -> dict[str, Any]:
    map_bundle = Path(map_bundle)
    scene_root = Path(scene_root)
    review_manifest_path = Path(review_manifest_path)
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
    validation = validate_nav2_map_bundle(map_bundle)
    validation.raise_for_errors()
    if not scene_root.is_dir():
        raise ValueError(f"scene root does not exist: {scene_root}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    _copy_raw_map_bundle(map_bundle, output_dir)

    raw_semantics_path = map_bundle / "semantics.json"
    semantics = json.loads(raw_semantics_path.read_text(encoding="utf-8"))
    frame_id = _source_map_frame_id(semantics)
    runtime_labels = runtime_labels_from_review(
        review,
        frame_id=frame_id,
        include_draft_labels=include_draft_labels,
    )
    review_summary = review_validation_summary(review, include_draft_labels=include_draft_labels)
    semantics["review_labels"] = runtime_labels
    semantics["room_category_hints"] = _room_category_hints_from_review(runtime_labels)
    semantics["spatial_contract"] = source_frame_spatial_contract(
        frame_id=frame_id,
        alignment_status=ALIGNMENT_STATUS_CANDIDATE,
    )
    semantics["display_frame"] = None
    semantics["provenance"] = {
        **(semantics.get("provenance") if isinstance(semantics.get("provenance"), dict) else {}),
        "generated_from_review_manifest": True,
        "b1_alignment_review_schema": review.get("schema"),
        "b1_alignment_review_source": str(review_manifest_path),
        "b1_runtime_compiler": Path(__file__).as_posix(),
        "contains_private_scoring_truth": False,
        "contains_runtime_observations": False,
    }
    (output_dir / "semantics.json").write_text(
        json.dumps(semantics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_review_topdown(output_dir, runtime_labels=runtime_labels)
    provenance = runtime_provenance(
        map_bundle=map_bundle,
        scene_root=scene_root,
        review_manifest_path=review_manifest_path,
        output_dir=output_dir,
        review=review,
        runtime_labels=runtime_labels,
        review_summary=review_summary,
        include_draft_labels=include_draft_labels,
    )
    (output_dir / "b1_runtime_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    runtime_validation = validate_nav2_map_bundle(output_dir)
    runtime_validation.raise_for_errors()
    return {
        "schema": B1_MAP12_RUNTIME_PROVENANCE_SCHEMA,
        "status": "compiled",
        "output_dir": str(output_dir),
        "runtime_label_count": len(runtime_labels),
        "excluded_label_count": review_summary["excluded_label_count"],
        "validation": runtime_validation.as_dict(),
        "provenance": str(output_dir / "b1_runtime_provenance.json"),
    }


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


def runtime_provenance(
    *,
    map_bundle: Path,
    scene_root: Path,
    review_manifest_path: Path,
    output_dir: Path,
    review: dict[str, Any],
    runtime_labels: list[dict[str, Any]],
    review_summary: dict[str, Any],
    include_draft_labels: bool,
) -> dict[str, Any]:
    source_files = [
        map_bundle / "map.yaml",
        map_bundle / "map.pgm",
        map_bundle / "semantics.json",
        map_bundle / "profiles" / "rby1m.yaml",
        map_bundle / "costmaps" / "rby1m.costmap_params.yaml",
        review_manifest_path,
    ]
    return {
        "schema": B1_MAP12_RUNTIME_PROVENANCE_SCHEMA,
        "generated_from_review_manifest": True,
        "generated_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "compiler": Path(__file__).as_posix(),
        "source_assets": {
            "map_bundle": str(map_bundle),
            "scene_root": str(scene_root),
            "review_manifest": str(review_manifest_path),
            "review_schema": str(review.get("schema") or ""),
        },
        "output_dir": str(output_dir),
        "source_file_hashes": {
            str(path): _file_sha256(path) for path in source_files if path.is_file()
        },
        "include_draft_labels": include_draft_labels,
        "runtime_label_count": len(runtime_labels),
        "review_validation": review_summary,
        "public_contract_note": (
            "This generated bundle preserves raw Map12 navigation layers. Human review "
            "labels are compiled as a semantic label layer and do not retarget waypoints "
            "or rebuild driveable ways."
        ),
    }


def write_review_topdown(output_dir: Path, *, runtime_labels: list[dict[str, Any]]) -> Path:
    preview_path = output_dir / "preview.png"
    output_path = output_dir / "review_labels_topdown.png"
    source = Image.open(preview_path).convert("RGB")
    image = source.copy()
    draw = ImageDraw.Draw(image, "RGBA")
    if runtime_labels:
        width, height = image.size
        all_points = [point for label in runtime_labels for point in label.get("polygon") or []]
        min_x = min(float(point["x"]) for point in all_points)
        max_x = max(float(point["x"]) for point in all_points)
        min_y = min(float(point["y"]) for point in all_points)
        max_y = max(float(point["y"]) for point in all_points)
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        scale = min((width * 0.78) / span_x, (height * 0.78) / span_y)
        offset_x = (width - span_x * scale) / 2.0
        offset_y = (height - span_y * scale) / 2.0

        def project(point: dict[str, float]) -> tuple[float, float]:
            return (
                offset_x + (float(point["x"]) - min_x) * scale,
                height - (offset_y + (float(point["y"]) - min_y) * scale),
            )

        palette = [
            (51, 102, 204, 90),
            (220, 57, 18, 90),
            (16, 150, 24, 90),
            (153, 0, 153, 90),
            (255, 153, 0, 90),
        ]
        for index, label in enumerate(runtime_labels):
            polygon = [project(point) for point in label.get("polygon") or []]
            if len(polygon) < 3:
                continue
            color = palette[index % len(palette)]
            draw.polygon(polygon, fill=color, outline=color[:3] + (210,))
            center = project(label["map_center"])
            draw.text(
                center,
                str(label.get("room_label") or label.get("label_id") or ""),
                fill=(20, 24, 28, 255),
            )
    image.save(output_path)
    return output_path


def _copy_raw_map_bundle(source: Path, output_dir: Path) -> None:
    for relative in (
        Path("map.yaml"),
        Path("map.pgm"),
        Path("preview.png"),
        Path("semantics.json"),
        Path("profiles"),
        Path("costmaps"),
    ):
        src = source / relative
        dst = output_dir / relative
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


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
