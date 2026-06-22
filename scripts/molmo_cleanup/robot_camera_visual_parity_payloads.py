from __future__ import annotations

from typing import Any


def best_object_parity_audit(*candidates: Any) -> dict[str, Any]:
    audits = [_dict(candidate) for candidate in candidates if _dict(candidate)]
    if not audits:
        return {}
    return max(audits, key=_object_parity_audit_completeness_score)


def compact_object_visual_parity_audit(audit: dict[str, Any]) -> dict[str, Any]:
    if not audit:
        return {}
    category_summary = _list_dicts(audit.get("category_status_summary"))
    if not category_summary:
        category_summary = _object_category_status_summary_from_items(
            _list_dicts(audit.get("items"))
        )
    return {
        "schema": audit.get("schema"),
        "status": audit.get("status"),
        "item_count": audit.get("item_count"),
        "object_count": audit.get("object_count"),
        "receptacle_count": audit.get("receptacle_count"),
        "high_priority_gap_count": audit.get("high_priority_gap_count"),
        "binding_status_counts": audit.get("binding_status_counts") or {},
        "category_status_counts": audit.get("category_status_counts") or {},
        "pose_status_counts": audit.get("pose_status_counts") or {},
        "support_status_counts": audit.get("support_status_counts") or {},
        "state_status_counts": audit.get("state_status_counts") or {},
        "render_contract_status_counts": audit.get("render_contract_status_counts") or {},
        "category_status_summary": category_summary,
        "recommended_next_action": audit.get("recommended_next_action"),
    }


def compact_native_isaac_render_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    if not diagnostics:
        return {}
    capture_quality = _dict(diagnostics.get("capture_quality_settings"))
    return {
        "schema": diagnostics.get("schema"),
        "status": diagnostics.get("status"),
        "renderer_mode": diagnostics.get("renderer_mode"),
        "capture_method": diagnostics.get("capture_method"),
        "settings_api_available": diagnostics.get("settings_api_available"),
        "available_setting_count": diagnostics.get("available_setting_count"),
        "missing_setting_count": diagnostics.get("missing_setting_count"),
        "camera_prim_paths": diagnostics.get("camera_prim_paths") or [],
        "render_product_paths": diagnostics.get("render_product_paths") or [],
        "isaac_lab_isp_active": diagnostics.get("isaac_lab_isp_active"),
        "default_render_settings_changed": diagnostics.get("default_render_settings_changed"),
        "tone_mapping": diagnostics.get("tone_mapping") or {},
        "camera_exposure": diagnostics.get("camera_exposure") or {},
        "ocio": diagnostics.get("ocio") or {},
        "color_correction": diagnostics.get("color_correction") or {},
        "color_grading": diagnostics.get("color_grading") or {},
        "renderer": diagnostics.get("renderer") or {},
        "capture_quality_settings": capture_quality,
        "post_render_comparison_profile": diagnostics.get("post_render_comparison_profile") or {},
    }


def capture_quality_probe_summary(payload: dict[str, Any]) -> dict[str, Any]:
    scene = _dict(payload.get("scene"))
    summary = _dict(payload.get("summary"))
    native_source = _dict(summary.get("native_isaac_render_diagnostics")) or _dict(
        payload.get("native_isaac_render_diagnostics")
    )
    native = _dict(_dict(native_source).get("primary")) or native_source
    native_capture_quality = _dict(native.get("capture_quality_settings"))
    raw_explicit = payload.get("capture_quality_probe")
    if "capture_quality_probe" in payload and not isinstance(raw_explicit, dict):
        raise ValueError("capture_quality_probe must be an object")
    explicit = _dict(raw_explicit)
    render_resolution = _resolution_from_explicit_or_scene(
        explicit,
        "render_resolution_requested",
        scene,
        width_field="render_width",
        height_field="render_height",
    )
    saved_resolution = _resolution_from_explicit_or_scene(
        explicit,
        "render_resolution_saved",
        scene,
        width_field="saved_report_width",
        height_field="saved_report_height",
        default=render_resolution,
    )
    metric_resolution = _resolution_from_explicit_or_scene(
        explicit,
        "metric_resolution",
        scene,
        width_field="metric_width",
        height_field="metric_height",
        default=saved_resolution,
    )
    saved_mode = str(explicit.get("saved_image_mode") or "")
    if not saved_mode:
        saved_mode = (
            "direct_capture"
            if saved_resolution == render_resolution
            else "downsampled_from_render_capture"
        )
    metric_mode = str(explicit.get("metric_image_mode") or "")
    if not metric_mode:
        metric_mode = (
            "direct_capture"
            if metric_resolution == render_resolution
            else "downsampled_from_render_capture"
        )
    render_settle_frames = (
        explicit.get("render_settle_frames")
        if "render_settle_frames" in explicit
        else native_capture_quality.get("render_settle_frames")
    )
    return {
        "schema": explicit.get("schema") or "robot_camera_capture_quality_probe_v1",
        "status": explicit.get("status") or "inferred_from_manifest",
        "render_resolution_requested": render_resolution,
        "render_resolution_saved": saved_resolution,
        "metric_resolution": metric_resolution,
        "saved_image_mode": saved_mode,
        "metric_image_mode": metric_mode,
        "direct_capture_metrics": metric_mode == "direct_capture",
        "downsampled_metrics": metric_mode != "direct_capture",
        "downsample_filter": explicit.get("downsample_filter") or "",
        "render_settle_frames": int(render_settle_frames or 0),
        "samples_per_pixel": _quality_setting_row(
            explicit,
            native_capture_quality,
            "samples_per_pixel",
        ),
        "anti_aliasing": _quality_setting_row(explicit, native_capture_quality, "anti_aliasing"),
        "tonemap_operator": _quality_setting_row(
            explicit,
            native_capture_quality,
            "tonemap_operator",
        ),
        "exposure_bias": _quality_setting_row(
            explicit,
            native_capture_quality,
            "exposure_bias",
        ),
        "colorcorr_gain": _quality_setting_row(
            explicit,
            native_capture_quality,
            "colorcorr_gain",
        ),
        "denoise": _quality_setting_row(explicit, native_capture_quality, "denoise"),
        "taa": _quality_setting_row(explicit, native_capture_quality, "taa"),
        "texture_filtering": _quality_setting_row(
            explicit,
            native_capture_quality,
            "texture_filtering",
        ),
        "policy_classification": explicit.get("policy_classification") or "capture_quality_probe",
        "default_renderer_promotion": explicit.get("default_renderer_promotion") is True,
    }


def capture_quality_settings_summary(
    capture_quality: dict[str, Any],
    native_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    native_capture_quality = _dict(native_diagnostics.get("capture_quality_settings"))
    return {
        "render_settle_frames": capture_quality.get("render_settle_frames"),
        "samples_per_pixel": _quality_setting_row(
            capture_quality,
            native_capture_quality,
            "samples_per_pixel",
        ),
        "anti_aliasing": _quality_setting_row(
            capture_quality,
            native_capture_quality,
            "anti_aliasing",
        ),
        "tonemap_operator": _quality_setting_row(
            capture_quality,
            native_capture_quality,
            "tonemap_operator",
        ),
        "exposure_bias": _quality_setting_row(
            capture_quality,
            native_capture_quality,
            "exposure_bias",
        ),
        "colorcorr_gain": _quality_setting_row(
            capture_quality,
            native_capture_quality,
            "colorcorr_gain",
        ),
        "denoise": _quality_setting_row(capture_quality, native_capture_quality, "denoise"),
        "taa": _quality_setting_row(capture_quality, native_capture_quality, "taa"),
        "texture_filtering": _quality_setting_row(
            capture_quality,
            native_capture_quality,
            "texture_filtering",
        ),
    }


def is_capture_quality_probe(capture_quality: dict[str, Any]) -> bool:
    if not capture_quality:
        return False
    render_resolution = _dict(capture_quality.get("render_resolution_requested"))
    render_size = (
        int(render_resolution.get("width") or 0),
        int(render_resolution.get("height") or 0),
    )
    return (
        capture_quality.get("metric_image_mode") != "direct_capture"
        or capture_quality.get("saved_image_mode") != "direct_capture"
        or int(capture_quality.get("render_settle_frames") or 0) > 0
        or render_size not in {(0, 0), (540, 360)}
        or _has_requested_quality_setting(capture_quality)
    )


def metric_scene_signature(scene: dict[str, Any], capture_quality: dict[str, Any]) -> str:
    metric = _dict(capture_quality.get("metric_resolution"))
    return "|".join(
        str(value)
        for value in (
            scene.get("scene_source"),
            scene.get("scene_index"),
            scene.get("seed"),
            scene.get("generated_mess_count"),
            metric.get("width") or scene.get("render_width"),
            metric.get("height") or scene.get("render_height"),
        )
    )


def status_counts(values: Any) -> dict[str, int]:
    collected = [str(value) for value in values if value]
    return {name: collected.count(name) for name in sorted(set(collected))}


def _object_parity_audit_completeness_score(audit: dict[str, Any]) -> tuple[int, int, int]:
    return (
        len(_list_dicts(audit.get("category_status_summary"))),
        len(_list_dicts(audit.get("items"))),
        len(_list_dicts(audit.get("high_priority_items"))),
    )


def _object_category_status_summary_from_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        mujoco = _dict(item.get("mujoco"))
        isaac = _dict(item.get("isaac"))
        category = (
            _object_category_key(mujoco.get("category"))
            or _object_category_key(isaac.get("category"))
            or _object_category_key(isaac.get("usd_category"))
            or "unknown"
        )
        grouped.setdefault(category, []).append(item)
    rows = []
    for category, category_items in sorted(grouped.items()):
        rows.append(
            {
                "category": category,
                "item_count": len(category_items),
                "kind_counts": status_counts(item.get("kind") for item in category_items),
                "binding_status_counts": status_counts(
                    item.get("binding_status") for item in category_items
                ),
                "category_status_counts": status_counts(
                    item.get("category_status") for item in category_items
                ),
                "pose_status_counts": status_counts(
                    item.get("pose_status") for item in category_items
                ),
                "support_status_counts": status_counts(
                    item.get("support_status") for item in category_items
                ),
                "state_status_counts": status_counts(
                    item.get("state_status") for item in category_items
                ),
                "rgb_view_evidence_status_counts": status_counts(
                    _dict(item.get("rgb_view_evidence")).get("status") for item in category_items
                ),
                "render_contract_status_counts": status_counts(
                    _dict(item.get("render_contract_delta")).get("status")
                    for item in category_items
                ),
            }
        )
    return rows


def _quality_setting_row(
    explicit: dict[str, Any],
    native_capture_quality: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    row = _dict(explicit.get(name)) or _dict(native_capture_quality.get(name))
    if row:
        return row
    return {
        "name": name,
        "status": "not_available",
        "value": None,
        "setting_path": "",
        "default_render_settings_changed": False,
    }


def _has_requested_quality_setting(capture_quality: dict[str, Any]) -> bool:
    for key in (
        "samples_per_pixel",
        "anti_aliasing",
        "tonemap_operator",
        "exposure_bias",
        "colorcorr_gain",
        "denoise",
        "taa",
        "texture_filtering",
    ):
        row = _dict(capture_quality.get(key))
        if not row:
            continue
        if row.get("default_render_settings_changed") is True:
            return True
        if str(row.get("status") or "") in {"requested", "applied", "set_failed"}:
            return True
        if row.get("requested_value") is not None:
            return True
    return False


def _resolution_from_explicit_or_scene(
    explicit: dict[str, Any],
    explicit_field: str,
    scene: dict[str, Any],
    *,
    width_field: str,
    height_field: str,
    default: dict[str, int] | None = None,
) -> dict[str, int]:
    if explicit_field in explicit:
        explicit_resolution = explicit.get(explicit_field)
        if not isinstance(explicit_resolution, dict):
            raise ValueError(f"{explicit_field} must be an object with width and height")
        return _required_resolution(explicit_resolution, field_name=explicit_field)
    width = scene.get(width_field)
    height = scene.get(height_field)
    if (
        _is_unspecified_dimension(width)
        and _is_unspecified_dimension(height)
        and default is not None
    ):
        return default
    if _is_unspecified_dimension(width) != _is_unspecified_dimension(height):
        raise ValueError(f"scene.{width_field} and scene.{height_field} must be set together")
    return _required_resolution(
        {"width": width, "height": height},
        field_name=f"scene.{width_field}/{height_field}",
    )


def _required_resolution(value: dict[str, Any], *, field_name: str) -> dict[str, int]:
    return {
        "width": _positive_int(value.get("width"), field_name=f"{field_name}.width"),
        "height": _positive_int(value.get("height"), field_name=f"{field_name}.height"),
    }


def _positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer; got {value!r}")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{field_name} must be a positive integer; got {value!r}")
        parsed = int(value)
    elif isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            raise ValueError(f"{field_name} must be a positive integer; got {value!r}") from None
    else:
        raise ValueError(f"{field_name} must be a positive integer; got {value!r}")
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer; got {value!r}")
    return parsed


def _is_unspecified_dimension(value: Any) -> bool:
    return value is None or value == ""


def _object_category_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
