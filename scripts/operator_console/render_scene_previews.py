#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

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
            "from the first public waypoint, and Top-down is a separate scene "
            "camera render rather than a semantic-map fallback."
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
        help="Do not render a world when both FPV and top-down preview files already exist.",
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
    topdown_path = output_dir / f"{slug}-topdown.png"
    metadata_path = output_dir / f"{slug}-preview.json"
    if skip_existing and fpv_path.exists() and topdown_path.exists():
        return {
            "world_id": world_id,
            "scene_index": scene_index,
            "status": "skipped",
            "fpv": str(fpv_path),
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
        waypoint = _first_public_waypoint(contract.metric_map())
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
        if not raw_fpv.is_file():
            return {
                "world_id": world_id,
                "scene_index": scene_index,
                "status": "fpv_missing",
                "waypoint_id": waypoint.get("waypoint_id"),
                "views": views,
            }

        state_path = run_dir / "backend" / "molmospaces_backend_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        topdown_request = _topdown_camera_request(state, width=width, height=height)
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

        shutil.copyfile(raw_fpv, fpv_path)
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
            topdown_path=topdown_path,
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
    topdown_path: Path,
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
            "topdown": {
                "path": topdown_path.name,
                "view": "topdown_scene_render",
                "waypoint_id": str(waypoint.get("waypoint_id") or ""),
                "camera_model": topdown_request.get("camera_model"),
                "camera_pose": {
                    "eye": topdown_view.get("eye"),
                    "target": topdown_view.get("target"),
                    "up": [0.0, 1.0, 0.0],
                },
                "provenance": "mujoco_camera_control_canonical_eye_target",
                "alignment_status": "mujoco_scene_rendered",
                "semantic_map_fallback": False,
                "image_diagnostics": _image_diagnostics(topdown_path),
            },
        },
    }


def _topdown_camera_request(state: dict[str, Any], *, width: int, height: int) -> dict[str, Any]:
    center, span = _scene_center_and_span(state)
    camera_height = max(7.0, span * 1.25)
    return canonical_scene_camera_control_request(
        [
            {
                "view_id": "topdown_scene",
                "label": "Top-down Scene View",
                "camera_basis": "whole_scene_true_topdown",
                "eye": [center[0], center[1], camera_height],
                "target": center,
                "up": [0.0, 1.0, 0.0],
                "calibration_status": "mujoco_scene_rendered",
            }
        ],
        width=width,
        height=height,
    )


def _scene_center_and_span(state: dict[str, Any]) -> tuple[list[float], float]:
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
    if not points:
        return [0.0, 0.0, 0.4], 1.0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        0.4,
    ], max(max(xs) - min(xs), max(ys) - min(ys), 1.0)


def _first_public_waypoint(metric_map: dict[str, Any]) -> dict[str, Any]:
    waypoints = metric_map.get("inspection_waypoints")
    if not isinstance(waypoints, list) or not waypoints:
        raise ValueError("metric map does not include public inspection waypoints")
    first = waypoints[0]
    if not isinstance(first, dict) or not first.get("waypoint_id"):
        raise ValueError("first public inspection waypoint is invalid")
    return dict(first)


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
