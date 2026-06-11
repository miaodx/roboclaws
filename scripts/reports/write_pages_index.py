"""Write the landing ``index.html`` for the RoboClaws Pages site.

Used by the CI ``publish-pages`` job after assembling household report
artifacts. The public site currently advertises the MolmoSpaces live cleanup
index when ``site/molmo/live/live-report-manifest.json`` is present.

Usage::

    python scripts/reports/write_pages_index.py site --include-molmo-live
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

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
{molmo_live_section}
<p><a href="https://github.com/MiaoDX/roboclaws">&larr; Back to the repository</a></p>
</body></html>
"""


def write_index(
    site_dir: Path,
    include_molmo_live: bool = False,
) -> Path:
    """Write ``index.html`` into *site_dir* and return its path.

    ``include_molmo_live`` reads the live cleanup manifest under
    ``site_dir/molmo/live``. When no manifest exists, the page still renders
    with a short placeholder section.
    """
    molmo_live_section = _molmo_live_section(site_dir) if include_molmo_live else ""
    if not molmo_live_section:
        molmo_live_section = (
            "<h2>Household Reports</h2>\n"
            '<p class="sub">No published household cleanup reports are available yet.</p>\n'
        )

    html = _TEMPLATE.format(
        molmo_live_section=molmo_live_section,
    )
    site_dir.mkdir(parents=True, exist_ok=True)
    out = site_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("site_dir", type=Path, help="Directory to write index.html into")
    p.add_argument(
        "--include-molmo-live",
        action="store_true",
        help="Include Molmo live cleanup tiles from site_dir/molmo/live/live-report-manifest.json",
    )
    args = p.parse_args(argv)
    args.site_dir.mkdir(parents=True, exist_ok=True)
    out = write_index(
        args.site_dir,
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
