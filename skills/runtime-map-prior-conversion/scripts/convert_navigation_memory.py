#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONVERTER = REPO_ROOT / "scripts" / "maps" / "convert_agibot_navigation_memory.py"


def main(argv: list[str] | None = None) -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("convert_agibot_navigation_memory", CONVERTER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load converter script: {CONVERTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main(argv)


if __name__ == "__main__":
    main()
