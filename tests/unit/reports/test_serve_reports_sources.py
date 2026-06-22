from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVE_REPORTS_SCRIPT = REPO_ROOT / "scripts" / "reports" / "serve_reports.py"


def _load_serve_reports_script():
    spec = importlib.util.spec_from_file_location(
        "serve_reports_sources",
        SERVE_REPORTS_SCRIPT,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_report_server_run_summary_missing_source_stays_empty(tmp_path: Path) -> None:
    serve_reports = _load_serve_reports_script()

    assert serve_reports._run_summary(tmp_path / "missing_run_result.json") == {}


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            r"report server run result source must contain valid JSON object: .*run_result\.json",
        ),
        (
            "[]\n",
            r"report server run result source must contain a JSON object: .*run_result\.json",
        ),
    ],
)
def test_report_server_run_summary_rejects_bad_present_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    serve_reports = _load_serve_reports_script()
    run_result = tmp_path / "run_result.json"
    run_result.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        serve_reports._run_summary(run_result)
