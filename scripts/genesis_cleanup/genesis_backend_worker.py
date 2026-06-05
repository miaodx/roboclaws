#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from PIL import Image, ImageDraw

from roboclaws.household.camera_control import (
    CAMERA_CONTROL_API_NAME,
    load_camera_control_request,
)
from roboclaws.household.color_management import apply_camera_color_profile
from roboclaws.household.genesis_backend import GENESIS_SCENE_CAMERA_VIEW_VARIANT

GENESIS_LANE_ID = "genesis-prepared-usd"
GENESIS_RENDER_LIGHTING_PROFILE = {
    "profile_id": "scene_probe_mujoco_headlight_fill_v1",
    "source": (
        "MuJoCo-headlight-inspired Genesis environment fill for prepared USD visual assets."
    ),
    "scene_key_light_direction": [-0.57735, 0.57735, -0.57735],
    "scene_key_light_frame": "molmospaces_scene_frame_v1",
    "mujoco_headlight_ambient": [0.35, 0.35, 0.35],
    "mujoco_headlight_diffuse": [0.4, 0.4, 0.4],
    "ambient_light": [0.37, 0.37, 0.37],
    "background_color": [0.04, 0.08, 0.12],
    "shadow": False,
    "lights": [
        {
            "type": "directional",
            "dir": [-1.0, -1.0, -1.0],
            "color": [1.0, 1.0, 1.0],
            "intensity": 3.0,
        },
        {
            "type": "directional",
            "dir": [1.0, 1.0, -0.6],
            "color": [1.0, 0.96, 0.9],
            "intensity": 0.8,
        },
        {
            "type": "directional",
            "dir": [0.0, -1.0, -0.35],
            "color": [0.9, 0.95, 1.0],
            "intensity": 0.45,
        },
    ],
}
GENESIS_COLOR_PROFILE_LUMINANCE_GAIN = 0.94
GENESIS_COLOR_PROFILE_RGB_GAIN = [1.04, 1.0, 0.97]
GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT = {
    "shadow_lift": 8.0,
    "shadow_floor": 135.0,
    "gamma": 1.1,
    "saturation": 1.0,
    "gain": 1.0,
}
GENESIS_COLOR_PROFILE_VIEW_TONE_ADJUSTMENT = {
    "room_01_room_2": {
        "shadow_lift": 8.0,
        "shadow_floor": 135.0,
        "gamma": 1.1,
        "saturation": 1.0,
        "gain": 1.2,
    },
}
GENESIS_COLOR_PROFILE_LUMINANCE_GAIN_SOURCE = (
    "Genesis materialized USD visual probe 2026-06-04; preserves existing "
    "candidate visual thresholds while matching MuJoCo review luminance."
)
GENESIS_COLOR_PROFILE_RGB_GAIN_SOURCE = (
    "Genesis materialized USD visual probe 2026-06-04; warms Genesis RGB response "
    "after USD diffuse-color texture baking."
)
GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT_SOURCE = (
    "Genesis baked-texture visual probe 2026-06-04; applies renderer-local shadow "
    "lift and gamma correction so room views remain reviewable after material "
    "albedo baking."
)
GENESIS_RUNTIME_POSE_OVERLAY_THRESHOLD_M = 0.25


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genesis scene-camera subprocess worker.")
    parser.add_argument("--state-path", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--run-dir", type=Path, required=True)
    init.add_argument("--scene-usd-path", type=Path, required=True)
    init.add_argument(
        "--runtime-mode",
        choices=("real", "fake"),
        default=os.environ.get("ROBOCLAWS_GENESIS_RUNTIME_MODE", "real"),
    )

    camera_views = subparsers.add_parser("camera_views")
    camera_views.add_argument("--output-dir", type=Path, required=True)
    camera_views.add_argument("--camera-request-path", type=Path, required=True)
    camera_views.add_argument("--render-width", type=int, required=True)
    camera_views.add_argument("--render-height", type=int, required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "init":
            result = init_state(args)
        else:
            state = read_state(args.state_path)
            if args.command == "camera_views":
                result = write_camera_views(args, state)
            else:  # pragma: no cover - argparse prevents this.
                raise ValueError(f"unsupported command: {args.command}")
    except Exception:
        traceback.print_exc()
        return 1
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result.get("ok") is True else 1


def init_state(args: argparse.Namespace) -> dict[str, Any]:
    args.run_dir.mkdir(parents=True, exist_ok=True)
    scene_usd_path = args.scene_usd_path
    runtime = _runtime_metadata(args.runtime_mode)
    if args.runtime_mode == "real" and not scene_usd_path.is_file():
        return _error(
            "init",
            "local_scene_usd_required",
            scene_usd=str(scene_usd_path),
        )
    scene_load = {
        "status": "fake_protocol" if args.runtime_mode == "fake" else "deferred_until_camera_views",
        "scene_usd": str(scene_usd_path),
        "usd_stage_loaded": False,
        "runtime_mode": args.runtime_mode,
    }
    state = {
        "schema": "genesis_backend_state_v1",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "run_dir": str(args.run_dir),
        "scene_usd": str(scene_usd_path),
        "runtime_mode": args.runtime_mode,
        "runtime": runtime,
        "scene_load": scene_load,
    }
    write_state(args.state_path, state)
    return {
        "ok": True,
        "tool": "init",
        "runtime": runtime,
        "scene_usd": str(scene_usd_path),
        "scene_load": scene_load,
    }


def write_camera_views(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    request = load_camera_control_request(
        args.camera_request_path,
        width=args.render_width,
        height=args.render_height,
    )
    runtime_mode = str(state.get("runtime_mode") or "real")
    if runtime_mode == "fake":
        return _write_fake_camera_views(args, state, request)
    return _write_real_camera_views(args, state, request)


def _write_real_camera_views(
    args: argparse.Namespace,
    state: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    scene_usd = Path(str(state.get("scene_usd") or ""))
    if not scene_usd.is_file():
        return _error("camera_views", "local_scene_usd_required", scene_usd=str(scene_usd))
    try:
        import genesis as gs
    except Exception as exc:
        return _error(
            "camera_views",
            "genesis_import_failed",
            message=str(exc),
            scene_usd=str(scene_usd),
        )
    runtime = _runtime_metadata(
        "real",
        genesis=gs,
        torch_module=sys.modules.get("torch"),
        numpy=np,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    resolution = request["render_resolution"]
    width = int(resolution["width"])
    height = int(resolution["height"])
    vertical_fov = float((request.get("lens") or {}).get("vertical_fov_deg") or 45.0)
    images: dict[str, str] = {}
    shapes: dict[str, list[int]] = {}
    views: list[dict[str, Any]] = []
    scene_load: dict[str, Any] = {
        "status": "success",
        "scene_usd": str(scene_usd),
        "usd_stage_loaded": True,
        "runtime_mode": "real",
        "genesis_import_mode": "native_usd_stage",
    }
    genesis_lighting_profile = _genesis_lighting_profile(request.get("lighting_profile") or {})

    try:
        if not getattr(gs, "_initialized", False):
            gs.init(backend=gs.cpu)
        scene = _genesis_scene(
            gs,
            width=width,
            height=height,
            vertical_fov=vertical_fov,
            lighting_profile=genesis_lighting_profile,
        )
        try:
            scene.add_stage(morph=gs.morphs.USD(file=str(scene_usd)))
        except Exception as exc:
            scene = _genesis_scene(
                gs,
                width=width,
                height=height,
                vertical_fov=vertical_fov,
                lighting_profile=genesis_lighting_profile,
            )
            scene_load = _add_prepared_usd_visual_fallback(
                scene=scene,
                gs=gs,
                scene_usd=scene_usd,
                output_dir=args.output_dir,
                native_error=exc,
                runtime_object_positions=_runtime_object_positions_from_request(request),
            )
        cameras = []
        for view in request.get("views") or []:
            if not isinstance(view, dict):
                continue
            eye = _vec3(view.get("eye"), fallback=[0.0, -3.0, 2.0])
            target = _vec3(view.get("target") or view.get("lookat"), fallback=[0.0, 0.0, 1.0])
            up = _vec3(view.get("up"), fallback=[0.0, 0.0, 1.0])
            cameras.append(
                (
                    view,
                    scene.add_camera(
                        res=(width, height),
                        pos=tuple(eye),
                        lookat=tuple(target),
                        up=tuple(up),
                        fov=vertical_fov,
                        GUI=False,
                    ),
                )
            )
        scene.build()
        color_profile = _genesis_color_profile(request.get("color_profile") or {})
        color_diagnostics: dict[str, dict[str, Any]] = {}
        for index, (view, camera) in enumerate(cameras, start=1):
            view_id = _safe_view_id(str(view.get("view_id") or f"view_{index:02d}"))
            rgb = camera.render(rgb=True, depth=False, segmentation=False, normal=False)[0]
            rgb_array = np.asarray(rgb)
            if rgb_array.ndim == 4:
                rgb_array = rgb_array[0]
            if rgb_array.dtype != np.uint8:
                rgb_array = np.clip(rgb_array, 0, 255).astype("uint8")
            rgb_array, color_diagnostic = apply_camera_color_profile(
                rgb_array,
                np=np,
                profile=color_profile,
                backend=GENESIS_LANE_ID,
                view_id=view_id,
            )
            image_path = args.output_dir / f"{view_id}.png"
            Image.fromarray(rgb_array).save(image_path)
            images[view_id] = str(image_path)
            shapes[view_id] = list(rgb_array.shape)
            color_diagnostics[view_id] = color_diagnostic
            views.append(_view_payload(view, image_path=image_path, shape=rgb_array.shape))
    except Exception as exc:
        return _error(
            "camera_views",
            "genesis_render_failed",
            message=str(exc),
            scene_usd=str(scene_usd),
        )

    return {
        "ok": True,
        "tool": "camera_views",
        "schema": "genesis_scene_camera_views_v1",
        "runtime": runtime,
        "view_variant": GENESIS_SCENE_CAMERA_VIEW_VARIANT,
        "visual_artifact_provenance": "genesis_real_rgb_render",
        "camera_control_api": CAMERA_CONTROL_API_NAME,
        "camera_request_schema": request.get("schema"),
        "calibration_status": request.get("calibration_status"),
        "lighting_profile": request.get("lighting_profile") or {},
        "lighting_diagnostics": {
            "status": "genesis_environment_fill_profile_applied",
            "source": "prepared_usd_plus_genesis_rasterizer",
            "requested_lighting_profile": request.get("lighting_profile") or {},
            "genesis_lighting_profile": genesis_lighting_profile,
        },
        "color_profile": color_profile,
        "color_management": {
            "status": "camera_color_profile_applied",
            "views": color_diagnostics,
        },
        "lens": request.get("lens") or {},
        "images": images,
        "shapes": shapes,
        "views": views,
        "scene_load": scene_load,
    }


def _genesis_scene(
    gs: Any,
    *,
    width: int,
    height: int,
    vertical_fov: float,
    lighting_profile: dict[str, Any] | None = None,
) -> Any:
    return gs.Scene(
        viewer_options=gs.options.ViewerOptions(
            res=(width, height),
            camera_pos=(0.0, -3.0, 2.0),
            camera_lookat=(0.0, 0.0, 1.0),
            camera_fov=vertical_fov,
        ),
        vis_options=_genesis_vis_options(gs, lighting_profile=lighting_profile),
        renderer=gs.renderers.Rasterizer(),
        show_viewer=False,
        show_FPS=False,
    )


def _genesis_vis_options(gs: Any, *, lighting_profile: dict[str, Any] | None = None) -> Any:
    profile = (
        lighting_profile if isinstance(lighting_profile, dict) else GENESIS_RENDER_LIGHTING_PROFILE
    )
    return gs.options.VisOptions(
        ambient_light=tuple(profile["ambient_light"]),
        background_color=tuple(profile["background_color"]),
        shadow=bool(profile["shadow"]),
        lights=[
            {
                "type": light["type"],
                "dir": tuple(light["dir"]),
                "color": tuple(light["color"]),
                "intensity": float(light["intensity"]),
            }
            for light in profile["lights"]
        ],
    )


def _genesis_lighting_profile(lighting_profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": str(
            lighting_profile.get("profile_id") or GENESIS_RENDER_LIGHTING_PROFILE["profile_id"]
        ),
        "source": str(lighting_profile.get("source") or GENESIS_RENDER_LIGHTING_PROFILE["source"]),
        "scene_key_light_direction": _vec3(
            lighting_profile.get("scene_key_light_direction"),
            fallback=GENESIS_RENDER_LIGHTING_PROFILE["scene_key_light_direction"],
        ),
        "scene_key_light_frame": str(
            lighting_profile.get("scene_key_light_frame")
            or GENESIS_RENDER_LIGHTING_PROFILE["scene_key_light_frame"]
        ),
        "mujoco_headlight_ambient": _vec3(
            lighting_profile.get("mujoco_headlight_ambient"),
            fallback=GENESIS_RENDER_LIGHTING_PROFILE["mujoco_headlight_ambient"],
        ),
        "mujoco_headlight_diffuse": _vec3(
            lighting_profile.get("mujoco_headlight_diffuse"),
            fallback=GENESIS_RENDER_LIGHTING_PROFILE["mujoco_headlight_diffuse"],
        ),
        "ambient_light": _vec3(
            lighting_profile.get("genesis_ambient_light"),
            fallback=GENESIS_RENDER_LIGHTING_PROFILE["ambient_light"],
        ),
        "background_color": _vec3(
            lighting_profile.get("genesis_background_color"),
            fallback=GENESIS_RENDER_LIGHTING_PROFILE["background_color"],
        ),
        "shadow": bool(
            lighting_profile.get("genesis_shadow", GENESIS_RENDER_LIGHTING_PROFILE["shadow"])
        ),
        "lights": _genesis_directional_lights(lighting_profile),
    }


def _genesis_directional_lights(lighting_profile: dict[str, Any]) -> list[dict[str, Any]]:
    raw_lights = (
        lighting_profile.get("genesis_directional_lights")
        if isinstance(lighting_profile.get("genesis_directional_lights"), list)
        else []
    )
    parsed: list[dict[str, Any]] = []
    for raw_light in raw_lights:
        if not isinstance(raw_light, dict):
            continue
        parsed.append(
            {
                "type": str(raw_light.get("type") or "directional"),
                "dir": _vec3(raw_light.get("dir"), fallback=[-1.0, -1.0, -1.0]),
                "color": _vec3(raw_light.get("color"), fallback=[1.0, 1.0, 1.0]),
                "intensity": float(raw_light.get("intensity", 1.0)),
            }
        )
    if not parsed:
        parsed = [dict(item) for item in GENESIS_RENDER_LIGHTING_PROFILE["lights"]]
    key_direction = _normalized_vec3(lighting_profile.get("scene_key_light_direction"))
    if key_direction is not None and parsed:
        parsed[0]["dir"] = key_direction
        parsed[0]["source"] = "scene_key_light_direction"
    return parsed


def _normalized_vec3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        vector = [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None
    magnitude = math.sqrt(sum(component * component for component in vector))
    if magnitude <= 0.0:
        return None
    return [component / magnitude for component in vector]


def _genesis_color_profile(color_profile: dict[str, Any]) -> dict[str, Any]:
    profile = json.loads(json.dumps(color_profile))
    gains = profile.get("backend_luminance_gain")
    if isinstance(gains, dict):
        profile["backend_luminance_gain"] = dict(gains)
    else:
        profile["backend_luminance_gain"] = {}
    profile["backend_luminance_gain"][GENESIS_LANE_ID] = GENESIS_COLOR_PROFILE_LUMINANCE_GAIN
    source = str(profile.get("backend_luminance_gain_source") or "")
    if GENESIS_COLOR_PROFILE_LUMINANCE_GAIN_SOURCE not in source:
        profile["backend_luminance_gain_source"] = (
            f"{source}; {GENESIS_COLOR_PROFILE_LUMINANCE_GAIN_SOURCE}"
            if source
            else GENESIS_COLOR_PROFILE_LUMINANCE_GAIN_SOURCE
        )
    profile["genesis_backend_luminance_gain_source"] = GENESIS_COLOR_PROFILE_LUMINANCE_GAIN_SOURCE
    rgb_gains = profile.get("backend_rgb_gain")
    if isinstance(rgb_gains, dict):
        profile["backend_rgb_gain"] = dict(rgb_gains)
    else:
        profile["backend_rgb_gain"] = {}
    profile["backend_rgb_gain"][GENESIS_LANE_ID] = list(GENESIS_COLOR_PROFILE_RGB_GAIN)
    rgb_source = str(profile.get("backend_rgb_gain_source") or "")
    if GENESIS_COLOR_PROFILE_RGB_GAIN_SOURCE not in rgb_source:
        profile["backend_rgb_gain_source"] = (
            f"{rgb_source}; {GENESIS_COLOR_PROFILE_RGB_GAIN_SOURCE}"
            if rgb_source
            else GENESIS_COLOR_PROFILE_RGB_GAIN_SOURCE
        )
    profile["genesis_backend_rgb_gain_source"] = GENESIS_COLOR_PROFILE_RGB_GAIN_SOURCE
    tone_adjustments = profile.get("backend_tone_adjustment")
    if isinstance(tone_adjustments, dict):
        profile["backend_tone_adjustment"] = dict(tone_adjustments)
    else:
        profile["backend_tone_adjustment"] = {}
    profile["backend_tone_adjustment"][GENESIS_LANE_ID] = dict(
        GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT
    )
    tone_source = str(profile.get("backend_tone_adjustment_source") or "")
    if GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT_SOURCE not in tone_source:
        profile["backend_tone_adjustment_source"] = (
            f"{tone_source}; {GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT_SOURCE}"
            if tone_source
            else GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT_SOURCE
        )
    profile["genesis_backend_tone_adjustment_source"] = GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT_SOURCE
    view_tone_adjustments = profile.get("backend_view_tone_adjustment")
    if isinstance(view_tone_adjustments, dict):
        profile["backend_view_tone_adjustment"] = dict(view_tone_adjustments)
    else:
        profile["backend_view_tone_adjustment"] = {}
    backend_view_tone_adjustments = profile["backend_view_tone_adjustment"].get(GENESIS_LANE_ID)
    if isinstance(backend_view_tone_adjustments, dict):
        profile["backend_view_tone_adjustment"][GENESIS_LANE_ID] = dict(
            backend_view_tone_adjustments
        )
    else:
        profile["backend_view_tone_adjustment"][GENESIS_LANE_ID] = {}
    profile["backend_view_tone_adjustment"][GENESIS_LANE_ID].update(
        json.loads(json.dumps(GENESIS_COLOR_PROFILE_VIEW_TONE_ADJUSTMENT))
    )
    view_tone_source = str(profile.get("backend_view_tone_adjustment_source") or "")
    if GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT_SOURCE not in view_tone_source:
        profile["backend_view_tone_adjustment_source"] = (
            f"{view_tone_source}; {GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT_SOURCE}"
            if view_tone_source
            else GENESIS_COLOR_PROFILE_TONE_ADJUSTMENT_SOURCE
        )
    return profile


def _add_prepared_usd_visual_fallback(
    *,
    scene: Any,
    gs: Any,
    scene_usd: Path,
    output_dir: Path,
    native_error: Exception,
    runtime_object_positions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        visual_asset = _extract_materialized_usd_visual_asset(
            scene_usd,
            output_dir / "prepared_usd_visual_asset",
            runtime_object_positions=runtime_object_positions,
        )
        scene.add_entity(
            morph=gs.morphs.Mesh(
                file=str(visual_asset["mesh_path"]),
                fixed=True,
                collision=False,
                visualization=True,
                decimate=False,
                convexify=False,
                group_by_material=True,
            )
        )
        return {
            "status": "success",
            "scene_usd": str(scene_usd),
            "usd_stage_loaded": True,
            "runtime_mode": "real",
            "genesis_import_mode": "prepared_usd_visual_asset_package",
            "native_usd_stage_error": str(native_error),
            "render_only_visual_asset": visual_asset,
            "claim_boundary": (
                "Genesis native USD stage import could not parse the prepared scene as a "
                "physics graph, so this render-only lane extracts final visible USD Mesh "
                "geometry into a temporary OBJ/MTL visual package that preserves "
                "USD material bindings, diffuse colors, UVs, and diffuse texture maps "
                "where available. This is scene-camera evidence only, not cleanup or "
                "physics support."
            ),
        }
    except Exception as asset_exc:
        visual_mesh = _extract_render_only_visual_mesh(
            scene_usd,
            output_dir / "prepared_usd_visual_mesh.obj",
        )
        scene.add_entity(
            morph=gs.morphs.Mesh(
                file=str(visual_mesh["mesh_path"]),
                fixed=True,
                collision=False,
                visualization=True,
                decimate=False,
                convexify=False,
            )
        )
        return {
            "status": "success",
            "scene_usd": str(scene_usd),
            "usd_stage_loaded": True,
            "runtime_mode": "real",
            "genesis_import_mode": "prepared_usd_visual_mesh",
            "native_usd_stage_error": str(native_error),
            "materialized_visual_asset_error": str(asset_exc),
            "render_only_visual_mesh": visual_mesh,
            "claim_boundary": (
                "Genesis native USD stage import and the material-preserving visual "
                "fallback could not parse the prepared scene, so this render-only lane "
                "uses a last-resort material-free OBJ. This is degraded scene-camera "
                "evidence only, not cleanup or physics support."
            ),
        }


def _write_fake_camera_views(
    args: argparse.Namespace,
    state: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    images: dict[str, str] = {}
    shapes: dict[str, list[int]] = {}
    views: list[dict[str, Any]] = []
    width = int(request["render_resolution"]["width"])
    height = int(request["render_resolution"]["height"])
    for index, view in enumerate(request.get("views") or [], start=1):
        if not isinstance(view, dict):
            continue
        view_id = _safe_view_id(str(view.get("view_id") or f"view_{index:02d}"))
        image_path = args.output_dir / f"{view_id}.png"
        image = Image.new("RGB", (width, height), (29, 78, 216))
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 8, max(9, width - 8), min(height - 8, 64)), fill=(15, 23, 42))
        draw.text((16, 24), f"fake Genesis {view_id}", fill=(248, 250, 252))
        image.save(image_path)
        images[view_id] = str(image_path)
        shapes[view_id] = [height, width, 3]
        views.append(_view_payload(view, image_path=image_path, shape=shapes[view_id]))
    return {
        "ok": True,
        "tool": "camera_views",
        "schema": "genesis_scene_camera_views_v1",
        "runtime": _runtime_metadata("fake"),
        "view_variant": GENESIS_SCENE_CAMERA_VIEW_VARIANT,
        "visual_artifact_provenance": "fake_protocol_placeholder_image",
        "camera_control_api": CAMERA_CONTROL_API_NAME,
        "camera_request_schema": request.get("schema"),
        "calibration_status": request.get("calibration_status"),
        "lighting_profile": request.get("lighting_profile") or {},
        "lighting_diagnostics": {
            "status": "fake_protocol",
            "source": "CI fake mode does not launch Genesis.",
        },
        "color_profile": request.get("color_profile") or {},
        "color_management": {"status": "fake_protocol"},
        "lens": request.get("lens") or {},
        "images": images,
        "shapes": shapes,
        "views": views,
        "scene_load": {
            "status": "fake_protocol",
            "scene_usd": str(state.get("scene_usd") or ""),
            "usd_stage_loaded": False,
            "runtime_mode": "fake",
        },
    }


def _extract_materialized_usd_visual_asset(
    scene_usd: Path,
    output_dir: Path,
    *,
    runtime_object_positions: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        from pxr import Gf, Usd, UsdGeom
    except Exception as exc:
        raise RuntimeError(
            f"pxr USD bindings unavailable for materialized visual extraction: {exc}"
        ) from exc
    stage = Usd.Stage.Open(str(scene_usd))
    if stage is None:
        raise RuntimeError(
            f"failed to open prepared USD for materialized visual extraction: {scene_usd}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    texture_dir = output_dir / "textures"
    obj_path = output_dir / "prepared_usd_visual_asset.obj"
    mtl_path = output_dir / "prepared_usd_visual_asset.mtl"
    mtl_name = mtl_path.name

    vertices: list[tuple[float, float, float]] = []
    texcoords: list[tuple[float, float]] = []
    face_lines: list[str] = []
    materials: dict[str, dict[str, Any]] = {}
    material_cache: dict[tuple[Any, ...], str] = {}
    metadata_objects = _load_scene_metadata_objects(scene_usd)
    runtime_pose_index = _index_runtime_object_positions(runtime_object_positions)
    object_audit_records: dict[str, dict[str, Any]] = {}
    object_vertex_indices: dict[str, list[int]] = {}
    copied_textures: dict[
        tuple[str, tuple[float, float, float], tuple[float, float, float]], str
    ] = {}
    used_texture_names: set[str] = set()
    current_material: str | None = None
    source_mesh_count = 0
    skipped_mesh_count = 0
    skipped_guide_mesh_count = 0
    skipped_collision_mesh_count = 0
    skipped_invisible_mesh_count = 0
    bound_material_count = 0
    textured_material_count = 0
    baked_texture_count = 0
    triangle_count = 0
    textured_triangle_count = 0

    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        gprim = UsdGeom.Gprim(prim)
        purpose = str(gprim.GetPurposeAttr().Get() or "default")
        object_key = _usd_object_key_for_prim(prim)
        if _usd_mesh_is_collision_guide(prim):
            skipped_collision_mesh_count += 1
            _record_visual_object_audit_mesh(
                object_audit_records,
                object_key=object_key,
                metadata_objects=metadata_objects,
                collision_mesh=True,
            )
            continue
        if purpose == "guide":
            skipped_guide_mesh_count += 1
            continue
        if str(gprim.ComputeVisibility()) == "invisible":
            skipped_invisible_mesh_count += 1
            continue
        points = list(mesh.GetPointsAttr().Get() or [])
        face_counts = [int(value) for value in list(mesh.GetFaceVertexCountsAttr().Get() or [])]
        face_indices = [int(value) for value in list(mesh.GetFaceVertexIndicesAttr().Get() or [])]
        if not points or not face_counts or not face_indices:
            skipped_mesh_count += 1
            continue

        mesh_material = _usd_material_name_for_prim(
            prim,
            scene_usd=scene_usd,
            material_cache=material_cache,
            materials=materials,
            texture_dir=texture_dir,
            copied_textures=copied_textures,
            used_texture_names=used_texture_names,
            fallback_label=str(prim.GetPath()),
        )
        if mesh_material is not None:
            bound_material_count += 1
        else:
            mesh_material = _usd_display_material_name(
                prim,
                material_cache=material_cache,
                materials=materials,
                fallback_label=str(prim.GetPath()),
            )
        face_materials = [mesh_material] * len(face_counts)
        for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh):
            subset_prim = subset.GetPrim()
            if str(subset.GetElementTypeAttr().Get() or "face") != "face":
                continue
            subset_face_ids = [int(value) for value in list(subset.GetIndicesAttr().Get() or [])]
            if not subset_face_ids:
                continue
            subset_material = (
                _usd_material_name_for_prim(
                    subset_prim,
                    scene_usd=scene_usd,
                    material_cache=material_cache,
                    materials=materials,
                    texture_dir=texture_dir,
                    copied_textures=copied_textures,
                    used_texture_names=used_texture_names,
                    fallback_label=str(subset_prim.GetPath()),
                )
                or mesh_material
            )
            for face_id in subset_face_ids:
                if 0 <= face_id < len(face_materials):
                    face_materials[face_id] = subset_material
        _record_visual_object_audit_mesh(
            object_audit_records,
            object_key=object_key,
            metadata_objects=metadata_objects,
            material_names=face_materials,
            materials=materials,
        )

        transform = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        transform_matrix = np.asarray(transform, dtype=np.float64)
        reverse_winding = bool(np.linalg.det(transform_matrix[:3, :3]) < 0)
        base_vertex_index = len(vertices)
        world_points: list[tuple[float, float, float]] = []
        for point in points:
            world = transform.Transform(Gf.Vec3d(float(point[0]), float(point[1]), float(point[2])))
            world_point = (float(world[0]), float(world[1]), float(world[2]))
            world_points.append(world_point)
        _record_visual_object_audit_bounds(
            object_audit_records,
            object_key=object_key,
            world_points=world_points,
        )
        vertices.extend(world_points)
        object_vertex_indices.setdefault(object_key, []).extend(
            range(base_vertex_index, base_vertex_index + len(world_points))
        )

        uv_cache: dict[str, dict[str, Any] | None] = {}
        cursor = 0
        for face_id, face_count in enumerate(face_counts):
            polygon = face_indices[cursor : cursor + face_count]
            face_vertex_offset = cursor
            cursor += face_count
            if len(polygon) < 3:
                continue
            material_name = face_materials[face_id] or _default_usd_material_name(
                material_cache=material_cache,
                materials=materials,
            )
            material_record = materials[material_name]
            uv_name = str(material_record.get("uv_name") or "st")
            if uv_name not in uv_cache:
                uv_cache[uv_name] = _usd_mesh_uv_data(prim, uv_name)
            uv_data = uv_cache[uv_name]
            if material_name != current_material:
                face_lines.append(f"usemtl {material_name}")
                current_material = material_name
            for index in range(1, len(polygon) - 1):
                triangle = [0, index, index + 1]
                if reverse_winding:
                    triangle = [0, index + 1, index]
                refs = []
                has_texture = bool(material_record.get("texture_relpath"))
                for local_corner in triangle:
                    point_index = int(polygon[local_corner])
                    vertex_ref = base_vertex_index + point_index + 1
                    uv = _usd_uv_at(
                        uv_data,
                        face_id=face_id,
                        face_vertex_offset=face_vertex_offset + local_corner,
                        vertex_index=point_index,
                    )
                    if uv is not None:
                        texcoords.append(uv)
                        refs.append(f"{vertex_ref}/{len(texcoords)}")
                    else:
                        refs.append(str(vertex_ref))
                face_lines.append("f " + " ".join(refs))
                triangle_count += 1
                if has_texture:
                    textured_triangle_count += 1
        source_mesh_count += 1

    if not vertices or not face_lines:
        raise RuntimeError("prepared USD contains no visible renderable UsdGeom.Mesh geometry")

    runtime_pose_overlay_count = _apply_runtime_pose_overlays(
        vertices,
        object_audit_records=object_audit_records,
        object_vertex_indices=object_vertex_indices,
        runtime_pose_index=runtime_pose_index,
    )

    for material in materials.values():
        if material.get("texture_relpath"):
            textured_material_count += 1
        if material.get("texture_color_baked"):
            baked_texture_count += 1

    with obj_path.open("w", encoding="utf-8") as file:
        file.write("# materialized render-only visual asset extracted from prepared USD\n")
        file.write(f"mtllib {mtl_name}\n")
        for vertex in vertices:
            file.write(f"v {vertex[0]:.8f} {vertex[1]:.8f} {vertex[2]:.8f}\n")
        for uv in texcoords:
            file.write(f"vt {uv[0]:.8f} {uv[1]:.8f}\n")
        for line in face_lines:
            file.write(line + "\n")
    with mtl_path.open("w", encoding="utf-8") as file:
        file.write("# USD material bindings extracted for Genesis visual fallback\n")
        for name, material in materials.items():
            color = (
                (1.0, 1.0, 1.0)
                if material.get("texture_color_baked")
                else material.get("diffuse_color") or (0.8, 0.8, 0.8)
            )
            opacity = float(material.get("opacity") if material.get("opacity") is not None else 1.0)
            file.write(f"newmtl {name}\n")
            file.write(f"Kd {float(color[0]):.6f} {float(color[1]):.6f} {float(color[2]):.6f}\n")
            file.write("Ka 0.000000 0.000000 0.000000\n")
            file.write("Ks 0.000000 0.000000 0.000000\n")
            file.write(f"d {opacity:.6f}\n")
            if material.get("texture_relpath"):
                file.write(f"map_Kd {material['texture_relpath']}\n")
            file.write("\n")

    return {
        "mesh_path": str(obj_path),
        "material_path": str(mtl_path),
        "source_usd": str(scene_usd),
        "source_mesh_count": source_mesh_count,
        "skipped_mesh_count": skipped_mesh_count,
        "skipped_guide_mesh_count": skipped_guide_mesh_count,
        "skipped_collision_mesh_count": skipped_collision_mesh_count,
        "skipped_invisible_mesh_count": skipped_invisible_mesh_count,
        "bound_material_count": bound_material_count,
        "material_count": len(materials),
        "textured_material_count": textured_material_count,
        "texture_count": len(copied_textures),
        "baked_texture_count": baked_texture_count,
        "runtime_pose_overlay_count": runtime_pose_overlay_count,
        "runtime_pose_overlay_threshold_m": GENESIS_RUNTIME_POSE_OVERLAY_THRESHOLD_M,
        "converted_texture_count": sum(
            1 for material in materials.values() if material.get("texture_converted")
        ),
        "vertex_count": len(vertices),
        "uv_count": len(texcoords),
        "triangle_count": triangle_count,
        "textured_triangle_count": textured_triangle_count,
        "format": "obj_mtl",
        "visual_filter": "visible_render_meshes_excluding_guide_and_collision_meshes",
        "visual_object_audit": _finalize_visual_object_audit(
            object_audit_records,
            metadata_source=scene_usd.with_name("scene_metadata.json"),
            runtime_pose_overlay_threshold_m=GENESIS_RUNTIME_POSE_OVERLAY_THRESHOLD_M,
        ),
    }


def _load_scene_metadata_objects(scene_usd: Path) -> dict[str, dict[str, Any]]:
    metadata_path = scene_usd.with_name("scene_metadata.json")
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    objects = payload.get("objects") if isinstance(payload, dict) else {}
    if not isinstance(objects, dict):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for key, value in objects.items():
        if not isinstance(value, dict):
            continue
        text_key = str(key)
        indexed[text_key] = value
        _index_scene_metadata_alias(indexed, text_key, value)
    return indexed


def _index_scene_metadata_alias(
    indexed: dict[str, dict[str, Any]],
    object_key: str,
    metadata: dict[str, Any],
) -> None:
    aliases = {
        object_key,
        str(metadata.get("hash_name") or ""),
        _safe_obj_token(object_key),
        _safe_obj_token(str(metadata.get("hash_name") or "")),
        _loose_obj_token(object_key),
        _loose_obj_token(str(metadata.get("hash_name") or "")),
    }
    name_map = metadata.get("name_map") if isinstance(metadata.get("name_map"), dict) else {}
    bodies = name_map.get("bodies") if isinstance(name_map.get("bodies"), dict) else {}
    for body_key in bodies:
        aliases.add(str(body_key))
        aliases.add(_safe_obj_token(str(body_key)))
        aliases.add(_loose_obj_token(str(body_key)))
    for alias in aliases:
        if alias:
            indexed.setdefault(alias, metadata)


def _usd_object_key_for_prim(prim: Any) -> str:
    parts = [part for part in str(prim.GetPath()).split("/") if part]
    if "Geometry" in parts:
        index = parts.index("Geometry")
        if index + 1 < len(parts):
            return parts[index + 1]
    return parts[0] if parts else str(prim.GetPath())


def _usd_mesh_is_collision_guide(prim: Any) -> bool:
    path_text = str(prim.GetPath())
    if "MeshCollider" in path_text or "collision" in path_text.lower():
        return True
    applied_schemas = {str(schema) for schema in prim.GetAppliedSchemas()}
    return bool(
        applied_schemas
        & {
            "PhysicsCollisionAPI",
            "PhysicsMeshCollisionAPI",
            "PhysicsMassAPI",
        }
    )


def _record_visual_object_audit_mesh(
    records: dict[str, dict[str, Any]],
    *,
    object_key: str,
    metadata_objects: dict[str, dict[str, Any]],
    material_names: list[str | None] | None = None,
    materials: dict[str, dict[str, Any]] | None = None,
    collision_mesh: bool = False,
) -> dict[str, Any]:
    record = records.get(object_key)
    if record is None:
        metadata = _scene_metadata_for_object_key(object_key, metadata_objects)
        category = metadata.get("category") or _scene_structure_category(object_key)
        record = {
            "object_key": object_key,
            "category": category,
            "asset_id": metadata.get("asset_id") or "",
            "object_id": metadata.get("object_id") or "",
            "is_static": (
                metadata.get("is_static")
                if "is_static" in metadata
                else _scene_structure_static_flag(object_key)
            ),
            "parent": metadata.get("parent") or "",
            "room_id": metadata.get("room_id"),
            "render_mesh_count": 0,
            "collision_mesh_count": 0,
            "material_names": [],
            "texture_relpaths": [],
            "converted_texture_relpaths": [],
            "converted_texture_names": [],
            "texture_modes": [],
            "metadata_match": metadata.get("_audit_match")
            or ("synthetic_scene_structure" if category else "unmatched"),
        }
        records[object_key] = record
    if collision_mesh:
        record["collision_mesh_count"] = int(record.get("collision_mesh_count") or 0) + 1
        return record
    record["render_mesh_count"] = int(record.get("render_mesh_count") or 0) + 1
    for name in sorted({str(item) for item in material_names or [] if item}):
        _append_unique(record["material_names"], name)
        material = materials.get(name, {}) if isinstance(materials, dict) else {}
        relpath = material.get("texture_relpath")
        if relpath:
            _append_unique(record["texture_relpaths"], str(relpath))
        mode = material.get("texture_mode")
        if mode:
            _append_unique(record["texture_modes"], str(mode))
        if material.get("texture_converted") and relpath:
            _append_unique(record["converted_texture_relpaths"], str(relpath))
            source_name = material.get("source_texture_name") or Path(str(relpath)).name
            _append_unique(record["converted_texture_names"], str(source_name))
    return record


def _append_unique(items: list[Any], value: Any) -> None:
    if value not in items:
        items.append(value)


def _record_visual_object_audit_bounds(
    records: dict[str, dict[str, Any]],
    *,
    object_key: str,
    world_points: list[tuple[float, float, float]],
    replace: bool = False,
) -> None:
    if not world_points:
        return
    record = records.get(object_key)
    if record is None:
        return
    mins = [min(point[index] for point in world_points) for index in range(3)]
    maxs = [max(point[index] for point in world_points) for index in range(3)]
    existing_min = record.get("bounds_min")
    existing_max = record.get("bounds_max")
    if not replace and _is_numeric_vec3(existing_min) and _is_numeric_vec3(existing_max):
        mins = [min(float(existing_min[index]), mins[index]) for index in range(3)]
        maxs = [max(float(existing_max[index]), maxs[index]) for index in range(3)]
    record["bounds_min"] = mins
    record["bounds_max"] = maxs
    record["bounds_center"] = [(mins[index] + maxs[index]) * 0.5 for index in range(3)]
    record["bounds_size"] = [maxs[index] - mins[index] for index in range(3)]


def _runtime_object_positions_from_request(request: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_positions = (
        request.get("runtime_object_positions")
        if isinstance(request.get("runtime_object_positions"), dict)
        else {}
    )
    positions: dict[str, dict[str, Any]] = {}
    for object_key, item in raw_positions.items():
        if not isinstance(item, dict) or not _is_numeric_vec3(item.get("position")):
            continue
        positions[str(object_key)] = {
            "object_key": str(object_key),
            "category": item.get("category") or "",
            "position": [float(value) for value in item["position"][:3]],
            "seeded_start_receptacle_id": item.get("seeded_start_receptacle_id") or "",
            "target_receptacle_id": item.get("target_receptacle_id") or "",
            "location_id": item.get("location_id") or "",
            "location_relation": item.get("location_relation") or "",
            "contained_in": item.get("contained_in"),
            "upstream_object_id": item.get("upstream_object_id") or "",
        }
    return positions


def _index_runtime_object_positions(
    runtime_object_positions: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    positions = runtime_object_positions if isinstance(runtime_object_positions, dict) else {}
    for object_key, item in positions.items():
        if not isinstance(item, dict) or not _is_numeric_vec3(item.get("position")):
            continue
        payload = dict(item)
        payload.setdefault("object_key", str(object_key))
        for alias in _runtime_pose_index_aliases(str(object_key)):
            if alias:
                index.setdefault(alias, payload)
    return index


def _runtime_pose_index_aliases(object_key: str) -> set[str]:
    aliases = {object_key, _safe_obj_token(object_key), _loose_obj_token(object_key)}
    return {alias for alias in aliases if alias}


def _runtime_pose_lookup_aliases(object_key: str) -> list[str]:
    candidates = [object_key]
    if object_key.startswith("tn__"):
        candidates.append(object_key[4:])
    candidates.extend(_trim_usd_name_suffixes(object_key))
    for candidate in list(candidates):
        if candidate.startswith("tn__"):
            candidates.append(candidate[4:])
        candidates.extend(_trim_usd_name_suffixes(candidate))
    aliases: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        for alias in (candidate, _safe_obj_token(candidate), _loose_obj_token(candidate)):
            if alias and alias not in seen:
                seen.add(alias)
                aliases.append(alias)
    return aliases


def _apply_runtime_pose_overlays(
    vertices: list[tuple[float, float, float]],
    *,
    object_audit_records: dict[str, dict[str, Any]],
    object_vertex_indices: dict[str, list[int]],
    runtime_pose_index: dict[str, dict[str, Any]],
) -> int:
    overlay_count = 0
    for object_key, record in object_audit_records.items():
        pose_overlay = _runtime_pose_overlay_for_object(
            object_key=object_key,
            record=record,
            runtime_pose_index=runtime_pose_index,
        )
        if pose_overlay is None:
            continue
        vertex_indices = object_vertex_indices.get(object_key) or []
        if not vertex_indices:
            continue
        _record_runtime_pose_overlay(record, pose_overlay)
        translation = pose_overlay["translation"]
        adjusted_points: list[tuple[float, float, float]] = []
        for vertex_index in vertex_indices:
            vertex = vertices[vertex_index]
            adjusted = (
                vertex[0] + translation[0],
                vertex[1] + translation[1],
                vertex[2] + translation[2],
            )
            vertices[vertex_index] = adjusted
            adjusted_points.append(adjusted)
        _record_visual_object_audit_bounds(
            object_audit_records,
            object_key=object_key,
            world_points=adjusted_points,
            replace=True,
        )
        overlay_count += 1
    return overlay_count


def _runtime_pose_overlay_for_object(
    *,
    object_key: str,
    record: dict[str, Any],
    runtime_pose_index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if record.get("is_static") is not False:
        return None
    center = record.get("bounds_center")
    if not _is_numeric_vec3(center):
        return None
    runtime_pose: dict[str, Any] | None = None
    runtime_match = ""
    for alias in _runtime_pose_lookup_aliases(object_key):
        runtime_pose = runtime_pose_index.get(alias)
        if runtime_pose is not None:
            runtime_match = alias
            break
    if runtime_pose is None or not _is_numeric_vec3(runtime_pose.get("position")):
        return None
    source_center = [float(value) for value in center[:3]]
    target_center = [float(value) for value in runtime_pose["position"][:3]]
    delta_m = _distance_3d(source_center, target_center)
    if delta_m <= GENESIS_RUNTIME_POSE_OVERLAY_THRESHOLD_M:
        return None
    translation = [target_center[index] - source_center[index] for index in range(3)]
    return {
        "status": "applied",
        "method": "translation_only_bounds_center_to_molmospaces_runtime_position",
        "runtime_match": runtime_match,
        "runtime_object_key": runtime_pose.get("object_key") or "",
        "threshold_m": GENESIS_RUNTIME_POSE_OVERLAY_THRESHOLD_M,
        "geometry_delta_m": delta_m,
        "source_bounds_center": source_center,
        "target_runtime_position": target_center,
        "translation": translation,
        "seeded_start_receptacle_id": runtime_pose.get("seeded_start_receptacle_id") or "",
        "target_receptacle_id": runtime_pose.get("target_receptacle_id") or "",
    }


def _record_runtime_pose_overlay(record: dict[str, Any], pose_overlay: dict[str, Any]) -> None:
    record["runtime_pose_overlay"] = pose_overlay
    record["runtime_pose_overlay_applied"] = True
    record["runtime_pose_overlay_geometry_delta_m"] = pose_overlay.get("geometry_delta_m")
    record["runtime_pose_overlay_translation"] = pose_overlay.get("translation")


def _is_numeric_vec3(value: Any) -> bool:
    if not isinstance(value, list) or len(value) < 3:
        return False
    try:
        [float(item) for item in value[:3]]
    except (TypeError, ValueError):
        return False
    return True


def _distance_3d(left: list[float], right: list[float]) -> float:
    return float(sum((float(left[index]) - float(right[index])) ** 2 for index in range(3)) ** 0.5)


def _scene_metadata_for_object_key(
    object_key: str,
    metadata_objects: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    metadata = metadata_objects.get(object_key)
    if metadata is not None:
        return {**metadata, "_audit_match": "exact"}
    token = _safe_obj_token(object_key)
    metadata = metadata_objects.get(token)
    if metadata is not None:
        return {**metadata, "_audit_match": "normalized_token"}
    loose_token = _loose_obj_token(object_key)
    metadata = metadata_objects.get(loose_token)
    if metadata is not None:
        return {**metadata, "_audit_match": "loose_token"}
    if object_key.startswith("tn__"):
        stripped = object_key[4:]
        metadata = (
            metadata_objects.get(stripped)
            or metadata_objects.get(_safe_obj_token(stripped))
            or metadata_objects.get(_loose_obj_token(stripped))
        )
        if metadata is not None:
            return {**metadata, "_audit_match": "usd_tn_prefix_alias"}
        for candidate in _trim_usd_name_suffixes(stripped):
            metadata = (
                metadata_objects.get(candidate)
                or metadata_objects.get(_safe_obj_token(candidate))
                or metadata_objects.get(_loose_obj_token(candidate))
            )
            if metadata is not None:
                return {**metadata, "_audit_match": "usd_tn_prefix_alias"}
    for candidate in _trim_usd_name_suffixes(object_key):
        metadata = (
            metadata_objects.get(candidate)
            or metadata_objects.get(_safe_obj_token(candidate))
            or metadata_objects.get(_loose_obj_token(candidate))
        )
        if metadata is not None:
            return {**metadata, "_audit_match": "usd_suffix_alias"}
    return {}


def _trim_usd_name_suffixes(object_key: str) -> list[str]:
    candidates: list[str] = []
    current = object_key
    for _ in range(4):
        head, separator, tail = current.rpartition("_")
        if not separator or not head or not tail:
            break
        if not (tail.isdigit() or (len(tail) <= 4 and tail.isalnum())):
            break
        current = head
        candidates.append(current)
    return candidates


def _scene_structure_category(object_key: str) -> str:
    if object_key.startswith("wall_"):
        return "RoomWall"
    if object_key.startswith("room_"):
        return "RoomShell"
    if object_key.startswith("floor_"):
        return "RoomFloor"
    if object_key.startswith("ceiling_"):
        return "RoomCeiling"
    return ""


def _scene_structure_static_flag(object_key: str) -> bool | None:
    if _scene_structure_category(object_key):
        return True
    return None


def _finalize_visual_object_audit(
    records: dict[str, dict[str, Any]],
    *,
    metadata_source: Path,
    runtime_pose_overlay_threshold_m: float = GENESIS_RUNTIME_POSE_OVERLAY_THRESHOLD_M,
) -> dict[str, Any]:
    objects = []
    for record in sorted(records.values(), key=lambda item: str(item.get("object_key") or "")):
        item = dict(record)
        item["material_count"] = len(item.get("material_names") or [])
        item["texture_count"] = len(item.get("texture_relpaths") or [])
        item["converted_texture_count"] = len(item.get("converted_texture_relpaths") or [])
        objects.append(item)
    converted = [item for item in objects if int(item.get("converted_texture_count") or 0) > 0]
    non_static = [
        item
        for item in objects
        if item.get("is_static") is False and int(item.get("render_mesh_count") or 0) > 0
    ]
    collision = [item for item in objects if int(item.get("collision_mesh_count") or 0) > 0]
    runtime_pose_overlay = [
        item for item in objects if bool(item.get("runtime_pose_overlay_applied"))
    ]
    risk_groups = [
        _visual_object_risk_group(
            "texture_conversion",
            converted,
            meaning="non_rgb_texture_normalized_for_genesis_import",
        ),
        _visual_object_risk_group(
            "non_static_render_object",
            non_static,
            meaning="real_movable_clutter_renderer_visibility_parity_risk",
        ),
        _visual_object_risk_group(
            "collision_mesh_filtered",
            collision,
            meaning="collider_geometry_removed_from_genesis_visual_package",
        ),
        _visual_object_risk_group(
            "runtime_pose_overlay",
            runtime_pose_overlay,
            meaning="non_static_object_translated_to_molmospaces_runtime_pose_for_rendering",
        ),
    ]
    return {
        "schema": "genesis_visual_asset_object_audit_v1",
        "metadata_source": str(metadata_source) if metadata_source.is_file() else "",
        "object_count": len(objects),
        "render_mesh_object_count": sum(
            1 for item in objects if int(item.get("render_mesh_count") or 0) > 0
        ),
        "texture_conversion_object_count": len(converted),
        "non_static_render_object_count": len(non_static),
        "collision_mesh_object_count": len(collision),
        "runtime_pose_overlay_object_count": len(runtime_pose_overlay),
        "runtime_pose_overlay_threshold_m": runtime_pose_overlay_threshold_m,
        "texture_conversion_objects": converted,
        "non_static_render_objects": non_static,
        "collision_mesh_objects": collision,
        "runtime_pose_overlay_objects": runtime_pose_overlay,
        "runtime_state_application": {
            "schema": "genesis_runtime_state_application_v1",
            "pose_overlay_method": "translation_only_bounds_center_to_molmospaces_runtime_position",
            "articulation_apply_status": "unsupported",
            "articulation_note": (
                "The prepared-USD visual package can translate grouped object vertices to "
                "MuJoCo runtime centers, but it does not currently apply child joint or "
                "articulation qpos such as box flaps."
            ),
        },
        "risk_groups": risk_groups,
        "objects": objects,
        "interpretation": (
            "Genesis visual package audit groups renderable USD meshes by source object, "
            "records palette/indexed texture normalization, lists non-static clutter that "
            "can produce renderer-dependent visibility, confirms collision meshes are not "
            "imported as visual geometry, and records render-only runtime pose overlays for "
            "non-static objects whose prepared-USD pose diverges materially from the "
            "MolmoSpaces runtime pose. Runtime pose overlays are translation-only and are "
            "not articulation-state application."
        ),
    }


def _visual_object_risk_group(
    risk: str,
    objects: list[dict[str, Any]],
    *,
    meaning: str,
) -> dict[str, Any]:
    category_counts: dict[str, int] = {}
    for item in objects:
        category = str(item.get("category") or "Uncategorized")
        category_counts[category] = category_counts.get(category, 0) + 1
    return {
        "risk": risk,
        "meaning": meaning,
        "object_count": len(objects),
        "category_counts": dict(
            sorted(category_counts.items(), key=lambda entry: (-entry[1], entry[0]))
        ),
    }


def _usd_material_name_for_prim(
    prim: Any,
    *,
    scene_usd: Path,
    material_cache: dict[tuple[Any, ...], str],
    materials: dict[str, dict[str, Any]],
    texture_dir: Path,
    copied_textures: dict[tuple[str, tuple[float, float, float], tuple[float, float, float]], str],
    used_texture_names: set[str],
    fallback_label: str,
) -> str | None:
    try:
        from pxr import UsdShade
    except Exception as exc:  # pragma: no cover - caller already imports pxr.
        raise RuntimeError(f"pxr USD bindings unavailable for material parsing: {exc}") from exc
    material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    material_prim = material.GetPrim()
    if not material_prim.IsValid():
        return None
    material_info = _usd_material_info(
        material,
        scene_usd=scene_usd,
        texture_dir=texture_dir,
        copied_textures=copied_textures,
        used_texture_names=used_texture_names,
    )
    key = (
        str(material_prim.GetPath()),
        tuple(material_info.get("diffuse_color") or ()),
        material_info.get("texture_relpath"),
        material_info.get("opacity"),
        material_info.get("uv_name"),
        material_info.get("texture_converted"),
    )
    if key in material_cache:
        return material_cache[key]
    name = _unique_obj_name(
        _safe_obj_token(str(material_prim.GetPath()).split("/")[-1] or fallback_label),
        existing=set(materials),
        prefix="mat",
    )
    materials[name] = {
        **material_info,
        "source_material": str(material_prim.GetPath()),
    }
    material_cache[key] = name
    return name


def _usd_material_info(
    material: Any,
    *,
    scene_usd: Path,
    texture_dir: Path,
    copied_textures: dict[tuple[str, tuple[float, float, float], tuple[float, float, float]], str],
    used_texture_names: set[str],
) -> dict[str, Any]:
    from pxr import Sdf

    material_info: dict[str, Any] = {
        "diffuse_color": (0.8, 0.8, 0.8),
        "opacity": 1.0,
        "uv_name": "st",
        "texture_relpath": None,
        "texture_color_baked": False,
        "texture_converted": False,
        "texture_mode": "",
        "source_texture_name": "",
    }
    for surface_output in material.GetSurfaceOutputs():
        if not surface_output.HasConnectedSource():
            continue
        source = surface_output.GetConnectedSource()
        shader = _usd_connected_shader(source[0], source[1])
        if shader is None or shader.GetShaderId() != "UsdPreviewSurface":
            continue
        diffuse_input = shader.GetInput("diffuseColor")
        if diffuse_input and diffuse_input.HasConnectedSource():
            texture_source = diffuse_input.GetConnectedSource()
            texture_shader = _usd_connected_shader(texture_source[0], texture_source[1])
            if texture_shader is not None and texture_shader.GetShaderId() == "UsdUVTexture":
                texture_color_scale = (1.0, 1.0, 1.0)
                texture_color_bias = (0.0, 0.0, 0.0)
                fallback = texture_shader.GetInput("fallback").Get()
                if fallback is not None:
                    material_info["diffuse_color"] = _color3(
                        fallback,
                        material_info["diffuse_color"],
                    )
                scale = texture_shader.GetInput("scale").Get()
                if scale is not None:
                    texture_color_scale = _color3(scale, texture_color_scale)
                    material_info["diffuse_color"] = texture_color_scale
                bias_input = texture_shader.GetInput("bias")
                if bias_input:
                    bias = bias_input.Get()
                    if bias is not None:
                        texture_color_bias = _color3(bias, texture_color_bias)
                texture_file = texture_shader.GetInput("file").Get()
                if isinstance(texture_file, Sdf.AssetPath):
                    texture_path = _resolved_usd_asset_path(texture_file, scene_usd=scene_usd)
                    material_info["texture_mode"] = _texture_mode(texture_path)
                    material_info["source_texture_name"] = texture_path.name
                    texture_relpath = _copy_usd_texture(
                        texture_path,
                        texture_dir=texture_dir,
                        copied_textures=copied_textures,
                        used_texture_names=used_texture_names,
                        color_scale=texture_color_scale,
                        color_bias=texture_color_bias,
                    )
                    if texture_relpath is not None:
                        material_info["texture_relpath"] = texture_relpath
                        material_info["texture_color_baked"] = _texture_color_adjustment_needed(
                            texture_color_scale,
                            texture_color_bias,
                        )
                        material_info["texture_converted"] = _texture_conversion_needed(
                            texture_path,
                        )
                material_info["uv_name"] = _usd_texture_uv_name(texture_shader) or "st"
        elif diffuse_input:
            material_info["diffuse_color"] = _color3(
                diffuse_input.Get(),
                material_info["diffuse_color"],
            )
        opacity_input = shader.GetInput("opacity")
        if opacity_input:
            opacity = opacity_input.Get()
            if opacity is not None:
                material_info["opacity"] = float(opacity)
        break
    return material_info


def _usd_connected_shader(connectable: Any, output_name: str) -> Any | None:
    from pxr import UsdShade

    prim = connectable.GetPrim()
    if prim.IsA(UsdShade.Shader):
        return UsdShade.Shader(prim)
    if prim.IsA(UsdShade.NodeGraph):
        source = UsdShade.NodeGraph(prim).ComputeOutputSource(output_name)
        if source and source[0]:
            return _usd_connected_shader(source[0], source[1])
    return None


def _usd_texture_uv_name(texture_shader: Any) -> str | None:
    st_input = texture_shader.GetInput("st")
    if not st_input or not st_input.HasConnectedSource():
        return None
    source = st_input.GetConnectedSource()
    shader = _usd_connected_shader(source[0], source[1])
    if shader is None or not shader.GetShaderId().startswith("UsdPrimvarReader"):
        return None
    varname_input = shader.GetInput("varname")
    value = varname_input.Get() if varname_input else None
    return str(value) if value else None


def _resolved_usd_asset_path(asset_path: Any, *, scene_usd: Path) -> Path:
    raw_path = str(asset_path.resolvedPath or asset_path.path)
    path = Path(raw_path)
    if not path.is_absolute():
        path = scene_usd.parent / raw_path
    return path


def _copy_usd_texture(
    texture_path: Path,
    *,
    texture_dir: Path,
    copied_textures: dict[tuple[str, tuple[float, float, float], tuple[float, float, float]], str],
    used_texture_names: set[str],
    color_scale: tuple[float, float, float] = (1.0, 1.0, 1.0),
    color_bias: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> str | None:
    if not texture_path.is_file():
        return None
    color_scale = _color_tuple(color_scale, fallback=(1.0, 1.0, 1.0))
    color_bias = _color_tuple(color_bias, fallback=(0.0, 0.0, 0.0))
    key = (str(texture_path.resolve()), color_scale, color_bias)
    if key in copied_textures:
        return copied_textures[key]
    texture_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_obj_token(texture_path.stem) or "texture"
    suffix = texture_path.suffix or ".png"
    should_bake = _texture_color_adjustment_needed(color_scale, color_bias)
    if should_bake:
        digest = hashlib.sha1(
            json.dumps({"scale": color_scale, "bias": color_bias}, sort_keys=True).encode("utf-8")
        ).hexdigest()[:8]
        filename = f"{stem}_baked_{digest}.png"
    else:
        filename = f"{stem}{suffix}"
    counter = 2
    while filename in used_texture_names:
        filename = (
            f"{stem}_baked_{digest}_{counter}.png" if should_bake else (f"{stem}_{counter}{suffix}")
        )
        counter += 1
    used_texture_names.add(filename)
    target = texture_dir / filename
    if should_bake:
        try:
            _write_color_baked_texture(
                texture_path,
                target=target,
                color_scale=color_scale,
                color_bias=color_bias,
            )
        except Exception:
            shutil.copy2(texture_path, target)
    elif _texture_conversion_needed(texture_path):
        _write_genesis_compatible_texture(texture_path, target=target)
    else:
        shutil.copy2(texture_path, target)
    relpath = f"textures/{filename}"
    copied_textures[key] = relpath
    return relpath


def _write_color_baked_texture(
    texture_path: Path,
    *,
    target: Path,
    color_scale: tuple[float, float, float],
    color_bias: tuple[float, float, float],
) -> None:
    with Image.open(texture_path) as image:
        has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
        converted = image.convert("RGBA" if has_alpha else "RGB")
        array = np.asarray(converted).astype("float32")
        rgb = array[..., :3] / 255.0
        scale = np.asarray(color_scale, dtype="float32").reshape(1, 1, 3)
        bias = np.asarray(color_bias, dtype="float32").reshape(1, 1, 3)
        array[..., :3] = np.clip(rgb * scale + bias, 0.0, 1.0) * 255.0
        Image.fromarray(np.clip(array, 0, 255).astype("uint8"), mode=converted.mode).save(target)


def _texture_conversion_needed(texture_path: Path) -> bool:
    try:
        with Image.open(texture_path) as image:
            return image.mode not in {"RGB", "RGBA"}
    except Exception:
        return False


def _texture_mode(texture_path: Path) -> str:
    try:
        with Image.open(texture_path) as image:
            return str(image.mode)
    except Exception:
        return ""


def _write_genesis_compatible_texture(texture_path: Path, *, target: Path) -> None:
    with Image.open(texture_path) as image:
        has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
        converted = image.convert("RGBA" if has_alpha else "RGB")
        converted.save(target)


def _texture_color_adjustment_needed(
    color_scale: tuple[float, float, float],
    color_bias: tuple[float, float, float],
) -> bool:
    return any(abs(value - 1.0) > 1e-6 for value in color_scale) or any(
        abs(value) > 1e-6 for value in color_bias
    )


def _color_tuple(
    value: Any,
    *,
    fallback: tuple[float, float, float],
) -> tuple[float, float, float]:
    return _color3(value, fallback)


def _usd_display_material_name(
    prim: Any,
    *,
    material_cache: dict[tuple[Any, ...], str],
    materials: dict[str, dict[str, Any]],
    fallback_label: str,
) -> str:
    color = _usd_display_color(prim) or (0.8, 0.8, 0.8)
    key = ("display", tuple(color))
    if key in material_cache:
        return material_cache[key]
    name = _unique_obj_name(
        _safe_obj_token(f"{Path(fallback_label).name}_display"),
        existing=set(materials),
        prefix="display",
    )
    materials[name] = {
        "diffuse_color": color,
        "opacity": 1.0,
        "uv_name": "st",
        "texture_relpath": None,
        "source_material": "usd_displayColor",
    }
    material_cache[key] = name
    return name


def _usd_display_color(prim: Any) -> tuple[float, float, float] | None:
    try:
        from pxr import UsdGeom
    except Exception:  # pragma: no cover - caller already imports pxr.
        return None
    gprim = UsdGeom.Gprim(prim)
    values = gprim.GetDisplayColorPrimvar().Get()
    if not values:
        return None
    return _color3(values[0], (0.8, 0.8, 0.8))


def _default_usd_material_name(
    *,
    material_cache: dict[tuple[Any, ...], str],
    materials: dict[str, dict[str, Any]],
) -> str:
    key = ("default",)
    if key in material_cache:
        return material_cache[key]
    name = _unique_obj_name("default_material", existing=set(materials), prefix="mat")
    materials[name] = {
        "diffuse_color": (0.8, 0.8, 0.8),
        "opacity": 1.0,
        "uv_name": "st",
        "texture_relpath": None,
        "source_material": "default",
    }
    material_cache[key] = name
    return name


def _usd_mesh_uv_data(prim: Any, uv_name: str) -> dict[str, Any] | None:
    from pxr import UsdGeom

    primvar = UsdGeom.PrimvarsAPI(prim).GetPrimvar(uv_name)
    if not primvar or not primvar.HasValue():
        return None
    values = list(primvar.Get() or [])
    if not values:
        return None
    indices = list(primvar.GetIndices() or [])
    return {
        "values": values,
        "indices": indices or None,
        "interpolation": str(primvar.GetInterpolation() or "vertex"),
    }


def _usd_uv_at(
    uv_data: dict[str, Any] | None,
    *,
    face_id: int,
    face_vertex_offset: int,
    vertex_index: int,
) -> tuple[float, float] | None:
    if uv_data is None:
        return None
    interpolation = str(uv_data.get("interpolation") or "vertex")
    if interpolation == "faceVarying":
        index = face_vertex_offset
    elif interpolation == "uniform":
        index = face_id
    elif interpolation == "constant":
        index = 0
    else:
        index = vertex_index
    indices = uv_data.get("indices")
    if indices is not None:
        if not 0 <= index < len(indices):
            return None
        index = int(indices[index])
    values = uv_data.get("values") or []
    if not 0 <= index < len(values):
        return None
    value = values[index]
    return (float(value[0]), float(value[1]))


def _color3(value: Any, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    if value is None:
        return fallback
    try:
        if len(value) >= 3:
            return (float(value[0]), float(value[1]), float(value[2]))
    except TypeError:
        pass
    try:
        scalar = float(value)
    except (TypeError, ValueError):
        return fallback
    return (scalar, scalar, scalar)


def _safe_obj_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value).strip("_")


def _loose_obj_token(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _unique_obj_name(value: str, *, existing: set[str], prefix: str) -> str:
    base = value or prefix
    if base[0].isdigit():
        base = f"{prefix}_{base}"
    name = base
    counter = 2
    while name in existing:
        name = f"{base}_{counter}"
        counter += 1
    return name


def _view_payload(view: dict[str, Any], *, image_path: Path, shape: Any) -> dict[str, Any]:
    payload = dict(view)
    payload["image_path"] = str(image_path)
    payload["shape"] = list(shape)
    payload["backend_eye"] = _vec3(view.get("eye"), fallback=[])
    payload["backend_target"] = _vec3(view.get("target") or view.get("lookat"), fallback=[])
    payload["backend_up"] = _vec3(view.get("up"), fallback=[])
    payload["calibration_status"] = view.get("calibration_status")
    return payload


def _runtime_metadata(
    runtime_mode: str,
    *,
    genesis: Any | None = None,
    torch_module: Any | None = None,
    numpy: Any | None = None,
) -> dict[str, Any]:
    metadata = {
        "runtime_mode": runtime_mode,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "backend": "genesis_subprocess",
        "renderer_mode": "fake_genesis_protocol" if runtime_mode == "fake" else "genesis_world",
        "real_rendering_proven": runtime_mode == "real",
    }
    if genesis is not None:
        metadata["genesis_version"] = str(getattr(genesis, "__version__", "unknown"))
        metadata["genesis_module"] = str(getattr(genesis, "__file__", ""))
    if torch_module is not None:
        metadata["torch_version"] = str(getattr(torch_module, "__version__", "unknown"))
        cuda = getattr(torch_module, "cuda", None)
        if cuda is not None:
            try:
                metadata["torch_cuda_available"] = bool(cuda.is_available())
            except Exception:
                metadata["torch_cuda_available"] = None
    if numpy is not None:
        metadata["numpy_version"] = str(getattr(numpy, "__version__", "unknown"))
    return metadata


def _extract_render_only_visual_mesh(scene_usd: Path, output_path: Path) -> dict[str, Any]:
    try:
        from pxr import Usd, UsdGeom
    except Exception as exc:
        raise RuntimeError(
            f"pxr USD bindings unavailable for render-only mesh extraction: {exc}"
        ) from exc
    stage = Usd.Stage.Open(str(scene_usd))
    if stage is None:
        raise RuntimeError(
            f"failed to open prepared USD for render-only mesh extraction: {scene_usd}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    mesh_count = 0
    triangle_count = 0
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        points = mesh.GetPointsAttr().Get()
        if not points:
            continue
        face_counts = list(mesh.GetFaceVertexCountsAttr().Get() or [])
        face_indices = list(mesh.GetFaceVertexIndicesAttr().Get() or [])
        if not face_counts or not face_indices:
            continue
        transform = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        base_index = len(vertices)
        for point in points:
            world = transform.Transform(point)
            vertices.append((float(world[0]), float(world[1]), float(world[2])))
        cursor = 0
        for face_count in face_counts:
            polygon = face_indices[cursor : cursor + int(face_count)]
            cursor += int(face_count)
            if len(polygon) < 3:
                continue
            for index in range(1, len(polygon) - 1):
                faces.append(
                    (
                        base_index + int(polygon[0]) + 1,
                        base_index + int(polygon[index]) + 1,
                        base_index + int(polygon[index + 1]) + 1,
                    )
                )
                triangle_count += 1
        mesh_count += 1
    if not vertices or not faces:
        raise RuntimeError("prepared USD contains no renderable UsdGeom.Mesh geometry")
    with output_path.open("w", encoding="utf-8") as file:
        file.write("# render-only visual mesh extracted from prepared USD\n")
        for vertex in vertices:
            file.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
        for face in faces:
            file.write(f"f {face[0]} {face[1]} {face[2]}\n")
    return {
        "mesh_path": str(output_path),
        "source_usd": str(scene_usd),
        "source_mesh_count": mesh_count,
        "vertex_count": len(vertices),
        "triangle_count": triangle_count,
        "format": "obj",
    }


def _error(tool: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "tool": tool,
        "error": {"reason": reason, **extra},
    }


def _safe_view_id(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return safe or "view"


def _vec3(value: Any, *, fallback: list[float]) -> list[float]:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return [float(value[0]), float(value[1]), float(value[2])]
    return list(fallback)


def read_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
