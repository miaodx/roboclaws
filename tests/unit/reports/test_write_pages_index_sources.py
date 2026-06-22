from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WRITE_PAGES_INDEX_PATH = REPO_ROOT / "scripts" / "reports" / "write_pages_index.py"


def _load_write_pages_index():
    spec = importlib.util.spec_from_file_location(
        "write_pages_index_sources", WRITE_PAGES_INDEX_PATH
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
                r"Molmo live report manifest source must contain valid JSON object: "
                r".*live-report-manifest\.json"
            ),
        ),
        (
            "[]\n",
            (
                r"Molmo live report manifest source must contain a JSON object: "
                r".*live-report-manifest\.json"
            ),
        ),
    ],
)
def test_pages_index_rejects_bad_live_manifest_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    write_pages_index = _load_write_pages_index()
    manifest_path = tmp_path / "site" / "molmo" / "live" / "live-report-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        write_pages_index.write_index(tmp_path / "site", include_molmo_live=True)


def test_pages_index_missing_live_manifest_still_renders_placeholder(tmp_path: Path) -> None:
    write_pages_index = _load_write_pages_index()

    out = write_pages_index.write_index(tmp_path / "site", include_molmo_live=True)
    html = out.read_text(encoding="utf-8")

    assert "Household Reports" in html
    assert "No published household cleanup reports are available yet." in html
