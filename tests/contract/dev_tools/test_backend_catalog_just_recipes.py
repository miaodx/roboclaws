from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def just_bin() -> str:
    path = shutil.which("just")
    if path:
        return path
    local_path = Path.home() / ".local/bin" / "just"
    if local_path.exists():
        return str(local_path)
    pytest.skip("just binary is not available")


def test_molmo_cleanup_rejects_unknown_backend_from_catalog() -> None:
    result = subprocess.run(
        [
            just_bin(),
            "molmo::household-world-impl",
            "direct",
            "world-oracle-labels",
            "7",
            "output/test",
            "task",
            "1",
            "127.0.0.1",
            "18788",
            "auto",
            "auto",
            "auto",
            "",
            "auto",
            "off",
            "",
            "backend=missing_backend",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "unsupported backend 'missing_backend'" in result.stderr
    assert "expected api_semantic_synthetic|molmospaces_subprocess|isaaclab_subprocess" in (
        result.stderr
    )


def test_codex_map_build_rejects_unknown_backend_from_catalog() -> None:
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    result = subprocess.run(
        [
            just_bin(),
            "agent::run",
            "household-world.map-build",
            "codex-cli",
            "world-oracle-labels",
            "backend=missing_backend",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "household-world.map-build codex-cli unsupported backend 'missing_backend'" in (
        result.stderr
    )
    assert "expected auto|molmospaces_subprocess|isaaclab_subprocess|agibot_gdk" in (result.stderr)
