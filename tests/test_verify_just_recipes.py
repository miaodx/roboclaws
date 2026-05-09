from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JUSTFILE = REPO_ROOT / "justfile"
JUST_DIR = REPO_ROOT / "just"
VERIFY_JUST = JUST_DIR / "verify.just"
HARNESS_JUST = JUST_DIR / "harness.just"


def test_verify_module_is_registered() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")

    assert re.search(r"^mod verify\s+'just/verify\.just'$", text, re.MULTILINE)


def test_verify_layer_keeps_static_checks_out_of_harness_namespace() -> None:
    verify_text = VERIFY_JUST.read_text(encoding="utf-8")
    harness_text = HARNESS_JUST.read_text(encoding="utf-8")

    assert "ruff check ." in verify_text
    assert "ruff format --check ." in verify_text
    assert "git diff --check" in verify_text
    assert "ruff check ." not in harness_text
    assert "ruff format --check ." not in harness_text
    assert "git diff --check" not in harness_text


def test_verify_delegates_scenario_gates_to_harness() -> None:
    text = VERIFY_JUST.read_text(encoding="utf-8")

    expected_calls = (
        "just harness::regression",
        "just harness::sim",
        "just harness::openclaw",
        "just harness::navigator",
        "just harness::molmo-cleanup",
        "just harness::molmo-prompt-cleanup",
        "just harness::molmo-real-cleanup",
        "just harness::molmo-robot-visual",
        "just harness::molmo-agent-bridge",
        "just harness::molmo-agent-bridge-visual",
        "just harness::molmo-realworld-cleanup",
        "just harness::molmo-realworld-agent-mcp",
        "just harness::molmo-realworld-agent-dogfood-kit",
        "just harness::molmo-realworld-openclaw-dogfood-kit",
        "just harness::molmo-realworld-openclaw-visual-dogfood-kit",
        "just harness::molmo-realworld-raw-fpv",
    )
    for call in expected_calls:
        assert call in text


def test_harness_exposes_named_execution_rigs() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    expected_headers = (
        r"^navigator task cap=\"900\":$",
        r"^regression mode=\"mock\"",
        r"^sim scenes=\"FloorPlan201\"",
        r"^openclaw scenes=\"FloorPlan201\"",
        r"^molmo-cleanup seed=\"7\"",
        r"^molmo-prompt-cleanup seed=\"7\"",
        r"^molmo-real-cleanup seed=\"7\"",
        r"^molmo-robot-visual seed=\"7\"",
        r"^molmo-agent-bridge seed=\"7\"",
        r"^molmo-agent-bridge-visual seed=\"7\"",
        r"^molmo-realworld-cleanup seeds=\"1 2 3\"",
        r"^molmo-realworld-agent-mcp seeds=\"1\"",
        r"^molmo-realworld-agent-dogfood-kit seed=\"7\"",
        r"^molmo-realworld-openclaw-dogfood-kit seed=\"7\"",
        r"^molmo-realworld-openclaw-visual-dogfood-kit seed=\"7\"",
        r"^molmo-realworld-raw-fpv seed=\"7\"",
    )
    for header in expected_headers:
        assert re.search(header, text, re.MULTILINE), f"missing recipe header: {header}"


def test_openclaw_visual_kit_uses_real_visual_backend_and_checker() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    recipe = re.search(
        r"^molmo-realworld-openclaw-visual-dogfood-kit[\s\S]*?(?=^# List task files)",
        text,
        re.MULTILINE,
    )
    assert recipe is not None
    body = recipe.group(0)
    for expected in (
        "--backend molmospaces_subprocess",
        "--policy openclaw_agent",
        "--include-robot",
        "--record-robot-views",
        "--require-openclaw-minimum",
        "--require-clean-agent-run",
        "--require-robot-views",
        "--require-advisory-scoring",
    ):
        assert expected in body


def test_realworld_gates_require_advisory_scoring() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    for recipe_name in (
        "molmo-realworld-cleanup",
        "molmo-realworld-agent-mcp",
        "molmo-realworld-agent-dogfood-kit",
        "molmo-realworld-openclaw-dogfood-kit",
        "molmo-realworld-openclaw-visual-dogfood-kit",
        "molmo-realworld-raw-fpv",
    ):
        recipe = re.search(
            rf"^{recipe_name}[\s\S]*?(?=^# |\Z)",
            text,
            re.MULTILINE,
        )
        assert recipe is not None, recipe_name
        assert "--require-advisory-scoring" in recipe.group(0), recipe_name


def test_raw_fpv_harness_uses_raw_mode_and_checker() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    recipe = re.search(
        r"^molmo-realworld-raw-fpv[\s\S]*?(?=^# List task files)",
        text,
        re.MULTILINE,
    )
    assert recipe is not None
    body = recipe.group(0)
    for expected in (
        "--backend molmospaces_subprocess",
        "--perception-mode raw_fpv_only",
        "--include-robot",
        "--record-robot-views",
        "--require-robot-views",
        "--require-raw-fpv-observations",
    ):
        assert expected in body
