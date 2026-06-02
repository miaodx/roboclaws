#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "roboclaws_molmospaces_flattened_semantic_usd_v1"
LABEL_INSTANCES = ("class", "kind", "usd_prim_path")
RENDERABLE_TYPE_NAMES = {"Mesh", "Cube", "Sphere", "Capsule", "Cone", "Cylinder"}
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
    parser.add_argument("--output-usd-path", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument(
        "--label-containers",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also label the metadata root prims, not only renderable descendants.",
    )
    parser.add_argument(
        "--material-texture-scale-mode",
        choices=("none", "identity", "square"),
        default="none",
        help=(
            "Opt-in default-candidate material conversion for UsdUVTexture "
            "scale/fallback inputs. The default 'none' preserves source USD material "
            "response."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = prepare_flattened_semantic_usd(
        scene_usd_path=args.scene_usd_path,
        output_usd_path=args.output_usd_path,
        summary_output=args.summary_output,
        label_containers=args.label_containers,
        material_texture_scale_mode=args.material_texture_scale_mode,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] in {"ready", "partial"} else 2


def prepare_flattened_semantic_usd(
    *,
    scene_usd_path: Path,
    output_usd_path: Path,
    summary_output: Path | None = None,
    label_containers: bool = True,
    material_texture_scale_mode: str = "none",
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
    flat_stage.GetRootLayer().Save()
    material_conversion_summary = _apply_material_texture_scale_candidate(
        output_usd_path=output_usd_path,
        mode=material_texture_scale_mode,
    )

    blockers = []
    if not entries:
        blockers.append("No MolmoSpaces scene_metadata objects matched flattened USD prim names.")
    if not label_summary["renderable_labeled_prim_count"]:
        blockers.append("No renderable Mesh/Gprim semantic label targets were authored.")
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
        "material_texture_scale_mode": material_texture_scale_mode,
        "material_texture_scale_rewrite_count": material_conversion_summary[
            "texture_scale_rewrite_count"
        ],
        "material_texture_scale_default_candidate": material_conversion_summary[
            "default_candidate"
        ],
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
