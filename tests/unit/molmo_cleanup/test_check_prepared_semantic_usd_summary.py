from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.isaac_lab_cleanup.check_prepared_semantic_usd_summary import (
    assert_prepared_semantic_usd_summary_ready,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "check_prepared_semantic_usd_summary.py"


def test_prepared_semantic_usd_summary_ready() -> None:
    assert_prepared_semantic_usd_summary_ready(
        {
            "status": "ready",
            "matched_entry_count": 2,
            "labeled_entry_count": 2,
            "renderable_labeled_prim_count": 8,
            "scene_metadata_copied": True,
        }
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "partial"),
        ("matched_entry_count", 0),
        ("labeled_entry_count", 0),
        ("renderable_labeled_prim_count", 0),
        ("scene_metadata_copied", False),
    ],
)
def test_prepared_semantic_usd_summary_rejects_incomplete_evidence(
    field: str,
    value: object,
) -> None:
    summary = {
        "status": "ready",
        "matched_entry_count": 2,
        "labeled_entry_count": 2,
        "renderable_labeled_prim_count": 8,
        "scene_metadata_copied": True,
    }
    summary[field] = value

    with pytest.raises(AssertionError):
        assert_prepared_semantic_usd_summary_ready(summary)


@pytest.mark.parametrize(
    ("source", "message"),
    (
        ("{not-json\n", "prepared semantic USD summary must contain valid JSON object"),
        ("[]\n", "prepared semantic USD summary must contain a JSON object"),
    ),
)
def test_prepared_semantic_usd_summary_cli_rejects_bad_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(source, encoding="utf-8")

    completed = _run_checker(summary_path)

    assert completed.returncode == 2
    assert message in completed.stderr
    assert str(summary_path) in completed.stderr


def test_prepared_semantic_usd_summary_cli_rejects_missing_source(tmp_path: Path) -> None:
    summary_path = tmp_path / "missing_summary.json"

    completed = _run_checker(summary_path)

    assert completed.returncode == 2
    assert "prepared semantic USD summary missing" in completed.stderr
    assert str(summary_path) in completed.stderr


def _run_checker(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
    )
