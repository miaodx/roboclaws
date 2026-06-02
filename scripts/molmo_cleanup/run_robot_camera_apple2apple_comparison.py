#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import math
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.renderer_comparison import _relpath
from roboclaws.household.scene_camera_comparison import (
    _isaac_render_contract_from_usda,
    _isaac_view_render_contract,
    _mujoco_render_contract_from_xml,
    _mujoco_view_render_contract,
    _view_render_contract_delta,
)
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
    parser.add_argument(
        "--output-dir", type=Path, default=Path("output/molmo/robot-camera-apple2apple")
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generated-mess-count", type=int, default=1)
    parser.add_argument("--scene-source", default="procthor-10k-val")
    parser.add_argument("--scene-index", type=int, default=1)
    parser.add_argument("--scene-usd-path", type=Path)
    parser.add_argument("--mujoco-python", type=Path, default=Path(".venv/bin/python"))
    parser.add_argument(
        "--isaac-python",
        type=Path,
        default=Path(".venv-isaaclab/bin/python"),
    )
    parser.add_argument("--render-width", type=int, default=540)
    parser.add_argument("--render-height", type=int, default=360)
    parser.add_argument("--location-count", type=int, default=4)
    parser.add_argument(
        "--isaac-robot-view-color-profile-path",
        type=Path,
        help=(
            "Optional comparison-only color profile override for Isaac robot-view "
            "captures. This does not change default cleanup rendering."
        ),
    )
    parser.add_argument(
        "--light-shadow-probe-manifest",
        type=Path,
        action="append",
        default=[],
        help=(
            "Optional prior comparison manifest for a light/shadow-only probe. Repeat to "
            "attach no-dome, no-shadow, or MuJoCo-like light/shadow probe history to this "
            "report without changing default rendering."
        ),
    )
    parser.add_argument(
        "--refresh-report-only",
        action="store_true",
        help=(
            "Recompute report diagnostics from an existing output directory without "
            "re-rendering MuJoCo or Isaac views."
        ),
    )
    args = parser.parse_args(argv)

    if args.refresh_report_only:
        manifest = refresh_report_only(args.output_dir, args.light_shadow_probe_manifest)
    else:
        if args.scene_usd_path is None:
            parser.error("--scene-usd-path is required unless --refresh-report-only is set")
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
    isaac_robot_view_color_profile = _load_optional_json(args.isaac_robot_view_color_profile_path)

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
    _attach_state_artifact_summaries(
        manifest,
        output_dir=output_dir,
        mujoco_state=mujoco_state,
        isaac_state=_read_json(isaac_state_path),
    )
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
            _patch_isaac_robot_pose(
                isaac_state_path,
                robot_pose,
                target=target,
                color_profile=isaac_robot_view_color_profile,
            )
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
    manifest["status"] = (
        "success"
        if locations and all(item["status"] == "success" for item in locations)
        else "blocked"
    )
    _refresh_location_camera_contract_diagnostics(locations)
    manifest["summary"] = _summary(locations)
    _attach_render_contract_diagnostics(
        manifest,
        output_dir=output_dir,
        light_shadow_probe_manifest_paths=args.light_shadow_probe_manifest,
    )
    _write_outputs(manifest, output_dir)
    return manifest


def refresh_report_only(
    output_dir: Path,
    light_shadow_probe_manifest_paths: list[Path] | None = None,
) -> dict[str, Any]:
    manifest_path = output_dir / "comparison_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = _read_json(manifest_path)
    locations = list(manifest.get("locations") or [])
    _refresh_location_camera_contract_diagnostics(locations)
    manifest["summary"] = _summary(locations)
    _attach_render_contract_diagnostics(
        manifest,
        output_dir=output_dir,
        light_shadow_probe_manifest_paths=light_shadow_probe_manifest_paths,
    )
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


def _load_optional_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
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
    color_profile: dict[str, Any] | None = None,
) -> None:
    state = _read_json(state_path)
    state["current_receptacle_id"] = (
        target["target_id"]
        if target["kind"] == "receptacle"
        else state.get("current_receptacle_id")
    )
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
    if isinstance(color_profile, dict) and color_profile:
        state["robot_view_color_profile_override"] = dict(color_profile)
    else:
        state.pop("robot_view_color_profile_override", None)
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
        "camera_diagnostics": {
            "mujoco": mujoco_views.get("camera_diagnostics", {}),
            "isaac": isaac_views.get("camera_diagnostics", {}),
        },
        "camera_contract_diagnostics": _location_camera_contract_diagnostics(
            {
                "robot_pose": robot_pose,
                "contracts": {
                    "mujoco": mujoco_views.get("camera_control_contract", {}),
                    "isaac": isaac_views.get("camera_control_contract", {}),
                },
                "camera_diagnostics": {
                    "mujoco": mujoco_views.get("camera_diagnostics", {}),
                    "isaac": isaac_views.get("camera_diagnostics", {}),
                },
            }
        ),
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
        pixel_count = max(left.size[0] * left.size[1], 1)
        nonzero = 0
        diff_gt_40 = 0
        diff_gt_80 = 0
        for pixel in diff.getdata():
            if pixel != (0, 0, 0):
                nonzero += 1
            mean_pixel_delta = sum(pixel) / 3.0
            if mean_pixel_delta > 40.0:
                diff_gt_40 += 1
            if mean_pixel_delta > 80.0:
                diff_gt_80 += 1
        residual = _render_residual_diagnostics(left, right)
        return {
            "left": str(left_path),
            "right": str(right_path),
            "size": list(left.size),
            "mean_abs_rgb": round(float(mean_abs), 4),
            "rms_rgb": round(float(rms), 4),
            "max_channel_diff": max(max(channel) for channel in extrema),
            "nonzero_fraction": round(nonzero / pixel_count, 6),
            "diff_gt_40_fraction": round(diff_gt_40 / pixel_count, 6),
            "diff_gt_80_fraction": round(diff_gt_80 / pixel_count, 6),
            "residual": residual,
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
        "camera_contract_diagnostics": _camera_contract_diagnostics(successful),
        "residual_triage": _residual_triage(successful),
    }


def _refresh_location_camera_contract_diagnostics(locations: list[dict[str, Any]]) -> None:
    for item in locations:
        if not isinstance(item, dict) or item.get("status") != "success":
            continue
        item["camera_contract_diagnostics"] = _location_camera_contract_diagnostics(item)


def _attach_state_artifact_summaries(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    mujoco_state: dict[str, Any],
    isaac_state: dict[str, Any],
) -> None:
    lanes = manifest.setdefault("lanes", {})
    if not isinstance(lanes, dict):
        lanes = {}
        manifest["lanes"] = lanes
    mujoco_lane = lanes.setdefault(MUJOCO_LANE_ID, {})
    isaac_lane = lanes.setdefault(ISAAC_LANE_ID, {})
    if isinstance(mujoco_lane, dict):
        mujoco_lane["scene_xml"] = mujoco_state.get("scene_xml")
        mujoco_lane["robot_xml"] = mujoco_state.get("robot_xml")
    if isinstance(isaac_lane, dict):
        isaac_lane["scene_usd"] = isaac_state.get("scene_usd") or _dict(manifest.get("scene")).get(
            "scene_usd_path"
        )
        isaac_lane["scene_binding_summary"] = _scene_binding_summary(
            _dict(isaac_state.get("scene_binding_diagnostics"))
        )
    artifacts = manifest.setdefault("artifacts", {})
    if isinstance(artifacts, dict):
        artifacts["mujoco_state"] = _relpath(output_dir / "mujoco_state.json", output_dir)
        artifacts["isaac_state"] = _relpath(output_dir / "isaac_state.json", output_dir)


def _attach_render_contract_diagnostics(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    light_shadow_probe_manifest_paths: list[Path] | None = None,
) -> None:
    mujoco_state = _read_json(output_dir / "mujoco_state.json")
    isaac_state = _read_json(output_dir / "isaac_state.json")
    _attach_state_artifact_summaries(
        manifest,
        output_dir=output_dir,
        mujoco_state=mujoco_state,
        isaac_state=isaac_state,
    )
    mujoco_scene_xml = str(mujoco_state.get("scene_xml") or "")
    isaac_scene_usd = str(
        isaac_state.get("scene_usd") or _dict(manifest.get("scene")).get("scene_usd_path") or ""
    )
    mujoco_contract = _mujoco_render_contract_from_xml(mujoco_scene_xml)
    isaac_contract = _isaac_render_contract_from_usda(isaac_scene_usd)
    scene_binding_diagnostics = _dict(isaac_state.get("scene_binding_diagnostics"))
    room_delta = _view_render_contract_delta(
        suspicion="room_light_wall_shadow_contract",
        mujoco=_mujoco_view_render_contract(mujoco_contract, anchor_id=""),
        isaac=_isaac_view_render_contract(isaac_contract, usd_prim_path=""),
    )
    successful_locations = [
        item
        for item in manifest.get("locations") or []
        if isinstance(item, dict) and item.get("status") == "success"
    ]
    per_location = []
    for item in successful_locations:
        diagnostics = _location_render_contract_diagnostics(
            item,
            mujoco_contract=mujoco_contract,
            isaac_contract=isaac_contract,
            scene_binding_diagnostics=scene_binding_diagnostics,
        )
        item["render_contract_diagnostics"] = diagnostics
        per_location.append(diagnostics)
    summary = _render_contract_summary(
        mujoco_contract=mujoco_contract,
        isaac_contract=isaac_contract,
        room_delta=room_delta,
        per_location=per_location,
    )
    manifest["render_contract_diagnostics"] = summary
    manifest.setdefault("summary", {})["render_contract_diagnostics"] = summary
    domain_checks = _render_domain_checks(
        manifest=manifest,
        output_dir=output_dir,
        locations=successful_locations,
        mujoco_contract=mujoco_contract,
        isaac_contract=isaac_contract,
        room_delta=room_delta,
        per_location=per_location,
        isaac_state=isaac_state,
        light_shadow_probe_manifest_paths=light_shadow_probe_manifest_paths,
    )
    manifest["render_domain_checks"] = domain_checks
    manifest.setdefault("summary", {})["render_domain_checks"] = domain_checks


def _scene_binding_summary(scene_binding_diagnostics: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": scene_binding_diagnostics.get("schema"),
        "status": scene_binding_diagnostics.get("status"),
        "public_receptacle_bound_count": scene_binding_diagnostics.get(
            "public_receptacle_bound_count"
        ),
        "public_object_bound_count": scene_binding_diagnostics.get("public_object_bound_count"),
        "selected_object_bound_count": scene_binding_diagnostics.get("selected_object_bound_count"),
        "selected_target_receptacle_bound_count": scene_binding_diagnostics.get(
            "selected_target_receptacle_bound_count"
        ),
    }


def _location_render_contract_diagnostics(
    item: dict[str, Any],
    *,
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    scene_binding_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    target = _dict(item.get("target"))
    target_id = str(target.get("target_id") or "")
    target_binding = _target_usd_binding(scene_binding_diagnostics, target)
    usd_prim_path = str(target_binding.get("usd_prim_path") or "")
    mujoco_target = _mujoco_view_render_contract(mujoco_contract, anchor_id=target_id)
    isaac_target = _isaac_view_render_contract(isaac_contract, usd_prim_path=usd_prim_path)
    target_delta = _view_render_contract_delta(
        suspicion="object_material_texture_binding_contract",
        mujoco=mujoco_target,
        isaac=isaac_target,
    )
    fpv_residual = _dict_path(item, ("image_diffs", "fpv", "residual"))
    chase_residual = _dict_path(item, ("image_diffs", "chase", "residual"))
    return {
        "schema": "robot_camera_location_render_contract_diagnostics_v1",
        "target": target,
        "target_usd_binding": _compact_target_binding(target_binding),
        "fpv_residual_class": fpv_residual.get("residual_class"),
        "chase_residual_class": chase_residual.get("residual_class"),
        "mujoco_target_contract": mujoco_target,
        "isaac_target_contract": isaac_target,
        "target_contract_delta": target_delta,
        "interpretation": (
            "Target material/texture parity is checked from the MJCF scene XML and Isaac "
            "USD material bindings. High image residual can still remain when these names "
            "match because the two renderers use different light, shadow, tone response, "
            "and material models."
        ),
    }


def _target_usd_binding(
    scene_binding_diagnostics: dict[str, Any],
    target: dict[str, Any],
) -> dict[str, Any]:
    target_id = str(target.get("target_id") or "")
    if not target_id:
        return {}
    if target.get("kind") == "receptacle":
        groups = ("receptacle_bindings", "selected_target_receptacle_bindings")
    else:
        groups = ("object_bindings", "selected_object_bindings")
    for group in groups:
        bindings = _dict(scene_binding_diagnostics.get(group))
        binding = _dict(bindings.get(target_id))
        if binding:
            return binding
    return {}


def _compact_target_binding(binding: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "public_id",
        "kind",
        "category",
        "usd_prim_path",
        "match_strategy",
        "geometry_status",
        "has_renderable_geometry",
        "mesh_descendant_count",
        "renderable_descendant_count",
        "missing_referenced_asset_count",
    )
    return {key: binding.get(key) for key in keys if key in binding}


def _render_contract_summary(
    *,
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    room_delta: dict[str, Any],
    per_location: list[dict[str, Any]],
) -> dict[str, Any]:
    target_delta_statuses = [
        str(_dict(item.get("target_contract_delta")).get("status") or "") for item in per_location
    ]
    target_delta_counts = {
        name: target_delta_statuses.count(name)
        for name in sorted(set(target_delta_statuses))
        if name
    }
    high_priority_target_delta_count = sum(
        count
        for status, count in target_delta_counts.items()
        if status in {"material_or_texture_name_delta", "missing_object_binding_evidence"}
    )
    parse_ok = (
        mujoco_contract.get("status") == "parsed" and isaac_contract.get("status") == "parsed"
    )
    if not parse_ok:
        status = "partial_artifact_parse"
        next_action = "Resolve missing scene XML/USD artifacts before drawing renderer conclusions."
    elif high_priority_target_delta_count:
        status = "target_material_texture_or_binding_gap"
        next_action = (
            "Fix the target USD material binding or texture-name mismatch before treating "
            "the remaining residual as camera geometry."
        )
    elif room_delta.get("status") == "light_or_shadow_contract_delta":
        status = "lighting_shadow_contract_delta"
        next_action = (
            "Material/texture names mostly match for checked targets; align Isaac/MuJoCo "
            "light count, shadow flags, exposure, and tone response before changing FPV pose."
        )
    else:
        status = "checked_targets_material_texture_names_match"
        next_action = (
            "Checked target material/texture names match; prioritize renderer response and "
            "Isaac static head articulation over camera-source changes."
        )
    return {
        "schema": "robot_camera_render_contract_diagnostics_v1",
        "status": status,
        "mujoco_parse_status": mujoco_contract.get("status"),
        "isaac_parse_status": isaac_contract.get("status"),
        "mujoco_scene_xml": mujoco_contract.get("path"),
        "isaac_scene_usd": isaac_contract.get("path"),
        "mujoco_material_count": mujoco_contract.get("material_count"),
        "mujoco_texture_count": mujoco_contract.get("texture_count"),
        "mujoco_light_count": mujoco_contract.get("light_count"),
        "isaac_material_count": isaac_contract.get("material_count"),
        "isaac_bound_prim_count": isaac_contract.get("bound_prim_count"),
        "isaac_light_count": isaac_contract.get("light_count"),
        "isaac_shadow_disabled_prim_count": isaac_contract.get("shadow_disabled_prim_count"),
        "room_light_shadow_delta": room_delta,
        "target_location_count": len(per_location),
        "target_contract_delta_counts": target_delta_counts,
        "high_priority_target_delta_count": high_priority_target_delta_count,
        "recommended_next_action": next_action,
        "interpretation": (
            "This report separates camera-source parity from render-domain parity. FPV can "
            "be the correct head camera while Isaac still differs through static head "
            "articulation, USD PreviewSurface conversion, renderer lighting, shadow flags, "
            "and tone response."
        ),
    }


def _render_domain_checks(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    locations: list[dict[str, Any]],
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    room_delta: dict[str, Any],
    per_location: list[dict[str, Any]],
    isaac_state: dict[str, Any],
    light_shadow_probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    checks = [
        _light_shadow_contract_check(
            manifest=manifest,
            output_dir=output_dir,
            mujoco_contract=mujoco_contract,
            isaac_contract=isaac_contract,
            room_delta=room_delta,
            probe_manifest_paths=light_shadow_probe_manifest_paths,
        ),
        _texture_colorspace_material_response_check(per_location),
        _usd_preview_surface_material_model_check(per_location),
        _tone_color_response_check(locations, isaac_state=isaac_state),
    ]
    status_counts = {
        name: sum(1 for item in checks if item.get("status") == name)
        for name in sorted({str(item.get("status") or "") for item in checks if item.get("status")})
    }
    action_checks = [
        item
        for item in checks
        if item.get("status")
        not in {
            "material_texture_names_match_no_render_gap",
            "tone_color_lower_priority",
        }
    ]
    if mujoco_contract.get("status") != "parsed" or isaac_contract.get("status") != "parsed":
        status = "partial_artifact_parse"
        next_action = "Resolve missing scene XML/USD artifacts before render-domain triage."
    elif any(item.get("status") == "target_material_texture_or_binding_gap" for item in checks):
        status = "target_material_texture_or_binding_gap"
        next_action = (
            "Fix target USD binding, referenced assets, or material/texture-name mismatches "
            "before changing lights, color, or camera geometry."
        )
    elif action_checks:
        status = "render_domain_delta_confirmed"
        next_action = str(action_checks[0].get("recommended_next_action") or "")
    else:
        status = "render_domain_checks_low_priority"
        next_action = "Broaden scene/seed coverage before changing renderer settings."
    return {
        "schema": "robot_camera_render_domain_checks_v1",
        "status": status,
        "check_count": len(checks),
        "check_status_counts": status_counts,
        "checks": checks,
        "recommended_next_action": next_action,
        "interpretation": (
            "These four checks keep camera parity separate from render-domain parity. They "
            "summarize light/shadow contracts, material/texture response, USD PreviewSurface "
            "conversion, and tone/color calibration evidence from the same apple-to-apple "
            "robot-view report."
        ),
    }


def _light_shadow_contract_check(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    room_delta: dict[str, Any],
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    probe_history = _light_shadow_probe_history(
        manifest,
        output_dir=output_dir,
        probe_manifest_paths=probe_manifest_paths,
    )
    status = (
        "light_shadow_contract_delta"
        if room_delta.get("status") == "light_or_shadow_contract_delta"
        else "light_shadow_contract_aligned"
    )
    if probe_history.get("worsened_probe_count"):
        next_action = (
            "Do not promote the already-worse light/shadow probes directly; split light "
            "count, shadow flags, intensity/direction, and material response in the next "
            "comparison-only probe."
        )
    else:
        next_action = (
            "Compare Isaac stage lights and shadow-disabled wall/ceiling prims against the "
            "MuJoCo light setup before treating brightness differences as camera differences."
        )
    return {
        "check_id": "light_shadow_contract",
        "status": status,
        "mujoco_light_count": mujoco_contract.get("light_count"),
        "isaac_light_count": isaac_contract.get("light_count"),
        "isaac_shadow_disabled_prim_count": isaac_contract.get("shadow_disabled_prim_count"),
        "room_light_shadow_delta": room_delta,
        "probe_history": probe_history,
        "recommended_next_action": next_action,
    }


def _light_shadow_probe_history(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    paths = [Path(path) for path in probe_manifest_paths or []]
    if not paths:
        return {
            "schema": "robot_camera_light_shadow_probe_history_v1",
            "status": "not_attached",
            "probe_count": 0,
            "probes": [],
        }
    baseline = _probe_manifest_summary(
        manifest, manifest_path=output_dir / "comparison_manifest.json"
    )
    probes = []
    comparable_count = 0
    improved_count = 0
    worsened_count = 0
    for path in paths:
        probe = _load_light_shadow_probe_manifest(path, output_dir=output_dir)
        if probe.get("status") == "loaded":
            comparable = _light_shadow_probe_comparable(baseline, probe)
            probe["comparable_to_current"] = comparable
            if comparable:
                comparable_count += 1
            delta = _light_shadow_probe_delta(baseline, probe)
            probe["delta_vs_current"] = delta
            if delta.get("fpv_improvement") is True:
                improved_count += 1
            if delta.get("fpv_worse") is True:
                worsened_count += 1
        probes.append(probe)
    if improved_count:
        status = "prior_probe_improved"
    elif worsened_count and comparable_count:
        status = "prior_probes_worse"
    elif comparable_count:
        status = "prior_probes_no_fpv_gain"
    else:
        status = "no_comparable_probe"
    return {
        "schema": "robot_camera_light_shadow_probe_history_v1",
        "status": status,
        "baseline": baseline,
        "probe_count": len(probes),
        "comparable_probe_count": comparable_count,
        "improved_probe_count": improved_count,
        "worsened_probe_count": worsened_count,
        "probes": probes,
        "interpretation": (
            "Historical light/shadow probes are comparison evidence only. They prevent "
            "repeating a worse light/shadow edit as a default renderer change."
        ),
    }


def _load_light_shadow_probe_manifest(path: Path, *, output_dir: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "status": "missing_manifest",
            "path": _relpath(path, output_dir),
        }
    try:
        payload = _read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "read_failed",
            "path": _relpath(path, output_dir),
            "error": f"{type(exc).__name__}: {exc}",
        }
    return _probe_manifest_summary(payload, manifest_path=path, output_dir=output_dir)


def _probe_manifest_summary(
    payload: dict[str, Any],
    *,
    manifest_path: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    summary = _dict(payload.get("summary"))
    scene = _dict(payload.get("scene"))
    render = _dict(summary.get("render_contract_diagnostics"))
    camera = _dict(summary.get("camera_contract_diagnostics"))
    residual = _dict(summary.get("residual_triage"))
    fpv_lens = _dict(camera.get("fpv_lens_delta_summary"))
    fpv_pose = _dict(camera.get("fpv_world_pose_delta_summary"))
    rel_path = _relpath(manifest_path, output_dir or manifest_path.parent)
    return {
        "status": "loaded",
        "path": rel_path,
        "scene": {
            "scene_source": scene.get("scene_source"),
            "scene_index": scene.get("scene_index"),
            "seed": scene.get("seed"),
            "generated_mess_count": scene.get("generated_mess_count"),
            "render_width": scene.get("render_width"),
            "render_height": scene.get("render_height"),
            "scene_usd_path": scene.get("scene_usd_path"),
        },
        "location_count": summary.get("location_count"),
        "fpv_mean_abs_rgb_avg": summary.get("fpv_mean_abs_rgb_avg"),
        "chase_mean_abs_rgb_avg": summary.get("chase_mean_abs_rgb_avg"),
        "camera_contract_status": camera.get("status"),
        "fpv_lens_status": fpv_lens.get("status"),
        "fpv_world_pose_status": fpv_pose.get("status"),
        "render_contract_status": render.get("status"),
        "mujoco_light_count": render.get("mujoco_light_count"),
        "isaac_light_count": render.get("isaac_light_count"),
        "isaac_shadow_disabled_prim_count": render.get("isaac_shadow_disabled_prim_count"),
        "residual_status": residual.get("status"),
        "fpv_residual_classes": _dict_path(residual, ("views", "fpv", "residual_classes")),
    }


def _light_shadow_probe_comparable(
    baseline: dict[str, Any],
    probe: dict[str, Any],
) -> bool:
    baseline_scene = _dict(baseline.get("scene"))
    probe_scene = _dict(probe.get("scene"))
    keys = ("scene_source", "scene_index", "seed", "render_width", "render_height")
    if any(baseline_scene.get(key) != probe_scene.get(key) for key in keys):
        return False
    if probe.get("camera_contract_status") != baseline.get("camera_contract_status"):
        return False
    pose_status = probe.get("fpv_world_pose_status")
    baseline_pose_status = baseline.get("fpv_world_pose_status")
    if pose_status and baseline_pose_status and pose_status != baseline_pose_status:
        return False
    lens_status = probe.get("fpv_lens_status")
    baseline_lens_status = baseline.get("fpv_lens_status")
    if lens_status and baseline_lens_status and lens_status != baseline_lens_status:
        return False
    return True


def _light_shadow_probe_delta(
    baseline: dict[str, Any],
    probe: dict[str, Any],
) -> dict[str, Any]:
    baseline_fpv = _float_or_none(baseline.get("fpv_mean_abs_rgb_avg"))
    probe_fpv = _float_or_none(probe.get("fpv_mean_abs_rgb_avg"))
    baseline_chase = _float_or_none(baseline.get("chase_mean_abs_rgb_avg"))
    probe_chase = _float_or_none(probe.get("chase_mean_abs_rgb_avg"))
    fpv_delta = (
        round(float(probe_fpv - baseline_fpv), 4)
        if baseline_fpv is not None and probe_fpv is not None
        else None
    )
    chase_delta = (
        round(float(probe_chase - baseline_chase), 4)
        if baseline_chase is not None and probe_chase is not None
        else None
    )
    return {
        "fpv_mean_abs_rgb_delta": fpv_delta,
        "chase_mean_abs_rgb_delta": chase_delta,
        "fpv_improvement": fpv_delta is not None and fpv_delta < -1.0,
        "fpv_worse": fpv_delta is not None and fpv_delta > 1.0,
        "chase_improvement": chase_delta is not None and chase_delta < -1.0,
        "chase_worse": chase_delta is not None and chase_delta > 1.0,
    }


def _texture_colorspace_material_response_check(
    per_location: list[dict[str, Any]],
) -> dict[str, Any]:
    deltas = [_dict(item.get("target_contract_delta")) for item in per_location]
    delta_statuses = [str(item.get("status") or "") for item in deltas]
    delta_counts = {
        name: delta_statuses.count(name) for name in sorted(set(delta_statuses)) if name
    }
    bindings = [_dict(item.get("target_usd_binding")) for item in per_location]
    missing_ref_count = sum(
        int(binding.get("missing_referenced_asset_count") or 0) for binding in bindings
    )
    exact_public_id_count = sum(
        1 for binding in bindings if binding.get("match_strategy") == "exact_public_id"
    )
    texture_name_match_count = 0
    texture_path_basename_match_count = 0
    texture_path_full_delta_count = 0
    for item in per_location:
        mujoco = _dict(item.get("mujoco_target_contract"))
        isaac = _dict(item.get("isaac_target_contract"))
        mujoco_names = {Path(str(value)).name for value in mujoco.get("texture_files") or []}
        isaac_names = {Path(str(value)).name for value in isaac.get("texture_files") or []}
        if mujoco_names or isaac_names:
            texture_name_match_count += int(mujoco_names == isaac_names)
        mujoco_paths = {str(value) for value in mujoco.get("texture_files") or []}
        isaac_paths = {str(value) for value in isaac.get("texture_files") or []}
        if mujoco_names and mujoco_names == isaac_names:
            texture_path_basename_match_count += 1
            if mujoco_paths != isaac_paths:
                texture_path_full_delta_count += 1
    high_priority_count = sum(
        count
        for name, count in delta_counts.items()
        if name in {"material_or_texture_name_delta", "missing_object_binding_evidence"}
    )
    if high_priority_count or missing_ref_count:
        status = "target_material_texture_or_binding_gap"
    elif texture_path_full_delta_count:
        status = "texture_basenames_match_paths_or_colorspace_unverified"
    elif delta_counts.get("material_texture_names_match") == len(per_location):
        status = "material_texture_names_match_no_render_gap"
    else:
        status = "material_texture_response_unverified"
    return {
        "check_id": "texture_colorspace_material_response",
        "status": status,
        "target_location_count": len(per_location),
        "target_contract_delta_counts": delta_counts,
        "exact_public_id_binding_count": exact_public_id_count,
        "missing_referenced_asset_count": missing_ref_count,
        "texture_name_match_count": texture_name_match_count,
        "texture_path_basename_match_count": texture_path_basename_match_count,
        "texture_path_full_delta_count": texture_path_full_delta_count,
        "recommended_next_action": (
            "For high-residual FPV views, compare texture color space, sampler behavior, "
            "material albedo, and roughness/specular response even when texture basenames match."
        ),
    }


def _usd_preview_surface_material_model_check(
    per_location: list[dict[str, Any]],
) -> dict[str, Any]:
    isaac_binding_count = 0
    preview_surface_binding_count = 0
    diffuse_texture_binding_count = 0
    mujoco_visual_count = 0
    mujoco_rgba_visual_count = 0
    for item in per_location:
        isaac = _dict(item.get("isaac_target_contract"))
        for binding in isaac.get("bindings") or []:
            if not isinstance(binding, dict):
                continue
            isaac_binding_count += 1
            preview_surface_binding_count += int(bool(binding.get("has_preview_surface")))
            diffuse_texture_binding_count += int(bool(binding.get("has_diffuse_texture")))
        mujoco = _dict(item.get("mujoco_target_contract"))
        for visual in mujoco.get("visuals") or []:
            if not isinstance(visual, dict):
                continue
            mujoco_visual_count += 1
            mujoco_rgba_visual_count += int(bool(visual.get("rgba")))
    if isaac_binding_count == 0 or mujoco_visual_count == 0:
        status = "preview_surface_material_evidence_missing"
    elif preview_surface_binding_count < isaac_binding_count:
        status = "usd_preview_surface_binding_gap"
    else:
        status = "usd_preview_surface_vs_mujoco_material_model_delta"
    return {
        "check_id": "usd_preview_surface_material_model",
        "status": status,
        "isaac_material_binding_count": isaac_binding_count,
        "isaac_preview_surface_binding_count": preview_surface_binding_count,
        "isaac_diffuse_texture_binding_count": diffuse_texture_binding_count,
        "mujoco_visual_count": mujoco_visual_count,
        "mujoco_rgba_visual_count": mujoco_rgba_visual_count,
        "recommended_next_action": (
            "Inspect USD PreviewSurface diffuse texture/color, roughness, opacity, and "
            "specular conversion against the MJCF material RGBA/texture inputs before "
            "changing the camera contract."
        ),
    }


def _tone_color_response_check(
    locations: list[dict[str, Any]],
    *,
    isaac_state: dict[str, Any],
) -> dict[str, Any]:
    triage = _residual_triage(locations)
    fpv = _dict_path(triage, ("views", "fpv"))
    mean_abs = _float_or_none(fpv.get("mean_abs_rgb_avg"))
    oracle_abs = _float_or_none(fpv.get("rgb_gain_oracle_mean_abs_rgb_avg"))
    improvement_fraction = None
    if mean_abs is not None and oracle_abs is not None and mean_abs > 0.0:
        improvement_fraction = max(0.0, (mean_abs - oracle_abs) / mean_abs)
    color_profile = _dict(isaac_state.get("robot_view_color_profile"))
    color_override = _dict(isaac_state.get("robot_view_color_profile_override"))
    rgb_gain = _dict(color_override.get("backend_rgb_gain")) or _dict(
        color_profile.get("backend_rgb_gain")
    )
    comparison_gain_applied = bool(rgb_gain)
    if mean_abs is None:
        status = "tone_color_metrics_missing"
    elif improvement_fraction is not None and improvement_fraction >= 0.1:
        status = (
            "tone_color_delta_remaining_after_comparison_gain"
            if comparison_gain_applied
            else "tone_color_delta_rgb_oracle"
        )
    elif mean_abs <= 35.0:
        status = "tone_color_lower_priority"
    else:
        status = "tone_color_response_unverified"
    return {
        "check_id": "tone_color_response",
        "status": status,
        "fpv_mean_abs_rgb_avg": mean_abs,
        "fpv_rgb_gain_oracle_mean_abs_rgb_avg": oracle_abs,
        "rgb_gain_oracle_improvement_fraction": round(float(improvement_fraction), 6)
        if improvement_fraction is not None
        else None,
        "comparison_rgb_gain_applied": comparison_gain_applied,
        "comparison_rgb_gain": rgb_gain,
        "comparison_only": True,
        "residual_triage_status": triage.get("status"),
        "recommended_next_action": (
            "Keep RGB gain as comparison-only until it improves a broader post-FOV corpus; "
            "use per-view oracle gain to separate color response from geometry/material residuals."
        ),
    }


def _camera_contract_diagnostics(locations: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics = [
        _location_camera_contract_diagnostics(item)
        for item in locations
        if item.get("status") == "success"
    ]
    fpv_head_camera_count = sum(
        1 for item in diagnostics if item.get("fpv_head_camera_contract") is True
    )
    pose_match_count = sum(1 for item in diagnostics if item.get("robot_pose_match") is True)
    static_import_count = sum(
        1 for item in diagnostics if _dict(item.get("isaac_robot_import")).get("static_only")
    )
    head_pitch_gap_count = sum(
        1
        for item in diagnostics
        if _dict(item.get("head_articulation")).get("status")
        == "isaac_static_head_pitch_not_applied"
    )
    lens_gap_count = sum(
        1
        for item in diagnostics
        if _dict(item.get("fpv_lens_delta")).get("status") == "fpv_lens_contract_delta"
    )
    chase_same_camera_count = sum(
        1 for item in diagnostics if _dict(item.get("chase_contract")).get("same_camera_contract")
    )
    if diagnostics and fpv_head_camera_count < len(diagnostics):
        status = "fpv_head_camera_contract_mismatch"
        next_action = "Fix FPV source first; both backends must use robot-mounted head camera."
    elif diagnostics and pose_match_count < len(diagnostics):
        status = "robot_pose_contract_mismatch"
        next_action = "Fix shared robot root pose/yaw before changing renderer or assets."
    elif head_pitch_gap_count:
        status = "fpv_contract_shared_with_static_head_articulation_gap"
        next_action = (
            "FPV uses head cameras and shared root pose, but Isaac static robot import does "
            "not apply head pitch; test articulated Isaac import or a proven head-link transform."
        )
    elif lens_gap_count:
        status = "fpv_contract_shared_with_lens_gap"
        next_action = (
            "FPV uses head cameras and shared root pose, but lens/FOV differs; align Isaac "
            "head-camera vertical FOV before triaging renderer or material residuals."
        )
    elif static_import_count:
        status = "fpv_contract_shared_with_static_head_camera_pitch_correction"
        next_action = (
            "FPV uses head cameras and shared root pose, and Isaac applies a static "
            "head-camera pitch correction; articulated Isaac import remains the stronger "
            "long-term parity target."
        )
    elif diagnostics:
        status = "fpv_head_camera_pose_contract_shared"
        next_action = (
            "Camera contract is shared enough for this probe; inspect renderer/material residuals."
        )
    else:
        status = "no_successful_camera_contracts"
        next_action = "Run at least one successful comparison location."
    chase_note = (
        "Chase is report evidence only. It is not expected to be the same camera contract "
        "unless both backends explicitly use the same chase camera model."
    )
    return {
        "schema": "robot_camera_contract_diagnostics_v1",
        "status": status,
        "location_count": len(diagnostics),
        "fpv_head_camera_contract_count": fpv_head_camera_count,
        "robot_pose_match_count": pose_match_count,
        "isaac_static_import_count": static_import_count,
        "isaac_static_head_pitch_gap_count": head_pitch_gap_count,
        "fpv_lens_gap_count": lens_gap_count,
        "chase_same_camera_contract_count": chase_same_camera_count,
        "fpv_world_pose_delta_summary": _fpv_world_pose_delta_summary(diagnostics),
        "fpv_lens_delta_summary": _fpv_lens_delta_summary(diagnostics),
        "chase_note": chase_note,
        "recommended_next_action": next_action,
    }


def _fpv_world_pose_delta_summary(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    ready = [
        _dict(item.get("fpv_world_pose_delta"))
        for item in diagnostics
        if _dict(item.get("fpv_world_pose_delta")).get("status") == "ready"
    ]
    position_deltas = [
        value
        for value in (_float_or_none(item.get("position_delta_m")) for item in ready)
        if value is not None
    ]
    forward_angle_deltas = [
        value
        for value in (_float_or_none(item.get("forward_angle_delta_deg")) for item in ready)
        if value is not None
    ]
    max_position_delta = max(position_deltas) if position_deltas else None
    max_forward_angle_delta = max(forward_angle_deltas) if forward_angle_deltas else None
    if not diagnostics:
        status = "no_successful_camera_contracts"
    elif len(ready) < len(diagnostics):
        status = "missing_fpv_world_pose_metadata"
    elif (
        max_position_delta is not None
        and max_position_delta <= 0.01
        and (max_forward_angle_delta is None or max_forward_angle_delta <= 0.05)
    ):
        status = "fpv_world_pose_aligned"
    elif (
        max_position_delta is not None
        and max_position_delta <= 0.05
        and (max_forward_angle_delta is None or max_forward_angle_delta <= 0.5)
    ):
        status = "fpv_world_pose_near_aligned"
    else:
        status = "fpv_world_pose_delta"
    return {
        "schema": "robot_camera_fpv_world_pose_delta_summary_v1",
        "status": status,
        "ready_count": len(ready),
        "location_count": len(diagnostics),
        "position_delta_m_avg": _avg(value for value in position_deltas),
        "position_delta_m_max": round(float(max_position_delta), 6)
        if max_position_delta is not None
        else None,
        "forward_angle_delta_deg_avg": _avg(value for value in forward_angle_deltas),
        "forward_angle_delta_deg_max": round(float(max_forward_angle_delta), 6)
        if max_forward_angle_delta is not None
        else None,
        "interpretation": (
            "Compares MuJoCo robot_0/head_camera and Isaac /World/robot_0/head_camera "
            "world-space position and forward axis. Small deltas mean remaining image "
            "differences should be triaged as renderer/material/lighting issues before "
            "changing FPV camera geometry."
        ),
    }


def _fpv_lens_delta_summary(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    ready = [
        _dict(item.get("fpv_lens_delta"))
        for item in diagnostics
        if _dict(item.get("fpv_lens_delta")).get("status")
        in {"fpv_lens_aligned", "fpv_lens_near_aligned", "fpv_lens_contract_delta"}
    ]
    vertical_fov_deltas = [
        value
        for value in (_float_or_none(item.get("vertical_fov_delta_deg")) for item in ready)
        if value is not None
    ]
    max_vertical_fov_delta = max(vertical_fov_deltas) if vertical_fov_deltas else None
    if not diagnostics:
        status = "no_successful_camera_contracts"
    elif len(ready) < len(diagnostics):
        status = "missing_fpv_lens_metadata"
    elif max_vertical_fov_delta is not None and max_vertical_fov_delta <= 0.25:
        status = "fpv_lens_aligned"
    elif max_vertical_fov_delta is not None and max_vertical_fov_delta <= 1.0:
        status = "fpv_lens_near_aligned"
    else:
        status = "fpv_lens_contract_delta"
    return {
        "schema": "robot_camera_fpv_lens_delta_summary_v1",
        "status": status,
        "ready_count": len(ready),
        "location_count": len(diagnostics),
        "vertical_fov_delta_deg_avg": _avg(value for value in vertical_fov_deltas),
        "vertical_fov_delta_deg_max": round(float(max_vertical_fov_delta), 6)
        if max_vertical_fov_delta is not None
        else None,
        "interpretation": (
            "Compares MuJoCo head-camera fovy with Isaac USD head-camera equivalent "
            "vertical FOV. Small deltas mean apparent zoom/framing differences should "
            "be triaged as renderer/material/geometry rather than camera intrinsics."
        ),
    }


def _location_camera_contract_diagnostics(item: dict[str, Any]) -> dict[str, Any]:
    contracts = _dict(item.get("contracts"))
    camera_diagnostics = _dict(item.get("camera_diagnostics"))
    mujoco_contract = _dict(contracts.get("mujoco"))
    isaac_contract = _dict(contracts.get("isaac"))
    requested_pose = _dict(item.get("robot_pose"))
    mujoco_pose_delta = _robot_pose_delta(requested_pose, _dict(mujoco_contract.get("robot_pose")))
    isaac_pose_delta = _robot_pose_delta(requested_pose, _dict(isaac_contract.get("robot_pose")))
    mujoco_fpv = _dict(mujoco_contract.get("agent_facing_fpv"))
    isaac_fpv = _dict(isaac_contract.get("agent_facing_fpv"))
    fpv_head_camera_contract = _is_head_camera_fpv(mujoco_fpv) and _is_head_camera_fpv(isaac_fpv)
    robot_pose_match = (
        mujoco_pose_delta.get("status") == "match" and isaac_pose_delta.get("status") == "match"
    )
    isaac_import = _isaac_robot_import_diagnostics(isaac_contract)
    head_articulation = _head_articulation_diagnostics(
        requested_pose=requested_pose,
        mujoco_contract=mujoco_contract,
        isaac_contract=isaac_contract,
        isaac_import=isaac_import,
        isaac_camera_metadata=_compact_camera_metadata(camera_diagnostics, "isaac", "fpv"),
    )
    mujoco_fpv_metadata = _compact_camera_metadata(camera_diagnostics, "mujoco", "fpv")
    isaac_fpv_metadata = _compact_camera_metadata(camera_diagnostics, "isaac", "fpv")
    return {
        "schema": "robot_camera_location_contract_diagnostics_v1",
        "fpv_head_camera_contract": fpv_head_camera_contract,
        "robot_pose_match": robot_pose_match,
        "mujoco_pose_delta": mujoco_pose_delta,
        "isaac_pose_delta": isaac_pose_delta,
        "fpv_world_pose_delta": _fpv_world_pose_delta(
            mujoco_fpv_metadata,
            isaac_fpv_metadata,
        ),
        "fpv_lens_delta": _fpv_lens_delta(
            mujoco_fpv_metadata,
            isaac_fpv_metadata,
        ),
        "mujoco_fpv": {
            "source": mujoco_fpv.get("source"),
            "robot_mounted": mujoco_fpv.get("robot_mounted"),
            "head_camera_equivalent": mujoco_fpv.get("head_camera_equivalent"),
        },
        "isaac_fpv": {
            "source": isaac_fpv.get("source"),
            "camera_prim_path": isaac_fpv.get("camera_prim_path"),
            "robot_mounted": isaac_fpv.get("robot_mounted"),
            "head_camera_equivalent": isaac_fpv.get("head_camera_equivalent"),
        },
        "isaac_robot_import": isaac_import,
        "fpv_camera_metadata": {
            "mujoco": mujoco_fpv_metadata,
            "isaac": isaac_fpv_metadata,
        },
        "head_articulation": head_articulation,
        "chase_contract": _chase_contract_diagnostics(mujoco_contract, isaac_contract),
    }


def _is_head_camera_fpv(fpv: dict[str, Any]) -> bool:
    source = str(fpv.get("source") or "")
    prim_path = str(fpv.get("camera_prim_path") or "")
    return bool(fpv.get("robot_mounted")) and (
        "head_camera" in source or "head_camera" in prim_path
    )


def _compact_camera_metadata(
    camera_diagnostics: dict[str, Any],
    lane: str,
    view_key: str,
) -> dict[str, Any]:
    view = _dict(_dict(_dict(camera_diagnostics.get(lane)).get("views")).get(view_key))
    if not view:
        return {"status": "missing_camera_metadata"}
    keys = (
        "schema",
        "status",
        "camera_type",
        "camera_name",
        "prim_path",
        "world_position",
        "forward_world",
        "world_matrix_rowmajor",
        "fovy_deg",
        "focal_length_mm",
        "horizontal_aperture_mm",
        "vertical_aperture_mm",
        "vertical_fov_deg",
        "horizontal_fov_deg",
        "clipping_range",
        "render_resolution",
        "lens_application",
        "robot_pose_stage_application",
    )
    return {key: view.get(key) for key in keys if key in view}


def _fpv_world_pose_delta(
    mujoco_metadata: dict[str, Any],
    isaac_metadata: dict[str, Any],
) -> dict[str, Any]:
    mujoco_position = _vec3_or_none(mujoco_metadata.get("world_position"))
    isaac_position = _vec3_or_none(isaac_metadata.get("world_position"))
    if isaac_position is None:
        matrix_position = _matrix_translation_or_none(isaac_metadata.get("world_matrix_rowmajor"))
        isaac_position = matrix_position
    if mujoco_position is None or isaac_position is None:
        return {
            "schema": "robot_camera_fpv_world_pose_delta_v1",
            "status": "missing_world_position_metadata",
        }
    position_delta = _vec_distance(mujoco_position, isaac_position)
    mujoco_forward = _vec3_or_none(mujoco_metadata.get("forward_world"))
    isaac_forward = _vec3_or_none(isaac_metadata.get("forward_world"))
    if isaac_forward is None:
        isaac_forward = _matrix_forward_or_none(isaac_metadata.get("world_matrix_rowmajor"))
    forward_angle_delta = _vec_angle_deg(mujoco_forward, isaac_forward)
    return {
        "schema": "robot_camera_fpv_world_pose_delta_v1",
        "status": "ready",
        "mujoco_world_position": [round(value, 6) for value in mujoco_position],
        "isaac_world_position": [round(value, 6) for value in isaac_position],
        "position_delta_m": round(float(position_delta), 6),
        "forward_angle_delta_deg": round(float(forward_angle_delta), 6)
        if forward_angle_delta is not None
        else None,
        "note": (
            "MuJoCo exposes fixed-camera world_position but not always an orientation "
            "vector in this probe. Isaac orientation is read from world_matrix_rowmajor "
            "when present."
        ),
    }


def _fpv_lens_delta(
    mujoco_metadata: dict[str, Any],
    isaac_metadata: dict[str, Any],
) -> dict[str, Any]:
    mujoco_vertical_fov = _float_or_none(mujoco_metadata.get("fovy_deg"))
    isaac_vertical_fov = _float_or_none(isaac_metadata.get("vertical_fov_deg"))
    if isaac_vertical_fov is None:
        isaac_vertical_fov = _isaac_vertical_fov_from_metadata(isaac_metadata)
    if mujoco_vertical_fov is None or isaac_vertical_fov is None:
        return {
            "schema": "robot_camera_fpv_lens_delta_v1",
            "status": "missing_fpv_lens_metadata",
        }
    vertical_fov_delta = abs(float(mujoco_vertical_fov) - float(isaac_vertical_fov))
    if vertical_fov_delta <= 0.25:
        status = "fpv_lens_aligned"
    elif vertical_fov_delta <= 1.0:
        status = "fpv_lens_near_aligned"
    else:
        status = "fpv_lens_contract_delta"
    return {
        "schema": "robot_camera_fpv_lens_delta_v1",
        "status": status,
        "mujoco_vertical_fov_deg": round(float(mujoco_vertical_fov), 6),
        "isaac_vertical_fov_deg": round(float(isaac_vertical_fov), 6),
        "vertical_fov_delta_deg": round(float(vertical_fov_delta), 6),
        "isaac_focal_length_mm": _float_or_none(isaac_metadata.get("focal_length_mm")),
        "isaac_horizontal_aperture_mm": _float_or_none(
            isaac_metadata.get("horizontal_aperture_mm")
        ),
        "note": (
            "MuJoCo fixed camera fovy is vertical FOV. Isaac USD camera stores focal "
            "length and horizontal aperture, so this derives equivalent vertical FOV "
            "from the render aspect ratio when diagnostics do not provide it directly."
        ),
    }


def _isaac_vertical_fov_from_metadata(metadata: dict[str, Any]) -> float | None:
    focal_length = _float_or_none(metadata.get("focal_length_mm"))
    horizontal_aperture = _float_or_none(metadata.get("horizontal_aperture_mm"))
    resolution = _dict(metadata.get("render_resolution"))
    width = _float_or_none(resolution.get("width"))
    height = _float_or_none(resolution.get("height"))
    if (
        focal_length is None
        or horizontal_aperture is None
        or width is None
        or height is None
        or focal_length <= 0.0
        or width <= 0.0
        or height <= 0.0
    ):
        return None
    vertical_aperture = float(horizontal_aperture) * float(height) / float(width)
    return math.degrees(2.0 * math.atan(vertical_aperture / (2.0 * float(focal_length))))


def _vec3_or_none(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return None


def _matrix_translation_or_none(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        return None
    try:
        return (float(value[12]), float(value[13]), float(value[14]))
    except (TypeError, ValueError):
        return None


def _matrix_forward_or_none(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        return None
    try:
        return (float(-value[8]), float(-value[9]), float(-value[10]))
    except (TypeError, ValueError):
        return None


def _vec_distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def _vec_angle_deg(
    left: tuple[float, float, float] | None,
    right: tuple[float, float, float] | None,
) -> float | None:
    if left is None or right is None:
        return None
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return None
    dot = sum(left[index] * right[index] for index in range(3)) / (left_norm * right_norm)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def _robot_pose_delta(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    expected_x = _float_or_none(expected.get("x"))
    expected_y = _float_or_none(expected.get("y"))
    actual_x = _float_or_none(actual.get("x"))
    actual_y = _float_or_none(actual.get("y"))
    if None in {expected_x, expected_y, actual_x, actual_y}:
        return {"status": "missing_pose"}
    xy_error = ((expected_x - actual_x) ** 2 + (expected_y - actual_y) ** 2) ** 0.5
    expected_yaw = _pose_yaw_deg(expected)
    actual_yaw = _pose_yaw_deg(actual)
    yaw_error = _angle_delta_deg(expected_yaw, actual_yaw)
    expected_head_pitch = _float_or_none(expected.get("head_pitch"))
    actual_head_pitch = _float_or_none(actual.get("head_pitch"))
    head_pitch_error = (
        abs(expected_head_pitch - actual_head_pitch)
        if expected_head_pitch is not None and actual_head_pitch is not None
        else None
    )
    yaw_match = yaw_error is None or yaw_error <= 0.001
    head_pitch_match = head_pitch_error is None or head_pitch_error <= 0.0001
    status = "match" if xy_error <= 0.0001 and yaw_match and head_pitch_match else "mismatch"
    return {
        "status": status,
        "xy_error_m": round(float(xy_error), 6),
        "yaw_error_deg": round(float(yaw_error), 6) if yaw_error is not None else None,
        "head_pitch_error_rad": round(float(head_pitch_error), 6)
        if head_pitch_error is not None
        else None,
    }


def _pose_yaw_deg(pose: dict[str, Any]) -> float | None:
    yaw = _float_or_none(pose.get("yaw_deg"))
    if yaw is not None:
        return yaw
    theta = _float_or_none(pose.get("theta"))
    if theta is None:
        return None
    return theta * 180.0 / 3.141592653589793


def _angle_delta_deg(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return abs((left - right + 180.0) % 360.0 - 180.0)


def _isaac_robot_import_diagnostics(isaac_contract: dict[str, Any]) -> dict[str, Any]:
    robot_asset = _dict(isaac_contract.get("robot_asset"))
    import_summary = _dict(robot_asset.get("import_summary"))
    converter = _dict(import_summary.get("converter"))
    fallback = _dict(converter.get("fallback"))
    static_only = bool(import_summary.get("static_only")) or (
        fallback.get("status") == "ready"
        and str(import_summary.get("import_method") or "").endswith("static_visual_usd_fallback")
    )
    return {
        "status": robot_asset.get("status"),
        "import_method": import_summary.get("import_method") or robot_asset.get("import_method"),
        "static_only": static_only,
        "head_camera_mounted": robot_asset.get("head_camera_mounted"),
        "head_camera_equivalent": robot_asset.get("head_camera_equivalent"),
        "head_camera_prim_path": robot_asset.get("head_camera_prim_path")
        or isaac_contract.get("camera_prim_path"),
        "head_link_name": robot_asset.get("head_link_name"),
        "required_joints": robot_asset.get("required_joints")
        or _dict(import_summary.get("urdf")).get("required_joints")
        or [],
        "missing_mesh_count": fallback.get("missing_mesh_count"),
        "unsupported_mesh_count": fallback.get("unsupported_mesh_count"),
    }


def _head_articulation_diagnostics(
    *,
    requested_pose: dict[str, Any],
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    isaac_import: dict[str, Any],
    isaac_camera_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requested_head_pitch = _float_or_none(requested_pose.get("head_pitch"))
    mujoco_head_pitch = _float_or_none(_dict(mujoco_contract.get("robot_pose")).get("head_pitch"))
    isaac_head_pitch = _float_or_none(_dict(isaac_contract.get("robot_pose")).get("head_pitch"))
    if requested_head_pitch is None:
        status = "head_pitch_not_requested"
    elif _isaac_head_pitch_applied(isaac_contract, isaac_camera_metadata):
        status = "isaac_static_head_pitch_applied_to_head_camera"
    elif isaac_import.get("static_only"):
        status = "isaac_static_head_pitch_not_applied"
    else:
        status = "head_pitch_application_not_reported"
    return {
        "status": status,
        "requested_head_pitch_rad": requested_head_pitch,
        "mujoco_contract_head_pitch_rad": mujoco_head_pitch,
        "isaac_contract_head_pitch_rad": isaac_head_pitch,
        "isaac_static_only": bool(isaac_import.get("static_only")),
        "isaac_head_pitch_applied": _isaac_head_pitch_applied(
            isaac_contract, isaac_camera_metadata
        ),
        "evidence_note": (
            "MuJoCo robot views use qpos-backed robot joints. Isaac is still a static visual "
            "robot import unless an articulated import succeeds, but it may apply a static "
            "head-camera transform correction that records head_pitch_applied=true."
        ),
    }


def _isaac_head_pitch_applied(
    isaac_contract: dict[str, Any],
    isaac_camera_metadata: dict[str, Any] | None = None,
) -> bool:
    metadata_application = _dict(_dict(isaac_camera_metadata).get("robot_pose_stage_application"))
    if metadata_application.get("head_pitch_applied") is True:
        return True
    capture = _dict(
        _dict(_dict(isaac_contract.get("robot_asset")).get("semantic_pose_view_capture")).get(
            "robot_pose_stage_application"
        )
    )
    if capture.get("head_pitch_applied") is True:
        return True
    return (
        _dict(_dict(isaac_contract.get("robot_pose_stage_application"))).get("head_pitch_applied")
        is True
    )


def _chase_contract_diagnostics(
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
) -> dict[str, Any]:
    mujoco_source = str(_dict(mujoco_contract.get("report_verify_view")).get("source") or "")
    isaac_source = str(_dict(isaac_contract.get("report_verify_view")).get("source") or "")
    return {
        "same_camera_contract": False,
        "mujoco_source": "robot_0/camera_follower",
        "isaac_source": "external rear/high report camera",
        "mujoco_verify_source": mujoco_source,
        "isaac_verify_source": isaac_source,
        "evidence_note": (
            "Chase is auxiliary report evidence; FPV is the policy/input camera contract."
        ),
    }


def _render_residual_diagnostics(left: Image.Image, right: Image.Image) -> dict[str, Any]:
    left = left.convert("RGB")
    right = right.convert("RGB")
    if right.size != left.size:
        right = right.resize(left.size)
    left_metrics = _image_visual_metrics(left)
    right_metrics = _image_visual_metrics(right)
    luma_gain, luma_gain_diff = _luminance_gain_oracle(left, right)
    rgb_gain, rgb_gain_diff = _rgb_gain_oracle(left, right)
    left_edge = _edge_image(left)
    right_edge = _edge_image(right)
    edge_abs_diff = _mean_abs_grayscale_diff(left_edge, right_edge)
    residual_class = _residual_class(
        mean_abs_rgb=_mean_abs_rgb(left, right),
        left_metrics=left_metrics,
        right_metrics=right_metrics,
        edge_abs_diff=edge_abs_diff,
        rgb_gain_diff=rgb_gain_diff,
    )
    return {
        "schema": "robot_camera_render_residual_diagnostics_v1",
        "left_metrics": left_metrics,
        "right_metrics": right_metrics,
        "luminance_gain_oracle": {
            "gain": round(luma_gain, 6),
            "mean_abs_rgb_after_gain": round(luma_gain_diff, 4),
            "interpretation": (
                "Per-view oracle only; this is diagnostic evidence, not a runtime "
                "color-calibration contract."
            ),
        },
        "rgb_gain_oracle": {
            "gain": [round(value, 6) for value in rgb_gain],
            "mean_abs_rgb_after_gain": round(rgb_gain_diff, 4),
            "interpretation": (
                "Per-view RGB oracle only; use it to classify residuals, not as "
                "backend output post-processing."
            ),
        },
        "edge_abs_diff": round(edge_abs_diff, 4),
        "residual_class": residual_class,
        "recommended_next_action": _residual_next_action(residual_class),
    }


def _image_visual_metrics(image: Image.Image) -> dict[str, float]:
    rgb = image.convert("RGB")
    pixels = list(rgb.getdata())
    if not pixels:
        return {
            "mean_luminance": 0.0,
            "overexposed_fraction": 0.0,
            "underexposed_fraction": 0.0,
            "edge_mean": 0.0,
        }
    luminance = [_luminance(pixel) for pixel in pixels]
    edge = _edge_image(rgb)
    return {
        "mean_luminance": round(sum(luminance) / len(luminance), 4),
        "overexposed_fraction": round(
            sum(1 for value in luminance if value >= 245.0) / len(luminance),
            6,
        ),
        "underexposed_fraction": round(
            sum(1 for value in luminance if value <= 10.0) / len(luminance),
            6,
        ),
        "edge_mean": round(float(ImageStat.Stat(edge).mean[0]), 4),
    }


def _edge_image(image: Image.Image) -> Image.Image:
    edge = image.convert("L").filter(ImageFilter.FIND_EDGES)
    width, height = edge.size
    if width > 2 and height > 2:
        return edge.crop((1, 1, width - 1, height - 1))
    return edge


def _luminance(pixel: tuple[int, int, int]) -> float:
    return float(pixel[0]) * 0.2126 + float(pixel[1]) * 0.7152 + float(pixel[2]) * 0.0722


def _luminance_gain_oracle(left: Image.Image, right: Image.Image) -> tuple[float, float]:
    left_pixels = list(left.convert("RGB").getdata())
    right_pixels = list(right.convert("RGB").getdata())
    numerator = 0.0
    denominator = 0.0
    for left_pixel, right_pixel in zip(left_pixels, right_pixels, strict=True):
        left_luma = _luminance(left_pixel)
        right_luma = _luminance(right_pixel)
        numerator += left_luma * right_luma
        denominator += right_luma * right_luma
    gain = numerator / denominator if denominator > 0.0 else 1.0
    return gain, _mean_abs_rgb_after_gain(left_pixels, right_pixels, (gain, gain, gain))


def _rgb_gain_oracle(
    left: Image.Image, right: Image.Image
) -> tuple[tuple[float, float, float], float]:
    left_pixels = list(left.convert("RGB").getdata())
    right_pixels = list(right.convert("RGB").getdata())
    gains = []
    for channel in range(3):
        numerator = 0.0
        denominator = 0.0
        for left_pixel, right_pixel in zip(left_pixels, right_pixels, strict=True):
            numerator += float(left_pixel[channel]) * float(right_pixel[channel])
            denominator += float(right_pixel[channel]) * float(right_pixel[channel])
        gains.append(numerator / denominator if denominator > 0.0 else 1.0)
    gain_tuple = (float(gains[0]), float(gains[1]), float(gains[2]))
    return gain_tuple, _mean_abs_rgb_after_gain(left_pixels, right_pixels, gain_tuple)


def _mean_abs_rgb_after_gain(
    left_pixels: list[tuple[int, int, int]],
    right_pixels: list[tuple[int, int, int]],
    gain: tuple[float, float, float],
) -> float:
    if not left_pixels:
        return 0.0
    total = 0.0
    for left_pixel, right_pixel in zip(left_pixels, right_pixels, strict=True):
        for channel in range(3):
            adjusted = max(0.0, min(255.0, float(right_pixel[channel]) * gain[channel]))
            total += abs(float(left_pixel[channel]) - adjusted)
    return total / (len(left_pixels) * 3.0)


def _mean_abs_rgb(left: Image.Image, right: Image.Image) -> float:
    diff = ImageChops.difference(left.convert("RGB"), right.convert("RGB"))
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / len(stat.mean))


def _mean_abs_grayscale_diff(left: Image.Image, right: Image.Image) -> float:
    if right.size != left.size:
        right = right.resize(left.size)
    stat = ImageStat.Stat(ImageChops.difference(left.convert("L"), right.convert("L")))
    return float(stat.mean[0])


def _residual_class(
    *,
    mean_abs_rgb: float,
    left_metrics: dict[str, float],
    right_metrics: dict[str, float],
    edge_abs_diff: float,
    rgb_gain_diff: float,
) -> str:
    if mean_abs_rgb <= 35.0:
        return "low_residual"
    left_edge = float(left_metrics.get("edge_mean") or 0.0)
    right_edge = float(right_metrics.get("edge_mean") or 0.0)
    if left_edge > 4.0 and right_edge < left_edge * 0.45:
        return "geometry_or_texture_edge_residual"
    if edge_abs_diff > 8.0:
        return "geometry_or_texture_edge_residual"
    if rgb_gain_diff <= mean_abs_rgb * 0.7:
        return "view_dependent_color_residual"
    if (
        abs(
            float(right_metrics.get("mean_luminance") or 0.0)
            - float(left_metrics.get("mean_luminance") or 0.0)
        )
        > 35.0
    ):
        return "luminance_residual"
    return "render_domain_residual"


def _residual_next_action(residual_class: str) -> str:
    if residual_class == "low_residual":
        return "Residual is low enough for this probe; inspect other views before changing code."
    if residual_class == "view_dependent_color_residual":
        return (
            "Per-view color gain helps, but a global post-process would overfit; inspect "
            "room/object lighting, material albedo, and tone response."
        )
    if residual_class == "geometry_or_texture_edge_residual":
        return (
            "Edge/detail residual is high; compare visible USD/MuJoCo geometry, material "
            "bindings, texture availability, and static robot/head articulation."
        )
    if residual_class == "luminance_residual":
        return "Try a renderer/light/color-profile calibration probe before changing camera pose."
    return "Inspect render-domain differences before changing camera geometry."


def _residual_triage(locations: list[dict[str, Any]]) -> dict[str, Any]:
    per_view: dict[str, dict[str, Any]] = {}
    for view_key in ROBOT_VIEW_KEYS:
        diffs = [
            _dict_path(item, ("image_diffs", view_key, "residual"))
            for item in locations
            if item.get("status") == "success"
        ]
        diffs = [item for item in diffs if item]
        classes = [str(item.get("residual_class") or "") for item in diffs]
        per_view[view_key] = {
            "view_count": len(diffs),
            "residual_classes": {name: classes.count(name) for name in sorted(set(classes))},
            "mean_abs_rgb_avg": _avg(
                _get_float(item, ("image_diffs", view_key, "mean_abs_rgb")) for item in locations
            ),
            "rgb_gain_oracle_mean_abs_rgb_avg": _avg(
                _get_float(item, ("rgb_gain_oracle", "mean_abs_rgb_after_gain")) for item in diffs
            ),
            "edge_abs_diff_avg": _avg(_get_float(item, ("edge_abs_diff",)) for item in diffs),
        }
    fpv = per_view.get("fpv") or {}
    fpv_classes = dict(fpv.get("residual_classes") or {})
    if fpv_classes.get("geometry_or_texture_edge_residual"):
        status = "render_domain_geometry_or_texture_residual"
        next_action = (
            "Camera pose/color are improved; next compare visible geometry/material/texture "
            "contracts and static head articulation for high-residual FPV views."
        )
    elif fpv_classes.get("view_dependent_color_residual"):
        status = "view_dependent_color_residual"
        next_action = (
            "A single global color profile is insufficient; inspect per-room lighting and "
            "material albedo before tuning camera geometry."
        )
    elif float(fpv.get("mean_abs_rgb_avg") or 0.0) <= 40.0:
        status = "fpv_residual_low"
        next_action = "FPV residual is low for this probe; broaden scene/seed coverage."
    else:
        status = "render_domain_residual_pending_triage"
        next_action = "Inspect high-residual views before changing camera pose."
    return {
        "schema": "robot_camera_render_residual_triage_v1",
        "status": status,
        "views": per_view,
        "recommended_next_action": next_action,
    }


def _dict_path(item: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    value: Any = item
    for key in path:
        if not isinstance(value, dict):
            return {}
        value = value.get(key)
    return value if isinstance(value, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def _float_or_none(value: Any) -> float | None:
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
    style = "\n".join(
        [
            "body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:24px;"
            "background:#f7f7f4;color:#202124}",
            "header,.location{max-width:1180px;margin:0 auto 18px;background:white;"
            "border:1px solid #d9d7ce;padding:16px}",
            "h1{margin:0 0 8px;font-size:24px}",
            "h2{font-size:18px;margin:0 0 10px}",
            "h2 span{font-weight:400;color:#5f6368}",
            ".pairs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}",
            ".pair{border-top:1px solid #ece8dd;padding-top:10px}",
            "figure{margin:0 0 8px}",
            "img{display:block;width:100%;height:auto;border:1px solid #ddd;background:#111}",
            "figcaption,p{font-size:13px;color:#5f6368;margin:6px 0}",
            "pre{font-size:12px;background:#f4f1e8;padding:10px;overflow:auto}",
            ".bad{color:#9b1c1c}",
            "@media(max-width:800px){.pairs{grid-template-columns:1fr}}",
        ]
    )
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
            residual = diff.get("residual") if isinstance(diff.get("residual"), dict) else {}
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
                + ", residual "
                + html.escape(str(residual.get("residual_class") or ""))
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
            + "</pre><pre>"
            + html.escape(
                json.dumps(
                    item.get("camera_contract_diagnostics", {}),
                    indent=2,
                    sort_keys=True,
                )
            )
            + "</pre><pre>"
            + html.escape(
                json.dumps(
                    item.get("render_contract_diagnostics", {}),
                    indent=2,
                    sort_keys=True,
                )
            )
            + "</pre><div class='pairs'>"
            + "".join(pairs)
            + "</div></section>"
        )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>RBY1M Robot Camera Apple2Apple</title>"
        "<style>" + style + "</style></head><body><header><h1>RBY1M Robot Camera Apple2Apple</h1>"
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
