"""Launch context helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LaunchContext:
    """Filesystem context for a task launch."""

    repo_root: Path
    env: dict[str, str]
