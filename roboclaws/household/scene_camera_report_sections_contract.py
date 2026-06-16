from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from roboclaws.household import scene_camera_lighting_diagnostics, scene_camera_render_domain
from roboclaws.household.scene_camera_report_format import (
    ISAAC_LANE_ID,
    MOLMOSPACES_LANE_ID,
    _badges,
    _dimension_text,
    _float_text,
    _image_button,
    _meters_text,
    _optional_float,
    _pixels_text,
    _ratio_text,
    _short_commit,
    _vec_text,
)

_backend_swap_geometry_contract = scene_camera_render_domain.backend_swap_geometry_contract
_isaac_lighting_summary = scene_camera_lighting_diagnostics.isaac_lighting_summary
_mujoco_lighting_summary = scene_camera_lighting_diagnostics.mujoco_lighting_summary
_generic_lighting_summary = scene_camera_lighting_diagnostics.generic_lighting_summary


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
  {_image_button(path, "MuJoCo and Isaac view contact sheet", css_class="contact-sheet")}
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
            f"<td>{html.escape(str(_lighting_diagnostics_text(lane, lane_id=str(lane_id))))}</td>"
            f"<td>{html.escape(str(_color_profile_id(lane)))}</td>"
            f"<td>{html.escape(str(_native_render_status(lane)))}</td>"
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
            "Native render",
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


def _native_render_status(lane: dict[str, Any]) -> str:
    diagnostics = (
        lane.get("native_render_diagnostics")
        if isinstance(lane.get("native_render_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    return str(diagnostics.get("status") or "")


def _lighting_diagnostics_text(lane: dict[str, Any], *, lane_id: str = "") -> str:
    diagnostics = (
        lane.get("lighting_diagnostics")
        if isinstance(lane.get("lighting_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    lighting = (
        lane.get("lighting_profile") if isinstance(lane.get("lighting_profile"), dict) else {}
    )
    if lane_id == ISAAC_LANE_ID:
        return _isaac_lighting_summary(diagnostics, lighting)["summary"]
    if lane_id == MOLMOSPACES_LANE_ID:
        return _mujoco_lighting_summary({"lanes": {lane_id: lane}}, lighting)["summary"]
    return _generic_lighting_summary(diagnostics, lighting)["summary"]


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
