#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

SCHEMA = "roboclaws_molmospaces_flattened_semantic_usd_v1"
DEFAULT_RENDERING_PARITY_PRESET = "combined-material-light"
COMBINED_MATERIAL_LIGHT_ROTATE_X_DEG = 25.0
LABEL_INSTANCES = ("class", "kind", "usd_prim_path")
RENDERABLE_TYPE_NAMES = {"Mesh", "Cube", "Sphere", "Capsule", "Cone", "Cylinder"}
PHYSICS_API_SCHEMA_NAMES = {
    "PhysicsArticulationRootAPI",
    "PhysicsCollisionAPI",
    "PhysicsFilteredPairsAPI",
    "PhysicsMassAPI",
    "PhysicsRigidBodyAPI",
}
PHYSICS_PRIM_TYPE_NAMES = {
    "PhysicsFixedJoint",
    "PhysicsPrismaticJoint",
    "PhysicsRevoluteJoint",
}
PHYSICS_PROPERTY_PREFIXES = ("physics:", "physx")
MOLMOSPACES_RECEPTACLE_CATEGORY_NORMS = {
    "bed",
    "bookshelf",
    "chair",
    "countertop",
    "desk",
    "diningtable",
    "dresser",
    "fridge",
    "garbagecan",
    "shelf",
    "shelvingunit",
    "sink",
    "sofa",
    "stand",
    "toilet",
    "tvstand",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compose a MolmoSpaces scene USD, flatten it, and author Isaac 5 semantic "
            "LabelsAPI metadata directly on renderable Mesh/Gprim targets."
        )
    )
    parser.add_argument("--scene-usd-path", type=Path, required=True)
    parser.add_argument(
        "--mujoco-scene-xml-path",
        type=Path,
        help=(
            "Optional source MuJoCo scene XML. When provided, articulated visual "
            "box/flap Xforms in the prepared USD are baked to the MJCF joint ref "
            "endpoint before physics state is stripped."
        ),
    )
    parser.add_argument("--output-usd-path", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument(
        "--label-containers",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also label the metadata root prims, not only renderable descendants.",
    )
    parser.add_argument(
        "--rendering-parity-preset",
        choices=("combined-material-light", "source-preserving"),
        default=DEFAULT_RENDERING_PARITY_PRESET,
        help=(
            "Prepared-USD rendering preset. The default applies the validated "
            "DistantLight rotateX=+25 while preserving source USD material texture "
            "scale/fallback values; 'source-preserving' keeps source USD material "
            "and light settings."
        ),
    )
    parser.add_argument(
        "--material-texture-scale-mode",
        choices=("none", "identity", "square"),
        default=None,
        help=(
            "Optional override for UsdUVTexture scale/fallback inputs. Omit this to use "
            "the selected rendering parity preset."
        ),
    )
    parser.add_argument(
        "--freeze-visual-physics",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Strip physics APIs/joints from the flattened report USD after visual xforms "
            "are baked. This keeps Isaac capture from re-solving THOR articulated assets "
            "such as Box flaps away from the MuJoCo visual pose."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = prepare_flattened_semantic_usd(
        scene_usd_path=args.scene_usd_path,
        mujoco_scene_xml_path=args.mujoco_scene_xml_path,
        output_usd_path=args.output_usd_path,
        summary_output=args.summary_output,
        label_containers=args.label_containers,
        rendering_parity_preset=args.rendering_parity_preset,
        material_texture_scale_mode=args.material_texture_scale_mode,
        freeze_visual_physics=args.freeze_visual_physics,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] in {"ready", "partial"} else 2


def prepare_flattened_semantic_usd(
    *,
    scene_usd_path: Path,
    mujoco_scene_xml_path: Path | None = None,
    output_usd_path: Path,
    summary_output: Path | None = None,
    label_containers: bool = True,
    rendering_parity_preset: str = DEFAULT_RENDERING_PARITY_PRESET,
    material_texture_scale_mode: str | None = None,
    freeze_visual_physics: bool = True,
) -> dict[str, Any]:
    from pxr import Sdf, Usd, UsdGeom

    stage = Usd.Stage.Open(str(scene_usd_path))
    if stage is None:
        raise RuntimeError(f"Could not open scene USD: {scene_usd_path}")
    stage.Load()

    flattened_layer = stage.Flatten()
    output_usd_path.parent.mkdir(parents=True, exist_ok=True)
    if output_usd_path.exists():
        output_usd_path.unlink()
    output_layer = Sdf.Layer.CreateNew(str(output_usd_path))
    output_layer.ImportFromString(flattened_layer.ExportToString())
    output_layer.Save()
    metadata_copied = _copy_metadata_next_to_output(
        scene_usd_path=scene_usd_path,
        output_usd_path=output_usd_path,
    )

    flat_stage = Usd.Stage.Open(str(output_usd_path))
    if flat_stage is None:
        raise RuntimeError(f"Could not open flattened USD: {output_usd_path}")

    metadata = _load_molmospaces_scene_metadata(scene_usd_path)
    prim_paths_by_name = _prim_paths_by_name(flat_stage)
    entries = _metadata_entries(metadata=metadata, prim_paths_by_name=prim_paths_by_name)
    label_summary = _author_semantic_labels(
        stage=flat_stage,
        entries=entries,
        usd_geom=UsdGeom,
        label_containers=label_containers,
    )
    visual_joint_endpoint_pose_summary = _apply_mujoco_visual_joint_endpoint_pose(
        stage=flat_stage,
        mujoco_scene_xml_path=mujoco_scene_xml_path,
    )
    visual_physics_summary = (
        _freeze_visual_physics(flat_stage)
        if freeze_visual_physics
        else _visual_physics_not_frozen()
    )
    flat_stage.GetRootLayer().Save()
    preset = _rendering_parity_preset(rendering_parity_preset)
    effective_material_texture_scale_mode = (
        material_texture_scale_mode
        if material_texture_scale_mode is not None
        else str(preset["material_texture_scale_mode"])
    )
    material_conversion_summary = _apply_material_texture_scale_candidate(
        output_usd_path=output_usd_path,
        mode=effective_material_texture_scale_mode,
    )
    light_conversion_summary = _apply_distant_light_orientation_candidate(
        output_usd_path=output_usd_path,
        rotate_x=preset["distant_light_rotate_x"],
    )
    default_rendering_path_status = _default_rendering_path_status(
        rendering_parity_preset=rendering_parity_preset,
        material_conversion_summary=material_conversion_summary,
        light_conversion_summary=light_conversion_summary,
    )

    blockers = []
    if not entries:
        blockers.append("No MolmoSpaces scene_metadata objects matched flattened USD prim names.")
    if not label_summary["renderable_labeled_prim_count"]:
        blockers.append("No renderable Mesh/Gprim semantic label targets were authored.")
    if _mujoco_visual_joint_endpoint_pose_blocking(visual_joint_endpoint_pose_summary):
        blockers.append(
            "Requested MuJoCo visual joint endpoint pose baking did not update every "
            "matched articulated visual target."
        )
    status = (
        "ready"
        if not blockers
        else "partial"
        if label_summary["labeled_entry_count"]
        else "blocked"
    )
    summary = {
        "schema": SCHEMA,
        "status": status,
        "source_scene_usd_path": str(scene_usd_path),
        "output_usd_path": str(output_usd_path),
        "source_stage_prim_count": sum(1 for _ in stage.Traverse()),
        "flattened_stage_prim_count": sum(1 for _ in flat_stage.Traverse()),
        "metadata_entry_count": len(metadata),
        "matched_entry_count": len(entries),
        "label_instances": list(LABEL_INSTANCES),
        "label_containers": bool(label_containers),
        "rendering_parity_preset": rendering_parity_preset,
        "material_texture_scale_mode": effective_material_texture_scale_mode,
        "material_texture_scale_rewrite_count": material_conversion_summary[
            "texture_scale_rewrite_count"
        ],
        "material_texture_scale_default_candidate": material_conversion_summary[
            "default_candidate"
        ],
        "distant_light_rotate_x": light_conversion_summary["rotate_x"],
        "distant_light_rotate_x_rewrite_count": light_conversion_summary["rewrite_count"],
        "distant_light_rotate_x_insert_count": light_conversion_summary["insert_count"],
        "distant_light_rotate_x_default_candidate": light_conversion_summary["default_candidate"],
        "default_rendering_path_status": default_rendering_path_status,
        "default_rendering_path_uses_combined_material_light": (
            default_rendering_path_status == "default_rendering_path_uses_combined_material_light"
        ),
        "visual_physics_freeze_enabled": bool(freeze_visual_physics),
        **visual_joint_endpoint_pose_summary,
        **visual_physics_summary,
        "scene_metadata_copied": metadata_copied,
        "blockers": blockers,
        **label_summary,
    }
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return summary


def _apply_mujoco_visual_joint_endpoint_pose(
    *,
    stage: Any,
    mujoco_scene_xml_path: Path | None,
) -> dict[str, Any]:
    if mujoco_scene_xml_path is None:
        return {
            "mujoco_visual_joint_endpoint_pose_status": "not_requested",
            "mujoco_visual_joint_endpoint_pose_source": None,
            "mujoco_visual_joint_endpoint_pose_target_count": 0,
            "mujoco_visual_joint_endpoint_pose_corrected_count": 0,
            "mujoco_visual_joint_endpoint_pose_missing_count": 0,
            "mujoco_visual_joint_endpoint_pose_samples": [],
            "mujoco_visual_joint_endpoint_pose_missing_samples": [],
        }
    if not mujoco_scene_xml_path.is_file():
        return {
            "mujoco_visual_joint_endpoint_pose_status": "missing_mujoco_scene_xml",
            "mujoco_visual_joint_endpoint_pose_source": str(mujoco_scene_xml_path),
            "mujoco_visual_joint_endpoint_pose_target_count": 0,
            "mujoco_visual_joint_endpoint_pose_corrected_count": 0,
            "mujoco_visual_joint_endpoint_pose_missing_count": 0,
            "mujoco_visual_joint_endpoint_pose_samples": [],
            "mujoco_visual_joint_endpoint_pose_missing_samples": [],
        }

    entries = _mujoco_flap_visual_joint_endpoint_entries(mujoco_scene_xml_path)
    paths_by_name = _prim_paths_by_name(stage)
    corrected: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for entry in entries:
        prim_path = _resolve_mujoco_visual_joint_prim_path(
            paths_by_name=paths_by_name,
            mesh_name=str(entry["mesh_name"]),
            ancestor_names=[str(value) for value in entry.get("ancestor_names") or []],
        )
        if prim_path is None:
            missing.append(
                {
                    "mesh_name": entry["mesh_name"],
                    "joint_name": entry["joint_name"],
                    "body_name": entry["body_name"],
                }
            )
            continue
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            missing.append(
                {
                    "mesh_name": entry["mesh_name"],
                    "joint_name": entry["joint_name"],
                    "body_name": entry["body_name"],
                    "usd_prim_path": prim_path,
                }
            )
            continue
        endpoint_quat = _mujoco_body_endpoint_quat(
            body_quat=[float(value) for value in entry["body_quat"]],
        )
        if not _set_usd_xform_orient(prim=prim, quat=endpoint_quat):
            missing.append(
                {
                    "mesh_name": entry["mesh_name"],
                    "joint_name": entry["joint_name"],
                    "body_name": entry["body_name"],
                    "usd_prim_path": prim_path,
                    "reason": "missing_or_invalid_xform_orient",
                }
            )
            continue
        corrected.append(
            {
                "mesh_name": entry["mesh_name"],
                "joint_name": entry["joint_name"],
                "body_name": entry["body_name"],
                "usd_prim_path": prim_path,
                "axis": entry["axis"],
                "ref": entry["ref"],
                "endpoint_quat": endpoint_quat,
            }
        )
    status = (
        "mujoco_visual_joint_endpoint_pose_applied"
        if corrected and not missing
        else "mujoco_visual_joint_endpoint_pose_partial"
        if corrected
        else "mujoco_visual_joint_endpoint_pose_no_targets"
    )
    return {
        "mujoco_visual_joint_endpoint_pose_status": status,
        "mujoco_visual_joint_endpoint_pose_source": str(mujoco_scene_xml_path),
        "mujoco_visual_joint_endpoint_pose_target_count": len(entries),
        "mujoco_visual_joint_endpoint_pose_corrected_count": len(corrected),
        "mujoco_visual_joint_endpoint_pose_missing_count": len(missing),
        "mujoco_visual_joint_endpoint_pose_samples": corrected[:25],
        "mujoco_visual_joint_endpoint_pose_missing_samples": missing[:25],
    }


def _mujoco_visual_joint_endpoint_pose_blocking(summary: dict[str, Any]) -> bool:
    status = str(summary.get("mujoco_visual_joint_endpoint_pose_status") or "")
    if status in {"not_requested", "mujoco_visual_joint_endpoint_pose_applied"}:
        return False
    target_count = int(summary.get("mujoco_visual_joint_endpoint_pose_target_count") or 0)
    missing_count = int(summary.get("mujoco_visual_joint_endpoint_pose_missing_count") or 0)
    return status == "missing_mujoco_scene_xml" or (target_count > 0 and missing_count > 0)


def _mujoco_flap_visual_joint_endpoint_entries(
    mujoco_scene_xml_path: Path,
) -> list[dict[str, Any]]:
    try:
        root = ElementTree.parse(mujoco_scene_xml_path).getroot()
    except ElementTree.ParseError:
        return []
    worldbody = root.find("worldbody")
    if worldbody is None:
        return []
    entries: list[dict[str, Any]] = []

    def visit(body: ElementTree.Element, ancestors: list[str]) -> None:
        body_name = str(body.attrib.get("name") or "")
        next_ancestors = [*ancestors, body_name] if body_name else list(ancestors)
        joint = _single_visual_flap_joint(body)
        if joint is not None:
            mesh_names = [
                str(geom.attrib.get("mesh") or "")
                for geom in body.findall("geom")
                if str(geom.attrib.get("mesh") or "")
            ]
            for mesh_name in mesh_names:
                if "flap" not in mesh_name.lower():
                    continue
                axis = _float_list(joint.attrib.get("axis"), default=[1.0, 0.0, 0.0])
                ref = _float_or_none(joint.attrib.get("ref"))
                if ref is None or len(axis) < 3:
                    continue
                entries.append(
                    {
                        "body_name": body_name,
                        "ancestor_names": next_ancestors,
                        "joint_name": str(joint.attrib.get("name") or ""),
                        "mesh_name": mesh_name,
                        "axis": axis[:3],
                        "ref": ref,
                        "body_quat": _float_list(
                            body.attrib.get("quat"),
                            default=[1.0, 0.0, 0.0, 0.0],
                        )[:4],
                    }
                )
        for child in body.findall("body"):
            visit(child, next_ancestors)

    for body in worldbody.findall("body"):
        visit(body, [])
    return entries


def _single_visual_flap_joint(body: ElementTree.Element) -> ElementTree.Element | None:
    joints = list(body.findall("joint"))
    if len(joints) != 1:
        return None
    joint = joints[0]
    joint_name = str(joint.attrib.get("name") or "").lower()
    joint_type = str(joint.attrib.get("type") or "hinge").lower()
    if joint_type != "hinge":
        return None
    if "flap" not in joint_name:
        return None
    return joint


def _resolve_mujoco_visual_joint_prim_path(
    *,
    paths_by_name: dict[str, list[str]],
    mesh_name: str,
    ancestor_names: list[str],
) -> str | None:
    candidates = list(paths_by_name.get(mesh_name) or [])
    if not candidates:
        return None
    ancestor_set = {name for name in ancestor_names if name}

    def rank(path: str) -> tuple[int, int, str]:
        normalized = f"/{path.strip('/')}/"
        has_geometry = "/geometry/" in normalized.lower()
        ancestor_hits = sum(1 for name in ancestor_set if f"/{name}/" in normalized)
        return (0 if has_geometry else 1, -ancestor_hits, normalized.count("/"), path)

    return sorted(candidates, key=rank)[0]


def _mujoco_body_endpoint_quat(
    *,
    body_quat: list[float],
) -> list[float]:
    # In MJCF, a hinge joint's `ref` is the qpos value represented by the XML body
    # pose. For these MolmoSpaces flap assets, qpos is at ref/range endpoint, so
    # the MuJoCo visual ref pose is the authored body quat, not body_quat * ref.
    quat = _normalize_quat(body_quat)
    if quat[0] < 0:
        quat = [-value for value in quat]
    return [_round_float(value) for value in quat]


def _normalize_quat(values: list[float]) -> list[float]:
    padded = [float(value) for value in values[:4]]
    while len(padded) < 4:
        padded.append(0.0)
    length = math.sqrt(sum(value * value for value in padded))
    if length <= 0:
        return [1.0, 0.0, 0.0, 0.0]
    return [value / length for value in padded]


def _set_usd_xform_orient(*, prim: Any, quat: list[float]) -> bool:
    from pxr import Gf, Sdf, Vt

    attr = prim.GetAttribute("xformOp:orient")
    if not attr or not attr.IsValid():
        return False
    type_name = attr.GetTypeName()
    if type_name == Sdf.ValueTypeNames.Quatd:
        attr.Set(Gf.Quatd(quat[0], Gf.Vec3d(*quat[1:4])))
    else:
        attr.Set(Gf.Quatf(quat[0], Gf.Vec3f(*quat[1:4])))
    order_attr = prim.GetAttribute("xformOpOrder")
    if order_attr and order_attr.IsValid():
        current = [str(value) for value in list(order_attr.Get() or [])]
        if "xformOp:orient" not in current:
            current.append("xformOp:orient")
            order_attr.Set(Vt.TokenArray(current))
    return True


def _float_list(raw: str | None, *, default: list[float]) -> list[float]:
    if raw is None:
        return list(default)
    values: list[float] = []
    for part in raw.split():
        try:
            values.append(float(part))
        except ValueError:
            return list(default)
    return values or list(default)


def _float_or_none(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _round_float(value: float) -> float:
    rounded = round(float(value), 8)
    return 0.0 if rounded == -0.0 else rounded


def _freeze_visual_physics(stage: Any) -> dict[str, Any]:
    removed_joint_paths: list[str] = []
    removed_api_schema_count = 0
    removed_property_count = 0
    for prim in list(stage.Traverse()):
        type_name = str(prim.GetTypeName() or "")
        if type_name in PHYSICS_PRIM_TYPE_NAMES:
            removed_joint_paths.append(str(prim.GetPath()))
            stage.RemovePrim(prim.GetPath())
            continue
        removed_api_schema_count += _remove_physics_api_schemas(prim)
        for prop_name in list(prim.GetPropertyNames()):
            if _is_physics_property_name(str(prop_name)):
                prim.RemoveProperty(prop_name)
                removed_property_count += 1
    return {
        "visual_physics_status": "frozen_static_visual_usd",
        "visual_physics_joint_removed_count": len(removed_joint_paths),
        "visual_physics_api_schema_removed_count": removed_api_schema_count,
        "visual_physics_property_removed_count": removed_property_count,
        "visual_physics_removed_joint_samples": removed_joint_paths[:25],
        "visual_physics_freeze_reason": (
            "Flattened USD already contains the visual xforms from the MolmoSpaces "
            "conversion. Removing physics schemas and joints prevents Isaac report "
            "capture from re-solving articulated THOR assets away from the MuJoCo "
            "visual/rest pose."
        ),
    }


def _visual_physics_not_frozen() -> dict[str, Any]:
    return {
        "visual_physics_status": "source_physics_preserved",
        "visual_physics_joint_removed_count": 0,
        "visual_physics_api_schema_removed_count": 0,
        "visual_physics_property_removed_count": 0,
        "visual_physics_removed_joint_samples": [],
        "visual_physics_freeze_reason": (
            "Physics schemas and joints were preserved by caller request."
        ),
    }


def _remove_physics_api_schemas(prim: Any) -> int:
    from pxr import Sdf, Vt

    removed = _remove_physics_api_schema_metadata(prim)
    attr = prim.GetAttribute("apiSchemas")
    if not attr or not attr.IsValid():
        return removed
    current = [str(value) for value in list(attr.Get() or [])]
    kept = [value for value in current if value not in PHYSICS_API_SCHEMA_NAMES]
    attr_removed = len(current) - len(kept)
    if not attr_removed:
        return removed
    attr.Set(Vt.TokenArray(kept))
    if not kept:
        prim.RemoveProperty("apiSchemas")
    elif attr.GetTypeName() != Sdf.ValueTypeNames.TokenArray:
        attr.Set(Vt.TokenArray(kept))
    return removed + attr_removed


def _remove_physics_api_schema_metadata(prim: Any) -> int:
    from pxr import Sdf

    api_schemas = prim.GetMetadata("apiSchemas")
    if api_schemas is None:
        return 0
    if isinstance(api_schemas, Sdf.TokenListOp):
        explicit = _filter_physics_api_schemas(api_schemas.explicitItems)
        prepended = _filter_physics_api_schemas(api_schemas.prependedItems)
        appended = _filter_physics_api_schemas(api_schemas.appendedItems)
        deleted = list(api_schemas.deletedItems or [])
        ordered = _filter_physics_api_schemas(api_schemas.orderedItems)
        removed = (
            len(api_schemas.explicitItems or [])
            + len(api_schemas.prependedItems or [])
            + len(api_schemas.appendedItems or [])
            + len(api_schemas.orderedItems or [])
            - len(explicit)
            - len(prepended)
            - len(appended)
            - len(ordered)
        )
        if not removed:
            return 0
        replacement = Sdf.TokenListOp()
        replacement.explicitItems = explicit
        replacement.prependedItems = prepended
        replacement.appendedItems = appended
        replacement.deletedItems = deleted
        replacement.orderedItems = ordered
        if explicit or prepended or appended or deleted or ordered:
            prim.SetMetadata("apiSchemas", replacement)
        else:
            prim.ClearMetadata("apiSchemas")
        return removed
    if isinstance(api_schemas, (list, tuple)):
        current = [str(value) for value in api_schemas]
        kept = _filter_physics_api_schemas(current)
        removed = len(current) - len(kept)
        if not removed:
            return 0
        if kept:
            prim.SetMetadata("apiSchemas", kept)
        else:
            prim.ClearMetadata("apiSchemas")
        return removed
    return 0


def _filter_physics_api_schemas(values: Any) -> list[str]:
    return [str(value) for value in values or [] if str(value) not in PHYSICS_API_SCHEMA_NAMES]


def _is_physics_property_name(name: str) -> bool:
    lowered = name.lower()
    return any(lowered.startswith(prefix) for prefix in PHYSICS_PROPERTY_PREFIXES)


def _rendering_parity_preset(name: str) -> dict[str, str | float | None]:
    if name == "combined-material-light":
        return {
            "material_texture_scale_mode": "none",
            "distant_light_rotate_x": COMBINED_MATERIAL_LIGHT_ROTATE_X_DEG,
        }
    if name == "source-preserving":
        return {
            "material_texture_scale_mode": "none",
            "distant_light_rotate_x": None,
        }
    raise ValueError(f"unsupported rendering parity preset: {name}")


def _apply_material_texture_scale_candidate(
    *,
    output_usd_path: Path,
    mode: str,
) -> dict[str, Any]:
    if mode == "none":
        return {
            "mode": mode,
            "texture_scale_rewrite_count": 0,
            "default_candidate": False,
        }
    text = output_usd_path.read_text(encoding="utf-8", errors="ignore")
    updated, rewrite_count = _rewrite_texture_scale_inputs(text, mode=mode)
    if rewrite_count:
        output_usd_path.write_text(updated, encoding="utf-8")
    return {
        "mode": mode,
        "texture_scale_rewrite_count": rewrite_count,
        "default_candidate": True,
    }


def _apply_distant_light_orientation_candidate(
    *,
    output_usd_path: Path,
    rotate_x: float | None,
) -> dict[str, Any]:
    if rotate_x is None:
        return {
            "rotate_x": None,
            "rewrite_count": 0,
            "insert_count": 0,
            "default_candidate": False,
        }
    text = output_usd_path.read_text(encoding="utf-8", errors="ignore")
    updated, rewrite_count, insert_count = _rewrite_distant_light_rotate_x(
        text,
        rotate_x=rotate_x,
    )
    if rewrite_count or insert_count:
        output_usd_path.write_text(updated, encoding="utf-8")
    return {
        "rotate_x": rotate_x,
        "rewrite_count": rewrite_count,
        "insert_count": insert_count,
        "default_candidate": True,
    }


def _default_rendering_path_status(
    *,
    rendering_parity_preset: str,
    material_conversion_summary: dict[str, Any],
    light_conversion_summary: dict[str, Any],
) -> str:
    if rendering_parity_preset == "source-preserving":
        return "source_preserving_rendering_path"
    material_ready = (
        material_conversion_summary.get("mode") == "none"
        and int(material_conversion_summary.get("texture_scale_rewrite_count") or 0) == 0
    )
    light_ready = light_conversion_summary.get("rotate_x") == COMBINED_MATERIAL_LIGHT_ROTATE_X_DEG
    if material_ready and light_ready:
        return "default_rendering_path_uses_combined_material_light"
    return "default_rendering_path_candidate_incomplete"


def _rewrite_texture_scale_inputs(text: str, *, mode: str) -> tuple[str, int]:
    def replacement(match: re.Match[str]) -> str:
        values = _parse_float_values(match.group(2))
        if not values:
            return match.group(0)
        if mode == "identity":
            rewritten = [1.0 for _ in values]
        elif mode == "square":
            rewritten = [value * value for value in values]
            if len(rewritten) >= 4:
                rewritten[3] = values[3]
        else:
            raise ValueError(f"unsupported material texture scale mode: {mode}")
        return f"{match.group(1)}({_format_float_list(rewritten)})"

    return re.subn(
        r"(float[234]? inputs:(?:scale|fallback) = )\(([^)]+)\)",
        replacement,
        text,
    )


def _rewrite_distant_light_rotate_x(text: str, *, rotate_x: float) -> tuple[str, int, int]:
    parts: list[str] = []
    cursor = 0
    rewrites = 0
    inserts = 0
    for match in re.finditer(r'(?m)^(\s*)def DistantLight "[^"]+"\s*\{\s*$', text):
        block_start = match.start()
        block_end = _balanced_block_end(text, match.end() - 1)
        if block_end is None:
            continue
        block = text[block_start:block_end]
        rewritten, count = re.subn(
            r"float xformOp:rotateX = [^\s]+",
            f"float xformOp:rotateX = {_format_float(rotate_x)}",
            block,
        )
        rewrites += count
        if count == 0:
            rewritten = _insert_distant_light_rotate_x(rewritten, rotate_x=rotate_x)
            inserts += int(rewritten != block)
        parts.append(text[cursor:block_start])
        parts.append(rewritten)
        cursor = block_end
    if not parts:
        return text, 0, 0
    parts.append(text[cursor:])
    return "".join(parts), rewrites, inserts


def _insert_distant_light_rotate_x(block: str, *, rotate_x: float) -> str:
    close_index = block.rfind("}")
    if close_index < 0:
        return block
    match = re.search(r'(?m)^(\s*)def DistantLight "', block)
    indent = match.group(1) + "    " if match else "    "
    insertion = (
        f"{indent}float xformOp:rotateX = {_format_float(rotate_x)}\n"
        f'{indent}uniform token[] xformOpOrder = ["xformOp:rotateX"]\n'
    )
    return block[:close_index] + insertion + block[close_index:]


def _balanced_block_end(text: str, open_brace_index: int) -> int | None:
    depth = 0
    for index in range(open_brace_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                if index + 1 < len(text) and text[index + 1] == "\n":
                    return index + 2
                return index + 1
    return None


def _parse_float_values(raw: str) -> list[float]:
    values: list[float] = []
    for part in raw.split(","):
        try:
            values.append(float(part.strip()))
        except ValueError:
            return []
    return values


def _format_float_list(values: list[float]) -> str:
    return ", ".join(_format_float(value) for value in values)


def _format_float(value: float) -> str:
    formatted = f"{value:.6g}"
    return "0" if formatted == "-0" else formatted


def _load_molmospaces_scene_metadata(scene_usd_path: Path) -> dict[str, dict[str, Any]]:
    metadata_path = scene_usd_path.parent / "scene_metadata.json"
    if not metadata_path.is_file():
        return {}
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    objects = payload.get("objects") if isinstance(payload, dict) else None
    if not isinstance(objects, dict):
        return {}
    return {
        str(handle): dict(info)
        for handle, info in objects.items()
        if isinstance(info, dict) and str(handle)
    }


def _copy_metadata_next_to_output(*, scene_usd_path: Path, output_usd_path: Path) -> bool:
    metadata_path = scene_usd_path.parent / "scene_metadata.json"
    if not metadata_path.is_file():
        return False
    output_metadata_path = output_usd_path.parent / "scene_metadata.json"
    output_metadata_path.write_text(metadata_path.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def _prim_paths_by_name(stage: Any) -> dict[str, list[str]]:
    paths_by_name: dict[str, list[str]] = {}
    for prim in stage.Traverse():
        paths_by_name.setdefault(prim.GetName(), []).append(str(prim.GetPath()))
    return paths_by_name


def _metadata_entries(
    *,
    metadata: dict[str, dict[str, Any]],
    prim_paths_by_name: dict[str, list[str]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for handle, raw_info in metadata.items():
        prim_path = _molmospaces_metadata_prim_path(handle, prim_paths_by_name)
        if prim_path is None:
            continue
        kind = "receptacle" if _is_molmospaces_receptacle_metadata(raw_info) else "object"
        category = str(raw_info.get("category") or _category_from_usd_name(handle))
        asset_id = str(raw_info.get("asset_id") or "")
        metadata_object_id = str(raw_info.get("object_id") or "")
        public_label = " ".join(part for part in (category, metadata_object_id, asset_id) if part)
        entries.append(
            {
                "metadata_handle": handle,
                "usd_prim_path": prim_path,
                "kind": kind,
                "category": category,
                "public_label": public_label or handle,
                "asset_id": asset_id,
                "metadata_object_id": metadata_object_id,
                "is_static": bool(raw_info.get("is_static")),
            }
        )
    return entries


def _molmospaces_metadata_prim_path(
    handle: str,
    prim_paths_by_name: dict[str, list[str]],
) -> str | None:
    candidates = list(prim_paths_by_name.get(handle) or [])
    if not candidates:
        return None
    return sorted(candidates, key=_molmospaces_prim_path_rank)[0]


def _molmospaces_prim_path_rank(prim_path: str) -> tuple[int, int, str]:
    normalized = f"/{prim_path.strip('/')}/"
    is_top_level_geometry = "/geometry/" in normalized.lower() and normalized.count("/") <= 4
    return (0 if is_top_level_geometry else 1, normalized.count("/"), prim_path)


def _is_molmospaces_receptacle_metadata(metadata: dict[str, Any]) -> bool:
    category = _norm(metadata.get("category"))
    if not category:
        return False
    if category in MOLMOSPACES_RECEPTACLE_CATEGORY_NORMS:
        return True
    return bool(metadata.get("children")) and metadata.get("is_static") is True


def _author_semantic_labels(
    *,
    stage: Any,
    entries: list[dict[str, Any]],
    usd_geom: Any,
    label_containers: bool,
) -> dict[str, Any]:
    requested = len(entries)
    labeled_entry_count = 0
    missing_prim_count = 0
    container_labeled_prim_count = 0
    renderable_labeled_prim_count = 0
    gprim_labeled_prim_count = 0
    mesh_labeled_prim_count = 0
    target_samples: list[dict[str, str]] = []
    missing_handles: list[str] = []

    for entry in entries:
        prim_path = str(entry["usd_prim_path"])
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            missing_prim_count += 1
            missing_handles.append(str(entry["metadata_handle"]))
            continue

        labels = _semantic_labels(entry=entry, prim_path=prim_path)
        targets = _semantic_label_targets(prim=prim, usd_geom=usd_geom)
        if label_containers:
            _set_semantic_labels(prim=prim, labels=labels)
            container_labeled_prim_count += 1
        for target in targets:
            _set_semantic_labels(prim=target, labels=labels)
            renderable_labeled_prim_count += 1
            classification = _target_classification(target, usd_geom=usd_geom)
            if classification["is_gprim"]:
                gprim_labeled_prim_count += 1
            if classification["type_name"] == "Mesh":
                mesh_labeled_prim_count += 1
            if len(target_samples) < 25:
                target_samples.append(
                    {
                        "metadata_handle": str(entry["metadata_handle"]),
                        "source_prim_path": prim_path,
                        "target_prim_path": classification["path"],
                        "target_type": classification["type_name"],
                        "target_kind": classification["kind"],
                    }
                )
        if targets or label_containers:
            labeled_entry_count += 1

    return {
        "requested_entry_count": requested,
        "labeled_entry_count": labeled_entry_count,
        "missing_prim_count": missing_prim_count,
        "container_labeled_prim_count": container_labeled_prim_count,
        "renderable_labeled_prim_count": renderable_labeled_prim_count,
        "gprim_labeled_prim_count": gprim_labeled_prim_count,
        "mesh_labeled_prim_count": mesh_labeled_prim_count,
        "missing_handles": missing_handles[:25],
        "target_samples": target_samples,
    }


def _semantic_label_targets(*, prim: Any, usd_geom: Any) -> list[Any]:
    from pxr import Usd

    targets: list[Any] = []
    for candidate in Usd.PrimRange(prim):
        if _prim_is_renderable(candidate, usd_geom=usd_geom):
            targets.append(candidate)
    return targets


def _prim_is_renderable(prim: Any, *, usd_geom: Any) -> bool:
    try:
        return bool(prim.IsA(usd_geom.Gprim))
    except Exception:
        return str(prim.GetTypeName() or "") in RENDERABLE_TYPE_NAMES


def _set_semantic_labels(*, prim: Any, labels: dict[str, str]) -> None:
    for instance_name, label in labels.items():
        _set_labels_api(prim=prim, instance_name=instance_name, labels=[label])


def _set_labels_api(*, prim: Any, instance_name: str, labels: list[str]) -> None:
    try:
        from pxr import UsdSemantics

        api = UsdSemantics.LabelsAPI.Apply(prim, instance_name)
        api.CreateLabelsAttr().Set(labels)
        return
    except Exception:
        pass

    attr = prim.CreateAttribute(f"semantics:labels:{instance_name}", _token_array_value_type())
    attr.Set(labels)
    _ensure_api_schema_token(prim=prim, schema=f"SemanticsLabelsAPI:{instance_name}")


def _token_array_value_type() -> Any:
    from pxr import Sdf

    return Sdf.ValueTypeNames.TokenArray


def _ensure_api_schema_token(*, prim: Any, schema: str) -> None:
    from pxr import Sdf, Vt

    attr = prim.GetAttribute("apiSchemas")
    current = list(attr.Get() or []) if attr and attr.IsValid() else []
    if schema in current:
        return
    current.append(schema)
    if not attr or not attr.IsValid():
        attr = prim.CreateAttribute("apiSchemas", Sdf.ValueTypeNames.TokenArray, custom=False)
    attr.Set(Vt.TokenArray(current))


def _semantic_labels(*, entry: dict[str, Any], prim_path: str) -> dict[str, str]:
    category = str(entry.get("category") or entry.get("public_label") or Path(prim_path).name)
    kind = str(entry.get("kind") or "scene_prim")
    return {
        "class": category,
        "kind": kind,
        "usd_prim_path": prim_path,
    }


def _target_classification(prim: Any, *, usd_geom: Any) -> dict[str, Any]:
    path = str(prim.GetPath())
    type_name = str(prim.GetTypeName() or "")
    is_gprim = _prim_is_renderable(prim, usd_geom=usd_geom)
    kind = "gprim" if is_gprim else "prim"
    if type_name:
        kind = f"{kind}:{type_name}"
    return {
        "path": path,
        "type_name": type_name,
        "kind": kind,
        "is_gprim": is_gprim,
    }


def _category_from_usd_name(value: str) -> str:
    normalized = _norm(value)
    return normalized or "unknown"


def _norm(value: object) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


if __name__ == "__main__":
    raise SystemExit(main())
