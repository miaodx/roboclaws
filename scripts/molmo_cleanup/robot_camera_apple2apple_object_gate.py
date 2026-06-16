from __future__ import annotations

from typing import Any

VISUAL_PHYSICS_PROTECTED_BY = "prepared_usd_visual_physics_freeze"
PASS_THROUGH_STATUSES = {
    "bound_in_both",
    "category_aligned",
    "pose_aligned",
    "support_metadata_aligned",
    "support_not_reported",
    "state_aligned",
    "not_applicable",
    "material_texture_names_match",
}


def object_render_parity_diagnostics(
    *,
    object_audit: dict[str, Any],
    render_domain_checks: dict[str, Any],
    residual_triage: dict[str, Any] | None,
    native_render_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items = _list_dicts(object_audit.get("items"))
    item_records = [object_gate_record(item) for item in items]
    object_failures = [
        item for item in item_records if item.get("object_gate_status") != "comparable"
    ]
    comparable = [item for item in item_records if item.get("object_gate_status") == "comparable"]
    render_gate = render_gate_diagnostics(
        comparable_records=comparable,
        render_domain_checks=render_domain_checks,
        residual_triage=residual_triage or {},
        native_render_diagnostics=native_render_diagnostics or {},
    )
    object_gate_status = (
        "no_object_records"
        if not item_records
        else "object_gate_failures_detected"
        if object_failures
        else "object_gate_comparable"
    )
    if object_gate_status == "no_object_records":
        status = "no_object_records"
        next_action = "Run a comparison with MuJoCo/Isaac state artifacts before parity claims."
    elif object_failures:
        status = "object_gate_failures_detected"
        next_action = (
            "Fix or mark non-comparable object bindings, geometry, pose, material, or "
            "visual-state rows before treating RGB residuals as render-domain evidence."
        )
    else:
        status = render_gate.get("status") or "render_gate_unclassified"
        next_action = str(
            render_gate.get("recommended_next_action")
            or "Comparable object rows are ready for render-domain residual triage."
        )
    return {
        "schema": "robot_camera_object_render_parity_diagnostics_v1",
        "status": status,
        "object_gate": {
            "status": object_gate_status,
            "item_count": len(item_records),
            "comparable_count": len(comparable),
            "failure_count": len(object_failures),
            "status_counts": _status_counts(
                item.get("object_gate_status") for item in item_records
            ),
            "classification_counts": _status_counts(
                item.get("classification") for item in item_records
            ),
            "failure_records": object_failures[:20],
            "comparable_records": comparable[:20],
        },
        "render_gate": render_gate,
        "recommended_next_action": next_action,
        "interpretation": (
            "The Object Gate decides whether scene objects are present, bound, renderable, "
            "posed, and in an auditable visual/material state. The Render Gate only "
            "interprets camera RGB residuals after comparable object rows are separated "
            "from missing or mismatched objects."
        ),
    }


def compact_object_render_parity_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    object_gate = _dict(diagnostics.get("object_gate"))
    render_gate = _dict(diagnostics.get("render_gate"))
    return {
        "schema": diagnostics.get("schema"),
        "status": diagnostics.get("status"),
        "skip_reason": diagnostics.get("skip_reason"),
        "object_gate_status": object_gate.get("status"),
        "object_gate_item_count": object_gate.get("item_count"),
        "object_gate_comparable_count": object_gate.get("comparable_count"),
        "object_gate_failure_count": object_gate.get("failure_count"),
        "object_gate_status_counts": object_gate.get("status_counts"),
        "object_gate_classification_counts": object_gate.get("classification_counts"),
        "render_gate_status": render_gate.get("status"),
        "render_gate_residual_status": render_gate.get("residual_status"),
        "render_gate_render_domain_status": render_gate.get("render_domain_status"),
        "render_gate_native_isaac_status": render_gate.get("native_isaac_status"),
        "recommended_next_action": diagnostics.get("recommended_next_action"),
    }


def skipped_object_render_parity_diagnostics(
    *,
    render_domain_checks: dict[str, Any],
    residual_triage: dict[str, Any] | None,
    native_render_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    render_gate = render_gate_diagnostics(
        comparable_records=[],
        render_domain_checks=render_domain_checks,
        residual_triage=residual_triage or {},
        native_render_diagnostics=native_render_diagnostics or {},
    )
    return {
        "schema": "robot_camera_object_render_parity_diagnostics_v1",
        "status": "skipped_for_capture_quality_probe",
        "skip_reason": (
            "The Object Gate was explicitly skipped with --skip-object-parity-audit. "
            "This run can rank capture-quality candidates, but it is not object-level "
            "parity evidence."
        ),
        "object_gate": {
            "status": "skipped_for_capture_quality_probe",
            "item_count": 0,
            "comparable_count": 0,
            "failure_count": 0,
            "status_counts": {},
            "classification_counts": {},
            "failure_records": [],
            "comparable_records": [],
        },
        "render_gate": render_gate,
        "recommended_next_action": (
            "Compare FPV/chase image metrics for the capture-quality candidate. Rerun "
            "without --skip-object-parity-audit before treating object rows as comparable."
        ),
        "interpretation": "The Object Gate is intentionally absent in this capture-quality probe.",
    }


def object_gate_record(item: dict[str, Any]) -> dict[str, Any]:
    statuses = object_parity_item_statuses(item)
    classification = object_gate_classification(item, statuses)
    blocking_status = object_gate_blocking_status(item, statuses)
    object_gate_status = "comparable" if classification == "comparable" else "not_comparable"
    render_delta = _dict(item.get("render_contract_delta"))
    visual_state = _dict(item.get("visual_state_contract"))
    rgb_evidence = _dict(item.get("rgb_view_evidence"))
    return {
        "kind": item.get("kind"),
        "target_id": item.get("target_id"),
        "object_gate_status": object_gate_status,
        "classification": classification,
        "blocking_status": blocking_status,
        "binding_status": item.get("binding_status"),
        "category_status": item.get("category_status"),
        "pose_status": item.get("pose_status"),
        "support_status": item.get("support_status"),
        "state_status": item.get("state_status"),
        "render_contract_status": render_delta.get("status"),
        "visual_state_status": visual_state.get("status"),
        "rgb_view_evidence_status": rgb_evidence.get("status"),
        "target_coverage_status": rgb_evidence.get("target_coverage_status"),
        "target_visual_state_status": rgb_evidence.get("target_visual_state_status"),
        "pose_delta_m": item.get("pose_delta_m"),
        "mujoco_category": _dict(item.get("mujoco")).get("category"),
        "isaac_category": _dict(item.get("isaac")).get("category")
        or _dict(item.get("isaac")).get("usd_category"),
        "isaac_usd_prim_path": _dict(item.get("isaac")).get("usd_prim_path"),
        "selected_public_target": item.get("selected_public_target"),
    }


def object_parity_item_statuses(item: dict[str, Any]) -> set[str]:
    return {
        str(value)
        for value in (
            item.get("binding_status"),
            item.get("category_status"),
            item.get("pose_status"),
            item.get("support_status"),
            item.get("state_status"),
            _dict(item.get("visual_state_contract")).get("status"),
            _dict(item.get("render_contract_delta")).get("status"),
        )
        if value
    }


def object_gate_classification(item: dict[str, Any], statuses: set[str]) -> str:
    binding_status = str(item.get("binding_status") or "")
    if binding_status in {"missing_both", "missing_mujoco_state", "missing_isaac_index"}:
        return "missing_binding"
    if binding_status in {"missing_usd_prim_path", "isaac_geometry_gap"}:
        return "missing_renderable_geometry"
    if str(item.get("category_status") or "") == "category_delta":
        return "not_comparable"
    if str(item.get("pose_status") or "") == "pose_delta":
        return "pose_delta"
    if str(item.get("support_status") or "") == "support_metadata_delta":
        return "pose_delta"
    visual_status = protected_visual_physics_status(item)
    if visual_status:
        return visual_status
    if str(item.get("state_status") or "") in {
        "state_delta",
        "state_not_rendered_to_usd",
        "visual_state_articulation_physics_preserved",
        "visual_state_unverified",
    }:
        return "visual_state_delta"
    if str(_dict(item.get("render_contract_delta")).get("status") or "") in {
        "material_or_texture_name_delta",
        "missing_object_binding_evidence",
    }:
        return "material_delta"
    if any(status.startswith("missing_") for status in statuses):
        return "missing_binding"
    return "comparable"


def object_gate_blocking_status(item: dict[str, Any], statuses: set[str]) -> str:
    if visual_physics_protected_without_selected_rgb(item):
        return "visual_state_requires_selected_rgb_evidence"
    if visual_physics_protected_without_target_coverage(item):
        return "visual_state_requires_selected_target_coverage"
    if visual_physics_protected_with_target_visual_delta(item):
        return str(
            _dict(item.get("rgb_view_evidence")).get("target_visual_state_status")
            or "selected_object_visual_state_delta"
        )
    for value in (
        item.get("binding_status"),
        item.get("category_status"),
        item.get("pose_status"),
        item.get("support_status"),
        item.get("state_status"),
        _dict(item.get("visual_state_contract")).get("status"),
        _dict(item.get("render_contract_delta")).get("status"),
    ):
        status = str(value or "")
        if status and status in statuses and status not in PASS_THROUGH_STATUSES:
            return status
    return ""


def render_gate_diagnostics(
    *,
    comparable_records: list[dict[str, Any]],
    render_domain_checks: dict[str, Any],
    residual_triage: dict[str, Any],
    native_render_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    residual_status = str(residual_triage.get("status") or "")
    render_domain_status = str(render_domain_checks.get("status") or "")
    native_status = str(native_render_diagnostics.get("status") or "")
    if not comparable_records:
        status = "blocked_by_object_gate"
        next_action = "No comparable object rows are available for render-domain residual claims."
    elif (
        render_domain_status
        in {
            "render_domain_delta_confirmed",
            "render_domain_checks_low_priority",
        }
        or residual_status
    ):
        status = "render_domain_residual"
        next_action = str(
            render_domain_checks.get("recommended_next_action")
            or residual_triage.get("recommended_next_action")
            or "Continue render-domain triage on comparable object rows."
        )
    else:
        status = "render_gate_unclassified"
        next_action = "Attach render-domain checks and residual triage before render claims."
    return {
        "schema": "robot_camera_render_gate_diagnostics_v1",
        "status": status,
        "comparable_object_count": len(comparable_records),
        "render_domain_status": render_domain_status,
        "residual_status": residual_status,
        "native_isaac_status": native_status,
        "native_isaac_render_diagnostics": compact_native_isaac_render_diagnostics(
            native_render_diagnostics
        )
        if native_render_diagnostics
        else {},
        "residual_triage": residual_triage,
        "render_domain_check_status_counts": render_domain_checks.get("check_status_counts") or {},
        "recommended_next_action": next_action,
    }


def compact_native_isaac_render_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    primary = _dict(diagnostics.get("primary")) or diagnostics
    return {
        "schema": diagnostics.get("schema") or primary.get("schema"),
        "status": diagnostics.get("status") or primary.get("status"),
        "native_settings_recorded": diagnostics.get("native_settings_recorded"),
        "renderer_mode": diagnostics.get("renderer_mode") or primary.get("renderer_mode"),
        "capture_method": diagnostics.get("capture_method") or primary.get("capture_method"),
        "view_kind": diagnostics.get("view_kind") or primary.get("view_kind"),
        "settings_api_available": diagnostics.get("settings_api_available")
        if "settings_api_available" in diagnostics
        else primary.get("settings_api_available"),
        "available_setting_count": diagnostics.get("available_setting_count")
        if "available_setting_count" in diagnostics
        else primary.get("available_setting_count"),
        "missing_setting_count": diagnostics.get("missing_setting_count")
        if "missing_setting_count" in diagnostics
        else primary.get("missing_setting_count"),
        "camera_prim_paths": diagnostics.get("camera_prim_paths")
        or primary.get("camera_prim_paths")
        or [],
        "render_product_paths": diagnostics.get("render_product_paths")
        or primary.get("render_product_paths")
        or [],
        "isaac_lab_isp_active": diagnostics.get("isaac_lab_isp_active")
        if "isaac_lab_isp_active" in diagnostics
        else primary.get("isaac_lab_isp_active"),
        "default_render_settings_changed": diagnostics.get("default_render_settings_changed")
        if "default_render_settings_changed" in diagnostics
        else primary.get("default_render_settings_changed"),
        "post_render_comparison_profile": diagnostics.get("post_render_comparison_profile")
        or primary.get("post_render_comparison_profile")
        or {},
        "recommended_next_action": diagnostics.get("recommended_next_action"),
    }


def protected_visual_physics_status(item: dict[str, Any]) -> str:
    if not _is_visual_physics_protected(item):
        return ""
    rgb_evidence = _dict(item.get("rgb_view_evidence"))
    if str(rgb_evidence.get("status") or "") != "selected_views_nonblank":
        return "visual_state_needs_rgb_evidence"
    if str(rgb_evidence.get("target_coverage_status") or "") != (
        "selected_object_centered_coverage"
    ):
        return "visual_state_needs_target_coverage"
    if str(rgb_evidence.get("target_visual_state_status") or "") != (
        "selected_object_visual_state_aligned"
    ):
        return "visual_state_delta"
    return ""


def visual_physics_protected_without_selected_rgb(item: dict[str, Any]) -> bool:
    return protected_visual_physics_status(item) == "visual_state_needs_rgb_evidence"


def visual_physics_protected_without_target_coverage(item: dict[str, Any]) -> bool:
    return protected_visual_physics_status(item) == "visual_state_needs_target_coverage"


def visual_physics_protected_with_target_visual_delta(item: dict[str, Any]) -> bool:
    return protected_visual_physics_status(item) == "visual_state_delta"


def _is_visual_physics_protected(item: dict[str, Any]) -> bool:
    visual_state = _dict(item.get("visual_state_contract"))
    if str(visual_state.get("protected_by") or "") != VISUAL_PHYSICS_PROTECTED_BY:
        return False
    return str(visual_state.get("status") or "") == "visual_state_static_ref_baked"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _status_counts(values: Any) -> dict[str, int]:
    collected = [str(value) for value in values if value]
    return {name: collected.count(name) for name in sorted(set(collected))}
