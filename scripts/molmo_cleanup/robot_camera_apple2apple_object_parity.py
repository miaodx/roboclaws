from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from roboclaws.household.scene_camera_comparison import (
    _isaac_view_render_contract,
    _mujoco_view_render_contract,
    _view_render_contract_delta,
)
from scripts.molmo_cleanup import robot_camera_apple2apple_materials as material_checks
from scripts.molmo_cleanup import robot_camera_apple2apple_object_gate as object_gate
from scripts.molmo_cleanup import robot_camera_apple2apple_rgb_evidence as rgb_evidence
from scripts.molmo_cleanup import robot_camera_apple2apple_visual_state as visual_state

OBJECT_PARITY_POSE_THRESHOLD_M = 0.05


def object_parity_audit(
    *,
    mujoco_state: dict[str, Any],
    isaac_state: dict[str, Any],
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    scene_binding_diagnostics: dict[str, Any],
    locations: list[dict[str, Any]] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    object_ids = sorted(
        set(_dict(mujoco_state.get("objects")))
        | set(_dict(isaac_state.get("object_index")))
        | _bound_ids_from_groups(scene_binding_diagnostics, ("object_bindings",))
    )
    receptacle_ids = sorted(
        set(_dict(mujoco_state.get("receptacles")))
        | set(_dict(isaac_state.get("receptacle_index")))
        | _bound_ids_from_groups(scene_binding_diagnostics, ("receptacle_bindings",))
    )
    for target_id in object_ids:
        items.append(
            _object_parity_item(
                kind="object",
                target_id=str(target_id),
                mujoco_state=mujoco_state,
                isaac_state=isaac_state,
                mujoco_contract=mujoco_contract,
                isaac_contract=isaac_contract,
                scene_binding_diagnostics=scene_binding_diagnostics,
                locations=locations or [],
                output_dir=output_dir,
            )
        )
    for target_id in receptacle_ids:
        items.append(
            _object_parity_item(
                kind="receptacle",
                target_id=str(target_id),
                mujoco_state=mujoco_state,
                isaac_state=isaac_state,
                mujoco_contract=mujoco_contract,
                isaac_contract=isaac_contract,
                scene_binding_diagnostics=scene_binding_diagnostics,
                locations=locations or [],
                output_dir=output_dir,
            )
        )
    high_priority_statuses = {
        "missing_isaac_index",
        "missing_mujoco_state",
        "isaac_geometry_gap",
        "missing_usd_prim_path",
        "category_delta",
        "pose_delta",
        "support_metadata_delta",
        "state_delta",
        "state_not_rendered_to_usd",
        "visual_state_articulation_physics_preserved",
        "visual_state_unverified",
        "material_or_texture_name_delta",
        "missing_object_binding_evidence",
    }
    high_priority = [
        item
        for item in items
        if any(
            status in high_priority_statuses
            for status in object_gate.object_parity_item_statuses(item)
        )
    ]
    if not items:
        status = "no_scene_objects"
        next_action = "No MuJoCo or Isaac scene objects were available for object parity audit."
    elif high_priority:
        status = "object_parity_gaps_detected"
        next_action = (
            "Inspect high-priority object parity rows before changing camera settings. "
            "Start with missing bindings, category/pose/support deltas, and USD state "
            "that is not rendered to geometry."
        )
    else:
        status = "object_parity_index_aligned"
        next_action = (
            "Object indices and compact material/state contracts align for this scene; "
            "remaining residuals are likely renderer response or robot visual import."
        )
    return {
        "schema": "robot_camera_object_parity_audit_v1",
        "status": status,
        "item_count": len(items),
        "object_count": sum(1 for item in items if item.get("kind") == "object"),
        "receptacle_count": sum(1 for item in items if item.get("kind") == "receptacle"),
        "high_priority_gap_count": len(high_priority),
        "binding_status_counts": _status_counts(item.get("binding_status") for item in items),
        "category_status_counts": _status_counts(item.get("category_status") for item in items),
        "pose_status_counts": _status_counts(item.get("pose_status") for item in items),
        "support_status_counts": _status_counts(item.get("support_status") for item in items),
        "state_status_counts": _status_counts(item.get("state_status") for item in items),
        "render_contract_status_counts": _status_counts(
            _dict(item.get("render_contract_delta")).get("status") for item in items
        ),
        "category_status_summary": _object_category_status_summary(items),
        "high_priority_items": high_priority[:20],
        "items": items,
        "recommended_next_action": next_action,
        "interpretation": (
            "This audit checks scene objects/receptacles beyond the limited image target "
            "set. It compares MuJoCo state and MJCF render contracts against Isaac USD "
            "indices, compact USD bounds, parent/support metadata, semantic open state, "
            "and PreviewSurface material bindings."
        ),
    }


def compact_object_parity_audit(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": audit.get("schema"),
        "status": audit.get("status"),
        "skip_reason": audit.get("skip_reason"),
        "item_count": audit.get("item_count"),
        "object_count": audit.get("object_count"),
        "receptacle_count": audit.get("receptacle_count"),
        "high_priority_gap_count": audit.get("high_priority_gap_count"),
        "binding_status_counts": audit.get("binding_status_counts"),
        "category_status_counts": audit.get("category_status_counts"),
        "pose_status_counts": audit.get("pose_status_counts"),
        "support_status_counts": audit.get("support_status_counts"),
        "state_status_counts": audit.get("state_status_counts"),
        "render_contract_status_counts": audit.get("render_contract_status_counts"),
        "category_status_summary": audit.get("category_status_summary"),
        "high_priority_items": audit.get("high_priority_items"),
        "recommended_next_action": audit.get("recommended_next_action"),
    }


def skipped_object_parity_audit() -> dict[str, Any]:
    return {
        "schema": "robot_camera_object_parity_audit_v1",
        "status": "skipped_for_capture_quality_probe",
        "skip_reason": (
            "The full-scene object parity audit was explicitly skipped for a bounded "
            "capture-quality probe. Use image diffs, render contract diagnostics, and "
            "native Isaac render diagnostics for this run; rerun without "
            "--skip-object-parity-audit before making object-level parity claims."
        ),
        "item_count": 0,
        "object_count": 0,
        "receptacle_count": 0,
        "high_priority_gap_count": 0,
        "binding_status_counts": {},
        "category_status_counts": {},
        "pose_status_counts": {},
        "support_status_counts": {},
        "state_status_counts": {},
        "render_contract_status_counts": {},
        "category_status_summary": [],
        "high_priority_items": [],
        "items": [],
        "recommended_next_action": (
            "Use this artifact only for capture-quality ranking. Rerun without the skip "
            "flag for object/render gate evidence."
        ),
        "interpretation": (
            "Capture-quality probes can skip the expensive full-scene audit so local "
            "render evidence remains fast and comparable."
        ),
    }


def _object_category_status_summary(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        records = [object_gate.object_gate_record(item) for item in category_items]
        rows.append(
            {
                "category": category,
                "item_count": len(category_items),
                "kind_counts": _status_counts(item.get("kind") for item in category_items),
                "object_gate_status_counts": _status_counts(
                    record.get("object_gate_status") for record in records
                ),
                "object_gate_classification_counts": _status_counts(
                    record.get("classification") for record in records
                ),
                "binding_status_counts": _status_counts(
                    item.get("binding_status") for item in category_items
                ),
                "category_status_counts": _status_counts(
                    item.get("category_status") for item in category_items
                ),
                "pose_status_counts": _status_counts(
                    item.get("pose_status") for item in category_items
                ),
                "support_status_counts": _status_counts(
                    item.get("support_status") for item in category_items
                ),
                "state_status_counts": _status_counts(
                    item.get("state_status") for item in category_items
                ),
                "rgb_view_evidence_status_counts": _status_counts(
                    _dict(item.get("rgb_view_evidence")).get("status") for item in category_items
                ),
                "target_coverage_status_counts": _status_counts(
                    _dict(item.get("rgb_view_evidence")).get("target_coverage_status")
                    for item in category_items
                ),
                "target_visual_state_status_counts": _status_counts(
                    _dict(item.get("rgb_view_evidence")).get("target_visual_state_status")
                    for item in category_items
                ),
                "render_contract_status_counts": _status_counts(
                    _dict(item.get("render_contract_delta")).get("status")
                    for item in category_items
                ),
            }
        )
    return rows


def _object_parity_item(
    *,
    kind: str,
    target_id: str,
    mujoco_state: dict[str, Any],
    isaac_state: dict[str, Any],
    mujoco_contract: dict[str, Any],
    isaac_contract: dict[str, Any],
    scene_binding_diagnostics: dict[str, Any],
    locations: list[dict[str, Any]],
    output_dir: Path | None,
) -> dict[str, Any]:
    mujoco_entry = _mujoco_state_entry(mujoco_state, kind, target_id)
    isaac_entry = isaac_effective_index_entry(isaac_state, kind, target_id)
    target = {"kind": kind, "target_id": target_id}
    binding = target_usd_binding(scene_binding_diagnostics, target)
    usd_prim_path = str(
        isaac_entry.get("usd_prim_path")
        or binding.get("usd_prim_path")
        or _dict(_dict(isaac_entry.get("usd_world_bounds")).get("prim")).get("path")
        or ""
    )
    mujoco_category = _object_category_key(mujoco_entry.get("category"))
    isaac_category = _object_category_key(
        isaac_entry.get("category") or isaac_entry.get("usd_category") or binding.get("category")
    )
    mujoco_position = _vec3_or_none(mujoco_entry.get("position"))
    isaac_position = _isaac_index_position(isaac_entry)
    pose_delta = (
        round(_vec_distance(mujoco_position, isaac_position), 6)
        if mujoco_position is not None and isaac_position is not None
        else None
    )
    mujoco_render = _mujoco_view_render_contract(mujoco_contract, anchor_id=target_id)
    isaac_render = _isaac_view_render_contract(isaac_contract, usd_prim_path=usd_prim_path)
    render_delta = _view_render_contract_delta(
        suspicion="object_material_texture_binding_contract",
        mujoco=mujoco_render,
        isaac=isaac_render,
    )
    return {
        "kind": kind,
        "target_id": target_id,
        "binding_status": _object_binding_status(mujoco_entry, isaac_entry, usd_prim_path),
        "selected_public_target": _is_selected_public_target(
            scene_binding_diagnostics,
            kind,
            target_id,
        ),
        "mujoco": _compact_mujoco_object_entry(mujoco_entry),
        "isaac": compact_isaac_index_entry(isaac_entry, usd_prim_path=usd_prim_path),
        "category_status": _object_category_status(
            mujoco_category=mujoco_category,
            isaac_category=isaac_category,
            mujoco_entry=mujoco_entry,
            isaac_entry=isaac_entry,
        ),
        "pose_status": _object_pose_status(mujoco_position, isaac_position, pose_delta),
        "pose_delta_m": pose_delta,
        "support_status": _object_support_status(mujoco_entry, isaac_entry),
        "state_status": _object_state_status(
            target_id=target_id,
            kind=kind,
            mujoco_entry=mujoco_entry,
            isaac_entry=isaac_entry,
            mujoco_state=mujoco_state,
            isaac_state=isaac_state,
            isaac_contract=isaac_contract,
            usd_prim_path=usd_prim_path,
        ),
        "visual_state_contract": visual_state.object_visual_state_contract(
            target_id=target_id,
            kind=kind,
            mujoco_entry=mujoco_entry,
            isaac_entry=isaac_entry,
            mujoco_state=mujoco_state,
            isaac_contract=isaac_contract,
            usd_prim_path=usd_prim_path,
        ),
        "rgb_view_evidence": rgb_evidence.object_rgb_view_evidence(
            kind=kind,
            target_id=target_id,
            locations=locations,
            output_dir=output_dir,
        ),
        "render_contract_delta": _compact_render_contract_delta(render_delta),
        "render_contract": {
            "mujoco_status": mujoco_render.get("status"),
            "isaac_status": isaac_render.get("status"),
            "mujoco_visual_geom_count": mujoco_render.get("visual_geom_count"),
            "isaac_material_binding_count": isaac_render.get("material_binding_count"),
            "mujoco_materials": mujoco_render.get("materials"),
            "isaac_materials": isaac_render.get("materials"),
            "mujoco_texture_basenames": material_checks.path_basenames(
                [str(value) for value in mujoco_render.get("texture_files") or []]
            ),
            "isaac_texture_basenames": material_checks.path_basenames(
                [str(value) for value in isaac_render.get("texture_files") or []]
            ),
        },
    }


def _mujoco_state_entry(state: dict[str, Any], kind: str, target_id: str) -> dict[str, Any]:
    group = "receptacles" if kind == "receptacle" else "objects"
    return _dict(_dict(state.get(group)).get(target_id))


def _isaac_index_entry(state: dict[str, Any], kind: str, target_id: str) -> dict[str, Any]:
    group = "receptacle_index" if kind == "receptacle" else "object_index"
    return _dict(_dict(state.get(group)).get(target_id))


def isaac_effective_index_entry(
    state: dict[str, Any],
    kind: str,
    target_id: str,
) -> dict[str, Any]:
    entry = _isaac_index_entry(state, kind, target_id)
    if kind != "object":
        return entry
    pose = _dict(_dict(_dict(state.get("semantic_pose_state")).get("object_poses")).get(target_id))
    if not pose:
        return entry
    effective = dict(entry)
    position = _vec3_or_none(pose.get("position"))
    if position is not None:
        effective["position"] = [round(float(value), 6) for value in position]
        effective["position_source"] = str(pose.get("position_source") or "semantic_pose_state")
        effective["semantic_pose_position_applied"] = (
            _dict(_dict(state.get("semantic_pose_state")).get("semantic_pose_view_capture")).get(
                "rendered_to_usd"
            )
            is True
        ) or _dict(state.get("semantic_pose_view_capture")).get("rendered_to_usd") is True
    if pose.get("support_receptacle_id"):
        effective["support_receptacle_id"] = str(pose.get("support_receptacle_id"))
    if pose.get("support_usd_prim_path"):
        effective["support_usd_prim_path"] = str(pose.get("support_usd_prim_path"))
    if pose.get("placement_support_status"):
        effective["placement_support_status"] = str(pose.get("placement_support_status"))
    if pose.get("placement_resolution_source"):
        effective["placement_resolution_source"] = str(pose.get("placement_resolution_source"))
    return effective


def isaac_index_usd_prim_path(entry: dict[str, Any]) -> str:
    return str(
        entry.get("usd_prim_path")
        or _dict(_dict(entry.get("usd_world_bounds")).get("prim")).get("path")
        or ""
    )


def _isaac_index_position(entry: dict[str, Any]) -> tuple[float, float, float] | None:
    position = _vec3_or_none(entry.get("position"))
    if position is not None:
        return position
    bounds = _dict(entry.get("usd_world_bounds"))
    center = _vec3_or_none(bounds.get("center"))
    if center is not None:
        return center
    return None


def _object_binding_status(
    mujoco_entry: dict[str, Any],
    isaac_entry: dict[str, Any],
    usd_prim_path: str,
) -> str:
    if not mujoco_entry and not isaac_entry:
        return "missing_both"
    if not mujoco_entry:
        return "missing_mujoco_state"
    if not isaac_entry:
        return "missing_isaac_index"
    if not usd_prim_path:
        return "missing_usd_prim_path"
    if (
        isaac_entry.get("geometry_status") == "missing"
        or isaac_entry.get("valid_stage_prim") is False
    ):
        return "isaac_geometry_gap"
    if isaac_entry.get("has_renderable_geometry") is False:
        return "isaac_geometry_gap"
    return "bound_in_both"


def _object_category_status(
    *,
    mujoco_category: str,
    isaac_category: str,
    mujoco_entry: dict[str, Any],
    isaac_entry: dict[str, Any],
) -> str:
    if not mujoco_entry or not isaac_entry:
        return "missing_entry"
    if not mujoco_category or not isaac_category:
        return "missing_category"
    return "category_aligned" if mujoco_category == isaac_category else "category_delta"


def _object_pose_status(
    mujoco_position: tuple[float, float, float] | None,
    isaac_position: tuple[float, float, float] | None,
    pose_delta: float | None,
) -> str:
    if mujoco_position is None or isaac_position is None or pose_delta is None:
        return "pose_missing"
    if pose_delta <= OBJECT_PARITY_POSE_THRESHOLD_M:
        return "pose_aligned"
    return "pose_delta"


def _object_support_status(mujoco_entry: dict[str, Any], isaac_entry: dict[str, Any]) -> str:
    if not mujoco_entry or not isaac_entry:
        return "missing_entry"
    mujoco_parent = str(
        mujoco_entry.get("location_id")
        or mujoco_entry.get("contained_in")
        or mujoco_entry.get("parent")
        or ""
    )
    isaac_parent = str(isaac_entry.get("parent") or isaac_entry.get("support_receptacle_id") or "")
    if not mujoco_parent and not isaac_parent:
        return "support_not_reported"
    if not mujoco_parent and isaac_parent:
        return "support_available_in_isaac_only"
    if mujoco_parent and not isaac_parent:
        return "support_available_in_mujoco_only"
    if mujoco_parent == isaac_parent:
        return "support_metadata_aligned"
    return "support_metadata_delta"


def _object_state_status(
    *,
    target_id: str,
    kind: str,
    mujoco_entry: dict[str, Any],
    isaac_entry: dict[str, Any],
    mujoco_state: dict[str, Any],
    isaac_state: dict[str, Any],
    isaac_contract: dict[str, Any],
    usd_prim_path: str,
) -> str:
    articulations = _dict(_dict(isaac_state.get("semantic_pose_state")).get("articulations"))
    articulation = _dict(articulations.get(target_id))
    category = _object_category_key(
        mujoco_entry.get("category")
        or isaac_entry.get("category")
        or isaac_entry.get("usd_category")
    )
    if kind != "receptacle" and not articulation:
        visual_contract = visual_state.object_visual_state_contract(
            target_id=target_id,
            kind=kind,
            mujoco_entry=mujoco_entry,
            isaac_entry=isaac_entry,
            mujoco_state=mujoco_state,
            isaac_contract=isaac_contract,
            usd_prim_path=usd_prim_path,
        )
        status = str(visual_contract.get("status") or "")
        if status in {
            "visual_state_static_ref_baked",
            "visual_state_articulation_physics_preserved",
        }:
            return status
        if category in visual_state.OBJECT_VISUAL_STATE_CATEGORIES or status != "not_applicable":
            return "visual_state_unverified"
        return "not_applicable"
    mujoco_open = target_id in {
        str(value) for value in mujoco_state.get("open_receptacle_ids") or []
    }
    isaac_open_ids = {str(value) for value in isaac_state.get("open_receptacle_ids") or []}
    isaac_open = target_id in isaac_open_ids or articulation.get("open") is True
    if mujoco_open != isaac_open:
        return "state_delta"
    if isaac_open and articulation and articulation.get("rendered_to_usd") is False:
        return "state_not_rendered_to_usd"
    return "state_aligned"


def _is_selected_public_target(
    scene_binding_diagnostics: dict[str, Any],
    kind: str,
    target_id: str,
) -> bool:
    groups = (
        ("selected_target_receptacle_bindings",)
        if kind == "receptacle"
        else ("selected_object_bindings",)
    )
    return any(target_id in _dict(scene_binding_diagnostics.get(group)) for group in groups)


def _compact_mujoco_object_entry(entry: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "object_id",
        "receptacle_id",
        "category",
        "name",
        "upstream_object_id",
        "location_id",
        "contained_in",
        "pickupable",
        "position",
        "support_top_z",
    )
    return {key: entry.get(key) for key in keys if key in entry}


def _object_category_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def compact_isaac_index_entry(entry: dict[str, Any], *, usd_prim_path: str) -> dict[str, Any]:
    keys = (
        "asset_id",
        "category",
        "usd_category",
        "metadata_object_id",
        "metadata_handle",
        "parent",
        "geometry_status",
        "has_renderable_geometry",
        "mesh_descendant_count",
        "renderable_descendant_count",
        "missing_referenced_asset_count",
        "valid_stage_prim",
        "position",
        "position_source",
        "semantic_pose_position_applied",
        "support_receptacle_id",
        "placement_support_status",
    )
    compact = {key: entry.get(key) for key in keys if key in entry}
    if usd_prim_path:
        compact["usd_prim_path"] = usd_prim_path
    bounds = _dict(entry.get("usd_world_bounds"))
    if bounds:
        compact["usd_world_bounds"] = {
            key: bounds.get(key) for key in ("center", "size", "min", "max") if key in bounds
        }
    return compact


def _compact_render_contract_delta(delta: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "mujoco_status",
        "isaac_status",
        "mujoco_material_count",
        "isaac_material_count",
        "mujoco_texture_count",
        "isaac_texture_count",
        "material_names_only_in_mujoco",
        "material_names_only_in_isaac",
        "texture_files_only_in_mujoco",
        "texture_files_only_in_isaac",
    )
    return {key: delta.get(key) for key in keys if key in delta}


def _status_counts(values: Any) -> dict[str, int]:
    collected = [str(value) for value in values if value]
    return {name: collected.count(name) for name in sorted(set(collected))}


def target_usd_binding(
    scene_binding_diagnostics: dict[str, Any],
    target: dict[str, Any],
) -> dict[str, Any]:
    target_id = str(target.get("target_id") or "")
    if not target_id:
        return {}
    if target.get("kind") == "receptacle":
        groups = ("receptacle_bindings", "selected_target_receptacle_bindings")
    else:
        groups = ("object_bindings", "selected_object_bindings")
    for group in groups:
        bindings = _dict(scene_binding_diagnostics.get(group))
        binding = _dict(bindings.get(target_id))
        if binding:
            return binding
    return {}


def compact_target_binding(binding: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "public_id",
        "kind",
        "category",
        "usd_prim_path",
        "match_strategy",
        "geometry_status",
        "has_renderable_geometry",
        "mesh_descendant_count",
        "renderable_descendant_count",
        "missing_referenced_asset_count",
    )
    return {key: binding.get(key) for key in keys if key in binding}


def _bound_ids_from_groups(
    scene_binding_diagnostics: dict[str, Any],
    groups: tuple[str, ...],
) -> set[str]:
    ids: set[str] = set()
    for group in groups:
        bindings = _dict(scene_binding_diagnostics.get(group))
        for target_id, raw_binding in bindings.items():
            binding = _dict(raw_binding)
            if binding.get("valid_stage_prim") is False:
                continue
            if binding.get("geometry_status") == "missing":
                continue
            ids.add(str(target_id))
    return ids


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _vec3_or_none(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return None


def _vec_distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))
