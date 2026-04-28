#!/usr/bin/env python3
"""Watch OpenClaw Gateway stdout and hint when multiple Control UI tabs connect.

Reads gateway log lines from stdin (piped via `tee >(...)` from
``[program:openclaw-gateway]`` in supervisord). Tracks WebSocket connection
lifecycle by parsing ``[ws] webchat connected conn=<id>`` / ``[ws] webchat
disconnected ... conn=<id>`` lines. When the policy decides "now's the time",
prints a one-line hint that the user sees inline with the gateway logs.

Why this exists: during the ~90s cold-start window the Gateway rejects
``chat.history`` / ``models.list`` with ``UNAVAILABLE`` until
``sidecars.channels`` finishes. Each open Control UI tab adds ~2 reject
lines per WS reconnect. Multiple tabs make startup look broken when it's
actually normal cold-start noise. See
``docs/retrospectives/openclaw-cold-start-2026-04-28.md``.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass, field

CONNECTED_RE = re.compile(r"\[ws\] webchat connected conn=([0-9a-f-]+)")
DISCONNECTED_RE = re.compile(r"\[ws\] webchat disconnected\b.*?conn=([0-9a-f-]+)")
# `[ws] closed before connect` never reached connected state — ignore it.


@dataclass
class WatcherState:
    """Mutable state passed to the policy on every WS lifecycle event."""

    active: dict[str, float] = field(default_factory=dict)  # conn_id -> connect t
    started_at: float = field(default_factory=time.monotonic)
    hint_count: int = 0
    last_hint_at: float | None = None
    peak_concurrent: int = 0

    def seconds_since_start(self) -> float:
        return time.monotonic() - self.started_at


# ---------------------------------------------------------------------------
# Hint policy — meaningful behavior choice, edit if you want different UX.
# ---------------------------------------------------------------------------
#
# Default: emit a single hint per gateway lifetime, at the moment concurrent
# Control UI connections first reach 2. Quiet, predictable, fires once during
# the noisy cold-start window if the user has multiple tabs open.
#
# Other reasonable policies:
#   - Cold-start-only: also gate on ``state.seconds_since_start() < 120``.
#     Quieter post-startup, at the cost of missing late multi-tab cases.
#   - Per-peak: hint each time concurrent count reaches a new peak.
#     Catches "user opened a 3rd tab later" but adds noise on reload.
#   - Throttled: hint every N seconds while ``len(state.active) >= 2``.
#     Most informative, most annoying.
#
# Return None to suppress the hint; return a string to print it.
def should_emit_hint(state: WatcherState) -> str | None:
    if state.hint_count >= 1:
        return None
    if len(state.active) < 2:
        return None
    return (
        f"[control-ui-watcher] hint: {len(state.active)} Control UI connections "
        f"active. During the ~90s cold-start window each open tab adds extra "
        f"`✗ chat.history` rejections to the log. Close extra tabs if you "
        f"didn't mean to open them."
    )


def _emit(line: str, *, sink) -> None:
    print(line, file=sink, flush=True)


def process_line(line: str, state: WatcherState, *, sink) -> None:
    m = CONNECTED_RE.search(line)
    if m:
        state.active[m.group(1)] = time.monotonic()
        state.peak_concurrent = max(state.peak_concurrent, len(state.active))
        hint = should_emit_hint(state)
        if hint is not None:
            _emit(hint, sink=sink)
            state.hint_count += 1
            state.last_hint_at = time.monotonic()
        return
    m = DISCONNECTED_RE.search(line)
    if m:
        state.active.pop(m.group(1), None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    state = WatcherState()
    for line in sys.stdin:
        try:
            process_line(line, state, sink=sys.stdout)
        except Exception as exc:  # noqa: BLE001 — never let watcher kill gateway pipe
            print(f"[control-ui-watcher] error: {exc!r}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
