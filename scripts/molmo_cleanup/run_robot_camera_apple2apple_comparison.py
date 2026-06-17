#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.artifact_paths import output_relpath
from roboclaws.household.generated_mess import (
    build_generated_mess_manifest,
    generated_mess_manifest_object_ids,
)
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
from scripts.molmo_cleanup import robot_camera_apple2apple_camera_contract as camera_contract
from scripts.molmo_cleanup import robot_camera_apple2apple_capture_quality as capture_quality
from scripts.molmo_cleanup import robot_camera_apple2apple_image_metrics as image_metrics
from scripts.molmo_cleanup import robot_camera_apple2apple_materials as material_checks
from scripts.molmo_cleanup import robot_camera_apple2apple_native_render as native_render
from scripts.molmo_cleanup import robot_camera_apple2apple_object_gate as object_gate
from scripts.molmo_cleanup import robot_camera_apple2apple_object_parity as object_parity
from scripts.molmo_cleanup import robot_camera_apple2apple_report as report_renderer
from scripts.molmo_cleanup import robot_camera_apple2apple_visual_state as visual_state

SCHEMA = "roboclaws_robot_camera_apple2apple_comparison_v1"
MUJOCO_LANE_ID = "molmospaces-mujoco-rby1m"
ISAAC_LANE_ID = "isaaclab-rby1m-usd"
ROBOT_VIEW_KEYS = ("fpv", "chase")


class _ComparisonRunPaths(NamedTuple):
    output_dir: Path
    canonical_scene_state: Path
    generated_mess_manifest: Path
    mujoco_state: Path
    isaac_state: Path
    mujoco_run_dir: Path
    isaac_run_dir: Path


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
    parser.add_argument("--render-width", type=_positive_int_arg, default=540)
    parser.add_argument("--render-height", type=_positive_int_arg, default=360)
    parser.add_argument(
        "--saved-report-width",
        type=int,
        help=(
            "Optional saved report-image width. Use with --saved-report-height to downsample "
            "high-resolution renders for the report without changing renderer defaults."
        ),
    )
    parser.add_argument(
        "--saved-report-height",
        type=int,
        help="Optional saved report-image height. Requires --saved-report-width.",
    )
    parser.add_argument(
        "--metric-width",
        type=int,
        help=(
            "Optional metric-comparison width. Use with --metric-height to compute "
            "same-size downsampled metrics from high-resolution captures."
        ),
    )
    parser.add_argument(
        "--metric-height",
        type=int,
        help="Optional metric-comparison height. Requires --metric-width.",
    )
    parser.add_argument(
        "--downsample-filter",
        choices=("nearest", "bilinear", "bicubic", "lanczos"),
        default="lanczos",
        help="PIL filter used for explicit saved-image or metric downsampling.",
    )
    parser.add_argument(
        "--render-settle-frames",
        type=int,
        default=0,
        help=(
            "Extra Isaac render frames to advance after first nonblank RGB before saving. "
            "This is an opt-in capture-quality probe control."
        ),
    )
    parser.add_argument(
        "--isaac-aa-op",
        type=int,
        help=(
            "Optional Isaac /rtx/post/aa/op value for an opt-in capture-quality probe. "
            "The worker records the previous value and restores it after capture."
        ),
    )
    parser.add_argument(
        "--isaac-tonemap-op",
        type=int,
        help=(
            "Optional Isaac /rtx/post/tonemap/op value for an opt-in native tone probe. "
            "The worker records the previous value and restores it after capture."
        ),
    )
    parser.add_argument(
        "--isaac-exposure-bias",
        type=float,
        help=(
            "Optional Isaac /rtx/post/tonemap/exposureBias value for an opt-in native "
            "exposure probe. The worker records the previous value and restores it after "
            "capture."
        ),
    )
    parser.add_argument(
        "--isaac-colorcorr-gain",
        type=capture_quality.parse_rgb_gain,
        help=(
            "Optional Isaac /rtx/post/colorcorr gain as R,G,B for an opt-in native color "
            "correction probe. The worker enables color correction, records previous values, "
            "and restores them after capture."
        ),
    )
    parser.add_argument("--location-count", type=_positive_int_arg, default=4)
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
        "--material-response-probe-manifest",
        type=Path,
        action="append",
        default=[],
        help=(
            "Optional prior comparison manifest for a material-response probe. Repeat to "
            "attach texture colorspace, roughness, or PreviewSurface probe history to this "
            "report without changing default rendering."
        ),
    )
    parser.add_argument(
        "--tone-color-probe-manifest",
        type=Path,
        action="append",
        default=[],
        help=(
            "Optional prior comparison manifest for a tone/color probe. Repeat to attach "
            "RGB gain or tone calibration probe history to this report without changing "
            "default rendering."
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
    parser.add_argument(
        "--skip-object-parity-audit",
        action="store_true",
        help=(
            "Skip the full-scene object parity audit and Object/Render Gate. This is "
            "only for bounded capture-quality probes where image diffs and native render "
            "metadata are the decision evidence."
        ),
    )
    args = parser.parse_args(argv)

    if args.refresh_report_only:
        manifest = refresh_report_only(
            args.output_dir,
            light_shadow_probe_manifest_paths=args.light_shadow_probe_manifest,
            material_response_probe_manifest_paths=args.material_response_probe_manifest,
            tone_color_probe_manifest_paths=args.tone_color_probe_manifest,
            skip_object_parity_audit=bool(args.skip_object_parity_audit),
        )
    else:
        if args.scene_usd_path is None:
            parser.error("--scene-usd-path is required unless --refresh-report-only is set")
        manifest = run_comparison(args)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"robot camera apple2apple manifest: {args.output_dir / 'comparison_manifest.json'}")
    print(f"robot camera apple2apple report: {args.output_dir / 'report.html'}")
    return 0 if manifest["status"] == "success" else 2


def run_comparison(args: argparse.Namespace) -> dict[str, Any]:
    paths = _comparison_run_paths(args.output_dir)
    output_dir = paths.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    isaac_robot_view_color_profile = _load_optional_json(args.isaac_robot_view_color_profile_path)
    capture_quality_probe = capture_quality.capture_quality_probe_config(args)
    manifest = _initial_comparison_manifest(args, capture_quality=capture_quality_probe)

    lane_states = _initialize_comparison_lanes(args, paths, manifest)
    if lane_states is None:
        return manifest
    mujoco_state, isaac_state = lane_states
    _attach_state_artifact_summaries(
        manifest,
        output_dir=output_dir,
        mujoco_state=mujoco_state,
        isaac_state=isaac_state,
    )
    target_selection = _select_comparison_targets(
        mujoco_state,
        limit=int(args.location_count),
        scene_binding_diagnostics=_dict(isaac_state.get("scene_binding_diagnostics")),
        isaac_state=isaac_state,
    )
    manifest["target_selection"] = target_selection
    candidates = [_dict(item) for item in target_selection.get("selected_targets") or []]
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
                        str(paths.mujoco_state),
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
                        str(paths.mujoco_state),
                        "frame_comparison_object",
                        "--object-id",
                        target["target_id"],
                    ],
                    cwd=Path.cwd(),
                )
            mujoco_state = _read_json(paths.mujoco_state)
            robot_pose = dict(mujoco_state.get("robot_pose") or nav.get("robot_pose") or {})
            _patch_isaac_robot_pose(
                paths.isaac_state,
                robot_pose,
                target=target,
                color_profile=isaac_robot_view_color_profile,
            )
            mujoco_views = _run_json(
                [
                    str(args.mujoco_python),
                    "scripts/molmo_cleanup/molmospaces_subprocess_worker.py",
                    "--state-path",
                    str(paths.mujoco_state),
                    "robot_views",
                    "--output-dir",
                    str(paths.mujoco_run_dir / "robot_views"),
                    "--label",
                    label,
                    "--render-width",
                    str(args.render_width),
                    "--render-height",
                    str(args.render_height),
                    *_focus_args(target),
                ],
                cwd=Path.cwd(),
            )
            isaac_views = _run_json(
                [
                    str(args.isaac_python),
                    "scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py",
                    "--state-path",
                    str(paths.isaac_state),
                    "robot_views",
                    "--output-dir",
                    str(paths.isaac_run_dir / "robot_views"),
                    "--label",
                    label,
                    "--render-width",
                    str(args.render_width),
                    "--render-height",
                    str(args.render_height),
                    *capture_quality.render_settle_args(capture_quality_probe),
                    *_focus_args(target),
                ],
                cwd=Path.cwd(),
            )
            image_metrics.prepare_saved_report_images(
                mujoco_views,
                isaac_views,
                capture_quality=capture_quality_probe,
            )
            locations.append(
                _location_result(
                    label=label,
                    target=target,
                    robot_pose=robot_pose,
                    mujoco_views=mujoco_views,
                    isaac_views=isaac_views,
                    output_dir=output_dir,
                    capture_quality=capture_quality_probe,
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
    camera_contract.refresh_location_camera_contract_diagnostics(locations)
    manifest["summary"] = _summary(locations)
    manifest["summary"]["capture_quality_probe"] = capture_quality_probe
    manifest["summary"]["target_selection"] = target_selection
    _attach_render_contract_diagnostics(
        manifest,
        output_dir=output_dir,
        light_shadow_probe_manifest_paths=args.light_shadow_probe_manifest,
        material_response_probe_manifest_paths=args.material_response_probe_manifest,
        tone_color_probe_manifest_paths=args.tone_color_probe_manifest,
        skip_object_parity_audit=bool(args.skip_object_parity_audit),
    )
    _write_outputs(manifest, output_dir)
    return manifest


def _comparison_run_paths(output_dir: Path) -> _ComparisonRunPaths:
    return _ComparisonRunPaths(
        output_dir=output_dir,
        canonical_scene_state=output_dir / "canonical_scene_state.json",
        generated_mess_manifest=output_dir / "generated_mess_manifest.json",
        mujoco_state=output_dir / "mujoco_state.json",
        isaac_state=output_dir / "isaac_state.json",
        mujoco_run_dir=output_dir / "mujoco",
        isaac_run_dir=output_dir / "isaac",
    )


def _initial_comparison_manifest(
    args: argparse.Namespace,
    *,
    capture_quality: dict[str, Any],
) -> dict[str, Any]:
    return {
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
            "saved_report_width": capture_quality["render_resolution_saved"]["width"],
            "saved_report_height": capture_quality["render_resolution_saved"]["height"],
            "metric_width": capture_quality["metric_resolution"]["width"],
            "metric_height": capture_quality["metric_resolution"]["height"],
        },
        "capture_quality_probe": capture_quality,
        "camera_contract": camera_contract.robot_camera_contract(
            mujoco_lane_id=MUJOCO_LANE_ID,
            isaac_lane_id=ISAAC_LANE_ID,
        ),
        "lanes": {},
        "locations": [],
        "artifacts": {
            "manifest": "comparison_manifest.json",
            "report": "report.html",
            "generated_mess_manifest": "generated_mess_manifest.json",
        },
    }


def _initialize_comparison_lanes(
    args: argparse.Namespace,
    paths: _ComparisonRunPaths,
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    canonical_mess_manifest: dict[str, Any] = {}
    try:
        mujoco_init, isaac_init, canonical_mess_manifest = _run_lane_initializers(
            args,
            paths,
        )
        manifest["mess_generation"] = _mess_generation_summary(
            canonical_mess_manifest,
            output_dir=paths.output_dir,
            manifest_path=paths.generated_mess_manifest,
        )
        _validate_generated_mess_init(
            lane_id=MUJOCO_LANE_ID,
            init_result=mujoco_init,
            canonical_manifest=canonical_mess_manifest,
        )
        _validate_generated_mess_init(
            lane_id=ISAAC_LANE_ID,
            init_result=isaac_init,
            canonical_manifest=canonical_mess_manifest,
        )
    except Exception as exc:
        if canonical_mess_manifest and "mess_generation" not in manifest:
            manifest["mess_generation"] = _mess_generation_summary(
                canonical_mess_manifest,
                output_dir=paths.output_dir,
                manifest_path=paths.generated_mess_manifest,
            )
        _block_comparison_manifest(manifest, paths.output_dir, exc)
        return None

    manifest["lanes"][MUJOCO_LANE_ID] = _lane_init_summary(mujoco_init)
    manifest["lanes"][ISAAC_LANE_ID] = _lane_init_summary(isaac_init)
    manifest["lanes"][ISAAC_LANE_ID]["robot_import"] = isaac_init.get("robot_import", {})
    mujoco_state = _read_json(paths.mujoco_state)
    isaac_state = _read_json(paths.isaac_state)
    try:
        _validate_generated_mess_state_locations(
            lane_id=MUJOCO_LANE_ID,
            state=mujoco_state,
            canonical_manifest=canonical_mess_manifest,
        )
        _validate_generated_mess_state_locations(
            lane_id=ISAAC_LANE_ID,
            state=isaac_state,
            canonical_manifest=canonical_mess_manifest,
        )
        _validate_generated_mess_placement_diagnostics(
            lane_id=MUJOCO_LANE_ID,
            state=mujoco_state,
            canonical_manifest=canonical_mess_manifest,
        )
        _validate_generated_mess_placement_diagnostics(
            lane_id=ISAAC_LANE_ID,
            state=isaac_state,
            canonical_manifest=canonical_mess_manifest,
        )
    except Exception as exc:
        _block_comparison_manifest(manifest, paths.output_dir, exc)
        return None
    return mujoco_state, isaac_state


def _run_lane_initializers(
    args: argparse.Namespace,
    paths: _ComparisonRunPaths,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _run_json(
        [
            str(args.mujoco_python),
            "scripts/molmo_cleanup/molmospaces_subprocess_worker.py",
            "--state-path",
            str(paths.canonical_scene_state),
            "init",
            "--seed",
            str(args.seed),
            "--scene-source",
            args.scene_source,
            "--scene-index",
            str(args.scene_index),
            "--generated-mess-count",
            str(args.generated_mess_count),
        ],
        cwd=Path.cwd(),
    )
    canonical_mess_manifest = _canonical_generated_mess_manifest_from_state(
        _read_json(paths.canonical_scene_state),
        args=args,
    )
    if int(canonical_mess_manifest.get("generated_mess_count") or 0) < int(
        args.generated_mess_count
    ):
        raise RuntimeError(
            "canonical generated mess manifest did not contain enough targets "
            f"({canonical_mess_manifest.get('generated_mess_count')} < "
            f"{args.generated_mess_count})"
        )
    _write_json(paths.generated_mess_manifest, canonical_mess_manifest)
    mujoco_init = _run_json(_mujoco_init_command(args, paths), cwd=Path.cwd())
    isaac_init = _run_json(_isaac_init_command(args, paths), cwd=Path.cwd())
    return mujoco_init, isaac_init, canonical_mess_manifest


def _mujoco_init_command(args: argparse.Namespace, paths: _ComparisonRunPaths) -> list[str]:
    return [
        str(args.mujoco_python),
        "scripts/molmo_cleanup/molmospaces_subprocess_worker.py",
        "--state-path",
        str(paths.mujoco_state),
        "init",
        "--seed",
        str(args.seed),
        "--scene-source",
        args.scene_source,
        "--scene-index",
        str(args.scene_index),
        "--generated-mess-count",
        str(args.generated_mess_count),
        "--generated-mess-manifest-path",
        str(paths.generated_mess_manifest),
        "--include-robot",
        "--robot-name",
        "rby1m",
    ]


def _isaac_init_command(args: argparse.Namespace, paths: _ComparisonRunPaths) -> list[str]:
    return [
        str(args.isaac_python),
        "scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py",
        "--state-path",
        str(paths.isaac_state),
        "init",
        "--run-dir",
        str(paths.isaac_run_dir),
        "--seed",
        str(args.seed),
        "--scene-source",
        args.scene_source,
        "--scene-index",
        str(args.scene_index),
        "--generated-mess-count",
        str(args.generated_mess_count),
        "--generated-mess-manifest-path",
        str(paths.generated_mess_manifest),
        "--runtime-mode",
        "real",
        "--include-robot",
        "--robot-name",
        "rby1m",
        "--scene-usd-path",
        str(args.scene_usd_path),
    ]


def _block_comparison_manifest(
    manifest: dict[str, Any],
    output_dir: Path,
    exc: Exception,
) -> None:
    manifest["status"] = "blocked"
    manifest["blocker"] = str(exc)
    _write_outputs(manifest, output_dir)


def refresh_report_only(
    output_dir: Path,
    light_shadow_probe_manifest_paths: list[Path] | None = None,
    material_response_probe_manifest_paths: list[Path] | None = None,
    tone_color_probe_manifest_paths: list[Path] | None = None,
    skip_object_parity_audit: bool = False,
) -> dict[str, Any]:
    manifest_path = output_dir / "comparison_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = _read_json(manifest_path)
    manifest["camera_contract"] = camera_contract.robot_camera_contract(
        mujoco_lane_id=MUJOCO_LANE_ID,
        isaac_lane_id=ISAAC_LANE_ID,
    )
    mujoco_state = _read_json(output_dir / "mujoco_state.json")
    isaac_state = _read_json(output_dir / "isaac_state.json")
    existing_selection = _dict(manifest.get("target_selection"))
    requested_limit = int(
        existing_selection.get("requested_limit") or len(manifest.get("locations") or []) or 4
    )
    target_selection = _select_comparison_targets(
        mujoco_state,
        limit=max(1, requested_limit),
        scene_binding_diagnostics=_dict(isaac_state.get("scene_binding_diagnostics")),
        isaac_state=isaac_state,
    )
    manifest["target_selection"] = target_selection
    locations = list(manifest.get("locations") or [])
    camera_contract.refresh_location_camera_contract_diagnostics(locations)
    capture_quality_probe = capture_quality.ensure_capture_quality_probe_manifest(manifest)
    manifest["summary"] = _summary(locations)
    manifest["summary"]["capture_quality_probe"] = capture_quality_probe
    manifest["summary"]["target_selection"] = target_selection
    _attach_render_contract_diagnostics(
        manifest,
        output_dir=output_dir,
        light_shadow_probe_manifest_paths=light_shadow_probe_manifest_paths,
        material_response_probe_manifest_paths=material_response_probe_manifest_paths,
        tone_color_probe_manifest_paths=tone_color_probe_manifest_paths,
        skip_object_parity_audit=skip_object_parity_audit,
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


def _canonical_generated_mess_manifest_from_state(
    state: dict[str, Any],
    *,
    args: argparse.Namespace,
) -> dict[str, Any]:
    objects = [_dict(item) for item in _dict(state.get("objects")).values()]
    receptacles = [_dict(item) for item in _dict(state.get("receptacles")).values()]
    if not objects:
        raise RuntimeError("canonical scene state did not expose any generated-mess objects")
    if not receptacles:
        raise RuntimeError("canonical scene state did not expose any generated-mess receptacles")
    return build_generated_mess_manifest(
        objects,
        receptacles,
        target_count=int(args.generated_mess_count),
        seed=int(args.seed),
        scene_source=str(args.scene_source),
        scene_index=int(args.scene_index),
        scene_metadata_source="molmospaces_scene_metadata",
    )


def _mess_generation_summary(
    canonical_manifest: dict[str, Any],
    *,
    output_dir: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    target_summaries = []
    for target in canonical_manifest.get("targets", []):
        item = _dict(target)
        target_summaries.append(
            {
                "object_id": item.get("object_id"),
                "target_receptacle_id": item.get("target_receptacle_id"),
                "valid_receptacle_ids": item.get("valid_receptacle_ids") or [],
                "start_receptacle_id": item.get("start_receptacle_id"),
                "relation": item.get("relation"),
                "placement_index": item.get("placement_index"),
            }
        )
    return {
        "schema": "robot_camera_apple2apple_mess_generation_v1",
        "status": "canonical_generated_mess_manifest",
        "manifest_schema": canonical_manifest.get("schema"),
        "provenance": canonical_manifest.get("provenance"),
        "object_id_source": "backend_neutral_generated_mess_manifest",
        "artifact": output_relpath(manifest_path, output_dir),
        "seed": _dict(canonical_manifest.get("selection")).get("seed"),
        "requested_generated_mess_count": canonical_manifest.get("requested_generated_mess_count"),
        "generated_mess_count": canonical_manifest.get("generated_mess_count"),
        "canonical_generated_mess_object_ids": generated_mess_manifest_object_ids(
            canonical_manifest
        ),
        "targets": target_summaries,
    }


def _validate_generated_mess_init(
    *,
    lane_id: str,
    init_result: dict[str, Any],
    canonical_manifest: dict[str, Any],
) -> None:
    expected = _private_manifest_target_pairs(canonical_manifest)
    actual = _private_manifest_target_pairs(_dict(init_result.get("private_manifest")))
    if actual != expected:
        raise RuntimeError(
            f"{lane_id} generated mess targets did not match canonical manifest: "
            f"{actual} != {expected}"
        )


def _validate_generated_mess_state_locations(
    *,
    lane_id: str,
    state: dict[str, Any],
    canonical_manifest: dict[str, Any],
) -> None:
    locations = _state_location_map(state)
    expected = {
        str(_dict(target).get("object_id") or ""): str(
            _dict(target).get("start_receptacle_id") or ""
        )
        for target in canonical_manifest.get("targets", [])
        if str(_dict(target).get("object_id") or "")
    }
    actual = {object_id: locations.get(object_id, "") for object_id in expected}
    if actual != expected:
        raise RuntimeError(
            f"{lane_id} generated mess start locations did not match canonical manifest: "
            f"{actual} != {expected}"
        )


def _validate_generated_mess_placement_diagnostics(
    *,
    lane_id: str,
    state: dict[str, Any],
    canonical_manifest: dict[str, Any],
) -> None:
    expected = _placement_contract_by_object(canonical_manifest.get("targets", []))
    actual = _placement_contract_by_object(
        item
        for item in state.get("mess_placement_diagnostics", [])
        if _dict(item).get("diagnostic_source") == "canonical_mess_manifest"
    )
    missing = sorted(set(expected) - set(actual))
    if missing:
        raise RuntimeError(
            f"{lane_id} generated mess placement diagnostics missing canonical targets: {missing}"
        )
    mismatches = {
        object_id: {"actual": actual[object_id], "expected": expected[object_id]}
        for object_id in sorted(expected)
        if actual.get(object_id) != expected[object_id]
    }
    if mismatches:
        raise RuntimeError(
            f"{lane_id} generated mess placement diagnostics did not match canonical "
            f"manifest: {mismatches}"
        )


def _placement_contract_by_object(items: Any) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for raw_item in items:
        item = _dict(raw_item)
        object_id = str(item.get("object_id") or "")
        if not object_id:
            continue
        contracts[object_id] = {
            "receptacle_id": str(
                item.get("start_receptacle_id") or item.get("receptacle_id") or ""
            ),
            "relation": str(item.get("relation") or ""),
            "placement_index": item.get("placement_index"),
        }
    return contracts


def _private_manifest_target_pairs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "object_id": str(_dict(target).get("object_id") or ""),
            "valid_receptacle_ids": [
                str(item) for item in _dict(target).get("valid_receptacle_ids", []) if str(item)
            ],
        }
        for target in manifest.get("targets", [])
        if str(_dict(target).get("object_id") or "")
    ]


def _state_location_map(state: dict[str, Any]) -> dict[str, str]:
    if isinstance(state.get("locations"), dict):
        return {str(key): str(value) for key, value in _dict(state.get("locations")).items()}
    locations: dict[str, str] = {}
    for object_id, raw_obj in _dict(state.get("objects")).items():
        obj = _dict(raw_obj)
        locations[str(object_id)] = str(
            obj.get("contained_in") or obj.get("seeded_start_receptacle_id") or ""
        )
    return locations


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


def _select_comparison_targets(
    state: dict[str, Any],
    *,
    limit: int,
    scene_binding_diagnostics: dict[str, Any] | None,
    isaac_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = _comparison_targets(state, limit=max(1, limit * 4))
    priority_targets = visual_state.visual_physics_sensitive_target_ids(state)
    binding_ids = _bound_comparison_target_ids(
        scene_binding_diagnostics or {},
        isaac_state=isaac_state or {},
    )
    if any(binding_ids.values()):
        bound_candidates = [
            item
            for item in candidates
            if str(item.get("target_id") or "")
            in binding_ids.get(str(item.get("kind") or ""), set())
        ]
        ordered_candidates = _prioritize_comparison_targets(bound_candidates, priority_targets)
        selected = ordered_candidates[:limit]
        dropped = [
            item
            for item in candidates
            if str(item.get("target_id") or "")
            not in binding_ids.get(str(item.get("kind") or ""), set())
        ]
        status = "isaac_bound_targets_selected"
    else:
        ordered_candidates = _prioritize_comparison_targets(candidates, priority_targets)
        selected = ordered_candidates[:limit]
        dropped = []
        status = "unfiltered_no_isaac_binding_diagnostics"
    selected_ids = {str(item.get("target_id") or "") for item in selected}
    priority_selected = [
        item for item in selected if str(item.get("target_id") or "") in priority_targets
    ]
    return {
        "schema": "robot_camera_comparison_target_selection_v1",
        "status": status,
        "requested_limit": limit,
        "candidate_count": len(candidates),
        "isaac_bound_candidate_count": len(bound_candidates) if any(binding_ids.values()) else 0,
        "selected_count": len(selected),
        "selected_targets": selected,
        "visual_physics_sensitive_target_count": len(priority_targets),
        "visual_physics_sensitive_selected_count": len(priority_selected),
        "visual_physics_sensitive_selected_targets": priority_selected,
        "visual_physics_sensitive_not_selected_targets": [
            item
            for item in ordered_candidates
            if str(item.get("target_id") or "") in priority_targets
            and str(item.get("target_id") or "") not in selected_ids
        ][:10],
        "dropped_unbound_target_count": len(dropped),
        "dropped_unbound_targets": dropped[:10],
        "not_selected_bound_target_count": max(
            0,
            len(ordered_candidates) - len(selected),
        ),
        "not_selected_bound_targets": (ordered_candidates[len(selected) : len(selected) + 10]),
        "interpretation": (
            "Robot-camera apple-to-apple image parity renders a bounded subset of targets "
            "that both backends can bind to USD/MJCF render contracts. Objects outside "
            "this selected image subset are still covered by object_parity_audit when "
            "state/index evidence is available, but visual-physics-sensitive objects are "
            "prioritized because physics-freeze metadata alone does not prove the frozen "
            "visual pose matches MuJoCo."
        ),
    }


def _prioritize_comparison_targets(
    candidates: list[dict[str, Any]],
    priority_target_ids: set[str],
) -> list[dict[str, Any]]:
    if not priority_target_ids:
        return list(candidates)
    return sorted(
        candidates,
        key=lambda item: (
            0 if str(item.get("target_id") or "") in priority_target_ids else 1,
            0 if str(item.get("kind") or "") == "object" else 1,
        ),
    )


def _bound_comparison_target_ids(
    scene_binding_diagnostics: dict[str, Any],
    *,
    isaac_state: dict[str, Any] | None = None,
) -> dict[str, set[str]]:
    return {
        "receptacle": set(
            _bound_ids_from_index(_dict((isaac_state or {}).get("receptacle_index")))
            | _bound_ids_from_groups(
                scene_binding_diagnostics,
                ("receptacle_bindings", "selected_target_receptacle_bindings"),
            )
        ),
        "object": set(
            _bound_ids_from_index(_dict((isaac_state or {}).get("object_index")))
            | _bound_ids_from_groups(
                scene_binding_diagnostics,
                ("object_bindings", "selected_object_bindings"),
            )
        ),
    }


def _bound_ids_from_index(index: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for target_id, raw_entry in index.items():
        entry = _dict(raw_entry)
        if entry.get("valid_stage_prim") is False:
            continue
        if entry.get("geometry_status") == "missing":
            continue
        if entry.get("usd_prim_path"):
            ids.add(str(target_id))
    return ids


def _bound_ids_from_groups(
    scene_binding_diagnostics: dict[str, Any],
    groups: tuple[str, ...],
) -> set[str]:
    ids: set[str] = set()
    for group in groups:
        bindings = _dict(scene_binding_diagnostics.get(group))
        for target_id, raw_binding in bindings.items():
            binding = _dict(raw_binding)
            if binding.get("status") == "bound" and binding.get("usd_prim_path"):
                ids.add(str(target_id))
    return ids


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


def _focus_args(target: dict[str, Any]) -> list[str]:
    target_id = str(target.get("target_id") or "")
    if not target_id:
        return []
    if str(target.get("kind") or "") == "object":
        return ["--focus-object-id", target_id]
    if str(target.get("kind") or "") == "receptacle":
        return ["--focus-receptacle-id", target_id]
    return []


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
    capture_quality: dict[str, Any],
) -> dict[str, Any]:
    image_artifacts = image_metrics.location_image_artifacts(
        mujoco_views=mujoco_views,
        isaac_views=isaac_views,
        output_dir=output_dir,
        capture_quality=capture_quality,
    )
    return {
        "label": label,
        "status": "success",
        "target": target,
        "robot_pose": robot_pose,
        "capture_quality_probe": capture_quality,
        "views": image_artifacts["views"],
        "raw_render_views": image_artifacts["raw_render_views"],
        "metric_views": image_artifacts["metric_views"],
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
        "camera_contract_diagnostics": camera_contract.location_camera_contract_diagnostics(
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
        "image_diffs": image_artifacts["image_diffs"],
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
        "camera_contract_diagnostics": camera_contract.camera_contract_diagnostics(successful),
        "residual_triage": image_metrics.residual_triage(successful),
    }


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
        native_render_diagnostics = native_render.native_isaac_render_diagnostics_from_state(
            isaac_state
        )
        if native_render_diagnostics:
            isaac_lane["native_render_diagnostics"] = (
                object_gate.compact_native_isaac_render_diagnostics(native_render_diagnostics)
            )
    artifacts = manifest.setdefault("artifacts", {})
    if isinstance(artifacts, dict):
        artifacts["mujoco_state"] = output_relpath(output_dir / "mujoco_state.json", output_dir)
        artifacts["isaac_state"] = output_relpath(output_dir / "isaac_state.json", output_dir)


def _attach_render_contract_diagnostics(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    light_shadow_probe_manifest_paths: list[Path] | None = None,
    material_response_probe_manifest_paths: list[Path] | None = None,
    tone_color_probe_manifest_paths: list[Path] | None = None,
    skip_object_parity_audit: bool = False,
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
            isaac_state=isaac_state,
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
        material_response_probe_manifest_paths=material_response_probe_manifest_paths,
        tone_color_probe_manifest_paths=tone_color_probe_manifest_paths,
    )
    manifest["render_domain_checks"] = domain_checks
    manifest.setdefault("summary", {})["render_domain_checks"] = domain_checks
    native_render_diagnostics = native_render.native_isaac_render_diagnostics_summary(
        isaac_state=isaac_state,
        locations=successful_locations,
    )
    manifest["native_isaac_render_diagnostics"] = native_render_diagnostics
    manifest.setdefault("summary", {})["native_isaac_render_diagnostics"] = (
        object_gate.compact_native_isaac_render_diagnostics(native_render_diagnostics)
    )
    if skip_object_parity_audit:
        skipped_audit = object_parity.skipped_object_parity_audit()
        skipped_gate = object_gate.skipped_object_render_parity_diagnostics(
            render_domain_checks=domain_checks,
            residual_triage=_dict(manifest.get("summary")).get("residual_triage"),
            native_render_diagnostics=native_render_diagnostics,
        )
        manifest["object_parity_audit"] = skipped_audit
        manifest["object_visual_parity_audit"] = skipped_audit
        manifest.setdefault("summary", {})["object_parity_audit"] = (
            object_parity.compact_object_parity_audit(skipped_audit)
        )
        manifest.setdefault("summary", {})["object_visual_parity_audit"] = (
            object_parity.compact_object_parity_audit(skipped_audit)
        )
        manifest["object_render_parity_diagnostics"] = skipped_gate
        manifest.setdefault("summary", {})["object_render_parity_diagnostics"] = (
            object_gate.compact_object_render_parity_diagnostics(skipped_gate)
        )
        return
    object_audit = object_parity.object_parity_audit(
        mujoco_state=mujoco_state,
        isaac_state=isaac_state,
        mujoco_contract=mujoco_contract,
        isaac_contract=isaac_contract,
        scene_binding_diagnostics=scene_binding_diagnostics,
        locations=successful_locations,
        output_dir=output_dir,
    )
    manifest["object_parity_audit"] = object_audit
    manifest["object_visual_parity_audit"] = object_audit
    manifest.setdefault("summary", {})["object_parity_audit"] = (
        object_parity.compact_object_parity_audit(object_audit)
    )
    manifest.setdefault("summary", {})["object_visual_parity_audit"] = (
        object_parity.compact_object_parity_audit(object_audit)
    )
    gate_diagnostics = object_gate.object_render_parity_diagnostics(
        object_audit=object_audit,
        render_domain_checks=domain_checks,
        residual_triage=_dict(manifest.get("summary")).get("residual_triage"),
        native_render_diagnostics=native_render_diagnostics,
    )
    manifest["object_render_parity_diagnostics"] = gate_diagnostics
    manifest.setdefault("summary", {})["object_render_parity_diagnostics"] = (
        object_gate.compact_object_render_parity_diagnostics(gate_diagnostics)
    )


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
    isaac_state: dict[str, Any],
) -> dict[str, Any]:
    target = _dict(item.get("target"))
    target_id = str(target.get("target_id") or "")
    target_kind = str(target.get("kind") or "object")
    target_binding = object_parity.target_usd_binding(scene_binding_diagnostics, target)
    target_binding_usd_path = str(target_binding.get("usd_prim_path") or "")
    fallback_entry = object_parity.isaac_effective_index_entry(isaac_state, target_kind, target_id)
    fallback_usd_path = object_parity.isaac_index_usd_prim_path(fallback_entry)
    usd_prim_path = target_binding_usd_path or fallback_usd_path
    usd_path_source = (
        "scene_binding_diagnostics"
        if target_binding_usd_path
        else "isaac_state_index"
        if fallback_usd_path
        else "missing"
    )
    mujoco_target = _mujoco_view_render_contract(mujoco_contract, anchor_id=target_id)
    isaac_target = _isaac_view_render_contract(isaac_contract, usd_prim_path=usd_prim_path)
    target_delta = _view_render_contract_delta(
        suspicion="object_material_texture_binding_contract",
        mujoco=mujoco_target,
        isaac=isaac_target,
    )
    fpv_diff = _dict_path(item, ("image_diffs", "fpv"))
    fpv_residual = _dict_path(item, ("image_diffs", "fpv", "residual"))
    chase_residual = _dict_path(item, ("image_diffs", "chase", "residual"))
    return {
        "schema": "robot_camera_location_render_contract_diagnostics_v1",
        "target": target,
        "target_usd_binding": object_parity.compact_target_binding(target_binding),
        "target_usd_path_source": usd_path_source,
        "target_usd_path_fallback": object_parity.compact_isaac_index_entry(
            fallback_entry,
            usd_prim_path=fallback_usd_path,
        )
        if not target_binding_usd_path and fallback_usd_path
        else {},
        "fpv_mean_abs_rgb": _float_or_none(fpv_diff.get("mean_abs_rgb")),
        "fpv_residual_class": fpv_residual.get("residual_class"),
        "fpv_edge_abs_diff": _float_or_none(fpv_residual.get("edge_abs_diff")),
        "fpv_rgb_gain_oracle_mean_abs_rgb_after_gain": _float_or_none(
            _dict(fpv_residual.get("rgb_gain_oracle")).get("mean_abs_rgb_after_gain")
        ),
        "fpv_mujoco_mean_luminance": _float_or_none(
            _dict(fpv_residual.get("left_metrics")).get("mean_luminance")
        ),
        "fpv_isaac_mean_luminance": _float_or_none(
            _dict(fpv_residual.get("right_metrics")).get("mean_luminance")
        ),
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
    material_response_probe_manifest_paths: list[Path] | None,
    tone_color_probe_manifest_paths: list[Path] | None,
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
        material_checks.texture_colorspace_material_response_check(per_location),
        material_checks.usd_preview_surface_material_model_check(
            manifest=manifest,
            output_dir=output_dir,
            per_location=per_location,
            probe_manifest_paths=material_response_probe_manifest_paths,
        ),
        _tone_color_response_check(
            manifest=manifest,
            output_dir=output_dir,
            locations=locations,
            isaac_state=isaac_state,
            probe_manifest_paths=tone_color_probe_manifest_paths,
        ),
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
    baseline = material_checks.probe_manifest_summary(
        manifest, manifest_path=output_dir / "comparison_manifest.json"
    )
    probes = []
    comparable_count = 0
    improved_count = 0
    worsened_count = 0
    for path in paths:
        probe = _load_light_shadow_probe_manifest(path, output_dir=output_dir)
        if probe.get("status") == "loaded":
            comparable = material_checks.comparison_probe_comparable(baseline, probe)
            probe["comparable_to_current"] = comparable
            if comparable:
                comparable_count += 1
            delta = material_checks.comparison_probe_delta(baseline, probe)
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
            "path": output_relpath(path, output_dir),
        }
    try:
        payload = _read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "read_failed",
            "path": output_relpath(path, output_dir),
            "error": f"{type(exc).__name__}: {exc}",
        }
    return material_checks.probe_manifest_summary(
        payload,
        manifest_path=path,
        output_dir=output_dir,
    )


def _tone_color_response_check(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    locations: list[dict[str, Any]],
    isaac_state: dict[str, Any],
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    triage = image_metrics.residual_triage(locations)
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
    probe_history = material_checks.tone_color_probe_history(
        manifest,
        output_dir=output_dir,
        probe_manifest_paths=probe_manifest_paths,
    )
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
    if probe_history.get("improved_probe_count"):
        next_action = (
            "Treat RGB/tone calibration as the strongest current comparison-only direction; "
            "broaden the same post-FOV head-camera corpus before promoting any default "
            "renderer or preprocessing change."
        )
    elif probe_history.get("worsened_probe_count"):
        next_action = (
            "Do not promote the attached tone/color probes directly; keep per-view oracle "
            "gain as diagnostics while testing narrower color-management hypotheses."
        )
    else:
        next_action = (
            "Keep RGB gain as comparison-only until it improves a broader post-FOV corpus; "
            "use per-view oracle gain to separate color response from geometry/material "
            "residuals."
        )
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
        "probe_history": probe_history,
        "residual_triage_status": triage.get("status"),
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


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


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


def _positive_int_arg(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive integer; got {value!r}") from None
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer; got {value!r}")
    return parsed


def _write_outputs(manifest: dict[str, Any], output_dir: Path) -> None:
    _write_json(output_dir / "comparison_manifest.json", manifest)
    (output_dir / "report.html").write_text(
        report_renderer.render_report(manifest), encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main())
