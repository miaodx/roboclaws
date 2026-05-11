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
    )
    for header in expected_headers:
        assert re.search(header, text, re.MULTILINE), f"missing recipe header: {header}"
