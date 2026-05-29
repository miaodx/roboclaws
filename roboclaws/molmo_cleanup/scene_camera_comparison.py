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

from PIL import Image, ImageDraw, ImageFont

from roboclaws.molmo_cleanup.camera_control import (
    CAMERA_CONTROL_API_NAME,
    CANONICAL_CAMERA_MODEL,
    CANONICAL_POSE_CALIBRATION,
    DEFAULT_SCENE_PROBE_CAMERA_ORBIT,
    DEFAULT_SCENE_PROBE_COLOR_PROFILE,
    DEFAULT_SCENE_PROBE_LENS,
    DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
    MOLMOSPACES_SCENE_FRAME,
    canonical_scene_camera_control_request,
    normalize_camera_control_request,
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
CANONICAL_CAMERA_POSE_THRESHOLD_M = 0.005
CANONICAL_CAMERA_PROJECTION_THRESHOLD_PX = 0.5
CANONICAL_ROOM_OUTLINE_THRESHOLD_M = 0.005
CANONICAL_CAMERA_ELEVATION_DEG = 78.0
SURFACE_AIM_HEIGHT_ALLOWANCE_M = 0.3
ROOM_CAMERA_HEIGHT_M = 1.45
ROOM_CAMERA_INSET_FRACTION = 0.35
REPO_ROOT = Path(__file__).resolve().parents[2]

OFFICIAL_RENDER_SOURCE_REFERENCES = (
    {
        "evidence_id": "mujoco_housegen_materials",
        "lane": MOLMOSPACES_LANE_ID,
        "path": "vendors/molmospaces/molmo_spaces/housegen/builder.py",
        "line_start": 361,
        "line_end": 399,
        "claim": (
            "MuJoCo scene generation parses AI2-THOR material albedo, specular values, "
            "and diffuse texture paths into MJCF material metadata."
        ),
    },
    {
        "evidence_id": "mujoco_housegen_lights",
        "lane": MOLMOSPACES_LANE_ID,
        "path": "vendors/molmospaces/molmo_spaces/housegen/builder.py",
        "line_start": 455,
        "line_end": 470,
        "claim": (
            "MuJoCo housegen optionally exports house lights, otherwise it creates a "
            "default MJCF light at scene-build time."
        ),
    },
    {
        "evidence_id": "mujoco_asset_texture_material_collection",
        "lane": MOLMOSPACES_LANE_ID,
        "path": "vendors/molmospaces/molmo_spaces/housegen/builder.py",
        "line_start": 1372,
        "line_end": 1452,
        "claim": (
            "MuJoCo asset import copies texture slots and material RGBA into the scene "
            "spec before rendering."
        ),
    },
    {
        "evidence_id": "isaac_preview_surface_material_conversion",
        "lane": ISAAC_LANE_ID,
        "path": (
            "vendors/molmospaces/molmo_spaces_isaac/src/molmo_spaces_isaac/assets/utils/material.py"
        ),
        "line_start": 52,
        "line_end": 112,
        "claim": (
            "Isaac USD conversion maps MJCF materials to USD PreviewSurface materials, "
            "forces opacity to 1.0, maps shininess to roughness, and handles diffuse "
            "textures through USD texture nodes."
        ),
    },
    {
        "evidence_id": "isaac_material_binding_texture_warning",
        "lane": ISAAC_LANE_ID,
        "path": (
            "vendors/molmospaces/molmo_spaces_isaac/src/"
            "molmo_spaces_isaac/assets/house_converter.py"
        ),
        "line_start": 288,
        "line_end": 322,
        "claim": (
            "Isaac material binding warns that textured materials bound to non-Mesh prims "
            "can discard textures at render time."
        ),
    },
    {
        "evidence_id": "isaac_default_lights_and_shadow_flags",
        "lane": ISAAC_LANE_ID,
        "path": (
            "vendors/molmospaces/molmo_spaces_isaac/src/"
            "molmo_spaces_isaac/assets/house_converter.py"
        ),
        "line_start": 325,
        "line_end": 380,
        "claim": (
            "Isaac scene conversion authors default DistantLight/DomeLight and disables "
            "shadow casting on selected wall or ceiling visual prims."
        ),
    },
)


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
            "color_profile": dict(DEFAULT_SCENE_PROBE_COLOR_PROFILE),
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
            "the same explicit eye/target/up request for both room-level and object-anchor "
            "views. The report also records USD-bounds residuals for matched anchors. If "
            "residuals are high, the artifact is evidence of a target-definition or scene "
            "geometry mismatch rather than proof of full backend-swappable visual parity."
        ),
        "official_molmospaces_source": _official_molmospaces_source(),
        "room_camera_views": [],
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
    room_views = _room_camera_control_views(molmo_state)
    manifest["room_camera_views"] = room_views
    molmo_specs = _molmospaces_view_specs(anchors, molmo_state=molmo_state)
    isaac_specs = _isaac_view_specs(
        anchors,
        scene_usd_path=config.scene_usd_path,
        scene_index=config.scene_index,
    )
    scene_transform = _identity_scene_frame_transform()
    anchor_views = _canonical_anchor_camera_control_views(
        anchors,
        molmo_specs=molmo_specs,
        isaac_specs=isaac_specs,
        scene_transform=scene_transform,
    )
    canonical_views = [*room_views, *anchor_views]
    camera_request = canonical_scene_camera_control_request(
        canonical_views,
        width=config.render_width,
        height=config.render_height,
        lens=DEFAULT_SCENE_PROBE_LENS,
        lighting_profile=DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
        color_profile=DEFAULT_SCENE_PROBE_COLOR_PROFILE,
    )
    camera_request_path = write_camera_control_request(
        output_dir / "camera_control_request.json",
        camera_request,
    )
    manifest["camera_control"]["request_artifact"] = _relpath(camera_request_path, output_dir)
    manifest["view_specs"] = {
        "room-level-canonical": room_views,
        MOLMOSPACES_LANE_ID: molmo_specs,
        ISAAC_LANE_ID: isaac_specs,
    }
    manifest["scene_frame_transform"] = scene_transform
    manifest["canonical_camera_views"] = canonical_views
    manifest["camera_control"]["view_count"] = len(camera_request.get("views") or [])
    manifest["camera_control"]["same_pose_contract"] = True
    if molmo.get("status") == "success" and canonical_views:
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
    manifest["camera_pose_contract"] = _camera_pose_contract_from_capture(
        canonical_views=canonical_views,
        molmospaces_lane=molmo,
        isaac_lane=manifest["lanes"][ISAAC_LANE_ID],
    )
    manifest["camera_intrinsics_contract"] = _camera_intrinsics_contract_from_capture(
        requested_lens=camera_request.get("lens"),
        requested_resolution=camera_request.get("render_resolution"),
        molmospaces_lane=molmo,
        isaac_lane=manifest["lanes"][ISAAC_LANE_ID],
    )
    manifest["room_scale_contract"] = _room_scale_contract_from_capture(
        room_views=room_views,
        isaac_lane=manifest["lanes"][ISAAC_LANE_ID],
    )
    manifest["scene_frame_transform"] = _scene_frame_transform_from_capture(
        canonical_views=canonical_views,
        isaac_lane=manifest["lanes"][ISAAC_LANE_ID],
    )
    manifest["projection_diagnostics"] = _projection_diagnostics(manifest)
    manifest["visual_diagnostics"] = _visual_diagnostics(manifest, output_dir=output_dir)
    manifest["render_domain_source_diagnostics"] = _render_domain_source_diagnostics(manifest)
    manifest["render_domain_view_triage"] = _render_domain_view_triage(manifest)
    manifest["backend_swap_geometry_contract"] = _backend_swap_geometry_contract(manifest)
    _write_contact_sheet(manifest, output_dir=output_dir)
    manifest_path = output_dir / "comparison_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_scene_camera_comparison_report(manifest, output_dir=output_dir)
    return manifest


def render_scene_camera_comparison_report(manifest: dict[str, Any], *, output_dir: Path) -> Path:
    _write_contact_sheet(manifest, output_dir=output_dir)
    if not isinstance(manifest.get("projection_diagnostics"), dict):
        manifest["projection_diagnostics"] = _projection_diagnostics(manifest)
    if not isinstance(manifest.get("visual_diagnostics"), dict):
        manifest["visual_diagnostics"] = _visual_diagnostics(manifest, output_dir=output_dir)
    if not isinstance(manifest.get("render_domain_source_diagnostics"), dict):
        manifest["render_domain_source_diagnostics"] = _render_domain_source_diagnostics(manifest)
    if not isinstance(manifest.get("render_domain_view_triage"), dict):
        manifest["render_domain_view_triage"] = _render_domain_view_triage(manifest)
    if not isinstance(manifest.get("backend_swap_geometry_contract"), dict):
        manifest["backend_swap_geometry_contract"] = _backend_swap_geometry_contract(manifest)
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


def _official_molmospaces_source() -> dict[str, Any]:
    try:
        from importlib import metadata

        distribution = metadata.distribution("molmo-spaces")
        direct_url_text = distribution.read_text("direct_url.json")
        payload = json.loads(direct_url_text) if direct_url_text else {}
    except (metadata.PackageNotFoundError, OSError, json.JSONDecodeError, KeyError):
        return {
            "package": "molmo-spaces",
            "status": "not_installed",
            "expected_source": "https://github.com/allenai/molmospaces",
        }
    vcs_info = payload.get("vcs_info") if isinstance(payload, dict) else {}
    return {
        "package": "molmo-spaces",
        "status": "installed",
        "url": str(payload.get("url") or ""),
        "vcs": str(vcs_info.get("vcs") or "") if isinstance(vcs_info, dict) else "",
        "commit_id": str(vcs_info.get("commit_id") or "") if isinstance(vcs_info, dict) else "",
        "requested_revision": str(vcs_info.get("requested_revision") or "")
        if isinstance(vcs_info, dict)
        else "",
    }


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
            "lighting_diagnostics": result.get("lighting_diagnostics") or {},
            "color_profile": result.get("color_profile") or {},
            "color_management": result.get("color_management") or {},
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
            "lighting_diagnostics": result.get("lighting_diagnostics") or {},
            "color_profile": result.get("color_profile") or {},
            "color_management": result.get("color_management") or {},
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
                    "isaac_worker_usd_prim_world_bounds_diagnostic"
                    if usd_prim_path
                    else "missing_isaac_usd_prim_path"
                ),
                "isaac_support_position": isaac_support_position,
                "min_target_z": 0.6,
            }
        )
        anchor["isaac_usd_prim_path"] = usd_prim_path
        if isaac_support_position:
            anchor["isaac_support_position"] = isaac_support_position
            anchor["isaac_target_source"] = (
                "Canonical explicit target; Isaac support pose recorded as navigation metadata"
            )
        else:
            anchor["isaac_target_source"] = (
                "Canonical explicit target; USD prim bounds resolved in Isaac worker"
            )
    return specs


def _room_camera_control_views(state: dict[str, Any]) -> list[dict[str, Any]]:
    views = []
    rooms = [room for room in (state.get("room_outlines") or []) if isinstance(room, dict)]
    rooms.sort(key=lambda item: str(item.get("room_id") or ""))
    for index, room in enumerate(rooms, start=1):
        center = room.get("center")
        half_extents = room.get("half_extents")
        if not (
            isinstance(center, list)
            and len(center) >= 2
            and isinstance(half_extents, list)
            and len(half_extents) >= 2
        ):
            continue
        room_id = str(room.get("room_id") or f"room_{index}")
        hx = max(float(half_extents[0]), 0.5)
        hy = max(float(half_extents[1]), 0.5)
        target = [float(center[0]), float(center[1]), ROOM_CAMERA_HEIGHT_M]
        eye = [
            float(center[0]) - hx * ROOM_CAMERA_INSET_FRACTION,
            float(center[1]) - hy * ROOM_CAMERA_INSET_FRACTION,
            ROOM_CAMERA_HEIGHT_M,
        ]
        views.append(
            {
                "view_id": f"room_{index:02d}_{_safe_id(room_id)}",
                "label": f"{room.get('label') or room_id} canonical room view",
                "anchor_id": room_id,
                "anchor_kind": "room",
                "category": "Room",
                "room_id": room_id,
                "camera_mode": "canonical_eye_target",
                "camera_model": CANONICAL_CAMERA_MODEL,
                "coordinate_frame": MOLMOSPACES_SCENE_FRAME,
                "coordinate_convention": MOLMOSPACES_SCENE_FRAME,
                "calibration_status": CANONICAL_POSE_CALIBRATION,
                "eye": eye,
                "target": target,
                "lookat": target,
                "up": [0.0, 0.0, 1.0],
                "camera_basis": "room_center_inset_eye_target",
                "target_source": {
                    MOLMOSPACES_LANE_ID: "molmospaces_room_outline_center",
                    ISAAC_LANE_ID: "canonical_explicit_room_target_from_molmospaces_scene_frame",
                },
                "lane_targets": {
                    MOLMOSPACES_LANE_ID: {"lookat": target, "room_id": room_id},
                    ISAAC_LANE_ID: {"room_id": room_id},
                },
                "room_outline": {
                    "center": [float(center[0]), float(center[1])],
                    "half_extents": [hx, hy],
                    "provenance": str(room.get("provenance") or ""),
                },
            }
        )
    return views


def _canonical_anchor_camera_control_views(
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
                ISAAC_LANE_ID: "canonical_explicit_target_from_molmospaces_scene_frame",
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


_canonical_camera_control_views = _canonical_anchor_camera_control_views


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
        bounds = captured.get("usd_bounds") if isinstance(captured.get("usd_bounds"), dict) else {}
        source = request_view.get("target")
        if not _is_vec3(source) or not _is_vec3(target):
            continue
        bounds_distance = _distance_to_axis_aligned_bounds(source, bounds)
        inside_xy = _point_inside_xy_bounds(source, bounds)
        inside_xyz = _point_inside_xyz_bounds(source, bounds)
        surface_aim_distance = _surface_aim_distance_to_bounds(
            source,
            bounds,
            allowance_m=SURFACE_AIM_HEIGHT_ALLOWANCE_M,
        )
        pairs.append(
            {
                "anchor_id": request_view.get("anchor_id"),
                "category": request_view.get("category"),
                "source": [float(value) for value in source[:3]],
                "target": [float(value) for value in target[:3]],
                "usd_bounds_min": _bounds_vec(bounds, "min"),
                "usd_bounds_max": _bounds_vec(bounds, "max"),
                "usd_bounds_center": _bounds_vec(bounds, "center"),
                "distance_to_usd_bounds_m": bounds_distance,
                "surface_aim_distance_to_usd_bounds_m": surface_aim_distance,
                "target_inside_usd_xy_bounds": inside_xy,
                "target_inside_usd_xyz_bounds": inside_xyz,
            }
        )
    if not pairs:
        transform = _identity_scene_frame_transform()
        transform["status"] = "missing_render_diagnostics"
        transform["parity_status"] = "not_proven"
        transform["diagnostic_kind"] = "camera_target_vs_isaac_usd_bounds"
        transform["interpretation"] = (
            "No Isaac USD-bounds diagnostics were captured; this does not prove or disprove "
            "camera pose parity."
        )
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
    bounds_distance_values = [
        float(item["distance_to_usd_bounds_m"])
        for item in residuals
        if item.get("distance_to_usd_bounds_m") is not None
    ]
    surface_aim_distance_values = [
        float(item["surface_aim_distance_to_usd_bounds_m"])
        for item in residuals
        if item.get("surface_aim_distance_to_usd_bounds_m") is not None
    ]
    xy_inside_count = sum(1 for item in residuals if item.get("target_inside_usd_xy_bounds"))
    xyz_inside_count = sum(1 for item in residuals if item.get("target_inside_usd_xyz_bounds"))
    max_residual = max(residual_values)
    mean_residual = sum(residual_values) / len(residual_values)
    max_xy_residual = max(xy_residual_values)
    mean_xy_residual = sum(xy_residual_values) / len(xy_residual_values)
    max_z_residual = max(z_residual_values)
    mean_z_residual = sum(z_residual_values) / len(z_residual_values)
    max_bounds_distance = max(bounds_distance_values) if bounds_distance_values else None
    mean_bounds_distance = (
        sum(bounds_distance_values) / len(bounds_distance_values)
        if bounds_distance_values
        else None
    )
    max_surface_aim_distance = (
        max(surface_aim_distance_values) if surface_aim_distance_values else None
    )
    mean_surface_aim_distance = (
        sum(surface_aim_distance_values) / len(surface_aim_distance_values)
        if surface_aim_distance_values
        else None
    )
    target_residual_status = (
        "target_inside_or_near_usd_bounds_with_surface_aim_allowance"
        if max_surface_aim_distance is not None
        and max_surface_aim_distance <= CANONICAL_POSE_PARITY_THRESHOLD_M
        else "target_inside_or_near_usd_bounds"
        if max_bounds_distance is not None
        and max_bounds_distance <= CANONICAL_POSE_PARITY_THRESHOLD_M
        else "target_matches_usd_bounds_center_within_threshold"
        if max_residual <= CANONICAL_POSE_PARITY_THRESHOLD_M
        else "target_definition_residual_high"
    )
    return {
        "schema": "molmospaces_to_isaac_scene_transform_v1",
        "source_frame": MOLMOSPACES_SCENE_FRAME,
        "target_frame": "isaac_prepared_usd_world_frame",
        "diagnostic_kind": "camera_target_vs_isaac_usd_bounds",
        "status": "identity_checked_against_usd_bounds",
        "parity_status": target_residual_status,
        "target_residual_status": target_residual_status,
        "interpretation": (
            "This diagnostic compares the requested canonical camera target with the matched "
            "Isaac USD prim bounds. Distance-to-bounds is the primary geometry check because "
            "large receptacles often use a surface aim point, not the object bounding-box "
            "center. Center residuals are retained as context and are not backend camera-pose "
            "residuals."
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
        "mean_distance_to_usd_bounds_m": mean_bounds_distance,
        "max_distance_to_usd_bounds_m": max_bounds_distance,
        "mean_surface_aim_distance_to_usd_bounds_m": mean_surface_aim_distance,
        "max_surface_aim_distance_to_usd_bounds_m": max_surface_aim_distance,
        "surface_aim_height_allowance_m": SURFACE_AIM_HEIGHT_ALLOWANCE_M,
        "target_inside_usd_xy_bounds_count": xy_inside_count,
        "target_inside_usd_xyz_bounds_count": xyz_inside_count,
        "pairs": residuals,
    }


def _camera_pose_contract_from_capture(
    *,
    canonical_views: list[dict[str, Any]],
    molmospaces_lane: dict[str, Any],
    isaac_lane: dict[str, Any],
) -> dict[str, Any]:
    request_views = {
        str(item.get("view_id") or ""): item for item in canonical_views if isinstance(item, dict)
    }
    molmo_views = _views_by_id(molmospaces_lane)
    isaac_views = _views_by_id(isaac_lane)
    pairs: list[dict[str, Any]] = []
    for view_id, request_view in request_views.items():
        requested_eye = request_view.get("eye")
        requested_target = request_view.get("target") or request_view.get("lookat")
        molmo_view = molmo_views.get(view_id, {})
        isaac_view = isaac_views.get(view_id, {})
        molmo_eye = _backend_vec(molmo_view, "eye")
        molmo_target = _backend_vec(molmo_view, "target")
        isaac_eye = _backend_vec(isaac_view, "eye")
        isaac_target = _backend_vec(isaac_view, "target")
        if not all(
            _is_vec3(value)
            for value in (
                requested_eye,
                requested_target,
                molmo_eye,
                molmo_target,
                isaac_eye,
                isaac_target,
            )
        ):
            continue
        pairs.append(
            {
                "view_id": view_id,
                "anchor_id": request_view.get("anchor_id"),
                "category": request_view.get("category"),
                "requested_eye": [float(value) for value in requested_eye[:3]],
                "requested_target": [float(value) for value in requested_target[:3]],
                "molmospaces_backend_eye": [float(value) for value in molmo_eye[:3]],
                "molmospaces_backend_target": [float(value) for value in molmo_target[:3]],
                "isaac_backend_eye": [float(value) for value in isaac_eye[:3]],
                "isaac_backend_target": [float(value) for value in isaac_target[:3]],
                "molmospaces_request_eye_residual_m": _distance_3d(requested_eye, molmo_eye),
                "molmospaces_request_target_residual_m": _distance_3d(
                    requested_target, molmo_target
                ),
                "isaac_request_eye_residual_m": _distance_3d(requested_eye, isaac_eye),
                "isaac_request_target_residual_m": _distance_3d(requested_target, isaac_target),
                "backend_eye_delta_m": _distance_3d(molmo_eye, isaac_eye),
                "backend_target_delta_m": _distance_3d(molmo_target, isaac_target),
            }
        )
    if not pairs:
        return {
            "schema": "canonical_camera_pose_contract_v1",
            "camera_model": CANONICAL_CAMERA_MODEL,
            "coordinate_frame": MOLMOSPACES_SCENE_FRAME,
            "status": "missing_pose_diagnostics",
            "pair_count": 0,
            "pose_threshold_m": CANONICAL_CAMERA_POSE_THRESHOLD_M,
            "interpretation": "No matched backend eye/target diagnostics were captured.",
            "pairs": [],
        }
    residual_keys = (
        "molmospaces_request_eye_residual_m",
        "molmospaces_request_target_residual_m",
        "isaac_request_eye_residual_m",
        "isaac_request_target_residual_m",
        "backend_eye_delta_m",
        "backend_target_delta_m",
    )
    maxima = {f"max_{key}": max(float(item[key]) for item in pairs) for key in residual_keys}
    max_pose_delta = max(maxima.values())
    status = (
        "same_backend_pose_within_threshold"
        if max_pose_delta <= CANONICAL_CAMERA_POSE_THRESHOLD_M
        else "backend_camera_pose_mismatch"
    )
    return {
        "schema": "canonical_camera_pose_contract_v1",
        "camera_model": CANONICAL_CAMERA_MODEL,
        "coordinate_frame": MOLMOSPACES_SCENE_FRAME,
        "status": status,
        "pair_count": len(pairs),
        "pose_threshold_m": CANONICAL_CAMERA_POSE_THRESHOLD_M,
        "max_pose_delta_m": max_pose_delta,
        **maxima,
        "interpretation": (
            "This checks the requested eye/target against the eye/target each backend "
            "reported after applying the Roboclaws camera-control request."
        ),
        "pairs": pairs,
    }


def _camera_intrinsics_contract_from_capture(
    *,
    requested_lens: Any,
    requested_resolution: Any,
    molmospaces_lane: dict[str, Any],
    isaac_lane: dict[str, Any],
) -> dict[str, Any]:
    lens = requested_lens if isinstance(requested_lens, dict) else {}
    resolution = requested_resolution if isinstance(requested_resolution, dict) else {}
    width = _optional_float(resolution.get("width"))
    height = _optional_float(resolution.get("height"))
    requested_vertical_fov = _optional_float(lens.get("vertical_fov_deg"))
    requested_focal = _optional_float(lens.get("focal_length_mm"))
    requested_horizontal_aperture = _optional_float(lens.get("horizontal_aperture_mm"))
    derived_horizontal_aperture = None
    derived_horizontal_fov = None
    if (
        requested_vertical_fov is not None
        and requested_focal is not None
        and width is not None
        and height is not None
        and height > 0
    ):
        vertical_aperture = (
            2.0 * requested_focal * math.tan(math.radians(requested_vertical_fov) / 2.0)
        )
        derived_horizontal_aperture = vertical_aperture * width / height
        derived_horizontal_fov = math.degrees(
            2.0 * math.atan(derived_horizontal_aperture / (2.0 * requested_focal))
        )
    aperture_delta = None
    if requested_horizontal_aperture is not None and derived_horizontal_aperture is not None:
        aperture_delta = abs(requested_horizontal_aperture - derived_horizontal_aperture)
    precedence = (
        "vertical_fov_deg"
        if requested_vertical_fov is not None
        else "horizontal_aperture_mm"
        if requested_horizontal_aperture is not None
        else "backend_default"
    )
    status = "intrinsics_consistent"
    if aperture_delta is not None and aperture_delta > 0.001:
        status = "vertical_fov_overrides_horizontal_aperture"
    return {
        "schema": "canonical_camera_intrinsics_contract_v1",
        "status": status,
        "camera_model": CANONICAL_CAMERA_MODEL,
        "resolution": {
            "width": int(width) if width is not None else None,
            "height": int(height) if height is not None else None,
        },
        "requested_lens": dict(lens),
        "molmospaces_lens": dict(molmospaces_lane.get("lens") or {}),
        "isaac_lens": dict(isaac_lane.get("lens") or {}),
        "isaac_derived_lens": dict(isaac_lane.get("derived_lens") or {}),
        "intrinsics_precedence": precedence,
        "derived_from_vertical_fov": {
            "horizontal_aperture_mm": derived_horizontal_aperture,
            "horizontal_fov_deg": derived_horizontal_fov,
        },
        "requested_vs_derived_horizontal_aperture_delta_mm": aperture_delta,
        "interpretation": (
            "The scene probe treats vertical_fov_deg as the canonical lens input. "
            "Isaac derives horizontal aperture from vertical FOV and aspect ratio; "
            "MuJoCo applies the same vertical FOV to its free camera."
        ),
    }


def _room_scale_contract_from_capture(
    *,
    room_views: list[dict[str, Any]],
    isaac_lane: dict[str, Any],
) -> dict[str, Any]:
    rooms = []
    for view in room_views:
        if not isinstance(view, dict):
            continue
        outline = view.get("room_outline") if isinstance(view.get("room_outline"), dict) else {}
        half_extents = outline.get("half_extents")
        center = outline.get("center")
        if not (
            isinstance(half_extents, list)
            and len(half_extents) >= 2
            and isinstance(center, list)
            and len(center) >= 2
        ):
            continue
        size = [float(half_extents[0]) * 2.0, float(half_extents[1]) * 2.0]
        rooms.append(
            {
                "view_id": view.get("view_id"),
                "room_id": view.get("room_id"),
                "center": [float(center[0]), float(center[1])],
                "size": size,
                "half_extents": [float(half_extents[0]), float(half_extents[1])],
                "provenance": str(outline.get("provenance") or ""),
            }
        )
    isaac_room_outlines = _isaac_room_outlines_by_id(isaac_lane)
    outline_pairs = []
    for room in rooms:
        room_id = str(room.get("room_id") or "")
        isaac_outline = isaac_room_outlines.get(room_id)
        if not isaac_outline:
            continue
        isaac_center = isaac_outline.get("center")
        isaac_half_extents = isaac_outline.get("half_extents")
        if not (
            isinstance(isaac_center, list)
            and len(isaac_center) >= 2
            and isinstance(isaac_half_extents, list)
            and len(isaac_half_extents) >= 2
        ):
            continue
        isaac_size = [float(isaac_half_extents[0]) * 2.0, float(isaac_half_extents[1]) * 2.0]
        center_delta = _distance_xy(room["center"], isaac_center)
        size_delta = _distance_xy(room["size"], isaac_size)
        half_extent_delta = _distance_xy(room["half_extents"], isaac_half_extents)
        outline_pairs.append(
            {
                "room_id": room_id,
                "molmospaces_center": list(room["center"]),
                "isaac_center": [float(isaac_center[0]), float(isaac_center[1])],
                "center_delta_m": center_delta,
                "molmospaces_size": list(room["size"]),
                "isaac_size": isaac_size,
                "size_delta_m": size_delta,
                "molmospaces_half_extents": list(room["half_extents"]),
                "isaac_half_extents": [
                    float(isaac_half_extents[0]),
                    float(isaac_half_extents[1]),
                ],
                "half_extent_delta_m": half_extent_delta,
                "molmospaces_provenance": str(room.get("provenance") or ""),
                "isaac_provenance": str(isaac_outline.get("provenance") or ""),
                "isaac_usd_prim_path": str(isaac_outline.get("usd_prim_path") or ""),
            }
        )
    max_center_delta = (
        max(float(item["center_delta_m"]) for item in outline_pairs) if outline_pairs else None
    )
    max_size_delta = (
        max(float(item["size_delta_m"]) for item in outline_pairs) if outline_pairs else None
    )
    max_half_extent_delta = (
        max(float(item["half_extent_delta_m"]) for item in outline_pairs) if outline_pairs else None
    )
    scene_bounds = (
        isaac_lane.get("scene_bounds") if isinstance(isaac_lane.get("scene_bounds"), dict) else {}
    )
    scene_size = scene_bounds.get("size") if isinstance(scene_bounds.get("size"), list) else []
    status = "room_outline_mesh_bounds"
    max_room_to_scene_width_ratio = None
    max_room_to_scene_depth_ratio = None
    if len(scene_size) >= 2 and rooms:
        scene_width = max(float(scene_size[0]), 1e-6)
        scene_depth = max(float(scene_size[1]), 1e-6)
        max_room_to_scene_width_ratio = max(float(room["size"][0]) / scene_width for room in rooms)
        max_room_to_scene_depth_ratio = max(float(room["size"][1]) / scene_depth for room in rooms)
        if max_room_to_scene_width_ratio > 1.05 or max_room_to_scene_depth_ratio > 1.05:
            status = "room_outline_exceeds_isaac_scene_bounds"
    if not rooms:
        status = "missing_room_outline_diagnostics"
    elif not outline_pairs:
        status = "missing_isaac_room_outline_pairs"
    elif (
        status == "room_outline_mesh_bounds"
        and max_center_delta is not None
        and max_size_delta is not None
        and max_half_extent_delta is not None
    ):
        if max(max_center_delta, max_size_delta, max_half_extent_delta) <= (
            CANONICAL_ROOM_OUTLINE_THRESHOLD_M
        ):
            status = "same_room_outlines_within_threshold"
        else:
            status = "room_outline_mismatch"
    return {
        "schema": "room_scale_contract_v1",
        "status": status,
        "room_count": len(rooms),
        "matched_room_outline_count": len(outline_pairs),
        "room_outline_source": "molmospaces_room_outlines",
        "isaac_room_outline_source": "isaac_scene_index_diagnostics.room_outlines",
        "isaac_scene_bounds": dict(scene_bounds),
        "max_room_to_scene_width_ratio": max_room_to_scene_width_ratio,
        "max_room_to_scene_depth_ratio": max_room_to_scene_depth_ratio,
        "room_outline_threshold_m": CANONICAL_ROOM_OUTLINE_THRESHOLD_M,
        "max_room_outline_center_delta_m": max_center_delta,
        "max_room_outline_size_delta_m": max_size_delta,
        "max_room_outline_half_extent_delta_m": max_half_extent_delta,
        "interpretation": (
            "Room-level camera poses are derived from MolmoSpaces room outlines. "
            "Those outlines must match Isaac USD room mesh world bounds room-by-room; "
            "otherwise same-pose backend comparisons can start from a wrong room scale."
        ),
        "rooms": rooms,
        "room_outline_pairs": outline_pairs,
    }


def _isaac_room_outlines_by_id(isaac_lane: dict[str, Any]) -> dict[str, dict[str, Any]]:
    diagnostics = (
        isaac_lane.get("scene_index_diagnostics")
        if isinstance(isaac_lane.get("scene_index_diagnostics"), dict)
        else {}
    )
    outlines = diagnostics.get("room_outlines") if isinstance(diagnostics, dict) else []
    result: dict[str, dict[str, Any]] = {}
    for item in outlines or []:
        if not isinstance(item, dict):
            continue
        room_id = str(item.get("room_id") or "")
        if room_id:
            result[room_id] = item
    return result


def _projection_diagnostics(manifest: dict[str, Any]) -> dict[str, Any]:
    pose_contract = (
        manifest.get("camera_pose_contract")
        if isinstance(manifest.get("camera_pose_contract"), dict)
        else {}
    )
    intrinsics = (
        manifest.get("camera_intrinsics_contract")
        if isinstance(manifest.get("camera_intrinsics_contract"), dict)
        else {}
    )
    resolution = (
        intrinsics.get("resolution") if isinstance(intrinsics.get("resolution"), dict) else {}
    )
    width = _optional_float(resolution.get("width"))
    height = _optional_float(resolution.get("height"))
    vertical_fov = _projection_vertical_fov(intrinsics)
    if width is None or height is None or vertical_fov is None:
        return {
            "schema": "canonical_camera_projection_diagnostics_v1",
            "status": "missing_intrinsics",
            "projection_threshold_px": CANONICAL_CAMERA_PROJECTION_THRESHOLD_PX,
            "pair_count": 0,
            "pairs": [],
        }
    pose_pairs = [item for item in pose_contract.get("pairs") or [] if isinstance(item, dict)]
    canonical_views = {
        str(item.get("view_id") or ""): item
        for item in manifest.get("canonical_camera_views") or []
        if isinstance(item, dict)
    }
    isaac_views = _views_by_id(
        (manifest.get("lanes") or {}).get(ISAAC_LANE_ID)
        if isinstance((manifest.get("lanes") or {}).get(ISAAC_LANE_ID), dict)
        else {}
    )
    pairs: list[dict[str, Any]] = []
    for item in pose_pairs:
        view_id = str(item.get("view_id") or "")
        sample_points = _projection_sample_points(
            canonical_views.get(view_id, {}), isaac_views.get(view_id, {})
        )
        point_projections = []
        for point in sample_points:
            world = point.get("world")
            if not _is_vec3(world):
                continue
            molmo_pixel = _project_world_point(
                world,
                eye=item.get("molmospaces_backend_eye"),
                target=item.get("molmospaces_backend_target"),
                width=width,
                height=height,
                vertical_fov_deg=vertical_fov,
            )
            isaac_pixel = _project_world_point(
                world,
                eye=item.get("isaac_backend_eye"),
                target=item.get("isaac_backend_target"),
                width=width,
                height=height,
                vertical_fov_deg=vertical_fov,
            )
            if molmo_pixel is None or isaac_pixel is None:
                continue
            delta_px = math.hypot(
                float(molmo_pixel["pixel"][0]) - float(isaac_pixel["pixel"][0]),
                float(molmo_pixel["pixel"][1]) - float(isaac_pixel["pixel"][1]),
            )
            point_projections.append(
                {
                    "label": point.get("label"),
                    "world": [float(value) for value in world[:3]],
                    "molmospaces_pixel": molmo_pixel["pixel"],
                    "isaac_pixel": isaac_pixel["pixel"],
                    "pixel_delta": delta_px,
                    "depth_m": molmo_pixel["depth_m"],
                    "inside_frame": bool(
                        molmo_pixel["inside_frame"] and isaac_pixel["inside_frame"]
                    ),
                }
            )
        if point_projections:
            max_delta = max(float(point["pixel_delta"]) for point in point_projections)
            pairs.append(
                {
                    "view_id": view_id,
                    "anchor_id": item.get("anchor_id"),
                    "category": item.get("category"),
                    "point_count": len(point_projections),
                    "max_pixel_delta": max_delta,
                    "all_points_inside_frame": all(
                        bool(point["inside_frame"]) for point in point_projections
                    ),
                    "points": point_projections,
                }
            )
    max_pixel_delta = max(float(item["max_pixel_delta"]) for item in pairs) if pairs else None
    status = (
        "same_projected_geometry_within_threshold"
        if max_pixel_delta is not None
        and max_pixel_delta <= CANONICAL_CAMERA_PROJECTION_THRESHOLD_PX
        else "missing_projection_pairs"
        if max_pixel_delta is None
        else "projected_geometry_mismatch"
    )
    return {
        "schema": "canonical_camera_projection_diagnostics_v1",
        "status": status,
        "interpretation": (
            "Projects the same canonical 3D sample points through the backend-reported "
            "eye/target pose and shared vertical FOV. When this passes, apparent framing "
            "differences are not explained by camera position, target, FOV, or room scale."
        ),
        "projection_threshold_px": CANONICAL_CAMERA_PROJECTION_THRESHOLD_PX,
        "resolution": {"width": int(width), "height": int(height)},
        "vertical_fov_deg": vertical_fov,
        "pair_count": len(pairs),
        "max_pixel_delta": max_pixel_delta,
        "pairs": pairs,
    }


def _projection_vertical_fov(intrinsics: dict[str, Any]) -> float | None:
    requested = (
        intrinsics.get("requested_lens")
        if isinstance(intrinsics.get("requested_lens"), dict)
        else {}
    )
    molmo = (
        intrinsics.get("molmospaces_lens")
        if isinstance(intrinsics.get("molmospaces_lens"), dict)
        else {}
    )
    isaac = intrinsics.get("isaac_lens") if isinstance(intrinsics.get("isaac_lens"), dict) else {}
    return (
        _optional_float(requested.get("vertical_fov_deg"))
        or _optional_float(molmo.get("vertical_fov_deg"))
        or _optional_float(isaac.get("vertical_fov_deg"))
    )


def _projection_sample_points(
    request_view: dict[str, Any],
    isaac_view: dict[str, Any],
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    target = request_view.get("target") or request_view.get("lookat") or isaac_view.get("target")
    if _is_vec3(target):
        points.append({"label": "camera_target", "world": [float(value) for value in target[:3]]})
    room_outline = (
        request_view.get("room_outline")
        if isinstance(request_view.get("room_outline"), dict)
        else {}
    )
    center = room_outline.get("center")
    half_extents = room_outline.get("half_extents")
    if (
        isinstance(center, list)
        and len(center) >= 2
        and isinstance(half_extents, list)
        and len(half_extents) >= 2
    ):
        z = float(target[2]) if _is_vec3(target) else ROOM_CAMERA_HEIGHT_M
        cx = float(center[0])
        cy = float(center[1])
        hx = float(half_extents[0])
        hy = float(half_extents[1])
        for label, x_sign, y_sign in (
            ("room_min_min", -1.0, -1.0),
            ("room_min_max", -1.0, 1.0),
            ("room_max_min", 1.0, -1.0),
            ("room_max_max", 1.0, 1.0),
        ):
            points.append({"label": label, "world": [cx + x_sign * hx, cy + y_sign * hy, z]})
    bounds = isaac_view.get("usd_bounds") if isinstance(isaac_view.get("usd_bounds"), dict) else {}
    minimum = _bounds_vec(bounds, "min")
    maximum = _bounds_vec(bounds, "max")
    center3 = _bounds_vec(bounds, "center")
    if center3 is not None:
        points.append({"label": "usd_bounds_center", "world": center3})
    if minimum is not None and maximum is not None:
        for label, x, y, z in (
            ("usd_bounds_min", minimum[0], minimum[1], minimum[2]),
            ("usd_bounds_max", maximum[0], maximum[1], maximum[2]),
        ):
            points.append({"label": label, "world": [x, y, z]})
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[float, float, float]]] = set()
    for point in points:
        world = point.get("world")
        if not _is_vec3(world):
            continue
        key = (
            str(point.get("label") or ""),
            (round(float(world[0]), 6), round(float(world[1]), 6), round(float(world[2]), 6)),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(point)
    return deduped


def _project_world_point(
    point: list[float],
    *,
    eye: Any,
    target: Any,
    width: float,
    height: float,
    vertical_fov_deg: float,
) -> dict[str, Any] | None:
    if not _is_vec3(eye) or not _is_vec3(target):
        return None
    eye_vec = [float(value) for value in eye[:3]]
    target_vec = [float(value) for value in target[:3]]
    forward = _normalize_vec3(
        [
            target_vec[0] - eye_vec[0],
            target_vec[1] - eye_vec[1],
            target_vec[2] - eye_vec[2],
        ]
    )
    if forward is None:
        return None
    world_up = [0.0, 0.0, 1.0]
    right = _normalize_vec3(_cross(forward, world_up))
    if right is None:
        right = [1.0, 0.0, 0.0]
    up = _cross(right, forward)
    relative = [
        float(point[0]) - eye_vec[0],
        float(point[1]) - eye_vec[1],
        float(point[2]) - eye_vec[2],
    ]
    depth = _dot(relative, forward)
    if depth <= 1e-9:
        return None
    x_camera = _dot(relative, right)
    y_camera = _dot(relative, up)
    focal_y = (height * 0.5) / math.tan(math.radians(vertical_fov_deg) * 0.5)
    focal_x = focal_y
    pixel_x = width * 0.5 + x_camera * focal_x / depth
    pixel_y = height * 0.5 - y_camera * focal_y / depth
    return {
        "pixel": [pixel_x, pixel_y],
        "depth_m": depth,
        "inside_frame": 0.0 <= pixel_x <= width and 0.0 <= pixel_y <= height,
    }


def _normalize_vec3(value: list[float]) -> list[float] | None:
    norm = math.sqrt(value[0] * value[0] + value[1] * value[1] + value[2] * value[2])
    if norm <= 1e-12:
        return None
    return [value[0] / norm, value[1] / norm, value[2] / norm]


def _cross(left: list[float], right: list[float]) -> list[float]:
    return [
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    ]


def _dot(left: list[float], right: list[float]) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _write_contact_sheet(manifest: dict[str, Any], *, output_dir: Path) -> Path | None:
    entries = _contact_sheet_entries(manifest, output_dir=output_dir)
    if not entries:
        return None
    contact_path = output_dir / "contact_sheet.png"
    tile_width = 360
    tile_height = 240
    label_height = 44
    gap = 12
    margin = 16
    lanes = (MOLMOSPACES_LANE_ID, ISAAC_LANE_ID)
    sheet_width = margin * 2 + len(lanes) * tile_width + (len(lanes) - 1) * gap
    sheet_height = margin * 2 + len(entries) * (tile_height + label_height + gap) - gap
    sheet = Image.new("RGB", (sheet_width, sheet_height), (238, 242, 246))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for row_index, entry in enumerate(entries):
        y = margin + row_index * (tile_height + label_height + gap)
        draw.text(
            (margin, y),
            f"{entry['view_id']}  {entry.get('label') or ''}",
            fill=(32, 36, 44),
            font=font,
        )
        for lane_index, lane_id in enumerate(lanes):
            x = margin + lane_index * (tile_width + gap)
            tile_y = y + label_height
            draw.rectangle(
                (x, tile_y, x + tile_width, tile_y + tile_height),
                fill=(255, 255, 255),
                outline=(203, 213, 225),
            )
            image_path = entry["images"].get(lane_id)
            if image_path is None:
                draw.text(
                    (x + 12, tile_y + 12),
                    f"missing {lane_id}",
                    fill=(100, 116, 139),
                    font=font,
                )
                continue
            with Image.open(image_path).convert("RGB") as image:
                image.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
                paste_x = x + (tile_width - image.width) // 2
                paste_y = tile_y + (tile_height - image.height) // 2
                sheet.paste(image, (paste_x, paste_y))
            draw.rectangle((x, tile_y, x + tile_width, tile_y + 18), fill=(15, 23, 42))
            draw.text((x + 6, tile_y + 4), lane_id, fill=(248, 250, 252), font=font)
    contact_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(contact_path)
    manifest.setdefault("artifacts", {})["contact_sheet"] = _relpath(contact_path, output_dir)
    manifest["contact_sheet"] = {
        "path": _relpath(contact_path, output_dir),
        "view_count": len(entries),
        "lanes": list(lanes),
        "dimensions": {
            "width": sheet.width,
            "height": sheet.height,
            "channels": 3,
        },
    }
    return contact_path


def _contact_sheet_entries(manifest: dict[str, Any], *, output_dir: Path) -> list[dict[str, Any]]:
    views = [
        item
        for item in manifest.get("canonical_camera_views") or []
        if isinstance(item, dict) and item.get("view_id")
    ]
    entries = []
    for view in views:
        view_id = str(view.get("view_id") or "")
        images: dict[str, Path] = {}
        for lane_id in (MOLMOSPACES_LANE_ID, ISAAC_LANE_ID):
            lane = (manifest.get("lanes") or {}).get(lane_id)
            if not isinstance(lane, dict):
                continue
            lane_images = lane.get("images") if isinstance(lane.get("images"), dict) else {}
            image = lane_images.get(view_id) if isinstance(lane_images, dict) else None
            if not isinstance(image, dict):
                continue
            rel_path = str(image.get("path") or "")
            path = output_dir / rel_path
            if path.is_file():
                images[lane_id] = path
        if images:
            entries.append(
                {
                    "view_id": view_id,
                    "label": view.get("label") or view.get("category") or "",
                    "images": images,
                }
            )
    return entries


def _visual_diagnostics(manifest: dict[str, Any], *, output_dir: Path) -> dict[str, Any]:
    entries = _contact_sheet_entries(manifest, output_dir=output_dir)
    view_results = []
    replay_results = []
    camera_control = (
        manifest.get("camera_control") if isinstance(manifest.get("camera_control"), dict) else {}
    )
    color_profile = (
        camera_control.get("color_profile")
        if isinstance(camera_control.get("color_profile"), dict)
        else DEFAULT_SCENE_PROBE_COLOR_PROFILE
    )
    color_profile = _normalize_color_profile_for_replay(color_profile)
    for entry in entries:
        molmo_path = entry["images"].get(MOLMOSPACES_LANE_ID)
        isaac_path = entry["images"].get(ISAAC_LANE_ID)
        if molmo_path is None or isaac_path is None:
            continue
        molmo_metrics = _image_visual_metrics(molmo_path)
        isaac_metrics = _image_visual_metrics(isaac_path)
        diff_metrics = _image_pair_visual_delta(molmo_path, isaac_path)
        view_results.append(
            {
                "view_id": entry["view_id"],
                "label": entry.get("label") or "",
                "lanes": {
                    MOLMOSPACES_LANE_ID: molmo_metrics,
                    ISAAC_LANE_ID: isaac_metrics,
                },
                "delta": {
                    **diff_metrics,
                    "mean_luminance_delta": (
                        isaac_metrics["mean_luminance"] - molmo_metrics["mean_luminance"]
                    ),
                    "mean_rgb_abs_delta": [
                        abs(
                            float(isaac_metrics["mean_rgb"][index])
                            - float(molmo_metrics["mean_rgb"][index])
                        )
                        for index in range(3)
                    ],
                },
            }
        )
        replay_results.append(
            _offline_color_profile_replay(
                view_id=entry["view_id"],
                label=entry.get("label") or "",
                molmo_path=molmo_path,
                isaac_path=isaac_path,
                color_profile=color_profile,
            )
        )
    luminance_deltas = [
        abs(float(item["delta"]["mean_luminance_delta"]))
        for item in view_results
        if isinstance(item.get("delta"), dict)
    ]
    mae_values = [
        float(item["delta"]["mean_absolute_pixel_delta"])
        for item in view_results
        if isinstance(item.get("delta"), dict)
    ]
    max_overexposed_fraction = 0.0
    max_underexposed_fraction = 0.0
    for item in view_results:
        lanes = item.get("lanes") if isinstance(item.get("lanes"), dict) else {}
        for metrics in lanes.values():
            if not isinstance(metrics, dict):
                continue
            max_overexposed_fraction = max(
                max_overexposed_fraction,
                float(metrics.get("overexposed_fraction") or 0.0),
            )
            max_underexposed_fraction = max(
                max_underexposed_fraction,
                float(metrics.get("underexposed_fraction") or 0.0),
            )
    return {
        "schema": "scene_camera_visual_diagnostics_v1",
        "status": "computed" if view_results else "missing_view_images",
        "interpretation": (
            "These image-level metrics quantify renderer/material/lighting differences after "
            "pose, intrinsics, room-scale, and target diagnostics pass. They are not a "
            "camera-pose contract."
        ),
        "view_count": len(view_results),
        "max_abs_mean_luminance_delta": max(luminance_deltas) if luminance_deltas else None,
        "mean_abs_mean_luminance_delta": (
            sum(luminance_deltas) / len(luminance_deltas) if luminance_deltas else None
        ),
        "max_mean_absolute_pixel_delta": max(mae_values) if mae_values else None,
        "mean_absolute_pixel_delta": sum(mae_values) / len(mae_values) if mae_values else None,
        "max_overexposed_fraction": max_overexposed_fraction,
        "max_underexposed_fraction": max_underexposed_fraction,
        "render_domain_calibration": _render_domain_calibration(view_results),
        "color_profile_replay": _color_profile_replay_summary(replay_results),
        "candidate_color_calibrations": _candidate_color_calibrations(
            view_results,
            entries=entries,
            base_color_profile=color_profile,
        ),
        "views": view_results,
    }


def _candidate_color_calibrations(
    view_results: list[dict[str, Any]],
    *,
    entries: list[dict[str, Any]],
    base_color_profile: dict[str, Any],
) -> dict[str, Any]:
    if not view_results:
        return {
            "schema": "scene_camera_candidate_color_calibrations_v1",
            "status": "missing_view_metrics",
            "candidates": [],
        }
    entry_by_id = {str(item.get("view_id") or ""): item for item in entries}
    candidates = [
        _candidate_color_calibration(
            "current_profile",
            view_results,
            entry_by_id=entry_by_id,
            base_color_profile=base_color_profile,
            color_profile=base_color_profile,
            interpretation="Current camera-control color profile replay.",
        ),
        _candidate_color_calibration(
            "ideal_per_view_luminance_gain",
            view_results,
            entry_by_id=entry_by_id,
            base_color_profile=base_color_profile,
            color_profile=_candidate_per_view_luminance_profile(view_results, base_color_profile),
            interpretation=(
                "Upper-bound diagnostic: per-view scalar gains match mean luminance. "
                "Do not promote directly without broader scene validation."
            ),
        ),
        _candidate_color_calibration(
            "ideal_per_view_rgb_gain",
            view_results,
            entry_by_id=entry_by_id,
            base_color_profile=base_color_profile,
            color_profile=_candidate_per_view_rgb_profile(view_results, base_color_profile),
            interpretation=(
                "Upper-bound diagnostic: per-view RGB channel gains match mean RGB. "
                "Useful for separating color response from geometry/material residuals."
            ),
        ),
    ]
    best = min(
        (item for item in candidates if item.get("status") == "computed"),
        key=lambda item: float(item.get("mean_absolute_pixel_delta") or 1e12),
        default=None,
    )
    return {
        "schema": "scene_camera_candidate_color_calibrations_v1",
        "status": "computed",
        "interpretation": (
            "Candidate calibrations replay existing PNGs with generated gain tables. They are "
            "diagnostics for choosing the next renderer slice, not fresh backend renders."
        ),
        "candidate_count": len(candidates),
        "best_candidate": best.get("candidate_id") if isinstance(best, dict) else None,
        "candidates": candidates,
    }


def _candidate_color_calibration(
    candidate_id: str,
    view_results: list[dict[str, Any]],
    *,
    entry_by_id: dict[str, dict[str, Any]],
    base_color_profile: dict[str, Any],
    color_profile: dict[str, Any],
    interpretation: str,
) -> dict[str, Any]:
    replay_results = []
    for item in view_results:
        view_id = str(item.get("view_id") or "")
        entry = entry_by_id.get(view_id)
        if not isinstance(entry, dict):
            continue
        molmo_path = entry["images"].get(MOLMOSPACES_LANE_ID)
        isaac_path = entry["images"].get(ISAAC_LANE_ID)
        if molmo_path is None or isaac_path is None:
            continue
        replay_results.append(
            _offline_color_profile_replay(
                view_id=view_id,
                label=str(item.get("label") or ""),
                molmo_path=molmo_path,
                isaac_path=isaac_path,
                color_profile=color_profile,
            )
        )
    summary = _color_profile_replay_summary(replay_results)
    return {
        "candidate_id": candidate_id,
        "status": summary.get("status"),
        "interpretation": interpretation,
        "gain_delta": _candidate_gain_delta(base_color_profile, color_profile),
        "view_count": summary.get("view_count"),
        "mean_abs_mean_luminance_delta": summary.get("mean_abs_mean_luminance_delta"),
        "mean_absolute_pixel_delta": summary.get("mean_absolute_pixel_delta"),
        "render_domain_calibration": summary.get("render_domain_calibration"),
    }


def _candidate_per_view_luminance_profile(
    view_results: list[dict[str, Any]],
    base_color_profile: dict[str, Any],
) -> dict[str, Any]:
    profile = json.loads(json.dumps(base_color_profile))
    gains: dict[str, float] = {}
    for item in view_results:
        view_id = str(item.get("view_id") or "")
        lanes = item.get("lanes") if isinstance(item.get("lanes"), dict) else {}
        molmo = lanes.get(MOLMOSPACES_LANE_ID) if isinstance(lanes, dict) else {}
        isaac = lanes.get(ISAAC_LANE_ID) if isinstance(lanes, dict) else {}
        molmo_luminance = _optional_float(
            molmo.get("mean_luminance") if isinstance(molmo, dict) else None
        )
        isaac_luminance = _optional_float(
            isaac.get("mean_luminance") if isinstance(isaac, dict) else None
        )
        if not view_id or molmo_luminance is None or isaac_luminance is None:
            continue
        gains[view_id] = molmo_luminance / isaac_luminance if isaac_luminance > 0 else 1.0
    if gains:
        profile["backend_view_luminance_gain"] = {ISAAC_LANE_ID: gains}
        profile["backend_view_luminance_gain_source"] = "candidate_from_current_view_metrics"
    return profile


def _candidate_per_view_rgb_profile(
    view_results: list[dict[str, Any]],
    base_color_profile: dict[str, Any],
) -> dict[str, Any]:
    profile = json.loads(json.dumps(base_color_profile))
    gains: dict[str, list[float]] = {}
    for item in view_results:
        view_id = str(item.get("view_id") or "")
        lanes = item.get("lanes") if isinstance(item.get("lanes"), dict) else {}
        molmo = lanes.get(MOLMOSPACES_LANE_ID) if isinstance(lanes, dict) else {}
        isaac = lanes.get(ISAAC_LANE_ID) if isinstance(lanes, dict) else {}
        molmo_rgb = molmo.get("mean_rgb") if isinstance(molmo, dict) else None
        isaac_rgb = isaac.get("mean_rgb") if isinstance(isaac, dict) else None
        if not view_id or not isinstance(molmo_rgb, list) or not isinstance(isaac_rgb, list):
            continue
        channel_gains = []
        for molmo_value, isaac_value in zip(molmo_rgb[:3], isaac_rgb[:3], strict=False):
            molmo_float = _optional_float(molmo_value)
            isaac_float = _optional_float(isaac_value)
            if molmo_float is None or isaac_float is None or isaac_float <= 0:
                channel_gains.append(1.0)
            else:
                channel_gains.append(molmo_float / isaac_float)
        if len(channel_gains) == 3:
            gains[view_id] = channel_gains
    if gains:
        profile["backend_view_rgb_gain"] = {ISAAC_LANE_ID: gains}
        profile["backend_view_rgb_gain_source"] = "candidate_from_current_view_metrics"
        profile["backend_view_luminance_gain"] = {
            ISAAC_LANE_ID: {view_id: 1.0 for view_id in gains}
        }
        profile["backend_view_luminance_gain_source"] = (
            "candidate_rgb_gain_already_includes_luminance"
        )
    return profile


def _candidate_gain_delta(
    base_color_profile: dict[str, Any],
    color_profile: dict[str, Any],
) -> dict[str, Any]:
    keys = (
        "backend_view_luminance_gain",
        "backend_view_rgb_gain",
        "backend_luminance_gain",
        "backend_rgb_gain",
    )
    return {
        key: color_profile.get(key)
        for key in keys
        if color_profile.get(key) != base_color_profile.get(key)
    }


def _offline_color_profile_replay(
    *,
    view_id: str,
    label: str,
    molmo_path: Path,
    isaac_path: Path,
    color_profile: dict[str, Any],
) -> dict[str, Any]:
    import numpy as np

    molmo_replay_path = _color_profile_replay_image(
        molmo_path,
        np=np,
        color_profile=color_profile,
        backend=MOLMOSPACES_LANE_ID,
        view_id=view_id,
    )
    isaac_replay_path = _color_profile_replay_image(
        isaac_path,
        np=np,
        color_profile=color_profile,
        backend=ISAAC_LANE_ID,
        view_id=view_id,
    )
    molmo_metrics = _image_visual_metrics(molmo_replay_path)
    isaac_metrics = _image_visual_metrics(isaac_replay_path)
    diff_metrics = _image_pair_visual_delta(molmo_replay_path, isaac_replay_path)
    return {
        "view_id": view_id,
        "label": label,
        "lanes": {
            MOLMOSPACES_LANE_ID: molmo_metrics,
            ISAAC_LANE_ID: isaac_metrics,
        },
        "delta": {
            **diff_metrics,
            "mean_luminance_delta": isaac_metrics["mean_luminance"]
            - molmo_metrics["mean_luminance"],
        },
    }


def _normalize_color_profile_for_replay(color_profile: dict[str, Any]) -> dict[str, Any]:
    request = normalize_camera_control_request(
        {
            "render_resolution": {"width": 1, "height": 1},
            "color_profile": color_profile,
            "views": [],
        }
    )
    return dict(request.get("color_profile") or {})


def _color_profile_replay_image(
    path: Path,
    *,
    np: Any,
    color_profile: dict[str, Any],
    backend: str,
    view_id: str,
) -> Path:
    with Image.open(path).convert("RGB") as image:
        array = np.asarray(image)
    rgb_gain = _color_profile_backend_rgb_gain(
        color_profile,
        backend=backend,
        view_id=view_id,
    )
    adjusted = array.astype("float32") * np.asarray(rgb_gain, dtype="float32").reshape(1, 1, 3)
    gain = _color_profile_backend_luminance_gain(
        color_profile,
        backend=backend,
        view_id=view_id,
    )
    adjusted = np.clip(adjusted * gain, 0, 255).astype("uint8")
    replay_path = path.with_name(f"{path.stem}.color_profile_replay.png")
    Image.fromarray(adjusted).save(replay_path)
    return replay_path


def _color_profile_backend_luminance_gain(
    color_profile: dict[str, Any],
    *,
    backend: str,
    view_id: str,
) -> float:
    view_gains = color_profile.get("backend_view_luminance_gain")
    if isinstance(view_gains, dict):
        backend_view_gains = view_gains.get(backend)
        if isinstance(backend_view_gains, dict) and view_id in backend_view_gains:
            try:
                return float(backend_view_gains[view_id])
            except (TypeError, ValueError):
                return 1.0
    gains = color_profile.get("backend_luminance_gain")
    if not isinstance(gains, dict) or backend not in gains:
        return 1.0
    try:
        return float(gains[backend])
    except (TypeError, ValueError):
        return 1.0


def _color_profile_backend_rgb_gain(
    color_profile: dict[str, Any],
    *,
    backend: str,
    view_id: str,
) -> list[float]:
    view_gains = color_profile.get("backend_view_rgb_gain")
    if isinstance(view_gains, dict):
        backend_view_gains = view_gains.get(backend)
        if isinstance(backend_view_gains, dict) and view_id in backend_view_gains:
            return _rgb_gain_or_identity(backend_view_gains[view_id])
    gains = color_profile.get("backend_rgb_gain")
    if isinstance(gains, dict) and backend in gains:
        return _rgb_gain_or_identity(gains[backend])
    return [1.0, 1.0, 1.0]


def _rgb_gain_or_identity(value: Any) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return [1.0, 1.0, 1.0]
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return [1.0, 1.0, 1.0]


def _color_profile_replay_summary(view_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not view_results:
        return {
            "schema": "scene_camera_color_profile_replay_v1",
            "status": "missing_view_images",
            "view_count": 0,
        }
    luminance_deltas = [
        abs(float(item["delta"]["mean_luminance_delta"]))
        for item in view_results
        if isinstance(item.get("delta"), dict)
    ]
    mae_values = [
        float(item["delta"]["mean_absolute_pixel_delta"])
        for item in view_results
        if isinstance(item.get("delta"), dict)
    ]
    return {
        "schema": "scene_camera_color_profile_replay_v1",
        "status": "computed",
        "interpretation": (
            "Offline replay applies only the current backend_luminance_gain delta to "
            "existing already-color-managed PNGs. It estimates the expected direction of "
            "renderer calibration without claiming a fresh backend rerender."
        ),
        "view_count": len(view_results),
        "mean_abs_mean_luminance_delta": (
            sum(luminance_deltas) / len(luminance_deltas) if luminance_deltas else None
        ),
        "max_abs_mean_luminance_delta": max(luminance_deltas) if luminance_deltas else None,
        "mean_absolute_pixel_delta": sum(mae_values) / len(mae_values) if mae_values else None,
        "max_mean_absolute_pixel_delta": max(mae_values) if mae_values else None,
        "render_domain_calibration": _render_domain_calibration(view_results),
        "views": view_results,
    }


def _render_domain_calibration(view_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Estimate whether one global Isaac luminance gain explains the visual delta."""

    pairs = []
    for item in view_results:
        lanes = item.get("lanes") if isinstance(item.get("lanes"), dict) else {}
        molmo = (
            lanes.get(MOLMOSPACES_LANE_ID)
            if isinstance(lanes.get(MOLMOSPACES_LANE_ID), dict)
            else {}
        )
        isaac = lanes.get(ISAAC_LANE_ID) if isinstance(lanes.get(ISAAC_LANE_ID), dict) else {}
        molmo_luminance = _optional_float(molmo.get("mean_luminance"))
        isaac_luminance = _optional_float(isaac.get("mean_luminance"))
        if molmo_luminance is None or isaac_luminance is None or isaac_luminance <= 0:
            continue
        pairs.append(
            {
                "view_id": str(item.get("view_id") or ""),
                "molmospaces_luminance": molmo_luminance,
                "isaac_luminance": isaac_luminance,
            }
        )
    if not pairs:
        return {
            "schema": "scene_camera_render_domain_calibration_v1",
            "status": "missing_luminance_pairs",
            "pair_count": 0,
        }

    numerator = sum(pair["molmospaces_luminance"] * pair["isaac_luminance"] for pair in pairs)
    denominator = sum(pair["isaac_luminance"] ** 2 for pair in pairs)
    gain = numerator / denominator if denominator > 0 else 1.0
    residuals = []
    original_abs_deltas = []
    for pair in pairs:
        calibrated = pair["isaac_luminance"] * gain
        residual = calibrated - pair["molmospaces_luminance"]
        original_delta = pair["isaac_luminance"] - pair["molmospaces_luminance"]
        original_abs_deltas.append(abs(original_delta))
        residuals.append(
            {
                **pair,
                "calibrated_isaac_luminance": calibrated,
                "original_luminance_delta": original_delta,
                "calibrated_luminance_residual": residual,
                "abs_calibrated_luminance_residual": abs(residual),
            }
        )
    mean_original_delta = sum(original_abs_deltas) / len(original_abs_deltas)
    abs_residuals = [item["abs_calibrated_luminance_residual"] for item in residuals]
    mean_residual = sum(abs_residuals) / len(abs_residuals)
    max_residual = max(abs_residuals)
    improvement_fraction = (
        1.0 - mean_residual / mean_original_delta if mean_original_delta > 0 else 1.0
    )
    if mean_original_delta <= 10.0:
        status = "already_luminance_matched"
        next_action = "Do not tune exposure from this artifact; inspect material/texture deltas."
    elif mean_residual <= 12.0 and max_residual <= 20.0:
        status = "global_luminance_gain_sufficient"
        next_action = "A global Isaac exposure/gain adjustment is a plausible next renderer slice."
    else:
        status = "view_dependent_render_domain_delta"
        next_action = (
            "A single global gain leaves large residuals; inspect per-room lights, material "
            "albedo, indirect lighting, and tone response before changing camera geometry."
        )
    return {
        "schema": "scene_camera_render_domain_calibration_v1",
        "status": status,
        "pair_count": len(pairs),
        "global_isaac_luminance_gain": gain,
        "mean_abs_original_luminance_delta": mean_original_delta,
        "mean_abs_calibrated_luminance_residual": mean_residual,
        "max_abs_calibrated_luminance_residual": max_residual,
        "mean_luminance_delta_improvement_fraction": improvement_fraction,
        "recommended_next_action": next_action,
        "residuals": residuals,
    }


def _backend_swap_geometry_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    camera = (
        manifest.get("camera_control") if isinstance(manifest.get("camera_control"), dict) else {}
    )
    pose = (
        manifest.get("camera_pose_contract")
        if isinstance(manifest.get("camera_pose_contract"), dict)
        else {}
    )
    intrinsics = (
        manifest.get("camera_intrinsics_contract")
        if isinstance(manifest.get("camera_intrinsics_contract"), dict)
        else {}
    )
    room_scale = (
        manifest.get("room_scale_contract")
        if isinstance(manifest.get("room_scale_contract"), dict)
        else {}
    )
    projection = (
        manifest.get("projection_diagnostics")
        if isinstance(manifest.get("projection_diagnostics"), dict)
        else {}
    )
    transform = (
        manifest.get("scene_frame_transform")
        if isinstance(manifest.get("scene_frame_transform"), dict)
        else {}
    )
    visual = (
        manifest.get("visual_diagnostics")
        if isinstance(manifest.get("visual_diagnostics"), dict)
        else {}
    )
    render_calibration = (
        visual.get("render_domain_calibration")
        if isinstance(visual.get("render_domain_calibration"), dict)
        else {}
    )
    required_checks = [
        {
            "check": "same_camera_api",
            "status": "pass" if camera.get("api_name") == CAMERA_CONTROL_API_NAME else "fail",
            "value": camera.get("api_name"),
            "expected": CAMERA_CONTROL_API_NAME,
        },
        {
            "check": "same_explicit_eye_target_pose",
            "status": "pass"
            if pose.get("status") == "same_backend_pose_within_threshold"
            else "fail",
            "value": pose.get("status"),
            "max_delta_m": pose.get("max_pose_delta_m"),
            "threshold_m": pose.get("pose_threshold_m"),
        },
        {
            "check": "same_intrinsics",
            "status": "pass" if intrinsics.get("status") == "intrinsics_consistent" else "fail",
            "value": intrinsics.get("status"),
            "vertical_fov_deg": projection.get("vertical_fov_deg"),
            "resolution": projection.get("resolution") or intrinsics.get("resolution"),
        },
        {
            "check": "same_room_scale",
            "status": "pass"
            if room_scale.get("status") == "same_room_outlines_within_threshold"
            else "fail",
            "value": room_scale.get("status"),
            "max_center_delta_m": room_scale.get("max_room_outline_center_delta_m"),
            "max_size_delta_m": room_scale.get("max_room_outline_size_delta_m"),
            "threshold_m": room_scale.get("room_outline_threshold_m"),
        },
        {
            "check": "same_projected_geometry",
            "status": "pass"
            if projection.get("status") == "same_projected_geometry_within_threshold"
            else "fail",
            "value": projection.get("status"),
            "max_pixel_delta": projection.get("max_pixel_delta"),
            "threshold_px": projection.get("projection_threshold_px"),
        },
    ]
    geometry_pass = all(item["status"] == "pass" for item in required_checks)
    mean_pixel_delta = _optional_float(visual.get("mean_absolute_pixel_delta"))
    mean_luminance_delta = _optional_float(visual.get("mean_abs_mean_luminance_delta"))
    render_domain_status = str(render_calibration.get("status") or "")
    visual_residual_status = (
        "render_domain_residual_high"
        if render_domain_status == "view_dependent_render_domain_delta"
        else "render_domain_luminance_matched"
        if render_domain_status == "already_luminance_matched"
        else render_domain_status or "missing_visual_diagnostics"
    )
    status = (
        "geometry_swap_ready_render_domain_pending"
        if geometry_pass and visual_residual_status == "render_domain_residual_high"
        else "geometry_swap_ready"
        if geometry_pass
        else "geometry_swap_not_ready"
    )
    return {
        "schema": "backend_swap_geometry_contract_v1",
        "status": status,
        "geometry_contract_status": "pass" if geometry_pass else "fail",
        "visual_residual_status": visual_residual_status,
        "required_checks": required_checks,
        "same_api_agent_swap_claim": geometry_pass,
        "view_count": pose.get("pair_count") or projection.get("pair_count"),
        "target_definition_status": transform.get("target_residual_status"),
        "max_target_center_residual_m": transform.get("max_residual_m"),
        "max_target_distance_to_usd_bounds_m": transform.get("max_distance_to_usd_bounds_m"),
        "max_surface_aim_distance_to_usd_bounds_m": transform.get(
            "max_surface_aim_distance_to_usd_bounds_m"
        ),
        "mean_absolute_pixel_delta": mean_pixel_delta,
        "mean_abs_mean_luminance_delta": mean_luminance_delta,
        "render_domain_status": render_domain_status,
        "recommended_next_action": render_calibration.get("recommended_next_action"),
        "interpretation": (
            "This is the backend-swap contract for agent-facing camera control: the same "
            "Roboclaws camera API, explicit eye/target pose, vertical FOV, room scale, and "
            "pinhole projection must pass before an agent can treat MuJoCo and Isaac as "
            "geometry-compatible backends. Visual residuals are tracked separately because "
            "material, texture, light, shadow, and tone-response differences can still make "
            "the images look different."
        ),
    }


def _render_domain_source_diagnostics(manifest: dict[str, Any]) -> dict[str, Any]:
    visual = (
        manifest.get("visual_diagnostics")
        if isinstance(manifest.get("visual_diagnostics"), dict)
        else {}
    )
    calibration = (
        visual.get("render_domain_calibration")
        if isinstance(visual.get("render_domain_calibration"), dict)
        else {}
    )
    source_refs = [_render_source_reference(item) for item in OFFICIAL_RENDER_SOURCE_REFERENCES]
    missing = [item for item in source_refs if item.get("status") != "available"]
    lane_summary = {
        MOLMOSPACES_LANE_ID: {
            "renderer_contract": "MJCF materials/textures/lights rendered by MuJoCo",
            "evidence_count": sum(
                1 for item in source_refs if item.get("lane") == MOLMOSPACES_LANE_ID
            ),
        },
        ISAAC_LANE_ID: {
            "renderer_contract": "USD PreviewSurface materials/lights rendered by Isaac",
            "evidence_count": sum(1 for item in source_refs if item.get("lane") == ISAAC_LANE_ID),
        },
    }
    status = "official_sources_available" if not missing else "missing_official_source_refs"
    root_cause_status = (
        "render_contract_mismatch_evidence"
        if calibration.get("status") == "view_dependent_render_domain_delta" and not missing
        else "source_evidence_available"
        if not missing
        else "source_evidence_incomplete"
    )
    return {
        "schema": "scene_camera_render_domain_source_diagnostics_v1",
        "status": status,
        "root_cause_status": root_cause_status,
        "official_source": "vendors/molmospaces",
        "source_reference_count": len(source_refs),
        "available_source_reference_count": len(source_refs) - len(missing),
        "missing_source_reference_count": len(missing),
        "lane_summary": lane_summary,
        "source_references": source_refs,
        "recommended_next_action": (
            "Tune renderer parity at the material/light/texture contract boundary before "
            "changing camera geometry: compare MJCF material/texture/light inputs against "
            "the converted USD PreviewSurface, default light, shadow, and texture-binding "
            "outputs for each high-delta view."
        ),
        "interpretation": (
            "These diagnostics cite the official MolmoSpaces code paths that feed each "
            "backend's renderer. They explain why equal camera geometry can still produce "
            "different images: MuJoCo renders MJCF material/light state, while Isaac renders "
            "converted USD PreviewSurface materials, authored USD lights, shadow flags, and "
            "texture bindings."
        ),
    }


def _render_domain_view_triage(manifest: dict[str, Any]) -> dict[str, Any]:
    visual = (
        manifest.get("visual_diagnostics")
        if isinstance(manifest.get("visual_diagnostics"), dict)
        else {}
    )
    projection = (
        manifest.get("projection_diagnostics")
        if isinstance(manifest.get("projection_diagnostics"), dict)
        else {}
    )
    source = (
        manifest.get("render_domain_source_diagnostics")
        if isinstance(manifest.get("render_domain_source_diagnostics"), dict)
        else _render_domain_source_diagnostics(manifest)
    )
    source_ids = [
        str(item.get("evidence_id"))
        for item in source.get("source_references") or []
        if isinstance(item, dict) and item.get("status") == "available"
    ]
    projection_by_view = {
        str(item.get("view_id") or ""): item
        for item in projection.get("pairs") or []
        if isinstance(item, dict)
    }
    views = [item for item in visual.get("views") or [] if isinstance(item, dict)]
    rows = []
    for item in views:
        view_id = str(item.get("view_id") or "")
        delta = item.get("delta") if isinstance(item.get("delta"), dict) else {}
        pixel_delta = _optional_float(delta.get("mean_absolute_pixel_delta"))
        luminance_delta = _optional_float(delta.get("mean_luminance_delta"))
        luminance_abs = abs(luminance_delta) if luminance_delta is not None else None
        projection_pair = projection_by_view.get(view_id, {})
        projection_delta = _optional_float(projection_pair.get("max_pixel_delta"))
        anchor_kind = _view_anchor_kind(manifest, view_id)
        usd_prim_path = _view_usd_prim_path(manifest, view_id)
        residual_class = _view_render_residual_class(
            pixel_delta=pixel_delta,
            luminance_abs=luminance_abs,
        )
        suspicion = _view_render_suspicion(
            residual_class=residual_class,
            anchor_kind=anchor_kind,
            usd_prim_path=usd_prim_path,
        )
        rows.append(
            {
                "view_id": view_id,
                "label": item.get("label"),
                "anchor_kind": anchor_kind,
                "usd_prim_path": usd_prim_path,
                "mean_absolute_pixel_delta": pixel_delta,
                "abs_mean_luminance_delta": luminance_abs,
                "max_projection_delta_px": projection_delta,
                "geometry_status": "projection_pass"
                if projection_delta is not None
                and projection_delta <= CANONICAL_CAMERA_PROJECTION_THRESHOLD_PX
                else "projection_missing_or_failed",
                "render_residual_class": residual_class,
                "suspected_contract": suspicion,
                "next_probe": _view_render_next_probe(suspicion),
            }
        )
    high = [
        item
        for item in rows
        if item.get("render_residual_class") in {"high_pixel_and_luminance", "high_pixel_delta"}
    ]
    rows.sort(
        key=lambda item: (
            float(item.get("mean_absolute_pixel_delta") or 0.0),
            float(item.get("abs_mean_luminance_delta") or 0.0),
        ),
        reverse=True,
    )
    return {
        "schema": "scene_camera_render_domain_view_triage_v1",
        "status": "computed" if rows else "missing_visual_view_metrics",
        "view_count": len(rows),
        "high_residual_view_count": len(high),
        "source_evidence_ids": source_ids,
        "top_residual_view_id": rows[0].get("view_id") if rows else None,
        "views": rows,
        "recommended_next_action": (
            "Start with the highest-residual object/receptacle views. For object views, "
            "compare the MuJoCo MJCF material/texture assigned to the anchor against the "
            "Isaac USD material binding and PreviewSurface inputs for the same prim. For "
            "room views, compare exported/default lights and wall or ceiling shadow flags."
        ),
        "interpretation": (
            "This view-level triage keeps camera geometry separate from renderer-domain "
            "work. A view can have projection_pass while still carrying a material, "
            "texture, lighting, shadow, or tone-response residual."
        ),
    }


def _view_anchor_kind(manifest: dict[str, Any], view_id: str) -> str:
    for view in manifest.get("canonical_camera_views") or []:
        if isinstance(view, dict) and str(view.get("view_id") or "") == view_id:
            return str(view.get("anchor_kind") or "")
    return ""


def _view_usd_prim_path(manifest: dict[str, Any], view_id: str) -> str:
    anchor_id = ""
    for view in ((manifest.get("lanes") or {}).get(ISAAC_LANE_ID) or {}).get("views") or []:
        if isinstance(view, dict) and str(view.get("view_id") or "") == view_id:
            usd_prim_path = str(view.get("usd_prim_path") or "")
            if usd_prim_path:
                return usd_prim_path
            anchor_id = str(view.get("anchor_id") or "")
            break
    for view in manifest.get("canonical_camera_views") or []:
        if isinstance(view, dict) and str(view.get("view_id") or "") == view_id:
            usd_prim_path = str(view.get("usd_prim_path") or "")
            if usd_prim_path:
                return usd_prim_path
            if not anchor_id:
                anchor_id = str(view.get("anchor_id") or "")
            break
    if anchor_id:
        for anchor in manifest.get("anchors") or []:
            if isinstance(anchor, dict) and str(anchor.get("anchor_id") or "") == anchor_id:
                return str(anchor.get("isaac_usd_prim_path") or "")
    return ""


def _view_render_residual_class(
    *,
    pixel_delta: float | None,
    luminance_abs: float | None,
) -> str:
    if pixel_delta is None:
        return "missing_pixel_delta"
    pixel_high = pixel_delta >= 50.0
    luminance_high = luminance_abs is not None and luminance_abs >= 30.0
    if pixel_high and luminance_high:
        return "high_pixel_and_luminance"
    if pixel_high:
        return "high_pixel_delta"
    if luminance_high:
        return "high_luminance_delta"
    return "moderate_or_low_residual"


def _view_render_suspicion(
    *,
    residual_class: str,
    anchor_kind: str,
    usd_prim_path: str,
) -> str:
    if residual_class == "moderate_or_low_residual":
        return "lower_priority_renderer_delta"
    if anchor_kind == "room":
        return "room_light_wall_shadow_contract"
    if usd_prim_path:
        return "object_material_texture_binding_contract"
    return "object_material_texture_contract_missing_usd_prim"


def _view_render_next_probe(suspicion: str) -> str:
    if suspicion == "room_light_wall_shadow_contract":
        return "Compare MuJoCo default/exported lights with Isaac USD lights and wall shadow flags."
    if suspicion == "object_material_texture_binding_contract":
        return "Compare MJCF material/texture inputs with the matched Isaac USD material binding."
    if suspicion == "object_material_texture_contract_missing_usd_prim":
        return "Resolve the Isaac USD prim path before comparing material or texture contracts."
    return "Keep as lower priority until high-residual views are explained."


def _render_source_reference(reference: dict[str, Any]) -> dict[str, Any]:
    rel_path = Path(str(reference.get("path") or ""))
    path = REPO_ROOT / rel_path
    line_start = int(reference.get("line_start") or 1)
    line_end = int(reference.get("line_end") or line_start)
    exists = path.is_file()
    snippet_status = "missing"
    snippet = ""
    if exists:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            selected = lines[max(line_start - 1, 0) : max(line_end, line_start)]
            snippet_status = "available" if selected else "empty"
            snippet = _render_source_snippet(selected)
        except OSError:
            snippet_status = "unreadable"
    return {
        "evidence_id": reference.get("evidence_id"),
        "lane": reference.get("lane"),
        "path": str(rel_path),
        "line_start": line_start,
        "line_end": line_end,
        "status": "available" if exists and snippet_status == "available" else snippet_status,
        "claim": reference.get("claim"),
        "snippet_summary": snippet,
    }


def _render_source_snippet(lines: list[str]) -> str:
    priority_keywords = (
        "doNotCastShadows",
        "opacity=1.0",
        "definePreviewMaterial",
        "addDiffuseTextureToPreviewMaterial",
        "UsdLux.DistantLight",
        "defineDomeLight",
        "add_light",
        "add_texture",
    )
    keywords = (
        "material",
        "texture",
        "light",
        "shadow",
        "opacity",
        "roughness",
        "specular",
        "Preview",
        "DistantLight",
        "DomeLight",
        "doNotCastShadows",
    )
    matching = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if (
            stripped.startswith("def ")
            or stripped.startswith("#")
            or stripped.endswith(":")
            or stripped in {")", "("}
        ):
            continue
        if any(keyword.lower() in stripped.lower() for keyword in keywords):
            matching.append(stripped)
    selected = []
    for keyword in priority_keywords:
        for line in matching:
            if keyword.lower() in line.lower() and line not in selected:
                selected.append(line)
            if len(selected) >= 5:
                break
        if len(selected) >= 5:
            break
    for line in matching:
        if line not in selected:
            selected.append(line)
        if len(selected) >= 5:
            break
    if not selected:
        selected = [line.strip() for line in lines if line.strip()][:3]
    return " | ".join(selected)


def _image_visual_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path).convert("RGB") as image:
        pixels = list(image.getdata())
    count = max(len(pixels), 1)
    sums = [0.0, 0.0, 0.0]
    luminance_sum = 0.0
    luminance_sq_sum = 0.0
    overexposed_count = 0
    underexposed_count = 0
    for red, green, blue in pixels:
        red_f = float(red)
        green_f = float(green)
        blue_f = float(blue)
        sums[0] += red_f
        sums[1] += green_f
        sums[2] += blue_f
        luminance = 0.2126 * red_f + 0.7152 * green_f + 0.0722 * blue_f
        luminance_sum += luminance
        luminance_sq_sum += luminance * luminance
        if red >= 250 and green >= 250 and blue >= 250:
            overexposed_count += 1
        if red <= 5 and green <= 5 and blue <= 5:
            underexposed_count += 1
    mean_luminance = luminance_sum / count
    variance = max(luminance_sq_sum / count - mean_luminance * mean_luminance, 0.0)
    return {
        "mean_rgb": [value / count for value in sums],
        "mean_luminance": mean_luminance,
        "std_luminance": math.sqrt(variance),
        "overexposed_fraction": overexposed_count / count,
        "underexposed_fraction": underexposed_count / count,
    }


def _image_pair_visual_delta(left_path: Path, right_path: Path) -> dict[str, Any]:
    with Image.open(left_path).convert("RGB") as left_image:
        with Image.open(right_path).convert("RGB") as right_image:
            if left_image.size != right_image.size:
                right_image = right_image.resize(left_image.size, Image.Resampling.BILINEAR)
            left_pixels = list(left_image.getdata())
            right_pixels = list(right_image.getdata())
    count = max(len(left_pixels), 1)
    absolute_sum = 0.0
    rms_sum = 0.0
    max_delta = 0.0
    for left, right in zip(left_pixels, right_pixels, strict=True):
        channel_deltas = [abs(float(left[index]) - float(right[index])) for index in range(3)]
        pixel_delta = sum(channel_deltas) / 3.0
        absolute_sum += pixel_delta
        rms_sum += sum(delta * delta for delta in channel_deltas) / 3.0
        max_delta = max(max_delta, max(channel_deltas))
    return {
        "mean_absolute_pixel_delta": absolute_sum / count,
        "rms_pixel_delta": math.sqrt(rms_sum / count),
        "max_channel_delta": max_delta,
    }


def _views_by_id(lane: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("view_id") or ""): item
        for item in lane.get("views") or []
        if isinstance(item, dict)
    }


def _backend_vec(view: dict[str, Any], key: str) -> list[float] | None:
    backend_value = view.get(f"backend_{key}")
    value = backend_value if _is_vec3(backend_value) else view.get(key)
    return [float(item) for item in value[:3]] if _is_vec3(value) else None


def _bounds_vec(bounds: dict[str, Any], key: str) -> list[float] | None:
    value = bounds.get(key)
    return [float(item) for item in value[:3]] if _is_vec3(value) else None


def _point_inside_xy_bounds(point: list[float], bounds: dict[str, Any]) -> bool | None:
    minimum = _bounds_vec(bounds, "min")
    maximum = _bounds_vec(bounds, "max")
    if minimum is None or maximum is None:
        return None
    return (
        minimum[0] <= float(point[0]) <= maximum[0] and minimum[1] <= float(point[1]) <= maximum[1]
    )


def _point_inside_xyz_bounds(point: list[float], bounds: dict[str, Any]) -> bool | None:
    minimum = _bounds_vec(bounds, "min")
    maximum = _bounds_vec(bounds, "max")
    if minimum is None or maximum is None:
        return None
    return (
        minimum[0] <= float(point[0]) <= maximum[0]
        and minimum[1] <= float(point[1]) <= maximum[1]
        and minimum[2] <= float(point[2]) <= maximum[2]
    )


def _distance_to_axis_aligned_bounds(point: list[float], bounds: dict[str, Any]) -> float | None:
    minimum = _bounds_vec(bounds, "min")
    maximum = _bounds_vec(bounds, "max")
    if minimum is None or maximum is None:
        return None
    squared = 0.0
    for index in range(3):
        value = float(point[index])
        if value < minimum[index]:
            squared += (minimum[index] - value) ** 2
        elif value > maximum[index]:
            squared += (value - maximum[index]) ** 2
    return math.sqrt(squared)


def _surface_aim_distance_to_bounds(
    point: list[float],
    bounds: dict[str, Any],
    *,
    allowance_m: float,
) -> float | None:
    minimum = _bounds_vec(bounds, "min")
    maximum = _bounds_vec(bounds, "max")
    if minimum is None or maximum is None:
        return None
    adjusted_maximum = list(maximum)
    adjusted_maximum[2] += max(0.0, float(allowance_m))
    return _distance_to_explicit_axis_aligned_bounds(point, minimum, adjusted_maximum)


def _distance_to_explicit_axis_aligned_bounds(
    point: list[float],
    minimum: list[float],
    maximum: list[float],
) -> float:
    squared = 0.0
    for index in range(3):
        value = float(point[index])
        if value < minimum[index]:
            squared += (minimum[index] - value) ** 2
        elif value > maximum[index]:
            squared += (value - maximum[index]) ** 2
    return math.sqrt(squared)


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
        float(target[0]) - math.cos(azimuth_rad) * horizontal,
        float(target[1]) - math.sin(azimuth_rad) * horizontal,
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


def _distance_xy(left: list[float], right: list[float]) -> float:
    return math.hypot(float(left[0]) - float(right[0]), float(left[1]) - float(right[1]))


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
            _contact_sheet_section(manifest, output_dir=output_dir),
            _pose_contract_section(manifest),
            _intrinsics_contract_section(manifest),
            _room_scale_section(manifest),
            _backend_swap_geometry_section(manifest),
            _transform_section(manifest),
            _projection_diagnostics_section(manifest),
            _visual_diagnostics_section(manifest),
            _render_domain_source_section(manifest),
            _render_domain_view_triage_section(manifest),
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
    .contact-sheet {{
      width: 100%;
      max-height: 960px;
      object-fit: contain;
      background: #f8fafc;
      border: 1px solid #d9dde6;
      border-radius: 6px;
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
    official_source = (
        manifest.get("official_molmospaces_source")
        if isinstance(manifest.get("official_molmospaces_source"), dict)
        else {}
    )
    camera = (
        manifest.get("camera_control") if isinstance(manifest.get("camera_control"), dict) else {}
    )
    lens = camera.get("lens") if isinstance(camera.get("lens"), dict) else {}
    lighting = (
        camera.get("lighting_profile") if isinstance(camera.get("lighting_profile"), dict) else {}
    )
    color = camera.get("color_profile") if isinstance(camera.get("color_profile"), dict) else {}
    transform = (
        manifest.get("scene_frame_transform")
        if isinstance(manifest.get("scene_frame_transform"), dict)
        else {}
    )
    pose_contract = (
        manifest.get("camera_pose_contract")
        if isinstance(manifest.get("camera_pose_contract"), dict)
        else {}
    )
    intrinsics = (
        manifest.get("camera_intrinsics_contract")
        if isinstance(manifest.get("camera_intrinsics_contract"), dict)
        else {}
    )
    room_scale = (
        manifest.get("room_scale_contract")
        if isinstance(manifest.get("room_scale_contract"), dict)
        else {}
    )
    projection = (
        manifest.get("projection_diagnostics")
        if isinstance(manifest.get("projection_diagnostics"), dict)
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
                ("MolmoSpaces source", official_source.get("url")),
                ("MolmoSpaces commit", _short_commit(official_source.get("commit_id"))),
                ("render", f"{scene.get('render_width')} x {scene.get('render_height')}"),
                ("camera API", camera.get("api_name")),
                ("camera model", camera.get("camera_model")),
                ("frame", camera.get("coordinate_frame")),
                ("calibration", camera.get("calibration_status")),
                ("same pose", camera.get("same_pose_contract")),
                ("camera pose", pose_contract.get("status")),
                ("max pose delta", _meters_text(pose_contract.get("max_pose_delta_m"))),
                ("intrinsics", intrinsics.get("status")),
                ("room scale", room_scale.get("status")),
                ("target vs USD", transform.get("target_residual_status")),
                ("projection", projection.get("status")),
                ("target residual", _meters_text(transform.get("max_residual_m"))),
                ("max projection delta", _pixels_text(projection.get("max_pixel_delta"))),
                ("FOV", f"{lens.get('vertical_fov_deg')} deg" if lens else ""),
                ("lighting", lighting.get("profile_id") if lighting else ""),
                ("color", color.get("profile_id") if color else ""),
            ]
        )
    }</div>
</section>
"""


def _contact_sheet_section(manifest: dict[str, Any], *, output_dir: Path) -> str:
    contact_sheet = (
        manifest.get("contact_sheet") if isinstance(manifest.get("contact_sheet"), dict) else {}
    )
    path = str(contact_sheet.get("path") or "")
    if not path:
        artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
        path = str(artifacts.get("contact_sheet") or "")
    if not path or not (output_dir / path).is_file():
        return ""
    dimensions = (
        contact_sheet.get("dimensions") if isinstance(contact_sheet.get("dimensions"), dict) else {}
    )
    note = (
        f"{contact_sheet.get('view_count') or ''} canonical views, "
        f"{_dimension_text(dimensions)}. "
        "Use this as a first-pass visual scan; the tables below carry the pose, "
        "intrinsics, room-scale, and target residual diagnostics."
    )
    return f"""
<section class="panel">
  <h2>Contact Sheet</h2>
  <p class="note">{html.escape(note)}</p>
  <img class="contact-sheet" src="{html.escape(path, quote=True)}"
       alt="MuJoCo and Isaac view contact sheet">
</section>
"""


def _intrinsics_contract_section(manifest: dict[str, Any]) -> str:
    contract = (
        manifest.get("camera_intrinsics_contract")
        if isinstance(manifest.get("camera_intrinsics_contract"), dict)
        else {}
    )
    if not contract:
        return ""
    requested = (
        contract.get("requested_lens") if isinstance(contract.get("requested_lens"), dict) else {}
    )
    molmo = (
        contract.get("molmospaces_lens")
        if isinstance(contract.get("molmospaces_lens"), dict)
        else {}
    )
    isaac = contract.get("isaac_lens") if isinstance(contract.get("isaac_lens"), dict) else {}
    isaac_derived = (
        contract.get("isaac_derived_lens")
        if isinstance(contract.get("isaac_derived_lens"), dict)
        else {}
    )
    derived = (
        contract.get("derived_from_vertical_fov")
        if isinstance(contract.get("derived_from_vertical_fov"), dict)
        else {}
    )
    rows = [
        ("Requested vertical FOV", f"{requested.get('vertical_fov_deg')} deg"),
        ("Requested focal length", f"{requested.get('focal_length_mm')} mm"),
        ("Requested horizontal aperture", f"{requested.get('horizontal_aperture_mm')} mm"),
        (
            "Derived horizontal aperture",
            f"{_optional_float(derived.get('horizontal_aperture_mm')):.6g} mm"
            if _optional_float(derived.get("horizontal_aperture_mm")) is not None
            else "",
        ),
        (
            "Derived horizontal FOV",
            f"{_optional_float(derived.get('horizontal_fov_deg')):.6g} deg"
            if _optional_float(derived.get("horizontal_fov_deg")) is not None
            else "",
        ),
        ("MuJoCo lens payload", json.dumps(molmo, sort_keys=True)),
        ("Isaac lens payload", json.dumps(isaac, sort_keys=True)),
        ("Isaac derived lens", json.dumps(isaac_derived, sort_keys=True)),
        ("Horizontal aperture delta", _intrinsics_delta_text(contract)),
    ]
    body = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
    )
    note = (
        f"status={contract.get('status')}; "
        f"precedence={contract.get('intrinsics_precedence')}. "
        f"{contract.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Camera Intrinsics Contract</h2>
  <p class="note">{html.escape(note)}</p>
  <div class="table-wrap"><table>
    <thead><tr><th>Field</th><th>Value</th></tr></thead>
    <tbody>{body}</tbody>
  </table></div>
</section>
"""


def _room_scale_section(manifest: dict[str, Any]) -> str:
    contract = (
        manifest.get("room_scale_contract")
        if isinstance(manifest.get("room_scale_contract"), dict)
        else {}
    )
    if not contract:
        return ""
    rows = []
    for room in contract.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(room.get('view_id', '')))}</td>"
            f"<td>{html.escape(str(room.get('room_id', '')))}</td>"
            f"<td>{html.escape(_vec_text(room.get('center')))}</td>"
            f"<td>{html.escape(_vec_text(room.get('size')))}</td>"
            f"<td>{html.escape(str(room.get('provenance', '')))}</td>"
            "</tr>"
        )
    bounds = (
        contract.get("isaac_scene_bounds")
        if isinstance(contract.get("isaac_scene_bounds"), dict)
        else {}
    )
    note = (
        f"status={contract.get('status')}; rooms={contract.get('room_count')}; "
        f"matched_room_outlines={contract.get('matched_room_outline_count')}; "
        f"isaac_scene_size={_vec_text(bounds.get('size'))}; "
        f"max_width_ratio={_ratio_text(contract.get('max_room_to_scene_width_ratio'))}; "
        f"max_depth_ratio={_ratio_text(contract.get('max_room_to_scene_depth_ratio'))}; "
        f"max_center_delta={_meters_text(contract.get('max_room_outline_center_delta_m'))}; "
        f"max_size_delta={_meters_text(contract.get('max_room_outline_size_delta_m'))}; "
        f"threshold={_meters_text(contract.get('room_outline_threshold_m'))}. "
        f"{contract.get('interpretation') or ''}"
    )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in ("View", "Room", "Center", "Size XY", "Provenance")
    )
    return f"""
<section class="panel">
  <h2>Room Scale Contract</h2>
  <p class="note">{html.escape(note)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
  {_room_outline_pairs_table(contract)}
</section>
"""


def _room_outline_pairs_table(contract: dict[str, Any]) -> str:
    pairs = [item for item in contract.get("room_outline_pairs") or [] if isinstance(item, dict)]
    if not pairs:
        return ""
    rows = []
    for item in pairs:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('room_id', '')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('molmospaces_center')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('isaac_center')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('center_delta_m')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('molmospaces_size')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('isaac_size')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('size_delta_m')))}</td>"
            f"<td>{html.escape(str(item.get('isaac_usd_prim_path', '')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "Room",
            "MuJoCo center",
            "Isaac center",
            "Center delta",
            "MuJoCo size",
            "Isaac size",
            "Size delta",
            "Isaac room prim",
        )
    )
    return f"""
  <h3>Matched Room Outlines</h3>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
"""


def _backend_swap_geometry_section(manifest: dict[str, Any]) -> str:
    contract = (
        manifest.get("backend_swap_geometry_contract")
        if isinstance(manifest.get("backend_swap_geometry_contract"), dict)
        else _backend_swap_geometry_contract(manifest)
    )
    if not contract:
        return ""
    rows = []
    for item in contract.get("required_checks") or []:
        if not isinstance(item, dict):
            continue
        detail_parts = []
        for key in (
            "value",
            "expected",
            "max_delta_m",
            "threshold_m",
            "max_center_delta_m",
            "max_size_delta_m",
            "vertical_fov_deg",
            "resolution",
            "max_pixel_delta",
            "threshold_px",
        ):
            value = item.get(key)
            if value is None or value == "":
                continue
            detail_parts.append(f"{key}={value}")
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('check', '')))}</td>"
            f"<td>{html.escape(str(item.get('status', '')))}</td>"
            f"<td>{html.escape('; '.join(detail_parts))}</td>"
            "</tr>"
        )
    headers = "".join(f"<th>{html.escape(label)}</th>" for label in ("Check", "Status", "Evidence"))
    note = (
        f"status={contract.get('status')}; "
        f"geometry={contract.get('geometry_contract_status')}; "
        f"visual_residual={contract.get('visual_residual_status')}; "
        f"target_definition={contract.get('target_definition_status')}; "
        f"max_target_center_residual={_meters_text(contract.get('max_target_center_residual_m'))}; "
        f"mean_pixel_delta={_float_text(contract.get('mean_absolute_pixel_delta'))}; "
        f"mean_luminance_delta={_float_text(contract.get('mean_abs_mean_luminance_delta'))}. "
        f"{contract.get('interpretation') or ''}"
    )
    next_action = str(contract.get("recommended_next_action") or "")
    return f"""
<section class="panel">
  <h2>Backend Swap Geometry Contract</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(next_action)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _intrinsics_delta_text(contract: dict[str, Any]) -> str:
    value = _optional_float(contract.get("requested_vs_derived_horizontal_aperture_delta_mm"))
    return f"{value:.6g} mm" if value is not None else ""


def _pose_contract_section(manifest: dict[str, Any]) -> str:
    contract = (
        manifest.get("camera_pose_contract")
        if isinstance(manifest.get("camera_pose_contract"), dict)
        else {}
    )
    if not contract:
        return ""
    rows = []
    for item in contract.get("pairs") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('anchor_id', '')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('requested_eye')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('requested_target')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('molmospaces_backend_eye')))}</td>"
            f"<td>{html.escape(_vec_text(item.get('isaac_backend_eye')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('backend_eye_delta_m')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('backend_target_delta_m')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "Handle",
            "Requested eye",
            "Requested target",
            "MuJoCo backend eye",
            "Isaac backend eye",
            "Backend eye delta",
            "Backend target delta",
        )
    )
    note = (
        f"status={contract.get('status')}; "
        f"max_pose_delta={_meters_text(contract.get('max_pose_delta_m'))}; "
        f"threshold={_meters_text(contract.get('pose_threshold_m'))}. "
        f"{contract.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Camera Pose Contract</h2>
  <p class="note">{html.escape(note)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
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
            f"<td>{html.escape(_meters_text(item.get('residual_m')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('xy_residual_m')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('z_residual_m')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('distance_to_usd_bounds_m')))}</td>"
            f"<td>{html.escape(_meters_text(item.get('surface_aim_distance_to_usd_bounds_m')))}</td>"
            f"<td>{html.escape(str(item.get('target_inside_usd_xy_bounds')))}</td>"
            f"<td>{html.escape(str(item.get('target_inside_usd_xyz_bounds')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "Handle",
            "Category",
            "Requested camera target",
            "Isaac USD bounds target",
            "Residual",
            "XY residual",
            "Z residual",
            "Distance to USD bounds",
            "Surface-aim distance",
            "Inside XY bounds",
            "Inside XYZ bounds",
        )
    )
    note = (
        f"diagnostic={transform.get('diagnostic_kind')}; "
        f"status={transform.get('status')}; result={transform.get('target_residual_status')}; "
        f"mean={_meters_text(transform.get('mean_residual_m'))}; "
        f"max={_meters_text(transform.get('max_residual_m'))}; "
        f"max_xy={_meters_text(transform.get('max_xy_residual_m'))}; "
        f"max_z={_meters_text(transform.get('max_z_residual_m'))}; "
        f"max_distance_to_bounds={_meters_text(transform.get('max_distance_to_usd_bounds_m'))}; "
        f"max_surface_aim_distance="
        f"{_meters_text(transform.get('max_surface_aim_distance_to_usd_bounds_m'))}; "
        f"inside_xy={transform.get('target_inside_usd_xy_bounds_count')}/"
        f"{transform.get('pair_count')}; "
        f"inside_xyz={transform.get('target_inside_usd_xyz_bounds_count')}/"
        f"{transform.get('pair_count')}. "
        f"{transform.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Target Vs USD Bounds Diagnostics</h2>
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
        "MuJoCo targets use metadata anchor/support surfaces. Isaac support poses are "
        "navigation/placement metadata diagnostics, not camera target coordinates. The "
        "canonical camera request itself carries explicit eye/target/up values, and "
        "USD-bounds residuals are measured after rendering."
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


def _projection_diagnostics_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("projection_diagnostics")
        if isinstance(manifest.get("projection_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    rows = []
    for item in diagnostics.get("pairs") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('anchor_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('point_count', '')))}</td>"
            f"<td>{html.escape(_pixels_text(item.get('max_pixel_delta')))}</td>"
            f"<td>{html.escape(str(item.get('all_points_inside_frame')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "Handle",
            "Projected points",
            "Max pixel delta",
            "All sampled points inside frame",
        )
    )
    note = (
        f"status={diagnostics.get('status')}; views={diagnostics.get('pair_count')}; "
        f"resolution={diagnostics.get('resolution')}; "
        f"vertical_fov={_float_text(diagnostics.get('vertical_fov_deg'))} deg; "
        f"max_pixel_delta={_pixels_text(diagnostics.get('max_pixel_delta'))}; "
        f"threshold={_pixels_text(diagnostics.get('projection_threshold_px'))}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Projection Diagnostics</h2>
  <p class="note">{html.escape(note)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _visual_diagnostics_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("visual_diagnostics")
        if isinstance(manifest.get("visual_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    rows = []
    for item in diagnostics.get("views") or []:
        if not isinstance(item, dict):
            continue
        lanes = item.get("lanes") if isinstance(item.get("lanes"), dict) else {}
        molmo = (
            lanes.get(MOLMOSPACES_LANE_ID)
            if isinstance(lanes.get(MOLMOSPACES_LANE_ID), dict)
            else {}
        )
        isaac = lanes.get(ISAAC_LANE_ID) if isinstance(lanes.get(ISAAC_LANE_ID), dict) else {}
        delta = item.get("delta") if isinstance(item.get("delta"), dict) else {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(_float_text(molmo.get('mean_luminance')))}</td>"
            f"<td>{html.escape(_float_text(isaac.get('mean_luminance')))}</td>"
            f"<td>{html.escape(_float_text(delta.get('mean_luminance_delta')))}</td>"
            f"<td>{html.escape(_float_text(delta.get('mean_absolute_pixel_delta')))}</td>"
            f"<td>{html.escape(_float_text(delta.get('rms_pixel_delta')))}</td>"
            f"<td>{html.escape(_percent_text(molmo.get('overexposed_fraction')))}</td>"
            f"<td>{html.escape(_percent_text(isaac.get('overexposed_fraction')))}</td>"
            f"<td>{html.escape(_percent_text(molmo.get('underexposed_fraction')))}</td>"
            f"<td>{html.escape(_percent_text(isaac.get('underexposed_fraction')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "MuJoCo luminance",
            "Isaac luminance",
            "Luminance delta",
            "Mean pixel delta",
            "RMS pixel delta",
            "MuJoCo overexposed",
            "Isaac overexposed",
            "MuJoCo underexposed",
            "Isaac underexposed",
        )
    )
    note = (
        f"status={diagnostics.get('status')}; "
        f"views={diagnostics.get('view_count')}; "
        f"max_luminance_delta="
        f"{_float_text(diagnostics.get('max_abs_mean_luminance_delta'))}; "
        f"mean_pixel_delta={_float_text(diagnostics.get('mean_absolute_pixel_delta'))}; "
        f"max_overexposed={_percent_text(diagnostics.get('max_overexposed_fraction'))}; "
        f"max_underexposed={_percent_text(diagnostics.get('max_underexposed_fraction'))}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    calibration = (
        diagnostics.get("render_domain_calibration")
        if isinstance(diagnostics.get("render_domain_calibration"), dict)
        else {}
    )
    calibration_note = ""
    if calibration:
        calibration_note = (
            f"Render-domain calibration: status={calibration.get('status')}; "
            f"global_isaac_luminance_gain="
            f"{_float_text(calibration.get('global_isaac_luminance_gain'))}; "
            f"mean_residual="
            f"{_float_text(calibration.get('mean_abs_calibrated_luminance_residual'))}; "
            f"max_residual="
            f"{_float_text(calibration.get('max_abs_calibrated_luminance_residual'))}; "
            f"{calibration.get('recommended_next_action') or ''}"
        )
    replay = (
        diagnostics.get("color_profile_replay")
        if isinstance(diagnostics.get("color_profile_replay"), dict)
        else {}
    )
    replay_note = ""
    if replay:
        replay_calibration = (
            replay.get("render_domain_calibration")
            if isinstance(replay.get("render_domain_calibration"), dict)
            else {}
        )
        replay_note = (
            f"Color-profile replay: status={replay.get('status')}; "
            f"mean_luminance_delta="
            f"{_float_text(replay.get('mean_abs_mean_luminance_delta'))}; "
            f"mean_pixel_delta={_float_text(replay.get('mean_absolute_pixel_delta'))}; "
            f"residual_status={replay_calibration.get('status') or ''}. "
            f"{replay.get('interpretation') or ''}"
        )
    candidates = (
        diagnostics.get("candidate_color_calibrations")
        if isinstance(diagnostics.get("candidate_color_calibrations"), dict)
        else {}
    )
    candidate_note = ""
    if candidates:
        candidate_rows = []
        for item in candidates.get("candidates") or []:
            if not isinstance(item, dict):
                continue
            candidate_rows.append(
                f"{item.get('candidate_id')}("
                f"lum={_float_text(item.get('mean_abs_mean_luminance_delta'))}, "
                f"px={_float_text(item.get('mean_absolute_pixel_delta'))})"
            )
        candidate_note = (
            f"Candidate color calibrations: best={candidates.get('best_candidate')}; "
            f"{'; '.join(candidate_rows)}. {candidates.get('interpretation') or ''}"
        )
    return f"""
<section class="panel">
  <h2>Visual Diagnostics</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(calibration_note)}</p>
  <p class="note">{html.escape(replay_note)}</p>
  <p class="note">{html.escape(candidate_note)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _render_domain_source_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("render_domain_source_diagnostics")
        if isinstance(manifest.get("render_domain_source_diagnostics"), dict)
        else _render_domain_source_diagnostics(manifest)
    )
    if not diagnostics:
        return ""
    rows = []
    for item in diagnostics.get("source_references") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('evidence_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('lane', '')))}</td>"
            f"<td>{html.escape(str(item.get('path', '')))}:"
            f"{html.escape(str(item.get('line_start', '')))}</td>"
            f"<td>{html.escape(str(item.get('status', '')))}</td>"
            f"<td>{html.escape(str(item.get('claim', '')))}</td>"
            f"<td>{html.escape(str(item.get('snippet_summary', '')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in ("Evidence", "Lane", "Source", "Status", "Claim", "Snippet")
    )
    lane_summary = (
        diagnostics.get("lane_summary") if isinstance(diagnostics.get("lane_summary"), dict) else {}
    )
    lane_note = "; ".join(
        f"{lane}: {summary.get('renderer_contract')} ({summary.get('evidence_count')} refs)"
        for lane, summary in lane_summary.items()
        if isinstance(summary, dict)
    )
    note = (
        f"status={diagnostics.get('status')}; "
        f"root_cause={diagnostics.get('root_cause_status')}; "
        f"source_refs={diagnostics.get('available_source_reference_count')}/"
        f"{diagnostics.get('source_reference_count')}; {lane_note}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Render Domain Source Diagnostics</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(diagnostics.get("recommended_next_action") or ""))}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _render_domain_view_triage_section(manifest: dict[str, Any]) -> str:
    triage = (
        manifest.get("render_domain_view_triage")
        if isinstance(manifest.get("render_domain_view_triage"), dict)
        else _render_domain_view_triage(manifest)
    )
    if not triage:
        return ""
    rows = []
    for item in triage.get("views") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('anchor_kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('render_residual_class', '')))}</td>"
            f"<td>{html.escape(_float_text(item.get('mean_absolute_pixel_delta')))}</td>"
            f"<td>{html.escape(_float_text(item.get('abs_mean_luminance_delta')))}</td>"
            f"<td>{html.escape(_pixels_text(item.get('max_projection_delta_px')))}</td>"
            f"<td>{html.escape(str(item.get('suspected_contract', '')))}</td>"
            f"<td>{html.escape(str(item.get('usd_prim_path', '')))}</td>"
            f"<td>{html.escape(str(item.get('next_probe', '')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "Anchor",
            "Residual",
            "Mean pixel delta",
            "Mean luminance delta",
            "Projection delta",
            "Suspected contract",
            "Isaac USD prim",
            "Next probe",
        )
    )
    note = (
        f"status={triage.get('status')}; views={triage.get('view_count')}; "
        f"high_residual_views={triage.get('high_residual_view_count')}; "
        f"top={triage.get('top_residual_view_id')}. "
        f"{triage.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Render Domain View Triage</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(triage.get("recommended_next_action") or ""))}</p>
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
            f"<td>{html.escape(str(_lighting_diagnostics_text(lane)))}</td>"
            f"<td>{html.escape(str(_color_profile_id(lane)))}</td>"
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
            "Lighting diagnostics",
            "Color",
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


def _color_profile_id(lane: dict[str, Any]) -> str:
    color = lane.get("color_profile") if isinstance(lane.get("color_profile"), dict) else {}
    return str(color.get("profile_id") or "")


def _lighting_diagnostics_text(lane: dict[str, Any]) -> str:
    diagnostics = (
        lane.get("lighting_diagnostics")
        if isinstance(lane.get("lighting_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    return (
        f"{diagnostics.get('status')}; "
        f"existing={diagnostics.get('existing_light_count')}; "
        f"added={diagnostics.get('added_light_count')}"
    )


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
    views = [
        item
        for item in manifest.get("canonical_camera_views") or []
        if isinstance(item, dict) and item.get("view_id")
    ]
    if not views:
        views = [
            {
                "view_id": f"view_{index:02d}_{_safe_id(anchor.get('category'))}",
                **anchor,
            }
            for index, anchor in enumerate(
                [item for item in manifest.get("anchors") or [] if isinstance(item, dict)],
                start=1,
            )
        ]
    blocks = []
    for view in views:
        view_id = str(view.get("view_id") or "")
        room = html.escape(str(view.get("room_id") or "scene"))
        category = html.escape(str(view.get("category") or "view"))
        anchor_id = html.escape(str(view.get("anchor_id") or ""))
        basis = html.escape(str(view.get("camera_basis") or ""))
        blocks.append(
            f"""
<section class="panel">
  <h2>{room} {category}</h2>
  <p class="note">{anchor_id} {basis}</p>
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
    if not isinstance(value, list) or len(value) < 2:
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


def _ratio_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _float_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _percent_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value) * 100.0:.2f}%"
    except (TypeError, ValueError):
        return str(value)


def _pixels_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.3f} px"
    except (TypeError, ValueError):
        return str(value)


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


def _short_commit(value: Any) -> str:
    text = str(value or "")
    return text[:12] if text else ""


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
