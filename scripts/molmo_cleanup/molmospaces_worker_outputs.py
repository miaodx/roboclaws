from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import mujoco
from PIL import Image

from roboclaws.household.camera_control import (
    CAMERA_CONTROL_API_NAME,
    CANONICAL_CAMERA_MODEL,
    normalize_camera_control_request,
)
from roboclaws.household.color_management import apply_camera_color_profile
from roboclaws.household.robot_view_camera_control import (
    robot_mounted_head_camera_control_contract,
    robot_view_display_color_profile,
)


@dataclass(frozen=True)
class MolmoWorkerOutputHooks:
    apply_qpos: Callable[..., Any]
    apply_robot_view_camera_offset: Callable[..., dict[str, Any]]
    annotate_focus_image: Callable[..., Any]
    annotate_focus_visual_grounding: Callable[..., dict[str, Any]]
    camera_from_view_spec: Callable[..., Any]
    camera_request_provenance: Callable[..., str]
    camera_request_variant: Callable[..., str]
    camera_view_spec: Callable[..., dict[str, Any]]
    count: Callable[..., Any]
    error: Callable[..., dict[str, Any]]
    fixed_camera_diagnostics: Callable[..., dict[str, Any]]
    focus_camera: Callable[..., Any]
    focus_payload: Callable[..., dict[str, Any]]
    focus_visibility: Callable[..., dict[str, Any]]
    free_camera_diagnostics: Callable[..., dict[str, Any]]
    load_model_data_for_state: Callable[..., tuple[Any, Any]]
    ok: Callable[..., dict[str, Any]]
    refresh_object_positions: Callable[..., Any]
    render_camera_views_with_model_data: Callable[..., dict[str, Any]]
    render_dimensions: Callable[..., tuple[int, int]]
    render_fixed_camera: Callable[..., Any]
    render_free_camera: Callable[..., Any]
    render_robot_map: Callable[..., Image.Image]
    should_use_fpv_as_verify_focus: Callable[..., bool]
    backend: str


def write_snapshot(
    state: dict[str, Any],
    output_path: Path,
    title: str,
    *,
    width: int,
    height: int,
    hooks: MolmoWorkerOutputHooks,
) -> dict[str, Any]:
    width, height = hooks.render_dimensions(width, height)
    model, data = hooks.load_model_data_for_state(state)
    hooks.apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, height=height, width=width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = [8.5, 6.5, 0.8]
    camera.distance = 9.5
    camera.azimuth = 225
    camera.elevation = -45
    renderer.update_scene(data, camera=camera)
    frame = renderer.render()
    renderer.close()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame).save(output_path)
    return hooks.ok("snapshot", path=str(output_path), title=title, shape=list(frame.shape))


def write_robot_views(
    state: dict[str, Any],
    output_dir: Path,
    label: str,
    *,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
    camera_yaw_offset_deg: float = 0.0,
    camera_pitch_offset_deg: float = 0.0,
    width: int,
    height: int,
    hooks: MolmoWorkerOutputHooks,
) -> dict[str, Any]:
    width, height = hooks.render_dimensions(width, height)
    hooks.count(state, "robot_views")
    if not state.get("robot_included"):
        return hooks.error("robot_views", "robot_not_included")
    if focus_object_id is not None and focus_object_id not in state["objects"]:
        return hooks.error("robot_views", "stale_reference", object_id=focus_object_id)
    if focus_receptacle_id is not None and focus_receptacle_id not in state["receptacles"]:
        return hooks.error("robot_views", "stale_reference", receptacle_id=focus_receptacle_id)
    model, data = hooks.load_model_data_for_state(state)
    hooks.apply_qpos(data, state["qpos"])
    camera_adjustment = hooks.apply_robot_view_camera_offset(
        model,
        data,
        yaw_offset_deg=camera_yaw_offset_deg,
        pitch_offset_deg=camera_pitch_offset_deg,
    )
    mujoco.mj_forward(model, data)
    hooks.refresh_object_positions(model, data, state)

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_label = safe_file_stem(label)
    fpv_path = output_dir / f"{safe_label}.fpv.png"
    chase_path = output_dir / f"{safe_label}.chase.png"
    map_path = output_dir / f"{safe_label}.map.png"
    verify_path = output_dir / f"{safe_label}.verify.png"

    focus = hooks.focus_payload(state, focus_object_id, focus_receptacle_id)
    fpv = hooks.render_fixed_camera(model, data, "robot_0/head_camera", width=width, height=height)
    verify_camera = hooks.focus_camera(state, focus)
    verify = hooks.render_free_camera(model, data, verify_camera, width=width, height=height)
    chase = hooks.render_fixed_camera(
        model,
        data,
        "robot_0/camera_follower",
        width=width,
        height=height,
    )
    camera_diagnostics = {
        "schema": "mujoco_robot_view_camera_diagnostics_v1",
        "backend": hooks.backend,
        "render_resolution": {"width": width, "height": height},
        "camera_adjustment": camera_adjustment,
        "views": {
            "fpv": hooks.fixed_camera_diagnostics(model, data, "robot_0/head_camera"),
            "chase": hooks.fixed_camera_diagnostics(model, data, "robot_0/camera_follower"),
            "verify": hooks.free_camera_diagnostics(verify_camera),
        },
    }
    fpv_camera = "robot_0/head_camera"
    focus["fpv_visibility"] = hooks.focus_visibility(
        model,
        data,
        fpv_camera,
        focus,
        frame=fpv,
    )
    focus["visibility"] = hooks.focus_visibility(
        model,
        data,
        verify_camera,
        focus,
        frame=verify,
    )
    focus = hooks.annotate_focus_visual_grounding(focus)
    if hooks.should_use_fpv_as_verify_focus(focus):
        verify = fpv.copy()
        fallback_visibility = dict(focus["fpv_visibility"])
        fallback_visibility["fallback_source"] = "fpv_focus_visibility"
        fallback_visibility.setdefault(
            "evidence_note",
            "Verify frame reused FPV because the closeup camera missed the focused object.",
        )
        focus["visibility"] = fallback_visibility
    color_profile = robot_view_display_color_profile()
    import numpy as np

    color_management: dict[str, dict[str, Any]] = {}
    fpv, color_management["fpv"] = apply_camera_color_profile(
        fpv,
        np=np,
        profile=color_profile,
        backend=hooks.backend,
        view_id="fpv",
    )
    chase, color_management["chase"] = apply_camera_color_profile(
        chase,
        np=np,
        profile=color_profile,
        backend=hooks.backend,
        view_id="chase",
    )
    verify, color_management["verify"] = apply_camera_color_profile(
        verify,
        np=np,
        profile=color_profile,
        backend=hooks.backend,
        view_id="verify",
    )
    camera_control_contract = robot_mounted_head_camera_control_contract(
        backend="molmospaces-mujoco",
        fpv_source="robot_0/head_camera",
        verify_source="mujoco_focus_camera",
        chase_source="robot_0/camera_follower",
        pose_source="rby1m_robot_qpos",
        lens_source="mujoco_model_camera_defaults",
        robot_pose=dict(state.get("robot_pose") or {}),
        focus=focus,
        color_profile=color_profile,
        color_management=color_management,
    )
    camera_control_contract["camera_adjustment"] = camera_adjustment
    camera_control_contract["agent_facing_fpv"]["camera_adjustment"] = camera_adjustment
    Image.fromarray(fpv).save(fpv_path)
    Image.fromarray(chase).save(chase_path)
    verify_image = Image.fromarray(verify)
    hooks.annotate_focus_image(verify_image, focus)
    verify_image.save(verify_path)
    hooks.render_robot_map(state, focus=focus).save(map_path)

    return hooks.ok(
        "robot_views",
        backend=hooks.backend,
        robot_name=state.get("robot_name"),
        robot_pose=state.get("robot_pose"),
        robot_trajectory=state.get("robot_trajectory", []),
        view_variant="molmospaces-rby1m-fpv-map-chase-verify",
        view_provenance=state.get("robot_view_provenance", {}),
        camera_control_contract=camera_control_contract,
        camera_diagnostics=camera_diagnostics,
        camera_adjustment=camera_adjustment,
        color_profile=color_profile,
        color_management=color_management,
        focus=focus,
        room_outline_count=len(state.get("room_outlines", [])),
        views={
            "fpv": str(fpv_path),
            "chase": str(chase_path),
            "map": str(map_path),
            "verify": str(verify_path),
        },
        shapes={
            "fpv": list(fpv.shape),
            "chase": list(chase.shape),
            "verify": list(verify.shape),
            "map": [420, 620, 3],
        },
        render_resolution={"width": width, "height": height},
    )


def robot_view_camera_adjustment(
    *,
    camera_yaw_offset_deg: float = 0.0,
    camera_pitch_offset_deg: float = 0.0,
    applied_joints: list[str] | None = None,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    yaw = round(float(camera_yaw_offset_deg), 3)
    pitch = round(float(camera_pitch_offset_deg), 3)
    requested = bool(yaw or pitch)
    applied_joints = list(applied_joints or [])
    applied = requested and bool(applied_joints) and unavailable_reason is None
    if not requested:
        apply_status = "not_requested"
    elif applied:
        apply_status = "robot_head_joints_render_only"
    elif unavailable_reason:
        apply_status = "unavailable"
    else:
        apply_status = "no_matching_mujoco_head_joints"
    return {
        "schema": "robot_view_camera_adjustment_v1",
        "yaw_delta_deg": yaw,
        "pitch_delta_deg": pitch,
        "requested": requested,
        "applied": applied,
        "apply_status": apply_status,
        "applied_joints": applied_joints,
        "unavailable_reason": unavailable_reason,
        "evidence_note": (
            "Camera offset requests are applied to robot head joints for this render "
            "without persisting the adjusted qpos to worker state."
        ),
    }


def write_camera_views(
    state: dict[str, Any],
    output_dir: Path,
    camera_request: dict[str, Any] | list[dict[str, Any]],
    *,
    width: int,
    height: int,
    hooks: MolmoWorkerOutputHooks,
) -> dict[str, Any]:
    hooks.count(state, "camera_views")
    camera_request = normalize_camera_control_request(camera_request, width=width, height=height)
    resolution = camera_request["render_resolution"]
    width, height = hooks.render_dimensions(resolution["width"], resolution["height"])
    model, data = hooks.load_model_data_for_state(state)
    hooks.apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    hooks.refresh_object_positions(model, data, state)
    return hooks.render_camera_views_with_model_data(
        model,
        data,
        state=state,
        output_dir=output_dir,
        camera_request=camera_request,
        width=width,
        height=height,
    )


def render_camera_views_with_model_data(
    model: Any,
    data: Any,
    *,
    state: dict[str, Any],
    output_dir: Path,
    camera_request: dict[str, Any] | list[dict[str, Any]],
    width: int,
    height: int,
    hooks: MolmoWorkerOutputHooks,
) -> dict[str, Any]:
    camera_request = normalize_camera_control_request(camera_request, width=width, height=height)
    resolution = camera_request["render_resolution"]
    width, height = hooks.render_dimensions(resolution["width"], resolution["height"])
    lens = camera_request.get("lens") if isinstance(camera_request.get("lens"), dict) else {}
    previous_fovy = float(model.vis.global_.fovy)
    model.vis.global_.fovy = float(lens.get("vertical_fov_deg", previous_fovy))
    output_dir.mkdir(parents=True, exist_ok=True)
    color_profile = camera_request.get("color_profile") or {}

    try:
        saved: dict[str, str] = {}
        shapes: dict[str, list[int]] = {}
        color_diagnostics: dict[str, dict[str, Any]] = {}
        views: list[dict[str, Any]] = []
        for index, raw_spec in enumerate(camera_request.get("views") or [], start=1):
            spec = hooks.camera_view_spec(raw_spec, index=index)
            camera = hooks.camera_from_view_spec(state, spec)
            frame = hooks.render_free_camera(model, data, camera, width=width, height=height)
            import numpy as np

            frame, color_diagnostic = apply_camera_color_profile(
                frame,
                np=np,
                profile=color_profile,
                backend="molmospaces-mujoco",
                view_id=str(spec["view_id"]),
            )
            output_path = output_dir / f"{spec['view_id']}.png"
            Image.fromarray(frame).save(output_path)
            saved[str(spec["view_id"])] = str(output_path)
            shapes[str(spec["view_id"])] = list(frame.shape)
            color_diagnostics[str(spec["view_id"])] = color_diagnostic
            views.append(
                {
                    **spec,
                    "image_path": str(output_path),
                    "shape": list(frame.shape),
                }
            )
    finally:
        model.vis.global_.fovy = previous_fovy
    return hooks.ok(
        "camera_views",
        backend=hooks.backend,
        camera_control_api=camera_request.get("api_name") or CAMERA_CONTROL_API_NAME,
        camera_request_schema=camera_request.get("schema"),
        calibration_status=camera_request.get("calibration_status"),
        lighting_profile=camera_request.get("lighting_profile") or {},
        color_profile=color_profile,
        color_management=color_diagnostics,
        lens=camera_request.get("lens") or {},
        view_variant=hooks.camera_request_variant(camera_request),
        visual_artifact_provenance=hooks.camera_request_provenance(camera_request),
        views=views,
        images=saved,
        shapes=shapes,
        render_resolution={"width": width, "height": height},
    )


def camera_request_variant(camera_request: dict[str, Any]) -> str:
    if camera_request.get("camera_model") == CANONICAL_CAMERA_MODEL:
        return "molmospaces-canonical-eye-target-camera-control-v1"
    return "molmospaces-anchor-orbit-camera-control-v1"


def camera_request_provenance(camera_request: dict[str, Any]) -> str:
    if camera_request.get("camera_model") == CANONICAL_CAMERA_MODEL:
        return "mujoco_camera_control_canonical_eye_target"
    return "mujoco_camera_control_anchor_orbit"


def safe_file_stem(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
