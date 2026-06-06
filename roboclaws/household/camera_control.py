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
SCENE_LIGHT_RIG_SCHEMA = "scene_light_rig_v1"
CANONICAL_SCENE_KEY_LIGHT_DIRECTION = [-0.57735, 0.57735, -0.57735]
CANONICAL_SCENE_KEY_LIGHT_ROTATION_DEG = [-45.0, 0.0, 35.0]

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
    "profile_id": "scene_probe_balanced_review_light_v1",
    "source": (
        "Default scene-camera light rig for MuJoCo/Isaac/Genesis review. It uses one "
        "canonical shadow-casting key role plus low ambient readability light, disables "
        "authored candidate-lane scene lights for comparison, and keeps fill off by default."
    ),
    "scene_light_rig": {
        "schema": SCENE_LIGHT_RIG_SCHEMA,
        "frame": MOLMOSPACES_SCENE_FRAME,
        "key": {
            "enabled": True,
            "direction": CANONICAL_SCENE_KEY_LIGHT_DIRECTION,
            "color": [1.0, 1.0, 1.0],
            "shadow": True,
        },
        "ambient": {
            "enabled": True,
            "mujoco_headlight_ambient": [0.35, 0.35, 0.35],
            "mujoco_headlight_diffuse": [0.4, 0.4, 0.4],
            "isaac_dome_intensity": 120.0,
            "genesis_ambient_light": [0.37, 0.37, 0.37],
            "genesis_background_color": [0.04, 0.08, 0.12],
        },
        "fill": {"enabled": False},
        "authored_scene_lights_policy": "disabled_for_comparison",
        "backend_overrides": {
            "isaac": {
                "key_intensity": 900.0,
                "key_rotation_deg": CANONICAL_SCENE_KEY_LIGHT_ROTATION_DEG,
                "existing_light_intensity_scale": 0.0,
            },
            "genesis": {"key_intensity": 3.0},
        },
    },
}
BALANCED_REVIEW_SCENE_PROBE_LIGHTING_PROFILE = DEFAULT_SCENE_PROBE_LIGHTING_PROFILE
SHADOW_PARITY_SCENE_PROBE_LIGHTING_PROFILE = {
    **DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
    "profile_id": "scene_probe_shadow_parity_probe_v1",
    "source": (
        "Shadow-parity probe for MuJoCo/Isaac/Genesis scene-camera review. This is "
        "not the default fill profile: it enables Genesis shadows, reduces Isaac "
        "dome fill, and adds an Isaac key light so bed/floor/wall cast-shadow "
        "behavior can be reviewed against MuJoCo."
    ),
    "scene_light_rig": {
        **DEFAULT_SCENE_PROBE_LIGHTING_PROFILE["scene_light_rig"],
        "key": {
            "enabled": True,
            "direction": CANONICAL_SCENE_KEY_LIGHT_DIRECTION,
            "color": [1.0, 1.0, 1.0],
            "shadow": True,
        },
        "ambient": {
            **DEFAULT_SCENE_PROBE_LIGHTING_PROFILE["scene_light_rig"]["ambient"],
            "isaac_dome_intensity": 12.0,
        },
        "fill": {"enabled": False},
        "authored_scene_lights_policy": "disabled_for_comparison",
        "backend_overrides": {
            "isaac": {
                "key_intensity": 1200.0,
                "key_rotation_deg": CANONICAL_SCENE_KEY_LIGHT_ROTATION_DEG,
                "existing_light_intensity_scale": 0.0,
            },
            "genesis": {"key_intensity": 3.0},
        },
    },
}
SCENE_PROBE_LIGHTING_PROFILES = {
    DEFAULT_SCENE_PROBE_LIGHTING_PROFILE["profile_id"]: DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
    "default": BALANCED_REVIEW_SCENE_PROBE_LIGHTING_PROFILE,
    BALANCED_REVIEW_SCENE_PROBE_LIGHTING_PROFILE[
        "profile_id"
    ]: BALANCED_REVIEW_SCENE_PROBE_LIGHTING_PROFILE,
    "balanced": BALANCED_REVIEW_SCENE_PROBE_LIGHTING_PROFILE,
    "balanced-review": BALANCED_REVIEW_SCENE_PROBE_LIGHTING_PROFILE,
    SHADOW_PARITY_SCENE_PROBE_LIGHTING_PROFILE[
        "profile_id"
    ]: SHADOW_PARITY_SCENE_PROBE_LIGHTING_PROFILE,
    "shadow-parity": SHADOW_PARITY_SCENE_PROBE_LIGHTING_PROFILE,
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
    "backend_view_luminance_gain": {},
    "backend_rgb_gain": {},
    "backend_view_rgb_gain": {},
    "backend_tone_adjustment": {},
    "backend_view_tone_adjustment": {},
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


def scene_light_rig(lighting_profile: dict[str, Any] | None) -> dict[str, Any]:
    """Return the canonical role-based scene light rig for a lighting profile."""

    profile = lighting_profile if isinstance(lighting_profile, dict) else {}
    return _scene_light_rig(profile.get("scene_light_rig"))


def scene_light_rig_roles(rig: dict[str, Any]) -> dict[str, Any]:
    """Summarize role intent without comparing backend-native light counts."""

    key = rig.get("key") if isinstance(rig.get("key"), dict) else {}
    ambient = rig.get("ambient") if isinstance(rig.get("ambient"), dict) else {}
    fill = rig.get("fill") if isinstance(rig.get("fill"), dict) else {}
    overrides = (
        rig.get("backend_overrides") if isinstance(rig.get("backend_overrides"), dict) else {}
    )
    isaac = overrides.get("isaac") if isinstance(overrides.get("isaac"), dict) else {}
    genesis = overrides.get("genesis") if isinstance(overrides.get("genesis"), dict) else {}
    fill_lights = (
        fill.get("genesis_directional_lights")
        if isinstance(fill.get("genesis_directional_lights"), list)
        else []
    )
    return {
        "schema": rig.get("schema"),
        "frame": rig.get("frame"),
        "key_enabled": bool(key.get("enabled")),
        "key_shadow": bool(key.get("shadow")),
        "key_direction": key.get("direction"),
        "ambient_enabled": bool(ambient.get("enabled")),
        "fill_enabled": bool(fill.get("enabled")),
        "fill_directional_light_count": len(fill_lights),
        "authored_scene_lights_policy": rig.get("authored_scene_lights_policy"),
        "isaac_key_intensity": isaac.get("key_intensity"),
        "isaac_dome_intensity": ambient.get("isaac_dome_intensity"),
        "isaac_existing_light_intensity_scale": isaac.get("existing_light_intensity_scale"),
        "genesis_key_intensity": genesis.get("key_intensity"),
    }


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
    default = DEFAULT_SCENE_PROBE_LIGHTING_PROFILE
    return {
        "profile_id": str(raw.get("profile_id") or default["profile_id"]),
        "source": str(raw.get("source") or default["source"]),
        "scene_light_rig": _scene_light_rig(raw.get("scene_light_rig")),
    }


def _scene_light_rig(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    default = DEFAULT_SCENE_PROBE_LIGHTING_PROFILE["scene_light_rig"]
    key = raw.get("key") if isinstance(raw.get("key"), dict) else {}
    ambient = raw.get("ambient") if isinstance(raw.get("ambient"), dict) else {}
    fill = raw.get("fill") if isinstance(raw.get("fill"), dict) else {}
    overrides = (
        raw.get("backend_overrides") if isinstance(raw.get("backend_overrides"), dict) else {}
    )
    isaac = overrides.get("isaac") if isinstance(overrides.get("isaac"), dict) else {}
    genesis = overrides.get("genesis") if isinstance(overrides.get("genesis"), dict) else {}
    default_ambient = default["ambient"]
    default_key = default["key"]
    default_fill = default["fill"]
    default_overrides = default["backend_overrides"]
    default_isaac = default_overrides["isaac"]
    default_genesis = default_overrides["genesis"]
    return {
        "schema": str(raw.get("schema") or SCENE_LIGHT_RIG_SCHEMA),
        "frame": str(raw.get("frame") or default["frame"]),
        "key": {
            "enabled": bool(key.get("enabled", default_key["enabled"])),
            "direction": _vec3(key.get("direction"), default=default_key["direction"]),
            "color": _vec3(key.get("color"), default=default_key["color"]),
            "shadow": bool(key.get("shadow", default_key["shadow"])),
        },
        "ambient": {
            "enabled": bool(ambient.get("enabled", default_ambient["enabled"])),
            "mujoco_headlight_ambient": _vec3(
                ambient.get("mujoco_headlight_ambient"),
                default=default_ambient["mujoco_headlight_ambient"],
            ),
            "mujoco_headlight_diffuse": _vec3(
                ambient.get("mujoco_headlight_diffuse"),
                default=default_ambient["mujoco_headlight_diffuse"],
            ),
            "isaac_dome_intensity": float(
                ambient.get("isaac_dome_intensity", default_ambient["isaac_dome_intensity"])
            ),
            "genesis_ambient_light": _vec3(
                ambient.get("genesis_ambient_light"),
                default=default_ambient["genesis_ambient_light"],
            ),
            "genesis_background_color": _vec3(
                ambient.get("genesis_background_color"),
                default=default_ambient["genesis_background_color"],
            ),
        },
        "fill": {
            "enabled": bool(fill.get("enabled", default_fill["enabled"])),
            "genesis_directional_lights": _directional_lights(
                fill.get("genesis_directional_lights"),
                default=default_fill.get("genesis_directional_lights") or [],
            ),
        },
        "authored_scene_lights_policy": str(
            raw.get("authored_scene_lights_policy") or default["authored_scene_lights_policy"]
        ),
        "backend_overrides": {
            "isaac": {
                "key_intensity": float(isaac.get("key_intensity", default_isaac["key_intensity"])),
                "key_rotation_deg": _vec3(
                    isaac.get("key_rotation_deg"),
                    default=default_isaac["key_rotation_deg"],
                ),
                "existing_light_intensity_scale": float(
                    isaac.get(
                        "existing_light_intensity_scale",
                        default_isaac["existing_light_intensity_scale"],
                    )
                ),
            },
            "genesis": {
                "key_intensity": float(
                    genesis.get("key_intensity", default_genesis["key_intensity"])
                ),
            },
        },
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
    backend_view_luminance_gain = _nested_float_mapping(
        raw.get(
            "backend_view_luminance_gain",
            DEFAULT_SCENE_PROBE_COLOR_PROFILE.get("backend_view_luminance_gain"),
        )
    )
    if backend_view_luminance_gain:
        profile["backend_view_luminance_gain"] = backend_view_luminance_gain
    if raw.get("backend_view_luminance_gain_source"):
        profile["backend_view_luminance_gain_source"] = str(
            raw["backend_view_luminance_gain_source"]
        )
    backend_rgb_gain = _rgb_gain_mapping(
        raw.get("backend_rgb_gain", DEFAULT_SCENE_PROBE_COLOR_PROFILE.get("backend_rgb_gain"))
    )
    if backend_rgb_gain:
        profile["backend_rgb_gain"] = backend_rgb_gain
    if raw.get("backend_rgb_gain_source"):
        profile["backend_rgb_gain_source"] = str(raw["backend_rgb_gain_source"])
    backend_view_rgb_gain = _nested_rgb_gain_mapping(
        raw.get(
            "backend_view_rgb_gain",
            DEFAULT_SCENE_PROBE_COLOR_PROFILE.get("backend_view_rgb_gain"),
        )
    )
    if backend_view_rgb_gain:
        profile["backend_view_rgb_gain"] = backend_view_rgb_gain
    if raw.get("backend_view_rgb_gain_source"):
        profile["backend_view_rgb_gain_source"] = str(raw["backend_view_rgb_gain_source"])
    backend_tone_adjustment = _tone_adjustment_mapping(
        raw.get(
            "backend_tone_adjustment",
            DEFAULT_SCENE_PROBE_COLOR_PROFILE.get("backend_tone_adjustment"),
        )
    )
    if backend_tone_adjustment:
        profile["backend_tone_adjustment"] = backend_tone_adjustment
    if raw.get("backend_tone_adjustment_source"):
        profile["backend_tone_adjustment_source"] = str(raw["backend_tone_adjustment_source"])
    backend_view_tone_adjustment = _nested_tone_adjustment_mapping(
        raw.get(
            "backend_view_tone_adjustment",
            DEFAULT_SCENE_PROBE_COLOR_PROFILE.get("backend_view_tone_adjustment"),
        )
    )
    if backend_view_tone_adjustment:
        profile["backend_view_tone_adjustment"] = backend_view_tone_adjustment
    if raw.get("backend_view_tone_adjustment_source"):
        profile["backend_view_tone_adjustment_source"] = str(
            raw["backend_view_tone_adjustment_source"]
        )
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


def _nested_float_mapping(value: Any) -> dict[str, dict[str, float]]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, dict[str, float]] = {}
    for key, raw_item in value.items():
        item = _float_mapping(raw_item)
        if item:
            parsed[str(key)] = item
    return parsed


def _rgb_gain_mapping(value: Any) -> dict[str, list[float]]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, list[float]] = {}
    for key, raw_item in value.items():
        rgb = _rgb_gain(raw_item)
        if rgb is not None:
            parsed[str(key)] = rgb
    return parsed


def _nested_rgb_gain_mapping(value: Any) -> dict[str, dict[str, list[float]]]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, dict[str, list[float]]] = {}
    for key, raw_item in value.items():
        item = _rgb_gain_mapping(raw_item)
        if item:
            parsed[str(key)] = item
    return parsed


def _tone_adjustment_mapping(value: Any) -> dict[str, dict[str, float]]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, dict[str, float]] = {}
    for key, raw_item in value.items():
        item = _tone_adjustment(raw_item)
        if item:
            parsed[str(key)] = item
    return parsed


def _nested_tone_adjustment_mapping(value: Any) -> dict[str, dict[str, dict[str, float]]]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, dict[str, dict[str, float]]] = {}
    for key, raw_item in value.items():
        item = _tone_adjustment_mapping(raw_item)
        if item:
            parsed[str(key)] = item
    return parsed


def _rgb_gain(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def _tone_adjustment(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    parsed: dict[str, float] = {}
    for key in ("shadow_lift", "shadow_floor", "gamma", "saturation", "gain"):
        if key not in value:
            continue
        try:
            parsed[key] = float(value[key])
        except (TypeError, ValueError):
            return None
    if not parsed:
        return None
    parsed.setdefault("shadow_lift", 0.0)
    parsed.setdefault("shadow_floor", 135.0)
    parsed.setdefault("gamma", 1.0)
    parsed.setdefault("saturation", 1.0)
    parsed.setdefault("gain", 1.0)
    return parsed


def _directional_lights(value: Any, *, default: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_lights = value if isinstance(value, list) else default
    parsed: list[dict[str, Any]] = []
    for raw_light in raw_lights:
        if not isinstance(raw_light, dict):
            continue
        parsed.append(
            {
                "type": str(raw_light.get("type") or "directional"),
                "dir": _vec3(raw_light.get("dir"), default=[-1.0, -1.0, -1.0]),
                "color": _vec3(raw_light.get("color"), default=[1.0, 1.0, 1.0]),
                "intensity": float(raw_light.get("intensity", 1.0)),
            }
        )
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
