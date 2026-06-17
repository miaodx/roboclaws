#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

from PIL import Image

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.b1_nurec_scene import prepare_b1_nurec_scene_usd
from roboclaws.household.camera_control import (
    CANONICAL_CAMERA_MODEL,
    canonical_scene_camera_control_request,
    write_camera_control_request,
)

TOPDOWN_RENDER_SCHEMA = "b1_scene_gaussian_topdown_render_v1"
SCENE_TOPDOWN_PICK_SOURCE = "rendered_gaussian_scene_topdown_ray_plane_pick"
DEFAULT_SCENE_USD = Path("data/robot-data-lab/scene-engine/data/2rd_floor_seperated/storey_1")
DEFAULT_SCENE_USD = DEFAULT_SCENE_USD / "scene_gs.usda"
DEFAULT_OUTPUT_DIR = Path("output/b1-map12/scene-gaussian-topdown")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the B1 rebuilt Gaussian scene as a required top-down review image."
    )
    parser.add_argument("--scene-usd", type=Path, default=DEFAULT_SCENE_USD)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=640)
    parser.add_argument(
        "--scene-xy-bounds",
        help="Scene XY bounds as min_x,min_y,max_x,max_y. Required; no inferred fallback.",
    )
    parser.add_argument("--camera-height-m", type=float, default=28.0)
    parser.add_argument("--target-z-m", type=float, default=0.6)
    parser.add_argument("--fov-deg", type=float, default=65.0)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--capture-one-scene", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--camera-request", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--views-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--result", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.capture_one_scene:
        return _capture_one_scene_cli(args)
    if not args.scene_xy_bounds:
        raise ValueError("--scene-xy-bounds is required; no inferred bounds fallback is allowed")

    scene_bounds = _parse_bounds(args.scene_xy_bounds)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_usd = Path(args.scene_usd)
    prepared_scene_usd = prepare_b1_nurec_scene_usd(scene_usd) or scene_usd
    request = build_topdown_camera_request(
        scene_bounds=scene_bounds,
        width=max(1, int(args.width)),
        height=max(1, int(args.height)),
        camera_height_m=float(args.camera_height_m),
        target_z_m=float(args.target_z_m),
        fov_deg=float(args.fov_deg),
    )
    request_path = write_camera_control_request(output_dir / "camera_request.json", request)
    packet = topdown_render_packet(
        scene_usd=scene_usd,
        prepared_scene_usd=prepared_scene_usd,
        scene_bounds=scene_bounds,
        request=request,
        request_path=request_path,
        output_dir=output_dir,
        capture_result=None,
    )
    if args.capture:
        result_path = output_dir / "capture_result.json"
        capture = _capture_scene(
            scene_usd=prepared_scene_usd,
            camera_request=request_path,
            output_dir=output_dir / "views",
            result_path=result_path,
            width=max(1, int(args.width)),
            height=max(1, int(args.height)),
        )
        packet = topdown_render_packet(
            scene_usd=scene_usd,
            prepared_scene_usd=prepared_scene_usd,
            scene_bounds=scene_bounds,
            request=request,
            request_path=request_path,
            output_dir=output_dir,
            capture_result=capture,
        )
    packet_path = output_dir / "scene_gaussian_topdown.json"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_topdown_render_packet(packet)
    summary = {
        "schema": TOPDOWN_RENDER_SCHEMA,
        "status": "passed" if not errors else "failed",
        "geometry_status": packet.get("geometry_status"),
        "packet": str(packet_path),
        "topdown_image": packet.get("topdown_image"),
        "errors": errors,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if not errors else 2


def build_topdown_camera_request(
    *,
    scene_bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    camera_height_m: float,
    target_z_m: float,
    fov_deg: float,
) -> dict[str, Any]:
    min_x, min_y, max_x, max_y = scene_bounds
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    span = max(max_x - min_x, max_y - min_y)
    view = {
        "view_id": "top2down",
        "label": "B1 Gaussian scene top-down oblique",
        "camera_model": CANONICAL_CAMERA_MODEL,
        "coordinate_frame": "b1_rebuilt_scene_usd_world_candidate",
        "coordinate_convention": "b1_rebuilt_scene_usd_world_candidate",
        "camera_mode": "high_oblique_topdown_perspective",
        "eye": [round(center_x, 6), round(center_y - span * 0.55, 6), round(camera_height_m, 6)],
        "target": [round(center_x, 6), round(center_y, 6), round(target_z_m, 6)],
        "up": [0.0, 0.0, 1.0],
        "lens": {"focal_length_mm": 18.0, "vertical_fov_deg": float(fov_deg)},
        "calibration_status": "explicit_scene_xy_bounds_topdown_v1",
    }
    request = canonical_scene_camera_control_request(
        [view],
        width=width,
        height=height,
        lens={"focal_length_mm": 18.0, "vertical_fov_deg": float(fov_deg)},
        scene_frame="b1_rebuilt_scene_usd_world_candidate",
        calibration_status="explicit_scene_xy_bounds_topdown_v1",
    )
    request["topdown_scene_xy_bounds"] = _bounds_payload(scene_bounds)
    request["topdown_pixel_to_scene_xyz"] = pixel_to_scene_xyz_transform(
        view=view,
        width=width,
        height=height,
    )
    return request


def topdown_render_packet(
    *,
    scene_usd: Path,
    prepared_scene_usd: Path,
    scene_bounds: tuple[float, float, float, float],
    request: dict[str, Any],
    request_path: Path,
    output_dir: Path,
    capture_result: dict[str, Any] | None,
) -> dict[str, Any]:
    image = ""
    capture_result_path = ""
    capture_status = "request_written"
    if capture_result:
        capture_status = "captured" if capture_result.get("ok") is True else "failed"
        capture_result_path = str(capture_result.get("result_path") or "")
        images = capture_result.get("capture", {}).get("images", {})
        image = str(images.get("top2down") or "")
    size = image_size(Path(image))
    return {
        "schema": TOPDOWN_RENDER_SCHEMA,
        "geometry_status": "rendered_gaussian_scene_topdown" if image else "render_required",
        "scene_usd": str(scene_usd),
        "prepared_scene_usd": str(prepared_scene_usd),
        "camera_request": str(request_path),
        "capture_result": capture_result_path,
        "capture_status": capture_status,
        "topdown_image": image,
        "width_px": size[0],
        "height_px": size[1],
        "up_axis": "z",
        "horizontal_axes": ["x", "y"],
        "scene_xy_bounds": _bounds_payload(scene_bounds),
        "pixel_to_scene_xyz": {
            **pixel_to_scene_xyz_transform(
                view=request["views"][0],
                width=int(request["render_resolution"]["width"]),
                height=int(request["render_resolution"]["height"]),
            ),
            "note": (
                "Scene picks intersect the perspective camera ray with z=0 in the "
                "recorded scene frame. Different camera heights/FOVs change visibility "
                "and ray geometry; review the recorded camera request before accepting anchors."
            ),
        },
        "camera": dict(request["views"][0]),
        "output_dir": str(output_dir),
    }


def validate_topdown_render_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if packet.get("schema") != TOPDOWN_RENDER_SCHEMA:
        errors.append("unexpected topdown render schema")
    if packet.get("geometry_status") != "rendered_gaussian_scene_topdown":
        errors.append("topdown render must be captured before review")
    image = Path(str(packet.get("topdown_image") or ""))
    if not image.is_file():
        errors.append("topdown render image missing")
    if int(packet.get("width_px") or 0) <= 0 or int(packet.get("height_px") or 0) <= 0:
        errors.append("topdown render image size missing")
    if packet.get("up_axis") != "z":
        errors.append("topdown render must record up_axis=z")
    if packet.get("horizontal_axes") != ["x", "y"]:
        errors.append("topdown render must record horizontal_axes=[x,y]")
    transform = packet.get("pixel_to_scene_xyz")
    if not isinstance(transform, dict):
        errors.append("topdown render missing pixel_to_scene_xyz")
    elif transform.get("source") != SCENE_TOPDOWN_PICK_SOURCE:
        errors.append("topdown render has unexpected pixel_to_scene_xyz source")
    return errors


def _capture_scene(
    *,
    scene_usd: Path,
    camera_request: Path,
    output_dir: Path,
    result_path: Path,
    width: int,
    height: int,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--capture-one-scene",
        "--scene-usd",
        str(scene_usd),
        "--camera-request",
        str(camera_request),
        "--views-dir",
        str(output_dir),
        "--result",
        str(result_path),
        "--width",
        str(width),
        "--height",
        str(height),
    ]
    env = os.environ.copy()
    env.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")
    env["ROBOCLAWS_HARD_EXIT_AFTER_ISAAC_CAPTURE"] = "1"
    subprocess.run(command, cwd=Path(__file__).resolve().parents[2], env=env, check=True)
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["result_path"] = str(result_path)
    return payload


def _capture_one_scene_cli(args: argparse.Namespace) -> int:
    if args.camera_request is None or args.views_dir is None or args.result is None:
        raise ValueError("--capture-one-scene requires --camera-request, --views-dir, and --result")
    request = json.loads(args.camera_request.read_text(encoding="utf-8"))
    from scripts.isaac_lab_cleanup import isaac_lab_backend_worker

    args.result.parent.mkdir(parents=True, exist_ok=True)
    try:
        capture = isaac_lab_backend_worker.capture_scene_camera_views(
            scene_usd=args.scene_usd,
            camera_request=request,
            output_dir=args.views_dir,
            width=max(1, int(args.width)),
            height=max(1, int(args.height)),
            semantic_pose_state={},
        )
        payload = {"ok": True, "scene_usd": str(args.scene_usd), "capture": capture}
    except Exception as exc:
        payload = {
            "ok": False,
            "scene_usd": str(args.scene_usd),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        args.result.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        raise
    args.result.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def pixel_to_scene_xyz_transform(
    *,
    view: dict[str, Any],
    width: int,
    height: int,
) -> dict[str, Any]:
    lens = view.get("lens") if isinstance(view.get("lens"), dict) else {}
    return {
        "status": "perspective_ray_plane_z0",
        "source": SCENE_TOPDOWN_PICK_SOURCE,
        "projection_model": "camera_ray_intersection_with_z_plane",
        "z_plane": 0.0,
        "width_px": int(width),
        "height_px": int(height),
        "vertical_fov_deg": float(lens.get("vertical_fov_deg") or 65.0),
        "eye": list(view.get("eye") or []),
        "target": list(view.get("target") or []),
        "world_up": [0.0, 0.0, 1.0],
        "formula": "ray = perspective_camera_ray(pixel); scene_xyz = ray intersect z=0",
    }


def _parse_bounds(value: str) -> tuple[float, float, float, float]:
    parts = [float(item.strip()) for item in value.split(",") if item.strip()]
    if len(parts) != 4:
        raise ValueError("--scene-xy-bounds must be min_x,min_y,max_x,max_y")
    min_x, min_y, max_x, max_y = parts
    if min_x >= max_x or min_y >= max_y:
        raise ValueError("--scene-xy-bounds min values must be less than max values")
    return min_x, min_y, max_x, max_y


def _bounds_payload(bounds: tuple[float, float, float, float]) -> dict[str, float]:
    min_x, min_y, max_x, max_y = bounds
    return {
        "min_x": round(float(min_x), 9),
        "min_y": round(float(min_y), 9),
        "max_x": round(float(max_x), 9),
        "max_y": round(float(max_y), 9),
    }


def image_size(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return 0, 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    if os.environ.get("ROBOCLAWS_HARD_EXIT_AFTER_ISAAC_CAPTURE") == "1":
        os._exit(code)
    raise SystemExit(code)
