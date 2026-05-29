from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CAMERA_CONTROL_REQUEST_SCHEMA = "roboclaws_camera_control_request_v1"
CAMERA_CONTROL_API_NAME = "roboclaws.camera_control.render_views"
ANCHOR_ORBIT_CAMERA_MODEL = "anchor_orbit_lookat_camera_v1"
CANONICAL_CAMERA_MODEL = "canonical_eye_target_camera_v1"
WORLD_Z_UP_ORBIT_CONVENTION = "world_z_up_anchor_orbit_v1"
MOLMOSPACES_SCENE_FRAME = "molmospaces_scene_frame_v1"
ANCHOR_ORBIT_CALIBRATION = "anchor_orbit_relative_calibrated_v1"
CANONICAL_POSE_CALIBRATION = "canonical_scene_frame_similarity_fit_v1"

DEFAULT_SCENE_PROBE_CAMERA_ORBIT = {
    "distance_m": 4.4,
    "azimuth_deg": 225.0,
    "elevation_deg": 28.0,
}
DEFAULT_SCENE_PROBE_LENS = {
    "vertical_fov_deg": 45.0,
    "focal_length_mm": 24.0,
}
DEFAULT_SCENE_PROBE_LIGHTING_PROFILE = {
    "profile_id": "scene_probe_existing_usd_lights_v1",
    "isaac_dome_intensity": 0.0,
    "isaac_key_intensity": 0.0,
    "isaac_key_rotation_deg": [-55.0, 0.0, 35.0],
}
DEFAULT_SCENE_PROBE_COLOR_PROFILE = {
    "profile_id": "display_srgb_soft_highlight_v1",
    "input_transfer": "renderer_rgb",
    "output_transfer": "srgb_uint8",
    "highlight_knee": 225.0,
    "highlight_compression": 0.55,
    "gamma": 1.0,
    "backend_luminance_gain": {
        "molmospaces-mujoco": 1.0,
        "molmospaces_subprocess": 1.0,
        "isaaclab-prepared-usd": 0.7161647108631373,
        "isaaclab_subprocess": 0.7161647108631373,
    },
    "backend_luminance_gain_source": (
        "output/molmo/scene-camera-comparison/0530_0009/comparison_manifest.json"
    ),
}


def scene_probe_camera_control_request(
    views: list[dict[str, Any]],
    *,
    width: int,
    height: int,
    camera_orbit: dict[str, Any] | None = None,
    lens: dict[str, Any] | None = None,
    lighting_profile: dict[str, Any] | None = None,
    color_profile: dict[str, Any] | None = None,
    calibration_status: str = ANCHOR_ORBIT_CALIBRATION,
) -> dict[str, Any]:
    """Build the public Roboclaws camera-control request used by scene probes."""

    orbit = _camera_orbit(camera_orbit)
    lens_payload = _camera_lens(lens)
    lighting = _lighting_profile(lighting_profile)
    color = _color_profile(color_profile)
    normalized_views = []
    for index, raw_view in enumerate(views, start=1):
        view = dict(raw_view)
        view.setdefault("view_id", f"view_{index:02d}")
        view.setdefault("label", str(view["view_id"]))
        view.setdefault("camera_model", ANCHOR_ORBIT_CAMERA_MODEL)
        view.setdefault("camera_orbit", dict(orbit))
        view.setdefault("lens", dict(lens_payload))
        view.setdefault("calibration_status", calibration_status)
        view.setdefault("coordinate_convention", WORLD_Z_UP_ORBIT_CONVENTION)
        normalized_views.append(view)
    return {
        "schema": CAMERA_CONTROL_REQUEST_SCHEMA,
        "api_name": CAMERA_CONTROL_API_NAME,
        "camera_model": ANCHOR_ORBIT_CAMERA_MODEL,
        "coordinate_convention": WORLD_Z_UP_ORBIT_CONVENTION,
        "calibration_status": calibration_status,
        "render_resolution": {
            "width": _positive_int(width),
            "height": _positive_int(height),
        },
        "camera_orbit": orbit,
        "lens": lens_payload,
        "lighting_profile": lighting,
        "color_profile": color,
        "views": normalized_views,
    }


def canonical_scene_camera_control_request(
    views: list[dict[str, Any]],
    *,
    width: int,
    height: int,
    lens: dict[str, Any] | None = None,
    lighting_profile: dict[str, Any] | None = None,
    color_profile: dict[str, Any] | None = None,
    scene_frame: str = MOLMOSPACES_SCENE_FRAME,
    calibration_status: str = CANONICAL_POSE_CALIBRATION,
) -> dict[str, Any]:
    """Build a camera request whose primary contract is explicit eye/target/up."""

    lens_payload = _camera_lens(lens)
    lighting = _lighting_profile(lighting_profile)
    color = _color_profile(color_profile)
    normalized_views = []
    for index, raw_view in enumerate(views, start=1):
        view = dict(raw_view)
        view.setdefault("view_id", f"view_{index:02d}")
        view.setdefault("label", str(view["view_id"]))
        view["camera_model"] = CANONICAL_CAMERA_MODEL
        view["coordinate_frame"] = scene_frame
        view["coordinate_convention"] = scene_frame
        view.setdefault("up", [0.0, 0.0, 1.0])
        view.setdefault("lens", dict(lens_payload))
        view.setdefault("calibration_status", calibration_status)
        normalized_views.append(view)
    return {
        "schema": CAMERA_CONTROL_REQUEST_SCHEMA,
        "api_name": CAMERA_CONTROL_API_NAME,
        "camera_model": CANONICAL_CAMERA_MODEL,
        "coordinate_frame": scene_frame,
        "coordinate_convention": scene_frame,
        "calibration_status": calibration_status,
        "render_resolution": {
            "width": _positive_int(width),
            "height": _positive_int(height),
        },
        "lens": lens_payload,
        "lighting_profile": lighting,
        "color_profile": color,
        "views": normalized_views,
    }


def normalize_camera_control_request(
    payload: dict[str, Any] | list[dict[str, Any]],
    *,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """Normalize legacy view lists into the public camera-control request shape."""

    if isinstance(payload, list):
        return scene_probe_camera_control_request(
            [dict(item) for item in payload if isinstance(item, dict)],
            width=width or 1,
            height=height or 1,
        )
    if not isinstance(payload, dict):
        raise ValueError("camera control request must be an object or a view list")
    raw_views = payload.get("views")
    if not isinstance(raw_views, list):
        raise ValueError("camera control request must include a views list")
    request = dict(payload)
    resolution = dict(request.get("render_resolution") or {})
    request["render_resolution"] = {
        "width": _positive_int(width if width is not None else resolution.get("width", 1)),
        "height": _positive_int(height if height is not None else resolution.get("height", 1)),
    }
    request.setdefault("schema", CAMERA_CONTROL_REQUEST_SCHEMA)
    request.setdefault("api_name", CAMERA_CONTROL_API_NAME)
    request.setdefault("camera_model", ANCHOR_ORBIT_CAMERA_MODEL)
    if request.get("camera_model") == CANONICAL_CAMERA_MODEL:
        request.setdefault("coordinate_frame", MOLMOSPACES_SCENE_FRAME)
        request.setdefault("coordinate_convention", request["coordinate_frame"])
    else:
        request.setdefault("coordinate_convention", WORLD_Z_UP_ORBIT_CONVENTION)
        request["camera_orbit"] = _camera_orbit(request.get("camera_orbit"))
    request["lens"] = _camera_lens(request.get("lens"))
    request["lighting_profile"] = _lighting_profile(request.get("lighting_profile"))
    request["color_profile"] = _color_profile(request.get("color_profile"))
    default_calibration = (
        CANONICAL_POSE_CALIBRATION
        if request.get("camera_model") == CANONICAL_CAMERA_MODEL
        else ANCHOR_ORBIT_CALIBRATION
    )
    calibration_status = str(request.get("calibration_status") or default_calibration)
    request["calibration_status"] = calibration_status
    request["views"] = [
        _normalize_view(item, index=index, request=request)
        for index, item in enumerate(raw_views, start=1)
        if isinstance(item, dict)
    ]
    return request


def load_camera_control_request(
    path: Path,
    *,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_camera_control_request(payload, width=width, height=height)


def write_camera_control_request(path: Path, request: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def camera_request_resolution(request: dict[str, Any]) -> tuple[int, int]:
    normalized = normalize_camera_control_request(request)
    resolution = normalized["render_resolution"]
    return int(resolution["width"]), int(resolution["height"])


def _normalize_view(
    raw_view: dict[str, Any],
    *,
    index: int,
    request: dict[str, Any],
) -> dict[str, Any]:
    view = dict(raw_view)
    view.setdefault("view_id", f"view_{index:02d}")
    view.setdefault("label", str(view["view_id"]))
    view.setdefault("camera_model", request.get("camera_model") or ANCHOR_ORBIT_CAMERA_MODEL)
    if view.get("camera_model") == CANONICAL_CAMERA_MODEL:
        view.setdefault(
            "coordinate_frame",
            request.get("coordinate_frame") or MOLMOSPACES_SCENE_FRAME,
        )
        view.setdefault("up", [0.0, 0.0, 1.0])
    else:
        view.setdefault("camera_orbit", dict(request["camera_orbit"]))
    view.setdefault("lens", dict(request["lens"]))
    view.setdefault("calibration_status", request["calibration_status"])
    view.setdefault("coordinate_convention", request["coordinate_convention"])
    return view


def _camera_orbit(value: Any) -> dict[str, float]:
    raw = value if isinstance(value, dict) else {}
    return {
        "distance_m": float(raw.get("distance_m", raw.get("distance", 4.4))),
        "azimuth_deg": float(raw.get("azimuth_deg", raw.get("azimuth", 225.0))),
        "elevation_deg": float(raw.get("elevation_deg", raw.get("elevation", 28.0))),
    }


def _camera_lens(value: Any) -> dict[str, float]:
    raw = value if isinstance(value, dict) else {}
    lens = {
        "vertical_fov_deg": float(raw.get("vertical_fov_deg", 45.0)),
        "focal_length_mm": float(raw.get("focal_length_mm", 24.0)),
    }
    if "horizontal_aperture_mm" in raw:
        lens["horizontal_aperture_mm"] = float(raw["horizontal_aperture_mm"])
    return lens


def _lighting_profile(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    return {
        "profile_id": str(raw.get("profile_id") or "scene_probe_existing_usd_lights_v1"),
        "isaac_dome_intensity": float(raw.get("isaac_dome_intensity", 0.0)),
        "isaac_key_intensity": float(raw.get("isaac_key_intensity", 0.0)),
        "isaac_key_rotation_deg": _vec3(
            raw.get("isaac_key_rotation_deg"),
            default=[-55.0, 0.0, 35.0],
        ),
    }


def _color_profile(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    profile = {
        "profile_id": str(raw.get("profile_id") or "display_srgb_soft_highlight_v1"),
        "input_transfer": str(raw.get("input_transfer") or "renderer_rgb"),
        "output_transfer": str(raw.get("output_transfer") or "srgb_uint8"),
        "highlight_knee": float(raw.get("highlight_knee", 225.0)),
        "highlight_compression": float(raw.get("highlight_compression", 0.55)),
        "gamma": float(raw.get("gamma", 1.0)),
    }
    backend_luminance_gain = _float_mapping(
        raw.get(
            "backend_luminance_gain",
            DEFAULT_SCENE_PROBE_COLOR_PROFILE.get("backend_luminance_gain"),
        )
    )
    if backend_luminance_gain:
        profile["backend_luminance_gain"] = backend_luminance_gain
    backend_luminance_gain_source = raw.get(
        "backend_luminance_gain_source",
        DEFAULT_SCENE_PROBE_COLOR_PROFILE.get("backend_luminance_gain_source"),
    )
    if backend_luminance_gain_source:
        profile["backend_luminance_gain_source"] = str(backend_luminance_gain_source)
    return profile


def _float_mapping(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, float] = {}
    for key, raw_item in value.items():
        try:
            parsed[str(key)] = float(raw_item)
        except (TypeError, ValueError):
            continue
    return parsed


def _vec3(value: Any, *, default: list[float]) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return [float(default[0]), float(default[1]), float(default[2])]
    return [float(value[0]), float(value[1]), float(value[2])]


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 1
    return max(1, parsed)
