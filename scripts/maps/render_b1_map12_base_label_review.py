#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.core.json_sources import read_json_object  # noqa: E402
from roboclaws.maps.bundle_validation import parse_map_yaml  # noqa: E402
from roboclaws.maps.navigation_memory import (  # noqa: E402
    navigation_memory_item,
    navigation_memory_items,
    read_navigation_memory,
)
from roboclaws.maps.room_semantics import build_scene_room_semantic_overlay  # noqa: E402
from scripts.maps.fit_b1_map12_scene_alignment import apply_transform_point  # noqa: E402
from scripts.maps.render_b1_scene_topdown_diagnostic import (  # noqa: E402
    DIAGNOSTIC_SCHEMA as SCENE_TOPDOWN_DIAGNOSTIC_SCHEMA,
)
from scripts.maps.render_b1_scene_topdown_diagnostic import (  # noqa: E402
    projected_bounds_polygon,
    scene_projector_from_topdown_packet,
)

REVIEW_PACKET_SCHEMA = "b1_map12_base_label_review_packet_v1"
DEFAULT_MAP_BUNDLE = Path("vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot")
DEFAULT_NAVIGATION_MEMORY = Path(
    "vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json"
)
DEFAULT_ROOM_SEMANTICS = Path("assets/maps/b1-map12-room-semantics.json")
DEFAULT_SCENE_ROOT = Path("data/robot-data-lab/scene-engine/data/2rd_floor_seperated")
DEFAULT_SCENE_TOPDOWN = Path(
    "output/b1-map12/scene-gaussian-topdown-crop-z1p8/scene_gaussian_topdown.json"
)
DEFAULT_SCENE_DIAGNOSTIC = Path(
    "output/b1-map12/scene-topdown-label-overlay/scene_topdown_diagnostic.json"
)
DEFAULT_ALIGNMENT_ARTIFACT = Path("output/b1-map12/alignment/alignment_residuals.json")
DEFAULT_OUTPUT_DIR = Path("output/b1-map12/base-map-label-review")

ROOM_CATEGORY_ALIASES = {
    "kitchen": ["kitchen", "open kitchen", "bar", "counter", "厨房", "吧台", "厨房/吧台区域"],
    "living_room": [
        "living room",
        "main hall",
        "reception area",
        "lobby",
        "起居室",
        "客厅",
        "大厅",
    ],
    "meeting_room": ["meeting room", "conference room", "会议室"],
    "corridor": ["corridor", "hallway", "走廊"],
    "storage": ["storage", "storage room", "utility", "储藏室", "库房"],
}

CATEGORY_NORMALIZATION = {
    "storage_room": "storage",
    "reception_area": "living_room",
    "meeting_room": "meeting_room",
    "kitchen": "kitchen",
    "living_room": "living_room",
    "corridor": "corridor",
}

EXPECTED_ANCHOR_TERMS = {
    "kitchen": ("sink", "fridge", "refrigerator", "counter", "kitchen"),
    "living_room": ("sofa", "couch", "coffee table", "coffee_table", "monitor"),
    "meeting_room": ("table", "monitor", "chair", "desk"),
    "corridor": (),
    "storage": ("storage", "trash", "black_machine"),
}

COLORS = [
    (64, 120, 216, 86),
    (236, 105, 80, 86),
    (72, 164, 104, 86),
    (242, 169, 59, 86),
    (155, 98, 218, 86),
    (45, 169, 178, 86),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render a B1 / Map 12 Base Navigation Map room-label review packet. "
            "This is review-only and never mutates accepted map artifacts."
        )
    )
    parser.add_argument("--map-bundle", type=Path, default=DEFAULT_MAP_BUNDLE)
    parser.add_argument("--navigation-memory", type=Path, default=DEFAULT_NAVIGATION_MEMORY)
    parser.add_argument("--room-semantics", type=Path, default=DEFAULT_ROOM_SEMANTICS)
    parser.add_argument("--scene-root", type=Path, default=DEFAULT_SCENE_ROOT)
    parser.add_argument("--scene-topdown-render", type=Path, default=DEFAULT_SCENE_TOPDOWN)
    parser.add_argument("--scene-topdown-diagnostic", type=Path, default=DEFAULT_SCENE_DIAGNOSTIC)
    parser.add_argument("--alignment-artifact", type=Path, default=DEFAULT_ALIGNMENT_ARTIFACT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        packet = build_review_packet(
            map_bundle=args.map_bundle,
            navigation_memory_path=args.navigation_memory,
            room_semantics_path=args.room_semantics,
            scene_root=args.scene_root,
            scene_topdown_render_path=args.scene_topdown_render,
            scene_topdown_diagnostic_path=args.scene_topdown_diagnostic,
            alignment_artifact_path=args.alignment_artifact,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = args.output_dir / "base_label_review_packet.json"
    overlay_path = args.output_dir / "base_label_review_aligned_overlay.png"
    checklist_path = args.output_dir / "base_label_review.md"
    packet["outputs"] = {
        "packet": str(packet_path),
        "overlay": str(overlay_path),
        "checklist": str(checklist_path),
    }
    render_aligned_overlay(packet, output_path=overlay_path)
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checklist_path.write_text(render_markdown(packet), encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": packet["schema"],
                "status": packet["status"],
                "overlay": str(overlay_path),
                "packet": str(packet_path),
                "checklist": str(checklist_path),
                "needs_review_count": packet["summary"]["needs_review_count"],
            },
            sort_keys=True,
        )
    )
    return 0


def build_review_packet(
    *,
    map_bundle: Path,
    navigation_memory_path: Path,
    room_semantics_path: Path,
    scene_root: Path,
    scene_topdown_render_path: Path,
    scene_topdown_diagnostic_path: Path = DEFAULT_SCENE_DIAGNOSTIC,
    alignment_artifact_path: Path,
) -> dict[str, Any]:
    map_bundle = Path(map_bundle)
    map_yaml_path = map_bundle / "map.yaml"
    if not map_yaml_path.is_file():
        map_yaml_path = map_bundle / "nav2.yaml"
    map_yaml = parse_map_yaml(map_yaml_path.read_text(encoding="utf-8"))
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else []
    map_image_path = map_bundle / str(map_yaml.get("image") or "map.pgm")
    with Image.open(map_image_path) as image:
        width_px, height_px = image.size
    room_semantics = read_json_object(room_semantics_path, label="room semantics")
    navigation_memory = read_navigation_memory(navigation_memory_path)
    scene_overlay = build_scene_room_semantic_overlay(scene_root, overrides=room_semantics)
    scene_topdown = read_json_object(scene_topdown_render_path, label="scene topdown render")
    scene_diagnostic = read_scene_topdown_diagnostic(scene_topdown_diagnostic_path)
    scene_bounds = scene_bounds_by_partition(scene_diagnostic)
    alignment = read_json_object(alignment_artifact_path, label="alignment artifact")
    alignment_transform = verified_transform(alignment)
    nav_items = [
        navigation_memory_item(raw_item, index=index)
        for index, raw_item in enumerate(navigation_memory_items(navigation_memory), start=1)
    ]
    scene_rooms = {
        str(room.get("asset_partition_id") or room.get("room_id") or ""): room
        for room in scene_overlay.get("rooms") or []
        if isinstance(room, dict)
    }
    areas = [
        area_review_row(room, index=index, nav_items=nav_items)
        for index, room in enumerate(scene_rooms.values(), start=1)
    ]
    for area in areas:
        partition_id = area["digital_twin_partition_id"]
        if partition_id not in scene_bounds:
            raise ValueError(
                f"scene topdown diagnostic missing Digital Twin room bounds for {partition_id!r}"
            )
        area["digital_twin_scene_bounds"] = scene_bounds[partition_id]
    memory_rows = [navigation_memory_review_row(item) for item in nav_items]
    return {
        "schema": REVIEW_PACKET_SCHEMA,
        "status": "needs_human_review",
        "map_bundle": str(map_bundle),
        "map_image": str(map_image_path),
        "map_yaml": str(map_yaml_path),
        "navigation_memory": str(navigation_memory_path),
        "room_semantics": str(room_semantics_path),
        "scene_root": str(scene_root),
        "scene_topdown_render": str(scene_topdown_render_path),
        "scene_topdown_diagnostic": str(scene_topdown_diagnostic_path),
        "scene_topdown_image": str(scene_topdown.get("topdown_image") or ""),
        "alignment_artifact": str(alignment_artifact_path),
        "alignment_status": str(alignment.get("global_alignment_status") or ""),
        "selected_transform": alignment_transform,
        "source_map_frame": "map",
        "policy": {
            "review_only": True,
            "mutates_product_bundle": False,
            "preferred_label_source": "digital_twin_room_semantics_reference",
            "room_aliases_should_be_uniform_base_map_fields": True,
            "object_alias_support": "navigation_memory_aliases",
            "default_overlay": "digital_twin_room_bounds",
            "map12_candidate_polygons_are_retired": True,
        },
        "map_transform": {
            "width_px": width_px,
            "height_px": height_px,
            "resolution_m": float(map_yaml.get("resolution") or 0.05),
            "origin": [
                float(origin[0]) if len(origin) >= 1 else 0.0,
                float(origin[1]) if len(origin) >= 2 else 0.0,
                float(origin[2]) if len(origin) >= 3 else 0.0,
            ],
        },
        "areas": areas,
        "navigation_memory_items": memory_rows,
        "normalization_notes": normalization_notes(areas),
        "scene_projection": {
            "schema": str(scene_topdown.get("schema") or ""),
            "topdown_image": str(scene_topdown.get("topdown_image") or ""),
            "diagnostic_schema": str(scene_diagnostic.get("schema") or ""),
            "diagnostic_image": str(scene_diagnostic.get("topdown_image") or ""),
            "camera_mode": str((scene_topdown.get("camera") or {}).get("camera_mode") or ""),
            "width_px": int(scene_topdown.get("width_px") or 0),
            "height_px": int(scene_topdown.get("height_px") or 0),
            "digital_twin_room_bounds_count": len(scene_bounds),
        },
        "summary": {
            "area_count": len(areas),
            "accepted_area_count": sum(1 for row in areas if row["review_status"] == "accepted"),
            "needs_review_count": sum(1 for row in areas if row["human_action"] != "accept_as_is"),
            "navigation_memory_item_count": len(memory_rows),
            "object_aliases_supported": all(
                isinstance(item.get("aliases"), list) for item in nav_items
            ),
            "room_aliases_recommended_as_required_field": True,
        },
    }


def read_scene_topdown_diagnostic(path: Path) -> dict[str, Any]:
    diagnostic = read_json_object(path, label="scene topdown diagnostic")
    if diagnostic.get("schema") != SCENE_TOPDOWN_DIAGNOSTIC_SCHEMA:
        raise ValueError(
            f"scene topdown diagnostic schema must be {SCENE_TOPDOWN_DIAGNOSTIC_SCHEMA}: {path}"
        )
    validation = (
        diagnostic.get("validation") if isinstance(diagnostic.get("validation"), dict) else {}
    )
    if validation.get("status") != "passed":
        errors = validation.get("errors") if isinstance(validation.get("errors"), list) else []
        raise ValueError(
            f"scene topdown diagnostic must have validation.status=passed: {path}; errors={errors}"
        )
    return diagnostic


def scene_bounds_by_partition(diagnostic: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output = {}
    for partition in diagnostic.get("partitions") or []:
        if not isinstance(partition, dict):
            continue
        partition_id = str(partition.get("partition_id") or "")
        bounds = (
            partition.get("scene_frame_bounds")
            if isinstance(partition.get("scene_frame_bounds"), dict)
            else {}
        )
        if not partition_id:
            continue
        if bounds.get("status") != "extracted_from_scene_usd_world_bounds":
            continue
        output[partition_id] = {
            "frame_id": "digital_twin_scene",
            "bounds_source": "scene_topdown_diagnostic.scene_usd_world_bounds",
            "partition_id": partition_id,
            "object_bounds_count": int(partition.get("object_bounds_count") or 0),
            "bounds": bounds,
        }
    return output


def verified_transform(alignment: dict[str, Any]) -> dict[str, Any]:
    if alignment.get("global_alignment_status") != "verified":
        raise ValueError("alignment artifact must have global_alignment_status=verified")
    transform = alignment.get("selected_transform")
    if not isinstance(transform, dict):
        raise ValueError("alignment artifact missing selected_transform")
    if transform.get("type") != "rigid_2d":
        raise ValueError("base label review expects rigid_2d alignment")
    if str(transform.get("source") or "") != "reviewed_correspondence_fit":
        raise ValueError("base label review expects reviewed_correspondence_fit transform")
    return transform


def area_review_row(
    room: dict[str, Any],
    *,
    index: int,
    nav_items: list[dict[str, Any]],
) -> dict[str, Any]:
    partition_id = str(room.get("asset_partition_id") or room.get("room_id") or "")
    label_id = str(room.get("room_id") or partition_id or f"area_{index:02d}")
    source_category = str(room.get("category") or "")
    semantic_category = normalize_category(source_category)
    canonical_label = str(room.get("room_label") or label_id)
    aliases = room_aliases(
        label_id=label_id,
        canonical_label=canonical_label,
        semantic_category=semantic_category,
        partition_id=partition_id,
        raw_label=room,
    )
    expected = [
        navigation_anchor_summary(item)
        for item in nav_items
        if item_matches_category(item, semantic_category)
    ]
    raw_dt_label = canonical_label
    name_conversion = "digital_twin_reference_label"
    status = str(room.get("review_status") or "needs_review")
    evidence = room.get("evidence") if isinstance(room.get("evidence"), dict) else {}
    human_action = "accept_as_is" if status == "accepted" else "review_digital_twin_room_label"
    return {
        "index": index,
        "label_id": label_id,
        "navigation_area_id": str(room.get("navigation_area_id") or ""),
        "digital_twin_partition_id": partition_id,
        "digital_twin_raw_label": raw_dt_label,
        "canonical_label": canonical_label,
        "semantic_category": semantic_category,
        "source_category": source_category,
        "aliases": aliases,
        "review_status": status,
        "name_conversion": name_conversion,
        "scene_evidence": {
            "object_name_counts": dict(evidence.get("object_name_counts") or {}),
            "matched_terms": list(evidence.get("matched_terms") or []),
            "weak_evidence": bool(evidence.get("weak_evidence")),
        },
        "related_navigation_memory": expected,
        "human_action": human_action,
        "operator_note": str(room.get("operator_note") or ""),
    }


def normalize_category(value: str) -> str:
    return CATEGORY_NORMALIZATION.get(str(value or "").strip(), str(value or "").strip())


def room_aliases(
    *,
    label_id: str,
    canonical_label: str,
    semantic_category: str,
    partition_id: str,
    raw_label: dict[str, Any],
) -> list[str]:
    aliases = [
        label_id,
        canonical_label,
        partition_id,
        partition_id.replace("_", " "),
        semantic_category,
        str(raw_label.get("category") or ""),
    ]
    aliases.extend(str(alias) for alias in raw_label.get("aliases") or [])
    aliases.extend(ROOM_CATEGORY_ALIASES.get(semantic_category, []))
    return dedupe_nonempty(aliases)


def item_matches_category(item: dict[str, Any], category: str) -> bool:
    terms = EXPECTED_ANCHOR_TERMS.get(category) or ()
    if not terms:
        return False
    text = " ".join(
        [
            str(item.get("id") or ""),
            str(item.get("label") or ""),
            str(item.get("kind") or ""),
            " ".join(str(alias) for alias in item.get("aliases") or []),
        ]
    ).lower()
    return any(term.lower() in text for term in terms)


def navigation_anchor_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or ""),
        "label": str(item.get("label") or ""),
        "kind": str(item.get("kind") or ""),
        "aliases": [str(alias) for alias in item.get("aliases") or []],
        "nav_goal": point_xy(item.get("nav_goal")),
        "pose": point_xy(item.get("pose")),
    }


def navigation_memory_review_row(item: dict[str, Any]) -> dict[str, Any]:
    aliases = [str(alias) for alias in item.get("aliases") or []]
    return {
        "id": str(item.get("id") or ""),
        "label": str(item.get("label") or ""),
        "kind": str(item.get("kind") or ""),
        "scene_id": str(item.get("scene_id") or ""),
        "aliases": aliases,
        "alias_count": len(aliases),
        "pose": point_xy(item.get("pose")),
        "nav_goal": point_xy(item.get("nav_goal")),
    }


def point_xy(payload: Any) -> dict[str, float] | None:
    if not isinstance(payload, dict):
        return None
    try:
        return {"x": round(float(payload["x"]), 6), "y": round(float(payload["y"]), 6)}
    except (KeyError, TypeError, ValueError):
        return None


def normalization_notes(areas: list[dict[str, Any]]) -> list[dict[str, str]]:
    notes = []
    for area in areas:
        if area["name_conversion"] != "same_as_digital_twin":
            notes.append(
                {
                    "digital_twin_partition_id": area["digital_twin_partition_id"],
                    "digital_twin_raw_label": area["digital_twin_raw_label"],
                    "canonical_label": area["canonical_label"],
                    "semantic_category": area["semantic_category"],
                    "reason": (
                        "raw DT partition/folder name is evidence, canonical label is "
                        "product-facing"
                    ),
                }
            )
    return notes


def render_aligned_overlay(
    packet: dict[str, Any],
    *,
    output_path: Path,
) -> None:
    scene_image_path = Path(str(packet.get("scene_topdown_image") or ""))
    if not scene_image_path.is_file():
        raise FileNotFoundError(f"scene topdown image missing: {scene_image_path}")
    scene_packet = read_json_object(
        Path(str(packet["scene_topdown_render"])),
        label="scene topdown render",
    )
    projector = scene_projector_from_topdown_packet(scene_packet)
    transform = packet["selected_transform"]
    scale = 1.15
    table_width = 720
    padding = 28
    title_height = 70
    base = Image.open(scene_image_path).convert("RGB")
    base = base.resize((int(base.width * scale), int(base.height * scale)))
    canvas_size = (
        base.width + table_width + padding * 3,
        base.height + title_height + padding * 2,
    )
    canvas = Image.new("RGB", canvas_size, "white")
    canvas.paste(base, (padding, title_height + padding))
    overlay = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    small_font = load_font(14)
    title_font = load_font(24)
    map_origin = (padding, title_height + padding)
    for index, area in enumerate(packet["areas"], start=1):
        color = COLORS[(index - 1) % len(COLORS)]
        dt_polygon = digital_twin_bounds_polygon(
            area.get("digital_twin_scene_bounds"),
            projector=projector,
            scale=scale,
            origin=map_origin,
        )
        if len(dt_polygon) >= 3:
            draw.polygon(dt_polygon, fill=color[:3] + (72,), outline=color[:3] + (230,))
            draw.line(dt_polygon + [dt_polygon[0]], fill=color[:3] + (255,), width=3)
        dt_center = digital_twin_bounds_center(
            area.get("digital_twin_scene_bounds"),
            projector=projector,
            scale=scale,
            origin=map_origin,
        )
        if dt_center:
            label = f"{index}. DT {area['canonical_label']}\n{area['digital_twin_partition_id']}"
            label_anchor = dt_label_anchor(area, dt_center)
            draw.line(
                (dt_center[0], dt_center[1], label_anchor[0], label_anchor[1]),
                fill=color[:3] + (210,),
                width=2,
            )
            draw_label_box(draw, label_anchor, label, font=small_font, fill=(255, 255, 255, 235))
    for item in packet["navigation_memory_items"]:
        point = item.get("nav_goal") or item.get("pose")
        if not point:
            continue
        px = projected_scene_pixel(
            point["x"],
            point["y"],
            transform=transform,
            projector=projector,
            scale=scale,
            origin=map_origin,
        )
        if not px:
            continue
        draw.ellipse((px[0] - 5, px[1] - 5, px[0] + 5, px[1] + 5), fill=(25, 110, 54, 230))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw_rgb = ImageDraw.Draw(canvas)
    draw_rgb.text(
        (padding, 18),
        "B1 / Map 12 Aligned Label Review",
        fill=(20, 32, 44),
        font=title_font,
    )
    draw_rgb.text(
        (padding, 47),
        aligned_overlay_subtitle(),
        fill=(80, 90, 105),
        font=small_font,
    )
    draw_review_table(
        draw_rgb,
        packet,
        x=base.width + padding * 2,
        y=title_height + padding,
        width=table_width,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def aligned_overlay_subtitle() -> str:
    return "Solid rooms are Digital Twin bounds. Green dots are navigation_memory nav goals."


def dt_label_anchor(
    area: dict[str, Any],
    center: tuple[float, float],
) -> tuple[float, float]:
    offsets = {
        "meeting_room_a": (120.0, -44.0),
        "meeting_room_b": (110.0, 18.0),
        "meeting_room_c": (88.0, 58.0),
        "reception_area_a": (-118.0, 0.0),
        "short_corridor_a": (-72.0, 36.0),
        "storage_room_a": (-92.0, 0.0),
    }
    dx, dy = offsets.get(str(area.get("digital_twin_partition_id") or ""), (0.0, 0.0))
    return center[0] + dx, center[1] + dy


def digital_twin_bounds_polygon(
    payload: Any,
    *,
    projector: Any,
    scale: float,
    origin: tuple[int, int],
) -> list[tuple[float, float]]:
    if not isinstance(payload, dict):
        return []
    bounds = payload.get("bounds") if isinstance(payload.get("bounds"), dict) else {}
    if bounds.get("status") != "extracted_from_scene_usd_world_bounds":
        return []
    polygon = projected_bounds_polygon(bounds, projector)
    return [(origin[0] + x * scale, origin[1] + y * scale) for x, y in polygon]


def digital_twin_bounds_center(
    payload: Any,
    *,
    projector: Any,
    scale: float,
    origin: tuple[int, int],
) -> tuple[float, float] | None:
    if not isinstance(payload, dict):
        return None
    bounds = payload.get("bounds") if isinstance(payload.get("bounds"), dict) else {}
    center = bounds.get("center") if isinstance(bounds.get("center"), dict) else {}
    if not center:
        return None
    projected = projector.project(float(center["x"]), float(center["y"]), z=0.0)
    if projected is None:
        return None
    return (origin[0] + projected[0] * scale, origin[1] + projected[1] * scale)


def projected_scene_pixel(
    x: float,
    y: float,
    *,
    transform: dict[str, Any],
    projector: Any,
    scale: float,
    origin: tuple[int, int],
) -> tuple[float, float] | None:
    scene_xy = apply_transform_point(np.array([float(x), float(y)], dtype=float), transform)
    projected = projector.project(float(scene_xy[0]), float(scene_xy[1]), z=0.0)
    if projected is None:
        return None
    return (origin[0] + projected[0] * scale, origin[1] + projected[1] * scale)


def draw_label_box(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    lines = text.splitlines()
    widths = [draw.textbbox((0, 0), line, font=font)[2] for line in lines]
    line_height = max(draw.textbbox((0, 0), line, font=font)[3] for line in lines) + 4
    box_width = max(widths) + 14
    box_height = line_height * len(lines) + 10
    x0 = center[0] - box_width / 2
    y0 = center[1] - box_height / 2
    draw.rounded_rectangle(
        (x0, y0, x0 + box_width, y0 + box_height),
        radius=5,
        fill=fill,
        outline=(30, 40, 50, 200),
    )
    y = y0 + 5
    for line in lines:
        draw.text((x0 + 7, y), line, fill=(20, 30, 40, 255), font=font)
        y += line_height


def draw_review_table(
    draw: ImageDraw.ImageDraw,
    packet: dict[str, Any],
    *,
    x: int,
    y: int,
    width: int,
) -> None:
    title_font = load_font(18)
    font = load_font(14)
    small_font = load_font(12)
    draw.text((x, y), "Human check list", fill=(20, 32, 44), font=title_font)
    y += 32
    for index, area in enumerate(packet["areas"], start=1):
        action = area["human_action"]
        action_color = (178, 73, 18) if action != "accept_as_is" else (23, 119, 82)
        row_text = (
            f"{index}. {area['canonical_label']} | {area['semantic_category']}\n"
            f"DT: {area['digital_twin_partition_id']} -> {area['canonical_label']}\n"
            f"status: {area['review_status']} | action: {action}"
        )
        lines = []
        for raw in row_text.splitlines():
            lines.extend(textwrap.wrap(raw, width=70) or [""])
        row_height = 22 * len(lines) + 18
        draw.rounded_rectangle(
            (x, y, x + width - 20, y + row_height),
            radius=6,
            outline=(210, 218, 226),
            fill=(248, 250, 252),
        )
        yy = y + 8
        for line_index, line in enumerate(lines):
            fill = action_color if line_index == len(lines) - 1 else (35, 45, 60)
            draw.text(
                (x + 10, yy),
                line,
                fill=fill,
                font=font if line_index == 0 else small_font,
            )
            yy += 22
        y += row_height + 10


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# B1 / Map 12 Base Label Review",
        "",
        "Status: needs human review.",
        "",
        "Artifacts:",
        f"- Aligned overlay: `{packet['outputs']['overlay']}`",
        f"- Packet: `{packet['outputs']['packet']}`",
        "",
        "Policy:",
        "- Prefer one canonical room label shared by Digital Twin and real-robot map artifacts.",
        (
            "- Keep raw Digital Twin partition ids as source evidence and aliases, "
            "not competing labels."
        ),
        "- Product bundles should carry required `semantic_category` and `aliases` uniformly.",
        "- Navigation-memory objects already support multiple aliases.",
        (
            "- The aligned overlay uses Digital Twin room bounds as the visual review layer; "
            "old Map12 candidate polygons are retired from this review packet."
        ),
        "",
        "## Room / Area Checklist",
        "",
        "| # | Map area | DT partition | Canonical label | Category | Status | Human action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for area in packet["areas"]:
        row = (
            "| {index} | `{navigation_area_id}` | `{digital_twin_partition_id}` | "
            "{canonical_label} | `{semantic_category}` | `{review_status}` | "
            "`{human_action}` |"
        )
        lines.append(row.format(**area))
    lines.extend(["", "## Name Normalization Notes", ""])
    for note in packet["normalization_notes"]:
        note_row = (
            "- `{digital_twin_partition_id}` / {digital_twin_raw_label} -> "
            "{canonical_label} (`{semantic_category}`): {reason}"
        )
        lines.append(note_row.format(**note))
    lines.extend(["", "## Navigation Memory Alias Evidence", ""])
    for item in packet["navigation_memory_items"]:
        aliases = ", ".join(item["aliases"][:8])
        lines.append(f"- `{item['id']}`: {item['label']} / `{item['kind']}` aliases: {aliases}")
    lines.append("")
    return "\n".join(lines)


def normalize_text(value: str) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").split())


def dedupe_nonempty(values: list[str]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = normalize_text(text)
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ):
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


if __name__ == "__main__":
    raise SystemExit(main())
