"""HTTP /reset endpoint for the appliance.

When the appliance container is fronted by nginx (Railway parity or
``make appliance-run-local``), nginx routes ``/reset`` to this loopback
listener. Hitting it atomically:

  1. Reloads the AI2-THOR scene back to its starting layout
  2. Wipes the per-agent snapshots dir so ``/views/`` goes blank

Both steps run under the MCP server's controller lock (see
:meth:`RoboclawsMCPServer.reset_world`) so reset cannot race an in-flight
observe/move.

The endpoint is intentionally **unauthenticated**, matching ``/views/``.
The parent ``/`` route (Gateway control UI) is already token-gated, so a
casual visitor can wipe demo state but cannot drive the robot.
"""

from __future__ import annotations

import html as _html
import http.server
import socketserver
import sys
import threading
from typing import TYPE_CHECKING
from urllib.parse import urlparse

_html_escape = _html.escape

if TYPE_CHECKING:
    from roboclaws.openclaw.mcp_server import RoboclawsMCPServer


_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 18790


# NB: these templates use ``str.replace`` (not ``str.format``) so the embedded
# CSS ``{...}`` blocks don't have to be escaped. Placeholders use ``__NAME__``.
_HTML_DONE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Roboclaws — reset</title>
<style>
  :root { color-scheme: dark light; }
  body { margin: 0; font-family: system-ui, sans-serif; background: #111;
         color: #eee; padding: 2em; max-width: 40em; margin: 0 auto; }
  h1 { font-weight: 500; font-size: 1.4rem; }
  .meta { opacity: 0.6; font-size: 0.9rem; }
  a { color: #6cf; }
</style>
</head>
<body>
<h1>Reset complete</h1>
<p class="meta">Scene reloaded · __REMOVED__ snapshot file(s) cleared · __MS__ ms</p>
<p><a href="/views/">Open live view →</a></p>
</body>
</html>
"""


_HTML_ERROR = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Roboclaws — reset failed</title>
<style>
  body { margin: 0; font-family: system-ui, sans-serif; background: #111;
         color: #eee; padding: 2em; max-width: 40em; margin: 0 auto; }
  h1 { color: #f77; font-weight: 500; }
  pre { background: #222; padding: 1em; border-radius: 3px; overflow: auto; }
</style>
</head>
<body>
<h1>Reset failed</h1>
<pre>__DETAIL__</pre>
</body>
</html>
"""


def _make_handler(mcp_server: RoboclawsMCPServer) -> type[http.server.BaseHTTPRequestHandler]:
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 — base class signature
            return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path not in ("/", "/reset"):
                self._send(404, "text/plain", b"not found\n")
                return
            try:
                summary = mcp_server.reset_world()
            except Exception as exc:  # surface as HTTP 500 with detail
                detail = f"{type(exc).__name__}: {exc}"
                print(f"[reset-server] reset failed: {detail}", file=sys.stderr)
                body = _HTML_ERROR.replace("__DETAIL__", _html_escape(detail)).encode("utf-8")
                self._send(500, "text/html; charset=utf-8", body)
                return
            body = (
                _HTML_DONE.replace("__REMOVED__", str(int(summary.get("snapshots_removed", 0))))
                .replace("__MS__", str(int(summary.get("elapsed_ms", 0))))
                .encode("utf-8")
            )
            self._send(200, "text/html; charset=utf-8", body)

        def _send(self, code: int, ctype: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


class ResetServer:
    """Thread-backed HTTP listener that exposes a single ``/reset`` route."""

    def __init__(
        self,
        mcp_server: RoboclawsMCPServer,
        *,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
    ) -> None:
        self.mcp_server = mcp_server
        self.host = host
        self.port = int(port)
        self._httpd: socketserver.TCPServer | None = None
        self._thread: threading.Thread | None = None

    def run_in_thread(self) -> threading.Thread:
        if self._thread is not None:
            raise RuntimeError("ResetServer already running")
        handler = _make_handler(self.mcp_server)
        socketserver.TCPServer.allow_reuse_address = True
        self._httpd = socketserver.TCPServer((self.host, self.port), handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="roboclaws-reset-server",
            daemon=True,
        )
        self._thread.start()
        return self._thread

    def shutdown(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        self._thread = None


DEFAULT_RESET_HOST = _DEFAULT_HOST
DEFAULT_RESET_PORT = _DEFAULT_PORT

__all__ = ["DEFAULT_RESET_HOST", "DEFAULT_RESET_PORT", "ResetServer", "_make_handler"]
