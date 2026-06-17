from __future__ import annotations

from typing import Any

ISAAC_NATIVE_RENDER_DIAGNOSTICS_SCHEMA = "isaac_native_render_diagnostics_v1"


def native_isaac_render_diagnostics_from_state(isaac_state: dict[str, Any]) -> dict[str, Any]:
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


def native_isaac_render_diagnostics_summary(
    *,
    isaac_state: dict[str, Any],
    locations: list[dict[str, Any]],
) -> dict[str, Any]:
    state_diagnostics = native_isaac_render_diagnostics_from_state(isaac_state)
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


def _status_counts(values: Any) -> dict[str, int]:
    names = [str(value) for value in values if str(value)]
    return {name: names.count(name) for name in sorted(set(names))}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
