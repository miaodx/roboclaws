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
