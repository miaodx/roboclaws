from __future__ import annotations

from pathlib import Path

from roboclaws.household.agibot_contract_rehearsal import (
    run_molmospaces_agibot_prehardware_rehearsal,
)


def test_map_evidence_refresh_report_surfaces_sim_boundary_and_runtime_map(
    tmp_path: Path,
) -> None:
    prompt = (
        "基于当前已有 Runtime Metric Map，自主选择 3 个最值得复核的 public semantic anchor "
        "或 inspection waypoint。"
    )
    run_dir = tmp_path / "map-evidence-refresh"

    run_molmospaces_agibot_prehardware_rehearsal(
        run_dir=run_dir,
        intent="map-build",
        profile="camera-grounded-labels",
        task_prompt=prompt,
        generated_mess_count=5,
        camera_labeler="sim",
    )

    report_text = (run_dir / "report.html").read_text(encoding="utf-8")

    assert "Map Evidence Refresh Summary" in report_text
    assert "The run is not agent-driven" in report_text
    assert "direct runtime-map sweep evidence, not autonomous target choice" in report_text
    assert "Public anchors" in report_text
    assert "Observed handles" in report_text
    assert "Raw observations" in report_text
    assert "Generated candidates" in report_text
    assert "physical robot=no" in report_text
    assert prompt in report_text
