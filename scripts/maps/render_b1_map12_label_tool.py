#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import io
import json
import shutil
import sys
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from PIL import Image

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.maps.bundle_validation import parse_map_yaml
from roboclaws.maps.spatial_contract import (
    ALIGNMENT_STATUS_CANDIDATE,
    GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
    POLYGON_GEOMETRY_SOURCES,
    POLYGON_ROLE_NAVIGATION_AREA,
    POLYGON_ROLES,
)

LABEL_TOOL_PACKET_SCHEMA = "b1_map12_label_tool_packet_v1"
LABEL_DRAFT_MANIFEST_SCHEMA = "b1_map12_label_draft_manifest_v1"
DEFAULT_MAP_BUNDLE = Path("assets/maps/b1-map12-room-semantics")
DEFAULT_OUTPUT_DIR = Path("output/b1-map12/label-tool")
TEMPLATE_PATH = Path(__file__).with_name("b1_map12_label_tool_template.html")


@dataclass(frozen=True)
class SourceMapTransform:
    width_px: int
    height_px: int
    resolution_m: float
    origin_x: float
    origin_y: float
    origin_yaw_rad: float = 0.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a standalone B1 / Map 12 source-map label editor."
    )
    parser.add_argument("--map-bundle", type=Path, default=DEFAULT_MAP_BUNDLE)
    parser.add_argument("--semantics", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve the generated label tool over HTTP after writing artifacts.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifacts = write_label_tool_artifacts(
        map_bundle=args.map_bundle,
        semantics_path=args.semantics,
        output_dir=args.output_dir,
    )
    payload = {
        "schema": LABEL_TOOL_PACKET_SCHEMA,
        "shape_count": artifacts["shape_count"],
        "output": str(artifacts["html_path"]),
        "packet": str(artifacts["packet_path"]),
    }
    if args.serve:
        payload["url"] = label_tool_url(args.host, args.port)
        print(json.dumps(payload, sort_keys=True), flush=True)
        serve_label_tool(args.output_dir, host=args.host, port=args.port)
        return 0
    print(json.dumps(payload, sort_keys=True))
    return 0


def write_label_tool_artifacts(
    *,
    map_bundle: Path,
    semantics_path: Path | None = None,
    output_dir: Path,
) -> dict[str, Any]:
    packet = build_label_tool_packet(
        map_bundle=map_bundle,
        semantics_path=semantics_path,
    )
    image_url = image_data_url(Path(packet["source_image"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    materialize_scene_evidence_artifacts(packet, output_dir=output_dir)
    packet_path = output_dir / "label_tool_packet.json"
    html_path = output_dir / "label_tool.html"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(
        render_label_tool_html(packet, image_data_url_value=image_url),
        encoding="utf-8",
    )
    return {
        "html_path": html_path,
        "packet_path": packet_path,
        "shape_count": len(packet["shapes"]),
    }


def label_tool_url(host: str, port: int) -> str:
    public_host = "127.0.0.1" if host in {"0.0.0.0", ""} else host
    return f"http://{public_host}:{port}/label_tool.html"


def serve_label_tool(output_dir: Path, *, host: str, port: int) -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=str(Path(output_dir).resolve()))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving B1 / Map 12 label tool at {label_tool_url(host, port)}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping label tool server.", flush=True)
    finally:
        server.server_close()


def build_label_tool_packet(
    *,
    map_bundle: Path,
    semantics_path: Path | None = None,
) -> dict[str, Any]:
    map_bundle = Path(map_bundle)
    semantics_path = semantics_path or map_bundle / "semantics.json"
    map_yaml_path = map_bundle / "map.yaml"
    map_yaml = parse_map_yaml(map_yaml_path.read_text(encoding="utf-8"))
    image_path = map_bundle / str(map_yaml.get("image") or "map.pgm")
    with Image.open(image_path) as image:
        width_px, height_px = image.size
    transform = SourceMapTransform(
        width_px=width_px,
        height_px=height_px,
        resolution_m=float(map_yaml.get("resolution") or 0.05),
        origin_x=float(_origin(map_yaml)[0]),
        origin_y=float(_origin(map_yaml)[1]),
        origin_yaw_rad=float(_origin(map_yaml)[2]),
    )
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    frame_id = source_map_frame_id(semantics)
    shapes = seed_shapes_from_semantics(semantics, transform=transform, frame_id=frame_id)
    semantic_layers = semantic_map_layers_from_semantics(
        semantics,
        transform=transform,
        frame_id=frame_id,
    )
    scene_evidence = scene_evidence_from_semantics(semantics)
    packet = {
        "schema": LABEL_TOOL_PACKET_SCHEMA,
        "draft_manifest_schema": LABEL_DRAFT_MANIFEST_SCHEMA,
        "map_bundle": str(map_bundle),
        "source_semantics": str(semantics_path),
        "source_image": str(image_path),
        "source_map_frame_id": frame_id,
        "source_map_frame_policy": "raw_source_map_frame_no_rectified_display_frame",
        "draft_policy": {
            "review_status": "draft",
            "export_alignment_status": ALIGNMENT_STATUS_CANDIDATE,
            "verified_status_allowed": False,
            "source_map_mutated": False,
        },
        "map": {
            "image_width_px": transform.width_px,
            "image_height_px": transform.height_px,
            "resolution_m": transform.resolution_m,
            "origin": {
                "x": transform.origin_x,
                "y": transform.origin_y,
                "yaw": transform.origin_yaw_rad,
            },
            "pixel_frame": "image_top_left_col_row",
            "world_frame": frame_id,
            "world_to_pixel": "px=(x-origin_x)/resolution; py=height-1-(y-origin_y)/resolution",
            "pixel_to_world": "x=origin_x+px*resolution; y=origin_y+(height-1-py)*resolution",
        },
        "shape_defaults": {
            "polygon_role": POLYGON_ROLE_NAVIGATION_AREA,
            "geometry_source": GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
            "alignment_status": ALIGNMENT_STATUS_CANDIDATE,
            "review_status": "draft",
        },
        "valid_polygon_roles": sorted(POLYGON_ROLES),
        "valid_geometry_sources": sorted(POLYGON_GEOMETRY_SOURCES),
        "shapes": shapes,
        "semantic_map_layers": semantic_layers,
        "scene_evidence": scene_evidence,
        "initial_draft_manifest": draft_manifest_from_shapes(
            shapes,
            source_packet={
                "source_map_frame_id": frame_id,
                "map_bundle": str(map_bundle),
                "source_semantics": str(semantics_path),
                "source_image": str(image_path),
            },
        ),
    }
    return packet


def materialize_scene_evidence_artifacts(packet: dict[str, Any], *, output_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    copied: dict[str, dict[str, Any]] = {}
    rooms = (packet.get("scene_evidence") or {}).get("rooms") or {}
    if not isinstance(rooms, dict):
        return
    for room in rooms.values():
        if not isinstance(room, dict):
            continue
        links = []
        for source in room.get("evidence_artifacts") or []:
            source_text = str(source)
            if source_text in copied:
                links.append(dict(copied[source_text]))
                continue
            link = {
                "source_path": source_text,
                "available": False,
                "href": "",
            }
            source_path = _repo_artifact_path(source_text, repo_root=repo_root)
            if source_path and source_path.is_file():
                evidence_dir = output_dir / "evidence"
                evidence_dir.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:12]
                destination = evidence_dir / f"{digest}_{source_path.name}"
                shutil.copy2(source_path, destination)
                link = {
                    **link,
                    "available": True,
                    "href": str(Path("evidence") / destination.name),
                }
            copied[source_text] = dict(link)
            links.append(link)
        room["evidence_artifact_links"] = links


def source_map_frame_id(semantics: dict[str, Any]) -> str:
    frame_ids = semantics.get("frame_ids") if isinstance(semantics.get("frame_ids"), dict) else {}
    if frame_ids.get("map"):
        return str(frame_ids["map"])
    contract = (
        semantics.get("spatial_contract")
        if isinstance(semantics.get("spatial_contract"), dict)
        else {}
    )
    source_frame = (
        contract.get("source_map_frame")
        if isinstance(contract.get("source_map_frame"), dict)
        else {}
    )
    return str(source_frame.get("frame_id") or "map")


def seed_shapes_from_semantics(
    semantics: dict[str, Any],
    *,
    transform: SourceMapTransform,
    frame_id: str,
) -> list[dict[str, Any]]:
    shapes: list[dict[str, Any]] = []
    for index, raw_room in enumerate(semantics.get("rooms") or [], start=1):
        if not isinstance(raw_room, dict):
            continue
        room = copy.deepcopy(raw_room)
        polygon = _polygon_points(room.get("polygon"))
        center = _center_from_room(room, polygon)
        shape_id = str(room.get("room_id") or f"label_{index:03d}")
        geometry: dict[str, Any]
        if len(polygon) >= 3:
            geometry = {
                "kind": "polygon",
                "polygon": polygon,
                "pixel_polygon": [
                    world_to_pixel(point["x"], point["y"], transform) for point in polygon
                ],
            }
        else:
            geometry = {
                "kind": "point",
                "center": center,
                "pixel_center": world_to_pixel(center["x"], center["y"], transform),
            }
        shapes.append(
            {
                "shape_id": shape_id,
                "label": str(room.get("label") or room.get("room_id") or shape_id),
                "category": str(room.get("category") or ""),
                "navigation_area_id": str(room.get("navigation_area_id") or ""),
                "asset_partition_id": str(room.get("asset_partition_id") or ""),
                "source_room_id": str(room.get("room_id") or ""),
                "source_map_frame_id": str(room.get("source_map_frame_id") or frame_id),
                "geometry": geometry,
                "map_center": center,
                "polygon_role": str(room.get("polygon_role") or POLYGON_ROLE_NAVIGATION_AREA),
                "geometry_source": str(
                    room.get("geometry_source") or GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE
                ),
                "source_alignment_status": str(room.get("alignment_status") or ""),
                "alignment_status": ALIGNMENT_STATUS_CANDIDATE,
                "review_status": "draft",
                "polygon_usage": {
                    "navigation": True,
                    "semantic_labeling": ALIGNMENT_STATUS_CANDIDATE,
                    "review": True,
                },
            }
        )
    return shapes


def semantic_map_layers_from_semantics(
    semantics: dict[str, Any],
    *,
    transform: SourceMapTransform,
    frame_id: str,
) -> dict[str, Any]:
    room_centers = _room_centers_by_id(semantics)
    waypoint_centers: dict[str, dict[str, float]] = {}
    fixture_centers: dict[str, dict[str, float]] = {}
    fixtures = []
    for raw_fixture in semantics.get("fixtures") or []:
        if not isinstance(raw_fixture, dict):
            continue
        pose = raw_fixture.get("pose") if isinstance(raw_fixture.get("pose"), dict) else {}
        if str(pose.get("frame_id") or frame_id) != frame_id:
            continue
        try:
            center = {"x": float(pose["x"]), "y": float(pose["y"])}
        except (KeyError, TypeError, ValueError):
            continue
        fixture_id = str(raw_fixture.get("fixture_id") or "")
        if fixture_id:
            fixture_centers[fixture_id] = center
        fixtures.append(
            {
                "fixture_id": fixture_id,
                "label": str(raw_fixture.get("label") or raw_fixture.get("name") or fixture_id),
                "name": str(raw_fixture.get("name") or ""),
                "category": str(raw_fixture.get("category") or ""),
                "room_id": str(raw_fixture.get("room_id") or ""),
                "pose": {
                    "frame_id": frame_id,
                    "x": center["x"],
                    "y": center["y"],
                    "yaw": float(pose.get("yaw") or 0.0),
                },
                "pixel_center": world_to_pixel(center["x"], center["y"], transform),
                "footprint": copy.deepcopy(raw_fixture.get("footprint") or {}),
                "affordances": list(raw_fixture.get("affordances") or []),
                "position_detail": str(raw_fixture.get("position_detail") or ""),
                "coordinate_status": "source_map_frame_coordinate",
            }
        )

    waypoints = []
    for raw_waypoint in semantics.get("inspection_waypoints") or []:
        if not isinstance(raw_waypoint, dict):
            continue
        if str(raw_waypoint.get("frame_id") or frame_id) != frame_id:
            continue
        try:
            center = {"x": float(raw_waypoint["x"]), "y": float(raw_waypoint["y"])}
        except (KeyError, TypeError, ValueError):
            continue
        waypoint_id = str(raw_waypoint.get("waypoint_id") or "")
        if waypoint_id:
            waypoint_centers[waypoint_id] = center
        waypoints.append(
            {
                "waypoint_id": waypoint_id,
                "label": str(raw_waypoint.get("label") or waypoint_id),
                "room_id": str(raw_waypoint.get("room_id") or ""),
                "navigation_area_id": str(raw_waypoint.get("navigation_area_id") or ""),
                "fixture_id": str(raw_waypoint.get("fixture_id") or ""),
                "purpose": str(raw_waypoint.get("purpose") or ""),
                "reachability_status": str(raw_waypoint.get("reachability_status") or ""),
                "pose": {
                    "frame_id": frame_id,
                    "x": center["x"],
                    "y": center["y"],
                    "yaw": float(raw_waypoint.get("yaw") or 0.0),
                },
                "pixel_center": world_to_pixel(center["x"], center["y"], transform),
                "coordinate_status": "source_map_frame_coordinate",
            }
        )

    driveable_ways = []
    for raw_way in semantics.get("driveable_ways") or []:
        if not isinstance(raw_way, dict):
            continue
        from_id = str(raw_way.get("from_room_id") or raw_way.get("from_waypoint_id") or "")
        to_id = str(raw_way.get("to_room_id") or raw_way.get("to_waypoint_id") or "")
        start = _resolve_map_anchor(
            from_id,
            room_centers=room_centers,
            waypoint_centers=waypoint_centers,
            fixture_centers=fixture_centers,
        )
        end = _resolve_map_anchor(
            to_id,
            room_centers=room_centers,
            waypoint_centers=waypoint_centers,
            fixture_centers=fixture_centers,
        )
        item = {
            "from_id": from_id,
            "to_id": to_id,
            "raw": copy.deepcopy(raw_way),
            "coordinate_status": "resolved_from_source_map_anchors",
        }
        if start and end:
            item.update(
                {
                    "from_kind": start["kind"],
                    "to_kind": end["kind"],
                    "from_center": start["center"],
                    "to_center": end["center"],
                    "from_pixel": world_to_pixel(
                        start["center"]["x"],
                        start["center"]["y"],
                        transform,
                    ),
                    "to_pixel": world_to_pixel(end["center"]["x"], end["center"]["y"], transform),
                }
            )
        driveable_ways.append(item)

    return {
        "coordinate_policy": "map_native_layers_use_source_map_frame_coordinates_only",
        "fixtures": fixtures,
        "inspection_waypoints": waypoints,
        "driveable_ways": driveable_ways,
    }


def scene_evidence_from_semantics(semantics: dict[str, Any]) -> dict[str, Any]:
    rooms: dict[str, dict[str, Any]] = {}
    for raw_room in semantics.get("rooms") or []:
        if not isinstance(raw_room, dict):
            continue
        room_id = str(raw_room.get("room_id") or "")
        if not room_id:
            continue
        evidence = raw_room.get("evidence") if isinstance(raw_room.get("evidence"), dict) else {}
        correspondence = (
            raw_room.get("scene_map_correspondence")
            if isinstance(raw_room.get("scene_map_correspondence"), dict)
            else {}
        )
        object_name_counts = evidence.get("object_name_counts")
        object_name_counts = object_name_counts if isinstance(object_name_counts, dict) else {}
        rooms[room_id] = {
            "room_id": room_id,
            "room_label": str(raw_room.get("room_label") or raw_room.get("label") or room_id),
            "navigation_area_id": str(raw_room.get("navigation_area_id") or ""),
            "candidate_scene_partition_id": str(
                correspondence.get("asset_partition_id")
                or raw_room.get("asset_partition_id")
                or evidence.get("partition_name")
                or ""
            ),
            "partition_name": str(evidence.get("partition_name") or ""),
            "alignment_status": str(
                correspondence.get("alignment_status")
                or raw_room.get("alignment_status")
                or ALIGNMENT_STATUS_CANDIDATE
            ),
            "transform_source": str(correspondence.get("transform_source") or ""),
            "map_polygon_provided": bool(correspondence.get("map_polygon_provided")),
            "weak_evidence": bool(evidence.get("weak_evidence")),
            "matched_terms": [str(item) for item in evidence.get("matched_terms") or []],
            "conflicting_evidence": [
                str(item) for item in evidence.get("conflicting_evidence") or []
            ],
            "object_name_counts": {
                str(name): int(count)
                for name, count in sorted(
                    object_name_counts.items(),
                    key=lambda item: (-int(item[1]), str(item[0])),
                )
            },
            "evidence_artifacts": [
                str(item)
                for item in (
                    correspondence.get("evidence_artifacts") or evidence.get("artifacts") or []
                )
            ],
            "semantic_source": str(raw_room.get("semantic_source") or ""),
            "coordinate_status": "scene_evidence_has_no_map_coordinates",
            "identity_status": "candidate_name_match_not_verified_identity",
        }
    return {
        "schema": "b1_map12_scene_evidence_packet_v1",
        "coordinate_policy": "do_not_project_scene_or_gaussian_objects_without_verified_transform",
        "rooms": rooms,
    }


def draft_manifest_from_shapes(
    shapes: list[dict[str, Any]],
    *,
    source_packet: dict[str, Any],
) -> dict[str, Any]:
    labels = [draft_label_from_shape(shape) for shape in shapes]
    return {
        "schema": LABEL_DRAFT_MANIFEST_SCHEMA,
        "source_map_frame_id": str(source_packet.get("source_map_frame_id") or "map"),
        "map_bundle": str(source_packet.get("map_bundle") or ""),
        "source_semantics": str(source_packet.get("source_semantics") or ""),
        "source_image": str(source_packet.get("source_image") or ""),
        "review_status": "draft",
        "alignment_status": ALIGNMENT_STATUS_CANDIDATE,
        "source_map_mutated": False,
        "verified_status_allowed": False,
        "labels": labels,
    }


def draft_label_from_shape(shape: dict[str, Any]) -> dict[str, Any]:
    geometry = _draft_geometry(shape.get("geometry"))
    center = geometry.get("center") or _geometry_center(geometry)
    return {
        "label_id": str(shape.get("shape_id") or ""),
        "label": str(shape.get("label") or ""),
        "category": str(shape.get("category") or ""),
        "navigation_area_id": str(shape.get("navigation_area_id") or ""),
        "asset_partition_id": str(shape.get("asset_partition_id") or ""),
        "source_room_id": str(shape.get("source_room_id") or ""),
        "source_map_frame_id": str(shape.get("source_map_frame_id") or "map"),
        "geometry": geometry,
        "map_center": center,
        "polygon_role": _valid_or_default(
            str(shape.get("polygon_role") or ""),
            POLYGON_ROLES,
            POLYGON_ROLE_NAVIGATION_AREA,
        ),
        "geometry_source": _valid_or_default(
            str(shape.get("geometry_source") or ""),
            POLYGON_GEOMETRY_SOURCES,
            GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
        ),
        "alignment_status": ALIGNMENT_STATUS_CANDIDATE,
        "review_status": "draft",
        "polygon_usage": {
            "navigation": True,
            "semantic_labeling": ALIGNMENT_STATUS_CANDIDATE,
            "review": True,
        },
    }


def validate_label_draft_manifest(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != LABEL_DRAFT_MANIFEST_SCHEMA:
        errors.append(f"schema must be {LABEL_DRAFT_MANIFEST_SCHEMA}")
    if payload.get("source_map_mutated") is not False:
        errors.append("label drafts must not mutate the source map")
    if payload.get("verified_status_allowed") is not False:
        errors.append("label drafts must not allow verified status")
    for index, raw_label in enumerate(payload.get("labels") or [], start=1):
        label = raw_label if isinstance(raw_label, dict) else {}
        label_id = str(label.get("label_id") or f"labels[{index}]")
        if label.get("alignment_status") != ALIGNMENT_STATUS_CANDIDATE:
            errors.append(f"label {label_id} alignment_status must remain candidate")
        if label.get("review_status") != "draft":
            errors.append(f"label {label_id} review_status must remain draft")
        geometry = label.get("geometry") if isinstance(label.get("geometry"), dict) else {}
        kind = str(geometry.get("kind") or "")
        if kind == "polygon" and len(geometry.get("polygon") or []) < 3:
            errors.append(f"label {label_id} polygon needs at least three points")
        elif kind == "circle":
            if not isinstance(geometry.get("center"), dict):
                errors.append(f"label {label_id} circle needs a center")
            if float(geometry.get("radius_m") or 0.0) <= 0.0:
                errors.append(f"label {label_id} circle radius_m must be positive")
        elif kind == "point":
            if not isinstance(geometry.get("center"), dict):
                errors.append(f"label {label_id} point needs a center")
        elif kind not in {"polygon", "circle", "point"}:
            errors.append(f"label {label_id} has unsupported geometry kind")
    return errors


def world_to_pixel(x: float, y: float, transform: SourceMapTransform) -> dict[str, float]:
    return {
        "x": (float(x) - transform.origin_x) / transform.resolution_m,
        "y": transform.height_px
        - 1.0
        - ((float(y) - transform.origin_y) / transform.resolution_m),
    }


def pixel_to_world(px: float, py: float, transform: SourceMapTransform) -> dict[str, float]:
    return {
        "x": transform.origin_x + float(px) * transform.resolution_m,
        "y": transform.origin_y + (transform.height_px - 1.0 - float(py)) * transform.resolution_m,
    }


def image_data_url(path: Path) -> str:
    with Image.open(path) as image:
        png = image.convert("RGB")
        buffer = io.BytesIO()
        png.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_label_tool_html(packet: dict[str, Any], *, image_data_url_value: str) -> str:
    packet_json = json.dumps(packet, sort_keys=True)
    image_json = json.dumps(image_data_url_value)
    return label_tool_template().replace("__PACKET_JSON__", packet_json).replace(
        "__IMAGE_DATA_URL__",
        image_json,
    )


def _origin(map_yaml: dict[str, Any]) -> list[float]:
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else []
    values = [float(item) for item in origin[:3]]
    while len(values) < 3:
        values.append(0.0)
    return values


def _polygon_points(value: Any) -> list[dict[str, float]]:
    points = []
    for raw_point in value or []:
        if not isinstance(raw_point, dict):
            continue
        try:
            points.append({"x": float(raw_point["x"]), "y": float(raw_point["y"])})
        except (KeyError, TypeError, ValueError):
            continue
    return points


def _center_from_room(room: dict[str, Any], polygon: list[dict[str, float]]) -> dict[str, float]:
    raw_center = room.get("map_center") if isinstance(room.get("map_center"), dict) else {}
    if "x" in raw_center and "y" in raw_center:
        return {"x": float(raw_center["x"]), "y": float(raw_center["y"])}
    if polygon:
        return {
            "x": sum(point["x"] for point in polygon) / len(polygon),
            "y": sum(point["y"] for point in polygon) / len(polygon),
        }
    return {"x": 0.0, "y": 0.0}


def _room_centers_by_id(semantics: dict[str, Any]) -> dict[str, dict[str, float]]:
    centers: dict[str, dict[str, float]] = {}
    for raw_room in semantics.get("rooms") or []:
        if not isinstance(raw_room, dict):
            continue
        room_id = str(raw_room.get("room_id") or "")
        if not room_id:
            continue
        centers[room_id] = _center_from_room(raw_room, _polygon_points(raw_room.get("polygon")))
    return centers


def _resolve_map_anchor(
    anchor_id: str,
    *,
    room_centers: dict[str, dict[str, float]],
    waypoint_centers: dict[str, dict[str, float]],
    fixture_centers: dict[str, dict[str, float]],
) -> dict[str, Any] | None:
    if anchor_id in room_centers:
        return {"kind": "room", "center": room_centers[anchor_id]}
    if anchor_id in waypoint_centers:
        return {"kind": "waypoint", "center": waypoint_centers[anchor_id]}
    if anchor_id in fixture_centers:
        return {"kind": "fixture", "center": fixture_centers[anchor_id]}
    return None


def _geometry_center(geometry: dict[str, Any]) -> dict[str, float]:
    if isinstance(geometry.get("center"), dict):
        center = geometry["center"]
        return {"x": float(center.get("x") or 0.0), "y": float(center.get("y") or 0.0)}
    polygon = _polygon_points(geometry.get("polygon"))
    if polygon:
        return {
            "x": sum(point["x"] for point in polygon) / len(polygon),
            "y": sum(point["y"] for point in polygon) / len(polygon),
        }
    return {"x": 0.0, "y": 0.0}


def _draft_geometry(value: Any) -> dict[str, Any]:
    geometry = value if isinstance(value, dict) else {}
    kind = str(geometry.get("kind") or "")
    if kind == "circle":
        center = _geometry_center(geometry)
        return {
            "kind": "circle",
            "center": center,
            "radius_m": max(float(geometry.get("radius_m") or 0.0), 0.0),
        }
    if kind == "point":
        return {"kind": "point", "center": _geometry_center(geometry)}
    polygon = _polygon_points(geometry.get("polygon"))
    return {"kind": "polygon", "polygon": polygon}


def _valid_or_default(value: str, valid_values: frozenset[str], default: str) -> str:
    return value if value in valid_values else default


def _repo_artifact_path(source: str, *, repo_root: Path) -> Path | None:
    raw_path = Path(source)
    candidate = raw_path if raw_path.is_absolute() else repo_root / raw_path
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return resolved


def label_tool_template_path() -> Path:
    return TEMPLATE_PATH


def label_tool_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")



if __name__ == "__main__":
    raise SystemExit(main())
