#!/usr/bin/env python3
"""Tail the OpenClaw Gateway's active session JSONL for a given agent.

The Gateway writes every user turn, assistant reply, and tool round-trip
to ``/home/node/.openclaw/agents/<agent>/sessions/<uuid>.jsonl`` inside
the container. That's the authoritative transcript of what you typed in
the Control UI chat tab — our host-side ``trace.jsonl`` only sees the
agent's tool-call side.

This helper:

1. Finds the most-recently-modified session file for the agent.
2. Prints its existing content in a compact human-readable form.
3. ``docker exec tail -F`` on that file, pretty-printing new lines as
   they arrive. Also mirrors the pretty output to ``--log-file`` (if
   given) so another process — or the operator's Claude Code session —
   can diff it offline.

Usage::

    python scripts/openclaw/tail-openclaw-chat.py
    python scripts/openclaw/tail-openclaw-chat.py --agent agent-0 \\
        --log-file output/openclaw-interactive/latest/chat.log
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import IO, Any

_DEFAULT_CONTAINER = "openclaw-gateway"
_DEFAULT_AGENT = "agent-0"
_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RUNS_DIR = _ROOT / "output" / "openclaw-interactive"
_LATEST_SYMLINK = _DEFAULT_RUNS_DIR / "latest-chat.log"

_SESSION_DIR_TMPL = "/home/node/.openclaw/agents/{agent}/sessions"
# Match `<uuid>.jsonl` only — exclude sidecars introduced by newer Gateway
# builds (`<uuid>.trajectory.jsonl`, `<uuid>.trajectory-path.json`,
# `<uuid>.jsonl.reset.<ts>`, ...). Trajectory files are touched per-event
# and would otherwise win `ls -t` over the per-turn message transcript.
_SESSION_FILE_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$"
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tail and pretty-print the active OpenClaw session JSONL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--container", default=_DEFAULT_CONTAINER)
    parser.add_argument("--agent", default=_DEFAULT_AGENT)
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Mirror the pretty-printed transcript to this host-side file. "
        "When omitted, defaults to `<latest-run>/chat.log` inside "
        "output/openclaw-interactive/ and keeps a `latest-chat.log` symlink "
        "at the parent pointing to it — per-run transcripts survive for "
        "later review, operator always has one stable filename.",
    )
    parser.add_argument(
        "--session",
        default=None,
        help="Explicit session UUID (default: pick the most recently modified).",
    )
    return parser.parse_args(argv)


def _latest_run_dir() -> Path | None:
    """Return the most-recently-modified run dir under output/openclaw-interactive/."""
    if not _DEFAULT_RUNS_DIR.exists():
        return None
    runs = [p for p in _DEFAULT_RUNS_DIR.iterdir() if p.is_dir()]
    if not runs:
        return None
    return max(runs, key=lambda p: p.stat().st_mtime)


def _refresh_latest_symlink(target: Path) -> None:
    """Point `output/openclaw-interactive/latest-chat.log` at `target`.

    Uses a relative symlink so moving the `output/` tree doesn't break
    it. Replaces any existing symlink (or file) atomically. Silently
    skips if symlink creation isn't supported (e.g. Windows without
    dev-mode) — the log still gets written to the per-run path.
    """
    link = _LATEST_SYMLINK
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        rel = Path(target).resolve().relative_to(link.parent.resolve())
    except ValueError:
        rel = Path(target).resolve()
    tmp = link.with_suffix(link.suffix + ".tmp")
    try:
        if tmp.is_symlink() or tmp.exists():
            tmp.unlink()
        tmp.symlink_to(rel)
        tmp.replace(link)
    except OSError:
        pass


def _latest_session(container: str, agent: str) -> str:
    """Return the path of the most-recently-modified `<uuid>.jsonl` session file."""
    sessions_dir = _SESSION_DIR_TMPL.format(agent=agent)
    out = subprocess.run(
        ["docker", "exec", container, "sh", "-lc", f"ls -t {sessions_dir} 2>/dev/null"],
        capture_output=True,
        text=True,
        check=True,
    )
    for name in out.stdout.splitlines():
        name = name.strip()
        if _SESSION_FILE_RE.match(name):
            return f"{sessions_dir}/{name}"
    raise RuntimeError(
        f"no session files matching <uuid>.jsonl found for agent '{agent}' "
        f"in container '{container}'"
    )


def _fmt_content(content: Any) -> list[str]:
    """Flatten a message content block into one-line summaries."""
    if isinstance(content, str):
        return [content.strip()] if content.strip() else []
    if not isinstance(content, list):
        return [repr(content)]
    lines: list[str] = []
    for part in content:
        rendered = _fmt_part(part)
        if rendered:
            lines.append(rendered)
    return lines


def _fmt_part(part: Any) -> str:
    if not isinstance(part, dict):
        return repr(part)
    ptype = part.get("type", "?")
    if ptype == "text":
        return str(part.get("text") or "").strip()
    if ptype == "toolCall":
        return _fmt_tool_call(part)
    if ptype == "toolResult":
        return _fmt_tool_result(part)
    if ptype in ("image", "image_url"):
        return _fmt_image_part(part)
    return f"[{ptype}]"


def _fmt_tool_call(part: dict[str, Any]) -> str:
    name = part.get("name", "?")
    args = part.get("arguments") or part.get("args") or {}
    args_s = json.dumps(args, separators=(",", ":"))
    if len(args_s) > 120:
        args_s = args_s[:117] + "..."
    return f"→ toolCall {name} {args_s}"


def _fmt_tool_result(part: dict[str, Any]) -> str:
    name = part.get("toolName") or part.get("name") or "?"
    inner = part.get("content") or []
    inner_kinds = [item.get("type", "?") for item in inner if isinstance(item, dict)]
    return f"← toolResult {name} parts={inner_kinds}"


def _fmt_image_part(part: dict[str, Any]) -> str:
    src = part.get("source") or part.get("image_url") or "?"
    if isinstance(src, dict):
        src = src.get("type", "?")
    return f"[image: {src}]"


def _render_line(raw: str) -> list[str]:
    """Return pretty-printed lines for a single session JSONL entry."""
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError:
        return [f"?? invalid json: {raw[:120]}"]
    etype = entry.get("type", "?")
    if etype != "message":
        # Surface session lifecycle events tersely (session/model_change/...).
        return [f". {etype}"]
    msg = entry.get("message", {})
    role = msg.get("role", "?")
    body_lines = _fmt_content(msg.get("content", []))
    if not body_lines:
        return [f"{role}:"]
    head, *tail = body_lines
    out = [f"{role}: {head}"]
    out.extend(f"  {line}" for line in tail)
    return out


def _emit(lines: list[str], sinks: list[IO[str]]) -> None:
    for line in lines:
        for sink in sinks:
            sink.write(line + "\n")
    for sink in sinks:
        sink.flush()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        session_path = _session_path(args)
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    log_file = _defaulted_log_file(args.log_file)
    log_fp = _open_log_sink(log_file)
    sinks: list[IO[str]] = [sys.stdout] + ([log_fp] if log_fp else [])

    banner = f"# tail {args.container}:{session_path}" + (
        f" → {log_file}  (symlink: {_LATEST_SYMLINK})" if log_file else ""
    )
    _emit([banner, "-" * len(banner)], sinks)
    return _tail_session(args.container, session_path, sinks=sinks, log_fp=log_fp)


def _session_path(args: argparse.Namespace) -> str:
    if args.session:
        return f"/home/node/.openclaw/agents/{args.agent}/sessions/{args.session}.jsonl"
    return _latest_session(args.container, args.agent)


def _defaulted_log_file(log_file: Path | None) -> Path | None:
    if log_file is not None:
        return log_file
    latest_run = _latest_run_dir()
    return latest_run / "chat.log" if latest_run is not None else None


def _open_log_sink(log_file: Path | None) -> IO[str] | None:
    if log_file is None:
        return None
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_fp = log_file.open("a", encoding="utf-8", buffering=1)
    _refresh_latest_symlink(log_file)
    return log_fp


def _tail_session(
    container: str,
    session_path: str,
    *,
    sinks: list[IO[str]],
    log_fp: IO[str] | None,
) -> int:
    # `tail -n +1 -F` prints the whole file then follows new lines.
    proc = subprocess.Popen(
        [
            "docker",
            "exec",
            container,
            "sh",
            "-lc",
            f"tail -n +1 -F {session_path}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None

    try:
        for raw in proc.stdout:
            raw = raw.rstrip("\n")
            if not raw:
                continue
            _emit(_render_line(raw), sinks)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        if log_fp is not None:
            log_fp.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
