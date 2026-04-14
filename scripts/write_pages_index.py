"""Write the landing ``index.html`` for the RoboClaws Pages site.

Used both by the local demo generator and by the CI ``publish-pages`` job so
the two landing pages stay in sync.

Usage::

    # Mock-only demo (no real AI2-THOR section)
    python scripts/write_pages_index.py output/demo

    # Full site including real-model smoke output at ./smoke/territory/
    # and ./smoke/coverage/
    python scripts/write_pages_index.py site --include-smoke

    # Also include OpenClaw Gateway reports at ./openclaw/territory/ and
    # ./openclaw/coverage/
    python scripts/write_pages_index.py site --include-smoke --include-openclaw
"""

from __future__ import annotations

import argparse
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

_OPENCLAW_ITEMS = (
    '  <li><a href="openclaw/territory/report.html">'
    "&#x25B6; Territory Control &mdash; OpenClaw + Kimi</a>"
    '<span class="tag">openclaw</span>'
    '      <div class="desc">Same adversarial territory game, but routed through an '
    "ephemeral OpenClaw Gateway so each agent has a persistent SOUL + MEMORY "
    "(<code>openclaw-smoke</code> CI job).</div></li>\n"
    '  <li><a href="openclaw/coverage/report.html">'
    "&#x25B6; Cooperative Coverage &mdash; OpenClaw + Kimi</a>"
    '<span class="tag">openclaw</span>'
    '      <div class="desc">Cooperative coverage game via the OpenClaw Gateway '
    "(<code>openclaw-smoke</code> CI job).</div></li>"
)

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
) -> Path:
    """Write ``index.html`` into *site_dir* and return its path."""
    smoke_section = (
        "<h2>Real AI2-THOR + Kimi (push to <code>main</code> only)</h2>\n<ul>\n"
        f"{_SMOKE_ITEMS}\n</ul>"
        if include_smoke
        else ""
    )
    openclaw_section = (
        "\n<h2>OpenClaw Gateway (Phase 2, push to <code>main</code> only)</h2>\n<ul>\n"
        f"{_OPENCLAW_ITEMS}\n</ul>"
        if include_openclaw
        else ""
    )
    html = _TEMPLATE.format(
        smoke_section=smoke_section,
        openclaw_section=openclaw_section,
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
        help="Include links to openclaw/territory/report.html and openclaw/coverage/report.html",
    )
    args = p.parse_args(argv)
    args.site_dir.mkdir(parents=True, exist_ok=True)
    out = write_index(
        args.site_dir,
        include_smoke=args.include_smoke,
        include_openclaw=args.include_openclaw,
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
