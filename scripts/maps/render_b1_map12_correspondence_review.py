#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from scripts.maps.fit_b1_map12_scene_alignment import (
    anchor_uses_known_poor_seed,
    valid_xy,
    valid_xyz,
    validate_correspondence_manifest,
)

REVIEW_PACKET_SCHEMA = "b1_map12_correspondence_review_packet_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a B1 / Map 12 correspondence anchor review packet."
    )
    parser.add_argument("--correspondences", type=Path, required=True)
    parser.add_argument("--map-bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = json.loads(args.correspondences.read_text(encoding="utf-8"))
    packet = build_review_packet(
        manifest,
        map_bundle=args.map_bundle,
        correspondences_path=args.correspondences,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = args.output_dir / "correspondence_review_packet.json"
    report_path = args.output_dir / "correspondence_review.html"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(
        render_review_report(
            packet,
            output_dir=args.output_dir,
            packet_path=packet_path,
            correspondences_path=args.correspondences,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": REVIEW_PACKET_SCHEMA,
                "status": packet["review_status"],
                "accepted_anchor_count": packet["accepted_anchor_count"],
                "output": str(report_path),
            },
            sort_keys=True,
        )
    )
    return 0


def build_review_packet(
    manifest: dict[str, Any],
    *,
    map_bundle: Path,
    correspondences_path: Path | None = None,
) -> dict[str, Any]:
    anchors = [item for item in manifest.get("anchors") or [] if isinstance(item, dict)]
    rows = [review_anchor_row(anchor, index=index) for index, anchor in enumerate(anchors, start=1)]
    accepted = [row for row in rows if row["review_status"] == "accepted"]
    ready = [row for row in accepted if row["fit_ready"]]
    validation_errors = validate_correspondence_manifest(manifest)
    review_status = (
        "ready_for_fit" if len(ready) >= 6 and not validation_errors else "review_pending"
    )
    if validation_errors:
        review_status = "manifest_needs_fix"
    return {
        "schema": REVIEW_PACKET_SCHEMA,
        "source_manifest_schema": manifest.get("schema"),
        "correspondences_artifact": str(correspondences_path) if correspondences_path else "",
        "map_bundle": str(map_bundle),
        "map_preview": first_existing_path(
            [
                Path(map_bundle) / "room_semantic_topdown.png",
                Path(map_bundle) / "preview.png",
                Path(map_bundle) / "map.pgm",
            ]
        ),
        "source_map_frame": str(manifest.get("source_map_frame") or ""),
        "target_scene_frame": str(manifest.get("target_scene_frame") or ""),
        "bbox_seed_policy": str(manifest.get("bbox_seed_policy") or ""),
        "known_poor_seed_rule": (
            "The bbox-fit overlay may seed coarse visual search only. It must not prefill "
            "accepted scene coordinates or count as residual evidence."
        ),
        "review_status": review_status,
        "anchor_count": len(rows),
        "accepted_anchor_count": len(accepted),
        "fit_ready_anchor_count": len(ready),
        "required_fit_ready_anchor_count": 6,
        "manifest_validation": {
            "status": "passed" if not validation_errors else "failed",
            "errors": validation_errors,
        },
        "anchors": rows,
        "next_action": next_action(review_status, rows),
    }


def review_anchor_row(anchor: dict[str, Any], *, index: int) -> dict[str, Any]:
    review_status = str(anchor.get("review_status") or "proposed")
    has_map_pick = valid_xy(anchor.get("map_xy"))
    has_scene_pick = valid_xyz(anchor.get("scene_xyz"))
    uses_seed = anchor_uses_known_poor_seed(anchor)
    fit_ready = review_status == "accepted" and has_map_pick and has_scene_pick and not uses_seed
    return {
        "index": index,
        "anchor_id": str(anchor.get("anchor_id") or f"anchor_{index:03d}"),
        "anchor_type": str(anchor.get("anchor_type") or ""),
        "navigation_area_id": str(anchor.get("navigation_area_id") or ""),
        "asset_partition_id": str(anchor.get("asset_partition_id") or ""),
        "review_status": review_status,
        "has_map_pick": has_map_pick,
        "has_scene_pick": has_scene_pick,
        "uses_known_poor_bbox_seed": uses_seed,
        "fit_ready": fit_ready,
        "map_xy": anchor.get("map_xy"),
        "scene_xyz": anchor.get("scene_xyz"),
        "confidence": anchor.get("confidence"),
        "evidence": anchor.get("evidence") if isinstance(anchor.get("evidence"), dict) else {},
        "review_action": review_action(
            review_status=review_status,
            has_map_pick=has_map_pick,
            has_scene_pick=has_scene_pick,
            uses_seed=uses_seed,
        ),
    }


def review_action(
    *,
    review_status: str,
    has_map_pick: bool,
    has_scene_pick: bool,
    uses_seed: bool,
) -> str:
    if uses_seed:
        return "replace seed-derived coordinates with explicit operator map and scene picks"
    if review_status != "accepted":
        return "pick explicit map_xy and scene_xyz, then mark accepted after operator review"
    if not has_map_pick or not has_scene_pick:
        return "accepted anchors require both map_xy and scene_xyz before fitting"
    return "ready_for_fit"


def next_action(review_status: str, rows: list[dict[str, Any]]) -> str:
    if review_status == "manifest_needs_fix":
        return "Fix manifest validation errors before anchor fitting."
    ready_count = sum(1 for row in rows if row["fit_ready"])
    if ready_count < 6:
        return (
            "Review anchor candidates and produce at least six accepted anchors with "
            "explicit map and scene picks."
        )
    return "Run the residual fitter and inspect global/area pass-fail status."


def render_review_report(
    packet: dict[str, Any],
    *,
    output_dir: Path,
    packet_path: Path,
    correspondences_path: Path,
) -> str:
    anchor_rows = "".join(
        render_anchor_row(row, output_dir=output_dir) for row in packet["anchors"]
    )
    preview = packet.get("map_preview") or ""
    preview_src = escape(relative_href(output_dir, Path(preview))) if preview else ""
    preview_html = (
        f'<img class="preview" src="{preview_src}" alt="Map preview" />'
        if preview
        else "<p>No map preview image was found.</p>"
    )
    packet_href = escape(relative_href(output_dir, packet_path))
    manifest_href = escape(relative_href(output_dir, correspondences_path))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>B1 / Map 12 Correspondence Review</title>
  <style>
    :root {{
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
      color: #17202a;
      background: #fff;
      --line: #d8dee6;
      --muted: #5d6b7a;
      --panel: #f7f8fa;
      --warn: #8a5a00;
    }}
    body {{ margin: 0; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 24px 48px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; line-height: 1.15; letter-spacing: 0; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; letter-spacing: 0; }}
    p {{ color: var(--muted); line-height: 1.5; }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      margin: 18px 0;
    }}
    .summary div {{
      padding: 12px 14px;
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }}
    .summary dt {{ color: var(--muted); font-size: 12px; margin-bottom: 4px; }}
    .summary dd {{ margin: 0; font-weight: 650; overflow-wrap: anywhere; }}
    .notice {{
      border: 1px solid #e3c075;
      background: #fff8e8;
      border-radius: 8px;
      padding: 12px 14px;
      color: #5b3e00;
    }}
    .preview {{
      max-width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #101820;
    }}
    table {{ width: 100%; border-collapse: collapse; border: 1px solid var(--line); }}
    th, td {{
      text-align: left;
      vertical-align: top;
      padding: 10px;
      border-bottom: 1px solid var(--line);
    }}
    th {{ background: var(--panel); color: #39424e; font-size: 12px; }}
    td {{ font-size: 13px; }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }}
    .warn {{ color: var(--warn); font-weight: 700; }}
    @media (max-width: 720px) {{
      main {{ padding: 22px 16px 36px; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>B1 / Map 12 Correspondence Review</h1>
  <p>Operator review packet for map-scene correspondence anchors before residual fitting.</p>
  <section class="summary">
    {summary_rows(packet)}
  </section>
  <div class="notice">{escape(str(packet["known_poor_seed_rule"]))}</div>
  <h2>Map Context</h2>
  {preview_html}
  <h2>Anchors</h2>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Status</th><th>Map Pick</th><th>Scene Pick</th>
        <th>Area / Partition</th><th>Evidence</th><th>Action</th>
      </tr>
    </thead>
    <tbody>{anchor_rows}</tbody>
  </table>
  <h2>Artifacts</h2>
  <p><a href="{packet_href}">correspondence_review_packet.json</a></p>
  <p><a href="{manifest_href}">source correspondence manifest</a></p>
</main>
</body>
</html>
"""


def render_anchor_row(row: dict[str, Any], *, output_dir: Path) -> str:
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    map_image = str(evidence.get("map_image") or "")
    scene_image = str(evidence.get("scene_image") or "")
    evidence_bits = []
    if map_image:
        evidence_bits.append(
            f'<a href="{escape(relative_href(output_dir, Path(map_image)))}">map image</a>'
        )
    if scene_image:
        evidence_bits.append(
            f'<a href="{escape(relative_href(output_dir, Path(scene_image)))}">scene image</a>'
        )
    note = str(evidence.get("operator_note") or "")
    if note:
        evidence_bits.append(escape(note))
    action_class = "warn" if not row.get("fit_ready") else ""
    anchor_cell = (
        f"<td><code>{escape(str(row['anchor_id']))}</code><br />"
        f"{escape(str(row['anchor_type']))}</td>"
    )
    area_cell = (
        f"<td>{escape(str(row['navigation_area_id']))}<br />"
        f"{escape(str(row['asset_partition_id']))}</td>"
    )
    return (
        "<tr>"
        f"{anchor_cell}"
        f"<td>{escape(str(row['review_status']))}</td>"
        f"<td>{escape(json.dumps(row.get('map_xy')))}</td>"
        f"<td>{escape(json.dumps(row.get('scene_xyz')))}</td>"
        f"{area_cell}"
        f"<td>{'<br />'.join(evidence_bits) if evidence_bits else ''}</td>"
        f'<td class="{action_class}">{escape(str(row["review_action"]))}</td>'
        "</tr>"
    )


def summary_rows(packet: dict[str, Any]) -> str:
    rows = [
        ("Review status", str(packet.get("review_status") or "")),
        ("Anchors", str(packet.get("anchor_count") or 0)),
        ("Accepted", str(packet.get("accepted_anchor_count") or 0)),
        ("Fit-ready", f"{packet.get('fit_ready_anchor_count') or 0}/6"),
        ("Source frame", str(packet.get("source_map_frame") or "")),
        ("Scene frame", str(packet.get("target_scene_frame") or "")),
        ("BBox seed policy", str(packet.get("bbox_seed_policy") or "")),
        ("Next action", str(packet.get("next_action") or "")),
    ]
    return "".join(
        f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>" for label, value in rows
    )


def first_existing_path(paths: list[Path]) -> str:
    for path in paths:
        if path.is_file():
            return str(path)
    return ""


def relative_href(base_dir: Path, path: Path) -> str:
    target = Path(path)
    if not target.is_absolute():
        target = target.resolve()
    base = Path(base_dir).resolve()
    try:
        return target.relative_to(base).as_posix()
    except ValueError:
        return target.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
