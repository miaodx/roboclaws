#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from PIL import Image, ImageDraw

from roboclaws.household.camera_control import (
    CAMERA_CONTROL_API_NAME,
    load_camera_control_request,
)
from roboclaws.household.genesis_backend import GENESIS_SCENE_CAMERA_VIEW_VARIANT


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
        import numpy as np
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

    try:
        if not getattr(gs, "_initialized", False):
            gs.init(backend=gs.cpu)
        scene = gs.Scene(
            viewer_options=gs.options.ViewerOptions(
                res=(width, height),
                camera_pos=(0.0, -3.0, 2.0),
                camera_lookat=(0.0, 0.0, 1.0),
                camera_fov=vertical_fov,
            ),
            renderer=gs.renderers.Rasterizer(),
            show_viewer=False,
            show_FPS=False,
        )
        scene.add_stage(morph=gs.morphs.USD(file=str(scene_usd)))
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
        for index, (view, camera) in enumerate(cameras, start=1):
            view_id = _safe_view_id(str(view.get("view_id") or f"view_{index:02d}"))
            rgb = camera.render(rgb=True, depth=False, segmentation=False, normal=False)[0]
            rgb_array = np.asarray(rgb)
            if rgb_array.ndim == 4:
                rgb_array = rgb_array[0]
            if rgb_array.dtype != np.uint8:
                rgb_array = np.clip(rgb_array, 0, 255).astype("uint8")
            image_path = args.output_dir / f"{view_id}.png"
            Image.fromarray(rgb_array).save(image_path)
            images[view_id] = str(image_path)
            shapes[view_id] = list(rgb_array.shape)
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
            "status": "genesis_default_scene_lighting",
            "source": "prepared_usd_plus_genesis_rasterizer",
        },
        "color_profile": request.get("color_profile") or {},
        "color_management": {"status": "renderer_rgb_uint8"},
        "lens": request.get("lens") or {},
        "images": images,
        "shapes": shapes,
        "views": views,
        "scene_load": {
            "status": "success",
            "scene_usd": str(scene_usd),
            "usd_stage_loaded": True,
            "runtime_mode": "real",
        },
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
