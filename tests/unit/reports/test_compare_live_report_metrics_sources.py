from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPARE_SCRIPT = REPO_ROOT / "scripts" / "reports" / "compare_live_report_metrics.py"


def _load_compare_script():
    spec = importlib.util.spec_from_file_location(
        "compare_live_report_metrics_sources",
        COMPARE_SCRIPT,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            (
                r"report performance comparison manifest source must contain valid JSON object: "
                r".*comparison-manifest\.json"
            ),
        ),
        (
            "[]\n",
            (
                r"report performance comparison manifest source must contain a JSON object: "
                r".*comparison-manifest\.json"
            ),
        ),
    ],
)
def test_compare_manifest_rejects_bad_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    compare_script = _load_compare_script()
    manifest = tmp_path / "comparison-manifest.json"
    manifest.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        compare_script._compare_manifest(
            manifest,
            diagnostic=False,
            calibration=None,
        )


def test_compare_manifest_rejects_missing_source(tmp_path: Path) -> None:
    compare_script = _load_compare_script()
    manifest = tmp_path / "comparison-manifest.json"

    with pytest.raises(
        FileNotFoundError,
        match=(
            r"report performance comparison manifest source is missing: "
            r".*comparison-manifest\.json"
        ),
    ):
        compare_script._compare_manifest(
            manifest,
            diagnostic=False,
            calibration=None,
        )


def test_compare_manifest_still_requires_comparisons_list(tmp_path: Path) -> None:
    compare_script = _load_compare_script()
    manifest = tmp_path / "comparison-manifest.json"
    manifest.write_text('{"comparisons": {}}\n', encoding="utf-8")

    with pytest.raises(SystemExit, match="manifest must contain comparisons list"):
        compare_script._compare_manifest(
            manifest,
            diagnostic=False,
            calibration=None,
        )
