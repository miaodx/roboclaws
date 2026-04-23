#!/usr/bin/env python3
"""Serve a small auto-refreshing HTML page showing the agent's latest view.

Chat MEDIA can only render one set of images per turn (Control UI quirk —
see the ``_maybe_write_labeled_snapshot`` hint in
``roboclaws/openclaw/mcp_server.py``). For long-running sessions where you
want to watch the robot move frame-by-frame without asking it to pause
between steps, open this viewer in a separate browser tab instead.

The viewer polls three stable filenames in the latest run's snapshots
dir — ``latest.fpv.png``, ``latest.map.png``, ``latest.chase.png`` —
which every ``roboclaws__observe`` call rewrites atomically (labeled or not).

Usage:

    python scripts/view-snapshots.py           # auto-pick newest run
    python scripts/view-snapshots.py --run-dir output/openclaw-interactive/<ts>
    python scripts/view-snapshots.py --port 8787
"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import sys
from pathlib import Path
from urllib.parse import urlparse

_DEFAULT_PORT = 8787
_POLL_MS = 500
_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_RUNS_DIR = _ROOT / "output" / "openclaw-interactive"

_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Roboclaws — live snapshot view</title>
<style>
  :root { color-scheme: dark light; }
  body { margin: 0; font-family: system-ui, sans-serif; background: #111; color: #eee; }
  header { padding: 0.5em 1em; background: #222; display: flex; gap: 1em; align-items: baseline; }
  header h1 { margin: 0; font-size: 1rem; font-weight: 500; }
  header .meta { font-size: 0.8rem; opacity: 0.6; margin-left: auto; }
  main { display: grid; grid-template-columns: 2fr 1fr; gap: 0.5em; padding: 0.5em; }
  .panel { background: #1a1a1a; border-radius: 4px; overflow: hidden; display: flex;
           flex-direction: column; }
  .panel h2 { margin: 0; padding: 0.4em 0.6em; font-size: 0.75rem; font-weight: 500;
              background: #222; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.7; }
  .panel img { width: 100%; height: auto; display: block; background: #000; }
  .fpv  { grid-row: span 2; }
  .stale { opacity: 0.85; }
</style>
</head>
<body>
<header>
  <h1>Roboclaws live view</h1>
  <span class="meta" id="meta">loading…</span>
</header>
<main>
  <section class="panel fpv"><h2>FPV</h2><img id="fpv" alt="fpv"></section>
  <section class="panel"><h2>Overhead map</h2><img id="map" alt="map"></section>
  <section class="panel"><h2>Chase cam</h2><img id="chase" alt="chase"></section>
</main>
<script>
  const POLL_MS = __POLL_MS__;
  const kinds = ["fpv", "map", "chase"];
  let lastMtimes = {};
  let lastChange = Date.now();
  function tick() {
    fetch("/status").then(r => r.json()).then(status => {
      const meta = document.getElementById("meta");
      if (!status.ok) {
        meta.textContent = "waiting for first snapshot…";
        return;
      }
      let changed = false;
      for (const k of kinds) {
        const t = status.mtimes[k];
        if (!t) continue;
        if (lastMtimes[k] !== t) {
          lastMtimes[k] = t;
          changed = true;
          document.getElementById(k).src = `/img/${k}?t=${t}`;
          document.getElementById(k).classList.remove("stale");
        }
      }
      if (changed) lastChange = Date.now();
      const age = Math.round((Date.now() - lastChange) / 1000);
      meta.textContent = `${status.run}  ·  last update: ${age}s ago`;
      if (age > 20) {
        for (const k of kinds) document.getElementById(k).classList.add("stale");
      }
    }).catch(err => {
      document.getElementById("meta").textContent = "server unreachable";
    });
  }
  setInterval(tick, POLL_MS);
  tick();
</script>
</body>
</html>
""".replace("__POLL_MS__", str(_POLL_MS))


def _resolve_run_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    if not _DEFAULT_RUNS_DIR.exists():
        raise RuntimeError(f"no runs dir at {_DEFAULT_RUNS_DIR}; pass --run-dir explicitly")
    runs = sorted(
        (p for p in _DEFAULT_RUNS_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not runs:
        raise RuntimeError(f"no run subdirs under {_DEFAULT_RUNS_DIR}")
    return runs[0].resolve()


def _snapshots_dir(run_dir: Path, agent_id: int) -> Path:
    return run_dir / "snapshots" / f"agent-{agent_id}"


def _make_handler(run_dir: Path, agent_id: int):
    snap_dir = _snapshots_dir(run_dir, agent_id)

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:  # quieter
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/" or path == "/index.html":
                self._send(200, "text/html; charset=utf-8", _HTML.encode("utf-8"))
                return
            if path == "/status":
                self._send_json(self._status())
                return
            if path.startswith("/img/"):
                kind = path.removeprefix("/img/").split("?", 1)[0]
                if kind in {"fpv", "map", "chase"}:
                    self._send_png(snap_dir / f"latest.{kind}.png")
                    return
            self._send(404, "text/plain", b"not found\n")

        def _status(self) -> dict:
            mtimes: dict[str, float] = {}
            for kind in ("fpv", "map", "chase"):
                p = snap_dir / f"latest.{kind}.png"
                if p.exists():
                    mtimes[kind] = p.stat().st_mtime
            return {
                "ok": bool(mtimes),
                "run": run_dir.name,
                "agent": f"agent-{agent_id}",
                "mtimes": mtimes,
            }

        def _send_json(self, payload: dict) -> None:
            import json

            body = json.dumps(payload).encode("utf-8")
            self._send(200, "application/json", body)

        def _send_png(self, path: Path) -> None:
            try:
                data = path.read_bytes()
            except FileNotFoundError:
                self._send(404, "text/plain", b"no snapshot yet\n")
                return
            self._send(200, "image/png", data, cache=False)

        def _send(self, code: int, ctype: str, body: bytes, *, cache: bool = False) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            if not cache:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Live viewer for roboclaws__observe latest.*.png output."
    )
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--agent-id", type=int, default=0)
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    try:
        run_dir = _resolve_run_dir(args.run_dir)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    snap_dir = _snapshots_dir(run_dir, args.agent_id)
    snap_dir.mkdir(parents=True, exist_ok=True)
    handler = _make_handler(run_dir, args.agent_id)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        print(f"snapshots dir : {snap_dir}")
        print(f"open          : http://{args.host}:{args.port}/")
        print("Ctrl-C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
