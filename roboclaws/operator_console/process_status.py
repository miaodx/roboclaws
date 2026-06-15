"""Small process-state helpers for operator-console lifecycle checks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def pid_is_active(pid: Any) -> bool:
    """Return true only for a live, non-zombie process id."""

    try:
        parsed_pid = int(pid)
    except (TypeError, ValueError):
        return False
    if parsed_pid <= 0:
        return False
    if _proc_state(parsed_pid) == "Z":
        return False
    try:
        os.kill(parsed_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _proc_state(pid: int) -> str:
    try:
        raw = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return ""
    try:
        return raw.rsplit(") ", 1)[1].split()[0]
    except IndexError:
        return ""
