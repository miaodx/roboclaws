from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from roboclaws.household.generated_mess import GENERATED_MESS_MANIFEST_SCHEMA
from roboclaws.launch.scene_sampler import _molmospaces_get_scenes_args


def load_generated_mess_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"generated mess manifest must be a JSON object: {path}")
    if manifest.get("schema") != GENERATED_MESS_MANIFEST_SCHEMA:
        raise ValueError(
            "generated mess manifest schema mismatch: "
            f"{manifest.get('schema')} != {GENERATED_MESS_MANIFEST_SCHEMA}"
        )
    return manifest


def prepare_molmospaces_scene(
    *,
    scene_source: str,
    scene_index: int,
    get_scenes: Callable[..., Any],
    get_scenes_root: Callable[[], Any],
    install_scene_with_objects_and_grasps_from_path: Callable[[Path], Any],
) -> tuple[Path, dict[str, Any]]:
    scene_xml, resolution = resolve_molmospaces_scene_xml(
        scene_source=scene_source,
        scene_index=scene_index,
        get_scenes=get_scenes,
        scenes_root=Path(get_scenes_root()),
    )
    install_scene_with_objects_and_grasps_from_path(scene_xml)
    resolution["install_method"] = "install_scene_with_objects_and_grasps_from_path"
    return scene_xml, resolution


def resolve_molmospaces_scene_xml(
    *,
    scene_source: str,
    scene_index: int,
    get_scenes: Callable[..., Any],
    scenes_root: Path,
) -> tuple[Path, dict[str, Any]]:
    dataset_name, split = _molmospaces_get_scenes_args(scene_source)
    mapping = get_scenes(dataset_name, split)
    if isinstance(mapping, tuple):
        mapping = mapping[0]
    split_mapping = mapping.get(split) if isinstance(mapping, dict) else None
    if not isinstance(split_mapping, dict):
        raise FileNotFoundError(
            f"MolmoSpaces get_scenes({dataset_name!r}, {split!r}) has no {split!r} map"
        )
    if scene_index not in split_mapping:
        raise FileNotFoundError(
            "MolmoSpaces scene index missing from get_scenes map: "
            f"scene_source={scene_source!r} scene_index={scene_index}"
        )
    raw_ref = split_mapping[scene_index]
    scene_xml, ref_role, path_was_relative = scene_xml_path_from_ref(
        raw_ref,
        scenes_root=scenes_root,
    )
    if scene_xml is None:
        raise FileNotFoundError(
            "MolmoSpaces get_scenes ref does not contain a scene XML path: "
            f"scene_source={scene_source!r} scene_index={scene_index} "
            f"raw_ref_type={type(raw_ref).__name__}"
        )
    return scene_xml, {
        "schema": "molmospaces_scene_resolution_v1",
        "scene_source": scene_source,
        "scene_index": scene_index,
        "dataset_name": dataset_name,
        "split": split,
        "raw_ref_type": type(raw_ref).__name__,
        "selected_ref_role": ref_role,
        "path_was_relative": path_was_relative,
        "scene_xml": str(scene_xml),
    }


def scene_xml_path_from_ref(
    raw_ref: Any,
    *,
    scenes_root: Path,
) -> tuple[Path | None, str, bool]:
    if isinstance(raw_ref, str | Path):
        path, path_was_relative = normalize_molmospaces_scene_ref_path(
            raw_ref,
            scenes_root=scenes_root,
        )
        if path.suffix == ".xml":
            return path, "path", path_was_relative
        return None, "path", path_was_relative
    if isinstance(raw_ref, dict):
        for role in ("base", "physics", "ceiling"):
            raw_path = raw_ref.get(role)
            path = scene_ref_candidate_xml_path(raw_path, scenes_root=scenes_root)
            if path is not None:
                return path[0], role, path[1]
        for role, raw_path in sorted(raw_ref.items()):
            path = scene_ref_candidate_xml_path(raw_path, scenes_root=scenes_root)
            if path is not None:
                return path[0], str(role), path[1]
    return None, "", False


def scene_ref_candidate_xml_path(
    raw_path: Any,
    *,
    scenes_root: Path,
) -> tuple[Path, bool] | None:
    if raw_path is None:
        return None
    path, path_was_relative = normalize_molmospaces_scene_ref_path(
        raw_path,
        scenes_root=scenes_root,
    )
    if path.suffix != ".xml":
        return None
    return path, path_was_relative


def normalize_molmospaces_scene_ref_path(
    raw_path: Any,
    *,
    scenes_root: Path,
) -> tuple[Path, bool]:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path, False
    return scenes_root / path, True


def scenario_id(*, scene_source: str, scene_index: int, seed: int) -> str:
    source_token = re.sub(r"[^A-Za-z0-9_.-]+", "-", scene_source).strip("-")
    return f"molmospaces-{source_token}-{scene_index}-{seed}"
