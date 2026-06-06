#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[3]
    runpy.run_path(
        str(repo_root / "scripts" / "molmo_cleanup" / "run_codex_cleanup_harness8.py"),
        run_name="__main__",
    )
