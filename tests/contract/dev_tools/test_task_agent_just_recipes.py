from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
JUSTFILE = REPO_ROOT / "justfile"
JUST_DIR = REPO_ROOT / "just"
TASK_JUST = JUST_DIR / "task.just"
AGENT_JUST = JUST_DIR / "agent.just"


def test_task_and_agent_modules_are_registered() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")

    assert re.search(r"^mod agent\s+'just/agent\.just'$", text, re.MULTILINE)
    assert re.search(r"^mod task\s+'just/task\.just'$", text, re.MULTILINE)


def test_agent_module_exposes_driver_facing_aliases() -> None:
    text = AGENT_JUST.read_text(encoding="utf-8")

    expected_headers = (
        r"^codex-nav scene=\"FloorPlan201\"",
        r"^claude-nav scene=\"FloorPlan201\"",
        r"^openclaw-nav agents=\"2\"",
        r"^openclaw-photo provider=\"kimi\"",
        r"^openclaw-territory agents=\"2\"",
        r"^openclaw-coverage agents=\"2\"",
        r"^openclaw-ui provider=\"mimo\"",
        r"^vlm-territory model=\"kimi-coding\"",
        r"^vlm-coverage model=\"kimi-coding\"",
        r"^script-territory agents=\"2\"",
        r"^script-coverage agents=\"2\"",
    )
    for header in expected_headers:
        assert re.search(header, text, re.MULTILINE), f"missing recipe header: {header}"


def test_task_module_exposes_outcome_facing_aliases() -> None:
    text = TASK_JUST.read_text(encoding="utf-8")

    expected_headers = (
        r"^navigate driver=\"openclaw\"",
        r"^control-ui driver=\"openclaw\"",
        r"^photo-chairs driver=\"openclaw\"",
        r"^territory driver=\"vlm\"",
        r"^coverage driver=\"vlm\"",
        r"^cleanup-quick-check driver=\"mcp-smoke\"",
        r"^cleanup-report driver=\"direct\"",
        r"^cleanup-raw-fpv seed=\"7\"",
        r"^planner-proof mode=\"dry-run\"",
        r"^check what=\"mock\"",
    )
    for header in expected_headers:
        assert re.search(header, text, re.MULTILINE), f"missing recipe header: {header}"


def test_agent_delegates_only_to_lower_level_modules_or_examples() -> None:
    text = AGENT_JUST.read_text(encoding="utf-8")

    expected_calls = (
        'just code::codex "{{scene}}" "{{host}}" "{{port}}"',
        'just code::cc "{{scene}}" "{{host}}" "{{port}}"',
        'just openclaw::run "nav"',
        'just openclaw::run "photo"',
        'just openclaw::run "territory"',
        'just openclaw::run "coverage"',
        "just chat::run",
        'just vlm::run "territory"',
        'just vlm::run "coverage"',
        "examples/territory_game.py",
        "examples/coverage_game.py",
    )
    for call in expected_calls:
        assert call in text

    assert "just task::" not in text


def test_task_delegates_downward_to_agent_molmo_harness_or_verify() -> None:
    text = TASK_JUST.read_text(encoding="utf-8")

    expected_calls = (
        "just agent::codex-nav",
        "just agent::claude-nav",
        "just agent::openclaw-nav",
        "just agent::openclaw-ui",
        "just agent::openclaw-photo",
        "just agent::vlm-territory",
        "just agent::openclaw-territory",
        "just agent::script-territory",
        "just agent::vlm-coverage",
        "just agent::openclaw-coverage",
        "just agent::script-coverage",
        "just molmo::quick-check",
        "just molmo::cleanup",
        "just molmo::raw-fpv-report",
        "just harness::molmo-planner-proof-bundle-runner",
        "just harness::molmo-planner-proof-bundle-execute-rerun",
        'just verify::"$what"',
        "just verify::molmo-realworld-cleanup",
    )
    for call in expected_calls:
        assert call in text

    assert 'selected_seeds="7"' in text
    assert "codex-live|claude-live|openclaw-live" in text


def test_lower_level_just_modules_do_not_call_task_or_agent_facades() -> None:
    for path in JUST_DIR.glob("*.just"):
        if path.name in {"task.just", "agent.just"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "just task::" not in text, path
        assert "just agent::" not in text, path
