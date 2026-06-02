from __future__ import annotations

import math
from typing import Any

from roboclaws.household.camera_control import (
    CAMERA_CONTROL_API_NAME,
    CANONICAL_CAMERA_MODEL,
    DEFAULT_SCENE_PROBE_COLOR_PROFILE,
    DEFAULT_SCENE_PROBE_LENS,
    MOLMOSPACES_SCENE_FRAME,
    canonical_scene_camera_control_request,
)

ROBOT_VIEW_CAMERA_CONTROL_CONTRACT_SCHEMA = "robot_view_camera_control_contract_v1"
CANONICAL_ROBOT_VIEW_CAMERA_STATUS = "canonical_camera_control_robot_view"
BACKEND_LOCAL_ROBOT_VIEW_CAMERA_MODEL = "backend_local_robot_view"
ROBOT_MOUNTED_HEAD_CAMERA_MODEL = "robot_mounted_head_camera_v1"
ROBOT_HEAD_CAMERA_EQUIVALENT_MODEL = "robot_head_camera_equivalent_v1"
ROBOT_MOUNTED_HEAD_CAMERA_STATUS = "robot_mounted_head_camera_robot_view"
ROBOT_HEAD_CAMERA_EQUIVALENT_STATUS = "robot_head_camera_equivalent_robot_view"

ROBOT_FPV_EYE_HEIGHT_M = 1.55
ROBOT_FPV_FORWARD_DISTANCE_M = 2.0
VERIFY_CAMERA_DISTANCE_M = 2.4
VERIFY_CAMERA_ELEVATION_DEG = 58.0


def canonical_cleanup_robot_view_camera_request(
    *,
    label: str,
    robot_pose: dict[str, Any] | None,
    focus: dict[str, Any] | None,
    width: int,
    height: int,
    current_target_position: list[float] | tuple[float, ...] | None = None,
    scene_focus_position: list[float] | tuple[float, ...] | None = None,
) -> dict[str, Any] | None:
    """Build canonical FPV/verify views for cleanup robot-view capture.

    The request is intentionally based on explicit eye/target/up values, not on a
    backend-local named robot camera. Auxiliary chase/map report views may still
    come from backend-specific renderers.
    """

    pose = robot_pose if isinstance(robot_pose, dict) else {}
    if not _has_xy(pose):
        return None
    safe_label = _safe_id(label)
    fpv_eye = [float(pose["x"]), float(pose["y"]), _pose_z(pose) + ROBOT_FPV_EYE_HEIGHT_M]
    fpv_target = _fpv_target(
        pose,
        focus=focus,
        eye=fpv_eye,
        current_target_position=current_target_position,
        scene_focus_position=scene_focus_position,
    )
    verify_target = _target_from_focus(
        focus,
        current_target_position=current_target_position,
        scene_focus_position=scene_focus_position,
        default=fpv_target,
    )
    verify_eye = _verify_eye_from_pose(
        pose,
        target=verify_target,
    )
    return canonical_scene_camera_control_request(
        [
            {
                "view_id": f"{safe_label}_fpv",
                "label": f"{label} canonical FPV",
                "robot_view_role": "fpv",
                "camera_mode": "canonical_robot_fpv",
                "camera_basis": "robot_pose_eye_target",
                "eye": fpv_eye,
                "target": fpv_target,
            },
            {
                "view_id": f"{safe_label}_verify",
                "label": f"{label} canonical verify",
                "robot_view_role": "verify",
                "camera_mode": "canonical_robot_verify",
                "camera_basis": "robot_pose_focus_orbit",
                "eye": verify_eye,
                "target": verify_target,
            },
        ],
        width=width,
        height=height,
        lens=DEFAULT_SCENE_PROBE_LENS,
    )


def canonical_robot_view_camera_control_contract(
    *,
    backend: str,
    pose_source: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    views = [item for item in request.get("views") or [] if isinstance(item, dict)]
    fpv = next((item for item in views if item.get("robot_view_role") == "fpv"), {})
    verify = next((item for item in views if item.get("robot_view_role") == "verify"), {})
    return {
        "schema": ROBOT_VIEW_CAMERA_CONTROL_CONTRACT_SCHEMA,
        "backend": backend,
        "status": CANONICAL_ROBOT_VIEW_CAMERA_STATUS,
        "camera_control_api": request.get("api_name") or CAMERA_CONTROL_API_NAME,
        "camera_model": CANONICAL_CAMERA_MODEL,
        "coordinate_frame": request.get("coordinate_frame") or MOLMOSPACES_SCENE_FRAME,
        "same_pose_api": True,
        "agent_facing_fpv": {
            "source": "canonical_eye_target_robot_pose",
            "canonical_camera_control": True,
            "eye": fpv.get("eye"),
            "target": fpv.get("target"),
        },
        "report_verify_view": {
            "source": "canonical_eye_target_robot_verify",
            "canonical_camera_control": True,
            "eye": verify.get("eye"),
            "target": verify.get("target"),
        },
        "pose_source": pose_source,
        "lens_source": "roboclaws_camera_control_lens",
        "lens": dict(request.get("lens") or {}),
        "lighting_profile": dict(request.get("lighting_profile") or {}),
        "color_profile": dict(request.get("color_profile") or {}),
        "render_resolution": dict(request.get("render_resolution") or {}),
        "evidence_note": (
            "Agent-facing FPV and verify views were rendered from the Roboclaws "
            "canonical eye/target camera-control request. Chase/map views remain "
            "report-only auxiliary evidence."
        ),
    }


def backend_local_robot_view_camera_control_contract(
    *,
    backend: str,
    status: str,
    fpv_source: str,
    verify_source: str,
    pose_source: str,
    lens_source: str,
) -> dict[str, Any]:
    return {
        "schema": ROBOT_VIEW_CAMERA_CONTROL_CONTRACT_SCHEMA,
        "backend": backend,
        "status": status,
        "camera_control_api": None,
        "camera_model": BACKEND_LOCAL_ROBOT_VIEW_CAMERA_MODEL,
        "same_pose_api": False,
        "agent_facing_fpv": {
            "source": fpv_source,
            "canonical_camera_control": False,
        },
        "report_verify_view": {
            "source": verify_source,
            "canonical_camera_control": False,
        },
        "pose_source": pose_source,
        "lens_source": lens_source,
        "evidence_note": (
            "Cleanup robot views are generated by backend-local robot/report cameras, "
            "not by roboclaws.camera_control.render_views. Scene-camera parity does "
            "not by itself prove raw-FPV cleanup parity."
        ),
    }


def robot_mounted_head_camera_control_contract(
    *,
    backend: str,
    fpv_source: str,
    verify_source: str,
    pose_source: str,
    lens_source: str,
    camera_model: str = ROBOT_MOUNTED_HEAD_CAMERA_MODEL,
    status: str = ROBOT_MOUNTED_HEAD_CAMERA_STATUS,
    camera_prim_path: str | None = None,
    robot_asset: dict[str, Any] | None = None,
    same_pose_api: bool = False,
    robot_pose: dict[str, Any] | None = None,
    focus: dict[str, Any] | None = None,
    lighting_profile: dict[str, Any] | None = None,
    color_profile: dict[str, Any] | None = None,
    color_management: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe FPV rendered from a real/equivalent robot head camera.

    ``same_pose_api`` is intentionally false for backend-native robot cameras:
    parity comes from the mounted camera contract, not the free-camera render API.
    """

    contract = {
        "schema": ROBOT_VIEW_CAMERA_CONTROL_CONTRACT_SCHEMA,
        "backend": backend,
        "status": status,
        "camera_control_api": None,
        "camera_model": camera_model,
        "same_pose_api": same_pose_api,
        "agent_facing_fpv": {
            "source": fpv_source,
            "canonical_camera_control": False,
            "robot_mounted": camera_model == ROBOT_MOUNTED_HEAD_CAMERA_MODEL,
            "head_camera_equivalent": camera_model == ROBOT_HEAD_CAMERA_EQUIVALENT_MODEL,
        },
        "report_verify_view": {
            "source": verify_source,
            "canonical_camera_control": False,
        },
        "pose_source": pose_source,
        "lens_source": lens_source,
        "evidence_note": (
            "Agent-facing FPV is rendered from a robot head camera or an explicitly "
            "declared head-camera equivalent. Chase/map views remain report-only "
            "auxiliary evidence."
        ),
    }
    if camera_prim_path:
        contract["camera_prim_path"] = camera_prim_path
        contract["agent_facing_fpv"]["camera_prim_path"] = camera_prim_path
    if robot_asset:
        contract["robot_asset"] = dict(robot_asset)
    if robot_pose:
        contract["robot_pose"] = dict(robot_pose)
    if focus:
        contract["focus"] = dict(focus)
    if lighting_profile:
        contract["lighting_profile"] = dict(lighting_profile)
    if color_profile:
        contract["color_profile"] = dict(color_profile)
    if color_management:
        contract["color_management"] = dict(color_management)
    return contract


def robot_view_display_color_profile() -> dict[str, Any]:
    """Return the shared display profile for backend-local robot-view images."""

    return dict(DEFAULT_SCENE_PROBE_COLOR_PROFILE)


def _fpv_target(
    pose: dict[str, Any],
    *,
    focus: dict[str, Any] | None,
    eye: list[float],
    current_target_position: list[float] | tuple[float, ...] | None,
    scene_focus_position: list[float] | tuple[float, ...] | None,
) -> list[float]:
    focus_target = _target_from_focus(
        focus,
        current_target_position=current_target_position,
        scene_focus_position=scene_focus_position,
        default=None,
    )
    if focus_target is not None:
        return focus_target
    theta = _pose_theta(pose)
    pitch = _pose_head_pitch(pose)
    distance = ROBOT_FPV_FORWARD_DISTANCE_M
    return [
        eye[0] + math.cos(theta) * distance,
        eye[1] + math.sin(theta) * distance,
        eye[2] - math.tan(pitch) * distance,
    ]


def _target_from_focus(
    focus: dict[str, Any] | None,
    *,
    current_target_position: list[float] | tuple[float, ...] | None,
    scene_focus_position: list[float] | tuple[float, ...] | None,
    default: list[float] | None,
) -> list[float] | None:
    focus_payload = focus if isinstance(focus, dict) else {}
    for value in (
        focus_payload.get("focus_position"),
        current_target_position,
        scene_focus_position,
    ):
        target = _vec3(value)
        if target is not None:
            target[2] += 0.2
            return target
    return list(default) if default is not None else None


def _verify_eye_from_pose(
    pose: dict[str, Any],
    *,
    target: list[float],
) -> list[float]:
    theta = _pose_theta(pose)
    azimuth = math.degrees(theta + math.pi)
    elevation = math.radians(VERIFY_CAMERA_ELEVATION_DEG)
    horizontal = math.cos(elevation) * VERIFY_CAMERA_DISTANCE_M
    return [
        target[0] + math.cos(math.radians(azimuth)) * horizontal,
        target[1] + math.sin(math.radians(azimuth)) * horizontal,
        target[2] + math.sin(elevation) * VERIFY_CAMERA_DISTANCE_M,
    ]


def _pose_theta(pose: dict[str, Any]) -> float:
    if "theta" in pose:
        return float(pose["theta"])
    if "yaw_deg" in pose:
        return math.radians(float(pose["yaw_deg"]))
    return 0.0


def _pose_head_pitch(pose: dict[str, Any]) -> float:
    try:
        return float(pose.get("head_pitch", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _pose_z(pose: dict[str, Any]) -> float:
    try:
        return float(pose.get("z", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _has_xy(pose: dict[str, Any]) -> bool:
    return "x" in pose and "y" in pose


def _vec3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def _safe_id(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return safe or "robot_view"
