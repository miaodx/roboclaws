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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Isaac Lab runtime smoke evidence.")
    parser.add_argument("--init-result", type=Path, required=True)
    parser.add_argument("--state-path", type=Path)
    parser.add_argument("--require-real-rendering", action="store_true")
    parser.add_argument("--require-usd-stage-loaded", action="store_true")
    parser.add_argument("--require-usd-scene-index", action="store_true")
    parser.add_argument("--require-nonblank-image", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = _read_json(args.init_result)
    state = _read_json(args.state_path) if args.state_path else {}
    errors = validate(
        result=result,
        state=state,
        require_real_rendering=args.require_real_rendering,
        require_usd_stage_loaded=args.require_usd_stage_loaded,
        require_usd_scene_index=args.require_usd_scene_index,
        require_nonblank_image=args.require_nonblank_image,
    )
    summary = {
        "schema": SCHEMA,
        "status": "failed" if errors else "passed",
        "errors": errors,
        "backend": result.get("backend"),
        "runtime_mode": (result.get("runtime") or {}).get("runtime_mode"),
        "scene_usd": result.get("scene_usd"),
        "scene_index_status": (_dict(result.get("scene_index_diagnostics"))).get("status"),
    }
    print(json.dumps(summary, sort_keys=True))
    return 1 if errors else 0


def validate(
    *,
    result: dict[str, Any],
    state: dict[str, Any],
    require_real_rendering: bool,
    require_usd_stage_loaded: bool,
    require_usd_scene_index: bool,
    require_nonblank_image: bool,
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
    if require_nonblank_image:
        image_path = artifacts.get("runtime_smoke_image")
        _require(
            isinstance(image_path, str) and bool(image_path), "missing smoke image path", errors
        )
        if isinstance(image_path, str) and image_path:
            errors.extend(_image_errors(Path(image_path)))

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


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
