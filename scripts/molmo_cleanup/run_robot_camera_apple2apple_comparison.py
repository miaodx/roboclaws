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

from roboclaws.household.generated_mess import (
    build_generated_mess_manifest,
    generated_mess_manifest_object_ids,
)
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
OBJECT_PARITY_POSE_THRESHOLD_M = 0.05
OBJECT_VISUAL_STATE_REGISTRY = {
    "box": {
        "schema": "robot_camera_object_visual_state_registry_entry_v1",
        "category": "box",
        "status": "active_category_contract",
        "protected_by": "prepared_usd_visual_physics_freeze",
        "policy": (
            "MuJoCo box flap joints render at MJCF ref/range endpoints. Prepared Isaac "
            "report USDs must freeze baked visual xforms and remove physics state before "
            "camera capture so the flaps cannot re-open during static visual comparison."
        ),
        "evidence_artifact": (
            "output/molmo/robot-camera-apple2apple/"
            "0603_val1_seed8_2mess_4loc_default_combined_chasefix/report.html"
        ),
        "promotion_rule": (
            "Keep this category-level contract until corpus evidence shows another "
            "visual-state category needs its own registry entry."
        ),
    }
}
OBJECT_VISUAL_STATE_CATEGORIES = set(OBJECT_VISUAL_STATE_REGISTRY)
ISAAC_NATIVE_RENDER_DIAGNOSTICS_SCHEMA = "isaac_native_render_diagnostics_v1"


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
    args = parser.parse_args(argv)

    if args.refresh_report_only:
        manifest = refresh_report_only(
            args.output_dir,
            light_shadow_probe_manifest_paths=args.light_shadow_probe_manifest,
            material_response_probe_manifest_paths=args.material_response_probe_manifest,
            tone_color_probe_manifest_paths=args.tone_color_probe_manifest,
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
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_scene_state_path = output_dir / "canonical_scene_state.json"
    generated_mess_manifest_path = output_dir / "generated_mess_manifest.json"
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
        "camera_contract": _robot_camera_contract(),
        "lanes": {},
        "locations": [],
        "artifacts": {
            "manifest": "comparison_manifest.json",
            "report": "report.html",
            "generated_mess_manifest": "generated_mess_manifest.json",
        },
    }

    canonical_mess_manifest: dict[str, Any] = {}
    try:
        _run_json(
            [
                str(args.mujoco_python),
                "scripts/molmo_cleanup/molmospaces_subprocess_worker.py",
                "--state-path",
                str(canonical_scene_state_path),
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
            _read_json(canonical_scene_state_path),
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
        _write_json(generated_mess_manifest_path, canonical_mess_manifest)
        manifest["mess_generation"] = _mess_generation_summary(
            canonical_mess_manifest,
            output_dir=output_dir,
            manifest_path=generated_mess_manifest_path,
        )
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
                "--generated-mess-manifest-path",
                str(generated_mess_manifest_path),
                "--include-robot",
                "--robot-name",
                "rby1m",
            ],
            cwd=Path.cwd(),
        )
        isaac_init_command = [
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
            "--generated-mess-manifest-path",
            str(generated_mess_manifest_path),
            "--runtime-mode",
            "real",
            "--include-robot",
            "--robot-name",
            "rby1m",
            "--scene-usd-path",
            str(args.scene_usd_path),
        ]
        isaac_init = _run_json(
            isaac_init_command,
            cwd=Path.cwd(),
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
                output_dir=output_dir,
                manifest_path=generated_mess_manifest_path,
            )
        manifest["status"] = "blocked"
        manifest["blocker"] = str(exc)
        _write_outputs(manifest, output_dir)
        return manifest

    manifest["lanes"][MUJOCO_LANE_ID] = _lane_init_summary(mujoco_init)
    manifest["lanes"][ISAAC_LANE_ID] = _lane_init_summary(isaac_init)
    manifest["lanes"][ISAAC_LANE_ID]["robot_import"] = isaac_init.get("robot_import", {})

    mujoco_state = _read_json(mujoco_state_path)
    isaac_state = _read_json(isaac_state_path)
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
    except Exception as exc:
        manifest["status"] = "blocked"
        manifest["blocker"] = str(exc)
        _write_outputs(manifest, output_dir)
        return manifest
    _attach_state_artifact_summaries(
        manifest,
        output_dir=output_dir,
        mujoco_state=mujoco_state,
        isaac_state=isaac_state,
    )
    target_selection = _select_comparison_targets(
        mujoco_state,
        limit=max(1, int(args.location_count)),
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
    manifest["summary"]["target_selection"] = target_selection
    _attach_render_contract_diagnostics(
        manifest,
        output_dir=output_dir,
        light_shadow_probe_manifest_paths=args.light_shadow_probe_manifest,
        material_response_probe_manifest_paths=args.material_response_probe_manifest,
        tone_color_probe_manifest_paths=args.tone_color_probe_manifest,
    )
    _write_outputs(manifest, output_dir)
    return manifest


def refresh_report_only(
    output_dir: Path,
    light_shadow_probe_manifest_paths: list[Path] | None = None,
    material_response_probe_manifest_paths: list[Path] | None = None,
    tone_color_probe_manifest_paths: list[Path] | None = None,
) -> dict[str, Any]:
    manifest_path = output_dir / "comparison_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = _read_json(manifest_path)
    manifest["camera_contract"] = _robot_camera_contract()
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
    _refresh_location_camera_contract_diagnostics(locations)
    manifest["summary"] = _summary(locations)
    manifest["summary"]["target_selection"] = target_selection
    _attach_render_contract_diagnostics(
        manifest,
        output_dir=output_dir,
        light_shadow_probe_manifest_paths=light_shadow_probe_manifest_paths,
        material_response_probe_manifest_paths=material_response_probe_manifest_paths,
        tone_color_probe_manifest_paths=tone_color_probe_manifest_paths,
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
        "artifact": _relpath(manifest_path, output_dir),
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


def _robot_camera_contract() -> dict[str, Any]:
    return {
        "fpv": {
            MUJOCO_LANE_ID: "robot_0/head_camera",
            ISAAC_LANE_ID: "/World/robot_0/head_camera",
        },
        "chase": {
            MUJOCO_LANE_ID: "robot_0/camera_follower",
            ISAAC_LANE_ID: "robot_relative_camera_follower",
        },
        "policy_input_note": "FPV is the robot camera. Chase is report evidence only.",
    }


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
        selected = bound_candidates[:limit]
        dropped = [
            item
            for item in candidates
            if str(item.get("target_id") or "")
            not in binding_ids.get(str(item.get("kind") or ""), set())
        ]
        status = "isaac_bound_targets_selected"
    else:
        selected = candidates[:limit]
        dropped = []
        status = "unfiltered_no_isaac_binding_diagnostics"
    return {
        "schema": "robot_camera_comparison_target_selection_v1",
        "status": status,
        "requested_limit": limit,
        "candidate_count": len(candidates),
        "isaac_bound_candidate_count": len(bound_candidates) if any(binding_ids.values()) else 0,
        "selected_count": len(selected),
        "selected_targets": selected,
        "dropped_unbound_target_count": len(dropped),
        "dropped_unbound_targets": dropped[:10],
        "not_selected_bound_target_count": max(
            0,
            (len(bound_candidates) if any(binding_ids.values()) else len(candidates))
            - len(selected),
        ),
        "not_selected_bound_targets": (
            bound_candidates[len(selected) : len(selected) + 10]
            if any(binding_ids.values())
            else candidates[len(selected) : len(selected) + 10]
        ),
        "interpretation": (
            "Robot-camera apple-to-apple image parity renders a bounded subset of targets "
            "that both backends can bind to USD/MJCF render contracts. Objects outside "
            "this selected image subset are still covered by object_parity_audit when "
            "state/index evidence is available."
        ),
    }


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
        native_render = _native_isaac_render_diagnostics_from_state(isaac_state)
        if native_render:
            isaac_lane["native_render_diagnostics"] = _compact_native_isaac_render_diagnostics(
                native_render
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
    material_response_probe_manifest_paths: list[Path] | None = None,
    tone_color_probe_manifest_paths: list[Path] | None = None,
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
        material_response_probe_manifest_paths=material_response_probe_manifest_paths,
        tone_color_probe_manifest_paths=tone_color_probe_manifest_paths,
    )
    manifest["render_domain_checks"] = domain_checks
    manifest.setdefault("summary", {})["render_domain_checks"] = domain_checks
    native_render_diagnostics = _native_isaac_render_diagnostics_summary(
        isaac_state=isaac_state,
        locations=successful_locations,
    )
    manifest["native_isaac_render_diagnostics"] = native_render_diagnostics
    manifest.setdefault("summary", {})["native_isaac_render_diagnostics"] = (
        _compact_native_isaac_render_diagnostics(native_render_diagnostics)
    )
    object_audit = _object_parity_audit(
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
    manifest.setdefault("summary", {})["object_parity_audit"] = _compact_object_parity_audit(
        object_audit
    )
    manifest.setdefault("summary", {})["object_visual_parity_audit"] = _compact_object_parity_audit(
        object_audit
    )
    gate_diagnostics = _object_render_parity_diagnostics(
        object_audit=object_audit,
        render_domain_checks=domain_checks,
        residual_triage=_dict(manifest.get("summary")).get("residual_triage"),
        native_render_diagnostics=native_render_diagnostics,
    )
    manifest["object_render_parity_diagnostics"] = gate_diagnostics
    manifest.setdefault("summary", {})["object_render_parity_diagnostics"] = (
        _compact_object_render_parity_diagnostics(gate_diagnostics)
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


def _native_isaac_render_diagnostics_from_state(isaac_state: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        _dict(isaac_state.get("native_render_diagnostics")),
        _dict(
            _dict(isaac_state.get("robot_view_camera_diagnostics")).get("native_render_diagnostics")
        ),
        _dict(
            _dict(_dict(isaac_state.get("runtime")).get("rendering")).get(
                "native_render_diagnostics"
            )
        ),
        _dict(_dict(isaac_state.get("real_runtime_smoke")).get("native_render_diagnostics")),
    ]
    for candidate in candidates:
        if candidate.get("schema") == ISAAC_NATIVE_RENDER_DIAGNOSTICS_SCHEMA:
            return candidate
    for candidate in candidates:
        if candidate:
            return candidate
    return {}


def _native_isaac_render_diagnostics_summary(
    *,
    isaac_state: dict[str, Any],
    locations: list[dict[str, Any]],
) -> dict[str, Any]:
    state_diagnostics = _native_isaac_render_diagnostics_from_state(isaac_state)
    location_diagnostics = [
        _dict(
            _dict(_dict(item.get("camera_diagnostics")).get("isaac")).get(
                "native_render_diagnostics"
            )
        )
        for item in locations
        if isinstance(item, dict)
    ]
    location_diagnostics = [
        item
        for item in location_diagnostics
        if item.get("schema") == ISAAC_NATIVE_RENDER_DIAGNOSTICS_SCHEMA
    ]
    primary = state_diagnostics or (location_diagnostics[0] if location_diagnostics else {})
    if not primary:
        status = "missing_native_diagnostics"
        next_action = (
            "Record Isaac native RTX/camera settings before treating brightness residuals "
            "as renderer-domain evidence."
        )
    elif primary.get("status") == "fake_protocol":
        status = "fake_protocol_schema_present"
        next_action = (
            "CI fake mode proves the diagnostics schema only; run a local Isaac capture "
            "to read real native RTX/camera settings."
        )
    elif primary.get("settings_api_available") is False:
        status = "native_settings_api_unavailable"
        next_action = (
            "The worker did not read Kit settings in this capture. Confirm Isaac exposes "
            "carb.settings before promoting a native exposure/tone preset."
        )
    else:
        status = "native_settings_recorded"
        next_action = (
            "Native Isaac settings are recorded. Compare held-out FPV and chase residuals "
            "before changing any default exposure or tone setting."
        )
    return {
        "schema": "robot_camera_native_isaac_render_diagnostics_v1",
        "status": status,
        "native_settings_recorded": status == "native_settings_recorded",
        "primary": primary,
        "location_diagnostic_count": len(location_diagnostics),
        "location_status_counts": _status_counts(
            item.get("status") for item in location_diagnostics
        ),
        "renderer_mode": primary.get("renderer_mode"),
        "capture_method": primary.get("capture_method"),
        "view_kind": primary.get("view_kind"),
        "settings_api_available": primary.get("settings_api_available"),
        "available_setting_count": primary.get("available_setting_count"),
        "missing_setting_count": primary.get("missing_setting_count"),
        "tone_mapping": _compact_native_setting_group(_dict(primary.get("tone_mapping"))),
        "camera_exposure": _compact_native_setting_group(_dict(primary.get("camera_exposure"))),
        "ocio": _compact_native_setting_group(_dict(primary.get("ocio"))),
        "color_correction": _compact_native_setting_group(_dict(primary.get("color_correction"))),
        "color_grading": _compact_native_setting_group(_dict(primary.get("color_grading"))),
        "renderer": _compact_native_setting_group(_dict(primary.get("renderer"))),
        "camera_prim_paths": primary.get("camera_prim_paths") or [],
        "render_product_paths": primary.get("render_product_paths") or [],
        "render_resolution": primary.get("render_resolution") or {},
        "isaac_lab_isp_active": primary.get("isaac_lab_isp_active"),
        "settings_mutation_attempted": primary.get("settings_mutation_attempted") is True,
        "default_render_settings_changed": primary.get("default_render_settings_changed") is True,
        "post_render_comparison_profile": primary.get("post_render_comparison_profile") or {},
        "recommended_next_action": next_action,
        "interpretation": (
            "These rows are native Isaac/RTX and camera diagnostics read from the Isaac "
            "capture path. They are separate from Roboclaws report-side RGB gain or "
            "color-profile comparison controls and do not change cleanup render defaults."
        ),
    }


def _compact_native_setting_group(group: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, raw in group.items():
        row = _dict(raw)
        compact[str(key)] = {
            "status": row.get("status"),
            "value": row.get("value"),
            "setting_path": row.get("setting_path"),
        }
    return compact


def _compact_native_isaac_render_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    primary = _dict(diagnostics.get("primary")) or diagnostics
    return {
        "schema": diagnostics.get("schema") or primary.get("schema"),
        "status": diagnostics.get("status") or primary.get("status"),
        "native_settings_recorded": diagnostics.get("native_settings_recorded"),
        "renderer_mode": diagnostics.get("renderer_mode") or primary.get("renderer_mode"),
        "capture_method": diagnostics.get("capture_method") or primary.get("capture_method"),
        "view_kind": diagnostics.get("view_kind") or primary.get("view_kind"),
        "settings_api_available": diagnostics.get("settings_api_available")
        if "settings_api_available" in diagnostics
        else primary.get("settings_api_available"),
        "available_setting_count": diagnostics.get("available_setting_count")
        if "available_setting_count" in diagnostics
        else primary.get("available_setting_count"),
        "missing_setting_count": diagnostics.get("missing_setting_count")
        if "missing_setting_count" in diagnostics
        else primary.get("missing_setting_count"),
        "camera_prim_paths": diagnostics.get("camera_prim_paths")
        or primary.get("camera_prim_paths")
        or [],
        "render_product_paths": diagnostics.get("render_product_paths")
        or primary.get("render_product_paths")
        or [],
        "isaac_lab_isp_active": diagnostics.get("isaac_lab_isp_active")
        if "isaac_lab_isp_active" in diagnostics
        else primary.get("isaac_lab_isp_active"),
        "default_render_settings_changed": diagnostics.get("default_render_settings_changed")
        if "default_render_settings_changed" in diagnostics
        else primary.get("default_render_settings_changed"),
        "post_render_comparison_profile": diagnostics.get("post_render_comparison_profile")
        or primary.get("post_render_comparison_profile")
        or {},
        "recommended_next_action": diagnostics.get("recommended_next_action"),
    }


def _object_parity_audit(
    *,
    mujoco_state: dict[str, Any],
    isaac_state: dict[str, Any],
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    scene_binding_diagnostics: dict[str, Any],
    locations: list[dict[str, Any]] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    object_ids = sorted(
        set(_dict(mujoco_state.get("objects")))
        | set(_dict(isaac_state.get("object_index")))
        | _bound_ids_from_groups(scene_binding_diagnostics, ("object_bindings",))
    )
    receptacle_ids = sorted(
        set(_dict(mujoco_state.get("receptacles")))
        | set(_dict(isaac_state.get("receptacle_index")))
        | _bound_ids_from_groups(scene_binding_diagnostics, ("receptacle_bindings",))
    )
    for target_id in object_ids:
        items.append(
            _object_parity_item(
                kind="object",
                target_id=str(target_id),
                mujoco_state=mujoco_state,
                isaac_state=isaac_state,
                mujoco_contract=mujoco_contract,
                isaac_contract=isaac_contract,
                scene_binding_diagnostics=scene_binding_diagnostics,
                locations=locations or [],
                output_dir=output_dir,
            )
        )
    for target_id in receptacle_ids:
        items.append(
            _object_parity_item(
                kind="receptacle",
                target_id=str(target_id),
                mujoco_state=mujoco_state,
                isaac_state=isaac_state,
                mujoco_contract=mujoco_contract,
                isaac_contract=isaac_contract,
                scene_binding_diagnostics=scene_binding_diagnostics,
                locations=locations or [],
                output_dir=output_dir,
            )
        )
    high_priority_statuses = {
        "missing_isaac_index",
        "missing_mujoco_state",
        "isaac_geometry_gap",
        "missing_usd_prim_path",
        "category_delta",
        "pose_delta",
        "support_metadata_delta",
        "state_delta",
        "state_not_rendered_to_usd",
        "visual_state_articulation_physics_preserved",
        "visual_state_unverified",
        "material_or_texture_name_delta",
        "missing_object_binding_evidence",
    }
    high_priority = [
        item
        for item in items
        if any(status in high_priority_statuses for status in _object_parity_item_statuses(item))
    ]
    if not items:
        status = "no_scene_objects"
        next_action = "No MuJoCo or Isaac scene objects were available for object parity audit."
    elif high_priority:
        status = "object_parity_gaps_detected"
        next_action = (
            "Inspect high-priority object parity rows before changing camera settings. "
            "Start with missing bindings, category/pose/support deltas, and USD state "
            "that is not rendered to geometry."
        )
    else:
        status = "object_parity_index_aligned"
        next_action = (
            "Object indices and compact material/state contracts align for this scene; "
            "remaining residuals are likely renderer response or robot visual import."
        )
    return {
        "schema": "robot_camera_object_parity_audit_v1",
        "status": status,
        "item_count": len(items),
        "object_count": sum(1 for item in items if item.get("kind") == "object"),
        "receptacle_count": sum(1 for item in items if item.get("kind") == "receptacle"),
        "high_priority_gap_count": len(high_priority),
        "binding_status_counts": _status_counts(item.get("binding_status") for item in items),
        "category_status_counts": _status_counts(item.get("category_status") for item in items),
        "pose_status_counts": _status_counts(item.get("pose_status") for item in items),
        "support_status_counts": _status_counts(item.get("support_status") for item in items),
        "state_status_counts": _status_counts(item.get("state_status") for item in items),
        "render_contract_status_counts": _status_counts(
            _dict(item.get("render_contract_delta")).get("status") for item in items
        ),
        "category_status_summary": _object_category_status_summary(items),
        "high_priority_items": high_priority[:20],
        "items": items,
        "recommended_next_action": next_action,
        "interpretation": (
            "This audit checks scene objects/receptacles beyond the limited image target "
            "set. It compares MuJoCo state and MJCF render contracts against Isaac USD "
            "indices, compact USD bounds, parent/support metadata, semantic open state, "
            "and PreviewSurface material bindings."
        ),
    }


def _compact_object_parity_audit(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": audit.get("schema"),
        "status": audit.get("status"),
        "item_count": audit.get("item_count"),
        "object_count": audit.get("object_count"),
        "receptacle_count": audit.get("receptacle_count"),
        "high_priority_gap_count": audit.get("high_priority_gap_count"),
        "binding_status_counts": audit.get("binding_status_counts"),
        "category_status_counts": audit.get("category_status_counts"),
        "pose_status_counts": audit.get("pose_status_counts"),
        "support_status_counts": audit.get("support_status_counts"),
        "state_status_counts": audit.get("state_status_counts"),
        "render_contract_status_counts": audit.get("render_contract_status_counts"),
        "category_status_summary": audit.get("category_status_summary"),
        "high_priority_items": audit.get("high_priority_items"),
        "recommended_next_action": audit.get("recommended_next_action"),
    }


def _object_category_status_summary(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        mujoco = _dict(item.get("mujoco"))
        isaac = _dict(item.get("isaac"))
        category = (
            _object_category_key(mujoco.get("category"))
            or _object_category_key(isaac.get("category"))
            or _object_category_key(isaac.get("usd_category"))
            or "unknown"
        )
        grouped.setdefault(category, []).append(item)
    rows = []
    for category, category_items in sorted(grouped.items()):
        records = [_object_gate_record(item) for item in category_items]
        rows.append(
            {
                "category": category,
                "item_count": len(category_items),
                "kind_counts": _status_counts(item.get("kind") for item in category_items),
                "object_gate_status_counts": _status_counts(
                    record.get("object_gate_status") for record in records
                ),
                "object_gate_classification_counts": _status_counts(
                    record.get("classification") for record in records
                ),
                "binding_status_counts": _status_counts(
                    item.get("binding_status") for item in category_items
                ),
                "category_status_counts": _status_counts(
                    item.get("category_status") for item in category_items
                ),
                "pose_status_counts": _status_counts(
                    item.get("pose_status") for item in category_items
                ),
                "support_status_counts": _status_counts(
                    item.get("support_status") for item in category_items
                ),
                "state_status_counts": _status_counts(
                    item.get("state_status") for item in category_items
                ),
                "rgb_view_evidence_status_counts": _status_counts(
                    _dict(item.get("rgb_view_evidence")).get("status") for item in category_items
                ),
                "render_contract_status_counts": _status_counts(
                    _dict(item.get("render_contract_delta")).get("status")
                    for item in category_items
                ),
            }
        )
    return rows


def _object_render_parity_diagnostics(
    *,
    object_audit: dict[str, Any],
    render_domain_checks: dict[str, Any],
    residual_triage: dict[str, Any] | None,
    native_render_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items = _list_dicts(object_audit.get("items"))
    item_records = [_object_gate_record(item) for item in items]
    object_failures = [
        item for item in item_records if item.get("object_gate_status") != "comparable"
    ]
    comparable = [item for item in item_records if item.get("object_gate_status") == "comparable"]
    render_gate = _render_gate_diagnostics(
        comparable_records=comparable,
        render_domain_checks=render_domain_checks,
        residual_triage=residual_triage or {},
        native_render_diagnostics=native_render_diagnostics or {},
    )
    object_gate_status = (
        "no_object_records"
        if not item_records
        else "object_gate_failures_detected"
        if object_failures
        else "object_gate_comparable"
    )
    if object_gate_status == "no_object_records":
        status = "no_object_records"
        next_action = "Run a comparison with MuJoCo/Isaac state artifacts before parity claims."
    elif object_failures:
        status = "object_gate_failures_detected"
        next_action = (
            "Fix or mark non-comparable object bindings, geometry, pose, material, or "
            "visual-state rows before treating RGB residuals as render-domain evidence."
        )
    else:
        status = render_gate.get("status") or "render_gate_unclassified"
        next_action = str(
            render_gate.get("recommended_next_action")
            or "Comparable object rows are ready for render-domain residual triage."
        )
    return {
        "schema": "robot_camera_object_render_parity_diagnostics_v1",
        "status": status,
        "object_gate": {
            "status": object_gate_status,
            "item_count": len(item_records),
            "comparable_count": len(comparable),
            "failure_count": len(object_failures),
            "status_counts": _status_counts(
                item.get("object_gate_status") for item in item_records
            ),
            "classification_counts": _status_counts(
                item.get("classification") for item in item_records
            ),
            "failure_records": object_failures[:20],
            "comparable_records": comparable[:20],
        },
        "render_gate": render_gate,
        "recommended_next_action": next_action,
        "interpretation": (
            "The Object Gate decides whether scene objects are present, bound, renderable, "
            "posed, and in an auditable visual/material state. The Render Gate only "
            "interprets camera RGB residuals after comparable object rows are separated "
            "from missing or mismatched objects."
        ),
    }


def _compact_object_render_parity_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    object_gate = _dict(diagnostics.get("object_gate"))
    render_gate = _dict(diagnostics.get("render_gate"))
    return {
        "schema": diagnostics.get("schema"),
        "status": diagnostics.get("status"),
        "object_gate_status": object_gate.get("status"),
        "object_gate_item_count": object_gate.get("item_count"),
        "object_gate_comparable_count": object_gate.get("comparable_count"),
        "object_gate_failure_count": object_gate.get("failure_count"),
        "object_gate_status_counts": object_gate.get("status_counts"),
        "object_gate_classification_counts": object_gate.get("classification_counts"),
        "render_gate_status": render_gate.get("status"),
        "render_gate_residual_status": render_gate.get("residual_status"),
        "render_gate_render_domain_status": render_gate.get("render_domain_status"),
        "render_gate_native_isaac_status": render_gate.get("native_isaac_status"),
        "recommended_next_action": diagnostics.get("recommended_next_action"),
    }


def _object_gate_record(item: dict[str, Any]) -> dict[str, Any]:
    statuses = _object_parity_item_statuses(item)
    classification = _object_gate_classification(item, statuses)
    blocking_status = _object_gate_blocking_status(item, statuses)
    object_gate_status = "comparable" if classification == "comparable" else "not_comparable"
    render_delta = _dict(item.get("render_contract_delta"))
    visual_state = _dict(item.get("visual_state_contract"))
    rgb_evidence = _dict(item.get("rgb_view_evidence"))
    return {
        "kind": item.get("kind"),
        "target_id": item.get("target_id"),
        "object_gate_status": object_gate_status,
        "classification": classification,
        "blocking_status": blocking_status,
        "binding_status": item.get("binding_status"),
        "category_status": item.get("category_status"),
        "pose_status": item.get("pose_status"),
        "support_status": item.get("support_status"),
        "state_status": item.get("state_status"),
        "render_contract_status": render_delta.get("status"),
        "visual_state_status": visual_state.get("status"),
        "rgb_view_evidence_status": rgb_evidence.get("status"),
        "pose_delta_m": item.get("pose_delta_m"),
        "mujoco_category": _dict(item.get("mujoco")).get("category"),
        "isaac_category": _dict(item.get("isaac")).get("category")
        or _dict(item.get("isaac")).get("usd_category"),
        "isaac_usd_prim_path": _dict(item.get("isaac")).get("usd_prim_path"),
        "selected_public_target": item.get("selected_public_target"),
    }


def _object_gate_classification(item: dict[str, Any], statuses: set[str]) -> str:
    binding_status = str(item.get("binding_status") or "")
    if binding_status in {"missing_both", "missing_mujoco_state", "missing_isaac_index"}:
        return "missing_binding"
    if binding_status in {"missing_usd_prim_path", "isaac_geometry_gap"}:
        return "missing_renderable_geometry"
    if str(item.get("category_status") or "") == "category_delta":
        return "not_comparable"
    if str(item.get("pose_status") or "") == "pose_delta":
        return "pose_delta"
    if str(item.get("support_status") or "") == "support_metadata_delta":
        return "pose_delta"
    if str(item.get("state_status") or "") in {
        "state_delta",
        "state_not_rendered_to_usd",
        "visual_state_articulation_physics_preserved",
        "visual_state_unverified",
    }:
        return "visual_state_delta"
    if str(_dict(item.get("render_contract_delta")).get("status") or "") in {
        "material_or_texture_name_delta",
        "missing_object_binding_evidence",
    }:
        return "material_delta"
    if any(status.startswith("missing_") for status in statuses):
        return "missing_binding"
    return "comparable"


def _object_gate_blocking_status(item: dict[str, Any], statuses: set[str]) -> str:
    for value in (
        item.get("binding_status"),
        item.get("category_status"),
        item.get("pose_status"),
        item.get("support_status"),
        item.get("state_status"),
        _dict(item.get("visual_state_contract")).get("status"),
        _dict(item.get("render_contract_delta")).get("status"),
    ):
        status = str(value or "")
        if (
            status
            and status in statuses
            and status
            not in {
                "bound_in_both",
                "category_aligned",
                "pose_aligned",
                "support_metadata_aligned",
                "support_not_reported",
                "state_aligned",
                "not_applicable",
                "material_texture_names_match",
            }
        ):
            return status
    return ""


def _render_gate_diagnostics(
    *,
    comparable_records: list[dict[str, Any]],
    render_domain_checks: dict[str, Any],
    residual_triage: dict[str, Any],
    native_render_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    residual_status = str(residual_triage.get("status") or "")
    render_domain_status = str(render_domain_checks.get("status") or "")
    native_status = str(native_render_diagnostics.get("status") or "")
    if not comparable_records:
        status = "blocked_by_object_gate"
        next_action = "No comparable object rows are available for render-domain residual claims."
    elif (
        render_domain_status
        in {
            "render_domain_delta_confirmed",
            "render_domain_checks_low_priority",
        }
        or residual_status
    ):
        status = "render_domain_residual"
        next_action = str(
            render_domain_checks.get("recommended_next_action")
            or residual_triage.get("recommended_next_action")
            or "Continue render-domain triage on comparable object rows."
        )
    else:
        status = "render_gate_unclassified"
        next_action = "Attach render-domain checks and residual triage before render claims."
    return {
        "schema": "robot_camera_render_gate_diagnostics_v1",
        "status": status,
        "comparable_object_count": len(comparable_records),
        "render_domain_status": render_domain_status,
        "residual_status": residual_status,
        "native_isaac_status": native_status,
        "native_isaac_render_diagnostics": _compact_native_isaac_render_diagnostics(
            native_render_diagnostics
        )
        if native_render_diagnostics
        else {},
        "residual_triage": residual_triage,
        "render_domain_check_status_counts": render_domain_checks.get("check_status_counts") or {},
        "recommended_next_action": next_action,
    }


def _object_parity_item(
    *,
    kind: str,
    target_id: str,
    mujoco_state: dict[str, Any],
    isaac_state: dict[str, Any],
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    scene_binding_diagnostics: dict[str, Any],
    locations: list[dict[str, Any]],
    output_dir: Path | None,
) -> dict[str, Any]:
    mujoco_entry = _mujoco_state_entry(mujoco_state, kind, target_id)
    isaac_entry = _isaac_effective_index_entry(isaac_state, kind, target_id)
    target = {"kind": kind, "target_id": target_id}
    binding = _target_usd_binding(scene_binding_diagnostics, target)
    usd_prim_path = str(
        isaac_entry.get("usd_prim_path")
        or binding.get("usd_prim_path")
        or _dict(_dict(isaac_entry.get("usd_world_bounds")).get("prim")).get("path")
        or ""
    )
    mujoco_category = _object_category_key(mujoco_entry.get("category"))
    isaac_category = _object_category_key(
        isaac_entry.get("category") or isaac_entry.get("usd_category") or binding.get("category")
    )
    mujoco_position = _vec3_or_none(mujoco_entry.get("position"))
    isaac_position = _isaac_index_position(isaac_entry)
    pose_delta = (
        round(_vec_distance(mujoco_position, isaac_position), 6)
        if mujoco_position is not None and isaac_position is not None
        else None
    )
    mujoco_render = _mujoco_view_render_contract(mujoco_contract, anchor_id=target_id)
    isaac_render = _isaac_view_render_contract(isaac_contract, usd_prim_path=usd_prim_path)
    render_delta = _view_render_contract_delta(
        suspicion="object_material_texture_binding_contract",
        mujoco=mujoco_render,
        isaac=isaac_render,
    )
    return {
        "kind": kind,
        "target_id": target_id,
        "binding_status": _object_binding_status(mujoco_entry, isaac_entry, usd_prim_path),
        "selected_public_target": _is_selected_public_target(
            scene_binding_diagnostics,
            kind,
            target_id,
        ),
        "mujoco": _compact_mujoco_object_entry(mujoco_entry),
        "isaac": _compact_isaac_index_entry(isaac_entry, usd_prim_path=usd_prim_path),
        "category_status": _object_category_status(
            mujoco_category=mujoco_category,
            isaac_category=isaac_category,
            mujoco_entry=mujoco_entry,
            isaac_entry=isaac_entry,
        ),
        "pose_status": _object_pose_status(mujoco_position, isaac_position, pose_delta),
        "pose_delta_m": pose_delta,
        "support_status": _object_support_status(mujoco_entry, isaac_entry),
        "state_status": _object_state_status(
            target_id=target_id,
            kind=kind,
            mujoco_entry=mujoco_entry,
            isaac_entry=isaac_entry,
            mujoco_state=mujoco_state,
            isaac_state=isaac_state,
            isaac_contract=isaac_contract,
            usd_prim_path=usd_prim_path,
        ),
        "visual_state_contract": _object_visual_state_contract(
            target_id=target_id,
            kind=kind,
            mujoco_entry=mujoco_entry,
            isaac_entry=isaac_entry,
            mujoco_state=mujoco_state,
            isaac_state=isaac_state,
            isaac_contract=isaac_contract,
            usd_prim_path=usd_prim_path,
        ),
        "rgb_view_evidence": _object_rgb_view_evidence(
            kind=kind,
            target_id=target_id,
            locations=locations,
            output_dir=output_dir,
        ),
        "render_contract_delta": _compact_render_contract_delta(render_delta),
        "render_contract": {
            "mujoco_status": mujoco_render.get("status"),
            "isaac_status": isaac_render.get("status"),
            "mujoco_visual_geom_count": mujoco_render.get("visual_geom_count"),
            "isaac_material_binding_count": isaac_render.get("material_binding_count"),
            "mujoco_materials": mujoco_render.get("materials"),
            "isaac_materials": isaac_render.get("materials"),
            "mujoco_texture_basenames": _path_basenames(
                [str(value) for value in mujoco_render.get("texture_files") or []]
            ),
            "isaac_texture_basenames": _path_basenames(
                [str(value) for value in isaac_render.get("texture_files") or []]
            ),
        },
    }


def _mujoco_state_entry(state: dict[str, Any], kind: str, target_id: str) -> dict[str, Any]:
    group = "receptacles" if kind == "receptacle" else "objects"
    return _dict(_dict(state.get(group)).get(target_id))


def _isaac_index_entry(state: dict[str, Any], kind: str, target_id: str) -> dict[str, Any]:
    group = "receptacle_index" if kind == "receptacle" else "object_index"
    return _dict(_dict(state.get(group)).get(target_id))


def _isaac_effective_index_entry(
    state: dict[str, Any],
    kind: str,
    target_id: str,
) -> dict[str, Any]:
    entry = _isaac_index_entry(state, kind, target_id)
    if kind != "object":
        return entry
    pose = _dict(_dict(_dict(state.get("semantic_pose_state")).get("object_poses")).get(target_id))
    if not pose:
        return entry
    effective = dict(entry)
    position = _vec3_or_none(pose.get("position"))
    if position is not None:
        effective["position"] = [round(float(value), 6) for value in position]
        effective["position_source"] = str(pose.get("position_source") or "semantic_pose_state")
        effective["semantic_pose_position_applied"] = (
            _dict(_dict(state.get("semantic_pose_state")).get("semantic_pose_view_capture")).get(
                "rendered_to_usd"
            )
            is True
        ) or _dict(state.get("semantic_pose_view_capture")).get("rendered_to_usd") is True
    if pose.get("support_receptacle_id"):
        effective["support_receptacle_id"] = str(pose.get("support_receptacle_id"))
    if pose.get("support_usd_prim_path"):
        effective["support_usd_prim_path"] = str(pose.get("support_usd_prim_path"))
    if pose.get("placement_support_status"):
        effective["placement_support_status"] = str(pose.get("placement_support_status"))
    if pose.get("placement_resolution_source"):
        effective["placement_resolution_source"] = str(pose.get("placement_resolution_source"))
    return effective


def _isaac_index_position(entry: dict[str, Any]) -> tuple[float, float, float] | None:
    position = _vec3_or_none(entry.get("position"))
    if position is not None:
        return position
    bounds = _dict(entry.get("usd_world_bounds"))
    center = _vec3_or_none(bounds.get("center"))
    if center is not None:
        return center
    return None


def _object_binding_status(
    mujoco_entry: dict[str, Any],
    isaac_entry: dict[str, Any],
    usd_prim_path: str,
) -> str:
    if not mujoco_entry and not isaac_entry:
        return "missing_both"
    if not mujoco_entry:
        return "missing_mujoco_state"
    if not isaac_entry:
        return "missing_isaac_index"
    if not usd_prim_path:
        return "missing_usd_prim_path"
    if (
        isaac_entry.get("geometry_status") == "missing"
        or isaac_entry.get("valid_stage_prim") is False
    ):
        return "isaac_geometry_gap"
    if isaac_entry.get("has_renderable_geometry") is False:
        return "isaac_geometry_gap"
    return "bound_in_both"


def _object_category_status(
    *,
    mujoco_category: str,
    isaac_category: str,
    mujoco_entry: dict[str, Any],
    isaac_entry: dict[str, Any],
) -> str:
    if not mujoco_entry or not isaac_entry:
        return "missing_entry"
    if not mujoco_category or not isaac_category:
        return "missing_category"
    return "category_aligned" if mujoco_category == isaac_category else "category_delta"


def _object_pose_status(
    mujoco_position: tuple[float, float, float] | None,
    isaac_position: tuple[float, float, float] | None,
    pose_delta: float | None,
) -> str:
    if mujoco_position is None or isaac_position is None or pose_delta is None:
        return "pose_missing"
    if pose_delta <= OBJECT_PARITY_POSE_THRESHOLD_M:
        return "pose_aligned"
    return "pose_delta"


def _object_support_status(mujoco_entry: dict[str, Any], isaac_entry: dict[str, Any]) -> str:
    if not mujoco_entry or not isaac_entry:
        return "missing_entry"
    mujoco_parent = str(
        mujoco_entry.get("location_id")
        or mujoco_entry.get("contained_in")
        or mujoco_entry.get("parent")
        or ""
    )
    isaac_parent = str(isaac_entry.get("parent") or isaac_entry.get("support_receptacle_id") or "")
    if not mujoco_parent and not isaac_parent:
        return "support_not_reported"
    if not mujoco_parent and isaac_parent:
        return "support_available_in_isaac_only"
    if mujoco_parent and not isaac_parent:
        return "support_available_in_mujoco_only"
    if mujoco_parent == isaac_parent:
        return "support_metadata_aligned"
    return "support_metadata_delta"


def _object_rgb_view_evidence(
    *,
    kind: str,
    target_id: str,
    locations: list[dict[str, Any]],
    output_dir: Path | None,
) -> dict[str, Any]:
    selected = None
    for item in locations:
        if not isinstance(item, dict):
            continue
        target = _dict(item.get("target"))
        same_kind = str(target.get("kind") or "") == kind
        same_target = str(target.get("target_id") or "") == target_id
        if same_kind and same_target:
            selected = item
            break
    if selected is None:
        return {
            "status": "not_captured_in_selected_views",
            "selected_target": False,
            "view_status_counts": {},
        }
    views = []
    for backend_id in ("mujoco", "isaac"):
        backend_views = _dict(_dict(selected.get("views")).get(backend_id))
        for view_key in ("fpv", "chase"):
            image_path = str(backend_views.get(view_key) or "")
            evidence = _image_nonblank_evidence(image_path=image_path, output_dir=output_dir)
            views.append(
                {
                    "backend": backend_id,
                    "view": view_key,
                    "image_path": image_path,
                    **evidence,
                }
            )
    status_counts = _status_counts(item.get("status") for item in views)
    if views and all(item.get("status") == "nonblank_rgb" for item in views):
        status = "selected_views_nonblank"
    elif any(item.get("status") == "blank_rgb" for item in views):
        status = "selected_views_blank_rgb"
    elif any(str(item.get("status") or "").startswith("missing") for item in views):
        status = "selected_views_missing_image"
    else:
        status = "selected_views_unverified"
    return {
        "schema": "robot_camera_object_rgb_view_evidence_v1",
        "status": status,
        "selected_target": True,
        "view_status_counts": status_counts,
        "views": views,
        "interpretation": (
            "Selected target FPV/chase image evidence checks whether the rendered RGB "
            "views are present and nonblank. It is not object segmentation and does not "
            "prove per-pixel object coverage without bbox/segmentation evidence."
        ),
    }


def _image_nonblank_evidence(*, image_path: str, output_dir: Path | None) -> dict[str, Any]:
    if not image_path:
        return {"status": "missing_image_path"}
    path = Path(image_path)
    if not path.is_absolute() and output_dir is not None:
        path = output_dir / path
    if not path.exists():
        return {"status": "missing_image_file"}
    try:
        with Image.open(path) as raw:
            metrics = _image_visual_metrics(raw.convert("RGB"))
    except OSError as exc:
        return {"status": "unreadable_image", "error": str(exc)}
    nonblank = (
        metrics.get("mean_luminance", 0.0) > 1.0
        or metrics.get("edge_mean", 0.0) > 0.1
        or metrics.get("overexposed_fraction", 0.0) > 0.0
    )
    return {
        "status": "nonblank_rgb" if nonblank else "blank_rgb",
        "mean_luminance": metrics.get("mean_luminance"),
        "edge_mean": metrics.get("edge_mean"),
        "overexposed_fraction": metrics.get("overexposed_fraction"),
        "underexposed_fraction": metrics.get("underexposed_fraction"),
    }


def _object_state_status(
    *,
    target_id: str,
    kind: str,
    mujoco_entry: dict[str, Any],
    isaac_entry: dict[str, Any],
    mujoco_state: dict[str, Any],
    isaac_state: dict[str, Any],
    isaac_contract: dict[str, Any],
    usd_prim_path: str,
) -> str:
    articulations = _dict(_dict(isaac_state.get("semantic_pose_state")).get("articulations"))
    articulation = _dict(articulations.get(target_id))
    category = _object_category_key(
        mujoco_entry.get("category")
        or isaac_entry.get("category")
        or isaac_entry.get("usd_category")
    )
    if kind != "receptacle" and not articulation:
        if category in OBJECT_VISUAL_STATE_CATEGORIES:
            visual_contract = _object_visual_state_contract(
                target_id=target_id,
                kind=kind,
                mujoco_entry=mujoco_entry,
                isaac_entry=isaac_entry,
                mujoco_state=mujoco_state,
                isaac_state=isaac_state,
                isaac_contract=isaac_contract,
                usd_prim_path=usd_prim_path,
            )
            status = str(visual_contract.get("status") or "")
            if status in {
                "visual_state_static_ref_baked",
                "visual_state_articulation_physics_preserved",
            }:
                return status
            return "visual_state_unverified"
        return "not_applicable"
    mujoco_open = target_id in {
        str(value) for value in mujoco_state.get("open_receptacle_ids") or []
    }
    isaac_open_ids = {str(value) for value in isaac_state.get("open_receptacle_ids") or []}
    isaac_open = target_id in isaac_open_ids or articulation.get("open") is True
    if mujoco_open != isaac_open:
        return "state_delta"
    if isaac_open and articulation and articulation.get("rendered_to_usd") is False:
        return "state_not_rendered_to_usd"
    return "state_aligned"


def _object_visual_state_contract(
    *,
    target_id: str,
    kind: str,
    mujoco_entry: dict[str, Any],
    isaac_entry: dict[str, Any],
    mujoco_state: dict[str, Any],
    isaac_state: dict[str, Any],
    isaac_contract: dict[str, Any],
    usd_prim_path: str,
) -> dict[str, Any]:
    category = _object_category_key(
        mujoco_entry.get("category")
        or isaac_entry.get("category")
        or isaac_entry.get("usd_category")
    )
    if kind != "object" or category not in OBJECT_VISUAL_STATE_CATEGORIES:
        return {"status": "not_applicable"}
    registry_entry = dict(OBJECT_VISUAL_STATE_REGISTRY.get(category) or {})
    mujoco_articulation = _mujoco_ref_endpoint_articulation_contract(
        target_id=target_id,
        mujoco_state=mujoco_state,
    )
    isaac_articulation = _isaac_usd_articulation_contract(
        isaac_contract=isaac_contract,
        usd_prim_path=usd_prim_path,
    )
    if (
        mujoco_articulation.get("status") == "mujoco_ref_endpoint_articulation"
        and isaac_articulation.get("status") == "isaac_visual_physics_frozen"
    ):
        status = "visual_state_static_ref_baked"
        reason = (
            "MuJoCo renders this THOR box at MJCF ref/range endpoint flap joints, and "
            "the prepared Isaac report USD freezes the already-baked visual xforms so "
            "PhysX will not re-open the flaps during camera capture."
        )
    elif (
        mujoco_articulation.get("status") == "mujoco_ref_endpoint_articulation"
        and isaac_articulation.get("status") == "isaac_articulation_physics_preserved"
    ):
        status = "visual_state_articulation_physics_preserved"
        reason = (
            "MuJoCo flap qpos is at MJCF ref/range endpoints, but the Isaac USD still "
            "contains physics joints or rigid-body APIs under the same object. Isaac "
            "camera capture can re-solve those joints, which explains an open-box "
            "visual even when pose, material, and texture names match."
        )
    elif mujoco_articulation.get("status") == "mujoco_ref_endpoint_articulation":
        status = "visual_state_ref_endpoint_unverified_in_isaac"
        reason = (
            "MuJoCo flap qpos is at MJCF ref/range endpoints, but this report lacks "
            "enough Isaac USD physics-freeze evidence to prove visual-state parity."
        )
    else:
        status = "visual_state_unverified"
        reason = (
            "The report does not have enough articulated-state evidence to compare this "
            "object's visual state."
        )
    return {
        "schema": "robot_camera_object_visual_state_contract_v1",
        "status": status,
        "target_id": target_id,
        "category": category,
        "registry": registry_entry,
        "protected_by": registry_entry.get("protected_by"),
        "evidence_artifact": registry_entry.get("evidence_artifact"),
        "mujoco": mujoco_articulation,
        "isaac": isaac_articulation,
        "reason": reason,
    }


def _mujoco_ref_endpoint_articulation_contract(
    *,
    target_id: str,
    mujoco_state: dict[str, Any],
) -> dict[str, Any]:
    joints = _mujoco_joint_state_entries(target_id=target_id, mujoco_state=mujoco_state)
    hinge_joints = [
        joint
        for joint in joints
        if str(joint.get("joint_type") or joint.get("type") or "").lower()
        in {"hinge", "3", "mjjnt_hinge"}
        or "flap" in str(joint.get("joint_name") or "").lower()
    ]
    if not hinge_joints:
        return {
            "status": "missing_mujoco_articulation_evidence",
            "joint_count": 0,
            "endpoint_joint_count": 0,
            "joints": [],
        }
    endpoint_count = sum(
        1 for joint in hinge_joints if _mujoco_joint_at_ref_or_range_endpoint(joint)
    )
    status = (
        "mujoco_ref_endpoint_articulation"
        if endpoint_count == len(hinge_joints)
        else "mujoco_articulation_not_at_ref_endpoint"
    )
    return {
        "status": status,
        "joint_count": len(hinge_joints),
        "endpoint_joint_count": endpoint_count,
        "joints": hinge_joints[:8],
    }


def _mujoco_joint_state_entries(
    *,
    target_id: str,
    mujoco_state: dict[str, Any],
) -> list[dict[str, Any]]:
    explicit = _dict(mujoco_state.get("joint_states"))
    raw_entries = explicit.get(target_id)
    if isinstance(raw_entries, list):
        return [_dict(item) for item in raw_entries if isinstance(item, dict)]
    if isinstance(raw_entries, dict):
        return [_dict(item) for item in raw_entries.values() if isinstance(item, dict)]
    scene_xml = str(mujoco_state.get("scene_xml") or "")
    robot_xml = str(mujoco_state.get("robot_xml") or "")
    qpos = mujoco_state.get("qpos")
    if not scene_xml or not isinstance(qpos, list):
        return []
    try:
        import mujoco

        if mujoco_state.get("robot_included") and robot_xml:
            from scripts.molmo_cleanup.molmospaces_subprocess_worker import _load_robot_model_data

            model, _ = _load_robot_model_data(Path(scene_xml), Path(robot_xml))
        else:
            model = mujoco.MjModel.from_xml_path(scene_xml)
    except Exception:
        return []
    entries: list[dict[str, Any]] = []
    joint_prefixes = _mujoco_joint_target_prefixes(target_id)
    for joint_id in range(model.njnt):
        joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id) or ""
        if not any(joint_name.startswith(prefix) for prefix in joint_prefixes):
            continue
        qposadr = int(model.jnt_qposadr[joint_id])
        qpos_value = float(qpos[qposadr]) if 0 <= qposadr < len(qpos) else None
        joint_range = [float(value) for value in model.jnt_range[joint_id]]
        ref_value = _mujoco_joint_ref_from_scene_xml(scene_xml, joint_name)
        entries.append(
            {
                "joint_name": joint_name,
                "joint_type": str(int(model.jnt_type[joint_id])),
                "qposadr": qposadr,
                "qpos": qpos_value,
                "ref": ref_value,
                "range": joint_range,
                "axis": [float(value) for value in model.jnt_axis[joint_id]],
            }
        )
    return entries


def _mujoco_joint_target_prefixes(target_id: str) -> tuple[str, ...]:
    parts = str(target_id or "").split("_")
    prefixes = [str(target_id or "")]
    if len(parts) >= 4 and parts[-1].isdigit() and parts[-2].isdigit() and parts[-3].isdigit():
        prefixes.append("_".join(parts[:-2]) + "_")
    return tuple(dict.fromkeys(prefix for prefix in prefixes if prefix))


def _mujoco_joint_ref_from_scene_xml(scene_xml: str, joint_name: str) -> float | None:
    try:
        from xml.etree import ElementTree

        root = ElementTree.parse(scene_xml).getroot()
    except Exception:
        return None
    for joint in root.findall(".//joint"):
        if str(joint.attrib.get("name") or "") != joint_name:
            continue
        raw_ref = joint.attrib.get("ref")
        if raw_ref is None:
            return None
        try:
            return float(raw_ref)
        except ValueError:
            return None
    return None


def _mujoco_joint_at_ref_or_range_endpoint(joint: dict[str, Any]) -> bool:
    qpos = _float_or_none(joint.get("qpos"))
    if qpos is None:
        return False
    ref = _float_or_none(joint.get("ref"))
    if ref is not None and abs(qpos - ref) <= 1e-4:
        return True
    raw_range = joint.get("range")
    if isinstance(raw_range, list) and len(raw_range) >= 2:
        lower = _float_or_none(raw_range[0])
        upper = _float_or_none(raw_range[1])
        if lower is not None and abs(qpos - lower) <= 1e-4:
            return True
        if upper is not None and abs(qpos - upper) <= 1e-4:
            return True
    return False


def _isaac_usd_articulation_contract(
    *,
    isaac_contract: dict[str, Any],
    usd_prim_path: str,
) -> dict[str, Any]:
    view_contract = _isaac_view_render_contract(isaac_contract, usd_prim_path=usd_prim_path)
    joint_count = int(view_contract.get("physics_joint_count") or 0)
    api_count = int(view_contract.get("physics_api_schema_prim_count") or 0)
    property_count = int(view_contract.get("physics_property_prim_count") or 0)
    if joint_count or api_count or property_count:
        status = "isaac_articulation_physics_preserved"
    else:
        status = "isaac_visual_physics_frozen"
    return {
        "status": status,
        "usd_prim_path": usd_prim_path,
        "physics_joint_count": joint_count,
        "physics_api_schema_prim_count": api_count,
        "physics_property_prim_count": property_count,
        "physics_joint_paths": view_contract.get("physics_joint_paths") or [],
        "physics_api_schema_prim_paths": view_contract.get("physics_api_schema_prim_paths") or [],
        "physics_property_prim_paths": view_contract.get("physics_property_prim_paths") or [],
        "visual_physics_status": view_contract.get("visual_physics_status"),
    }


def _is_selected_public_target(
    scene_binding_diagnostics: dict[str, Any],
    kind: str,
    target_id: str,
) -> bool:
    groups = (
        ("selected_target_receptacle_bindings",)
        if kind == "receptacle"
        else ("selected_object_bindings",)
    )
    return any(target_id in _dict(scene_binding_diagnostics.get(group)) for group in groups)


def _compact_mujoco_object_entry(entry: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "object_id",
        "receptacle_id",
        "category",
        "name",
        "upstream_object_id",
        "location_id",
        "contained_in",
        "pickupable",
        "position",
        "support_top_z",
    )
    return {key: entry.get(key) for key in keys if key in entry}


def _object_category_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _compact_isaac_index_entry(entry: dict[str, Any], *, usd_prim_path: str) -> dict[str, Any]:
    keys = (
        "asset_id",
        "category",
        "usd_category",
        "metadata_object_id",
        "metadata_handle",
        "parent",
        "geometry_status",
        "has_renderable_geometry",
        "mesh_descendant_count",
        "renderable_descendant_count",
        "missing_referenced_asset_count",
        "valid_stage_prim",
        "position",
        "position_source",
        "semantic_pose_position_applied",
        "support_receptacle_id",
        "placement_support_status",
    )
    compact = {key: entry.get(key) for key in keys if key in entry}
    if usd_prim_path:
        compact["usd_prim_path"] = usd_prim_path
    bounds = _dict(entry.get("usd_world_bounds"))
    if bounds:
        compact["usd_world_bounds"] = {
            key: bounds.get(key) for key in ("center", "size", "min", "max") if key in bounds
        }
    return compact


def _compact_render_contract_delta(delta: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "mujoco_status",
        "isaac_status",
        "mujoco_material_count",
        "isaac_material_count",
        "mujoco_texture_count",
        "isaac_texture_count",
        "material_names_only_in_mujoco",
        "material_names_only_in_isaac",
        "texture_files_only_in_mujoco",
        "texture_files_only_in_isaac",
    )
    return {key: delta.get(key) for key in keys if key in delta}


def _object_parity_item_statuses(item: dict[str, Any]) -> set[str]:
    return {
        str(value)
        for value in (
            item.get("binding_status"),
            item.get("category_status"),
            item.get("pose_status"),
            item.get("support_status"),
            item.get("state_status"),
            _dict(item.get("visual_state_contract")).get("status"),
            _dict(item.get("render_contract_delta")).get("status"),
        )
        if value
    }


def _status_counts(values: Any) -> dict[str, int]:
    collected = [str(value) for value in values if value]
    return {name: collected.count(name) for name in sorted(set(collected))}


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
    fpv_diff = _dict_path(item, ("image_diffs", "fpv"))
    fpv_residual = _dict_path(item, ("image_diffs", "fpv", "residual"))
    chase_residual = _dict_path(item, ("image_diffs", "chase", "residual"))
    return {
        "schema": "robot_camera_location_render_contract_diagnostics_v1",
        "target": target,
        "target_usd_binding": _compact_target_binding(target_binding),
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
        _texture_colorspace_material_response_check(per_location),
        _usd_preview_surface_material_model_check(
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
            comparable = _comparison_probe_comparable(baseline, probe)
            probe["comparable_to_current"] = comparable
            if comparable:
                comparable_count += 1
            delta = _comparison_probe_delta(baseline, probe)
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
    domain_checks = _dict(summary.get("render_domain_checks"))
    check_by_id = {
        str(item.get("check_id")): item
        for item in domain_checks.get("checks") or []
        if isinstance(item, dict) and item.get("check_id")
    }
    tone_color = _dict(check_by_id.get("tone_color_response"))
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
        "tone_color_status": tone_color.get("status"),
        "comparison_rgb_gain_applied": tone_color.get("comparison_rgb_gain_applied"),
        "comparison_rgb_gain": tone_color.get("comparison_rgb_gain"),
    }


def _comparison_probe_comparable(
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


def _comparison_probe_delta(
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


def _material_response_probe_history(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    paths = [Path(path) for path in probe_manifest_paths or []]
    if not paths:
        return {
            "schema": "robot_camera_material_response_probe_history_v1",
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
    neutral_count = 0
    for path in paths:
        probe = _load_material_response_probe_manifest(path, output_dir=output_dir)
        if probe.get("status") == "loaded":
            comparable = _comparison_probe_comparable(baseline, probe)
            probe["comparable_to_current"] = comparable
            if comparable:
                comparable_count += 1
            delta = _comparison_probe_delta(baseline, probe)
            probe["delta_vs_current"] = delta
            if delta.get("fpv_improvement") is True:
                improved_count += 1
            if delta.get("fpv_worse") is True:
                worsened_count += 1
            if (
                comparable
                and delta.get("fpv_improvement") is not True
                and delta.get("fpv_worse") is not True
            ):
                neutral_count += 1
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
        "schema": "robot_camera_material_response_probe_history_v1",
        "status": status,
        "baseline": baseline,
        "probe_count": len(probes),
        "comparable_probe_count": comparable_count,
        "improved_probe_count": improved_count,
        "worsened_probe_count": worsened_count,
        "neutral_probe_count": neutral_count,
        "probes": probes,
        "interpretation": (
            "Historical material-response probes are comparison evidence only. They "
            "separate texture colorspace, PreviewSurface roughness/specular response, "
            "and tone/material effects from the head-camera contract."
        ),
    }


def _load_material_response_probe_manifest(path: Path, *, output_dir: Path) -> dict[str, Any]:
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


def _tone_color_probe_history(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    paths = [Path(path) for path in probe_manifest_paths or []]
    if not paths:
        return {
            "schema": "robot_camera_tone_color_probe_history_v1",
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
    neutral_count = 0
    for path in paths:
        probe = _load_tone_color_probe_manifest(path, output_dir=output_dir)
        if probe.get("status") == "loaded":
            comparable = _comparison_probe_comparable(baseline, probe)
            probe["comparable_to_current"] = comparable
            if comparable:
                comparable_count += 1
            delta = _comparison_probe_delta(baseline, probe)
            probe["delta_vs_current"] = delta
            if comparable and delta.get("fpv_improvement") is True:
                improved_count += 1
            if comparable and delta.get("fpv_worse") is True:
                worsened_count += 1
            if (
                comparable
                and delta.get("fpv_improvement") is not True
                and delta.get("fpv_worse") is not True
            ):
                neutral_count += 1
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
        "schema": "robot_camera_tone_color_probe_history_v1",
        "status": status,
        "baseline": baseline,
        "probe_count": len(probes),
        "comparable_probe_count": comparable_count,
        "improved_probe_count": improved_count,
        "worsened_probe_count": worsened_count,
        "neutral_probe_count": neutral_count,
        "probes": probes,
        "interpretation": (
            "Historical tone/color probes are comparison evidence only. They show whether "
            "RGB gain or tone calibration reduces FPV residuals under the same head-camera "
            "contract before any default renderer or policy-input change."
        ),
    }


def _load_tone_color_probe_manifest(path: Path, *, output_dir: Path) -> dict[str, Any]:
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
    target_summaries = [_texture_material_target_summary(item) for item in per_location]
    target_statuses = [str(item.get("material_response_status") or "") for item in target_summaries]
    target_status_counts = {
        name: target_statuses.count(name) for name in sorted(set(target_statuses)) if name
    }
    high_residual_targets = [
        item
        for item in target_summaries
        if item.get("fpv_residual_class") != "low_residual"
        or float(item.get("fpv_mean_abs_rgb") or 0.0) > 35.0
    ]
    high_residual_targets.sort(
        key=lambda item: float(item.get("fpv_mean_abs_rgb") or 0.0),
        reverse=True,
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
        "material_response_status_counts": target_status_counts,
        "texture_backing_mismatch_count": sum(
            1 for item in target_summaries if item.get("texture_backing_mismatch")
        ),
        "rgba_diffuse_color_mismatch_count": sum(
            1 for item in target_summaries if item.get("rgba_diffuse_color_mismatch")
        ),
        "high_residual_target_count": len(high_residual_targets),
        "high_residual_targets": high_residual_targets[:5],
        "recommended_next_action": (
            "For high-residual FPV views, compare texture color space, sampler behavior, "
            "material albedo, and roughness/specular response even when texture basenames match."
        ),
    }


def _texture_material_target_summary(item: dict[str, Any]) -> dict[str, Any]:
    target = _dict(item.get("target"))
    binding = _dict(item.get("target_usd_binding"))
    delta = _dict(item.get("target_contract_delta"))
    mujoco = _dict(item.get("mujoco_target_contract"))
    isaac = _dict(item.get("isaac_target_contract"))
    mujoco_visuals = [_dict(value) for value in mujoco.get("visuals") or []]
    isaac_bindings = [_dict(value) for value in isaac.get("bindings") or []]
    mujoco_texture_files = [str(value) for value in mujoco.get("texture_files") or []]
    isaac_texture_files = [str(value) for value in isaac.get("texture_files") or []]
    mujoco_texture_basenames = _path_basenames(mujoco_texture_files)
    isaac_texture_basenames = _path_basenames(isaac_texture_files)
    mujoco_texture_backed_visual_count = sum(
        1 for value in mujoco_visuals if value.get("texture") or value.get("texture_file")
    )
    mujoco_rgba_visual_count = sum(1 for value in mujoco_visuals if value.get("rgba"))
    isaac_diffuse_texture_binding_count = sum(
        1
        for value in isaac_bindings
        if value.get("has_diffuse_texture") or value.get("diffuse_texture_files")
    )
    isaac_diffuse_color_binding_count = sum(
        1 for value in isaac_bindings if value.get("diffuse_color")
    )
    texture_backing_mismatch = (
        mujoco_texture_backed_visual_count != isaac_diffuse_texture_binding_count
    )
    rgba_diffuse_color_mismatch = mujoco_rgba_visual_count != isaac_diffuse_color_binding_count
    texture_full_path_delta = set(mujoco_texture_files) != set(isaac_texture_files)
    indicators: list[str] = []
    if delta.get("status") != "material_texture_names_match":
        indicators.append("material_texture_binding_gap")
    if int(binding.get("missing_referenced_asset_count") or 0) > 0:
        indicators.append("missing_referenced_assets")
    if mujoco_texture_basenames == isaac_texture_basenames and texture_full_path_delta:
        indicators.append("texture_full_path_or_source_delta")
    if texture_backing_mismatch:
        indicators.append("texture_backing_count_delta")
    if rgba_diffuse_color_mismatch:
        indicators.append("rgba_vs_usd_diffuse_color_count_delta")
    residual_class = str(item.get("fpv_residual_class") or "")
    if not indicators and residual_class not in {"", "low_residual"}:
        indicators.append("residual_after_material_texture_name_match")
    if "material_texture_binding_gap" in indicators or "missing_referenced_assets" in indicators:
        status = "material_texture_binding_gap"
    elif "texture_full_path_or_source_delta" in indicators:
        status = "texture_path_or_colorspace_unverified"
    elif texture_backing_mismatch or rgba_diffuse_color_mismatch:
        status = "material_source_mix_delta"
    elif residual_class not in {"", "low_residual"}:
        status = "visual_residual_with_material_names_match"
    else:
        status = "material_response_low_priority"
    return {
        "target_id": target.get("target_id"),
        "target_kind": target.get("kind"),
        "fpv_mean_abs_rgb": item.get("fpv_mean_abs_rgb"),
        "fpv_residual_class": item.get("fpv_residual_class"),
        "fpv_edge_abs_diff": item.get("fpv_edge_abs_diff"),
        "fpv_rgb_gain_oracle_mean_abs_rgb_after_gain": item.get(
            "fpv_rgb_gain_oracle_mean_abs_rgb_after_gain"
        ),
        "fpv_mujoco_mean_luminance": item.get("fpv_mujoco_mean_luminance"),
        "fpv_isaac_mean_luminance": item.get("fpv_isaac_mean_luminance"),
        "target_contract_status": delta.get("status"),
        "usd_match_strategy": binding.get("match_strategy"),
        "missing_referenced_asset_count": binding.get("missing_referenced_asset_count"),
        "mujoco_visual_count": mujoco.get("visual_geom_count"),
        "mujoco_texture_backed_visual_count": mujoco_texture_backed_visual_count,
        "mujoco_rgba_visual_count": mujoco_rgba_visual_count,
        "isaac_material_binding_count": isaac.get("material_binding_count"),
        "isaac_diffuse_texture_binding_count": isaac_diffuse_texture_binding_count,
        "isaac_diffuse_color_binding_count": isaac_diffuse_color_binding_count,
        "mujoco_texture_basenames": mujoco_texture_basenames,
        "isaac_texture_basenames": isaac_texture_basenames,
        "texture_full_path_delta": texture_full_path_delta,
        "texture_backing_mismatch": texture_backing_mismatch,
        "rgba_diffuse_color_mismatch": rgba_diffuse_color_mismatch,
        "material_response_status": status,
        "material_response_indicators": indicators,
    }


def _path_basenames(values: list[str]) -> list[str]:
    return sorted({Path(str(value)).name for value in values if value})


def _usd_preview_surface_material_model_check(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    per_location: list[dict[str, Any]],
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    probe_history = _material_response_probe_history(
        manifest,
        output_dir=output_dir,
        probe_manifest_paths=probe_manifest_paths,
    )
    isaac_binding_count = 0
    preview_surface_binding_count = 0
    diffuse_texture_binding_count = 0
    mujoco_visual_count = 0
    mujoco_rgba_visual_count = 0
    preview_input_statuses: list[str] = []
    target_summaries = [_preview_surface_target_summary(item) for item in per_location]
    high_residual_targets = [
        item
        for item in target_summaries
        if item.get("fpv_residual_class") != "low_residual"
        or float(item.get("fpv_mean_abs_rgb") or 0.0) > 35.0
    ]
    high_residual_targets.sort(
        key=lambda item: float(item.get("fpv_mean_abs_rgb") or 0.0),
        reverse=True,
    )
    for item in per_location:
        isaac = _dict(item.get("isaac_target_contract"))
        for binding in isaac.get("bindings") or []:
            if not isinstance(binding, dict):
                continue
            isaac_binding_count += 1
            preview_surface_binding_count += int(bool(binding.get("has_preview_surface")))
            diffuse_texture_binding_count += int(bool(binding.get("has_diffuse_texture")))
            preview_inputs = _dict(binding.get("preview_surface_inputs"))
            preview_input_statuses.extend(
                key
                for key in ("roughness", "opacity", "metallic", "specular")
                if preview_inputs.get(key) is not None
            )
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
    if probe_history.get("improved_probe_count"):
        next_action = (
            "A material-response probe improved FPV under the frozen head-camera "
            "contract, but keep it comparison-only until the same material conversion "
            "direction is validated across more targets, scenes, and seeds. Do not "
            "promote broad raw/colorspace or roughness edits from mixed probe history."
        )
    elif probe_history.get("worsened_probe_count") and probe_history.get("neutral_probe_count"):
        next_action = (
            "Do not promote global material-response edits yet: prior raw/colorspace or "
            "combined probes worsened FPV, while roughness-only evidence is below the "
            "improvement threshold. Continue with target-specific material probes or a "
            "broader corpus before changing defaults."
        )
    elif probe_history.get("worsened_probe_count"):
        next_action = (
            "Do not promote the already-worse material-response probe directly; split "
            "texture sourceColorSpace, PreviewSurface roughness, and target-specific "
            "sampler/material changes in comparison-only probes."
        )
    else:
        next_action = (
            "Inspect USD PreviewSurface diffuse texture/color, roughness, opacity, and "
            "specular conversion against the MJCF material RGBA/texture inputs before "
            "changing the camera contract."
        )
    return {
        "check_id": "usd_preview_surface_material_model",
        "status": status,
        "isaac_material_binding_count": isaac_binding_count,
        "isaac_preview_surface_binding_count": preview_surface_binding_count,
        "isaac_diffuse_texture_binding_count": diffuse_texture_binding_count,
        "mujoco_visual_count": mujoco_visual_count,
        "mujoco_rgba_visual_count": mujoco_rgba_visual_count,
        "preview_surface_input_counts": {
            name: preview_input_statuses.count(name) for name in sorted(set(preview_input_statuses))
        },
        "high_residual_target_count": len(high_residual_targets),
        "high_residual_targets": high_residual_targets[:5],
        "probe_history": probe_history,
        "recommended_next_action": next_action,
    }


def _preview_surface_target_summary(item: dict[str, Any]) -> dict[str, Any]:
    target = _dict(item.get("target"))
    mujoco = _dict(item.get("mujoco_target_contract"))
    isaac = _dict(item.get("isaac_target_contract"))
    visuals = [_dict(value) for value in mujoco.get("visuals") or []]
    bindings = [_dict(value) for value in isaac.get("bindings") or []]
    isaac_preview_inputs = [
        _dict(binding.get("preview_surface_inputs"))
        for binding in bindings
        if binding.get("has_preview_surface")
    ]
    texture_source_color_spaces = sorted(
        {
            str(binding.get("texture_source_color_space"))
            for binding in bindings
            if binding.get("texture_source_color_space")
        }
    )
    texture_scales = [
        binding.get("texture_scale") for binding in bindings if binding.get("texture_scale")
    ]
    texture_fallbacks = [
        binding.get("texture_fallback") for binding in bindings if binding.get("texture_fallback")
    ]
    mujoco_rgba_values = [visual.get("rgba") for visual in visuals if visual.get("rgba")]
    isaac_diffuse_colors = [
        binding.get("diffuse_color") for binding in bindings if binding.get("diffuse_color")
    ]
    return {
        "target_id": target.get("target_id"),
        "target_kind": target.get("kind"),
        "fpv_mean_abs_rgb": item.get("fpv_mean_abs_rgb"),
        "fpv_residual_class": item.get("fpv_residual_class"),
        "fpv_mujoco_mean_luminance": item.get("fpv_mujoco_mean_luminance"),
        "fpv_isaac_mean_luminance": item.get("fpv_isaac_mean_luminance"),
        "mujoco_materials": mujoco.get("materials"),
        "mujoco_textures": mujoco.get("textures"),
        "mujoco_rgba_values": mujoco_rgba_values[:5],
        "isaac_materials": isaac.get("materials"),
        "isaac_diffuse_texture_basenames": _path_basenames(
            [str(value) for value in isaac.get("texture_files") or []]
        ),
        "isaac_diffuse_colors": isaac_diffuse_colors[:5],
        "isaac_preview_surface_inputs": isaac_preview_inputs[:5],
        "isaac_texture_source_color_spaces": texture_source_color_spaces,
        "isaac_texture_scales": texture_scales[:5],
        "isaac_texture_fallbacks": texture_fallbacks[:5],
        "isaac_texture_wrap_modes": sorted(
            {
                f"{binding.get('texture_wrap_s')}/{binding.get('texture_wrap_t')}"
                for binding in bindings
                if binding.get("texture_wrap_s") or binding.get("texture_wrap_t")
            }
        ),
    }


def _tone_color_response_check(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    locations: list[dict[str, Any]],
    isaac_state: dict[str, Any],
    probe_manifest_paths: list[Path] | None,
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
    probe_history = _tone_color_probe_history(
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
        "Chase is report evidence only. Current robot-camera parity runs expect both "
        "backends to use a robot-relative rear/high follower camera, but FPV remains "
        "the policy/input camera contract."
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
    same_camera_contract = (
        str(_dict(mujoco_contract.get("report_chase_view")).get("source") or "")
        == "robot_0/camera_follower"
        and str(_dict(isaac_contract.get("report_chase_view")).get("source") or "")
        == "robot_relative_camera_follower"
    )
    return {
        "same_camera_contract": same_camera_contract,
        "mujoco_source": "robot_0/camera_follower",
        "isaac_source": "robot_relative_camera_follower"
        if same_camera_contract
        else "external rear/high report camera",
        "mujoco_verify_source": mujoco_source,
        "isaac_verify_source": isaac_source,
        "evidence_note": (
            "Chase now uses a robot-relative rear/high report camera in both backends."
            if same_camera_contract
            else "Chase is auxiliary report evidence; FPV is the policy/input camera contract."
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
        + "</pre>"
        + _render_native_isaac_render_diagnostics(manifest)
        + _render_object_render_parity_diagnostics(manifest)
        + _render_object_parity_audit(manifest)
        + "</header>"
        + "".join(rows)
        + "</body></html>"
    )


def _render_native_isaac_render_diagnostics(manifest: dict[str, Any]) -> str:
    diagnostics = _dict(manifest.get("native_isaac_render_diagnostics")) or _dict(
        _dict(manifest.get("summary")).get("native_isaac_render_diagnostics")
    )
    if not diagnostics:
        return ""
    rows = []
    for group_name in (
        "tone_mapping",
        "camera_exposure",
        "ocio",
        "color_correction",
        "color_grading",
        "renderer",
    ):
        group = _dict(diagnostics.get(group_name))
        for field_name, raw in group.items():
            row = _dict(raw)
            rows.append(
                "<tr>"
                f"<td>{html.escape(group_name)}</td>"
                f"<td>{html.escape(str(field_name))}</td>"
                f"<td>{html.escape(str(row.get('status') or ''))}</td>"
                f"<td>{html.escape(str(row.get('value')))}</td>"
                f"<td>{html.escape(str(row.get('setting_path') or ''))}</td>"
                "</tr>"
            )
    table = (
        "<table><thead><tr><th>Group</th><th>Setting</th><th>Status</th>"
        "<th>Value</th><th>Path</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        if rows
        else "<p>No native setting rows were recorded.</p>"
    )
    return (
        "<h2>Native Isaac Render Diagnostics</h2>"
        "<p>Status: <code>"
        + html.escape(str(diagnostics.get("status") or ""))
        + "</code>; renderer <code>"
        + html.escape(str(diagnostics.get("renderer_mode") or ""))
        + "</code>; capture <code>"
        + html.escape(str(diagnostics.get("capture_method") or ""))
        + "</code>. Settings API available: <code>"
        + html.escape(str(diagnostics.get("settings_api_available")))
        + "</code>. Default render settings changed: <code>"
        + html.escape(str(diagnostics.get("default_render_settings_changed")))
        + "</code>.</p><p>"
        + html.escape(str(diagnostics.get("interpretation") or ""))
        + "</p><p>"
        + html.escape(str(diagnostics.get("recommended_next_action") or ""))
        + "</p><pre>"
        + html.escape(
            json.dumps(
                {
                    "camera_prim_paths": diagnostics.get("camera_prim_paths") or [],
                    "render_product_paths": diagnostics.get("render_product_paths") or [],
                    "render_resolution": diagnostics.get("render_resolution") or {},
                    "isaac_lab_isp_active": diagnostics.get("isaac_lab_isp_active"),
                    "post_render_comparison_profile": diagnostics.get(
                        "post_render_comparison_profile"
                    )
                    or {},
                },
                indent=2,
                sort_keys=True,
            )
        )
        + "</pre>"
        + table
    )


def _render_object_render_parity_diagnostics(manifest: dict[str, Any]) -> str:
    diagnostics = _dict(manifest.get("object_render_parity_diagnostics")) or _dict(
        _dict(manifest.get("summary")).get("object_render_parity_diagnostics")
    )
    if not diagnostics:
        return ""
    object_gate = _dict(diagnostics.get("object_gate"))
    render_gate = _dict(diagnostics.get("render_gate"))
    failure_rows = []
    for item in object_gate.get("failure_records") or []:
        if not isinstance(item, dict):
            continue
        failure_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('kind') or ''))}</td>"
            f"<td>{html.escape(str(item.get('target_id') or ''))}</td>"
            f"<td>{html.escape(str(item.get('classification') or ''))}</td>"
            f"<td>{html.escape(str(item.get('blocking_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('binding_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('pose_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('state_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('render_contract_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('isaac_usd_prim_path') or ''))}</td>"
            "</tr>"
        )
    failure_table = (
        "<table><thead><tr><th>Kind</th><th>Target</th><th>Class</th>"
        "<th>Blocking Status</th><th>Binding</th><th>Pose</th><th>State</th>"
        "<th>Render Contract</th><th>Isaac Prim</th>"
        "</tr></thead><tbody>" + "".join(failure_rows) + "</tbody></table>"
        if failure_rows
        else "<p>No Object Gate failures were detected.</p>"
    )
    return (
        "<h2>Object/Render Gate</h2>"
        "<p>Status: <code>"
        + html.escape(str(diagnostics.get("status") or ""))
        + "</code>. Object Gate <code>"
        + html.escape(str(object_gate.get("status") or ""))
        + "</code> with "
        + html.escape(str(object_gate.get("comparable_count") or 0))
        + " comparable and "
        + html.escape(str(object_gate.get("failure_count") or 0))
        + " failing rows. Render Gate <code>"
        + html.escape(str(render_gate.get("status") or ""))
        + "</code>.</p><p>"
        + html.escape(str(diagnostics.get("recommended_next_action") or ""))
        + "</p>"
        + failure_table
    )


def _render_object_parity_audit(manifest: dict[str, Any]) -> str:
    summary = _dict(manifest.get("summary"))
    audit = (
        _dict(manifest.get("object_visual_parity_audit"))
        or _dict(manifest.get("object_parity_audit"))
        or _dict(summary.get("object_visual_parity_audit"))
        or _dict(summary.get("object_parity_audit"))
    )
    if not audit:
        return ""

    def counts_cell(item: dict[str, Any], key: str) -> str:
        return "<td>" + html.escape(json.dumps(item.get(key) or {}, sort_keys=True)) + "</td>"

    category_rows = []
    for item in audit.get("category_status_summary") or []:
        if not isinstance(item, dict):
            continue
        category_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('category') or ''))}</td>"
            f"<td>{html.escape(str(item.get('item_count') or 0))}</td>"
            + counts_cell(item, "kind_counts")
            + counts_cell(item, "object_gate_status_counts")
            + counts_cell(item, "object_gate_classification_counts")
            + counts_cell(item, "binding_status_counts")
            + counts_cell(item, "state_status_counts")
            + counts_cell(item, "rgb_view_evidence_status_counts")
            + counts_cell(item, "render_contract_status_counts")
            + "</tr>"
        )
    category_table = (
        "<h3>Category Status Summary</h3><table><thead><tr>"
        "<th>Category</th><th>Items</th><th>Kinds</th><th>Object Gate</th>"
        "<th>Classes</th><th>Binding</th><th>State</th><th>RGB Evidence</th><th>Render</th>"
        "</tr></thead><tbody>" + "".join(category_rows) + "</tbody></table>"
        if category_rows
        else "<p>No category/status summary rows were recorded.</p>"
    )
    rows = []
    for item in audit.get("high_priority_items") or []:
        if not isinstance(item, dict):
            continue
        render_delta = _dict(item.get("render_contract_delta"))
        visual_state = _dict(item.get("visual_state_contract"))
        rgb_evidence = _dict(item.get("rgb_view_evidence"))
        mujoco = _dict(item.get("mujoco"))
        isaac = _dict(item.get("isaac"))
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('kind') or ''))}</td>"
            f"<td>{html.escape(str(item.get('target_id') or ''))}</td>"
            f"<td>{html.escape(str(item.get('binding_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('category_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('pose_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('support_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('state_status') or ''))}</td>"
            f"<td>{html.escape(str(rgb_evidence.get('status') or ''))}</td>"
            f"<td>{html.escape(str(render_delta.get('status') or ''))}</td>"
            f"<td>{html.escape(str(visual_state.get('protected_by') or ''))}</td>"
            f"<td>{html.escape(str(visual_state.get('evidence_artifact') or ''))}</td>"
            f"<td>{html.escape(str(mujoco.get('category') or ''))}</td>"
            f"<td>{html.escape(str(isaac.get('category') or isaac.get('usd_category') or ''))}</td>"
            f"<td>{html.escape(str(isaac.get('asset_id') or ''))}</td>"
            "</tr>"
        )
    table = (
        "<table><thead><tr>"
        "<th>Kind</th><th>Target</th><th>Binding</th><th>Category</th>"
        "<th>Pose</th><th>Support</th><th>State</th><th>RGB Evidence</th><th>Render</th>"
        "<th>Protected By</th><th>Evidence</th>"
        "<th>MuJoCo Cat</th><th>Isaac Cat</th><th>Isaac Asset</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        if rows
        else "<p>No high-priority object parity gaps were detected.</p>"
    )
    return (
        "<h2>Object Parity Audit</h2>"
        "<p>Status: <code>"
        + html.escape(str(audit.get("status") or ""))
        + "</code>; items "
        + html.escape(str(audit.get("item_count") or 0))
        + "; high-priority gaps "
        + html.escape(str(audit.get("high_priority_gap_count") or 0))
        + ".</p><p>"
        + html.escape(str(audit.get("recommended_next_action") or ""))
        + "</p>"
        + category_table
        + table
    )


if __name__ == "__main__":
    raise SystemExit(main())
