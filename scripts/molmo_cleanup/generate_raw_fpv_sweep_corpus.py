#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]

from roboclaws.household.backend_contract import CleanupBackendSession  # noqa: E402
from roboclaws.household.realworld_contract import (  # noqa: E402
    MINIMAL_MAP_MODE,
    RAW_FPV_ONLY_MODE,
    RealWorldCleanupContract,
)
from roboclaws.household.subprocess_backend import MolmoSpacesSubprocessBackend  # noqa: E402
from scripts.molmo_cleanup.generate_raw_fpv_private_labels import (  # noqa: E402
    MANIFEST_SCHEMA,
    coarse_regions_from_bbox,
    generated_mess_manifest_from_state,
    normalize_box_xywh,
    surface_hint_from_focus,
)

REPORT_SCHEMA = "raw_fpv_public_sweep_corpus_report_v1"
DEFAULT_SOURCE_RUN_DIR = Path(
    "output/household/household-cleanup/codex-camera-raw/0606_1537/seed-7"
)
DEFAULT_OUTPUT_ROOT = Path("output/molmo/raw-fpv-sweep-corpus")
DEFAULT_CAMERA_YAWS = (-45.0, 0.0, 45.0)
DEFAULT_CAMERA_PITCHES = (-10.0, 0.0)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = generate_sweep_corpus(args)
    print(json.dumps(_console_summary(report), indent=2, sort_keys=True))
    return 0 if report.get("status") in {"success", "partial"} else 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a fixed public RAW-FPV sweep corpus from generated exploration "
            "candidates. Public prompt inputs get only frame artifacts and waypoint/camera "
            "metadata; private generated-mess labels are written for scorer use only."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--source-run-dir", type=Path, default=DEFAULT_SOURCE_RUN_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-waypoints", type=int, default=0)
    parser.add_argument(
        "--camera-yaw-deg",
        action="append",
        type=float,
        default=[],
        help="Camera yaw offsets to capture at each public waypoint.",
    )
    parser.add_argument(
        "--camera-pitch-deg",
        action="append",
        type=float,
        default=[],
        help="Camera pitch offsets to capture at each public waypoint.",
    )
    parser.add_argument("--min-object-pixels", type=int, default=12)
    parser.add_argument("--render-width", type=int, default=540)
    parser.add_argument("--render-height", type=int, default=360)
    return parser.parse_args(argv)


def generate_sweep_corpus(args: argparse.Namespace) -> dict[str, Any]:
    source_run_dir = args.source_run_dir.expanduser()
    source_state_path = source_run_dir / "molmospaces_backend_state.json"
    if not source_state_path.is_file():
        raise FileNotFoundError(source_state_path)
    source_state = _load_json(source_state_path)

    output_run_dir = _output_run_dir(args.output_dir, args.run_id)
    output_run_dir.mkdir(parents=True, exist_ok=True)

    generated_manifest = generated_mess_manifest_from_state(source_state)
    generated_manifest_path = output_run_dir / "generated_mess_manifest.private.json"
    generated_manifest_path.write_text(
        json.dumps(generated_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    backend = MolmoSpacesSubprocessBackend(
        run_dir=output_run_dir / "backend",
        seed=int(source_state.get("seed") or 7),
        python_executable=Path(str(source_state.get("python_executable") or sys.executable)),
        scene_source=str(source_state.get("scene_source") or "procthor-10k-val"),
        scene_index=int(source_state.get("scene_index") or 0),
        include_robot=True,
        robot_name=str(source_state.get("robot_name") or "rby1m"),
        generated_mess_count=len(generated_manifest["targets"]),
        generated_mess_manifest_path=generated_manifest_path,
    )
    base_contract = CleanupBackendSession(backend.scenario, backend=backend)
    contract = RealWorldCleanupContract(
        base_contract,
        perception_mode=RAW_FPV_ONLY_MODE,
        map_mode=MINIMAL_MAP_MODE,
    )

    yaw_offsets = tuple(args.camera_yaw_deg or DEFAULT_CAMERA_YAWS)
    pitch_offsets = tuple(args.camera_pitch_deg or DEFAULT_CAMERA_PITCHES)
    waypoints = list((contract.metric_map().get("inspection_waypoints") or []))
    if args.max_waypoints and args.max_waypoints > 0:
        waypoints = waypoints[: int(args.max_waypoints)]

    labels: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    frames: list[dict[str, Any]] = []
    image_dir = output_run_dir / "robot_views"
    observation_index = 0
    for waypoint in waypoints:
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        nav = contract.navigate_to_waypoint(waypoint_id)
        if not nav.get("ok"):
            frames.append(
                {
                    "waypoint_id": waypoint_id,
                    "capture_status": "navigate_failed",
                    "navigation": _public_navigation_summary(nav),
                }
            )
            continue
        for yaw in yaw_offsets:
            for pitch in pitch_offsets:
                observation_index += 1
                observation_id = f"raw_fpv_{observation_index:03d}"
                label = f"{observation_index:04d}_{observation_id}"
                view = backend.write_robot_views_with_resolution(
                    image_dir,
                    label=label,
                    width=max(1, int(args.render_width)),
                    height=max(1, int(args.render_height)),
                    camera_yaw_offset_deg=float(yaw),
                    camera_pitch_offset_deg=float(pitch),
                )
                frame_id = f"{_run_id_for_path(output_run_dir)}/{observation_id}"
                observation = _public_observation(
                    observation_id=observation_id,
                    waypoint=waypoint,
                    yaw=float(yaw),
                    pitch=float(pitch),
                    view=view,
                    image_artifact=f"robot_views/{label}.fpv.png",
                )
                observations.append(observation)
                frame_labels = _labels_from_view_focuses(
                    backend=backend,
                    frame_id=frame_id,
                    observation_id=observation_id,
                    targets=generated_manifest["targets"],
                    output_dir=image_dir,
                    label_prefix=label,
                    min_object_pixels=max(1, int(args.min_object_pixels)),
                    width=max(1, int(args.render_width)),
                    height=max(1, int(args.render_height)),
                    yaw=float(yaw),
                    pitch=float(pitch),
                )
                labels.extend(frame_labels)
                frames.append(
                    {
                        "frame_id": frame_id,
                        "source_observation_id": observation_id,
                        "waypoint_id": waypoint_id,
                        "camera_yaw_offset_deg": float(yaw),
                        "camera_pitch_offset_deg": float(pitch),
                        "image_artifact": observation["image_artifacts"]["fpv"],
                        "capture_status": "ok",
                        "label_count": len(frame_labels),
                        "labeled_objects": sorted(
                            {str(item.get("object_id") or "") for item in frame_labels}
                        ),
                    }
                )

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": _utc_timestamp(),
        "provenance": {
            "label_source": "private_molmospaces_public_sweep_fpv_segmentation",
            "source_run_dir": str(source_run_dir),
            "scorer_only": True,
            "private_truth_included_in_prompt_inputs": False,
            "public_frame_policy": (
                "generated_exploration_waypoints_plus_camera_offsets_no_target_handles"
            ),
        },
        "source_run": {
            "run_id": _run_id_for_path(source_run_dir),
            "seed": source_state.get("seed"),
            "scene_source": source_state.get("scene_source"),
            "scene_index": source_state.get("scene_index"),
            "generated_mess_count": len(generated_manifest["targets"]),
        },
        "labels": labels,
    }
    manifest_path = output_run_dir / "raw_fpv_private_label_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    observations_path = output_run_dir / "raw_fpv_observations.json"
    observations_path.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_public_sweep_observations_v1",
                "raw_fpv_observations": observations,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    unique_labeled = sorted({str(item.get("object_id") or "") for item in labels})
    target_ids = {str(item.get("object_id") or "") for item in generated_manifest["targets"]}
    missing_targets = sorted(target_ids.difference(unique_labeled))
    status = "success" if not missing_targets and labels else "partial"
    report = {
        "schema": REPORT_SCHEMA,
        "status": status,
        "generated_at": _utc_timestamp(),
        "output_dir": str(output_run_dir),
        "source_run_dir": str(source_run_dir),
        "public_frame_policy": (
            "generated_exploration_waypoints_plus_camera_offsets_no_target_handles"
        ),
        "waypoint_count": len(waypoints),
        "frame_count": len(observations),
        "label_count": len(labels),
        "unique_labeled_object_count": len(unique_labeled),
        "selected_object_count": len(target_ids),
        "missing_private_targets": missing_targets,
        "min_object_pixels": max(1, int(args.min_object_pixels)),
        "camera_yaw_offsets_deg": list(yaw_offsets),
        "camera_pitch_offsets_deg": list(pitch_offsets),
        "privacy": {
            "private_labels_in_prompt_inputs": _contains_any_target_id(observations, target_ids),
            "agent_facing_input_contains_executable_prior_handles": False,
        },
        "artifacts": {
            "observations": str(observations_path),
            "manifest": str(manifest_path),
            "generated_mess_manifest": str(generated_manifest_path),
        },
        "frames": frames,
    }
    (output_run_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _labels_from_view_focuses(
    *,
    backend: MolmoSpacesSubprocessBackend,
    frame_id: str,
    observation_id: str,
    targets: list[dict[str, Any]],
    output_dir: Path,
    label_prefix: str,
    min_object_pixels: int,
    width: int,
    height: int,
    yaw: float,
    pitch: float,
) -> list[dict[str, Any]]:
    labels = []
    for target in targets:
        object_id = str(target.get("object_id") or "")
        if not object_id:
            continue
        result = backend.write_robot_views_with_resolution(
            output_dir,
            label=f"{label_prefix}_{_safe_filename(object_id)}",
            width=width,
            height=height,
            focus_object_id=object_id,
            camera_yaw_offset_deg=yaw,
            camera_pitch_offset_deg=pitch,
        )
        focus = result.get("focus") or {}
        visibility = focus.get("fpv_visibility") or {}
        box = _object_box_from_visibility(visibility)
        pixels = int((box or {}).get("pixels") or 0)
        if box is None or pixels < min_object_pixels:
            continue
        bbox = normalize_box_xywh(box["bbox"], width=width, height=height)
        labels.append(
            {
                "frame_id": frame_id,
                "source_observation_id": observation_id,
                "object_id": object_id,
                "category": str(focus.get("object_category") or target.get("category") or ""),
                "bbox": bbox,
                "coarse_regions": coarse_regions_from_bbox(bbox),
                "surface_hint": surface_hint_from_focus(focus),
                "label_source": "private_molmospaces_public_sweep_fpv_segmentation",
                "private": True,
                "pixel_bbox": list(box["bbox"]),
                "object_pixels": pixels,
            }
        )
    return labels


def _public_observation(
    *,
    observation_id: str,
    waypoint: dict[str, Any],
    yaw: float,
    pitch: float,
    view: dict[str, Any],
    image_artifact: str,
) -> dict[str, Any]:
    return {
        "observation_id": observation_id,
        "waypoint_id": str(waypoint.get("waypoint_id") or ""),
        "room_id": str(waypoint.get("room_id") or "generated_area"),
        "held_object_id": None,
        "perception_mode": RAW_FPV_ONLY_MODE,
        "structured_detections_available": False,
        "camera_offset": {
            "yaw_offset_deg": yaw,
            "pitch_offset_deg": pitch,
        },
        "image_artifacts": {
            "fpv": image_artifact,
            "map": image_artifact.replace(".fpv.png", ".map.png"),
            "chase": image_artifact.replace(".fpv.png", ".chase.png"),
            "verify": image_artifact.replace(".fpv.png", ".verify.png"),
        },
        "robot_view_label": image_artifact.rsplit("/", 1)[-1].removesuffix(".fpv.png"),
        "camera_control_contract": view.get("camera_control_contract")
        if isinstance(view.get("camera_control_contract"), dict)
        else {},
        "artifact_status": "captured",
        "public_contract_note": (
            "Public sweep frame only: no structured movable-object detections, "
            "categories, target labels, or private scoring truth are included."
        ),
    }


def _object_box_from_visibility(visibility: dict[str, Any]) -> dict[str, Any] | None:
    boxes = [
        item
        for item in visibility.get("boxes") or []
        if isinstance(item, dict) and item.get("source") in {"segmentation", "highlight_diff"}
    ]
    if not boxes:
        return None
    return max(boxes, key=lambda item: int(item.get("pixels") or 0))


def _public_navigation_summary(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(response.get("ok")),
        "tool": str(response.get("tool") or "navigate_to_waypoint"),
        "status": str(response.get("status") or ""),
        "failure_reason": str(response.get("failure_reason") or response.get("reason") or ""),
    }


def _contains_any_target_id(payload: Any, target_ids: set[str]) -> bool:
    text = json.dumps(payload, sort_keys=True)
    return any(target_id and target_id in text for target_id in target_ids)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _output_run_dir(output_root: Path, run_id: str) -> Path:
    if run_id:
        return output_root / _safe_filename(run_id)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    return output_root / stamp


def _run_id_for_path(path: Path) -> str:
    parts = [part for part in path.parts[-4:] if part not in {"output", "household"}]
    return _safe_filename("-".join(parts))


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "item"


def _utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _console_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "manifest": (report.get("artifacts") or {}).get("manifest"),
        "observations": (report.get("artifacts") or {}).get("observations"),
        "label_count": report.get("label_count"),
        "frame_count": report.get("frame_count"),
        "unique_labeled_object_count": report.get("unique_labeled_object_count"),
        "missing_private_targets": report.get("missing_private_targets"),
        "report_json": str(Path(str(report.get("output_dir", ""))) / "report.json"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
