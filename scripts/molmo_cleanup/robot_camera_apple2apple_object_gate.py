from __future__ import annotations

from typing import Any

VISUAL_PHYSICS_PROTECTED_BY = "prepared_usd_visual_physics_freeze"


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
