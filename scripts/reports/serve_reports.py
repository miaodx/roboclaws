#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import mimetypes
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse


class ReportRequestHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: object,
        root: Path,
        title: str,
        max_reports: int,
        **kwargs: object,
    ) -> None:
        self.report_root = root.resolve()
        self.index_title = title
        self.max_reports = max_reports
        super().__init__(*args, directory=str(self.report_root), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"", "/", "/index.html"}:
            return self._index()
        return super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"", "/", "/index.html"}:
            body = self._index_html().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return
        return super().do_HEAD()

    def _index(self) -> None:
        body = self._index_html().encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _index_html(self) -> str:
        reports = _find_reports(self.report_root, max_reports=self.max_reports)
        cards = "\n".join(_report_card(self.report_root, item) for item in reports)
        empty = (
            '<p class="empty">No report.html files found under this root.</p>'
            if not reports
            else ""
        )
        root_label = html.escape(str(self.report_root))
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(self.index_title)}</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    body {{
      margin: 0;
      background: Canvas;
      color: CanvasText;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    .root {{
      margin: 0 0 24px;
      color: color-mix(in srgb, CanvasText 70%, transparent);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    .list {{
      display: grid;
      gap: 12px;
    }}
    .card {{
      border: 1px solid color-mix(in srgb, CanvasText 18%, transparent);
      border-radius: 8px;
      padding: 14px 16px;
      background: color-mix(in srgb, Canvas 94%, CanvasText 6%);
    }}
    .card a {{
      color: LinkText;
      font-weight: 650;
      text-decoration: none;
      overflow-wrap: anywhere;
    }}
    .card a:hover {{
      text-decoration: underline;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    .badge {{
      border: 1px solid color-mix(in srgb, CanvasText 18%, transparent);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      color: color-mix(in srgb, CanvasText 78%, transparent);
      background: Canvas;
      white-space: nowrap;
    }}
    .empty {{
      padding: 16px;
      border: 1px dashed color-mix(in srgb, CanvasText 30%, transparent);
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(self.index_title)}</h1>
    <p class="root">{root_label}</p>
    {empty}
    <section class="list">
      {cards}
    </section>
  </main>
</body>
</html>
"""


def _find_reports(root: Path, *, max_reports: int) -> list[Path]:
    reports = [path for path in root.rglob("report.html") if path.is_file()]
    reports.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if max_reports > 0:
        return reports[:max_reports]
    return reports


def _report_card(root: Path, report_path: Path) -> str:
    rel = report_path.relative_to(root)
    href = quote(rel.as_posix(), safe="/")
    summary = _run_summary(report_path.parent / "run_result.json")
    badges = [_badge("updated", _mtime_label(report_path))]
    badges.extend(_summary_badges(summary))
    meta = "".join(badges)
    return (
        '<article class="card">'
        f'<a href="{href}">{html.escape(rel.as_posix())}</a>'
        f'<div class="meta">{meta}</div>'
        "</article>"
    )


def _run_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _summary_badges(summary: dict[str, Any]) -> list[str]:
    if not summary:
        return []
    score = summary.get("score") if isinstance(summary.get("score"), dict) else {}
    semantic = (
        score.get("semantic_acceptability")
        if isinstance(score.get("semantic_acceptability"), dict)
        else {}
    )
    badges = [
        _badge("status", summary.get("cleanup_status") or summary.get("completion_status")),
        _badge("policy", summary.get("policy")),
        _badge("backend", summary.get("backend")),
        _badge("mode", summary.get("perception_mode")),
    ]
    restored = _count_pair(score.get("restored_count"), score.get("total_targets"))
    if restored:
        badges.append(_badge("restored", restored))
    accepted = _count_pair(semantic.get("accepted_count"), semantic.get("total_targets"))
    if accepted:
        badges.append(_badge("semantic", accepted))
    if summary.get("sweep_coverage_rate") is not None:
        badges.append(_badge("sweep", summary.get("sweep_coverage_rate")))
    return [item for item in badges if item]


def _badge(label: str, value: object) -> str:
    if value is None or value == "":
        return ""
    return f'<span class="badge">{html.escape(label)}: {html.escape(str(value))}</span>'


def _count_pair(count: object, total: object) -> str:
    if count is None or total is None:
        return ""
    return f"{count}/{total}"


def _mtime_label(path: Path) -> str:
    return f"{path.stat().st_mtime_ns // 1_000_000_000}"


def run_server(root: Path, host: str, port: int, *, title: str, max_reports: int) -> None:
    mimetypes.add_type("application/json", ".json")
    handler = partial(ReportRequestHandler, root=root, title=title, max_reports=max_reports)
    server = ThreadingHTTPServer((host, port), handler)
    url_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    print(f"Serving Roboclaws reports from {root.resolve()}")
    print(f"Index: http://{url_host}:{port}/")
    if host in {"0.0.0.0", "::"}:
        print(f"Listening on all interfaces; remote URL: http://<server-ip>:{port}/")
    print(f"SSH tunnel example: ssh -N -L {port}:127.0.0.1:{port} <host>")
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve Roboclaws report artifacts.")
    parser.add_argument("root", nargs="?", type=Path, default=Path("output"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--title", default="Roboclaws Reports")
    parser.add_argument(
        "--max-reports",
        type=int,
        default=300,
        help="Maximum report links to show on the index page. Use 0 for no limit.",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"report root does not exist or is not a directory: {root}")
    run_server(root, args.host, args.port, title=args.title, max_reports=args.max_reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
