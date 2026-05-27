#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from roboclaws.molmo_cleanup.subprocess_backend import _parse_last_json_object

SCHEMA = "roboclaws_isaac_lab_runtime_smoke_check_v1"
SCENE_BINDING_SCHEMA = "isaac_public_scene_bindings_v1"
ISAACLAB_ROBOT_VIEW_VARIANT = "isaaclab-fpv-map-chase-verify"
ROBOT_VIEW_KEYS = ("fpv", "chase", "map", "verify")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Isaac Lab runtime smoke evidence.")
    parser.add_argument("--init-result", type=Path, required=True)
    parser.add_argument("--state-path", type=Path)
    parser.add_argument("--robot-views-result", type=Path)
    parser.add_argument("--require-real-rendering", action="store_true")
    parser.add_argument("--require-usd-stage-loaded", action="store_true")
    parser.add_argument("--require-usd-scene-index", action="store_true")
    parser.add_argument("--require-selected-usd-bindings", action="store_true")
    parser.add_argument("--require-robot-view-images", action="store_true")
    parser.add_argument("--require-nonblank-image", action="store_true")
    parser.add_argument("--require-segmentation-evidence", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = _read_json(args.init_result)
    state = _read_json(args.state_path) if args.state_path else {}
    robot_views_result = _read_json(args.robot_views_result) if args.robot_views_result else {}
    errors = validate(
        result=result,
        state=state,
        robot_views_result=robot_views_result,
        require_real_rendering=args.require_real_rendering,
        require_usd_stage_loaded=args.require_usd_stage_loaded,
        require_usd_scene_index=args.require_usd_scene_index,
        require_selected_usd_bindings=args.require_selected_usd_bindings,
        require_robot_view_images=args.require_robot_view_images,
        require_nonblank_image=args.require_nonblank_image,
        require_segmentation_evidence=args.require_segmentation_evidence,
    )
    summary = {
        "schema": SCHEMA,
        "status": "failed" if errors else "passed",
        "errors": errors,
        "backend": result.get("backend"),
        "runtime_mode": (result.get("runtime") or {}).get("runtime_mode"),
        "scene_usd": result.get("scene_usd"),
        "scene_index_status": (_dict(result.get("scene_index_diagnostics"))).get("status"),
        "scene_binding_status": (_dict(result.get("scene_binding_diagnostics"))).get("status"),
        "robot_view_status": _robot_view_status(robot_views_result),
    }
    print(json.dumps(summary, sort_keys=True))
    return 1 if errors else 0


def validate(
    *,
    result: dict[str, Any],
    state: dict[str, Any],
    robot_views_result: dict[str, Any],
    require_real_rendering: bool,
    require_usd_stage_loaded: bool,
    require_usd_scene_index: bool,
    require_selected_usd_bindings: bool,
    require_robot_view_images: bool,
    require_nonblank_image: bool,
    require_segmentation_evidence: bool,
) -> list[str]:
    errors: list[str] = []
    _require(result.get("ok") is True, "init result did not report ok=true", errors)
    _require(
        result.get("backend") == "isaaclab_subprocess",
        "init result backend is not isaaclab_subprocess",
        errors,
    )
    runtime = _dict(result.get("runtime"))
    rendering = _dict(runtime.get("rendering"))
    scene_load = _dict(result.get("scene_load"))
    scene_index = _dict(result.get("scene_index_diagnostics"))
    scene_bindings = _dict(result.get("scene_binding_diagnostics"))
    segmentation = _dict(result.get("segmentation"))
    artifacts = _dict(result.get("artifacts"))

    if require_real_rendering:
        _require(
            runtime.get("runtime_mode") == "real",
            "runtime_mode is not real",
            errors,
        )
        _require(
            rendering.get("real_rendering_proven") is True,
            "real Isaac rendering is not proven",
            errors,
        )
        _require(
            rendering.get("placeholder_visuals") is not True,
            "runtime smoke still reports placeholder visuals",
            errors,
        )
    if require_usd_stage_loaded:
        _require(
            scene_load.get("usd_stage_loaded") is True,
            "USD stage loading is not proven",
            errors,
        )
        _require(
            scene_load.get("status") == "loaded",
            "scene_load status is not loaded",
            errors,
        )
    if require_usd_scene_index:
        object_index = _dict(result.get("object_index"))
        receptacle_index = _dict(result.get("receptacle_index"))
        _require(bool(scene_index), "missing USD scene index diagnostics", errors)
        _require(
            int(scene_index.get("stage_prim_count") or 0) > 0,
            "USD scene index has no stage prims",
            errors,
        )
        _require(
            int(scene_index.get("object_candidate_count") or 0) > 0 or bool(object_index),
            "USD scene index has no object candidates",
            errors,
        )
        _require(
            int(scene_index.get("receptacle_candidate_count") or 0) > 0 or bool(receptacle_index),
            "USD scene index has no receptacle candidates",
            errors,
        )
    if require_selected_usd_bindings:
        errors.extend(_selected_usd_binding_errors(scene_bindings))
    if require_nonblank_image:
        image_path = artifacts.get("runtime_smoke_image")
        _require(
            isinstance(image_path, str) and bool(image_path), "missing smoke image path", errors
        )
        if isinstance(image_path, str) and image_path:
            errors.extend(_image_errors(Path(image_path)))
    if require_robot_view_images:
        errors.extend(
            _robot_view_errors(
                robot_views_result,
                require_real_rendering=require_real_rendering,
            )
        )
    if require_segmentation_evidence:
        errors.extend(_segmentation_errors(segmentation))

    if state:
        _require(
            state.get("backend") == result.get("backend"),
            "state backend does not match init result",
            errors,
        )
        _require(
            _dict(state.get("runtime")).get("runtime_mode") == runtime.get("runtime_mode"),
            "state runtime_mode does not match init result",
            errors,
        )
    return errors


def _selected_usd_binding_errors(scene_bindings: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(bool(scene_bindings), "missing selected USD binding diagnostics", errors)
    if not scene_bindings:
        return errors
    _require(
        scene_bindings.get("schema") == SCENE_BINDING_SCHEMA,
        "selected USD binding diagnostics schema is not isaac_public_scene_bindings_v1",
        errors,
    )
    _require(
        scene_bindings.get("source") == "usd_stage_traversal",
        "selected USD bindings are not sourced from USD stage traversal",
        errors,
    )
    _require(
        scene_bindings.get("status") == "selected_bound",
        "selected cleanup handles are not fully bound to USD prims",
        errors,
    )
    selected_object_count = _int(scene_bindings.get("selected_object_count"))
    selected_receptacle_count = _int(scene_bindings.get("selected_target_receptacle_count"))
    selected_object_bound_count = _int(scene_bindings.get("selected_object_bound_count"))
    selected_receptacle_bound_count = _int(
        scene_bindings.get("selected_target_receptacle_bound_count")
    )
    _require(selected_object_count > 0, "no selected cleanup objects were checked", errors)
    _require(
        selected_receptacle_count > 0,
        "no selected target receptacles were checked",
        errors,
    )
    _require(
        selected_object_bound_count >= selected_object_count,
        "not all selected cleanup objects have USD prim bindings",
        errors,
    )
    _require(
        selected_receptacle_bound_count >= selected_receptacle_count,
        "not all selected target receptacles have USD prim bindings",
        errors,
    )
    _require(
        not scene_bindings.get("blockers"),
        "selected USD binding diagnostics still report blockers",
        errors,
    )
    _require(
        scene_bindings.get("private_manifest_exposed_to_agent") is False,
        "selected USD binding diagnostics report private manifest exposure",
        errors,
    )
    return errors


def _segmentation_errors(segmentation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(bool(segmentation), "missing Isaac segmentation diagnostics", errors)
    if not segmentation:
        return errors
    _require(
        segmentation.get("schema") == "isaac_segmentation_diagnostics_v1",
        "Isaac segmentation diagnostics schema is not isaac_segmentation_diagnostics_v1",
        errors,
    )
    _require(
        segmentation.get("status") == "available",
        "Isaac segmentation evidence is not available",
        errors,
    )
    _require(
        segmentation.get("available") is True,
        "Isaac segmentation diagnostics do not report available=true",
        errors,
    )
    _require(
        segmentation.get("tensor_output_available") is True,
        "Isaac segmentation tensors were not captured",
        errors,
    )
    _require(
        _int(segmentation.get("candidate_bbox_count")) > 0,
        "Isaac segmentation produced no bbox candidates",
        errors,
    )
    _require(
        _int(segmentation.get("selected_usd_prim_match_count")) > 0,
        "Isaac segmentation produced no selected-USD candidate matches",
        errors,
    )
    _require(
        segmentation.get("candidate_overlay_status") == "available",
        "Isaac segmentation candidate overlays are not available",
        errors,
    )
    _require(
        segmentation.get("agent_facing") is False,
        "Isaac segmentation diagnostics leaked into agent-facing fields",
        errors,
    )
    _require(
        segmentation.get("no_simulator_label_fallback") is True,
        "Isaac segmentation diagnostics used simulator-label fallback",
        errors,
    )
    return errors


def _robot_view_errors(
    result: dict[str, Any],
    *,
    require_real_rendering: bool,
) -> list[str]:
    errors: list[str] = []
    _require(bool(result), "missing robot views result", errors)
    if not result:
        return errors
    _require(result.get("ok") is True, "robot views result did not report ok=true", errors)
    _require(
        result.get("view_variant") == ISAACLAB_ROBOT_VIEW_VARIANT,
        "robot views result is not the Isaac Lab view variant",
        errors,
    )
    views = _dict(result.get("views"))
    for key in ROBOT_VIEW_KEYS:
        image_path = views.get(key)
        _require(
            isinstance(image_path, str) and bool(image_path),
            f"missing {key} robot view image path",
            errors,
        )
        if isinstance(image_path, str) and image_path:
            errors.extend(
                error.replace("smoke image", f"{key} robot view")
                for error in _image_errors(Path(image_path))
            )
    if require_real_rendering:
        provenance_text = json.dumps(result.get("view_provenance"), sort_keys=True).lower()
        _require(
            "placeholder" not in provenance_text,
            "robot view provenance still reports placeholder visuals",
            errors,
        )
        _require(
            "isaac_lab_camera_rgb" in provenance_text,
            "robot view provenance does not show Isaac camera capture",
            errors,
        )
    return errors


def _robot_view_status(result: dict[str, Any]) -> str:
    if not result:
        return "not_checked"
    if result.get("ok") is not True:
        return "failed"
    views = _dict(result.get("views"))
    if all(views.get(key) for key in ROBOT_VIEW_KEYS):
        return "present"
    return "partial"


def _image_errors(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"smoke image is missing: {path}"]
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            stat = ImageStat.Stat(image.convert("RGB"))
            extrema = image.convert("RGB").getextrema()
    except Exception as exc:
        return [f"smoke image is unreadable: {exc}"]
    if all(high <= low for low, high in extrema):
        errors.append("smoke image appears blank")
    if max(stat.stddev or [0.0]) <= 0.0:
        errors.append("smoke image has no pixel variance")
    return errors


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _parse_last_json_object(text)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
