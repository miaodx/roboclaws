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

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageStat

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
from roboclaws.launch.scene_sampler import parse_molmospaces_world_id  # noqa: E402
from roboclaws.launch.worlds import MOLMOSPACES_CONSOLE_WORLD_IDS  # noqa: E402
from scripts.operator_console.semantic_map_preview import (  # noqa: E402
    render_semantic_map_preview as _render_semantic_map_preview,
)
from scripts.operator_console.semantic_map_preview import (  # noqa: E402
    semantic_map_preview_projection_summary as _semantic_map_preview_projection_summary,
)

PREVIEW_METADATA_SCHEMA = "operator_console_scene_preview_v1"
DEFAULT_OUTPUT_DIR = Path("roboclaws/operator_console/static/previews")
DEFAULT_WORK_DIR = Path("output/operator-console-scene-previews")
DEFAULT_WIDTH = 900
DEFAULT_HEIGHT = 560
B1_MAP12_WORLD_ID = "b1-map12"
B1_MAP_BUNDLE_DIR = Path("assets/maps/b1-map12-room-semantics")
B1_SCENE_USD_PATH = Path(
    "data/robot-data-lab/scene-engine/data/"
    "2rd_floor_seperated/storey_1/configuration/scene_base.usd"
)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = render_previews(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "success" else 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render operator-console scene previews. MolmoSpaces previews are real "
            "MuJoCo renders: Raw FPV is captured from the first public waypoint, "
            "Chase is the robot follower camera, and Top-down is a separate scene "
            "camera render rather than a semantic-map fallback. B1 / Map 12 "
            "previews are static digital-twin overview assets generated from the "
            "committed map bundle and scene semantic overlay so the console can "
            "show the experimental digital twin before Isaac starts."
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
        if world_id == B1_MAP12_WORLD_ID:
            result = render_b1_map12_preview(
                output_dir=output_dir,
                width=max(1, int(args.width)),
                height=max(1, int(args.height)),
                skip_existing=bool(args.skip_existing),
            )
        else:
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
    scene_ref = _molmospaces_scene_ref(world_id)
    scene_index = scene_ref.scene_index
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
            "scene_source": scene_ref.scene_source,
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
        scene_source=scene_ref.scene_source,
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
                "scene_source": scene_ref.scene_source,
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
                "scene_source": scene_ref.scene_source,
                "scene_index": scene_index,
                "status": "fpv_missing",
                "waypoint_id": waypoint.get("waypoint_id"),
                "views": views,
            }
        if not raw_chase.is_file():
            return {
                "world_id": world_id,
                "scene_source": scene_ref.scene_source,
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
        semantic_projection = _semantic_map_preview_projection_summary(
            state,
            metric_map=metric_map,
            alignment=scene_alignment,
        )

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
                "scene_source": scene_ref.scene_source,
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
            scene_source=scene_ref.scene_source,
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
            semantic_projection=semantic_projection,
        )
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "world_id": world_id,
            "scene_source": scene_ref.scene_source,
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


def render_b1_map12_preview(
    *,
    output_dir: Path,
    width: int,
    height: int,
    skip_existing: bool = False,
) -> dict[str, Any]:
    slug = _world_slug(B1_MAP12_WORLD_ID)
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
        and metadata_path.exists()
    ):
        return {
            "world_id": B1_MAP12_WORLD_ID,
            "scene_source": "b1-gaussian-digital-twin",
            "status": "skipped",
            "fpv": str(fpv_path),
            "map": str(map_path),
            "chase": str(chase_path),
            "topdown": str(topdown_path),
            "metadata": str(metadata_path),
        }

    map_bundle = B1_MAP_BUNDLE_DIR
    if not map_bundle.is_dir():
        return {
            "world_id": B1_MAP12_WORLD_ID,
            "scene_source": "b1-gaussian-digital-twin",
            "status": "map_bundle_missing",
            "map_bundle": str(map_bundle),
        }
    required_assets = (
        map_bundle / "preview.png",
        map_bundle / "room_semantic_topdown.png",
        map_bundle / "semantics.json",
        map_bundle / "room_semantic_overlay.json",
    )
    missing = [str(path) for path in required_assets if not path.is_file()]
    if missing:
        return {
            "world_id": B1_MAP12_WORLD_ID,
            "scene_source": "b1-gaussian-digital-twin",
            "status": "map_bundle_incomplete",
            "missing": missing,
        }

    semantics = json.loads((map_bundle / "semantics.json").read_text(encoding="utf-8"))
    overlay = json.loads((map_bundle / "room_semantic_overlay.json").read_text(encoding="utf-8"))
    map_image = _fit_preview_image(
        Image.open(map_bundle / "preview.png"), width=width, height=height
    )
    topdown_image = _fit_preview_image(
        Image.open(map_bundle / "room_semantic_topdown.png"),
        width=width,
        height=height,
    )
    map_image.save(map_path)
    topdown_image.save(topdown_path)
    _render_b1_room_overview(
        semantics=semantics,
        overlay=overlay,
        base_image=topdown_image,
        output_path=fpv_path,
        width=width,
        height=height,
        variant="room_overview",
    )
    _render_b1_scene_evidence_overview(
        semantics=semantics,
        overlay=overlay,
        base_image=map_image,
        output_path=chase_path,
        width=width,
        height=height,
    )
    metadata = _b1_map12_preview_metadata(
        width=width,
        height=height,
        fpv_path=fpv_path,
        map_path=map_path,
        chase_path=chase_path,
        topdown_path=topdown_path,
        semantics=semantics,
        overlay=overlay,
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "world_id": B1_MAP12_WORLD_ID,
        "scene_source": "b1-gaussian-digital-twin",
        "status": "rendered",
        "fpv": str(fpv_path),
        "map": str(map_path),
        "chase": str(chase_path),
        "topdown": str(topdown_path),
        "metadata": str(metadata_path),
    }


def _preview_metadata(
    *,
    world_id: str,
    scene_source: str,
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
    semantic_projection: dict[str, Any] | None = None,
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
        "scene_source": scene_source,
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
                "semantic_projection": semantic_projection or {},
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


def _b1_map12_preview_metadata(
    *,
    width: int,
    height: int,
    fpv_path: Path,
    map_path: Path,
    chase_path: Path,
    topdown_path: Path,
    semantics: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    rooms = semantics.get("rooms") if isinstance(semantics.get("rooms"), list) else []
    waypoints = (
        semantics.get("inspection_waypoints")
        if isinstance(semantics.get("inspection_waypoints"), list)
        else []
    )
    correspondence = (
        overlay.get("scene_map_correspondence_v1")
        if isinstance(overlay.get("scene_map_correspondence_v1"), list)
        else []
    )
    return {
        "schema": PREVIEW_METADATA_SCHEMA,
        "generated_at": _utc_timestamp(),
        "world_id": B1_MAP12_WORLD_ID,
        "backend": "isaaclab",
        "renderer": "static_b1_map12_digital_twin_overview",
        "scene_source": "b1-gaussian-digital-twin",
        "scene_usd_path": str(B1_SCENE_USD_PATH),
        "map_bundle": str(B1_MAP_BUNDLE_DIR),
        "render_resolution": {"width": width, "height": height},
        "views": {
            "fpv": {
                "path": fpv_path.name,
                "view": "digital_twin_room_overview",
                "provenance": "b1_map12_room_semantic_overlay_static_overview",
                "camera_semantics": "overview_slot_not_live_robot_camera",
                "semantic_map_fallback": False,
                "image_diagnostics": _image_diagnostics(fpv_path),
            },
            "map": {
                "path": map_path.name,
                "view": "source_map_preview",
                "provenance": "b1_map12_room_semantics_preview_png",
                "alignment_status": str(
                    (semantics.get("spatial_contract") or {}).get("alignment_status") or "candidate"
                ),
                "display_frame": semantics.get("display_frame"),
                "semantic_map_fallback": False,
                "image_diagnostics": _image_diagnostics(map_path),
            },
            "chase": {
                "path": chase_path.name,
                "view": "digital_twin_scene_evidence_overview",
                "provenance": "b1_map12_scene_map_correspondence_static_overview",
                "camera_semantics": "overview_slot_not_live_robot_camera",
                "correspondence_schema": overlay.get("scene_map_correspondence_schema"),
                "correspondence_count": len(correspondence),
                "semantic_map_fallback": False,
                "image_diagnostics": _image_diagnostics(chase_path),
            },
            "topdown": {
                "path": topdown_path.name,
                "view": "semantic_room_topdown",
                "provenance": "b1_map12_room_semantic_topdown_png",
                "alignment_status": str(
                    (semantics.get("spatial_contract") or {}).get("alignment_status") or "candidate"
                ),
                "semantic_map_fallback": False,
                "room_count": len(rooms),
                "inspection_waypoint_count": len(waypoints),
                "image_diagnostics": _image_diagnostics(topdown_path),
            },
        },
    }


def _fit_preview_image(image: Image.Image, *, width: int, height: int) -> Image.Image:
    source = image.convert("RGB")
    source.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), (228, 231, 235))
    x = (width - source.width) // 2
    y = (height - source.height) // 2
    canvas.paste(source, (x, y))
    return canvas


def _render_b1_room_overview(
    *,
    semantics: dict[str, Any],
    overlay: dict[str, Any],
    base_image: Image.Image,
    output_path: Path,
    width: int,
    height: int,
    variant: str,
) -> None:
    image = _map_canvas(base_image, width=width, height=height)
    draw = ImageDraw.Draw(image, "RGBA")
    transform = _map_transform(semantics, width=width, height=height)
    room_colors = {
        "meeting_room": (99, 102, 241, 58),
        "kitchen": (16, 185, 129, 62),
        "living_room": (245, 158, 11, 58),
        "corridor": (14, 165, 233, 54),
        "storage_room": (168, 85, 247, 54),
    }
    outline_colors = {
        "meeting_room": (79, 70, 229, 180),
        "kitchen": (5, 150, 105, 180),
        "living_room": (217, 119, 6, 180),
        "corridor": (2, 132, 199, 180),
        "storage_room": (126, 34, 206, 180),
    }
    rooms = [item for item in semantics.get("rooms") or [] if isinstance(item, dict)]
    for room in rooms:
        polygon = _room_polygon(room)
        if len(polygon) < 3:
            continue
        category = str(room.get("category") or "")
        points = [transform(x, y) for x, y in polygon]
        draw.polygon(points, fill=room_colors.get(category, (100, 116, 139, 46)))
        draw.line(
            [*points, points[0]],
            fill=outline_colors.get(category, (71, 85, 105, 170)),
            width=2,
        )
        label = str(room.get("room_label") or room.get("room_id") or "")
        cx, cy = _polygon_center(polygon)
        _draw_label(draw, transform(cx, cy), label, fill=(17, 24, 39, 230))

    for waypoint in semantics.get("inspection_waypoints") or []:
        if not isinstance(waypoint, dict):
            continue
        point = _xy(waypoint)
        if point is None:
            continue
        px, py = transform(*point)
        draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=(5, 150, 105, 230))

    _draw_b1_overview_header(
        draw,
        width=width,
        title="B1 / Map 12 Digital Twin",
        subtitle=f"{len(rooms)} semantic rooms, static overview",
    )
    _draw_b1_overview_footer(
        draw,
        width=width,
        height=height,
        text=f"{variant}: generated from room_semantic_overlay.json and semantics.json",
    )
    image.save(output_path)


def _render_b1_scene_evidence_overview(
    *,
    semantics: dict[str, Any],
    overlay: dict[str, Any],
    base_image: Image.Image,
    output_path: Path,
    width: int,
    height: int,
) -> None:
    image = _map_canvas(base_image, width=width, height=height)
    draw = ImageDraw.Draw(image, "RGBA")
    transform = _map_transform(semantics, width=width, height=height)
    correspondences = [
        item for item in overlay.get("scene_map_correspondence_v1") or [] if isinstance(item, dict)
    ]
    by_partition = {
        str(item.get("asset_partition_id") or ""): item
        for item in correspondences
        if isinstance(item, dict)
    }
    for index, room in enumerate(
        item for item in semantics.get("rooms") or [] if isinstance(item, dict)
    ):
        polygon = _room_polygon(room)
        if len(polygon) < 3:
            continue
        points = [transform(x, y) for x, y in polygon]
        alpha = 36 + (index % 3) * 18
        draw.polygon(points, fill=(15, 23, 42, alpha))
        draw.line([*points, points[0]], fill=(15, 23, 42, 160), width=2)
        cx, cy = _polygon_center(polygon)
        match = by_partition.get(str(room.get("asset_partition_id") or ""))
        status = str((match or {}).get("alignment_status") or room.get("alignment_status") or "")
        label = str(room.get("asset_partition_id") or room.get("room_id") or "")
        _draw_label(
            draw,
            transform(cx, cy),
            f"{label} / {status}",
            fill=(15, 23, 42, 235),
            background=(255, 255, 255, 210),
        )

    fixtures = [item for item in semantics.get("fixtures") or [] if isinstance(item, dict)]
    for fixture in fixtures:
        pose = fixture.get("pose")
        if not isinstance(pose, dict):
            continue
        point = _xy(pose)
        if point is None:
            continue
        px, py = transform(*point)
        draw.rounded_rectangle(
            (px - 5, py - 5, px + 5, py + 5),
            radius=2,
            fill=(180, 83, 9, 230),
        )

    _draw_b1_overview_header(
        draw,
        width=width,
        title="Scene Correspondence",
        subtitle=f"{len(correspondences)} partitions, {len(fixtures)} public fixtures",
    )
    _draw_b1_overview_footer(
        draw,
        width=width,
        height=height,
        text="Static digital-twin evidence view, not a live chase camera frame",
    )
    image.save(output_path)


def _map_canvas(base_image: Image.Image, *, width: int, height: int) -> Image.Image:
    image = _fit_preview_image(base_image, width=width, height=height)
    image = ImageEnhance.Color(image).enhance(1.08)
    image = ImageEnhance.Contrast(image).enhance(1.07)
    return image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=4))


def _map_transform(semantics: dict[str, Any], *, width: int, height: int):
    points: list[tuple[float, float]] = []
    for room in semantics.get("rooms") or []:
        if isinstance(room, dict):
            points.extend(_room_polygon(room))
    for waypoint in semantics.get("inspection_waypoints") or []:
        if isinstance(waypoint, dict):
            point = _xy(waypoint)
            if point is not None:
                points.append(point)
    for fixture in semantics.get("fixtures") or []:
        if isinstance(fixture, dict) and isinstance(fixture.get("pose"), dict):
            point = _xy(fixture["pose"])
            if point is not None:
                points.append(point)
    if not points:
        points = [(-1.0, -1.0), (1.0, 1.0)]
    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    min_y = min(y for _, y in points)
    max_y = max(y for _, y in points)
    pad_x = max((max_x - min_x) * 0.12, 0.5)
    pad_y = max((max_y - min_y) * 0.12, 0.5)
    min_x -= pad_x
    max_x += pad_x
    min_y -= pad_y
    max_y += pad_y
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    plot_left = width * 0.08
    plot_right = width * 0.92
    plot_top = height * 0.16
    plot_bottom = height * 0.88
    scale = min((plot_right - plot_left) / span_x, (plot_bottom - plot_top) / span_y)
    offset_x = (width - span_x * scale) / 2.0
    offset_y = plot_top + ((plot_bottom - plot_top) - span_y * scale) / 2.0

    def transform(x: float, y: float) -> tuple[float, float]:
        return (
            offset_x + (x - min_x) * scale,
            offset_y + (max_y - y) * scale,
        )

    return transform


def _room_polygon(room: dict[str, Any]) -> list[tuple[float, float]]:
    polygon = room.get("polygon")
    if not isinstance(polygon, list):
        return []
    points = []
    for item in polygon:
        if not isinstance(item, dict):
            continue
        point = _xy(item)
        if point is not None:
            points.append(point)
    return points


def _xy(item: dict[str, Any]) -> tuple[float, float] | None:
    try:
        return float(item["x"]), float(item["y"])
    except (KeyError, TypeError, ValueError):
        return None


def _polygon_center(points: list[tuple[float, float]]) -> tuple[float, float]:
    if not points:
        return (0.0, 0.0)
    return (
        sum(x for x, _ in points) / len(points),
        sum(y for _, y in points) / len(points),
    )


def _draw_label(
    draw: ImageDraw.ImageDraw,
    point: tuple[float, float],
    text: str,
    *,
    fill: tuple[int, int, int, int],
    background: tuple[int, int, int, int] = (255, 255, 255, 185),
) -> None:
    if not text:
        return
    x, y = point
    text = text[:42]
    bbox = draw.textbbox((x, y), text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    rect = (
        x - text_width / 2 - 5,
        y - text_height / 2 - 4,
        x + text_width / 2 + 5,
        y + text_height / 2 + 4,
    )
    draw.rounded_rectangle(rect, radius=4, fill=background)
    draw.text((x - text_width / 2, y - text_height / 2 - 1), text, fill=fill)


def _draw_b1_overview_header(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    title: str,
    subtitle: str,
) -> None:
    draw.rounded_rectangle((18, 18, min(width - 18, 472), 74), radius=8, fill=(255, 255, 255, 230))
    draw.text((34, 30), title, fill=(15, 23, 42, 245))
    draw.text((34, 52), subtitle, fill=(71, 85, 105, 235))


def _draw_b1_overview_footer(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    height: int,
    text: str,
) -> None:
    margin = 18
    y = height - 44
    draw.rounded_rectangle(
        (margin, y, min(width - margin, 640), height - 16),
        radius=8,
        fill=(255, 255, 255, 218),
    )
    draw.text((margin + 16, y + 10), text[:92], fill=(51, 65, 85, 238))


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
    return tuple(raw_world_ids or (*MOLMOSPACES_CONSOLE_WORLD_IDS, B1_MAP12_WORLD_ID))


def _molmospaces_scene_index(world_id: str) -> int:
    return _molmospaces_scene_ref(world_id).scene_index


def _molmospaces_scene_ref(world_id: str):
    return parse_molmospaces_world_id(world_id)


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
