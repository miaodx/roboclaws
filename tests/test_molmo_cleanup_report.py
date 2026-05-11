from __future__ import annotations

from pathlib import Path

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.report import render_cleanup_report, write_state_snapshot
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.scoring import score_cleanup


def test_cleanup_report_renders_score_moves_and_provenance(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    final_locations = scenario.object_locations()
    final_locations.update({"mug_01": "sink_01", "book_01": "bookshelf_01"})
    score = score_cleanup(final_locations, scenario.private_manifest)
    before = write_state_snapshot(
        scenario,
        scenario.object_locations(),
        tmp_path / "before.png",
        title="Before",
    )
    after = write_state_snapshot(scenario, final_locations, tmp_path / "after.png", title="After")
    run_result = {
        "cleanup_status": score.status,
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "score": score.to_dict(),
    }
    trace_events = [
        {
            "tool": "place",
            "event": "response",
            "response": {
                "ok": True,
                "object_id": "mug_01",
                "receptacle_id": "sink_01",
                "primitive_provenance": API_SEMANTIC_PROVENANCE,
            },
        }
    ]

    report_path = render_cleanup_report(
        run_dir=tmp_path,
        scenario=scenario,
        run_result=run_result,
        trace_events=trace_events,
        before_snapshot=before,
        after_snapshot=after,
    )

    html = report_path.read_text(encoding="utf-8")
    assert "MolmoSpaces Cleanup Pilot" in html
    assert "api_semantic" in html
    assert "mug_01" in html
    assert "valid_receptacle_ids" not in html
    assert before.is_file()
    assert after.is_file()
