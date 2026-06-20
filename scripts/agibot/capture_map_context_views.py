#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.core.json_sources import read_json_object  # noqa: E402

CAMERA_NAMES = (
    "head_back_fisheye",
    "head_left_fisheye",
    "head_right_fisheye",
    "head_stereo_left",
    "head_stereo_right",
    "hand_left_color",
    "hand_right_color",
    "head_color",
    "head_depth",
    "hand_left_depth",
    "hand_right_depth",
    "hand_left_upper_color",
    "hand_right_upper_color",
    "hand_left_lower_color",
    "hand_right_lower_color",
    "hand_left_upper_depth",
    "hand_right_upper_depth",
    "hand_left_lower_depth",
    "hand_right_lower_depth",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture Agibot G2 map id, robot pose, and camera views for human "
            "cleanup-map authoring. Run this on the robot/GDK machine."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Capture directory. Defaults to output/agibot/map-context/<timestamp>.",
    )
    parser.add_argument(
        "--context-json",
        type=Path,
        default=None,
        help=(
            "Existing agibot_map_context JSON to update. When provided, this "
            "capture appends or replaces --waypoint-id in that file."
        ),
    )
    parser.add_argument(
        "--cameras",
        default="all",
        help="Comma-separated camera names, or 'all'. Default: all.",
    )
    parser.add_argument("--image-timeout-ms", type=float, default=1000.0)
    parser.add_argument("--init-wait-s", type=float, default=2.0)
    parser.add_argument("--waypoint-id", default="wp_todo_1")
    parser.add_argument("--room-id", default="room_todo")
    parser.add_argument("--fixture-id", default="fixture_todo")
    parser.add_argument("--label", default="TODO: describe this waypoint")
    parser.add_argument("--room-label", default="TODO: room label")
    parser.add_argument("--fixture-label", default="TODO: fixture label")
    parser.add_argument("--fixture-category", default="TODO: sofa/table/shelf/etc")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    output_dir = args.output_dir or _default_output_dir(
        context_json=args.context_json,
        waypoint_id=args.waypoint_id,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    gdk = _import_gdk()
    initialized = False
    try:
        result = gdk.gdk_init()
        if hasattr(gdk, "GDKRes") and result != gdk.GDKRes.kSuccess:
            raise SystemExit(f"agibot_gdk.gdk_init failed: {result}")
        initialized = True

        map_manager = gdk.Map()
        slam = gdk.Slam()
        camera = gdk.Camera()
        time.sleep(args.init_wait_s)

        current_map = _map_name_to_dict(_try_call(map_manager.get_curr_map))
        all_maps = [_map_name_to_dict(item) for item in (_try_call(map_manager.get_all_map) or [])]
        current_pose = _pose_to_xyyaw(_try_call(slam.get_curr_pose))
        if current_pose is None:
            current_pose = _odom_to_xyyaw(_try_call(slam.get_odom_info))

        camera_results = _capture_cameras(
            gdk=gdk,
            camera=camera,
            names=_selected_cameras(args.cameras),
            output_dir=output_dir,
            timeout_ms=args.image_timeout_ms,
        )
        try:
            camera.close_camera()
        except Exception as exc:  # noqa: BLE001
            print(f"warning: failed to close camera: {exc}", file=sys.stderr)

        manifest = {
            "schema": "agibot_gdk_map_context_capture_v1",
            "captured_at": _now_iso(),
            "waypoint_id": args.waypoint_id,
            "map_source": {
                "type": "agibot_gdk_map_context",
                "map_id": current_map.get("id"),
                "map_name": current_map.get("name", ""),
                "is_curr_map": current_map.get("is_curr_map"),
                "all_maps": all_maps,
            },
            "robot_pose": current_pose,
            "camera_results": camera_results,
            "public_contract_note": (
                "This capture is operator-prep evidence. It is not a Nav2 map export "
                "and does not contain private cleanup target truth."
            ),
        }
        manifest_path = output_dir / "capture_manifest.json"
        _write_json(manifest_path, manifest)

        if args.context_json is not None:
            context = _load_context(args.context_json)
            _upsert_capture_into_context(
                context,
                manifest=manifest,
                manifest_path=manifest_path,
                context_dir=args.context_json.parent,
                room_id=args.room_id,
                room_label=args.room_label,
                fixture_id=args.fixture_id,
                fixture_label=args.fixture_label,
                fixture_category=args.fixture_category,
                waypoint_id=args.waypoint_id,
                waypoint_label=args.label,
            )
            _write_json(args.context_json, context)
            context_path = args.context_json
        else:
            template = _authoring_template(
                manifest=manifest,
                manifest_path=manifest_path,
                context_dir=output_dir,
                waypoint_id=args.waypoint_id,
                room_id=args.room_id,
                room_label=args.room_label,
                fixture_id=args.fixture_id,
                fixture_label=args.fixture_label,
                fixture_category=args.fixture_category,
                label=args.label,
            )
            context_path = output_dir / "agibot_map_context.todo.json"
            _write_json(context_path, template)
        print(f"agibot map-context capture written: {output_dir}")
        print(f"fill or review this file next: {context_path}")
    finally:
        if initialized:
            try:
                gdk.gdk_release()
            except Exception as exc:  # noqa: BLE001
                print(f"warning: agibot_gdk.gdk_release failed: {exc}", file=sys.stderr)


def _default_output_dir(*, context_json: Path | None, waypoint_id: str) -> Path:
    if context_json is not None:
        return context_json.parent / "captures" / waypoint_id
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("output") / "agibot" / "map-context" / stamp


def _import_gdk() -> Any:
    try:
        import agibot_gdk
    except ImportError as exc:
        raise SystemExit(
            "agibot_gdk is not importable. Run this script on the Agibot GDK machine."
        ) from exc
    return agibot_gdk


def _selected_cameras(raw: str) -> list[str]:
    if raw.strip().lower() == "all":
        return list(CAMERA_NAMES)
    names = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [name for name in names if name not in CAMERA_NAMES]
    if unknown:
        raise SystemExit(f"unknown camera name(s): {', '.join(unknown)}")
    return names


def _capture_cameras(
    *,
    gdk: Any,
    camera: Any,
    names: list[str],
    output_dir: Path,
    timeout_ms: float,
) -> list[dict[str, Any]]:
    camera_types = _camera_name_to_type(gdk)
    results = []
    for name in names:
        try:
            image = camera.get_latest_image(camera_types[name], timeout_ms)
            if image is None:
                raise RuntimeError("camera returned no image")
            saved = _save_image(name=name, image=image, output_dir=output_dir)
            results.append(
                {
                    "camera_name": name,
                    "ok": True,
                    "image_path": saved["image_path"],
                    "raw_path": saved.get("raw_path"),
                    "width": int(getattr(image, "width", 0) or 0),
                    "height": int(getattr(image, "height", 0) or 0),
                    "timestamp_ns": int(getattr(image, "timestamp_ns", 0) or 0),
                    "encoding": _enum_name(getattr(image, "encoding", "")),
                    "color_format": _enum_name(getattr(image, "color_format", "")),
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append({"camera_name": name, "ok": False, "error": str(exc)})
            print(f"warning: failed to capture {name}: {exc}", file=sys.stderr)
    return results


def _save_image(*, name: str, image: Any, output_dir: Path) -> dict[str, str]:
    raw = _image_bytes(image)
    encoding = _enum_name(getattr(image, "encoding", ""))
    color_format = _enum_name(getattr(image, "color_format", ""))
    width = int(getattr(image, "width", 0) or 0)
    height = int(getattr(image, "height", 0) or 0)

    if encoding == "JPEG":
        path = output_dir / f"{name}.jpg"
        path.write_bytes(raw)
        return {"image_path": path.name}
    if encoding == "PNG":
        path = output_dir / f"{name}.png"
        path.write_bytes(raw)
        return {"image_path": path.name}
    if encoding != "UNCOMPRESSED" or width <= 0 or height <= 0:
        raw_path = output_dir / f"{name}.bin"
        raw_path.write_bytes(raw)
        return {"image_path": raw_path.name, "raw_path": raw_path.name}

    path = output_dir / f"{name}.png"
    if color_format == "RGB":
        Image.frombytes("RGB", (width, height), raw).save(path)
    elif color_format == "BGR":
        array = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        Image.fromarray(array[:, :, ::-1], mode="RGB").save(path)
    elif color_format == "GRAY8":
        Image.frombytes("L", (width, height), raw).save(path)
    elif color_format in {"GRAY16", "RS2_FORMAT_Z16"}:
        array = np.frombuffer(raw, dtype=np.uint16).reshape((height, width))
        Image.fromarray(array, mode="I;16").save(path)
    else:
        raw_path = output_dir / f"{name}.bin"
        raw_path.write_bytes(raw)
        return {"image_path": raw_path.name, "raw_path": raw_path.name}
    return {"image_path": path.name}


def _authoring_template(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    context_dir: Path,
    waypoint_id: str,
    room_id: str,
    room_label: str,
    fixture_id: str,
    fixture_label: str,
    fixture_category: str,
    label: str,
) -> dict[str, Any]:
    pose = manifest.get("robot_pose") or {}
    capture = _capture_reference(
        manifest=manifest,
        manifest_path=manifest_path,
        context_dir=context_dir,
    )
    return {
        "schema": "agibot_gdk_map_context_authoring_v1",
        "map_source": manifest["map_source"],
        "capture": capture,
        "waypoint_captures": [capture],
        "human_todo": [
            "Replace TODO labels with stable room/fixture names.",
            "Record more waypoints with --context-json pointing at this file.",
            "Keep runtime movable-object targets and private scoring truth out of this file.",
        ],
        "frame_id": pose.get("frame_id", "map"),
        "map_version": "operator-authored-v1",
        "rooms": [
            {
                "room_id": room_id,
                "room_label": room_label,
                "polygon": [],
            }
        ],
        "fixtures": [
            {
                "fixture_id": fixture_id,
                "room_id": room_id,
                "label": fixture_label,
                "category": fixture_category,
                "pose": {"x": None, "y": None, "yaw": None},
                "footprint": [],
            }
        ],
        "inspection_waypoints": [
            _waypoint_template(
                manifest=manifest,
                capture=capture,
                waypoint_id=waypoint_id,
                room_id=room_id,
                fixture_id=fixture_id,
                label=label,
            )
        ],
        "driveable_ways": [],
    }


def _load_context(path: Path) -> dict[str, Any]:
    try:
        return read_json_object(path, label="Agibot map context")
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


def _upsert_capture_into_context(
    context: dict[str, Any],
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    context_dir: Path,
    room_id: str,
    room_label: str,
    fixture_id: str,
    fixture_label: str,
    fixture_category: str,
    waypoint_id: str,
    waypoint_label: str,
) -> None:
    if context.get("schema") != "agibot_gdk_map_context_authoring_v1":
        raise SystemExit("context schema must be agibot_gdk_map_context_authoring_v1")
    context["map_source"] = manifest["map_source"]
    context.setdefault("frame_id", (manifest.get("robot_pose") or {}).get("frame_id", "map"))
    context.setdefault("map_version", "operator-authored-v1")
    context.setdefault("driveable_ways", [])
    _upsert_by_key(
        context.setdefault("rooms", []),
        "room_id",
        {
            "room_id": room_id,
            "room_label": room_label,
            "polygon": [],
        },
    )
    _upsert_by_key(
        context.setdefault("fixtures", []),
        "fixture_id",
        {
            "fixture_id": fixture_id,
            "room_id": room_id,
            "label": fixture_label,
            "category": fixture_category,
            "pose": {"x": None, "y": None, "yaw": None},
            "footprint": [],
        },
        preserve_existing=True,
    )
    capture = _capture_reference(
        manifest=manifest,
        manifest_path=manifest_path,
        context_dir=context_dir,
    )
    _upsert_by_key(context.setdefault("waypoint_captures", []), "waypoint_id", capture)
    _upsert_by_key(
        context.setdefault("inspection_waypoints", []),
        "waypoint_id",
        _waypoint_template(
            manifest=manifest,
            capture=capture,
            waypoint_id=waypoint_id,
            room_id=room_id,
            fixture_id=fixture_id,
            label=waypoint_label,
        ),
    )


def _waypoint_template(
    *,
    manifest: dict[str, Any],
    capture: dict[str, Any],
    waypoint_id: str,
    room_id: str,
    fixture_id: str,
    label: str,
) -> dict[str, Any]:
    pose = manifest.get("robot_pose") or {}
    return {
        "waypoint_id": waypoint_id,
        "room_id": room_id,
        "fixture_id": fixture_id,
        "label": label,
        "purpose": "inspect_fixture",
        "waypoint_source": "operator_recorded_pose",
        "x": pose.get("x"),
        "y": pose.get("y"),
        "yaw": pose.get("yaw"),
        "visited": False,
        "capture": capture,
    }


def _capture_reference(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    context_dir: Path,
) -> dict[str, Any]:
    return {
        "waypoint_id": str(manifest.get("waypoint_id") or ""),
        "captured_at": manifest["captured_at"],
        "manifest_path": _relative_path(manifest_path, context_dir),
        "camera_images": [
            {
                "camera_name": item["camera_name"],
                "image_path": _relative_path(
                    manifest_path.parent / str(item.get("image_path", "")), context_dir
                )
                if item.get("image_path")
                else "",
                "ok": item.get("ok", False),
            }
            for item in manifest["camera_results"]
        ],
    }


def _upsert_by_key(
    items: list[Any],
    key: str,
    replacement: dict[str, Any],
    *,
    preserve_existing: bool = False,
) -> None:
    value = replacement.get(key)
    for index, item in enumerate(items):
        if isinstance(item, dict) and item.get(key) == value:
            if preserve_existing:
                merged = dict(replacement)
                merged.update(item)
                items[index] = merged
            else:
                items[index] = replacement
            return
    items.append(replacement)


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _camera_name_to_type(gdk: Any) -> dict[str, Any]:
    return {
        "head_back_fisheye": gdk.CameraType.kHeadBackFisheye,
        "head_left_fisheye": gdk.CameraType.kHeadLeftFisheye,
        "head_right_fisheye": gdk.CameraType.kHeadRightFisheye,
        "head_stereo_left": gdk.CameraType.kHeadStereoLeft,
        "head_stereo_right": gdk.CameraType.kHeadStereoRight,
        "hand_left_color": gdk.CameraType.kHandLeftColor,
        "hand_right_color": gdk.CameraType.kHandRightColor,
        "head_color": gdk.CameraType.kHeadColor,
        "head_depth": gdk.CameraType.kHeadDepth,
        "hand_left_depth": gdk.CameraType.kHandLeftDepth,
        "hand_right_depth": gdk.CameraType.kHandRightDepth,
        "hand_left_upper_color": gdk.CameraType.kHandLeftUpperColor,
        "hand_right_upper_color": gdk.CameraType.kHandRightUpperColor,
        "hand_left_lower_color": gdk.CameraType.kHandLeftLowerColor,
        "hand_right_lower_color": gdk.CameraType.kHandRightLowerColor,
        "hand_left_upper_depth": gdk.CameraType.kHandLeftUpperDepth,
        "hand_right_upper_depth": gdk.CameraType.kHandRightUpperDepth,
        "hand_left_lower_depth": gdk.CameraType.kHandLeftLowerDepth,
        "hand_right_lower_depth": gdk.CameraType.kHandRightLowerDepth,
    }


def _map_name_to_dict(item: Any) -> dict[str, Any]:
    if item is None:
        return {"id": None, "name": "", "is_curr_map": None}
    return {
        "id": _get_attr(item, "id"),
        "name": str(_get_attr(item, "name") or ""),
        "is_curr_map": _get_attr(item, "is_curr_map"),
    }


def _pose_to_xyyaw(item: Any) -> dict[str, Any] | None:
    position, orientation = _extract_position_orientation(item)
    if position is None or orientation is None:
        return None
    return {
        "frame_id": "map",
        "x": float(position.x),
        "y": float(position.y),
        "z": float(getattr(position, "z", 0.0) or 0.0),
        "yaw": _yaw_from_quaternion(orientation),
        "orientation_xyzw": [
            float(getattr(orientation, "x", 0.0) or 0.0),
            float(getattr(orientation, "y", 0.0) or 0.0),
            float(getattr(orientation, "z", 0.0) or 0.0),
            float(getattr(orientation, "w", 1.0) or 1.0),
        ],
        "pose_source": "agibot_gdk_slam_get_curr_pose",
    }


def _odom_to_xyyaw(item: Any) -> dict[str, Any] | None:
    pose = _pose_to_xyyaw(item)
    if pose is not None:
        pose["pose_source"] = "agibot_gdk_slam_get_odom_info"
    return pose


def _extract_position_orientation(item: Any) -> tuple[Any | None, Any | None]:
    candidates = [item]
    if item is not None and hasattr(item, "pose"):
        candidates.append(item.pose)
        if hasattr(item.pose, "pose"):
            candidates.append(item.pose.pose)
    for candidate in candidates:
        if (
            candidate is not None
            and hasattr(candidate, "position")
            and hasattr(candidate, "orientation")
        ):
            return candidate.position, candidate.orientation
    return None, None


def _yaw_from_quaternion(quat: Any) -> float:
    x = float(getattr(quat, "x", 0.0) or 0.0)
    y = float(getattr(quat, "y", 0.0) or 0.0)
    z = float(getattr(quat, "z", 0.0) or 0.0)
    w = float(getattr(quat, "w", 1.0) or 1.0)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def _image_bytes(image: Any) -> bytes:
    data = image.data
    if hasattr(data, "tobytes"):
        return data.tobytes()
    return bytes(data)


def _enum_name(value: Any) -> str:
    name = getattr(value, "name", None)
    if name:
        return str(name)
    return str(value).rsplit(".", 1)[-1]


def _get_attr(item: Any, name: str) -> Any:
    return getattr(item, name, None)


def _try_call(func: Any) -> Any:
    try:
        return func()
    except Exception as exc:  # noqa: BLE001
        print(f"warning: {getattr(func, '__name__', 'gdk call')} failed: {exc}", file=sys.stderr)
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
