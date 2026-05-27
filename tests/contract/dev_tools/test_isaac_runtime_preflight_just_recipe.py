from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
JUST_DIR = REPO_ROOT / "just"
AGENT_JUST = JUST_DIR / "agent.just"
HARNESS_JUST = JUST_DIR / "harness.just"


def just_bin() -> str:
    path = shutil.which("just")
    if path:
        return path
    local_path = Path.home() / ".local/bin" / "just"
    if local_path.exists():
        return str(local_path)
    pytest.skip("just binary is not available")


def trace_agent_harness(*args: str) -> list[str]:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::harness", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


def test_agent_harness_allows_isaac_runtime_preflight_target() -> None:
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    harness_text = HARNESS_JUST.read_text(encoding="utf-8")

    assert "molmo-isaac-runtime-preflight" in agent_text
    assert re.search(r"^molmo-isaac-runtime-preflight \*overrides:", harness_text, re.MULTILINE)
    assert "check_isaac_lab_runtime.py" in harness_text
    assert "accept_nvidia_eula=true" in harness_text

    route = trace_agent_harness(
        "molmo-isaac-runtime-preflight",
        "output_dir=/tmp/roboclaws-isaac-preflight",
        "strict=true",
    )
    assert route == [
        "just",
        "harness::molmo-isaac-runtime-preflight",
        "output_dir=/tmp/roboclaws-isaac-preflight",
        "strict=true",
    ]


def test_agent_harness_allows_isaac_runtime_smoke_target() -> None:
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    harness_text = HARNESS_JUST.read_text(encoding="utf-8")

    assert "molmo-isaac-runtime-smoke" in agent_text
    assert re.search(r"^molmo-isaac-runtime-smoke \*overrides:", harness_text, re.MULTILINE)
    assert "isaac_lab_backend_worker.py" in harness_text
    assert "check_isaac_lab_runtime_smoke_result.py" in harness_text
    assert "scene_usd_path" in harness_text
    assert "--require-real-rendering" in harness_text
    assert "--require-usd-stage-loaded" in harness_text
    assert "--require-usd-scene-index" in harness_text

    route = trace_agent_harness(
        "molmo-isaac-runtime-smoke",
        "output_dir=/tmp/roboclaws-isaac-smoke",
        "runtime_python=/tmp/isaac-python",
        "scene_usd_path=/tmp/molmospaces-scene.usd",
    )
    assert route == [
        "just",
        "harness::molmo-isaac-runtime-smoke",
        "output_dir=/tmp/roboclaws-isaac-smoke",
        "runtime_python=/tmp/isaac-python",
        "scene_usd_path=/tmp/molmospaces-scene.usd",
    ]
