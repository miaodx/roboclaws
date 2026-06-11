"""Stdlib HTTP server for the standalone agent operator console."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from roboclaws.operator_console.history import latest_run_payload
from roboclaws.operator_console.interactions import (
    InteractionError,
    append_ask_why,
    append_next_goal_request,
    append_steer_message,
    create_operator_session,
    get_operator_session,
    list_operator_messages,
)
from roboclaws.operator_console.launcher import (
    ConsoleLaunchError,
    LaunchRequest,
    route_readiness,
    start_console_run,
    stop_console_run,
)
from roboclaws.operator_console.paths import OUTPUT_ROOT_ENV, console_output_root
from roboclaws.operator_console.routes import (
    get_route,
    get_selection,
    list_console_combinations,
    list_evidence_lanes,
    list_worlds,
)
from roboclaws.operator_console.state import derive_operator_state, redacted_artifact_text

PAUSE_UNAVAILABLE_REASON = "Pause is unavailable for this route. Use Stop or Emergency Stop."


class ConsoleRequestHandler(SimpleHTTPRequestHandler):
    """Serve static assets plus JSON APIs."""

    def __init__(self, *args: object, root: Path, **kwargs: object) -> None:
        self.repo_root = root.resolve()
        static_root = Path(__file__).resolve().parent / "static"
        self.static_root = static_root.resolve()
        super().__init__(*args, directory=str(static_root), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html", "/app.js", "/styles.css"}:
            return self._static_file(parsed.path)
        if parsed.path.startswith("/previews/"):
            rel = Path(unquote(parsed.path.removeprefix("/previews/")))
            path = (self.static_root / "previews" / rel).resolve()
            preview_root = (self.static_root / "previews").resolve()
            if not _is_relative_to(path, preview_root) or not path.exists():
                return self.send_error(HTTPStatus.NOT_FOUND)
            return self._file(path)
        if parsed.path == "/api/routes":
            return self._json(
                {
                    "worlds": list(list_worlds()),
                    "evidence_lanes": list(list_evidence_lanes()),
                    "combinations": [
                        selection.to_payload()
                        for selection in list_console_combinations(include_disabled=True)
                    ],
                    "routes": [
                        selection.to_payload()
                        for selection in list_console_combinations(include_disabled=True)
                    ],
                    "readiness": {
                        selection.id: route_readiness(self.repo_root, selection)
                        for selection in list_console_combinations(include_disabled=False)
                    },
                }
            )
        if parsed.path == "/api/readiness":
            try:
                query = parse_qs(parsed.query)
                selection_id = str(query.get("selection_id", [""])[0])
                if not selection_id:
                    world_id = str(query.get("world_id", [""])[0])
                    backend_id = str(query.get("backend_id", [""])[0])
                    intent_id = str(query.get("intent_id", [""])[0])
                    agent_engine_id = str(query.get("agent_engine_id", [""])[0])
                    evidence_lane = str(query.get("evidence_lane", ["world-oracle-labels"])[0])
                    selection_id = "::".join(
                        (world_id, backend_id, intent_id, agent_engine_id, evidence_lane)
                    )
                route = get_selection(selection_id)
                overrides = {
                    key: str(query[key][0])
                    for key in (
                        "host",
                        "port",
                        "context_json",
                        "real_movement_enabled",
                        "scenario_setup",
                        "provider_profile",
                    )
                    if query.get(key, [""])[0]
                }
                gates = {
                    key: str(query[key][0]).lower() == "true"
                    for key in ("localization_ready", "run_enabled", "estop_ready")
                    if query.get(key, [""])[0]
                }
                env_overrides = {
                    "ROBOCLAWS_CODEX_PROVIDER": str(query.get("codex_provider", [""])[0]),
                    "ROBOCLAWS_CLAUDE_PROVIDER": str(query.get("claude_provider", [""])[0]),
                }
                env_overrides = {key: value for key, value in env_overrides.items() if value}
                return self._json(
                    route_readiness(
                        self.repo_root,
                        route,
                        overrides=overrides,
                        env_overrides=env_overrides,
                        gates=gates,
                    )
                )
            except (ConsoleLaunchError, KeyError, ValueError) as exc:
                return self._json({"error": str(exc)}, status=400)
        if parsed.path == "/api/runs/latest":
            latest = latest_run_payload(self.repo_root)
            if not latest:
                return self._json({"error": "No operator-console run artifacts found."}, status=404)
            return self._json(latest)
        if parsed.path.startswith("/api/sessions/"):
            session_id = unquote(parsed.path.removeprefix("/api/sessions/"))
            try:
                return self._json(get_operator_session(self.repo_root, session_id))
            except InteractionError as exc:
                return self._json({"error": str(exc)}, status=404)
        if parsed.path.startswith("/api/runs/"):
            run_id = unquote(parsed.path.removeprefix("/api/runs/"))
            if run_id.endswith("/pause"):
                run_id = run_id.removesuffix("/pause")
                return self._json(
                    {
                        "run_id": run_id,
                        "paused": False,
                        "reason": PAUSE_UNAVAILABLE_REASON,
                    }
                )
            if run_id.endswith("/messages"):
                run_id = run_id.removesuffix("/messages")
                try:
                    return self._json(list_operator_messages(self.repo_root, run_id))
                except InteractionError as exc:
                    return self._json({"error": str(exc)}, status=404)
            route_id = parse_qs(parsed.query).get("route", [""])[0]
            route = get_route(route_id) if route_id else None
            run_dir = console_output_root(self.repo_root) / "runs" / run_id
            return self._json(derive_operator_state(self.repo_root, run_dir, route))
        if parsed.path.startswith("/api/raw/"):
            rel = Path(unquote(parsed.path.removeprefix("/api/raw/")))
            path = (self.repo_root / rel).resolve()
            if not _is_relative_to(path, self.repo_root) or not path.exists():
                return self.send_error(HTTPStatus.NOT_FOUND)
            return self._text(redacted_artifact_text(path))
        if parsed.path.startswith("/artifacts/"):
            rel = Path(unquote(parsed.path.removeprefix("/artifacts/")))
            path = (self.repo_root / rel).resolve()
            if not _is_relative_to(path, self.repo_root) or not path.exists():
                return self.send_error(HTTPStatus.NOT_FOUND)
            return self._file(path)
        return super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html", "/app.js", "/styles.css"}:
            return self._static_file(parsed.path, body=False)
        return super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            payload = self._read_payload()
            if parsed.path == "/api/sessions":
                return self._json(create_operator_session(self.repo_root), status=201)
            if parsed.path == "/api/runs":
                request = LaunchRequest(
                    world_id=str(payload.get("world_id") or ""),
                    backend_id=str(payload.get("backend_id") or ""),
                    intent_id=str(payload.get("intent_id") or payload.get("intent") or ""),
                    agent_engine_id=str(payload.get("agent_engine_id") or ""),
                    provider_profile=str(payload.get("provider_profile") or ""),
                    evidence_lane=str(payload.get("evidence_lane") or ""),
                    scenario_setup=str(payload.get("scenario_setup") or ""),
                    prompt=str(payload.get("prompt") or ""),
                    overrides=dict(payload.get("overrides") or {}),
                    env_overrides=dict(payload.get("env_overrides") or {}),
                    gates=dict(payload.get("gates") or {}),
                    operator_session_id=str(payload.get("operator_session_id") or ""),
                    parent_run_id=str(payload.get("parent_run_id") or ""),
                    next_goal_packet=dict(payload.get("next_goal_packet") or {}),
                    route_id=str(payload.get("route_id") or ""),
                )
                return self._json(start_console_run(self.repo_root, request), status=201)
            run_action = _parse_run_action_path(parsed.path)
            if run_action and run_action[1] == "ask-why":
                run_id = run_action[0]
                return self._json(
                    append_ask_why(self.repo_root, run_id, str(payload.get("question") or "")),
                    status=201,
                )
            if run_action and run_action[1] == "messages":
                run_id = run_action[0]
                return self._json(
                    append_steer_message(self.repo_root, run_id, str(payload.get("body") or "")),
                    status=201,
                )
            if run_action and run_action[1] == "next-goal":
                run_id = run_action[0]
                follow_up = append_next_goal_request(
                    self.repo_root,
                    run_id,
                    str(payload.get("prompt") or payload.get("body") or ""),
                    confirmed=bool(payload.get("confirmed")),
                )
                if follow_up.get("status") == "ready_to_start" and follow_up.get(
                    "auto_start_allowed"
                ):
                    launch = LaunchRequest(
                        route_id=str(follow_up.get("route_id") or ""),
                        intent_id=str(follow_up.get("intent") or ""),
                        prompt=str(follow_up.get("body") or ""),
                        operator_session_id=str(follow_up.get("operator_session_id") or ""),
                        parent_run_id=run_id,
                        next_goal_packet=dict(follow_up.get("next_goal_packet") or {}),
                    )
                    selection_id = str(follow_up.get("selection_id") or "")
                    if selection_id:
                        parts = selection_id.split("::")
                        if len(parts) == 5:
                            (
                                launch.world_id,
                                launch.backend_id,
                                launch.intent_id,
                                launch.agent_engine_id,
                                launch.evidence_lane,
                            ) = parts
                    try:
                        follow_up["started_run"] = start_console_run(self.repo_root, launch)
                        follow_up["status"] = "started"
                    except ConsoleLaunchError as exc:
                        follow_up["start_error"] = str(exc)
                return self._json(follow_up, status=201)
            if run_action and run_action[1] == "pause":
                run_id = run_action[0]
                return self._json(
                    {
                        "run_id": run_id,
                        "paused": False,
                        "reason": PAUSE_UNAVAILABLE_REASON,
                    }
                )
            if run_action and run_action[1] == "stop":
                run_id = run_action[0]
                return self._json(stop_console_run(self.repo_root, run_id))
            if run_action and run_action[1] == "emergency-stop":
                run_id = run_action[0]
                return self._json(stop_console_run(self.repo_root, run_id, emergency=True))
        except (ConsoleLaunchError, InteractionError, KeyError, ValueError) as exc:
            return self._json({"error": str(exc)}, status=400)
        return self.send_error(HTTPStatus.NOT_FOUND)

    def _read_payload(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        data = self.rfile.read(length)
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("expected JSON object")
        return payload

    def _json(self, payload: object, *, status: int = 200) -> None:
        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _text(self, text: str, *, status: int = 200) -> None:
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _static_file(self, request_path: str, *, body: bool = True) -> None:
        name = "index.html" if request_path in {"/", "/index.html"} else request_path.lstrip("/")
        path = Path(self.directory) / name
        if not path.exists():
            return self.send_error(HTTPStatus.NOT_FOUND)
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix in {".html", ".css", ".js"}:
            content_type = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
            }[path.suffix]
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if body:
            self.wfile.write(data)


def run_server(root: Path, host: str, port: int) -> None:
    handler = partial(ConsoleRequestHandler, root=root)
    server = ThreadingHTTPServer((host, port), handler)
    url_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    print(f"Agent Operator Console: http://{url_host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the standalone agent operator console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.output_root is not None:
        os.environ[OUTPUT_ROOT_ENV] = str(args.output_root)
    run_server(args.repo_root.resolve(), args.host, args.port)
    return 0


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _parse_run_action_path(path: str) -> tuple[str, str] | None:
    prefix = "/api/runs/"
    if not path.startswith(prefix):
        return None
    remainder = path.removeprefix(prefix)
    for action in ("emergency-stop", "next-goal", "ask-why", "messages", "pause", "stop"):
        suffix = f"/{action}"
        if remainder.endswith(suffix):
            return unquote(remainder[: -len(suffix)]), action
    return None
