#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from scripts.maps.fit_b1_map12_scene_alignment import (
    SCENE_PROJECTION_HORIZONTAL_AXES,
    SCENE_PROJECTION_UP_AXIS,
)

DIAGNOSTIC_SCHEMA = "b1_scene_topdown_diagnostic_v1"
DEFAULT_SCENE_ROOT = Path("data/robot-data-lab/scene-engine/data/2rd_floor_seperated")
_PARTITION_RE = re.compile(r'over\s+"([^"]+)"')
_INSTANCE_SUFFIX_RE = re.compile(r"(?:_\d+)+$")
_PARTITION_COLORS = [
    (69, 123, 157),
    (42, 157, 143),
    (233, 196, 106),
    (244, 162, 97),
    (231, 111, 81),
    (128, 90, 213),
    (95, 111, 82),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an honest 2rd_floor_seperated scene topdown diagnostic."
    )
    parser.add_argument("--scene-root", type=Path, default=DEFAULT_SCENE_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=640)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_scene_topdown_diagnostic(
        scene_root=args.scene_root,
        output_dir=args.output_dir,
        width=max(1, int(args.width)),
        height=max(1, int(args.height)),
    )
    errors = validate_scene_topdown_diagnostic(packet)
    packet["validation"] = {"status": "passed" if not errors else "failed", "errors": errors}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = args.output_dir / "scene_topdown_diagnostic.json"
    html_path = args.output_dir / "scene_topdown_diagnostic.html"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(render_diagnostic_html(packet, packet_path=packet_path), encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": DIAGNOSTIC_SCHEMA,
                "status": packet["validation"]["status"],
                "geometry_status": packet.get("geometry_status"),
                "partition_count": packet.get("partition_count"),
                "topdown": packet.get("topdown_image"),
                "packet": str(packet_path),
                "report": str(html_path),
                "errors": errors,
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 2


def build_scene_topdown_diagnostic(
    *,
    scene_root: Path,
    output_dir: Path,
    width: int = 960,
    height: int = 640,
) -> dict[str, Any]:
    scene_root = Path(scene_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    partitions = scene_partitions(scene_root)
    topdown_path = output_dir / "scene_topdown_diagnostic.png"
    render_label_inventory_topdown(partitions, topdown_path, width=width, height=height)
    geometry_status = "label_inventory_only" if partitions else "unavailable_no_scene_partitions"
    return {
        "schema": DIAGNOSTIC_SCHEMA,
        "scene_root": str(scene_root),
        "up_axis": SCENE_PROJECTION_UP_AXIS,
        "horizontal_axes": SCENE_PROJECTION_HORIZONTAL_AXES,
        "scene_projection_policy": {
            "up_axis": SCENE_PROJECTION_UP_AXIS,
            "horizontal_axes": SCENE_PROJECTION_HORIZONTAL_AXES,
            "source": "2rd_floor_seperated_scene_topdown_policy",
        },
        "geometry_status": geometry_status,
        "geometry_backend": "scene_partition_label_inventory",
        "geometry_honesty": (
            "No metric USD/mesh bounds were extracted. The PNG is a review inventory "
            "layout showing partition identities and object label counts. It is not a "
            "Gaussian asset topdown, not a metric scene projection, and cannot verify "
            "map-scene alignment by itself."
        ),
        "topdown_image": str(topdown_path),
        "partition_count": len(partitions),
        "partitions": partitions,
        "high_signal_object_labels": high_signal_object_labels(partitions),
        "self_consistency": scene_self_consistency(partitions),
    }


def scene_partitions(scene_root: Path) -> list[dict[str, Any]]:
    if not scene_root.is_dir():
        return []
    partitions = []
    for index, partition_root in enumerate(
        sorted(path for path in scene_root.iterdir() if path.is_dir()),
        start=1,
    ):
        if partition_root.name == "storey_1":
            continue
        scene_usd = partition_root / "scene.usd"
        gaussian_layer = partition_root / "scene_gs.usda"
        if not scene_usd.is_file() and not gaussian_layer.is_file():
            continue
        object_counts = object_counts_from_gaussian_layer(gaussian_layer)
        if not object_counts:
            object_counts = object_counts_from_materials(
                partition_root / "configuration" / "materials"
            )
        partitions.append(
            {
                "partition_id": partition_root.name,
                "display_order": index,
                "scene_usd": file_inventory(scene_usd),
                "gaussian_layer": file_inventory(gaussian_layer),
                "config_yaml": file_inventory(partition_root / "config.yaml"),
                "usdz": file_inventory(partition_root / "xm_large_scene.usdz"),
                "object_label_count": int(sum(object_counts.values())),
                "unique_object_label_count": int(len(object_counts)),
                "object_name_counts": dict(object_counts.most_common()),
                "high_signal_object_labels": [
                    {"label": name, "count": count} for name, count in object_counts.most_common(12)
                ],
                "scene_frame_bounds": {"status": "not_extracted"},
                "geometry_status": "label_inventory_only",
            }
        )
    return partitions


def object_counts_from_gaussian_layer(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not path.is_file():
        return counts
    text = path.read_text(encoding="utf-8", errors="ignore")
    for name in _PARTITION_RE.findall(text):
        if "__" not in name:
            continue
        _partition_id, raw_object = name.split("__", 1)
        object_name = _INSTANCE_SUFFIX_RE.sub("", raw_object)
        object_name = re.sub(r"__.*$", "", object_name)
        if object_name:
            counts[object_name] += 1
    return counts


def object_counts_from_materials(materials_dir: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not materials_dir.is_dir():
        return counts
    for path in sorted(materials_dir.glob("*_aligned_albedo.png")):
        stem = path.name.removesuffix("_aligned_albedo.png")
        object_name = _INSTANCE_SUFFIX_RE.sub("", stem)
        if object_name:
            counts[object_name] += 1
    return counts


def high_signal_object_labels(partitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total: Counter[str] = Counter()
    for partition in partitions:
        total.update(
            {
                str(name): int(count)
                for name, count in (partition.get("object_name_counts") or {}).items()
            }
        )
    return [{"label": name, "count": count} for name, count in total.most_common(20)]


def scene_self_consistency(partitions: list[dict[str, Any]]) -> dict[str, Any]:
    conflicts = []
    for partition in partitions:
        if int(partition.get("object_label_count") or 0) <= 0:
            conflicts.append(f"{partition['partition_id']} has no object labels")
    return {
        "status": "needs_operator_review" if conflicts else "inventory_consistent",
        "conflicts": conflicts,
        "review_note": (
            "This check proves only inventory consistency. Room-label identity still needs "
            "operator review against a rendered or metric topdown when available."
        ),
    }


def render_label_inventory_topdown(
    partitions: list[dict[str, Any]],
    path: Path,
    *,
    width: int,
    height: int,
) -> None:
    image = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, width - 18, height - 18), outline=(191, 201, 214), width=2)
    draw.text((34, 30), "2rd_floor_seperated label inventory diagnostic", fill=(23, 32, 42))
    draw.text(
        (34, 54),
        "Not Gaussian topdown. Not metric geometry. Labels only.",
        fill=(85, 99, 114),
    )
    if not partitions:
        draw.text((34, 92), "No scene partitions found.", fill=(130, 40, 40))
        image.save(path)
        return
    columns = min(3, max(1, len(partitions)))
    rows = (len(partitions) + columns - 1) // columns
    pad = 22
    top = 92
    cell_w = max(1, (width - 2 * pad) / columns)
    cell_h = max(1, (height - top - pad) / rows)
    for index, partition in enumerate(partitions):
        row = index // columns
        col = index % columns
        x0 = int(pad + col * cell_w + 8)
        y0 = int(top + row * cell_h + 8)
        x1 = int(pad + (col + 1) * cell_w - 8)
        y1 = int(top + (row + 1) * cell_h - 8)
        color = _PARTITION_COLORS[index % len(_PARTITION_COLORS)]
        draw.rounded_rectangle(
            (x0, y0, x1, y1), radius=6, fill=(255, 255, 255), outline=color, width=3
        )
        draw.text((x0 + 12, y0 + 12), str(partition["partition_id"]), fill=(23, 32, 42))
        label_count = partition["object_label_count"]
        unique_label_count = partition["unique_object_label_count"]
        draw.text(
            (x0 + 12, y0 + 34),
            f"labels: {label_count} / unique: {unique_label_count}",
            fill=(85, 99, 114),
        )
        labels = [
            f"{item['label']} x{item['count']}"
            for item in partition.get("high_signal_object_labels", [])[:5]
        ]
        for label_index, label in enumerate(labels):
            draw.text((x0 + 12, y0 + 60 + label_index * 18), label, fill=(35, 45, 58))
    image.save(path)


def validate_scene_topdown_diagnostic(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    require(packet.get("schema") == DIAGNOSTIC_SCHEMA, "unexpected diagnostic schema", errors)
    require(packet.get("up_axis") == "z", "diagnostic must record up_axis=z", errors)
    require(
        packet.get("horizontal_axes") == ["x", "y"],
        "diagnostic must record horizontal_axes=[x,y]",
        errors,
    )
    require(bool(packet.get("geometry_status")), "diagnostic must record geometry_status", errors)
    require(
        int(packet.get("partition_count") or 0) > 0, "diagnostic must list scene partitions", errors
    )
    require(
        Path(str(packet.get("topdown_image") or "")).is_file(),
        "topdown diagnostic image missing",
        errors,
    )
    for partition in packet.get("partitions") or []:
        if not isinstance(partition, dict):
            errors.append("partition rows must be objects")
            continue
        require(bool(partition.get("partition_id")), "partition missing partition_id", errors)
        require(
            "object_name_counts" in partition,
            f"partition {partition.get('partition_id')} missing object_name_counts",
            errors,
        )
    return errors


def render_diagnostic_html(packet: dict[str, Any], *, packet_path: Path) -> str:
    axes = escape_html(json.dumps(packet.get("horizontal_axes") or []))
    rows = "".join(
        "<tr>"
        f"<td>{escape_html(str(partition.get('partition_id') or ''))}</td>"
        f"<td>{partition.get('object_label_count') or 0}</td>"
        f"<td>{partition.get('unique_object_label_count') or 0}</td>"
        f"<td>{high_signal_label_summary(partition)}</td>"
        "</tr>"
        for partition in packet.get("partitions") or []
        if isinstance(partition, dict)
    )
    image_name = Path(str(packet.get("topdown_image") or "")).name
    packet_name = packet_path.name
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>B1 Scene Label Inventory Diagnostic</title>
  <style>
    :root {{ font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #17202a; }}
    body {{ margin: 0; background: #fff; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px 24px 44px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    p {{ color: #5d6b7a; line-height: 1.5; }}
    img {{ max-width: 100%; border: 1px solid #d8dee6; border-radius: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
    th, td {{ padding: 10px; border: 1px solid #d8dee6; text-align: left; vertical-align: top; }}
    th {{ background: #f7f8fa; font-size: 12px; color: #39424e; }}
  </style>
</head>
<body>
<main>
  <h1>B1 Scene Label Inventory Diagnostic</h1>
  <p>Geometry status: <strong>{escape_html(str(packet.get("geometry_status") or ""))}</strong>.
  Up axis: <strong>{escape_html(str(packet.get("up_axis") or ""))}</strong>.
  Horizontal axes: <strong>{axes}</strong>.</p>
  <p>{escape_html(str(packet.get("geometry_honesty") or ""))}</p>
  <img src="{escape_html(image_name)}" alt="B1 scene label inventory diagnostic" />
  <table>
    <thead>
      <tr><th>Partition</th><th>Object Labels</th><th>Unique</th><th>High-Signal Labels</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p><a href="{escape_html(packet_name)}">scene_topdown_diagnostic.json</a></p>
</main>
</body>
</html>
"""


def high_signal_label_summary(partition: dict[str, Any]) -> str:
    labels = [
        str(item.get("label") or "")
        for item in partition.get("high_signal_object_labels", [])[:8]
        if isinstance(item, dict)
    ]
    return escape_html(", ".join(label for label in labels if label))


def file_inventory(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else 0,
    }


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


if __name__ == "__main__":
    raise SystemExit(main())
