#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.renderer_comparison import _relpath
from scripts.isaac_lab_cleanup.isaac_lab_backend_worker import (
    ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
    ISAAC_SEMANTIC_POSE_STATE_SOURCE,
)

SCHEMA = "roboclaws_robot_camera_apple2apple_comparison_v1"
MUJOCO_LANE_ID = "molmospaces-mujoco-rby1m"
ISAAC_LANE_ID = "isaaclab-rby1m-usd"
ROBOT_VIEW_KEYS = ("fpv", "chase")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render-only apple-to-apple comparison for RBY1M FPV/chase cameras "
            "across MuJoCo and Isaac."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/molmo/robot-camera-apple2apple"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generated-mess-count", type=int, default=1)
    parser.add_argument("--scene-source", default="procthor-10k-val")
    parser.add_argument("--scene-index", type=int, default=1)
    parser.add_argument("--scene-usd-path", type=Path, required=True)
    parser.add_argument("--mujoco-python", type=Path, default=Path(".venv/bin/python"))
    parser.add_argument(
        "--isaac-python",
        type=Path,
        default=Path(".venv-isaaclab/bin/python"),
    )
    parser.add_argument("--render-width", type=int, default=540)
    parser.add_argument("--render-height", type=int, default=360)
    parser.add_argument("--location-count", type=int, default=4)
    args = parser.parse_args(argv)

    manifest = run_comparison(args)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"robot camera apple2apple manifest: {args.output_dir / 'comparison_manifest.json'}")
    print(f"robot camera apple2apple report: {args.output_dir / 'report.html'}")
    return 0 if manifest["status"] == "success" else 2


def run_comparison(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    mujoco_state_path = output_dir / "mujoco_state.json"
    isaac_state_path = output_dir / "isaac_state.json"
    mujoco_run_dir = output_dir / "mujoco"
    isaac_run_dir = output_dir / "isaac"

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "running",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "purpose": (
            "Sim-only render comparison of robot-view cameras. This does not execute "
            "cleanup, pick/place, scoring, or planner-backed manipulation proof."
        ),
        "scene": {
            "scene_source": args.scene_source,
            "scene_index": args.scene_index,
            "scene_usd_path": str(args.scene_usd_path),
            "seed": args.seed,
            "generated_mess_count": args.generated_mess_count,
            "render_width": args.render_width,
            "render_height": args.render_height,
        },
        "camera_contract": {
            "fpv": {
                MUJOCO_LANE_ID: "robot_0/head_camera",
                ISAAC_LANE_ID: "/World/robot_0/head_camera",
            },
            "chase": {
                MUJOCO_LANE_ID: "robot_0/camera_follower",
                ISAAC_LANE_ID: "external rear/high report camera",
            },
            "policy_input_note": "FPV is the robot camera. Chase is report evidence only.",
        },
        "lanes": {},
        "locations": [],
        "artifacts": {
            "manifest": "comparison_manifest.json",
            "report": "report.html",
        },
    }

    try:
        mujoco_init = _run_json(
            [
                str(args.mujoco_python),
                "scripts/molmo_cleanup/molmospaces_subprocess_worker.py",
                "--state-path",
                str(mujoco_state_path),
                "init",
                "--seed",
                str(args.seed),
                "--scene-source",
                args.scene_source,
                "--scene-index",
                str(args.scene_index),
                "--generated-mess-count",
                str(args.generated_mess_count),
                "--include-robot",
                "--robot-name",
                "rby1m",
            ],
            cwd=Path.cwd(),
        )
        isaac_init = _run_json(
            [
                str(args.isaac_python),
                "scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py",
                "--state-path",
                str(isaac_state_path),
                "init",
                "--run-dir",
                str(isaac_run_dir),
                "--seed",
                str(args.seed),
                "--scene-source",
                args.scene_source,
                "--scene-index",
                str(args.scene_index),
                "--generated-mess-count",
                str(args.generated_mess_count),
                "--runtime-mode",
                "real",
                "--include-robot",
                "--robot-name",
                "rby1m",
                "--scene-usd-path",
                str(args.scene_usd_path),
            ],
            cwd=Path.cwd(),
        )
    except Exception as exc:
        manifest["status"] = "blocked"
        manifest["blocker"] = str(exc)
        _write_outputs(manifest, output_dir)
        return manifest

    manifest["lanes"][MUJOCO_LANE_ID] = _lane_init_summary(mujoco_init)
    manifest["lanes"][ISAAC_LANE_ID] = _lane_init_summary(isaac_init)
    manifest["lanes"][ISAAC_LANE_ID]["robot_import"] = isaac_init.get("robot_import", {})

    mujoco_state = _read_json(mujoco_state_path)
    candidates = _comparison_targets(mujoco_state, limit=max(1, int(args.location_count)))
    if not candidates:
        manifest["status"] = "blocked"
        manifest["blocker"] = "No MuJoCo receptacle/object targets were available for robot poses."
        _write_outputs(manifest, output_dir)
        return manifest

    locations: list[dict[str, Any]] = []
    for index, target in enumerate(candidates, start=1):
        label = f"{index:04d}_{target['target_id']}"
        try:
            if target["kind"] == "receptacle":
                nav = _run_json(
                    [
                        str(args.mujoco_python),
                        "scripts/molmo_cleanup/molmospaces_subprocess_worker.py",
                        "--state-path",
                        str(mujoco_state_path),
                        "navigate_to_receptacle",
                        "--receptacle-id",
                        target["target_id"],
                    ],
                    cwd=Path.cwd(),
                )
            else:
                nav = _run_json(
                    [
                        str(args.mujoco_python),
                        "scripts/molmo_cleanup/molmospaces_subprocess_worker.py",
                        "--state-path",
                        str(mujoco_state_path),
                        "navigate_to_object",
                        "--object-id",
                        target["target_id"],
                    ],
                    cwd=Path.cwd(),
                )
            mujoco_state = _read_json(mujoco_state_path)
            robot_pose = dict(mujoco_state.get("robot_pose") or nav.get("robot_pose") or {})
            _patch_isaac_robot_pose(isaac_state_path, robot_pose, target=target)
            mujoco_views = _run_json(
                [
                    str(args.mujoco_python),
                    "scripts/molmo_cleanup/molmospaces_subprocess_worker.py",
                    "--state-path",
                    str(mujoco_state_path),
                    "robot_views",
                    "--output-dir",
                    str(mujoco_run_dir / "robot_views"),
                    "--label",
                    label,
                    "--render-width",
                    str(args.render_width),
                    "--render-height",
                    str(args.render_height),
                ],
                cwd=Path.cwd(),
            )
            isaac_views = _run_json(
                [
                    str(args.isaac_python),
                    "scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py",
                    "--state-path",
                    str(isaac_state_path),
                    "robot_views",
                    "--output-dir",
                    str(isaac_run_dir / "robot_views"),
                    "--label",
                    label,
                    "--render-width",
                    str(args.render_width),
                    "--render-height",
                    str(args.render_height),
                ],
                cwd=Path.cwd(),
            )
            locations.append(
                _location_result(
                    label=label,
                    target=target,
                    robot_pose=robot_pose,
                    mujoco_views=mujoco_views,
                    isaac_views=isaac_views,
                    output_dir=output_dir,
                )
            )
        except Exception as exc:
            locations.append(
                {
                    "label": label,
                    "target": target,
                    "status": "blocked",
                    "blocker": str(exc),
                }
            )

    manifest["locations"] = locations
    manifest["status"] = "success" if locations and all(item["status"] == "success" for item in locations) else "blocked"
    manifest["summary"] = _summary(locations)
    _write_outputs(manifest, output_dir)
    return manifest


def _run_json(command: list[str], *, cwd: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=360,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )
    return _parse_last_json_object(completed.stdout)


def _parse_last_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index in range(len(text) - 1, -1, -1):
        if text[index] != "{":
            continue
        try:
            value, end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if text[index + end :].strip():
            continue
        if isinstance(value, dict):
            return value
    raise RuntimeError(f"worker output did not end with a JSON object: {text[-1000:]}")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _comparison_targets(state: dict[str, Any], *, limit: int) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    for receptacle_id in sorted((state.get("receptacles") or {}).keys()):
        targets.append({"kind": "receptacle", "target_id": str(receptacle_id)})
        if len(targets) >= limit:
            return targets
    for object_id in sorted((state.get("objects") or {}).keys()):
        targets.append({"kind": "object", "target_id": str(object_id)})
        if len(targets) >= limit:
            return targets
    return targets


def _patch_isaac_robot_pose(
    state_path: Path,
    robot_pose: dict[str, Any],
    *,
    target: dict[str, str],
) -> None:
    state = _read_json(state_path)
    state["current_receptacle_id"] = target["target_id"] if target["kind"] == "receptacle" else state.get("current_receptacle_id")
    semantic_pose_state = dict(state.get("semantic_pose_state") or {})
    semantic_pose_state.update(
        {
            "schema": ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
            "state_source": ISAAC_SEMANTIC_POSE_STATE_SOURCE,
            "rendered_to_usd": False,
            "planner_backed": False,
            "physical_robot": False,
            "semantic_pose_only": True,
            "robot_pose": robot_pose,
            "comparison_pose_target": target,
        }
    )
    state["semantic_pose_state"] = semantic_pose_state
    _write_json(state_path, state)


def _lane_init_summary(init_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "backend": init_result.get("backend"),
        "ok": init_result.get("ok"),
        "runtime": init_result.get("runtime", {}),
        "scene_load": init_result.get("scene_load", {}),
        "scene_usd": init_result.get("scene_usd"),
        "robot": init_result.get("robot"),
    }


def _location_result(
    *,
    label: str,
    target: dict[str, str],
    robot_pose: dict[str, Any],
    mujoco_views: dict[str, Any],
    isaac_views: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    for view_key in ROBOT_VIEW_KEYS:
        mujoco_path = Path(str(mujoco_views["views"][view_key]))
        isaac_path = Path(str(isaac_views["views"][view_key]))
        comparisons[view_key] = _image_diff(mujoco_path, isaac_path)
    return {
        "label": label,
        "status": "success",
        "target": target,
        "robot_pose": robot_pose,
        "views": {
            "mujoco": {
                key: _relpath(Path(str(path)), output_dir)
                for key, path in dict(mujoco_views.get("views") or {}).items()
                if key in {"fpv", "chase", "map", "verify"}
            },
            "isaac": {
                key: _relpath(Path(str(path)), output_dir)
                for key, path in dict(isaac_views.get("views") or {}).items()
                if key in {"fpv", "chase", "map", "verify"}
            },
        },
        "contracts": {
            "mujoco": mujoco_views.get("camera_control_contract", {}),
            "isaac": isaac_views.get("camera_control_contract", {}),
        },
        "provenance": {
            "mujoco": mujoco_views.get("view_provenance", {}),
            "isaac": isaac_views.get("view_provenance", {}),
        },
        "image_diffs": comparisons,
    }


def _image_diff(left_path: Path, right_path: Path) -> dict[str, Any]:
    with Image.open(left_path) as left_raw, Image.open(right_path) as right_raw:
        left = left_raw.convert("RGB")
        right = right_raw.convert("RGB")
        if right.size != left.size:
            right = right.resize(left.size)
        diff = ImageChops.difference(left, right)
        stat = ImageStat.Stat(diff)
        mean_abs = sum(stat.mean) / len(stat.mean)
        rms = sum(value * value for value in stat.rms) ** 0.5 / len(stat.rms)
        extrema = diff.getextrema()
        nonzero = 0
        for pixel in diff.getdata():
            if pixel != (0, 0, 0):
                nonzero += 1
        return {
            "left": str(left_path),
            "right": str(right_path),
            "size": list(left.size),
            "mean_abs_rgb": round(float(mean_abs), 4),
            "rms_rgb": round(float(rms), 4),
            "max_channel_diff": max(max(channel) for channel in extrema),
            "nonzero_fraction": round(nonzero / max(left.size[0] * left.size[1], 1), 6),
        }


def _summary(locations: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [item for item in locations if item.get("status") == "success"]
    return {
        "location_count": len(locations),
        "successful_location_count": len(successful),
        "fpv_mean_abs_rgb_avg": _avg(
            _get_float(item, ("image_diffs", "fpv", "mean_abs_rgb")) for item in successful
        ),
        "chase_mean_abs_rgb_avg": _avg(
            _get_float(item, ("image_diffs", "chase", "mean_abs_rgb")) for item in successful
        ),
    }


def _get_float(item: dict[str, Any], path: tuple[str, ...]) -> float | None:
    value: Any = item
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(values: Any) -> float | None:
    collected = [value for value in values if value is not None]
    if not collected:
        return None
    return round(sum(collected) / len(collected), 4)


def _write_outputs(manifest: dict[str, Any], output_dir: Path) -> None:
    _write_json(output_dir / "comparison_manifest.json", manifest)
    (output_dir / "report.html").write_text(_render_report(manifest), encoding="utf-8")


def _render_report(manifest: dict[str, Any]) -> str:
    rows = []
    for item in manifest.get("locations") or []:
        if item.get("status") != "success":
            rows.append(
                "<section class='location'><h2>"
                + html.escape(str(item.get("label")))
                + "</h2><p class='bad'>"
                + html.escape(str(item.get("blocker")))
                + "</p></section>"
            )
            continue
        pairs = []
        for view_key in ROBOT_VIEW_KEYS:
            diff = item["image_diffs"][view_key]
            pairs.append(
                "<div class='pair'>"
                f"<h3>{html.escape(view_key.upper())}</h3>"
                "<figure><img src='"
                + html.escape(item["views"]["mujoco"][view_key])
                + "'><figcaption>MuJoCo</figcaption></figure>"
                "<figure><img src='"
                + html.escape(item["views"]["isaac"][view_key])
                + "'><figcaption>Isaac</figcaption></figure>"
                "<p>mean abs RGB "
                + html.escape(str(diff["mean_abs_rgb"]))
                + ", nonzero "
                + html.escape(str(diff["nonzero_fraction"]))
                + "</p></div>"
            )
        rows.append(
            "<section class='location'><h2>"
            + html.escape(str(item["label"]))
            + " <span>"
            + html.escape(str(item["target"]))
            + "</span></h2>"
            + "<pre>"
            + html.escape(json.dumps(item["robot_pose"], indent=2, sort_keys=True))
            + "</pre><div class='pairs'>"
            + "".join(pairs)
            + "</div></section>"
        )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>RBY1M Robot Camera Apple2Apple</title>"
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:24px;background:#f7f7f4;color:#202124}"
        "header,.location{max-width:1180px;margin:0 auto 18px;background:white;border:1px solid #d9d7ce;padding:16px}"
        "h1{margin:0 0 8px;font-size:24px}h2{font-size:18px;margin:0 0 10px}h2 span{font-weight:400;color:#5f6368}"
        ".pairs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.pair{border-top:1px solid #ece8dd;padding-top:10px}"
        "figure{margin:0 0 8px}img{display:block;width:100%;height:auto;border:1px solid #ddd;background:#111}"
        "figcaption,p{font-size:13px;color:#5f6368;margin:6px 0}pre{font-size:12px;background:#f4f1e8;padding:10px;overflow:auto}"
        ".bad{color:#9b1c1c}@media(max-width:800px){.pairs{grid-template-columns:1fr}}"
        "</style></head><body><header><h1>RBY1M Robot Camera Apple2Apple</h1>"
        "<p>"
        + html.escape(str(manifest.get("purpose")))
        + "</p><pre>"
        + html.escape(json.dumps(manifest.get("summary", {}), indent=2, sort_keys=True))
        + "</pre></header>"
        + "".join(rows)
        + "</body></html>"
    )


if __name__ == "__main__":
    raise SystemExit(main())
