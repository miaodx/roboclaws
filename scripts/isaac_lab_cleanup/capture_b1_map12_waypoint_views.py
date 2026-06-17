#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]

from roboclaws.household.b1_nurec_scene import prepare_b1_nurec_scene_usd  # noqa: E402
from roboclaws.household.camera_control import (  # noqa: E402
    canonical_scene_camera_control_request,
    write_camera_control_request,
)

DEFAULT_SEMANTICS = Path("output/operator-console-scene-previews/b1-map12-runtime-map-bundle")
DEFAULT_SEMANTICS = DEFAULT_SEMANTICS / "semantics.json"
DEFAULT_REVIEW_MANIFEST = Path("assets/maps/b1-map12-alignment-review.json")
DEFAULT_OLD_SCENE = Path("data/robot-data-lab/scene-engine/data/B1_floor2_slow/usda/F2_all")
DEFAULT_OLD_SCENE = DEFAULT_OLD_SCENE / "F2_all.usda"
DEFAULT_NEW_SCENE = Path("data/robot-data-lab/scene-engine/data/2rd_floor_seperated/storey_1")
DEFAULT_NEW_SCENE = DEFAULT_NEW_SCENE / "scene_gs.usda"
DEFAULT_OUTPUT_DIR = Path("output/gaussian-map-comparison/b1-map12-waypoint-capture")
DEFAULT_SCENE_XY_BOUNDS = (
    -22.7833251953125,
    -13.112351417541504,
    8.074257850646973,
    7.298900469562338,
)
CAPTURE_MANIFEST_SCHEMA = "b1_map12_waypoint_capture_manifest_v1"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.capture_one_scene:
        return _capture_one_scene_cli(args)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_bounds = _parse_bounds(args.scene_bounds)
    request, manifest = build_waypoint_capture_request(
        semantics_path=args.semantics,
        review_manifest_path=args.review_manifest,
        width=args.width,
        height=args.height,
        scene_xy_bounds=scene_bounds,
        include_extra_points=args.extra_points,
    )
    request_path = write_camera_control_request(output_dir / "camera_request.json", request)
    manifest["camera_request"] = str(request_path)
    manifest["scenes"] = _scene_manifest(
        args.old_scene,
        args.new_scene,
        prepare_new=bool(args.capture),
    )
    manifest_path = output_dir / "capture_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result: dict[str, Any] = {
        "schema": CAPTURE_MANIFEST_SCHEMA,
        "status": "request_written",
        "output_dir": str(output_dir),
        "camera_request": str(request_path),
        "manifest": str(manifest_path),
        "view_count": len(request["views"]),
    }
    if args.capture:
        capture = capture_scene_pair(
            old_scene=args.old_scene,
            new_scene=args.new_scene,
            request=request,
            request_path=request_path,
            output_dir=output_dir,
            width=args.width,
            height=args.height,
            allow_blank=args.allow_blank,
        )
        contact_sheet = write_contact_sheet(
            request=request,
            old_images=capture["old"]["capture"].get("images", {}),
            new_images=capture["new"]["capture"].get("images", {}),
            output_path=output_dir / "old_vs_new_waypoint_contact_sheet.png",
        )
        result.update(
            {
                "status": "captured",
                "old_result": capture["old"]["result_path"],
                "new_result": capture["new"]["result_path"],
                "contact_sheet": str(contact_sheet),
            }
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic B1/Map12 camera request from runtime waypoints, "
            "then optionally capture old/new Gaussian scenes with the same views."
        )
    )
    parser.add_argument("--semantics", type=Path, default=DEFAULT_SEMANTICS)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_MANIFEST)
    parser.add_argument("--old-scene", type=Path, default=DEFAULT_OLD_SCENE)
    parser.add_argument("--new-scene", type=Path, default=DEFAULT_NEW_SCENE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument(
        "--scene-bounds",
        default=",".join(str(value) for value in DEFAULT_SCENE_XY_BOUNDS),
        help="Approx scene XY bounds as min_x,min_y,max_x,max_y.",
    )
    parser.add_argument("--extra-points", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--allow-blank", action="store_true")
    parser.add_argument("--capture-one-scene", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--scene-usd", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--camera-request", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--views-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--result", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def build_waypoint_capture_request(
    *,
    semantics_path: Path,
    review_manifest_path: Path,
    width: int,
    height: int,
    scene_xy_bounds: tuple[float, float, float, float] = DEFAULT_SCENE_XY_BOUNDS,
    include_extra_points: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    semantics = _load_json(semantics_path)
    review = _load_json(review_manifest_path) if review_manifest_path.is_file() else {}
    points = _waypoint_points(semantics)
    extra_points = _extra_points(semantics, review) if include_extra_points else []
    all_points = [*points, *extra_points]
    map_bounds = _map_bounds(semantics, review, all_points)
    transform = _bbox_map_to_scene_transform(map_bounds, scene_xy_bounds)
    views = [_camera_view(point, transform) for point in all_points]
    request = canonical_scene_camera_control_request(views, width=width, height=height)
    request["point_capture"] = {
        "schema": CAPTURE_MANIFEST_SCHEMA,
        "source_semantics": str(semantics_path),
        "source_review_manifest": str(review_manifest_path),
        "point_count": len(all_points),
        "waypoint_count": len(points),
        "extra_point_count": len(extra_points),
        "map_to_scene_transform": transform,
        "transform_status": "approx_bbox_fit_unverified",
    }
    manifest = {
        "schema": CAPTURE_MANIFEST_SCHEMA,
        "source_semantics": str(semantics_path),
        "source_review_manifest": str(review_manifest_path),
        "point_count": len(all_points),
        "waypoint_count": len(points),
        "extra_point_count": len(extra_points),
        "points": all_points,
        "map_bounds": _bounds_payload(map_bounds),
        "scene_xy_bounds": _bounds_payload(scene_xy_bounds),
        "map_to_scene_transform": transform,
        "transform_status": "approx_bbox_fit_unverified",
        "transform_note": (
            "Map12 waypoints are in the source map frame. Until reviewed map-scene "
            "correspondence anchors exist, this script uses a deterministic bbox fit "
            "only for visual comparison captures, not navigation truth."
        ),
    }
    return request, manifest


def capture_scene_pair(
    *,
    old_scene: Path,
    new_scene: Path,
    request: dict[str, Any],
    request_path: Path,
    output_dir: Path,
    width: int,
    height: int,
    allow_blank: bool = False,
) -> dict[str, Any]:
    return {
        "old": _capture_scene(
            scene_usd=old_scene,
            request=request,
            request_path=request_path,
            output_dir=output_dir / "old_b1_floor2_slow_views",
            result_path=output_dir / "old_b1_floor2_slow_result.json",
            width=width,
            height=height,
            allow_blank=allow_blank,
        ),
        "new": _capture_scene(
            scene_usd=prepare_b1_nurec_scene_usd(new_scene) or new_scene,
            request=request,
            request_path=request_path,
            output_dir=output_dir / "new_2rd_floor_seperated_views",
            result_path=output_dir / "new_2rd_floor_seperated_result.json",
            width=width,
            height=height,
            allow_blank=allow_blank,
        ),
    }


def _capture_scene(
    *,
    scene_usd: Path,
    request: dict[str, Any],
    request_path: Path,
    output_dir: Path,
    result_path: Path,
    width: int,
    height: int,
    allow_blank: bool,
) -> dict[str, Any]:
    del request
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--capture-one-scene",
        "--scene-usd",
        str(scene_usd),
        "--camera-request",
        str(request_path),
        "--views-dir",
        str(output_dir),
        "--result",
        str(result_path),
        "--width",
        str(width),
        "--height",
        str(height),
    ]
    if allow_blank:
        command.append("--allow-blank")
    env = os.environ.copy()
    env.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")
    env["ROBOCLAWS_HARD_EXIT_AFTER_ISAAC_CAPTURE"] = "1"
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    return {"result_path": str(result_path), **payload}


def _capture_one_scene_cli(args: argparse.Namespace) -> int:
    if args.scene_usd is None or args.camera_request is None or args.views_dir is None:
        raise ValueError("--capture-one-scene requires --scene-usd, --camera-request, --views-dir")
    if args.result is None:
        raise ValueError("--capture-one-scene requires --result")
    request = _load_json(args.camera_request)
    _capture_scene_in_process(
        scene_usd=args.scene_usd,
        request=request,
        output_dir=args.views_dir,
        result_path=args.result,
        width=args.width,
        height=args.height,
        allow_blank=bool(args.allow_blank),
    )
    return 0


def _capture_scene_in_process(
    *,
    scene_usd: Path,
    request: dict[str, Any],
    output_dir: Path,
    result_path: Path,
    width: int,
    height: int,
    allow_blank: bool,
) -> None:
    from scripts.isaac_lab_cleanup import isaac_lab_backend_worker

    if allow_blank:
        isaac_lab_backend_worker._image_has_variance = lambda array, *, np: array is not None
    result_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        capture = isaac_lab_backend_worker.capture_scene_camera_views(
            scene_usd=scene_usd,
            camera_request=request,
            output_dir=output_dir,
            width=width,
            height=height,
            semantic_pose_state={},
        )
        payload = {"ok": True, "scene_usd": str(scene_usd), "capture": capture}
    except Exception as exc:
        payload = {
            "ok": False,
            "scene_usd": str(scene_usd),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        raise
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_contact_sheet(
    *,
    request: dict[str, Any],
    old_images: dict[str, str],
    new_images: dict[str, str],
    output_path: Path,
) -> Path:
    views = request.get("views") or []
    thumb_w, thumb_h = 360, 202
    pad, label_h, header_h = 16, 36, 70
    sheet_w = pad * 3 + thumb_w * 2
    sheet_h = header_h + len(views) * (thumb_h + label_h + pad) + pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (242, 244, 247))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((pad, 14), "B1 / Map12 waypoint capture comparison", fill=(20, 24, 32), font=font)
    draw.text(
        (pad, 40),
        "Same deterministic waypoint/extra-point camera request for old and new maps.",
        fill=(70, 76, 88),
        font=font,
    )
    columns = [
        (pad, "OLD: B1_floor2_slow", old_images),
        (pad * 2 + thumb_w, "NEW: 2rd", new_images),
    ]
    for x, title, _ in columns:
        draw.rectangle((x, header_h - 22, x + thumb_w, header_h - 2), fill=(25, 31, 43))
        draw.text((x + 8, header_h - 18), title, fill=(255, 255, 255), font=font)
    for row, view in enumerate(views):
        y = header_h + row * (thumb_h + label_h + pad)
        view_id = str(view.get("view_id") or f"view_{row + 1:02d}")
        draw.text((pad, y + 9), view_id, fill=(31, 41, 55), font=font)
        for x, _, images in columns:
            image_path = images.get(view_id)
            if image_path and Path(image_path).is_file():
                image = Image.open(image_path).convert("RGB")
                image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                frame = Image.new("RGB", (thumb_w, thumb_h), (229, 231, 235))
                frame.paste(image, ((thumb_w - image.width) // 2, (thumb_h - image.height) // 2))
            else:
                frame = Image.new("RGB", (thumb_w, thumb_h), (229, 231, 235))
                ImageDraw.Draw(frame).text((12, 12), "missing", fill=(120, 30, 30), font=font)
            sheet.paste(frame, (x, y + label_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path


def _waypoint_points(semantics: dict[str, Any]) -> list[dict[str, Any]]:
    points = []
    for raw in semantics.get("inspection_waypoints") or []:
        if not isinstance(raw, dict) or "x" not in raw or "y" not in raw:
            continue
        waypoint_id = _slug(str(raw.get("waypoint_id") or f"waypoint_{len(points) + 1:02d}"))
        points.append(
            {
                "point_id": f"wp_{waypoint_id}",
                "source": "inspection_waypoint",
                "source_id": str(raw.get("waypoint_id") or ""),
                "label": str(raw.get("label") or raw.get("waypoint_id") or ""),
                "purpose": str(raw.get("purpose") or ""),
                "frame_id": str(raw.get("frame_id") or "map"),
                "x": float(raw["x"]),
                "y": float(raw["y"]),
                "yaw": float(raw.get("yaw") or 0.0),
            }
        )
    return points


def _extra_points(semantics: dict[str, Any], review: dict[str, Any]) -> list[dict[str, Any]]:
    existing = {
        (round(float(point["x"]), 3), round(float(point["y"]), 3))
        for point in _waypoint_points(semantics)
    }
    extras: list[dict[str, Any]] = []
    for raw in review.get("labels") or []:
        if not isinstance(raw, dict):
            continue
        center = _label_center(raw)
        if center is None:
            continue
        key = (round(center[0], 3), round(center[1], 3))
        if key in existing:
            continue
        existing.add(key)
        label_id = _slug(str(raw.get("label_id") or f"review_label_{len(extras) + 1:02d}"))
        extras.append(
            {
                "point_id": f"extra_review_{label_id}_center",
                "source": "review_label_center",
                "source_id": str(raw.get("label_id") or ""),
                "label": str(raw.get("room_label") or raw.get("label_id") or ""),
                "purpose": str(raw.get("review_status") or "review_label_center"),
                "frame_id": "map",
                "x": center[0],
                "y": center[1],
                "yaw": 0.0,
            }
        )
    bounds = _map_bounds(semantics, review, _waypoint_points(semantics))
    min_x, min_y, max_x, max_y = bounds
    coverage = [
        ("center", (min_x + max_x) / 2.0, (min_y + max_y) / 2.0),
        ("west_mid", min_x + (max_x - min_x) * 0.2, (min_y + max_y) / 2.0),
        ("east_mid", min_x + (max_x - min_x) * 0.8, (min_y + max_y) / 2.0),
        ("south_mid", (min_x + max_x) / 2.0, min_y + (max_y - min_y) * 0.2),
        ("north_mid", (min_x + max_x) / 2.0, min_y + (max_y - min_y) * 0.8),
    ]
    for name, x, y in coverage:
        extras.append(
            {
                "point_id": f"extra_map_{name}",
                "source": "map_bounds_coverage_point",
                "source_id": name,
                "label": name.replace("_", " "),
                "purpose": "extra_coverage",
                "frame_id": "map",
                "x": x,
                "y": y,
                "yaw": 0.0,
            }
        )
    return extras


def _camera_view(point: dict[str, Any], transform: dict[str, Any]) -> dict[str, Any]:
    scene_x, scene_y = _map_to_scene_xy(float(point["x"]), float(point["y"]), transform)
    yaw = float(point.get("yaw") or 0.0)
    look_distance = 3.0
    eye_z = 1.35
    target_z = 1.15
    target = [
        scene_x + math.cos(yaw) * look_distance,
        scene_y + math.sin(yaw) * look_distance,
        target_z,
    ]
    return {
        "view_id": _slug(str(point["point_id"])),
        "label": str(point.get("label") or point["point_id"]),
        "eye": _round_list([scene_x, scene_y, eye_z]),
        "target": _round_list(target),
        "up": [0.0, 0.0, 1.0],
        "map_point": {
            "frame_id": str(point.get("frame_id") or "map"),
            "x": round(float(point["x"]), 6),
            "y": round(float(point["y"]), 6),
            "yaw": round(yaw, 6),
            "source": str(point.get("source") or ""),
            "source_id": str(point.get("source_id") or ""),
            "purpose": str(point.get("purpose") or ""),
        },
        "scene_point_source": "approx_bbox_fit_unverified",
    }


def _bbox_map_to_scene_transform(
    map_bounds: tuple[float, float, float, float],
    scene_bounds: tuple[float, float, float, float],
) -> dict[str, Any]:
    map_min_x, map_min_y, map_max_x, map_max_y = map_bounds
    scene_min_x, scene_min_y, scene_max_x, scene_max_y = scene_bounds
    scale_x = (scene_max_x - scene_min_x) / max(map_max_x - map_min_x, 1e-6)
    scale_y = (scene_max_y - scene_min_y) / max(map_max_y - map_min_y, 1e-6)
    return {
        "type": "axis_aligned_bbox_fit_2d",
        "source": "deterministic_waypoint_capture_approximation",
        "source_frame": "map",
        "target_frame": "b1_scene_usd_world_xy",
        "map_bounds": _bounds_payload(map_bounds),
        "scene_xy_bounds": _bounds_payload(scene_bounds),
        "scale": {"x": round(scale_x, 9), "y": round(scale_y, 9)},
        "translation": {
            "x": round(scene_min_x - map_min_x * scale_x, 9),
            "y": round(scene_min_y - map_min_y * scale_y, 9),
        },
    }


def _map_to_scene_xy(x: float, y: float, transform: dict[str, Any]) -> tuple[float, float]:
    scale = transform["scale"]
    translation = transform["translation"]
    return (
        float(scale["x"]) * x + float(translation["x"]),
        float(scale["y"]) * y + float(translation["y"]),
    )


def _map_bounds(
    semantics: dict[str, Any],
    review: dict[str, Any],
    points: list[dict[str, Any]],
) -> tuple[float, float, float, float]:
    xs = [float(point["x"]) for point in points]
    ys = [float(point["y"]) for point in points]
    for raw in review.get("labels") or []:
        geometry = raw.get("geometry") if isinstance(raw, dict) else {}
        for point in geometry.get("points") or []:
            if isinstance(point, dict) and "x" in point and "y" in point:
                xs.append(float(point["x"]))
                ys.append(float(point["y"]))
    if not xs or not ys:
        raise ValueError("no map points available for waypoint capture")
    return min(xs), min(ys), max(xs), max(ys)


def _label_center(label: dict[str, Any]) -> tuple[float, float] | None:
    geometry = label.get("geometry") if isinstance(label.get("geometry"), dict) else {}
    points = geometry.get("points") if isinstance(geometry.get("points"), list) else []
    parsed = [
        (float(point["x"]), float(point["y"]))
        for point in points
        if isinstance(point, dict) and "x" in point and "y" in point
    ]
    if not parsed:
        return None
    return (
        sum(point[0] for point in parsed) / len(parsed),
        sum(point[1] for point in parsed) / len(parsed),
    )


def _scene_manifest(old_scene: Path, new_scene: Path, *, prepare_new: bool) -> dict[str, Any]:
    prepared_new = prepare_b1_nurec_scene_usd(new_scene) if prepare_new else None
    return {
        "old": {"label": "B1_floor2_slow", "scene_usd": str(old_scene)},
        "new": {
            "label": "2rd_floor_seperated",
            "scene_usd": str(new_scene),
            "prepared_scene_usd": str(prepared_new) if prepared_new else "",
        },
    }


def _parse_bounds(value: str) -> tuple[float, float, float, float]:
    parts = [float(item.strip()) for item in value.split(",") if item.strip()]
    if len(parts) != 4:
        raise ValueError("--scene-bounds must be min_x,min_y,max_x,max_y")
    min_x, min_y, max_x, max_y = parts
    if min_x >= max_x or min_y >= max_y:
        raise ValueError("--scene-bounds min values must be less than max values")
    return min_x, min_y, max_x, max_y


def _bounds_payload(bounds: tuple[float, float, float, float]) -> dict[str, float]:
    min_x, min_y, max_x, max_y = bounds
    return {
        "min_x": round(min_x, 9),
        "min_y": round(min_y, 9),
        "max_x": round(max_x, 9),
        "max_y": round(max_y, 9),
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    normalized = []
    for char in value.lower():
        normalized.append(char if char.isalnum() else "_")
    return "_".join("".join(normalized).split("_")).strip("_") or "point"


def _round_list(values: list[float]) -> list[float]:
    return [round(float(value), 6) for value in values]


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    if os.environ.get("ROBOCLAWS_HARD_EXIT_AFTER_ISAAC_CAPTURE") == "1":
        os._exit(code)
    raise SystemExit(code)
