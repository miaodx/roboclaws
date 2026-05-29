from __future__ import annotations

import html
import json
import math
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.camera_control import (
    CAMERA_CONTROL_API_NAME,
    CANONICAL_CAMERA_MODEL,
    CANONICAL_POSE_CALIBRATION,
    DEFAULT_SCENE_PROBE_CAMERA_ORBIT,
    DEFAULT_SCENE_PROBE_LENS,
    DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
    MOLMOSPACES_SCENE_FRAME,
    canonical_scene_camera_control_request,
    write_camera_control_request,
)
from roboclaws.molmo_cleanup.isaac_lab_backend import IsaacLabSubprocessBackend
from roboclaws.molmo_cleanup.renderer_comparison import _dimensions_from_shape, _relpath
from roboclaws.molmo_cleanup.subprocess_backend import MolmoSpacesSubprocessBackend

SCENE_CAMERA_COMPARISON_SCHEMA = "molmospaces_isaac_scene_camera_comparison_v1"
MOLMOSPACES_LANE_ID = "molmospaces-mujoco"
ISAAC_LANE_ID = "isaaclab-prepared-usd"
DEFAULT_RENDER_WIDTH = 960
DEFAULT_RENDER_HEIGHT = 640
CANONICAL_POSE_PARITY_THRESHOLD_M = 0.08
CANONICAL_CAMERA_ELEVATION_DEG = 78.0


@dataclass(frozen=True)
class SceneCameraComparisonConfig:
    output_dir: Path
    scene_usd_path: Path
    seed: int = 7
    generated_mess_count: int = 1
    scene_source: str = "procthor-10k-val"
    scene_index: int = 1
    molmospaces_python: Path = Path(".venv/bin/python")
    isaac_python: Path = Path(".venv-isaaclab/bin/python")
    render_width: int = DEFAULT_RENDER_WIDTH
    render_height: int = DEFAULT_RENDER_HEIGHT


def run_scene_camera_comparison(config: SceneCameraComparisonConfig) -> dict[str, Any]:
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema": SCENE_CAMERA_COMPARISON_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "purpose": (
            "Render-only scene identity probe. This does not execute household cleanup, "
            "pick, place, or scoring."
        ),
        "scene": {
            "scene_source": config.scene_source,
            "scene_index": config.scene_index,
            "seed": config.seed,
            "generated_mess_count": config.generated_mess_count,
            "scene_usd_path": str(config.scene_usd_path),
            "render_width": config.render_width,
            "render_height": config.render_height,
        },
        "camera_control": {
            "api_name": CAMERA_CONTROL_API_NAME,
            "camera_model": CANONICAL_CAMERA_MODEL,
            "coordinate_frame": MOLMOSPACES_SCENE_FRAME,
            "lens": dict(DEFAULT_SCENE_PROBE_LENS),
            "lighting_profile": dict(DEFAULT_SCENE_PROBE_LIGHTING_PROFILE),
            "calibration_status": CANONICAL_POSE_CALIBRATION,
            "calibration_note": (
                "One Roboclaws camera-control request carries explicit eye/target/up poses "
                "in the MolmoSpaces scene frame. Backends apply their registered scene-frame "
                "transform internally; the report records fit residuals instead of hiding "
                "camera mismatch behind lane-local orbit overrides."
            ),
            "request_artifact": "camera_control_request.json",
        },
        "frame_mapping_note": (
            "The canonical camera frame is the MolmoSpaces scene frame. The Isaac lane renders "
            "the same explicit eye/target/up request and reports USD-bounds residuals for the "
            "matched anchors. If residuals are high, the artifact is evidence of a scene "
            "geometry/anchor mismatch rather than proof of full backend-swappable parity."
        ),
        "anchors": [],
        "view_specs": {},
        "lanes": {},
        "artifacts": {
            "comparison_manifest": "comparison_manifest.json",
            "report": "report.html",
        },
    }

    molmo = _capture_molmospaces_lane(config)
    manifest["lanes"][MOLMOSPACES_LANE_ID] = molmo
    molmo_state = molmo.pop("_state", {}) if isinstance(molmo, dict) else {}
    anchors = _scene_anchors(molmo_state, limit=4)
    manifest["anchors"] = anchors
    molmo_specs = _molmospaces_view_specs(anchors, molmo_state=molmo_state)
    isaac_specs = _isaac_view_specs(
        anchors,
        scene_usd_path=config.scene_usd_path,
        scene_index=config.scene_index,
    )
    scene_transform = _identity_scene_frame_transform()
    canonical_views = _canonical_camera_control_views(
        anchors,
        molmo_specs=molmo_specs,
        isaac_specs=isaac_specs,
        scene_transform=scene_transform,
    )
    camera_request = canonical_scene_camera_control_request(
        canonical_views,
        width=config.render_width,
        height=config.render_height,
        lens=DEFAULT_SCENE_PROBE_LENS,
        lighting_profile=DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
    )
    camera_request_path = write_camera_control_request(
        output_dir / "camera_control_request.json",
        camera_request,
    )
    manifest["camera_control"]["request_artifact"] = _relpath(camera_request_path, output_dir)
    manifest["view_specs"] = {
        MOLMOSPACES_LANE_ID: molmo_specs,
        ISAAC_LANE_ID: isaac_specs,
    }
    manifest["scene_frame_transform"] = scene_transform
    manifest["canonical_camera_views"] = canonical_views
    manifest["camera_control"]["view_count"] = len(camera_request.get("views") or [])
    manifest["camera_control"]["same_pose_contract"] = True
    if molmo.get("status") == "success" and anchors:
        molmo.update(
            _capture_molmospaces_camera_views(
                config,
                camera_request_path=camera_request_path,
                lane_dir=output_dir / "molmospaces",
            )
        )
    manifest["lanes"][ISAAC_LANE_ID] = _capture_isaac_lane(
        config,
        camera_request_path=camera_request_path,
        lane_dir=output_dir / "isaaclab",
    )
    manifest["scene_frame_transform"] = _scene_frame_transform_from_capture(
        canonical_views=canonical_views,
        isaac_lane=manifest["lanes"][ISAAC_LANE_ID],
    )
    manifest_path = output_dir / "comparison_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_scene_camera_comparison_report(manifest, output_dir=output_dir)
    return manifest


def render_scene_camera_comparison_report(manifest: dict[str, Any], *, output_dir: Path) -> Path:
    report_path = output_dir / "report.html"
    report_path.write_text(_report_html(manifest, output_dir=output_dir), encoding="utf-8")
    return report_path


def comparison_successful(manifest: dict[str, Any]) -> bool:
    lanes = manifest.get("lanes") or {}
    return bool(lanes) and all(
        isinstance(lane, dict) and lane.get("status") == "success" for lane in lanes.values()
    )


def failed_lane_summaries(manifest: dict[str, Any]) -> list[str]:
    summaries = []
    for lane_id, lane in (manifest.get("lanes") or {}).items():
        if not isinstance(lane, dict) or lane.get("status") == "success":
            continue
        failure = lane.get("failure") if isinstance(lane.get("failure"), dict) else {}
        summaries.append(f"{lane_id}: {failure.get('message') or lane.get('status')}")
    return summaries


def _capture_molmospaces_lane(config: SceneCameraComparisonConfig) -> dict[str, Any]:
    lane_dir = config.output_dir / "molmospaces"
    try:
        backend = MolmoSpacesSubprocessBackend(
            run_dir=lane_dir,
            seed=config.seed,
            python_executable=config.molmospaces_python,
            scene_source=config.scene_source,
            scene_index=config.scene_index,
            include_robot=False,
            generated_mess_count=config.generated_mess_count,
        )
        try:
            state = backend._read_state()
            return {
                "status": "success",
                "python_executable": str(config.molmospaces_python),
                "runtime": dict(backend.runtime),
                "scene_xml": backend.scene_xml,
                "requested_generated_mess_count": backend.requested_generated_mess_count,
                "generated_mess_count": backend.generated_mess_count,
                "_state": state,
            }
        finally:
            backend.close()
    except Exception as exc:
        return _lane_failure(config.molmospaces_python, exc)


def _capture_molmospaces_camera_views(
    config: SceneCameraComparisonConfig,
    *,
    camera_request_path: Path,
    lane_dir: Path,
) -> dict[str, Any]:
    try:
        lane_dir.mkdir(parents=True, exist_ok=True)
        backend = MolmoSpacesSubprocessBackend(
            run_dir=lane_dir,
            seed=config.seed,
            python_executable=config.molmospaces_python,
            scene_source=config.scene_source,
            scene_index=config.scene_index,
            include_robot=False,
            generated_mess_count=config.generated_mess_count,
        )
        try:
            result = backend.render_camera_control_request(
                lane_dir / "camera_views",
                request_path=camera_request_path,
            )
        finally:
            backend.close()
        if result.get("ok") is not True:
            raise RuntimeError(f"MolmoSpaces camera view capture failed: {result}")
        return {
            "status": "success",
            "view_variant": result.get("view_variant"),
            "visual_artifact_provenance": result.get("visual_artifact_provenance"),
            "camera_control_api": result.get("camera_control_api"),
            "camera_request_schema": result.get("camera_request_schema"),
            "calibration_status": result.get("calibration_status"),
            "lighting_profile": result.get("lighting_profile") or {},
            "lens": result.get("lens") or {},
            "images": _image_entries(output_dir=config.output_dir, result=result),
            "views": result.get("views") or [],
            "camera_control_request": _relpath(camera_request_path, config.output_dir),
        }
    except Exception as exc:
        return _lane_failure(config.molmospaces_python, exc)


def _capture_isaac_lane(
    config: SceneCameraComparisonConfig,
    *,
    camera_request_path: Path,
    lane_dir: Path,
) -> dict[str, Any]:
    try:
        lane_dir.mkdir(parents=True, exist_ok=True)
        backend = IsaacLabSubprocessBackend(
            run_dir=lane_dir,
            seed=config.seed,
            python_executable=config.isaac_python,
            scene_source=config.scene_source,
            scene_index=config.scene_index,
            include_robot=False,
            generated_mess_count=config.generated_mess_count,
            scene_usd_path=config.scene_usd_path,
            runtime_mode="real",
        )
        result = backend.render_camera_control_request(
            lane_dir / "camera_views",
            request_path=camera_request_path,
        )
        if result.get("ok") is not True:
            raise RuntimeError(f"Isaac camera view capture failed: {result}")
        return {
            "status": "success",
            "python_executable": str(config.isaac_python),
            "runtime": dict(backend.runtime),
            "scene_usd": backend.scene_usd,
            "scene_load": backend.scene_load,
            "scene_index_diagnostics": backend.scene_index_diagnostics,
            "requested_generated_mess_count": backend.requested_generated_mess_count,
            "generated_mess_count": backend.generated_mess_count,
            "view_variant": result.get("view_variant"),
            "visual_artifact_provenance": result.get("visual_artifact_provenance"),
            "camera_control_api": result.get("camera_control_api"),
            "camera_request_schema": result.get("camera_request_schema"),
            "calibration_status": result.get("calibration_status"),
            "lighting_profile": result.get("lighting_profile") or {},
            "lens": result.get("lens") or {},
            "derived_lens": result.get("derived_lens") or {},
            "render_steps": result.get("render_steps"),
            "scene_bounds": result.get("scene_bounds"),
            "images": _image_entries(output_dir=config.output_dir, result=result),
            "views": result.get("views") or [],
            "camera_control_request": _relpath(camera_request_path, config.output_dir),
        }
    except Exception as exc:
        return _lane_failure(config.isaac_python, exc)


def _scene_anchors(state: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    anchors = []
    for item in (state.get("receptacles") or {}).values():
        if not isinstance(item, dict):
            continue
        position = item.get("position")
        if not isinstance(position, list) or len(position) < 3:
            continue
        room_id = str(item.get("room_area") or "")
        room = _room_outline(state, room_id)
        room_center = room.get("center") if isinstance(room.get("center"), list) else None
        anchors.append(
            {
                "anchor_id": str(item.get("receptacle_id") or ""),
                "anchor_kind": "receptacle",
                "category": str(item.get("category") or ""),
                "room_id": room_id,
                "label": str(item.get("name") or item.get("receptacle_id") or ""),
                "molmospaces_position": [
                    float(position[0]),
                    float(position[1]),
                    float(position[2]),
                ],
                "molmospaces_support_top_z": _optional_float(item.get("support_top_z")),
                "room_center_xy": [float(room_center[0]), float(room_center[1])]
                if isinstance(room_center, list) and len(room_center) >= 2
                else None,
            }
        )
    anchors.sort(key=lambda item: (item["room_id"], item["category"], item["anchor_id"]))
    return anchors[:limit]


def _molmospaces_view_specs(
    anchors: list[dict[str, Any]],
    *,
    molmo_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    specs = []
    for index, anchor in enumerate(anchors, start=1):
        position = anchor["molmospaces_position"]
        support_top_z = anchor.get("molmospaces_support_top_z")
        target_z = float(support_top_z) + 0.25 if support_top_z is not None else position[2]
        lookat = [position[0], position[1], max(float(target_z), 0.6)]
        camera_orbit = _anchor_camera_orbit(anchor, state=molmo_state or {})
        specs.append(
            {
                "view_id": f"view_{index:02d}_{_safe_id(anchor['category'])}",
                "label": f"{anchor['room_id']} {anchor['category']} {anchor['anchor_id']}",
                "anchor_id": anchor["anchor_id"],
                "anchor_kind": anchor["anchor_kind"],
                "camera_mode": "anchor_orbit",
                "focus_receptacle_id": anchor["anchor_id"],
                "lookat": lookat,
                "target_source": "molmospaces_metadata_anchor_position",
                "camera_orbit": camera_orbit,
            }
        )
    return specs


def _anchor_camera_orbit(anchor: dict[str, Any], *, state: dict[str, Any]) -> dict[str, float]:
    """Choose a room-interior orbit that keeps the anchor visible in MuJoCo."""

    category = _category_key(anchor.get("category"))
    if category == "sink":
        azimuth = 315.0
    elif category in {"diningtable", "table"}:
        azimuth = 90.0
    elif category == "bed":
        azimuth = _bed_anchor_azimuth(anchor, state=state)
    else:
        azimuth = float(DEFAULT_SCENE_PROBE_CAMERA_ORBIT["azimuth_deg"])
    return {
        "distance_m": float(DEFAULT_SCENE_PROBE_CAMERA_ORBIT["distance_m"]),
        "azimuth_deg": azimuth,
        "elevation_deg": float(DEFAULT_SCENE_PROBE_CAMERA_ORBIT["elevation_deg"]),
    }


def _bed_anchor_azimuth(anchor: dict[str, Any], *, state: dict[str, Any]) -> float:
    room = _room_outline(state, str(anchor.get("room_id") or ""))
    position = anchor.get("molmospaces_position") if isinstance(anchor, dict) else None
    if room and isinstance(position, list) and len(position) >= 2:
        center = room.get("center")
        if isinstance(center, list) and len(center) >= 2:
            dy = float(position[1]) - float(center[1])
            return 90.0 if dy >= 0 else 225.0
    return 90.0


def _room_outline(state: dict[str, Any], room_id: str) -> dict[str, Any]:
    for room in state.get("room_outlines") or []:
        if isinstance(room, dict) and str(room.get("room_id") or "") == room_id:
            return room
    return {}


def _category_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _isaac_lane_camera_orbit(anchor: dict[str, Any]) -> dict[str, float]:
    category = _category_key(anchor.get("category"))
    if category == "bed":
        azimuth = 225.0
    elif category in {"diningtable", "table"}:
        azimuth = 180.0
    elif category == "sink":
        azimuth = 315.0
    else:
        azimuth = float(DEFAULT_SCENE_PROBE_CAMERA_ORBIT["azimuth_deg"])
    return {
        "distance_m": float(DEFAULT_SCENE_PROBE_CAMERA_ORBIT["distance_m"]),
        "azimuth_deg": azimuth,
        "elevation_deg": float(DEFAULT_SCENE_PROBE_CAMERA_ORBIT["elevation_deg"]),
    }


def _isaac_view_specs(
    anchors: list[dict[str, Any]],
    *,
    scene_usd_path: Path,
    scene_index: int,
) -> list[dict[str, Any]]:
    metadata = _load_scene_metadata(scene_usd_path)
    local_scene_index = _load_local_isaac_scene_index(scene_usd_path)
    specs = []
    for index, anchor in enumerate(anchors, start=1):
        raw = metadata.get(anchor["anchor_id"]) or {}
        index_entry = _isaac_scene_index_entry(anchor["anchor_id"], local_scene_index)
        usd_prim_path = (
            str(index_entry.get("usd_prim_path") or "") if isinstance(index_entry, dict) else ""
        )
        support_pose = index_entry.get("support_pose") if isinstance(index_entry, dict) else None
        isaac_support_position = _support_pose_position(support_pose)
        if not usd_prim_path and raw:
            usd_prim_path = f"/val_{scene_index}/Geometry/{anchor['anchor_id']}"
        specs.append(
            {
                "view_id": f"view_{index:02d}_{_safe_id(anchor['category'])}",
                "label": f"{anchor['room_id']} {anchor['category']} {anchor['anchor_id']}",
                "anchor_id": anchor["anchor_id"],
                "anchor_kind": anchor["anchor_kind"],
                "usd_prim_path": usd_prim_path,
                "target_source": (
                    "isaac_scene_index_support_pose"
                    if isaac_support_position
                    else "isaac_worker_usd_prim_world_bounds"
                ),
                "isaac_support_position": isaac_support_position,
                "min_target_z": 0.6,
            }
        )
        anchor["isaac_usd_prim_path"] = usd_prim_path
        if isaac_support_position:
            anchor["isaac_support_position"] = isaac_support_position
            anchor["isaac_target_source"] = "Isaac scene-index support pose"
        else:
            anchor["isaac_target_source"] = "USD prim world bounds resolved in Isaac worker"
    return specs


def _canonical_camera_control_views(
    anchors: list[dict[str, Any]],
    *,
    molmo_specs: list[dict[str, Any]],
    isaac_specs: list[dict[str, Any]],
    scene_transform: dict[str, Any],
) -> list[dict[str, Any]]:
    views = []
    for anchor, molmo_spec, isaac_spec in zip(anchors, molmo_specs, isaac_specs, strict=True):
        target = [float(value) for value in molmo_spec.get("lookat") or []]
        camera_orbit = molmo_spec.get("camera_orbit") or DEFAULT_SCENE_PROBE_CAMERA_ORBIT
        distance = float(
            camera_orbit.get("distance_m", DEFAULT_SCENE_PROBE_CAMERA_ORBIT["distance_m"])
        )
        azimuth = float(
            camera_orbit.get("azimuth_deg", DEFAULT_SCENE_PROBE_CAMERA_ORBIT["azimuth_deg"])
        )
        eye = _eye_from_mujoco_orbit(
            target=target,
            distance=distance,
            azimuth=azimuth,
            elevation=-CANONICAL_CAMERA_ELEVATION_DEG,
        )
        view = {
            "view_id": molmo_spec["view_id"],
            "label": molmo_spec["label"],
            "anchor_id": anchor["anchor_id"],
            "anchor_kind": anchor["anchor_kind"],
            "category": anchor["category"],
            "room_id": anchor["room_id"],
            "camera_mode": "canonical_eye_target",
            "camera_model": CANONICAL_CAMERA_MODEL,
            "coordinate_frame": MOLMOSPACES_SCENE_FRAME,
            "coordinate_convention": MOLMOSPACES_SCENE_FRAME,
            "calibration_status": CANONICAL_POSE_CALIBRATION,
            "eye": eye,
            "target": target,
            "lookat": target,
            "up": [0.0, 0.0, 1.0],
            "camera_basis": "near_topdown_anchor_orbit",
            "backend_transforms": {
                ISAAC_LANE_ID: scene_transform,
            },
            "target_source": {
                MOLMOSPACES_LANE_ID: molmo_spec.get("target_source"),
                ISAAC_LANE_ID: isaac_spec.get("target_source"),
            },
            "lane_targets": {
                MOLMOSPACES_LANE_ID: {
                    "lookat": target,
                    "focus_receptacle_id": molmo_spec.get("focus_receptacle_id"),
                },
                ISAAC_LANE_ID: {
                    "usd_prim_path": isaac_spec.get("usd_prim_path"),
                    "support_position": isaac_spec.get("isaac_support_position"),
                    "min_target_z": isaac_spec.get("min_target_z", 0.6),
                },
            },
            "usd_prim_path": isaac_spec.get("usd_prim_path"),
            "min_target_z": isaac_spec.get("min_target_z", 0.6),
        }
        views.append(view)
    return views


def _camera_control_views(
    anchors: list[dict[str, Any]],
    *,
    molmo_specs: list[dict[str, Any]],
    isaac_specs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    views = []
    for anchor, molmo_spec, isaac_spec in zip(anchors, molmo_specs, isaac_specs, strict=True):
        view = {
            "view_id": molmo_spec["view_id"],
            "label": molmo_spec["label"],
            "anchor_id": anchor["anchor_id"],
            "anchor_kind": anchor["anchor_kind"],
            "category": anchor["category"],
            "room_id": anchor["room_id"],
            "camera_mode": "anchor_orbit",
            "camera_orbit": dict(
                molmo_spec.get("camera_orbit") or DEFAULT_SCENE_PROBE_CAMERA_ORBIT
            ),
            "lane_camera_orbits": {
                MOLMOSPACES_LANE_ID: dict(
                    molmo_spec.get("camera_orbit") or DEFAULT_SCENE_PROBE_CAMERA_ORBIT
                ),
                ISAAC_LANE_ID: _isaac_lane_camera_orbit(anchor),
            },
            "target_source": {
                MOLMOSPACES_LANE_ID: molmo_spec.get("target_source"),
                ISAAC_LANE_ID: isaac_spec.get("target_source"),
            },
            "lane_targets": {
                MOLMOSPACES_LANE_ID: {
                    "lookat": list(molmo_spec.get("lookat") or []),
                    "focus_receptacle_id": molmo_spec.get("focus_receptacle_id"),
                },
                ISAAC_LANE_ID: {
                    "usd_prim_path": isaac_spec.get("usd_prim_path"),
                    "min_target_z": isaac_spec.get("min_target_z", 0.6),
                },
            },
            "lookat": list(molmo_spec.get("lookat") or []),
            "usd_prim_path": isaac_spec.get("usd_prim_path"),
            "min_target_z": isaac_spec.get("min_target_z", 0.6),
        }
        views.append(view)
    return views


def _identity_scene_frame_transform() -> dict[str, Any]:
    return {
        "schema": "molmospaces_to_isaac_scene_transform_v1",
        "source_frame": MOLMOSPACES_SCENE_FRAME,
        "target_frame": "isaac_prepared_usd_world_frame",
        "status": "identity_pending_render_diagnostics",
        "parity_status": "pending_render_diagnostics",
        "pair_count": 0,
        "xy_scale": 1.0,
        "rotation_z_deg": 0.0,
        "translation": [0.0, 0.0, 0.0],
        "residual_threshold_m": CANONICAL_POSE_PARITY_THRESHOLD_M,
        "pairs": [],
    }


def _scene_frame_transform_from_capture(
    *,
    canonical_views: list[dict[str, Any]],
    isaac_lane: dict[str, Any],
) -> dict[str, Any]:
    views = {
        str(item.get("view_id") or ""): item
        for item in isaac_lane.get("views") or []
        if isinstance(item, dict)
    }
    pairs = []
    for request_view in canonical_views:
        view_id = str(request_view.get("view_id") or "")
        captured = views.get(view_id, {})
        target = captured.get("usd_bounds_target")
        source = request_view.get("target")
        if not _is_vec3(source) or not _is_vec3(target):
            continue
        pairs.append(
            {
                "anchor_id": request_view.get("anchor_id"),
                "category": request_view.get("category"),
                "source": [float(value) for value in source[:3]],
                "target": [float(value) for value in target[:3]],
            }
        )
    if not pairs:
        transform = _identity_scene_frame_transform()
        transform["status"] = "missing_render_diagnostics"
        transform["parity_status"] = "not_proven"
        return transform
    # Fit residuals against identity first; the current prepared USD should already
    # share the MolmoSpaces scene frame when camera parity is real.
    residuals = []
    for item in pairs:
        xy_residual = math.hypot(
            float(item["source"][0]) - float(item["target"][0]),
            float(item["source"][1]) - float(item["target"][1]),
        )
        z_residual = abs(float(item["source"][2]) - float(item["target"][2]))
        residuals.append(
            {
                **item,
                "fitted": [float(value) for value in item["source"]],
                "residual_m": _distance_3d(item["source"], item["target"]),
                "xy_residual_m": xy_residual,
                "z_residual_m": z_residual,
            }
        )
    residual_values = [float(item["residual_m"]) for item in residuals]
    xy_residual_values = [float(item["xy_residual_m"]) for item in residuals]
    z_residual_values = [float(item["z_residual_m"]) for item in residuals]
    max_residual = max(residual_values)
    mean_residual = sum(residual_values) / len(residual_values)
    max_xy_residual = max(xy_residual_values)
    mean_xy_residual = sum(xy_residual_values) / len(xy_residual_values)
    max_z_residual = max(z_residual_values)
    mean_z_residual = sum(z_residual_values) / len(z_residual_values)
    return {
        "schema": "molmospaces_to_isaac_scene_transform_v1",
        "source_frame": MOLMOSPACES_SCENE_FRAME,
        "target_frame": "isaac_prepared_usd_world_frame",
        "status": "identity_checked_against_usd_bounds",
        "parity_status": (
            "canonical_pose_fit_within_threshold"
            if max_residual <= CANONICAL_POSE_PARITY_THRESHOLD_M
            else "canonical_pose_fit_residual_high"
        ),
        "pair_count": len(pairs),
        "xy_scale": 1.0,
        "rotation_z_deg": 0.0,
        "translation": [0.0, 0.0, 0.0],
        "residual_threshold_m": CANONICAL_POSE_PARITY_THRESHOLD_M,
        "mean_residual_m": mean_residual,
        "max_residual_m": max_residual,
        "mean_xy_residual_m": mean_xy_residual,
        "max_xy_residual_m": max_xy_residual,
        "mean_z_residual_m": mean_z_residual,
        "max_z_residual_m": max_z_residual,
        "pairs": residuals,
    }


def _support_pose_position(value: Any) -> list[float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return [
            float(value["x"]),
            float(value["y"]),
            float(value.get("z", 0.0)),
        ]
    except (KeyError, TypeError, ValueError):
        return None


def _eye_from_mujoco_orbit(
    *,
    target: list[float],
    distance: float,
    azimuth: float,
    elevation: float,
) -> list[float]:
    azimuth_rad = math.radians(azimuth)
    elevation_rad = math.radians(elevation)
    horizontal = math.cos(elevation_rad) * distance
    return [
        float(target[0]) + math.sin(azimuth_rad) * horizontal,
        float(target[1]) + math.cos(azimuth_rad) * horizontal,
        float(target[2]) - math.sin(elevation_rad) * distance,
    ]


def _canonical_eye_from_room_context(
    anchor: dict[str, Any],
    *,
    target: list[float],
    distance: float,
    azimuth: float,
    elevation: float,
) -> tuple[list[float], str]:
    room_center = anchor.get("room_center_xy")
    if isinstance(room_center, list) and len(room_center) >= 2:
        dx = float(room_center[0]) - float(target[0])
        dy = float(room_center[1]) - float(target[1])
        norm = math.hypot(dx, dy)
        if norm > 1e-6:
            elevation_rad = math.radians(elevation)
            horizontal = math.cos(elevation_rad) * distance
            return (
                [
                    float(target[0]) + dx / norm * horizontal,
                    float(target[1]) + dy / norm * horizontal,
                    float(target[2]) - math.sin(elevation_rad) * distance,
                ],
                "room_center_to_anchor",
            )
    return (
        _eye_from_mujoco_orbit(
            target=target,
            distance=distance,
            azimuth=azimuth,
            elevation=elevation,
        ),
        "anchor_orbit_fallback",
    )


def _distance_3d(left: list[float], right: list[float]) -> float:
    return math.sqrt(
        (float(left[0]) - float(right[0])) ** 2
        + (float(left[1]) - float(right[1])) ** 2
        + (float(left[2]) - float(right[2])) ** 2
    )


def _is_vec3(value: Any) -> bool:
    return isinstance(value, list) and len(value) >= 3


def _load_scene_metadata(scene_usd_path: Path) -> dict[str, dict[str, Any]]:
    metadata_path = scene_usd_path.parent / "scene_metadata.json"
    if not metadata_path.is_file():
        return {}
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    objects = payload.get("objects") if isinstance(payload, dict) else None
    if not isinstance(objects, dict):
        return {}
    return {str(key): dict(value) for key, value in objects.items() if isinstance(value, dict)}


def _load_local_isaac_scene_index(scene_usd_path: Path) -> dict[str, Any]:
    """Load the newest nearby Isaac scene index for USD prim path hints.

    Any support poses in this artifact are deliberately ignored by the camera
    comparison; Isaac targets are resolved from USD prim world bounds instead.
    """

    root = scene_usd_path.parents[2] if len(scene_usd_path.parents) > 2 else Path("output/isaaclab")
    candidates = sorted(
        root.glob("cleanup-smoke/*/isaac_scene_index.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("scene_usd") or "") != str(scene_usd_path):
            continue
        return payload
    return {}


def _isaac_scene_index_entry(anchor_id: str, scene_index: dict[str, Any]) -> dict[str, Any]:
    receptacles = scene_index.get("receptacle_index") if isinstance(scene_index, dict) else None
    if not isinstance(receptacles, dict):
        return {}
    raw = receptacles.get(anchor_id)
    return dict(raw) if isinstance(raw, dict) else {}


def _image_entries(*, output_dir: Path, result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    images = result.get("images") if isinstance(result.get("images"), dict) else {}
    shapes = result.get("shapes") if isinstance(result.get("shapes"), dict) else {}
    entries = {}
    for view_id, raw_path in images.items():
        path = Path(str(raw_path))
        entries[str(view_id)] = {
            "path": _relpath(path, output_dir),
            "dimensions": _dimensions_from_shape(shapes.get(view_id)),
        }
    return entries


def _lane_failure(python_executable: Path, exc: Exception) -> dict[str, Any]:
    return {
        "status": "failed",
        "python_executable": str(python_executable),
        "failure": {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(limit=8),
        },
    }


def _safe_id(value: Any) -> str:
    text = str(value or "scene").lower()
    safe = "".join(ch if ch.isalnum() else "_" for ch in text).strip("_")
    return safe or "scene"


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _report_html(manifest: dict[str, Any], *, output_dir: Path) -> str:
    title = "MolmoSpaces / Isaac Scene Camera Comparison"
    body = "\n".join(
        [
            _summary_section(title, manifest),
            _transform_section(manifest),
            _anchor_section(manifest),
            _runtime_section(manifest),
            _failure_section(manifest),
            _view_sections(manifest, output_dir=output_dir),
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: #eef2f6;
      color: #20242c;
    }}
    main {{ max-width: 1360px; margin: 0 auto; padding: 28px 20px 48px; }}
    h1 {{ margin: 0; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; letter-spacing: 0; }}
    .summary {{
      background: #20242c;
      color: #f8fafc;
      border-radius: 8px;
      padding: 22px;
    }}
    .summary p {{ color: #dbe5ef; max-width: 980px; }}
    .eyebrow {{
      margin: 0 0 6px;
      color: #a7d8cf;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 7px 10px;
      overflow-wrap: anywhere;
    }}
    .summary .badge {{
      background: rgba(255,255,255,.09);
      border-color: rgba(255,255,255,.18);
      color: #e9edf4;
    }}
    .panel {{
      background: #fff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
      padding: 18px;
      margin-top: 18px;
    }}
    .note {{ color: #565f70; margin: 0 0 12px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d9dde6; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      padding: 9px 10px;
      text-align: left;
      border-bottom: 1px solid #e5e8ee;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    th {{ background: #eef1f5; font-weight: 650; }}
    .comparison-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 12px;
    }}
    figure {{
      margin: 0;
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 10px;
    }}
    img {{ width: 100%; height: auto; display: block; }}
    figcaption {{
      display: grid;
      gap: 3px;
      margin-top: 8px;
      color: #565f70;
      font-size: 14px;
    }}
    figcaption strong {{ color: #20242c; }}
    figcaption span {{ color: #647083; font-size: 12px; }}
    .missing {{
      display: grid;
      place-items: center;
      min-height: 220px;
      border: 1px dashed #cbd5e1;
      border-radius: 6px;
      color: #647083;
      background: #f8fafc;
    }}
    @media (max-width: 720px) {{
      main {{ padding: 18px 12px 36px; }}
      .comparison-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body><main>{body}</main></body>
</html>
"""


def _summary_section(title: str, manifest: dict[str, Any]) -> str:
    scene = manifest.get("scene") if isinstance(manifest.get("scene"), dict) else {}
    camera = (
        manifest.get("camera_control") if isinstance(manifest.get("camera_control"), dict) else {}
    )
    lens = camera.get("lens") if isinstance(camera.get("lens"), dict) else {}
    lighting = (
        camera.get("lighting_profile") if isinstance(camera.get("lighting_profile"), dict) else {}
    )
    transform = (
        manifest.get("scene_frame_transform")
        if isinstance(manifest.get("scene_frame_transform"), dict)
        else {}
    )
    return f"""
<section class="summary">
  <p class="eyebrow">Render-only scene identity probe</p>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(str(manifest.get("purpose") or ""))}</p>
  <p>{html.escape(str(manifest.get("frame_mapping_note") or ""))}</p>
  <p>{html.escape(str(camera.get("calibration_note") or ""))}</p>
  <div class="badges">{
        _badges(
            [
                ("scene", f"{scene.get('scene_source')}:{scene.get('scene_index')}"),
                ("seed", scene.get("seed")),
                ("prepared USD", scene.get("scene_usd_path")),
                ("render", f"{scene.get('render_width')} x {scene.get('render_height')}"),
                ("camera API", camera.get("api_name")),
                ("camera model", camera.get("camera_model")),
                ("frame", camera.get("coordinate_frame")),
                ("calibration", camera.get("calibration_status")),
                ("same pose", camera.get("same_pose_contract")),
                ("fit", transform.get("parity_status")),
                ("max residual", _meters_text(transform.get("max_residual_m"))),
                ("FOV", f"{lens.get('vertical_fov_deg')} deg" if lens else ""),
                ("lighting", lighting.get("profile_id") if lighting else ""),
            ]
        )
    }</div>
</section>
"""


def _transform_section(manifest: dict[str, Any]) -> str:
    transform = (
        manifest.get("scene_frame_transform")
        if isinstance(manifest.get("scene_frame_transform"), dict)
        else {}
    )
    if not transform:
        return ""
    rows = []
    for item in transform.get("pairs") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('anchor_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('source')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('target')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('fitted')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('residual_m')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('xy_residual_m')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('z_residual_m')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "Handle",
            "Category",
            "MolmoSpaces anchor",
            "Isaac support pose",
            "Fitted Isaac pose",
            "Residual",
            "XY residual",
            "Z residual",
        )
    )
    note = (
        f"{transform.get('source_frame')} -> {transform.get('target_frame')}; "
        f"status={transform.get('status')}; parity={transform.get('parity_status')}; "
        f"mean={_meters_text(transform.get('mean_residual_m'))}; "
        f"max={_meters_text(transform.get('max_residual_m'))}; "
        f"max_xy={_meters_text(transform.get('max_xy_residual_m'))}; "
        f"max_z={_meters_text(transform.get('max_z_residual_m'))}."
    )
    return f"""
<section class="panel">
  <h2>Scene Frame Transform</h2>
  <p class="note">{html.escape(note)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _anchor_section(manifest: dict[str, Any]) -> str:
    rows = []
    for anchor in manifest.get("anchors") or []:
        if not isinstance(anchor, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(anchor.get('anchor_id', '')))}</td>"
            f"<td>{html.escape(str(anchor.get('category', '')))}</td>"
            f"<td>{html.escape(str(anchor.get('room_id', '')))}</td>"
            f"<td>{html.escape(_vec_text(anchor.get('molmospaces_position')))}</td>"
            f"<td>{html.escape(str(anchor.get('molmospaces_support_top_z') or ''))}</td>"
            f"<td>{html.escape(_vec_text(anchor.get('isaac_support_position')))}</td>"
            f"<td>{html.escape(str(anchor.get('isaac_usd_prim_path', '')))}</td>"
            f"<td>{html.escape(str(anchor.get('isaac_target_source', '')))}</td>"
            "</tr>"
        )
    note = (
        "Anchors are matched by MolmoSpaces metadata handle, not by cleanup action. "
        "MuJoCo targets use metadata anchor/support surfaces; Isaac support poses are "
        "recorded as diagnostics. The canonical camera request itself carries explicit "
        "eye/target/up values, and USD-bounds residuals are measured after rendering."
    )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "Handle",
            "Category",
            "Room",
            "MuJoCo position",
            "MuJoCo support top z",
            "Isaac support pose",
            "Isaac USD prim",
            "Isaac target source",
        )
    )
    return f"""
<section class="panel">
  <h2>Matched Scene Anchors</h2>
  <p class="note">{html.escape(note)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _runtime_section(manifest: dict[str, Any]) -> str:
    rows = []
    for lane_id, lane in (manifest.get("lanes") or {}).items():
        if not isinstance(lane, dict):
            continue
        runtime = lane.get("runtime") if isinstance(lane.get("runtime"), dict) else {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(lane_id))}</td>"
            f"<td>{html.escape(str(lane.get('status', '')))}</td>"
            f"<td>{html.escape(str(lane.get('python_executable', '')))}</td>"
            f"<td>{html.escape(str(runtime.get('python_version', '')))}</td>"
            f"<td>{html.escape(str(_renderer_version(runtime)))}</td>"
            f"<td>{html.escape(str(lane.get('scene_xml') or lane.get('scene_usd') or ''))}</td>"
            f"<td>{html.escape(str(lane.get('visual_artifact_provenance', '')))}</td>"
            f"<td>{html.escape(str(lane.get('view_variant', '')))}</td>"
            f"<td>{html.escape(str(lane.get('calibration_status', '')))}</td>"
            f"<td>{html.escape(str(_lighting_profile_id(lane)))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "Lane",
            "Status",
            "Python",
            "Python version",
            "Renderer version",
            "Scene source",
            "Visual provenance",
            "View variant",
            "Calibration",
            "Lighting",
        )
    )
    return f"""
<section class="panel">
  <h2>Runtime Metadata</h2>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _renderer_version(runtime: dict[str, Any]) -> str:
    return str(runtime.get("mujoco_version") or runtime.get("isaac_lab_version") or "")


def _lighting_profile_id(lane: dict[str, Any]) -> str:
    lighting = (
        lane.get("lighting_profile") if isinstance(lane.get("lighting_profile"), dict) else {}
    )
    return str(lighting.get("profile_id") or "")


def _failure_section(manifest: dict[str, Any]) -> str:
    rows = []
    for lane_id, lane in (manifest.get("lanes") or {}).items():
        if not isinstance(lane, dict) or lane.get("status") == "success":
            continue
        failure = lane.get("failure") if isinstance(lane.get("failure"), dict) else {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(lane_id))}</td>"
            f"<td>{html.escape(str(failure.get('type', '')))}</td>"
            f"<td>{html.escape(str(failure.get('message', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return f"""
<section class="panel">
  <h2>Lane Failures</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Lane</th><th>Error</th><th>Message</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _view_sections(manifest: dict[str, Any], *, output_dir: Path) -> str:
    anchors = [item for item in manifest.get("anchors") or [] if isinstance(item, dict)]
    blocks = []
    for index, anchor in enumerate(anchors, start=1):
        view_id = f"view_{index:02d}_{_safe_id(anchor.get('category'))}"
        room = html.escape(str(anchor.get("room_id") or "scene"))
        category = html.escape(str(anchor.get("category") or "view"))
        anchor_id = html.escape(str(anchor.get("anchor_id") or ""))
        blocks.append(
            f"""
<section class="panel">
  <h2>{room} {category}</h2>
  <p class="note">{anchor_id}</p>
  <div class="comparison-grid">
    {_figure(manifest, MOLMOSPACES_LANE_ID, view_id, output_dir=output_dir)}
    {_figure(manifest, ISAAC_LANE_ID, view_id, output_dir=output_dir)}
  </div>
</section>
"""
        )
    return "".join(blocks)


def _figure(manifest: dict[str, Any], lane_id: str, view_id: str, *, output_dir: Path) -> str:
    lane = (manifest.get("lanes") or {}).get(lane_id)
    if not isinstance(lane, dict):
        return _missing_figure("missing lane", lane_id)
    image = (
        (lane.get("images") or {}).get(view_id) if isinstance(lane.get("images"), dict) else None
    )
    view = _view_payload(lane, view_id)
    if not isinstance(image, dict):
        return _missing_figure(f"missing {view_id}", lane_id)
    path = str(image.get("path") or "")
    missing = "" if (output_dir / path).is_file() else " (missing on disk)"
    detail = _dimension_text(
        image.get("dimensions") if isinstance(image.get("dimensions"), dict) else {}
    )
    alt = f"{lane_id} {view_id}"
    target = view.get("target") or view.get("lookat")
    pose = f"eye={_vec_text(view.get('eye'))} target={_vec_text(target)}"
    backend_pose = _backend_pose_text(view)
    calibration = str(view.get("calibration_status") or lane.get("calibration_status") or "")
    return (
        f'<figure><img src="{html.escape(path, quote=True)}" alt="{html.escape(alt)}">'
        f"<figcaption><strong>{html.escape(lane_id)}</strong>"
        f"<span>{html.escape(detail + missing)}</span>"
        f"<span>{html.escape(pose)}</span>"
        f"<span>{html.escape(backend_pose)}</span>"
        f"<span>{html.escape(calibration)}</span>"
        "</figcaption></figure>"
    )


def _missing_figure(message: str, lane_id: str) -> str:
    return (
        f'<figure><div class="missing">{html.escape(message)}</div>'
        f"<figcaption><strong>{html.escape(lane_id)}</strong></figcaption></figure>"
    )


def _view_payload(lane: dict[str, Any], view_id: str) -> dict[str, Any]:
    for item in lane.get("views") or []:
        if isinstance(item, dict) and str(item.get("view_id")) == view_id:
            return item
    return {}


def _backend_pose_text(view: dict[str, Any]) -> str:
    backend_eye = view.get("backend_eye")
    backend_target = view.get("backend_target")
    if _is_vec3(backend_eye) and _is_vec3(backend_target):
        return f"backend eye={_vec_text(backend_eye)} target={_vec_text(backend_target)}"
    return ""


def _dimension_text(dimensions: dict[str, Any]) -> str:
    width = dimensions.get("width")
    height = dimensions.get("height")
    channels = dimensions.get("channels")
    if not width or not height:
        return "dimensions unavailable"
    suffix = f", {channels} channels" if channels else ""
    return f"{width} x {height}{suffix}"


def _vec_text(value: Any) -> str:
    if not isinstance(value, list) or len(value) < 3:
        return ""
    return "[" + ", ".join(f"{float(item):.3f}" for item in value[:3]) + "]"


def _meters_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        text = f"{float(value):.4f}"
    except (TypeError, ValueError):
        text = str(value)
    return f"{text} m" if text else ""


def _badges(items: list[tuple[str, Any]]) -> str:
    parts = []
    for label, value in items:
        if value is None or value == "":
            continue
        parts.append(
            f'<span class="badge">{html.escape(str(label))}: '
            f"<strong>{html.escape(str(value))}</strong></span>"
        )
    return "".join(parts)


def default_output_dir() -> Path:
    stamp = datetime.now().astimezone().strftime("%m%d_%H%M")
    return Path("output/molmo/scene-camera-comparison") / stamp


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Render the same MolmoSpaces scene anchors through MuJoCo and Isaac."
    )
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    parser.add_argument("--scene-usd-path", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generated-mess-count", type=int, default=1)
    parser.add_argument("--scene-source", default="procthor-10k-val")
    parser.add_argument("--scene-index", type=int, default=1)
    parser.add_argument("--molmospaces-python", type=Path, default=Path(".venv/bin/python"))
    parser.add_argument("--isaac-python", type=Path, default=Path(".venv-isaaclab/bin/python"))
    parser.add_argument("--render-width", type=int, default=DEFAULT_RENDER_WIDTH)
    parser.add_argument("--render-height", type=int, default=DEFAULT_RENDER_HEIGHT)
    args = parser.parse_args(argv)

    if args.scene_usd_path.is_file():
        os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")
    manifest = run_scene_camera_comparison(
        SceneCameraComparisonConfig(
            output_dir=args.output_dir,
            scene_usd_path=args.scene_usd_path,
            seed=args.seed,
            generated_mess_count=args.generated_mess_count,
            scene_source=args.scene_source,
            scene_index=args.scene_index,
            molmospaces_python=args.molmospaces_python,
            isaac_python=args.isaac_python,
            render_width=args.render_width,
            render_height=args.render_height,
        )
    )
    print(f"scene camera comparison manifest: {args.output_dir / 'comparison_manifest.json'}")
    print(f"scene camera comparison report: {args.output_dir / 'report.html'}")
    if comparison_successful(manifest):
        return 0
    print("scene camera comparison failed:", file=sys.stderr)
    for summary in failed_lane_summaries(manifest):
        print(f"  {summary}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
