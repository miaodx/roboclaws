from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER = REPO_ROOT / "scripts" / "visual_grounding" / "check_visual_grounding_benchmark_result.py"


def test_visual_grounding_checker_rejects_malformed_result_source(tmp_path: Path) -> None:
    result_path = tmp_path / "visual_grounding_benchmark_result.json"
    result_path.write_text("{not json", encoding="utf-8")

    result = _run_checker(tmp_path)

    assert result.returncode == 1
    assert "error: JSON file must contain valid JSON object" in result.stderr
    assert "visual_grounding_benchmark_result.json" in result.stderr
    assert "Traceback" not in result.stderr


def test_visual_grounding_checker_rejects_non_object_result_source(tmp_path: Path) -> None:
    result_path = tmp_path / "visual_grounding_benchmark_result.json"
    result_path.write_text("[]", encoding="utf-8")

    result = _run_checker(tmp_path)

    assert result.returncode == 1
    assert "error: JSON file must contain a JSON object" in result.stderr
    assert "visual_grounding_benchmark_result.json" in result.stderr
    assert "Traceback" not in result.stderr


def test_visual_grounding_checker_rejects_malformed_predictions_source(tmp_path: Path) -> None:
    _write_minimal_visual_grounding_checker_sources(tmp_path, predictions_text="{not json\n")

    result = _run_checker(tmp_path)

    assert result.returncode == 1
    assert "error: JSONL row must contain valid JSON object" in result.stderr
    assert "visual_grounding_predictions.jsonl:1" in result.stderr
    assert "Traceback" not in result.stderr


def test_visual_grounding_checker_rejects_non_object_predictions_source(tmp_path: Path) -> None:
    _write_minimal_visual_grounding_checker_sources(tmp_path, predictions_text="[]\n")

    result = _run_checker(tmp_path)

    assert result.returncode == 1
    assert "error: JSONL row must contain a JSON object" in result.stderr
    assert "visual_grounding_predictions.jsonl:1" in result.stderr
    assert "Traceback" not in result.stderr


def _run_checker(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def _write_minimal_visual_grounding_checker_sources(
    output_dir: Path,
    *,
    predictions_text: str,
) -> None:
    (output_dir / "visual_grounding_benchmark_result.json").write_text(
        json.dumps(
            {
                "schema": "visual_grounding_benchmark_result_v1",
                "corpus": {"private_label_details_included": False},
                "pipelines": [
                    {
                        "benchmark_row_id": "grounding-dino",
                        "pipeline_id": "grounding-dino",
                    }
                ],
                "family_sweep": [
                    {
                        "model_family": "grounding-dino",
                        "tested_config_count": 1,
                        "successful_config_count": 0,
                        "row_ids": ["grounding-dino"],
                        "successful_row_ids": [],
                        "size_tiers": ["tiny"],
                        "under_sampled": True,
                        "under_sampled_reason": "fixture",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "visual_grounding_benchmark_report.html").write_text(
        "<html><body>fixture</body></html>",
        encoding="utf-8",
    )
    (output_dir / "visual_grounding_predictions.jsonl").write_text(
        predictions_text,
        encoding="utf-8",
    )
