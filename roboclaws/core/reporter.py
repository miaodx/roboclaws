"""Self-contained HTML report generator for RoboClaws game replays.

Usage (module CLI)::

    python -m roboclaws.core.reporter <replay_dir> [--open] [--compare <other>]

Programmatic::

    from roboclaws.core.reporter import generate, compare
    report_path = generate("output/run_001", auto_open=True)
    compare_path = compare("output/run_a", "output/run_b")
"""

from __future__ import annotations

import argparse
import base64
import html as _html
import json
import webbrowser
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate(
    replay_dir: str | Path,
    output_path: str | Path | None = None,
    auto_open: bool = False,
) -> Path:
    """Generate a self-contained HTML report from a replay directory.

    Args:
        replay_dir: Directory created by :meth:`roboclaws.core.replay.ReplayRecorder.save`.
        output_path: Output ``.html`` path (defaults to ``replay_dir/report.html``).
        auto_open: Open the report in the default browser after writing it.

    Returns:
        Resolved path to the written ``report.html``.

    Raises:
        FileNotFoundError: If ``replay.json`` is not found in *replay_dir*.
    """
    replay_dir = Path(replay_dir)
    manifest_path = replay_dir / "replay.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"replay.json not found in {replay_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    section = _build_run_section(replay_dir, manifest, run_id="run")
    html_content = _wrap_html(section, title="RoboClaws Run Report")
    out_path = Path(output_path) if output_path else replay_dir / "report.html"
    out_path.write_text(html_content, encoding="utf-8")
    if auto_open:
        webbrowser.open(out_path.as_uri())
    return out_path


def compare(
    dir1: str | Path,
    dir2: str | Path,
    output_path: str | Path | None = None,
    auto_open: bool = False,
) -> Path:
    """Generate a side-by-side A/B comparison HTML report for two replay directories.

    Args:
        dir1: First replay directory (labeled "Run A").
        dir2: Second replay directory (labeled "Run B").
        output_path: Output ``.html`` path (defaults to ``dir1/report_compare.html``).
        auto_open: Open the report in the default browser after writing it.

    Returns:
        Resolved path to the written HTML file.
    """
    dir1 = Path(dir1)
    dir2 = Path(dir2)
    manifest1 = json.loads((dir1 / "replay.json").read_text(encoding="utf-8"))
    manifest2 = json.loads((dir2 / "replay.json").read_text(encoding="utf-8"))
    section1 = _build_run_section(dir1, manifest1, run_id="run-a")
    section2 = _build_run_section(dir2, manifest2, run_id="run-b")
    name1 = _html.escape(dir1.name)
    name2 = _html.escape(dir2.name)
    body = (
        f'<div class="compare-layout">'
        f'<div class="compare-col"><h2>Run A: {name1}</h2>{section1}</div>'
        f'<div class="compare-col"><h2>Run B: {name2}</h2>{section2}</div>'
        f"</div>"
    )
    html_content = _wrap_html(body, title="RoboClaws A/B Comparison")
    out_path = Path(output_path) if output_path else dir1 / "report_compare.html"
    out_path.write_text(html_content, encoding="utf-8")
    if auto_open:
        webbrowser.open(out_path.as_uri())
    return out_path


# ---------------------------------------------------------------------------
# HTML building helpers
# ---------------------------------------------------------------------------


def _build_run_section(
    replay_dir: Path,
    manifest: dict[str, Any],
    run_id: str = "run",
) -> str:
    """Return the HTML string for a single run's section."""
    metadata = manifest.get("metadata", {})
    summary = manifest.get("summary", {})
    steps_data: list[dict[str, Any]] = manifest.get("steps", [])

    game = metadata.get("game", "unknown")
    agent_count = int(metadata.get("agent_count", 1))
    total_steps = metadata.get("total_steps", len(steps_data))
    duration = metadata.get("duration_seconds", 0.0)
    vlm_cost = metadata.get("vlm_cost_usd", 0.0)
    scene = metadata.get("scene", "\u2014")
    termination = summary.get("termination_reason", "unknown")
    final_scores: dict[str, Any] = summary.get("final_scores", {})

    if final_scores:
        scores_str = ", ".join(
            f"agent {k}: {v}" for k, v in sorted(final_scores.items(), key=lambda x: str(x[0]))
        )
    else:
        scores_str = "\u2014"

    summary_bar = (
        f'<div class="summary-bar">'
        f'<span class="badge">Game: <strong>{_html.escape(str(game))}</strong></span>'
        f'<span class="badge">Scene: <strong>{_html.escape(str(scene))}</strong></span>'
        f'<span class="badge">Agents: <strong>{agent_count}</strong></span>'
        f'<span class="badge">Steps: <strong>{total_steps}</strong></span>'
        f'<span class="badge">Duration: <strong>{duration:.1f}s</strong></span>'
        f'<span class="badge">VLM cost: <strong>${vlm_cost:.6f}</strong></span>'
        f'<span class="badge">End: <strong>{_html.escape(str(termination))}</strong></span>'
        f'<span class="badge">Scores: <strong>{_html.escape(scores_str)}</strong></span>'
        f"</div>"
    )

    # Frame data (base64 images loaded once, stored in a JS array)
    frame_data: list[dict[str, Any]] = []
    latest_decisions: dict[int, dict[str, Any]] = {}
    for rec in steps_data:
        step = rec.get("step", 0)
        acting_agent = int(rec.get("agent_id", 0))
        tag = f"{step:04d}"
        agent_imgs = [
            _img_to_b64(replay_dir / "agent_frames" / f"{tag}_agent{aid}.png")
            for aid in range(agent_count)
        ]
        overhead_img = _img_to_b64(replay_dir / "overhead" / f"{tag}_overhead.png")
        vlm_response = rec.get("vlm_response", {})
        latest_decisions[acting_agent] = {
            "agent_id": acting_agent,
            "step": step,
            "reasoning": str(vlm_response.get("reasoning") or ""),
            "action": str(vlm_response.get("action") or ""),
            "executed_action": str(vlm_response.get("executed_action") or ""),
            "raw_action": str(vlm_response.get("raw_action") or ""),
            "override_reason": str(vlm_response.get("override_reason") or ""),
        }

        decisions: list[dict[str, Any]] = []
        for aid in range(agent_count):
            decision = dict(latest_decisions.get(aid, {}))
            decision.setdefault("agent_id", aid)
            decision["is_current"] = aid == acting_agent
            decisions.append(decision)

        frame_data.append(
            {
                "step": step,
                "agent_id": acting_agent,
                "agent_imgs": agent_imgs,
                "overhead_img": overhead_img,
                "decisions": decisions,
            }
        )

    n_frames = len(frame_data)
    max_idx = max(0, n_frames - 1)

    agent_ths = "".join(f"<th>Agent {i}</th>" for i in range(agent_count))
    agent_tds = "".join(
        f'<td><img id="{run_id}-agent-{i}" class="frame-img" src="" alt="Agent {i}"/></td>'
        for i in range(agent_count)
    )
    agent_init_js = "; ".join(
        f'document.getElementById(rid+"-agent-{i}").src = f.agent_imgs[{i}] || ""'
        for i in range(agent_count)
    )
    js_id = run_id.replace("-", "_")
    frames_json = json.dumps(frame_data)
    initial_decisions = (
        frame_data[0]["decisions"]
        if frame_data
        else [{"agent_id": aid, "is_current": False} for aid in range(agent_count)]
    )
    decision_cards_html = "".join(_render_decision_card(decision) for decision in initial_decisions)

    viewer_html = (
        f'<div class="viewer">'
        f'<table class="frame-table">'
        f"<thead><tr>{agent_ths}<th>Overhead</th></tr></thead>"
        f"<tbody><tr>"
        f"{agent_tds}"
        f'<td><img id="{run_id}-overhead" class="frame-img" src="" alt="Overhead"/></td>'
        f"</tr></tbody>"
        f"</table>"
        f'<div class="slider-row">'
        f'<button onclick="rc_{js_id}_change(-1)">&#9664;</button>'
        f'<input type="range" id="{run_id}-slider" min="0" max="{max_idx}" value="0"'
        f' oninput="rc_{js_id}_set(parseInt(this.value))">'
        f'<button onclick="rc_{js_id}_change(1)">&#9654;</button>'
        f'<span id="{run_id}-step-label">Step — / {max_idx}</span>'
        f"</div>"
        f'<div class="decision-panel">'
        f"<h3>Latest Agent Decisions</h3>"
        f'<div id="{run_id}-decision-cards" class="decision-cards">{decision_cards_html}</div>'
        f"</div>"
        f"</div>"
        f"<script>"
        f"(function(){{"
        f"var FRAMES={frames_json};"
        f'var rid="{_html.escape(run_id, quote=True)}";'
        f"var cur=0;"
        f"function esc(s){{return String(s||'').replace(/&/g,'&amp;')"
        f".replace(/</g,'&lt;').replace(/>/g,'&gt;')"
        f".replace(/\"/g,'&quot;').replace(/'/g,'&#39;');}}"
        f"function decisionCardHtml(d){{"
        f"var agentId = Number(d.agent_id || 0);"
        f"var stepLabel = d.step === undefined ? 'No decision recorded yet.'"
        f" : (d.is_current ? 'Acting this step (step ' + d.step + ').'"
        f" : 'Latest decision from step ' + d.step + '.');"
        f"var chosenAction = d.executed_action || d.action || '—';"
        f"var rawLine = (d.raw_action && d.raw_action !== chosenAction)"
        f" ? '<p><strong>Model action:</strong> ' + esc(d.raw_action) + '</p>' : '';"
        f"var overrideLine = d.override_reason"
        f" ? '<p><strong>Override:</strong> ' + esc(d.override_reason) + '</p>' : '';"
        f"var reasoning = d.reasoning ? esc(d.reasoning) : 'No reasoning recorded yet.';"
        f"var cardClass = 'decision-card' + (d.is_current ? ' decision-card-current' : '');"
        f"return '<article class=\"' + cardClass + '\">' +"
        f"  '<div class=\"decision-card-head\"><strong>Agent ' + agentId + "
        f"  '</strong><span>' + esc(stepLabel) + '</span></div>' +"
        f"  '<p><strong>Chosen action:</strong> ' + esc(chosenAction) + '</p>' +"
        f"  rawLine + overrideLine +"
        f"  '<p class=\"decision-reasoning\"><strong>Reasoning:</strong> ' + reasoning + '</p>' +"
        f"  '</article>';"
        f"}}"
        f"function upd(idx){{"
        f"if(!FRAMES.length)return;"
        f"idx=Math.max(0,Math.min(FRAMES.length-1,idx));"
        f"cur=idx;"
        f"var f=FRAMES[idx];"
        f"{agent_init_js};"
        f'document.getElementById(rid+"-overhead").src=f.overhead_img||"";'
        f'document.getElementById(rid+"-slider").value=idx;'
        f'document.getElementById(rid+"-step-label").textContent='
        f'"Step "+f.step+" / {max_idx}";'
        f'document.getElementById(rid+"-decision-cards").innerHTML=(f.decisions||[]).map(decisionCardHtml).join("");'
        f"}}"
        f"window.rc_{js_id}_set=function(v){{upd(v);}};  "
        f"window.rc_{js_id}_change=function(d){{upd(cur+d);}};  "
        f"if(FRAMES.length)upd(0);"
        f"}})();"
        f"</script>"
    )

    metrics = _extract_metrics(steps_data, agent_count)
    svg_chart = _build_svg_chart(metrics)

    vlm_items: list[str] = []
    for rec in steps_data:
        step = rec.get("step", "?")
        agent_id = rec.get("agent_id", "?")
        vlm_resp = rec.get("vlm_response", {})
        action = _html.escape(str(vlm_resp.get("action", "?")))
        reasoning = _html.escape(str(vlm_resp.get("reasoning", "")))
        prompt_json = _html.escape(json.dumps(rec.get("vlm_prompt_state", {}), indent=2))
        vlm_items.append(
            f"<details>"
            f"<summary>Step {step} \u2014 agent {agent_id} \u2014 {action}</summary>"
            f'<div class="vlm-entry">'
            f"<p><strong>Reasoning:</strong> {reasoning}</p>"
            f"<details><summary>Prompt state</summary>"
            f"<pre>{prompt_json}</pre></details>"
            f"</div></details>"
        )
    vlm_log_html = "\n".join(vlm_items) if vlm_items else "<p>No VLM data recorded.</p>"

    return (
        f'<div class="run-section" id="{_html.escape(run_id)}">'
        f"{summary_bar}"
        f"{viewer_html}"
        f'<div class="chart-section"><h3>Metrics Timeline</h3>{svg_chart}</div>'
        f'<div class="vlm-log-section"><h3>VLM Reasoning Log</h3>{vlm_log_html}</div>'
        f"</div>"
    )


def _render_decision_card(decision: dict[str, Any]) -> str:
    """Render one agent's latest decision card for the viewer panel."""
    agent_id = int(decision.get("agent_id", 0))
    step = decision.get("step")
    is_current = bool(decision.get("is_current"))
    if step is None:
        status = "No decision recorded yet."
    elif is_current:
        status = f"Acting this step (step {step})."
    else:
        status = f"Latest decision from step {step}."

    chosen_action = str(decision.get("executed_action") or decision.get("action") or "—")
    raw_action = str(decision.get("raw_action") or "")
    override_reason = str(decision.get("override_reason") or "")
    reasoning = str(decision.get("reasoning") or "No reasoning recorded yet.")
    classes = "decision-card decision-card-current" if is_current else "decision-card"

    raw_line = ""
    if raw_action and raw_action != chosen_action:
        raw_line = f"<p><strong>Model action:</strong> {_html.escape(raw_action)}</p>"

    override_line = ""
    if override_reason:
        override_line = f"<p><strong>Override:</strong> {_html.escape(override_reason)}</p>"

    return (
        f'<article class="{classes}">'
        f'<div class="decision-card-head"><strong>Agent {agent_id}</strong>'
        f"<span>{_html.escape(status)}</span></div>"
        f"<p><strong>Chosen action:</strong> {_html.escape(chosen_action)}</p>"
        f"{raw_line}"
        f"{override_line}"
        f'<p class="decision-reasoning"><strong>Reasoning:</strong> {_html.escape(reasoning)}</p>'
        f"</article>"
    )


def _wrap_html(body: str, title: str = "RoboClaws Report") -> str:
    """Wrap *body* in a complete self-contained HTML document."""
    safe_title = _html.escape(title)
    # CSS is placed inside a Python string; line lengths inside the literal are unchecked.
    css = (
        "* { box-sizing: border-box; }"
        "body { font-family: system-ui, sans-serif; margin: 0; padding: 1rem;"
        "       background: #f5f6fa; color: #1a1a2e; }"
        "h2 { margin: 0.5rem 0 1rem; font-size: 1.2rem; }"
        "h3 { margin: 0.75rem 0 0.4rem; color: #444; font-size: 1rem; }"
        ".run-section { margin-bottom: 2rem; }"
        ".summary-bar { display: flex; flex-wrap: wrap; gap: 0.4rem; background: #fff;"
        "  border-radius: 8px; padding: 0.75rem 1rem; box-shadow: 0 1px 4px #0001;"
        "  margin-bottom: 1rem; }"
        ".badge { background: #eef2ff; border-radius: 4px;"
        "  padding: 0.2rem 0.6rem; font-size: 0.82rem; }"
        ".viewer { background: #fff; border-radius: 8px; padding: 1rem;"
        "  box-shadow: 0 1px 4px #0001; margin-bottom: 1rem; overflow-x: auto; }"
        ".frame-table { border-collapse: collapse; margin-bottom: 0.75rem; }"
        ".frame-table th { background: #e8edf8; padding: 4px 10px; font-size: 0.78rem; }"
        ".frame-table td { padding: 4px; }"
        ".frame-img { display: block; max-width: 200px; max-height: 160px; background: #ddd;"
        "  border: 1px solid #bbb; border-radius: 3px; }"
        ".slider-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }"
        ".slider-row input[type=range] { flex: 1; min-width: 200px; }"
        ".slider-row button { padding: 0.2rem 0.7rem; cursor: pointer;"
        "  border: 1px solid #bbb; border-radius: 4px; background: #fff; }"
        ".slider-row button:hover { background: #e8edf8; }"
        ".decision-panel { margin-top: 1rem; }"
        ".decision-cards { display: grid;"
        "  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));"
        "  gap: 0.75rem; }"
        ".decision-card { border: 1px solid #d8dfeb; border-radius: 8px; padding: 0.75rem;"
        "  background: #f8faff; min-height: 150px; }"
        ".decision-card-current { border-color: #6b8cff; box-shadow: inset 0 0 0 1px #c6d5ff; }"
        ".decision-card-head { display: flex; justify-content: space-between; gap: 0.75rem;"
        "  align-items: baseline; margin-bottom: 0.5rem; }"
        ".decision-card-head span { color: #5f6c85; font-size: 0.78rem; text-align: right; }"
        ".decision-card p { margin: 0.35rem 0; font-size: 0.84rem; }"
        ".decision-reasoning { line-height: 1.45; }"
        ".chart-section { background: #fff; border-radius: 8px; padding: 1rem;"
        "  box-shadow: 0 1px 4px #0001; margin-bottom: 1rem; }"
        ".vlm-log-section { background: #fff; border-radius: 8px; padding: 1rem;"
        "  box-shadow: 0 1px 4px #0001; }"
        "details { border-bottom: 1px solid #eee; }"
        "summary { cursor: pointer; padding: 0.35rem 0.25rem;"
        "  font-size: 0.88rem; user-select: none; }"
        "summary:hover { background: #f0f4ff; }"
        ".vlm-entry { padding: 0.5rem 1rem; font-size: 0.84rem; }"
        ".vlm-entry p { margin: 0.25rem 0; }"
        ".vlm-entry pre { background: #f6f8fb; border-radius: 4px; padding: 0.6rem;"
        "  overflow-x: auto; font-size: 0.78rem; max-height: 180px;"
        "  border: 1px solid #e0e4ec; }"
        ".compare-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }"
        ".compare-col { min-width: 0; }"
        "@media (max-width: 900px) { .compare-layout { grid-template-columns: 1fr; } }"
    )
    return (
        f"<!DOCTYPE html>\n"
        f'<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{safe_title}</title>\n"
        f"<style>{css}</style>\n"
        f"</head>\n<body>\n"
        f"{body}\n"
        f"</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# Metrics extraction and charting
# ---------------------------------------------------------------------------


def _extract_metrics(
    steps_data: list[dict[str, Any]],
    agent_count: int,
) -> dict[str, list[float]]:
    """Extract per-step numeric KPIs from game_state for charting.

    Handles territory and coverage game states, plus generic numeric fields.

    Returns:
        Mapping of series name to list of float values (one per recorded step).
    """
    if not steps_data:
        return {}

    sample_gs: dict[str, Any] = steps_data[0].get("game_state", {})
    game = sample_gs.get("game", "")
    metrics: dict[str, list[float]] = {}

    for rec in steps_data:
        gs = rec.get("game_state", {})

        if game == "territory":
            agents = gs.get("agents", {})
            for aid in range(agent_count):
                key = f"agent_{aid}_cells"
                info = agents.get(str(aid), agents.get(aid, {}))
                metrics.setdefault(key, []).append(float(info.get("cells_claimed", 0)))
            metrics.setdefault("total_claimed", []).append(float(gs.get("total_claimed", 0)))

        elif game == "coverage":
            agents = gs.get("agents", {})
            for aid in range(agent_count):
                key = f"agent_{aid}_cells"
                info = agents.get(str(aid), agents.get(aid, {}))
                metrics.setdefault(key, []).append(float(info.get("cells_covered", 0)))
            metrics.setdefault("coverage_pct", []).append(float(gs.get("coverage_pct", 0)))
            metrics.setdefault("total_covered", []).append(float(gs.get("total_covered", 0)))

        else:
            _SKIP = {"step", "remaining_steps", "current_agent"}
            for k, v in gs.items():
                if k in _SKIP:
                    continue
                if isinstance(v, (int, float)):
                    metrics.setdefault(str(k), []).append(float(v))

    return metrics


def _build_svg_chart(
    metrics: dict[str, list[float]],
    width: int = 700,
    height: int = 200,
) -> str:
    """Build a self-contained SVG line chart for the given metrics series.

    Returns an SVG string, or a plain ``<p>`` if there is nothing to chart.
    """
    series = {k: v for k, v in metrics.items() if len(v) >= 2}
    if not series:
        return "<p><em>No metrics data available.</em></p>"

    all_vals = [v for vals in series.values() for v in vals]
    lo = min(all_vals)
    hi = max(all_vals)
    if hi == lo:
        hi = lo + 1.0

    pad_l, pad_r, pad_t, pad_b = 45, 10, 10, 30
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b

    colors = ["#4285f4", "#ea4335", "#34a853", "#fbbc05", "#a142f4", "#00bcd4", "#ff6d00"]
    lines: list[str] = []
    legend: list[str] = []

    for idx, (name, vals) in enumerate(series.items()):
        color = colors[idx % len(colors)]
        n = len(vals)
        pts = " ".join(
            f"{pad_l + (j / (n - 1)) * chart_w:.1f},"
            f"{pad_t + chart_h - ((v - lo) / (hi - lo)) * chart_h:.1f}"
            for j, v in enumerate(vals)
        )
        lines.append(
            f'<polyline points="{pts}" fill="none"'
            f' stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
        )
        lx = 4 + idx * 130
        legend.append(
            f'<rect x="{lx}" y="{height + 2}" width="11" height="11" fill="{color}"/>'
            f'<text x="{lx + 14}" y="{height + 12}" font-size="10" fill="#333">'
            f"{_html.escape(name)}</text>"
        )

    y0 = f'<text x="{pad_l - 4}" y="{pad_t + 5}" text-anchor="end" font-size="10"'
    y0 += f' fill="#666">{hi:.0f}</text>'
    y1 = f'<text x="{pad_l - 4}" y="{pad_t + chart_h}" text-anchor="end" font-size="10"'
    y1 += f' fill="#666">{lo:.0f}</text>'
    n_max = max(len(v) for v in series.values())
    x0 = (
        f'<text x="{pad_l}" y="{pad_t + chart_h + 14}" text-anchor="middle"'
        f' font-size="10" fill="#666">0</text>'
    )
    x1 = (
        f'<text x="{pad_l + chart_w}" y="{pad_t + chart_h + 14}" text-anchor="middle"'
        f' font-size="10" fill="#666">{n_max - 1}</text>'
    )

    total_h = height + 20
    bg = (
        f'<rect x="{pad_l}" y="{pad_t}" width="{chart_w}" height="{chart_h}"'
        f' fill="#fafbfc" stroke="#dde1e7" stroke-width="1"/>'
    )
    return (
        f'<svg viewBox="0 0 {width} {total_h}" xmlns="http://www.w3.org/2000/svg"'
        f' style="width:100%;max-width:{width}px;display:block">'
        + bg
        + y0
        + y1
        + x0
        + x1
        + "".join(lines)
        + "".join(legend)
        + "</svg>"
    )


# ---------------------------------------------------------------------------
# Image helper
# ---------------------------------------------------------------------------


def _img_to_b64(path: Path) -> str:
    """Return a base64 PNG data URI for *path*, or empty string if missing."""
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m roboclaws.core.reporter",
        description="Generate a self-contained HTML report from a RoboClaws replay directory.",
    )
    parser.add_argument("replay_dir", help="Replay directory (output of ReplayRecorder.save())")
    parser.add_argument("--open", dest="auto_open", action="store_true", help="Open in browser")
    parser.add_argument(
        "--compare",
        metavar="OTHER_DIR",
        help="Generate side-by-side A/B comparison with OTHER_DIR",
    )
    parser.add_argument("--output", metavar="PATH", help="Override output HTML file path")
    args = parser.parse_args(argv)

    if args.compare:
        out = compare(
            args.replay_dir,
            args.compare,
            output_path=args.output,
            auto_open=args.auto_open,
        )
    else:
        out = generate(args.replay_dir, output_path=args.output, auto_open=args.auto_open)

    print(f"Report written to: {out}")


if __name__ == "__main__":
    _main()
