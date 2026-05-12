from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
JUSTFILE = REPO_ROOT / "justfile"
JUST_DIR = REPO_ROOT / "just"
TASK_JUST = JUST_DIR / "task.just"
AGENT_JUST = JUST_DIR / "agent.just"


def just_bin() -> str:
    path = shutil.which("just")
    if path:
        return path
    local_path = Path.home() / ".local/bin" / "just"
    if local_path.exists():
        return str(local_path)
    pytest.skip("just binary is not available")


def just_summary() -> set[str]:
    result = subprocess.run(
        [just_bin(), "--summary"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.split())


def trace_task_run(*args: str) -> list[str]:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "task::run", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


def test_public_just_summary_is_small_facade() -> None:
    summary = just_summary()

    assert summary == {
        "task::run",
        "agent::run",
        "agent::verify",
        "agent::harness",
        "agent::mcp",
        "agent::gateway",
    }

    hidden_recipes = {
        "openclaw::run",
        "vlm::run",
        "molmo::cleanup",
        "harness::molmo-realworld-cleanup",
        "verify::mock",
        "code::codex",
        "task::territory",
        "agent::codex-nav",
    }
    assert summary.isdisjoint(hidden_recipes)


def test_justfile_marks_implementation_modules_private() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")

    for module in (
        "openclaw",
        "vlm",
        "chat",
        "appliance",
        "dev",
        "mcp",
        "code",
        "harness",
        "verify",
        "molmo",
    ):
        assert re.search(
            rf"^\[private\]\nmod {module}\s+'just/{module}\.just'$",
            text,
            re.MULTILINE,
        )

    assert re.search(r"^mod agent\s+'just/agent\.just'$", text, re.MULTILINE)
    assert re.search(r"^mod task\s+'just/task\.just'$", text, re.MULTILINE)


def test_agent_module_exposes_compact_dispatchers() -> None:
    text = AGENT_JUST.read_text(encoding="utf-8")

    expected_headers = (
        r"^run task driver report=\"visual\" \*overrides:",
        r"^verify target=\"mock\" \*args:",
        r"^harness target \*args:",
        r"^mcp action=\"up\"",
        r"^gateway action=\"up\"",
    )
    for header in expected_headers:
        assert re.search(header, text, re.MULTILINE), f"missing recipe header: {header}"

    removed_combo_aliases = (
        "codex-nav",
        "claude-nav",
        "openclaw-territory",
        "vlm-coverage",
        "script-territory",
    )
    for alias in removed_combo_aliases:
        assert not re.search(rf"^{alias}\b", text, re.MULTILINE)


def test_task_module_exposes_only_run_publicly() -> None:
    text = TASK_JUST.read_text(encoding="utf-8")

    assert re.search(r"^run task driver report=\"visual\" \*overrides:", text, re.MULTILINE)
    assert "[private]\nnavigate " in text
    assert "[private]\nterritory " in text
    assert "[private]\ncleanup-report " in text

    summary = just_summary()
    assert "task::run" in summary
    assert "task::navigate" not in summary
    assert "task::cleanup-report" not in summary


def test_prompt_mapping_molmo_cleanup_codex_visual_default() -> None:
    route = trace_task_run("molmo-cleanup", "codex")

    assert route[:7] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "molmospaces",
        "visual",
        "7",
        "output/molmo/codex-report",
    ]


def test_prompt_mapping_molmo_cleanup_codex_minimal_override() -> None:
    route = trace_task_run("molmo-cleanup", "codex", "minimal")

    assert route[:7] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "synthetic",
        "semantic",
        "7",
        "output/molmo/codex-minimal",
    ]


def test_prompt_mapping_ai2thor_nav_openclaw_visual_default() -> None:
    route = trace_task_run("ai2thor-nav", "openclaw")

    assert route == [
        "just",
        "openclaw::run",
        "nav",
        "2",
        "10",
        "kimi",
        "output/openclaw/nav",
    ]


def test_key_value_third_argument_keeps_visual_default() -> None:
    route = trace_task_run("molmo-cleanup", "codex", "output_dir=output/custom")

    assert route[:7] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "molmospaces",
        "visual",
        "7",
        "output/custom",
    ]


def test_lower_level_just_modules_do_not_call_task_or_agent_facades() -> None:
    for path in JUST_DIR.glob("*.just"):
        if path.name in {"task.just", "agent.just"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "just task::" not in text, path
        assert "just agent::" not in text, path
