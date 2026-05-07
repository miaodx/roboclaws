from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from roboclaws.molmo_cleanup.types import CleanupScenario

_COLORS = {
    "dish": (65, 125, 193),
    "book": (117, 86, 160),
    "linen": (78, 154, 96),
    "food": (206, 108, 65),
    "toy": (196, 154, 56),
    "electronics": (80, 80, 80),
}


def write_state_snapshot(
    scenario: CleanupScenario,
    locations: dict[str, str],
    output_path: Path,
    *,
    title: str,
) -> Path:
    """Render a compact deterministic room-state PNG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (900, 520), (249, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 888, 508), outline=(190, 194, 202), width=2)
    draw.text((28, 26), title, fill=(30, 34, 42))

    positions = _receptacle_positions()
    receptacles = {item.receptacle_id: item for item in scenario.receptacles}
    for receptacle_id, (x, y) in positions.items():
        receptacle = receptacles[receptacle_id]
        draw.rounded_rectangle((x - 80, y - 32, x + 80, y + 32), radius=6, fill=(232, 235, 241))
        draw.rectangle((x - 80, y - 32, x + 80, y + 32), outline=(169, 176, 190), width=1)
        draw.text((x - 70, y - 8), receptacle.name[:22], fill=(45, 51, 64))

    offsets: dict[str, int] = {}
    for obj in sorted(scenario.objects, key=lambda item: item.object_id):
        location_id = locations.get(obj.object_id, obj.location_id)
        x, y = positions.get(location_id, (450, 470))
        offset = offsets.get(location_id, 0)
        offsets[location_id] = offset + 1
        color = _COLORS.get(obj.category, (70, 90, 120))
        marker_x = x - 58 + offset * 28
        marker_y = y + 44
        draw.ellipse((marker_x, marker_y, marker_x + 20, marker_y + 20), fill=color)
        draw.text(
            (marker_x - 8, marker_y + 24),
            obj.object_id.split("_", 1)[0][:8],
            fill=(30, 34, 42),
        )

    image.save(output_path, format="PNG")
    return output_path


def render_cleanup_report(
    *,
    run_dir: Path,
    scenario: CleanupScenario,
    run_result: dict[str, Any],
    trace_events: list[dict[str, Any]],
    before_snapshot: Path,
    after_snapshot: Path,
    robot_view_steps: list[dict[str, Any]] | None = None,
) -> Path:
    """Write a self-contained cleanup `report.html`."""
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.html"
    moves = _extract_moves(trace_events)
    score = run_result["score"]
    restored_summary = f"{score['restored_count']}/{score['total_targets']}"
    before_name = html.escape(before_snapshot.name)
    after_name = html.escape(after_snapshot.name)
    body = f"""
    <section class="summary">
      <h1>MolmoSpaces Cleanup Pilot</h1>
      <div class="badges">
        {_badge("Scenario", scenario.scenario_id)}
        {_badge("Backend", run_result.get("backend", "unknown"))}
        {_badge("Status", run_result["cleanup_status"])}
        {_badge("Restored", restored_summary)}
        {_badge("Planner", run_result.get("planner", "unknown"))}
        {_badge("Provenance", run_result["primitive_provenance"])}
        {_robot_badge(run_result)}
      </div>
    </section>
    <section class="snapshots">
      <figure>
        <img src="{before_name}" alt="Before cleanup">
        <figcaption>Before</figcaption>
      </figure>
      <figure>
        <img src="{after_name}" alt="After cleanup">
        <figcaption>After</figcaption>
      </figure>
    </section>
    <section>
      <h2>Object Moves</h2>
      {_moves_table(moves)}
    </section>
    {_robot_timeline(robot_view_steps or [])}
    <section>
      <h2>Score</h2>
      {_score_table(score)}
    </section>
    """
    report_path.write_text(_wrap_html(body), encoding="utf-8")
    return report_path


def _badge(label: str, value: Any) -> str:
    return (
        f'<span class="badge">{html.escape(str(label))}: '
        f"<strong>{html.escape(str(value))}</strong></span>"
    )


def _robot_badge(run_result: dict[str, Any]) -> str:
    robot_name = run_result.get("robot_name")
    if not robot_name:
        return ""
    return _badge("Robot", robot_name)


def _robot_timeline(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return ""
    cards = []
    for index, step in enumerate(steps, start=1):
        views = step.get("views", {})
        pose = step.get("robot_pose") or {}
        pose_text = f"x={pose.get('x', '?')} y={pose.get('y', '?')} theta={pose.get('theta', '?')}"
        cards.append(
            '<article class="robot-step">'
            f"<h3>{index}. {html.escape(str(step.get('action', step.get('label', 'step'))))}</h3>"
            f'<p class="pose">{html.escape(pose_text)}</p>'
            '<div class="views">'
            f"{_view_figure(views.get('fpv'), 'FPV')}"
            f"{_view_figure(views.get('chase'), 'Chase')}"
            f"{_view_figure(views.get('map'), 'Map')}"
            "</div>"
            "</article>"
        )
    return (
        "<section><h2>Robot View Timeline</h2>"
        '<p class="note">FPV and chase are rendered from the RBY1M MuJoCo scene. '
        "The map is a report artifact from public simulator state.</p>"
        + "".join(cards)
        + "</section>"
    )


def _view_figure(path: Any, label: str) -> str:
    if not path:
        return ""
    escaped_path = html.escape(str(path))
    escaped_label = html.escape(label)
    return (
        "<figure>"
        f'<img src="{escaped_path}" alt="{escaped_label} view">'
        f"<figcaption>{escaped_label}</figcaption>"
        "</figure>"
    )


def _moves_table(moves: list[dict[str, Any]]) -> str:
    if not moves:
        return "<p>No place operations recorded.</p>"
    rows = []
    for index, move in enumerate(moves, start=1):
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(str(move.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(move.get('receptacle_id', '')))}</td>"
            f"<td>{html.escape(str(move.get('primitive_provenance', '')))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>#</th><th>Object</th><th>Placed at</th>"
        "<th>Primitive provenance</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _score_table(score: dict[str, Any]) -> str:
    rows = []
    for row in score["object_results"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['object_id']))}</td>"
            f"<td>{html.escape(str(row['actual_location_id']))}</td>"
            f"<td>{'yes' if row['restored'] else 'no'}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Object</th><th>Final location</th><th>Restored</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _extract_moves(trace_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    moves: list[dict[str, Any]] = []
    for event in trace_events:
        if event.get("tool") != "place" or event.get("event") != "response":
            continue
        response = event.get("response")
        if isinstance(response, dict) and response.get("ok"):
            moves.append(response)
    return moves


def _wrap_html(body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MolmoSpaces Cleanup Pilot</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      color: #20242c;
      background: #f7f8fa;
    }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 24px 48px; }}
    h1 {{ font-size: 28px; margin: 0 0 16px; }}
    h2 {{ font-size: 19px; margin: 28px 0 12px; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{ background: #fff; border: 1px solid #d9dde6; border-radius: 6px; padding: 7px 10px; }}
    .snapshots {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }}
    figure {{
      margin: 0;
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 10px;
    }}
    img {{ width: 100%; height: auto; display: block; }}
    figcaption {{ margin-top: 8px; color: #565f70; font-size: 14px; }}
    .note {{ color: #565f70; margin: 0 0 12px; }}
    .robot-step {{
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 12px;
      margin-bottom: 14px;
    }}
    .robot-step h3 {{ font-size: 16px; margin: 0 0 4px; }}
    .pose {{ margin: 0 0 10px; color: #565f70; font-size: 13px; }}
    .views {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 10px;
    }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9dde6; }}
    th, td {{
      padding: 9px 10px;
      text-align: left;
      border-bottom: 1px solid #e5e8ee;
      font-size: 14px;
    }}
    th {{ background: #eef1f5; font-weight: 650; }}
  </style>
</head>
<body><main>{body}</main></body>
</html>
"""


def _receptacle_positions() -> dict[str, tuple[int, int]]:
    return {
        "sofa_01": (160, 130),
        "floor_01": (450, 250),
        "armchair_01": (725, 130),
        "desk_01": (160, 350),
        "coffee_table_01": (450, 130),
        "sink_01": (725, 350),
        "bookshelf_01": (160, 465),
        "laundry_hamper_01": (450, 465),
        "fridge_01": (725, 465),
        "toy_bin_01": (450, 350),
    }


def write_trace_jsonl(trace_path: Path, events: list[dict[str, Any]]) -> None:
    trace_path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
