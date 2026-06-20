from __future__ import annotations

from pathlib import Path

import pytest

from roboclaws.evals.live_artifacts import load_live_eval_json


def test_load_live_eval_json_missing_source_stays_empty(tmp_path: Path) -> None:
    assert load_live_eval_json(tmp_path / "missing.json") == {}


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            r"invalid live eval JSON artifact source must contain valid JSON object: "
            r".*run_result\.json",
        ),
        (
            "[]\n",
            r"invalid live eval JSON artifact source must contain a JSON object: "
            r".*run_result\.json",
        ),
    ],
)
def test_load_live_eval_json_rejects_bad_present_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    artifact = tmp_path / "run_result.json"
    artifact.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_live_eval_json(artifact)


def test_load_live_eval_json_reads_object_source(tmp_path: Path) -> None:
    artifact = tmp_path / "run_result.json"
    artifact.write_text('{"status": "passed"}\n', encoding="utf-8")

    assert load_live_eval_json(artifact) == {"status": "passed"}
