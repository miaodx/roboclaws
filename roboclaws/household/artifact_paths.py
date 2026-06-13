from __future__ import annotations

from pathlib import Path
from typing import Any


def dimensions_from_shape(shape: Any) -> dict[str, int]:
    if not isinstance(shape, list) or len(shape) < 2:
        return {}
    try:
        height = int(shape[0])
        width = int(shape[1])
        dimensions = {"width": width, "height": height}
        if len(shape) >= 3:
            dimensions["channels"] = int(shape[2])
        return dimensions
    except (TypeError, ValueError):
        return {}


def output_relpath(path: Path, output_dir: Path) -> str:
    try:
        return str(path.resolve().relative_to(output_dir.resolve()))
    except ValueError:
        return str(path)
