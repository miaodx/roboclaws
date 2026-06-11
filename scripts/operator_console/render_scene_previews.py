#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageStat

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]

from roboclaws.household.backend_contract import CleanupBackendSession  # noqa: E402
from roboclaws.household.camera_control import canonical_scene_camera_control_request  # noqa: E402
from roboclaws.household.realworld_contract import (  # noqa: E402
    MINIMAL_MAP_MODE,
    RAW_FPV_ONLY_MODE,
    RealWorldCleanupContract,
)
from roboclaws.household.subprocess_backend import MolmoSpacesSubprocessBackend  # noqa: E402
from roboclaws.launch.worlds import MOLMOSPACES_CONSOLE_WORLD_IDS  # noqa: E402

PREVIEW_METADATA_SCHEMA = "operator_console_scene_preview_v1"
DEFAULT_OUTPUT_DIR = Path("roboclaws/operator_console/static/previews")
DEFAULT_WORK_DIR = Path("output/operator-console-scene-previews")
DEFAULT_WIDTH = 900
DEFAULT_HEIGHT = 560


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = render_previews(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "success" else 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render operator-console scene previews from backend cameras. "
            "MolmoSpaces previews are real MuJoCo renders: Raw FPV is captured "
            "from the first public waypoint, Chase is the robot follower camera, "
            "and Top-down is a separate scene camera render rather than a "
            "semantic-map fallback."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--world",
        action="append",
        default=[],
        help="World id to render. Defaults to all visible MolmoSpaces console scenes.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help=(
            "Do not render a world when FPV, semantic map, chase, and top-down preview "
            "files already exist."
        ),
    )
    return parser.parse_args(argv)


def render_previews(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = args.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for world_id in _selected_world_ids(args.world):
        result = render_molmospaces_preview(
            world_id=world_id,
            output_dir=output_dir,
            work_dir=work_dir,
            seed=int(args.seed),
            width=max(1, int(args.width)),
            height=max(1, int(args.height)),
            skip_existing=bool(args.skip_existing),
        )
        results.append(result)

    status = (
        "success"
        if all(item.get("status") in {"rendered", "skipped"} for item in results)
        else "failed"
    )
    return {
        "schema": "operator_console_scene_preview_render_report_v1",
        "status": status,
        "generated_at": _utc_timestamp(),
        "output_dir": str(output_dir),
        "work_dir": str(work_dir),
        "results": results,
    }


def render_molmospaces_preview(
    *,
    world_id: str,
    output_dir: Path,
    work_dir: Path,
    seed: int,
    width: int,
    height: int,
    skip_existing: bool = False,
) -> dict[str, Any]:
    scene_index = _molmospaces_scene_index(world_id)
    slug = _world_slug(world_id)
    fpv_path = output_dir / f"{slug}-fpv.png"
    map_path = output_dir / f"{slug}-map.png"
    chase_path = output_dir / f"{slug}-chase.png"
    topdown_path = output_dir / f"{slug}-topdown.png"
    metadata_path = output_dir / f"{slug}-preview.json"
    if (
        skip_existing
        and fpv_path.exists()
        and map_path.exists()
        and chase_path.exists()
        and topdown_path.exists()
    ):
        return {
            "world_id": world_id,
            "scene_index": scene_index,
            "status": "skipped",
            "fpv": str(fpv_path),
            "map": str(map_path),
            "chase": str(chase_path),
            "topdown": str(topdown_path),
            "metadata": str(metadata_path),
        }

    run_dir = work_dir / slug
    backend = MolmoSpacesSubprocessBackend(
        run_dir=run_dir / "backend",
        seed=seed,
        scene_source="procthor-10k-val",
        scene_index=scene_index,
        include_robot=True,
        robot_name="rby1m",
        generated_mess_count=0,
    )
    try:
        contract = RealWorldCleanupContract(
            CleanupBackendSession(backend.scenario, backend=backend),
            perception_mode=RAW_FPV_ONLY_MODE,
            map_mode=MINIMAL_MAP_MODE,
        )
        metric_map = contract.metric_map()
        waypoint = _first_public_waypoint(metric_map)
        navigation = contract.navigate_to_waypoint(str(waypoint["waypoint_id"]))
        if not navigation.get("ok"):
            return {
                "world_id": world_id,
                "scene_index": scene_index,
                "status": "navigate_failed",
                "waypoint_id": waypoint.get("waypoint_id"),
                "navigation": navigation,
            }

        views = backend.write_robot_views_with_resolution(
            run_dir / "robot_views",
            label="preview_first_waypoint",
            width=width,
            height=height,
        )
        raw_fpv = Path(str(views.get("views", {}).get("fpv") or ""))
        raw_chase = Path(str(views.get("views", {}).get("chase") or ""))
        if not raw_fpv.is_file():
            return {
                "world_id": world_id,
                "scene_index": scene_index,
                "status": "fpv_missing",
                "waypoint_id": waypoint.get("waypoint_id"),
                "views": views,
            }
        if not raw_chase.is_file():
            return {
                "world_id": world_id,
                "scene_index": scene_index,
                "status": "chase_missing",
                "waypoint_id": waypoint.get("waypoint_id"),
                "views": views,
            }

        state_path = run_dir / "backend" / "molmospaces_backend_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        scene_alignment = _scene_alignment(state, width=width, height=height)
        semantic_map = _render_semantic_map_preview(
            state,
            metric_map=metric_map,
            alignment=scene_alignment,
            world_label=world_id,
            width=width,
            height=height,
        )
        semantic_map.save(map_path)

        topdown_request = _topdown_camera_request(
            state,
            width=width,
            height=height,
            alignment=scene_alignment,
        )
        request_path = run_dir / "topdown_camera_request.json"
        request_path.write_text(
            json.dumps(topdown_request, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        topdown = backend.render_camera_control_request(
            run_dir / "camera_views",
            request_path=request_path,
        )
        raw_topdown = Path(str(topdown.get("images", {}).get("topdown_scene") or ""))
        if not raw_topdown.is_file():
            return {
                "world_id": world_id,
                "scene_index": scene_index,
                "status": "topdown_missing",
                "waypoint_id": waypoint.get("waypoint_id"),
                "topdown": topdown,
            }

        chase_selection = _select_chase_preview(
            contract=contract,
            backend=backend,
            run_dir=run_dir,
            width=width,
            height=height,
            first_waypoint=waypoint,
            first_navigation=navigation,
            first_robot_views=views,
            first_chase_path=raw_chase,
            candidate_waypoints=_public_waypoints(metric_map)[1:],
        )
        raw_chase = Path(str(chase_selection["path"]))

        shutil.copyfile(raw_fpv, fpv_path)
        shutil.copyfile(raw_chase, chase_path)
        shutil.copyfile(raw_topdown, topdown_path)
        metadata = _preview_metadata(
            world_id=world_id,
            scene_index=scene_index,
            seed=seed,
            width=width,
            height=height,
            waypoint=waypoint,
            navigation=navigation,
            robot_views=views,
            topdown_result=topdown,
            topdown_request=topdown_request,
            fpv_path=fpv_path,
            map_path=map_path,
            chase_path=chase_path,
            chase_waypoint=chase_selection["waypoint"],
            chase_navigation=chase_selection["navigation"],
            chase_robot_views=chase_selection["robot_views"],
            chase_selection=chase_selection,
            topdown_path=topdown_path,
            scene_alignment=scene_alignment,
        )
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "world_id": world_id,
            "scene_index": scene_index,
            "status": "rendered",
            "waypoint_id": waypoint.get("waypoint_id"),
            "fpv": str(fpv_path),
            "map": str(map_path),
            "chase": str(chase_path),
            "topdown": str(topdown_path),
            "metadata": str(metadata_path),
        }
    finally:
        backend.close()


def _preview_metadata(
    *,
    world_id: str,
    scene_index: int,
    seed: int,
    width: int,
    height: int,
    waypoint: dict[str, Any],
    navigation: dict[str, Any],
    robot_views: dict[str, Any],
    topdown_result: dict[str, Any],
    topdown_request: dict[str, Any],
    fpv_path: Path,
    map_path: Path,
    chase_path: Path,
    chase_waypoint: dict[str, Any],
    chase_navigation: dict[str, Any],
    chase_robot_views: dict[str, Any],
    chase_selection: dict[str, Any],
    topdown_path: Path,
    scene_alignment: dict[str, Any],
) -> dict[str, Any]:
    topdown_view = next(
        (
            item
            for item in topdown_result.get("views") or []
            if item.get("view_id") == "topdown_scene"
        ),
        {},
    )
    return {
        "schema": PREVIEW_METADATA_SCHEMA,
        "generated_at": _utc_timestamp(),
        "world_id": world_id,
        "backend": "mujoco",
        "renderer": "molmospaces_subprocess_mujoco",
        "scene_source": "procthor-10k-val",
        "scene_index": scene_index,
        "seed": seed,
        "render_resolution": {"width": width, "height": height},
        "views": {
            "fpv": {
                "path": fpv_path.name,
                "view": "raw_fpv",
                "waypoint_id": str(waypoint.get("waypoint_id") or ""),
                "camera": "robot_0/head_camera",
                "provenance": "mujoco_robot_head_camera_first_public_waypoint",
                "navigation_status": navigation.get("status") or "ok",
                "image_diagnostics": _image_diagnostics(fpv_path),
                "camera_diagnostics": (robot_views.get("camera_diagnostics") or {})
                .get("views", {})
                .get("fpv", {}),
            },
            "map": {
                "path": map_path.name,
                "view": "semantic_map_aligned_preview",
                "provenance": "scene_state_semantic_overlay_shared_bounds",
                "alignment_status": "aligned_to_topdown_scene_bounds",
                "semantic_map_fallback": False,
                "scene_alignment": scene_alignment,
                "image_diagnostics": _image_diagnostics(map_path),
            },
            "chase": {
                "path": chase_path.name,
                "view": "chase_camera",
                "waypoint_id": str(chase_waypoint.get("waypoint_id") or ""),
                "camera": "robot_0/camera_follower",
                "provenance": "mujoco_robot_camera_follower_public_waypoint",
                "navigation_status": chase_navigation.get("status") or "ok",
                "selection_policy": "first_reviewable_public_waypoint_fallback_to_first",
                "selection_status": chase_selection.get("status"),
                "candidate_count_evaluated": chase_selection.get("candidate_count_evaluated"),
                "image_diagnostics": _image_diagnostics(chase_path),
                "camera_diagnostics": (chase_robot_views.get("camera_diagnostics") or {})
                .get("views", {})
                .get("chase", {}),
            },
            "topdown": {
                "path": topdown_path.name,
                "view": "topdown_scene_render",
                "waypoint_id": str(waypoint.get("waypoint_id") or ""),
                "camera_model": topdown_request.get("camera_model"),
                "camera_pose": {
                    "eye": topdown_view.get("eye"),
                    "target": topdown_view.get("target"),
                    "azimuth": topdown_view.get("azimuth"),
                    "elevation": topdown_view.get("elevation"),
                    "distance": topdown_view.get("distance"),
                },
                "provenance": "mujoco_camera_control_canonical_eye_target",
                "alignment_status": "mujoco_scene_rendered",
                "scene_alignment": scene_alignment,
                "semantic_map_fallback": False,
                "image_diagnostics": _image_diagnostics(topdown_path),
            },
        },
    }


def _select_chase_preview(
    *,
    contract: RealWorldCleanupContract,
    backend: MolmoSpacesSubprocessBackend,
    run_dir: Path,
    width: int,
    height: int,
    first_waypoint: dict[str, Any],
    first_navigation: dict[str, Any],
    first_robot_views: dict[str, Any],
    first_chase_path: Path,
    candidate_waypoints: list[dict[str, Any]],
) -> dict[str, Any]:
    first_diagnostics = _image_diagnostics(first_chase_path)
    if first_diagnostics["visual_status"] == "reviewable":
        return {
            "status": "first_waypoint_reviewable",
            "path": first_chase_path,
            "waypoint": first_waypoint,
            "navigation": first_navigation,
            "robot_views": first_robot_views,
            "candidate_count_evaluated": 1,
        }

    candidate_count = 1
    for index, waypoint in enumerate(candidate_waypoints, start=2):
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if not waypoint_id:
            continue
        navigation = contract.navigate_to_waypoint(waypoint_id)
        candidate_count += 1
        if not navigation.get("ok"):
            continue
        robot_views = backend.write_robot_views_with_resolution(
            run_dir / "robot_views",
            label=f"preview_chase_candidate_{index:02d}",
            width=width,
            height=height,
        )
        chase_path = Path(str((robot_views.get("views") or {}).get("chase") or ""))
        if not chase_path.is_file():
            continue
        if _image_diagnostics(chase_path)["visual_status"] != "reviewable":
            continue
        return {
            "status": "alternate_waypoint_reviewable",
            "path": chase_path,
            "waypoint": dict(waypoint),
            "navigation": navigation,
            "robot_views": robot_views,
            "candidate_count_evaluated": candidate_count,
        }

    return {
        "status": "fallback_first_waypoint_low_detail",
        "path": first_chase_path,
        "waypoint": first_waypoint,
        "navigation": first_navigation,
        "robot_views": first_robot_views,
        "candidate_count_evaluated": candidate_count,
    }


def _topdown_camera_request(
    state: dict[str, Any],
    *,
    width: int,
    height: int,
    alignment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    alignment = alignment or _scene_alignment(state, width=width, height=height)
    center = alignment["center"]
    vertical_fov_deg = 45.0
    camera_distance = (
        float(alignment["span_y_m"]) / (2.0 * math.tan(math.radians(vertical_fov_deg / 2.0))) * 1.04
    )
    camera_height = float(center[2]) + max(1.0, camera_distance)
    return canonical_scene_camera_control_request(
        [
            {
                "view_id": "topdown_scene",
                "label": "Top-down Scene View",
                "camera_basis": "whole_scene_true_topdown_aligned_to_semantic_map",
                "eye": [center[0], center[1], camera_height],
                "target": center,
                "azimuth": 90.0,
                "scene_alignment": alignment,
                "calibration_status": "mujoco_scene_rendered",
            }
        ],
        lens={"vertical_fov_deg": vertical_fov_deg, "focal_length_mm": 24.0},
        width=width,
        height=height,
    )


def _render_semantic_map_preview(
    state: dict[str, Any],
    *,
    metric_map: dict[str, Any],
    alignment: dict[str, Any],
    world_label: str,
    width: int,
    height: int,
) -> Image.Image:
    image = Image.new("RGB", (width, height), (246, 248, 247))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, height - 1), outline=(190, 201, 195), width=2)

    room_fills = [
        (229, 217, 238),
        (215, 235, 238),
        (219, 238, 227),
        (221, 230, 244),
        (241, 229, 213),
    ]
    room_names = _semantic_room_names(state)
    for index, outline in enumerate(state.get("room_outlines") or []):
        if not isinstance(outline, dict):
            continue
        rect = _outline_screen_rect(outline, alignment, width=width, height=height)
        if rect is None:
            continue
        left, top, right, bottom = rect
        fill = room_fills[index % len(room_fills)]
        draw.rectangle((left, top, right, bottom), fill=fill, outline=(111, 124, 138), width=2)
        label = room_names.get(str(outline.get("room_id") or "")) or str(
            outline.get("label") or "Room"
        )
        label_x = int(round((left + right) / 2))
        label_y = int(round((top + bottom) / 2))
        draw.text((label_x - max(14, len(label) * 3), label_y - 6), label, fill=(45, 55, 72))

    for waypoint in _public_waypoints(metric_map):
        if not _is_vec((waypoint.get("x"), waypoint.get("y")), 2):
            continue
        x, y = _project_to_aligned_preview(
            float(waypoint.get("x") or 0.0),
            float(waypoint.get("y") or 0.0),
            alignment,
            width=width,
            height=height,
        )
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(99, 102, 241))

    for receptacle in (state.get("receptacles") or {}).values():
        if not isinstance(receptacle, dict) or not _is_vec(receptacle.get("position"), 2):
            continue
        x, y = _project_to_aligned_preview(
            float(receptacle["position"][0]),
            float(receptacle["position"][1]),
            alignment,
            width=width,
            height=height,
        )
        draw.rounded_rectangle((x - 5, y - 5, x + 5, y + 5), radius=3, fill=(86, 103, 140))

    selected_object_ids = set(str(item) for item in state.get("selected_object_ids") or [])
    for object_id, obj in (state.get("objects") or {}).items():
        if not isinstance(obj, dict) or not _is_vec(obj.get("position"), 2):
            continue
        x, y = _project_to_aligned_preview(
            float(obj["position"][0]),
            float(obj["position"][1]),
            alignment,
            width=width,
            height=height,
        )
        color = (239, 68, 68) if str(object_id) in selected_object_ids else (245, 158, 11)
        radius = 5 if str(object_id) in selected_object_ids else 3
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    trajectory = [
        item
        for item in state.get("robot_trajectory") or []
        if isinstance(item, dict) and "x" in item and "y" in item
    ]
    projected_path = [
        _project_to_aligned_preview(
            float(pose["x"]),
            float(pose["y"]),
            alignment,
            width=width,
            height=height,
        )
        for pose in trajectory
    ]
    if len(projected_path) >= 2:
        draw.line(projected_path, fill=(37, 99, 235), width=4)
    for index, (x, y) in enumerate(projected_path):
        radius = 8 if index == len(projected_path) - 1 else 4
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(37, 99, 235))
    if trajectory:
        pose = trajectory[-1]
        x, y = projected_path[-1]
        heading = float(pose.get("theta") or 0.0)
        tip = (int(round(x + math.cos(heading) * 20)), int(round(y - math.sin(heading) * 20)))
        left = (
            int(round(x + math.cos(heading + 2.45) * 12)),
            int(round(y - math.sin(heading + 2.45) * 12)),
        )
        right = (
            int(round(x + math.cos(heading - 2.45) * 12)),
            int(round(y - math.sin(heading - 2.45) * 12)),
        )
        draw.polygon([tip, left, right], fill=(15, 23, 42))

    draw.rectangle((18, 16, 280, 56), fill=(246, 248, 247))
    draw.text((28, 24), world_label, fill=(31, 41, 55))
    draw.text((28, 40), "Semantic map aligned to top-down bounds", fill=(92, 105, 118))
    return image


def _semantic_room_names(state: dict[str, Any]) -> dict[str, str]:
    room_ids = [str(item.get("room_id") or "") for item in state.get("room_outlines") or []]
    if len(room_ids) == 2:
        return {room_ids[0]: "Bedroom", room_ids[1]: "Bathroom"}
    if len(room_ids) == 4:
        return {
            room_ids[0]: "Bedroom",
            room_ids[1]: "Bathroom",
            room_ids[2]: "Kitchen",
            room_ids[3]: "Living",
        }
    return {}


def _outline_screen_rect(
    outline: dict[str, Any],
    alignment: dict[str, Any],
    *,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    center = outline.get("center")
    half_extents = outline.get("half_extents")
    if not _is_vec(center, 2) or not _is_vec(half_extents, 2):
        return None
    x1, y1 = _project_to_aligned_preview(
        float(center[0]) - float(half_extents[0]),
        float(center[1]) - float(half_extents[1]),
        alignment,
        width=width,
        height=height,
    )
    x2, y2 = _project_to_aligned_preview(
        float(center[0]) + float(half_extents[0]),
        float(center[1]) + float(half_extents[1]),
        alignment,
        width=width,
        height=height,
    )
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def _project_to_aligned_preview(
    x: float,
    y: float,
    alignment: dict[str, Any],
    *,
    width: int,
    height: int,
) -> tuple[int, int]:
    bounds = alignment["bounds"]
    min_x = float(bounds["min_x"])
    max_x = float(bounds["max_x"])
    min_y = float(bounds["min_y"])
    max_y = float(bounds["max_y"])
    px = (float(x) - min_x) / max(max_x - min_x, 0.001) * (width - 1)
    py = (1.0 - (float(y) - min_y) / max(max_y - min_y, 0.001)) * (height - 1)
    return int(round(px)), int(round(py))


def _scene_alignment(state: dict[str, Any], *, width: int, height: int) -> dict[str, Any]:
    points = _scene_points(state)
    if not points:
        min_x = min_y = -0.5
        max_x = max_y = 0.5
    else:
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
    pad = 0.35
    min_x -= pad
    max_x += pad
    min_y -= pad
    max_y += pad
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    target_aspect = max(float(width) / max(float(height), 1.0), 0.001)
    current_aspect = span_x / span_y
    if current_aspect < target_aspect:
        expanded_span_x = span_y * target_aspect
        extra = (expanded_span_x - span_x) / 2.0
        min_x -= extra
        max_x += extra
        span_x = expanded_span_x
    elif current_aspect > target_aspect:
        expanded_span_y = span_x / target_aspect
        extra = (expanded_span_y - span_y) / 2.0
        min_y -= extra
        max_y += extra
        span_y = expanded_span_y
    center = [(min_x + max_x) / 2.0, (min_y + max_y) / 2.0, 0.4]
    return {
        "schema": "operator_console_scene_alignment_v1",
        "bounds": {
            "min_x": round(min_x, 6),
            "max_x": round(max_x, 6),
            "min_y": round(min_y, 6),
            "max_y": round(max_y, 6),
        },
        "center": [round(float(value), 6) for value in center],
        "span_x_m": round(float(span_x), 6),
        "span_y_m": round(float(span_y), 6),
        "camera_span_m": round(float(max(span_x, span_y)), 6),
        "screen_coordinate_convention": "screen_x_world_positive_x_screen_y_world_negative_y",
        "topdown_azimuth_deg": 90.0,
    }


def _scene_points(state: dict[str, Any]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for outline in state.get("room_outlines") or []:
        if not isinstance(outline, dict):
            continue
        center = outline.get("center")
        half_extents = outline.get("half_extents")
        if not _is_vec(center, 2) or not _is_vec(half_extents, 2):
            continue
        points.append(
            (
                float(center[0]) - float(half_extents[0]),
                float(center[1]) - float(half_extents[1]),
            )
        )
        points.append(
            (
                float(center[0]) + float(half_extents[0]),
                float(center[1]) + float(half_extents[1]),
            )
        )
    for collection_key in ("objects", "receptacles"):
        collection = state.get(collection_key)
        if not isinstance(collection, dict):
            continue
        for item in collection.values():
            if not isinstance(item, dict) or not _is_vec(item.get("position"), 2):
                continue
            position = item["position"]
            points.append((float(position[0]), float(position[1])))
    for pose in state.get("robot_trajectory") or []:
        if not isinstance(pose, dict) or "x" not in pose or "y" not in pose:
            continue
        points.append((float(pose["x"]), float(pose["y"])))
    return points


def _scene_center_and_span(state: dict[str, Any]) -> tuple[list[float], float]:
    alignment = _scene_alignment(state, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT)
    return list(alignment["center"]), float(alignment["camera_span_m"])


def _first_public_waypoint(metric_map: dict[str, Any]) -> dict[str, Any]:
    waypoints = _public_waypoints(metric_map)
    if not waypoints:
        raise ValueError("metric map does not include public inspection waypoints")
    first = waypoints[0]
    if not first.get("waypoint_id"):
        raise ValueError("first public inspection waypoint is invalid")
    return first


def _public_waypoints(metric_map: dict[str, Any]) -> list[dict[str, Any]]:
    waypoints = metric_map.get("inspection_waypoints")
    if not isinstance(waypoints, list):
        return []
    return [
        dict(item)
        for item in waypoints
        if isinstance(item, dict) and str(item.get("waypoint_id") or "")
    ]


def _selected_world_ids(raw_world_ids: list[str]) -> tuple[str, ...]:
    return tuple(raw_world_ids or MOLMOSPACES_CONSOLE_WORLD_IDS)


def _molmospaces_scene_index(world_id: str) -> int:
    prefix = "molmospaces/val_"
    if not world_id.startswith(prefix):
        raise ValueError(f"unsupported preview world: {world_id}")
    return int(world_id.removeprefix(prefix))


def _world_slug(world_id: str) -> str:
    return world_id.replace("/", "-")


def _is_vec(value: Any, min_length: int) -> bool:
    return isinstance(value, (list, tuple)) and len(value) >= min_length


def _image_diagnostics(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        stat = ImageStat.Stat(rgb)
        extrema = rgb.getextrema()
    channel_ranges = [float(high) - float(low) for low, high in extrema]
    max_channel_range = max(channel_ranges)
    max_stddev = max(float(value) for value in stat.stddev)
    visual_status = "low_detail" if max_channel_range <= 8.0 and max_stddev <= 2.0 else "reviewable"
    return {
        "schema": "operator_console_preview_image_diagnostics_v1",
        "width": int(rgb.width),
        "height": int(rgb.height),
        "mean_rgb": [round(float(value), 3) for value in stat.mean],
        "channel_extrema_rgb": [[int(low), int(high)] for low, high in extrema],
        "max_channel_range": round(max_channel_range, 3),
        "max_stddev": round(max_stddev, 3),
        "visual_status": visual_status,
    }


def _utc_timestamp() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
