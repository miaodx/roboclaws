from __future__ import annotations

import html
from collections.abc import Callable
from pathlib import Path
from typing import Any

MetricRenderer = Callable[[str, Any], str]
ReportAssetSrcResolver = Callable[[Any, Path | None], str]
ReviewImageRenderer = Callable[[Any, str], str]


def nav2_map_bundle_section(
    run_dir: Path,
    run_result: dict[str, Any],
    *,
    metric: MetricRenderer,
    review_image: ReviewImageRenderer,
    report_asset_src: ReportAssetSrcResolver,
) -> str:
    bundle = run_result.get("nav2_map_bundle") or {}
    if not bundle:
        return ""
    artifacts = bundle.get("artifact_paths") or {}
    hashes = bundle.get("artifact_hashes") or {}
    map_contract_label = _map_contract_label(bundle)
    map_contract_note = _map_contract_note(bundle)
    preview = _nav2_bundle_preview_asset(run_dir, artifacts, report_asset_src=report_asset_src)
    preview_figure = (
        '<figure class="nav2-preview">'
        f"{review_image(preview, map_contract_label)}"
        f"<figcaption><strong>{html.escape(map_contract_label)}</strong>"
        "<span>Static navigation artifact. Top-down scene maps and Runtime Metric Map "
        "tables are the active review surfaces.</span>"
        "</figcaption>"
        "</figure>"
        if preview
        else ""
    )
    rows = []
    labels = {
        "map_yaml": "map.yaml",
        "occupancy_image": "map.pgm",
        "semantics_json": "semantics.json",
        "robot_profile": "profiles/rby1m.yaml",
        "costmap_params": "costmaps/rby1m.costmap_params.yaml",
        "preview_png": "preview.png",
    }
    for key, label in labels.items():
        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{html.escape(str(artifacts.get(key, '')))}</td>"
            f"<td><code>{html.escape(str(hashes.get(key, ''))[:16])}</code></td>"
            "</tr>"
        )
    gaps = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in bundle.get("runtime_costmap_gaps") or []
    )
    metrics = (
        '<div class="metric-grid">'
        f"{metric('Environment', bundle.get('environment_id', 'unknown'))}"
        f"{metric('Map source', bundle.get('source_provenance', 'unknown'))}"
        f"{metric('Robot profile', bundle.get('robot_profile_id', 'unknown'))}"
        f"{metric('Costmap profile', bundle.get('costmap_profile_id', 'unknown'))}"
        f"{metric('Parameter hash', str(bundle.get('parameter_hash', ''))[:16])}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Artifact</th><th>Path</th>'
        "<th>SHA-256</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    gap_list = (
        f'<ul class="requirements">{gaps}</ul>'
        if gaps
        else '<p class="note">No runtime costmap gaps were recorded.</p>'
    )
    return (
        '<section class="panel nav2-map-bundle">'
        "<h2>Base Navigation Map Preview "
        f"<span>Nav2 Map Bundle / {html.escape(_map_contract_subtitle(bundle))}</span></h2>"
        '<p class="note">The Nav2 Map Bundle files are the map package a Nav2-style robot '
        "would consume: occupancy grid, static fixture semantics, robot footprint, costmap "
        "parameters, and report views. This section links static map artifacts only; "
        "top-down scene maps and Runtime Metric Map tables carry the active visual and "
        "semantic review evidence.</p>"
        f'<p class="note">{html.escape(map_contract_note)}</p>'
        f"{metrics}"
        '<div class="nav2-explainer">'
        "<div><strong>What it proves</strong><span>Static map, fixtures, robot profile, "
        "and costmap parameters are versioned together.</span></div>"
        "<div><strong>What it does not prove</strong><span>Dynamic obstacle layers, "
        "TF timing, and rolling local costmaps remain explicit gaps.</span></div>"
        "</div>"
        '<div class="nav2-preview-layout">'
        f"{preview_figure}"
        f"{_nav2_preview_legend()}"
        "</div>"
        '<details class="artifact-details"><summary>Map files, hashes, and known gaps</summary>'
        f"{table}{gap_list}</details></section>"
    )


def _map_contract_label(bundle: dict[str, Any]) -> str:
    source = str(bundle.get("source_provenance") or "")
    if "agibot" in source.lower():
        return "Agibot GDK base navigation map preview"
    if "molmospaces" in source.lower():
        return "Agibot-shaped base navigation map preview"
    return "Static navigation map preview"


def _map_contract_subtitle(bundle: dict[str, Any]) -> str:
    source = str(bundle.get("source_provenance") or "")
    if "agibot" in source.lower():
        return "Agibot GDK map artifact"
    if "molmospaces" in source.lower():
        return "Agibot-shaped static map contract"
    return "Static map contract"


def _map_contract_note(bundle: dict[str, Any]) -> str:
    source = str(bundle.get("source_provenance") or "unknown")
    source_root = str(bundle.get("source_bundle_root") or "")
    map_id = str(bundle.get("map_id") or "unknown")
    source_schema = str(bundle.get("source_schema") or "")
    if "agibot" in source.lower():
        prefix = "This map bundle came from an Agibot GDK map artifact."
    elif "molmospaces" in source.lower():
        prefix = (
            "This map bundle is not a real Agibot GDK map; it is a MolmoSpaces public "
            "static navigation map rendered through the Agibot-shaped household "
            "map contract."
        )
    else:
        prefix = "This map bundle is a static public map-contract artifact."
    details = f" Source provenance: {source}; map id: {map_id}."
    if source_schema:
        details += f" Source schema: {source_schema}."
    if source_root:
        details += f" Source root: {source_root}."
    return prefix + details


def _nav2_bundle_preview_asset(
    run_dir: Path,
    artifacts: dict[str, Any],
    *,
    report_asset_src: ReportAssetSrcResolver,
) -> str:
    preview_path = run_dir / str(artifacts.get("preview_png") or "map_bundle/preview.png")
    if preview_path.is_file():
        return report_asset_src(preview_path, run_dir)
    return ""


def _nav2_preview_legend() -> str:
    items = [
        ("room", "Pale polygons", "navigation_area unless marked as a room_boundary"),
        ("fixture", "Gray blocks", "static fixture or obstacle footprint"),
        ("waypoint", "Green dots", "inspection waypoints the agent may visit"),
        ("robot", "Blue dot", "current robot pose on the public map"),
    ]
    rows = []
    for kind, label, detail in items:
        rows.append(
            f'<li><span class="legend-swatch {kind}"></span>'
            f"<strong>{html.escape(label)}</strong><small>{html.escape(detail)}</small></li>"
        )
    return (
        '<aside class="nav2-legend"><h3>Legend</h3><ul>'
        + "".join(rows)
        + "</ul><p>This is the robot's raw/source static navigation map, not a camera "
        "image, not a rectified display frame, and not private mess truth.</p></aside>"
    )
