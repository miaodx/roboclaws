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

    python scripts/tail-openclaw-chat.py
    python scripts/tail-openclaw-chat.py --agent agent-0 \\
        --log-file output/openclaw-interactive/latest/chat.log
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import IO, Any

_DEFAULT_CONTAINER = "openclaw-gateway"
_DEFAULT_AGENT = "agent-0"


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
        help="Mirror the pretty-printed transcript to this host-side file "
        "(parent dirs are auto-created).",
    )
    parser.add_argument(
        "--session",
        default=None,
        help="Explicit session UUID (default: pick the most recently modified).",
    )
    return parser.parse_args(argv)


def _latest_session(container: str, agent: str) -> str:
    """Return the basename of the most-recently-modified session .jsonl."""
    out = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "sh",
            "-lc",
            f"ls -t /home/node/.openclaw/agents/{agent}/sessions/*.jsonl 2>/dev/null | head -n1",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    path = out.stdout.strip()
    if not path:
        raise RuntimeError(f"no session files found for agent '{agent}' in container '{container}'")
    return path


def _fmt_content(content: Any) -> list[str]:
    """Flatten a message content block into one-line summaries."""
    if isinstance(content, str):
        return [content.strip()] if content.strip() else []
    if not isinstance(content, list):
        return [repr(content)]
    lines: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            lines.append(repr(part))
            continue
        ptype = part.get("type", "?")
        if ptype == "text":
            text = (part.get("text") or "").strip()
            if text:
                lines.append(text)
        elif ptype == "toolCall":
            name = part.get("name", "?")
            args = part.get("arguments") or part.get("args") or {}
            args_s = json.dumps(args, separators=(",", ":"))
            if len(args_s) > 120:
                args_s = args_s[:117] + "..."
            lines.append(f"→ toolCall {name} {args_s}")
        elif ptype == "toolResult":
            name = part.get("toolName") or part.get("name") or "?"
            inner = part.get("content") or []
            inner_kinds = [c.get("type", "?") for c in inner if isinstance(c, dict)]
            lines.append(f"← toolResult {name} parts={inner_kinds}")
        elif ptype in ("image", "image_url"):
            src = part.get("source") or part.get("image_url") or "?"
            if isinstance(src, dict):
                src = src.get("type", "?")
            lines.append(f"[image: {src}]")
        else:
            lines.append(f"[{ptype}]")
    return lines


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
        if args.session:
            session_path = f"/home/node/.openclaw/agents/{args.agent}/sessions/{args.session}.jsonl"
        else:
            session_path = _latest_session(args.container, args.agent)
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    log_fp: IO[str] | None = None
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_fp = args.log_file.open("a", encoding="utf-8", buffering=1)
    sinks: list[IO[str]] = [sys.stdout] + ([log_fp] if log_fp else [])

    banner = f"# tail {args.container}:{session_path}" + (
        f" → {args.log_file}" if args.log_file else ""
    )
    _emit([banner, "-" * len(banner)], sinks)

    # `tail -n +1 -F` prints the whole file then follows new lines.
    proc = subprocess.Popen(
        [
            "docker",
            "exec",
            args.container,
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
