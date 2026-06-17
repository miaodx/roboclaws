from __future__ import annotations

import math
from typing import Any


def robot_camera_contract(
    *,
    mujoco_lane_id: str,
    isaac_lane_id: str,
) -> dict[str, Any]:
    return {
        "fpv": {
            mujoco_lane_id: "robot_0/head_camera",
            isaac_lane_id: "/World/robot_0/head_camera",
        },
        "chase": {
            mujoco_lane_id: "robot_0/camera_follower",
            isaac_lane_id: "robot_relative_camera_follower",
        },
        "policy_input_note": "FPV is the robot camera. Chase is report evidence only.",
    }


def refresh_location_camera_contract_diagnostics(locations: list[dict[str, Any]]) -> None:
    for item in locations:
        if not isinstance(item, dict) or item.get("status") != "success":
            continue
        item["camera_contract_diagnostics"] = location_camera_contract_diagnostics(item)


def camera_contract_diagnostics(locations: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics = [
        location_camera_contract_diagnostics(item)
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


def location_camera_contract_diagnostics(item: dict[str, Any]) -> dict[str, Any]:
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
        "chase_contract": chase_contract_diagnostics(mujoco_contract, isaac_contract),
    }


def chase_contract_diagnostics(
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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
