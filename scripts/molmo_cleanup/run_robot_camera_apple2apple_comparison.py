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

from PIL import Image, ImageChops, ImageFilter, ImageStat

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
    parser.add_argument(
        "--output-dir", type=Path, default=Path("output/molmo/robot-camera-apple2apple")
    )
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
    manifest["status"] = (
        "success"
        if locations and all(item["status"] == "success" for item in locations)
        else "blocked"
    )
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
        "camera_contract_diagnostics": _location_camera_contract_diagnostics(
            {
                "robot_pose": robot_pose,
                "contracts": {
                    "mujoco": mujoco_views.get("camera_control_contract", {}),
                    "isaac": isaac_views.get("camera_control_contract", {}),
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
        "chase_same_camera_contract_count": chase_same_camera_count,
        "chase_note": chase_note,
        "recommended_next_action": next_action,
    }


def _location_camera_contract_diagnostics(item: dict[str, Any]) -> dict[str, Any]:
    contracts = _dict(item.get("contracts"))
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
    )
    return {
        "schema": "robot_camera_location_contract_diagnostics_v1",
        "fpv_head_camera_contract": fpv_head_camera_contract,
        "robot_pose_match": robot_pose_match,
        "mujoco_pose_delta": mujoco_pose_delta,
        "isaac_pose_delta": isaac_pose_delta,
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
        "head_articulation": head_articulation,
        "chase_contract": _chase_contract_diagnostics(mujoco_contract, isaac_contract),
    }


def _is_head_camera_fpv(fpv: dict[str, Any]) -> bool:
    source = str(fpv.get("source") or "")
    prim_path = str(fpv.get("camera_prim_path") or "")
    return bool(fpv.get("robot_mounted")) and (
        "head_camera" in source or "head_camera" in prim_path
    )


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
) -> dict[str, Any]:
    requested_head_pitch = _float_or_none(requested_pose.get("head_pitch"))
    mujoco_head_pitch = _float_or_none(_dict(mujoco_contract.get("robot_pose")).get("head_pitch"))
    isaac_head_pitch = _float_or_none(_dict(isaac_contract.get("robot_pose")).get("head_pitch"))
    if requested_head_pitch is None:
        status = "head_pitch_not_requested"
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
        "evidence_note": (
            "MuJoCo robot views use qpos-backed robot joints. The current Isaac comparison "
            "contract records the same requested head pitch, but static-only USD import does "
            "not prove that the head joint is articulated during FPV capture."
        ),
    }


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
