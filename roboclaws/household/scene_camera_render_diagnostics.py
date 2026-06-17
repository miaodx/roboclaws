from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

RENDER_SOURCE_PRIORITY_KEYWORDS = (
    "doNotCastShadows",
    "opacity=1.0",
    "definePreviewMaterial",
    "addDiffuseTextureToPreviewMaterial",
    "UsdLux.DistantLight",
    "defineDomeLight",
    "add_light",
    "add_texture",
)
RENDER_SOURCE_KEYWORDS = (
    "material",
    "texture",
    "light",
    "shadow",
    "opacity",
    "roughness",
    "specular",
    "Preview",
    "DistantLight",
    "DomeLight",
    "doNotCastShadows",
)


def room_scale_contract_from_capture(
    *,
    room_views: list[dict[str, Any]],
    isaac_lane: dict[str, Any],
    threshold_m: float,
) -> dict[str, Any]:
    rooms = [
        room for room in (_room_outline_from_view(view) for view in room_views) if room is not None
    ]
    isaac_room_outlines = _isaac_room_outlines_by_id(isaac_lane)
    outline_pairs = [
        pair
        for pair in (
            _room_outline_pair(room, isaac_room_outlines.get(str(room.get("room_id") or "")))
            for room in rooms
        )
        if pair is not None
    ]
    max_center_delta = _max_delta(outline_pairs, "center_delta_m")
    max_size_delta = _max_delta(outline_pairs, "size_delta_m")
    max_half_extent_delta = _max_delta(outline_pairs, "half_extent_delta_m")
    scene_bounds = _dict_or_empty(isaac_lane.get("scene_bounds"))
    scene_size = scene_bounds.get("size") if isinstance(scene_bounds.get("size"), list) else []
    width_ratio, depth_ratio, exceeds_scene = _room_to_scene_ratios(rooms, scene_size)
    status = _room_scale_status(
        rooms=rooms,
        outline_pairs=outline_pairs,
        exceeds_scene=exceeds_scene,
        max_center_delta=max_center_delta,
        max_size_delta=max_size_delta,
        max_half_extent_delta=max_half_extent_delta,
        threshold_m=threshold_m,
    )
    return {
        "schema": "room_scale_contract_v1",
        "status": status,
        "room_count": len(rooms),
        "matched_room_outline_count": len(outline_pairs),
        "room_outline_source": "molmospaces_room_outlines",
        "isaac_room_outline_source": "isaac_scene_index_diagnostics.room_outlines",
        "isaac_scene_bounds": dict(scene_bounds),
        "max_room_to_scene_width_ratio": width_ratio,
        "max_room_to_scene_depth_ratio": depth_ratio,
        "room_outline_threshold_m": threshold_m,
        "max_room_outline_center_delta_m": max_center_delta,
        "max_room_outline_size_delta_m": max_size_delta,
        "max_room_outline_half_extent_delta_m": max_half_extent_delta,
        "interpretation": (
            "Room-level camera poses are derived from MolmoSpaces room outlines. "
            "Those outlines must match Isaac USD room mesh world bounds room-by-room; "
            "otherwise same-pose backend comparisons can start from a wrong room scale."
        ),
        "rooms": rooms,
        "room_outline_pairs": outline_pairs,
    }


def view_usd_prim_path(
    manifest: dict[str, Any],
    view_id: str,
    *,
    isaac_lane_id: str,
) -> str:
    lane_view = _matching_view(
        _dict_or_empty(_dict_or_empty(manifest.get("lanes")).get(isaac_lane_id)).get("views"),
        view_id,
    )
    canonical_view = _matching_view(manifest.get("canonical_camera_views"), view_id)
    for view in (lane_view, canonical_view):
        usd_path = _view_path(view, "usd_prim_path")
        if usd_path:
            return usd_path
    return _anchor_isaac_usd_prim_path(manifest, _first_anchor_id(lane_view, canonical_view))


def mujoco_render_contract_from_xml(path_text: str | None) -> dict[str, Any]:
    path = Path(str(path_text or ""))
    if not path.is_file():
        return {"status": "missing_scene_xml", "path": str(path)}
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        return {"status": "parse_failed", "path": str(path), "error": str(exc)}
    textures = _mujoco_textures(root)
    materials = _mujoco_materials(root, textures)
    lights = _mujoco_lights(root)
    body_visuals = _mujoco_body_visuals(root, materials)
    return {
        "status": "parsed",
        "path": str(path),
        "texture_count": len(textures),
        "material_count": len(materials),
        "light_count": len(lights),
        "textures": textures,
        "materials": materials,
        "lights": lights,
        "body_visuals": body_visuals,
    }


def render_source_snippet(lines: list[str]) -> str:
    matching = [
        stripped
        for stripped in (_snippet_candidate(line) for line in lines)
        if stripped and _mentions_any(stripped, RENDER_SOURCE_KEYWORDS)
    ]
    selected = _select_priority_lines(matching)
    if not selected:
        selected = [line.strip() for line in lines if line.strip()][:3]
    return " | ".join(selected)


def float_list(value: Any) -> list[float] | None:
    if value is None:
        return None
    result = []
    for token in str(value).replace(",", " ").split():
        try:
            result.append(float(token))
        except ValueError:
            return None
    return result or None


def normalized_vec3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        vector = [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None
    magnitude = math.sqrt(sum(component * component for component in vector))
    if magnitude <= 0.0:
        return None
    return [component / magnitude for component in vector]


def _room_outline_from_view(view: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(view, dict):
        return None
    outline = _dict_or_empty(view.get("room_outline"))
    half_extents = outline.get("half_extents")
    center = outline.get("center")
    if not _xy_values_available(half_extents) or not _xy_values_available(center):
        return None
    return {
        "view_id": view.get("view_id"),
        "room_id": view.get("room_id"),
        "center": [float(center[0]), float(center[1])],
        "size": [float(half_extents[0]) * 2.0, float(half_extents[1]) * 2.0],
        "half_extents": [float(half_extents[0]), float(half_extents[1])],
        "provenance": str(outline.get("provenance") or ""),
    }


def _room_outline_pair(
    room: dict[str, Any],
    isaac_outline: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isaac_outline:
        return None
    isaac_center = isaac_outline.get("center")
    isaac_half_extents = isaac_outline.get("half_extents")
    if not _xy_values_available(isaac_center) or not _xy_values_available(isaac_half_extents):
        return None
    isaac_size = [float(isaac_half_extents[0]) * 2.0, float(isaac_half_extents[1]) * 2.0]
    return {
        "room_id": str(room.get("room_id") or ""),
        "molmospaces_center": list(room["center"]),
        "isaac_center": [float(isaac_center[0]), float(isaac_center[1])],
        "center_delta_m": _distance_xy(room["center"], isaac_center),
        "molmospaces_size": list(room["size"]),
        "isaac_size": isaac_size,
        "size_delta_m": _distance_xy(room["size"], isaac_size),
        "molmospaces_half_extents": list(room["half_extents"]),
        "isaac_half_extents": [float(isaac_half_extents[0]), float(isaac_half_extents[1])],
        "half_extent_delta_m": _distance_xy(room["half_extents"], isaac_half_extents),
        "molmospaces_provenance": str(room.get("provenance") or ""),
        "isaac_provenance": str(isaac_outline.get("provenance") or ""),
        "isaac_usd_prim_path": str(isaac_outline.get("usd_prim_path") or ""),
    }


def _room_scale_status(
    *,
    rooms: list[dict[str, Any]],
    outline_pairs: list[dict[str, Any]],
    exceeds_scene: bool,
    max_center_delta: float | None,
    max_size_delta: float | None,
    max_half_extent_delta: float | None,
    threshold_m: float,
) -> str:
    if not rooms:
        return "missing_room_outline_diagnostics"
    if not outline_pairs:
        return "missing_isaac_room_outline_pairs"
    if exceeds_scene:
        return "room_outline_exceeds_isaac_scene_bounds"
    deltas = [max_center_delta, max_size_delta, max_half_extent_delta]
    if all(delta is not None for delta in deltas) and max(float(delta) for delta in deltas) <= (
        threshold_m
    ):
        return "same_room_outlines_within_threshold"
    return "room_outline_mismatch"


def _room_to_scene_ratios(
    rooms: list[dict[str, Any]],
    scene_size: Any,
) -> tuple[float | None, float | None, bool]:
    if not (isinstance(scene_size, list) and len(scene_size) >= 2 and rooms):
        return None, None, False
    scene_width = max(float(scene_size[0]), 1e-6)
    scene_depth = max(float(scene_size[1]), 1e-6)
    width_ratio = max(float(room["size"][0]) / scene_width for room in rooms)
    depth_ratio = max(float(room["size"][1]) / scene_depth for room in rooms)
    return width_ratio, depth_ratio, width_ratio > 1.05 or depth_ratio > 1.05


def _isaac_room_outlines_by_id(isaac_lane: dict[str, Any]) -> dict[str, dict[str, Any]]:
    diagnostics = _dict_or_empty(isaac_lane.get("scene_index_diagnostics"))
    result: dict[str, dict[str, Any]] = {}
    for item in diagnostics.get("room_outlines") or []:
        if isinstance(item, dict) and str(item.get("room_id") or ""):
            result[str(item.get("room_id") or "")] = item
    return result


def _mujoco_textures(root: ElementTree.Element) -> dict[str, dict[str, Any]]:
    textures: dict[str, dict[str, Any]] = {}
    for texture in root.findall(".//texture"):
        name = str(texture.attrib.get("name") or "")
        if name:
            textures[name] = {
                "name": name,
                "type": texture.attrib.get("type"),
                "file": texture.attrib.get("file"),
            }
    return textures


def _mujoco_materials(
    root: ElementTree.Element,
    textures: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    materials: dict[str, dict[str, Any]] = {}
    for material in root.findall(".//material"):
        name = str(material.attrib.get("name") or "")
        if name:
            texture_name = str(material.attrib.get("texture") or "")
            materials[name] = {
                "name": name,
                "rgba": float_list(material.attrib.get("rgba")),
                "texture": texture_name,
                "texture_file": textures.get(texture_name, {}).get("file")
                if texture_name
                else None,
            }
    return materials


def _mujoco_lights(root: ElementTree.Element) -> list[dict[str, Any]]:
    lights = []
    for light in root.findall(".//light"):
        light_contract = dict(light.attrib)
        light_contract["dir_vector"] = normalized_vec3(float_list(light.attrib.get("dir")))
        light_contract["pos_vector"] = float_list(light.attrib.get("pos"))
        lights.append(light_contract)
    return lights


def _mujoco_body_visuals(
    root: ElementTree.Element,
    materials: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    body_visuals: dict[str, list[dict[str, Any]]] = {}
    for body in root.findall(".//body"):
        body_name = str(body.attrib.get("name") or "")
        visuals = _mujoco_body_visual_entries(body, materials) if body_name else []
        if visuals:
            body_visuals[body_name] = visuals
    return body_visuals


def _mujoco_body_visual_entries(
    body: ElementTree.Element,
    materials: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    visuals = []
    for geom in body.findall(".//geom"):
        if not _is_mujoco_visual_geom(geom):
            continue
        material_name = str(geom.attrib.get("material") or "")
        material = materials.get(material_name, {})
        visuals.append(
            {
                "geom_name": str(geom.attrib.get("name") or ""),
                "mesh": geom.attrib.get("mesh"),
                "material": material_name,
                "rgba": material.get("rgba") or float_list(geom.attrib.get("rgba")),
                "texture": material.get("texture"),
                "texture_file": material.get("texture_file"),
            }
        )
    return visuals


def _is_mujoco_visual_geom(geom: ElementTree.Element) -> bool:
    geom_name = str(geom.attrib.get("name") or "")
    geom_class = str(geom.attrib.get("class") or "")
    return "_visual_" in geom_name or "__VISUAL" in geom_class


def _matching_view(views: Any, view_id: str) -> dict[str, Any]:
    for view in views or []:
        if isinstance(view, dict) and str(view.get("view_id") or "") == view_id:
            return view
    return {}


def _view_path(view: dict[str, Any], key: str) -> str:
    return str(view.get(key) or "") if isinstance(view, dict) else ""


def _first_anchor_id(*views: dict[str, Any]) -> str:
    for view in views:
        anchor_id = str(view.get("anchor_id") or "") if isinstance(view, dict) else ""
        if anchor_id:
            return anchor_id
    return ""


def _anchor_isaac_usd_prim_path(manifest: dict[str, Any], anchor_id: str) -> str:
    if not anchor_id:
        return ""
    for anchor in manifest.get("anchors") or []:
        if isinstance(anchor, dict) and str(anchor.get("anchor_id") or "") == anchor_id:
            return str(anchor.get("isaac_usd_prim_path") or "")
    return ""


def _select_priority_lines(lines: list[str]) -> list[str]:
    selected = _dedupe_limited(
        line
        for keyword in RENDER_SOURCE_PRIORITY_KEYWORDS
        for line in lines
        if _mentions_any(line, (keyword,))
    )
    return (
        selected
        + _dedupe_limited((line for line in lines if line not in selected), limit=5)[
            : max(0, 5 - len(selected))
        ]
    )


def _dedupe_limited(lines: Any, *, limit: int = 5) -> list[str]:
    selected = []
    for line in lines:
        if line not in selected:
            selected.append(line)
        if len(selected) >= limit:
            break
    return selected


def _snippet_candidate(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("def ") or stripped.startswith("#"):
        return ""
    if stripped.endswith(":") or stripped in {")", "("}:
        return ""
    return stripped


def _mentions_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _max_delta(rows: list[dict[str, Any]], key: str) -> float | None:
    return max(float(item[key]) for item in rows) if rows else None


def _xy_values_available(value: Any) -> bool:
    return isinstance(value, list) and len(value) >= 2


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _distance_xy(left: list[float], right: list[float]) -> float:
    return math.hypot(float(left[0]) - float(right[0]), float(left[1]) - float(right[1]))
