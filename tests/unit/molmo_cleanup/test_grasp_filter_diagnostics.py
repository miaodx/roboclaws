from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from roboclaws.household import grasp_filter_diagnostics as diagnostics
from roboclaws.household.grasp_filter_diagnostics import (
    GRASP_FILTER_DIAGNOSTICS_SCHEMA,
    run_grasp_filter_diagnostics,
)
from roboclaws.household.report import render_grasp_filter_diagnostics_report


def test_filter_diagnostics_dry_run_builds_pipeline_and_report(tmp_path: Path) -> None:
    result = run_grasp_filter_diagnostics(
        generation_preflight=_generation_preflight(tmp_path),
        output_dir=tmp_path / "out",
        molmospaces_python=Path("/tmp/molmo/.venv/bin/python"),
        dry_run=True,
    )

    assert result["schema"] == GRASP_FILTER_DIAGNOSTICS_SCHEMA
    assert result["status"] == "dry_run"
    assert result["object_name"] == "Bread_1"
    assert len(result["pipeline"]["commands"]) == 4
    assert len(result["variants"]) == 3
    assert result["variants"][0]["classification"] == "not_run"

    report = render_grasp_filter_diagnostics_report(output_dir=tmp_path / "out", result=result)
    text = report.read_text(encoding="utf-8")
    assert "MolmoSpaces Grasp Filter Diagnostics" in text
    assert "Diagnostic Artifacts" in text
    assert "Filter Variants" in text


def test_filter_diagnostics_reports_zero_success_variants(tmp_path: Path, monkeypatch) -> None:
    candidate = tmp_path / "Bread_1_grasps.json"
    candidate.write_text(json.dumps(_candidate_payload()), encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = "Saved 0 successful grasps"
        stderr = ""

    def fake_run(command, **_kwargs):
        grasps_path = Path(command[command.index("--grasps_path") + 1])
        np.savez(grasps_path.with_name(grasps_path.stem + "_filtered.npz"), transforms=[])
        return Completed()

    monkeypatch.setattr(diagnostics.subprocess, "run", fake_run)

    result = run_grasp_filter_diagnostics(
        generation_preflight=_generation_preflight(tmp_path),
        output_dir=tmp_path / "out",
        molmospaces_python=Path("/tmp/molmo/.venv/bin/python"),
        candidate_grasps_path=candidate,
        sample_size=2,
        dry_run=False,
    )

    subset = json.loads(Path(result["candidate_subset"]["subset_path"]).read_text())
    assert result["status"] == "blocked"
    assert result["candidate_subset"]["subset_count"] == 2
    assert subset["quality_antipodal"] == [0.9, 0.2]
    assert {variant["classification"] for variant in result["variants"]} == {"zero_success"}
    assert result["blockers"][0]["code"] == "all_filter_variants_zero_success"


def test_filter_diagnostics_ready_when_variant_generates_transform(
    tmp_path: Path, monkeypatch
) -> None:
    candidate = tmp_path / "Bread_1_grasps.json"
    candidate.write_text(json.dumps(_candidate_payload()), encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **_kwargs):
        grasps_path = Path(command[command.index("--grasps_path") + 1])
        output = grasps_path.with_name(grasps_path.stem + "_filtered.npz")
        count = 1 if "initial_contact" in grasps_path.name else 0
        np.savez(output, transforms=np.zeros((count, 4, 4)))
        return Completed()

    monkeypatch.setattr(diagnostics.subprocess, "run", fake_run)

    result = run_grasp_filter_diagnostics(
        generation_preflight=_generation_preflight(tmp_path),
        output_dir=tmp_path / "out",
        molmospaces_python=Path("/tmp/molmo/.venv/bin/python"),
        candidate_grasps_path=candidate,
        sample_size=2,
        dry_run=False,
    )

    assert result["status"] == "ready"
    assert result["successful_variant_count"] == 1
    assert result["variants"][0]["classification"] == "success"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not-json\n", "candidate grasp JSON source must contain valid JSON object"),
        ("[]\n", "candidate grasp JSON source must contain a JSON object"),
    ],
)
def test_filter_diagnostics_rejects_malformed_candidate_grasp_source(
    tmp_path: Path, content: str, message: str
) -> None:
    candidate = tmp_path / "Bread_1_grasps.json"
    candidate.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        run_grasp_filter_diagnostics(
            generation_preflight=_generation_preflight(tmp_path),
            output_dir=tmp_path / "out",
            molmospaces_python=Path("/tmp/molmo/.venv/bin/python"),
            candidate_grasps_path=candidate,
            sample_size=2,
            dry_run=False,
        )


def _candidate_payload() -> dict:
    transforms = []
    for idx in range(3):
        transform = np.eye(4)
        transform[0, 3] = idx
        transforms.append(transform.tolist())
    return {
        "transforms": transforms,
        "quality_antipodal": [0.1, 0.9, 0.2],
        "grasp_widths": [0.01, 0.02, 0.03],
        "contact_depths": [0.3, 0.7, 0.5],
    }


def _generation_preflight(tmp_path: Path) -> dict:
    working_dir = tmp_path / "molmospaces" / "molmo_spaces" / "grasp_generation"
    working_dir.mkdir(parents=True, exist_ok=True)
    xml = tmp_path / "Bread_1.xml"
    xml.write_text("<mujoco />", encoding="utf-8")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    return {
        "status": "ready",
        "molmospaces_python": "/tmp/molmo/.venv/bin/python",
        "working_dir": str(working_dir),
        "assets_dir": str(assets_dir),
        "assets": [
            {
                "asset_uid": "Bread_1",
                "objects_list_entry": {"name": "Bread_1", "xml": str(xml)},
            }
        ],
    }
