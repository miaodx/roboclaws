"""Write the landing ``index.html`` for the RoboClaws Pages site.

Used both by the local demo generator and by the CI ``publish-pages`` job so
the two landing pages stay in sync.

Usage::

    # Mock-only demo (no real AI2-THOR section)
    python scripts/reports/write_pages_index.py output/demo

    # Full site including real-model smoke output at ./smoke/territory/
    # and ./smoke/coverage/
    python scripts/reports/write_pages_index.py site --include-smoke

    # Include all available OpenClaw tiles (whichever subdirs exist under
    # site/openclaw/ are auto-detected when --include-openclaw is passed)
    python scripts/reports/write_pages_index.py site --include-smoke --include-openclaw

    # Include opt-in Molmo live cleanup tiles from
    # site/molmo/live/live-report-manifest.json
    python scripts/reports/write_pages_index.py site --include-smoke --include-molmo-live
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

_SMOKE_ITEMS = (
    '  <li><a href="smoke/territory/report.html">'
    "&#x25B6; Territory Control &mdash; Real AI2-THOR + Kimi</a>"
    '<span class="tag">real model</span>'
    '      <div class="desc">Adversarial 2-agent territory game in a real indoor scene, '
    "driven by the Kimi VLM via the <code>real-model-smoke</code> CI job.</div></li>\n"
    '  <li><a href="smoke/coverage/report.html">'
    "&#x25B6; Cooperative Coverage &mdash; Real AI2-THOR + Kimi</a>"
    '<span class="tag">real model</span>'
    '      <div class="desc">Cooperative 2-agent coverage game in a real indoor scene, '
    "driven by the Kimi VLM via the <code>real-model-smoke</code> CI job.</div></li>"
)

_OPENCLAW_ITEM_DEMO = (
    '  <li><a href="openclaw/demo/report.html">'
    "&#x25B6; Navigation Demo &mdash; OpenClaw + Kimi</a>"
    '<span class="tag">openclaw</span>'
    '      <div class="desc">Multi-agent AI2-THOR navigation routed through '
    "a local OpenClaw Gateway (Phase 2.1 transport smoke).</div></li>"
)

_OPENCLAW_ITEM_TERRITORY = (
    '  <li><a href="openclaw/territory/report.html">'
    "&#x25B6; Territory Control &mdash; OpenClaw + Kimi</a>"
    '<span class="tag">openclaw</span>'
    '      <div class="desc">Adversarial 2-agent territory game over OpenClaw with '
    "per-agent SOULs (aggressive=red / defensive=blue trails). "
    "Phase 2.2 long-running Gateway demo.</div></li>"
)

_OPENCLAW_ITEM_COVERAGE = (
    '  <li><a href="openclaw/coverage/report.html">'
    "&#x25B6; Cooperative Coverage &mdash; OpenClaw + Kimi</a>"
    '<span class="tag">openclaw</span>'
    '      <div class="desc">Cooperative 2-agent coverage game over OpenClaw with '
    "cooperative SOUL personas (cooperative=green trails). "
    "Phase 2.2 long-running Gateway demo.</div></li>"
)

# Legacy alias: the single-item _OPENCLAW_ITEMS string that older callers may
# reference. Points at the demo tile for back-compat.
_OPENCLAW_ITEMS = _OPENCLAW_ITEM_DEMO

_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<title>RoboClaws &mdash; Demo Reports</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 3rem auto;
        padding: 0 1rem; color: #1a1a2e; background: #f5f6fa; }}
 h1 {{ margin-bottom: 0.25rem; }}
 h2 {{ margin-top: 2rem; font-size: 1.05rem; color: #444; }}
 .sub {{ color: #666; margin-top: 0; }}
 ul {{ list-style: none; padding: 0; }}
 li {{ background: #fff; margin: 0.5rem 0; padding: 1rem 1.2rem; border-radius: 8px;
      box-shadow: 0 1px 3px #0001; }}
 a {{ color: #2952cc; text-decoration: none; font-weight: 600; }}
 a:hover {{ text-decoration: underline; }}
 .desc {{ color: #555; font-size: 0.9rem; margin-top: 0.25rem; }}
 .tag {{ display: inline-block; margin-left: 0.5rem; font-size: 0.72rem;
        padding: 1px 7px; border-radius: 10px; background: #ffeec2; color: #8a5a00;
        vertical-align: middle; font-weight: 600; }}
</style></head><body>
<h1>RoboClaws &mdash; Demo Reports</h1>
<p class="sub">Regenerated on every push to <code>main</code> by GitHub Actions.</p>

<h2>Mock-engine demos (every push)</h2>
<ul>
  <li><a href="territory/report.html">&#x25B6; Territory Control</a>
      <div class="desc">2-3 VLM agents compete to claim grid cells.</div></li>
  <li><a href="coverage/report.html">&#x25B6; Cooperative Coverage</a>
      <div class="desc">2-3 VLM agents cooperate to cover a room.</div></li>
  <li><a href="report_compare.html">&#x25B6; A/B Comparison</a>
      <div class="desc">Two runs side-by-side.</div></li>
</ul>
{smoke_section}{openclaw_section}
<p><a href="https://github.com/MiaoDX/roboclaws">&larr; Back to the repository</a></p>
</body></html>
"""


def write_index(
    site_dir: Path,
    include_smoke: bool = False,
    include_openclaw: bool = False,
    include_molmo_live: bool = False,
) -> Path:
    """Write ``index.html`` into *site_dir* and return its path.

    When ``include_openclaw`` is True, the OpenClaw section is built by
    auto-detecting which tiles are present under ``site_dir/openclaw/``
    (demo, territory, coverage). Missing tiles are silently omitted so a
    partial CI run still produces a valid page.
    """
    smoke_section = (
        "<h2>Real AI2-THOR + Kimi (push to <code>main</code> only)</h2>\n<ul>\n"
        f"{_SMOKE_ITEMS}\n</ul>"
        if include_smoke
        else ""
    )

    openclaw_items: list[str] = []
    if include_openclaw:
        # Enumerate the 4 cases: none / demo-only / territory-only / coverage-only /
        # any combination — missing artifact dir → omit tile (matches CI best-effort pattern).
        openclaw_dir = site_dir / "openclaw"
        if (openclaw_dir / "demo").is_dir():
            openclaw_items.append(_OPENCLAW_ITEM_DEMO)
        if (openclaw_dir / "territory").is_dir():
            openclaw_items.append(_OPENCLAW_ITEM_TERRITORY)
        if (openclaw_dir / "coverage").is_dir():
            openclaw_items.append(_OPENCLAW_ITEM_COVERAGE)

    openclaw_section = (
        "\n<h2>OpenClaw Gateway (Phase 2, push to <code>main</code> only)</h2>\n<ul>\n"
        + "\n".join(openclaw_items)
        + "\n</ul>"
        if openclaw_items
        else ""
    )

    molmo_live_section = _molmo_live_section(site_dir) if include_molmo_live else ""

    html = _TEMPLATE.format(
        smoke_section=smoke_section,
        openclaw_section=openclaw_section + molmo_live_section,
    )
    out = site_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("site_dir", type=Path, help="Directory to write index.html into")
    p.add_argument(
        "--include-smoke",
        action="store_true",
        help="Include links to smoke/territory/report.html and smoke/coverage/report.html",
    )
    p.add_argument(
        "--include-openclaw",
        action="store_true",
        help=(
            "Include OpenClaw tiles (auto-detected from "
            "site_dir/openclaw/{demo,territory,coverage}/)"
        ),
    )
    p.add_argument(
        "--include-molmo-live",
        action="store_true",
        help="Include Molmo live cleanup tiles from site_dir/molmo/live/live-report-manifest.json",
    )
    args = p.parse_args(argv)
    args.site_dir.mkdir(parents=True, exist_ok=True)
    out = write_index(
        args.site_dir,
        include_smoke=args.include_smoke,
        include_openclaw=args.include_openclaw,
        include_molmo_live=args.include_molmo_live,
    )
    print(f"Wrote {out}")


def _molmo_live_section(site_dir: Path) -> str:
    manifest_path = site_dir / "molmo" / "live" / "live-report-manifest.json"
    if not manifest_path.is_file():
        return ""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries") or []
    if not entries:
        return ""

    items = []
    for entry in entries:
        label = html.escape(str(entry.get("label") or entry.get("entry") or "Molmo live run"))
        model = html.escape(str(entry.get("model") or "unknown model"))
        provider = html.escape(str(entry.get("provider_profile") or "unknown provider"))
        status = html.escape(str(entry.get("status") or "unknown"))
        profile = html.escape(str(entry.get("profile") or "unknown profile"))
        reason = html.escape(str(entry.get("reason") or ""))
        report_path = str(entry.get("report_path") or "")
        diagnostic_path = str(entry.get("diagnostic_path") or "")
        if status == "success" and report_path:
            href = html.escape("molmo/live/" + report_path, quote=True)
            title = f'<a href="{href}">&#x25B6; {label}</a>'
        elif diagnostic_path:
            href = html.escape("molmo/live/" + diagnostic_path, quote=True)
            title = f'<a href="{href}">{label} diagnostics</a>'
        else:
            title = f"<span>{label}</span>"
        desc = (
            f'      <div class="desc">Claude Code live cleanup via '
            f"<code>{provider}</code> / <code>{model}</code> using "
            f"<code>{profile}</code>. Status: "
            f"<code>{status}</code>"
        )
        if reason:
            desc += f" ({reason})"
        desc += ".</div>"
        items.append(f'  <li>{title}<span class="tag">molmo live</span>\n{desc}</li>')

    return (
        "\n<h2>MolmoSpaces Live Cleanup (main-only / opt-in CI)</h2>\n"
        '<p class="sub"><a href="molmo/live/">Open the dedicated MolmoSpaces live page</a></p>\n'
        "<ul>\n" + "\n".join(items) + "\n</ul>"
    )


if __name__ == "__main__":
    main()
