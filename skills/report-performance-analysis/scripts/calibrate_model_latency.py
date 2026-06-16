#!/usr/bin/env python3
"""Skill wrapper for scripts/reports/calibrate_model_latency.py."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[3]
    runpy.run_path(
        str(repo_root / "scripts" / "reports" / "calibrate_model_latency.py"),
        run_name="__main__",
    )
