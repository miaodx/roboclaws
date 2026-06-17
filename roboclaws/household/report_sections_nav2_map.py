from __future__ import annotations

import html
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

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
    agent_view = run_result.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    fixture_hints = agent_view.get("fixture_hints") or {}
    map_contract_label = _map_contract_label(bundle)
    map_contract_note = _map_contract_note(bundle)
    preview = _nav2_bundle_preview_asset(
        run_dir,
        artifacts,
        metric_map=metric_map,
        fixture_hints=fixture_hints,
        report_asset_src=report_asset_src,
    )
    fallback_preview = ""
    if not preview:
        fallback_preview = _write_nav2_static_navigation_preview(
            run_dir,
            run_result,
            report_asset_src=report_asset_src,
        )
        preview = fallback_preview
    preview_figure = (
        '<figure class="nav2-preview">'
        f"{review_image(preview, map_contract_label)}"
        f"<figcaption><strong>{html.escape(map_contract_label)}</strong>"
        "<span>Raw/source-map aligned static navigation preview. Runtime semantic "
        "evidence is reported from Runtime Metric Map JSON and tables, not this image.</span>"
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
    if fallback_preview:
        rows.append(
            "<tr>"
            "<td>report_static_navigation_map.png</td>"
            f"<td>{html.escape(str(fallback_preview))}</td>"
            "<td><code></code></td>"
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
        "parameters, and report views. The static navigation preview is rendered in "
        "the raw/source map orientation; no rectified display frame is substituted. The "
        "raw occupancy artifact remains linked below. This is not Runtime Metric Map "
        "evidence and not live ROS/Nav2 execution.</p>"
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
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    report_asset_src: ReportAssetSrcResolver,
) -> str:
    preview_path = run_dir / str(artifacts.get("preview_png") or "map_bundle/preview.png")
    map_pgm = run_dir / str(artifacts.get("occupancy_image") or "map_bundle/map.pgm")
    map_yaml = run_dir / str(artifacts.get("map_yaml") or "map_bundle/map.yaml")
    if preview_path.is_file() and (
        not map_pgm.is_file()
        or not map_yaml.is_file()
        or _nav2_occupancy_preview_has_usable_framing(
            map_pgm=map_pgm,
            map_yaml=map_yaml,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
        )
    ):
        return report_asset_src(preview_path, run_dir)
    return ""


def _write_nav2_static_navigation_preview(
    run_dir: Path,
    run_result: dict[str, Any],
    *,
    report_asset_src: ReportAssetSrcResolver,
) -> str:
    agent_view = run_result.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    fixture_hints = agent_view.get("fixture_hints") or {}
    rooms = metric_map.get("rooms") or []
    waypoints = metric_map.get("inspection_waypoints") or []
    fixture_rooms = fixture_hints.get("rooms") or []
    if not rooms and not waypoints and not fixture_rooms:
        return ""
    output_dir = run_dir / "map_bundle"
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = run_result.get("nav2_map_bundle") or {}
    artifacts = bundle.get("artifact_paths") or {}
    map_pgm = run_dir / str(artifacts.get("occupancy_image") or "map_bundle/map.pgm")
    map_yaml = run_dir / str(artifacts.get("map_yaml") or "map_bundle/map.yaml")
    if (
        map_pgm.is_file()
        and map_yaml.is_file()
        and _nav2_occupancy_preview_has_usable_framing(
            map_pgm=map_pgm,
            map_yaml=map_yaml,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
        )
    ):
        return _write_nav2_occupancy_navigation_preview(
            run_dir,
            output_dir=output_dir,
            map_pgm=map_pgm,
            map_yaml=map_yaml,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
            report_asset_src=report_asset_src,
        )
    output_path = output_dir / "report_static_navigation_map.png"
    image = Image.new("RGB", (1100, 360), (248, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.text((28, 22), _map_contract_label(bundle), fill=(30, 34, 42))
    draw.text(
        (28, 44), "Source-frame fallback view; no rectified display frame.", fill=(86, 95, 112)
    )
    transform = _nav2_preview_transform(rooms, waypoints, fixture_rooms)
    room_labels: list[tuple[int, int, str]] = []

    for room in rooms:
        points = room.get("polygon") or []
        if len(points) < 2:
            continue
        xs = [float(point.get("x", 0.0)) for point in points]
        ys = [float(point.get("y", 0.0)) for point in points]
        left, top = transform(min(xs), max(ys))
        right, bottom = transform(max(xs), min(ys))
        draw.rectangle(
            (left, top, right, bottom),
            fill=(232, 238, 246),
            outline=(148, 163, 184),
            width=2,
        )
        room_labels.append((left, top, str(room.get("room_label") or room.get("room_id") or "")))

    for room in fixture_rooms:
        for fixture in room.get("fixtures") or []:
            pose = fixture.get("pose") or {}
            footprint = fixture.get("footprint") or {}
            x, y = transform(float(pose.get("x", 0.0)), float(pose.get("y", 0.0)))
            half_w = max(
                14,
                int(float(footprint.get("width_m") or 0.5) * getattr(transform, "x_scale") * 0.5),
            )
            half_h = max(
                8,
                int(float(footprint.get("depth_m") or 0.35) * getattr(transform, "y_scale") * 0.5),
            )
            draw.rounded_rectangle(
                (x - half_w, y - half_h, x + half_w, y + half_h),
                radius=3,
                fill=(113, 124, 141),
                outline=(71, 85, 105),
            )

    for waypoint in waypoints:
        x, y = transform(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0)))
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(35, 134, 90))

    robot_pose = metric_map.get("robot_pose") or {}
    if robot_pose:
        x, y = transform(float(robot_pose.get("x", 0.0)), float(robot_pose.get("y", 0.0)))
        draw.ellipse(
            (x - 13, y - 13, x + 13, y + 13),
            fill=(46, 88, 178),
            outline=(30, 64, 130),
            width=2,
        )
        draw.text((x + 16, y - 7), "robot", fill=(30, 64, 130))

    for left, top, label in room_labels:
        label_y = max(48, top - 18)
        text_box = draw.textbbox((left, label_y), label)
        draw.rounded_rectangle(
            (text_box[0] - 4, text_box[1] - 2, text_box[2] + 4, text_box[3] + 2),
            radius=3,
            fill=(248, 250, 252),
            outline=(213, 220, 230),
        )
        draw.text((left, label_y), label, fill=(51, 65, 85))

    image.save(output_path, format="PNG")
    return report_asset_src(output_path, run_dir)


def _nav2_occupancy_preview_has_usable_framing(
    *,
    map_pgm: Path,
    map_yaml: Path,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> bool:
    """Return whether the occupancy map gives the semantic overlay a readable frame."""

    try:
        image = Image.open(map_pgm)
    except OSError:
        return False
    if image.width < 1 or image.height < 1:
        return False
    parsed_yaml = _simple_map_yaml(map_yaml.read_text(encoding="utf-8"))
    resolution = float(parsed_yaml.get("resolution") or metric_map.get("resolution_m") or 0.05)
    if resolution <= 0:
        return False
    origin = parsed_yaml.get("origin") if isinstance(parsed_yaml.get("origin"), list) else []
    origin = (origin + [0.0, 0.0, 0.0])[:3]
    points = _nav2_semantic_preview_points(metric_map, fixture_hints)
    if len(points) < 2:
        return False

    cols: list[int] = []
    rows: list[int] = []
    for x, y in points:
        cols.append(int(round((x - float(origin[0])) / resolution)))
        rows.append(image.height - 1 - int(round((y - float(origin[1])) / resolution)))
    min_col, max_col = max(0, min(cols)), min(image.width - 1, max(cols))
    min_row, max_row = max(0, min(rows)), min(image.height - 1, max(rows))
    if min_col >= max_col or min_row >= max_row:
        return False
    x_coverage = (max_col - min_col + 1) / image.width
    y_coverage = (max_row - min_row + 1) / image.height
    return x_coverage >= 0.35 and y_coverage >= 0.35


def _nav2_semantic_preview_points(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for room in metric_map.get("rooms") or []:
        for point in room.get("polygon") or []:
            points.append((float(point.get("x", 0.0)), float(point.get("y", 0.0))))
    for waypoint in metric_map.get("inspection_waypoints") or []:
        points.append((float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0))))
    robot_pose = metric_map.get("robot_pose") or {}
    if robot_pose:
        points.append((float(robot_pose.get("x", 0.0)), float(robot_pose.get("y", 0.0))))
    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            pose = fixture.get("pose") or {}
            points.append((float(pose.get("x", 0.0)), float(pose.get("y", 0.0))))
    return points


def _write_nav2_occupancy_navigation_preview(
    run_dir: Path,
    *,
    output_dir: Path,
    map_pgm: Path,
    map_yaml: Path,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    report_asset_src: ReportAssetSrcResolver,
) -> str:
    output_path = output_dir / "report_static_navigation_map.png"
    image = Image.open(map_pgm).convert("L")
    image = Image.eval(image, lambda value: 255 if value >= 250 else 28 if value <= 5 else 205)
    image = image.convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    parsed_yaml = _simple_map_yaml(map_yaml.read_text(encoding="utf-8"))
    resolution = float(parsed_yaml.get("resolution") or metric_map.get("resolution_m") or 0.05)
    origin = parsed_yaml.get("origin") if isinstance(parsed_yaml.get("origin"), list) else []
    origin = (origin + [0.0, 0.0, 0.0])[:3]

    def transform(x: float, y: float) -> tuple[int, int]:
        col = int(round((x - float(origin[0])) / resolution))
        row = image.height - 1 - int(round((y - float(origin[1])) / resolution))
        return col, row

    draw.rectangle((10, 10, 565, 46), fill=(255, 255, 255, 225), outline=(213, 220, 230, 230))
    draw.text(
        (18, 17), "Raw/source-map aligned view; no rectified display frame", fill=(30, 41, 59, 255)
    )

    for room in metric_map.get("rooms") or []:
        points = [
            transform(float(point.get("x", 0.0)), float(point.get("y", 0.0)))
            for point in room.get("polygon") or []
        ]
        if len(points) < 3:
            continue
        draw.polygon(points, fill=(72, 121, 210, 44), outline=(31, 79, 168, 210))
        cx = sum(point[0] for point in points) / len(points)
        cy = sum(point[1] for point in points) / len(points)
        draw.text(
            (cx - 28, cy - 7),
            str(room.get("room_label") or room.get("room_id") or "")[:18],
            fill=(15, 39, 82, 255),
        )

    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            pose = fixture.get("pose") or {}
            x, y = transform(float(pose.get("x", 0.0)), float(pose.get("y", 0.0)))
            draw.rectangle((x - 7, y - 5, x + 7, y + 5), fill=(130, 82, 32, 230))

    for waypoint in metric_map.get("inspection_waypoints") or []:
        x, y = transform(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0)))
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(34, 158, 91, 245))
        draw.text((x + 7, y - 6), str(waypoint.get("waypoint_id") or ""), fill=(12, 74, 38, 255))

    robot_pose = metric_map.get("robot_pose") or {}
    if robot_pose:
        x, y = transform(float(robot_pose.get("x", 0.0)), float(robot_pose.get("y", 0.0)))
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(46, 88, 178, 240))
        draw.text((x + 12, y - 7), "robot", fill=(22, 50, 112, 255))

    max_width = 1200
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, max(1, int(image.height * ratio))))
    image.save(output_path, format="PNG")
    return report_asset_src(output_path, run_dir)


def _simple_map_yaml(text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            payload[key.strip()] = [
                float(item.strip()) for item in value.removeprefix("[").removesuffix("]").split(",")
            ]
        elif value.replace(".", "", 1).replace("-", "", 1).isdigit():
            payload[key.strip()] = float(value) if "." in value else int(value)
        else:
            payload[key.strip()] = value.strip('"')
    return payload


def _nav2_preview_transform(
    rooms: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
    fixture_rooms: list[dict[str, Any]],
) -> Any:
    xs: list[float] = []
    ys: list[float] = []
    for room in rooms:
        for point in room.get("polygon") or []:
            xs.append(float(point.get("x", 0.0)))
            ys.append(float(point.get("y", 0.0)))
    for waypoint in waypoints:
        xs.append(float(waypoint.get("x", 0.0)))
        ys.append(float(waypoint.get("y", 0.0)))
    for room in fixture_rooms:
        for fixture in room.get("fixtures") or []:
            pose = fixture.get("pose") or {}
            xs.append(float(pose.get("x", 0.0)))
            ys.append(float(pose.get("y", 0.0)))
    min_x, max_x = (min(xs), max(xs)) if xs else (0.0, 1.0)
    min_y, max_y = (min(ys), max(ys)) if ys else (0.0, 1.0)
    x_span = max(max_x - min_x, 1.0)
    y_span = max(max_y - min_y, 1.0)
    margin_x = 58
    margin_y = 72
    x_scale = (1100 - margin_x * 2) / x_span
    y_scale = (360 - margin_y * 2) / y_span

    def transform(x: float, y: float) -> tuple[int, int]:
        return (
            int(margin_x + (x - min_x) * x_scale),
            int(360 - margin_y - (y - min_y) * y_scale),
        )

    setattr(transform, "x_scale", x_scale)
    setattr(transform, "y_scale", y_scale)
    return transform


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
