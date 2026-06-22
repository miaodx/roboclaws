"""Path helpers for the standalone operator console."""

from __future__ import annotations

import os
from pathlib import Path

OUTPUT_ROOT_ENV = "ROBOCLAWS_OPERATOR_CONSOLE_OUTPUT_ROOT"


def console_output_root(root: Path) -> Path:
    configured = os.environ.get(OUTPUT_ROOT_ENV, "")
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = root / path
        return path
    return root / "output" / "operator-console"


def operator_output_file(root: Path, rel: str) -> Path | None:
    output_root = console_output_root(root).resolve()
    path = (root / Path(rel)).resolve()
    if not _is_relative_to(path, output_root) or not path.is_file():
        return None
    return path


def operator_output_request_path(root: Path, path: Path) -> str:
    try:
        resolved = path.resolve()
        resolved.relative_to(console_output_root(root).resolve())
    except (OSError, ValueError):
        return ""
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
