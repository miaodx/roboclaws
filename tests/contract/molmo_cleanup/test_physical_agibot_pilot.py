from __future__ import annotations

import json
from pathlib import Path

from roboclaws.molmo_cleanup.agibot_sdk_runner import (
    AGIBOT_SDK_RUNNER_BACKEND,
    BLOCKED_MANIPULATION_TOOLS,
    run_physical_agibot_cleanup_pilot,
)
from roboclaws.molmo_cleanup.artifact_report import (
    is_cleanup_run_result_artifact,
    rerender_cleanup_report_from_artifact_path,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPLETED_CONTEXT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "agibot_map_context.completed.json"


def test_physical_agibot_pilot_uses_sdk_runner_reports_without_movement(
    tmp_path: Path,
) -> None:
    context_path = tmp_path / "agibot_map_context.completed.json"
    context_path.write_text(json.dumps(_completed_context()), encoding="utf-8")

    run_result = run_physical_agibot_cleanup_pilot(
        run_dir=tmp_path / "run",
        context_json=context_path,
    )

    run_dir = tmp_path / "run"
    report_text = (run_dir / "report.html").read_text(encoding="utf-8")
    persisted = json.loads((run_dir / "run_result.json").read_text(encoding="utf-8"))
    runner = run_result["agibot_sdk_runner"]
    subphase_reports = runner["subphase_reports"]

    assert run_result["cleanup_profile"] == "real_robot_cleanup_v1"
    assert run_result["backend"] == AGIBOT_SDK_RUNNER_BACKEND
    assert run_result["backend_variant"] == "agibot_gdk"
    assert run_result["primitive_provenance"] == "blocked_capability"
    assert run_result["real_robot_readiness"]["status"] == (
        "physical_agibot_navigation_pilot_rehearsal"
    )
    assert run_result["real_robot_readiness"]["movement_enabled"] is False
    assert run_result["real_robot_readiness"]["physical_navigation_pilot"] is True
    assert run_result["real_robot_readiness"]["physical_cleanup_ready"] is False
    assert run_result["physical_agibot_pilot"]["navigation_attempt"]["navigation_status"] == (
        "dry_run_not_executed"
    )
    assert [
        item["tool"] for item in run_result["physical_agibot_pilot"]["blocked_manipulation_results"]
    ] == list(BLOCKED_MANIPULATION_TOOLS)
    assert [item["stage"] for item in subphase_reports] == [
        "agent_view_export",
        "observe",
        "navigate_waypoint",
    ]
    for item in subphase_reports:
        assert (run_dir / item["report"]).is_file()
        assert (run_dir / item["run_result"]).is_file()

    assert "AgiBot SDK Runner" in report_text
    assert "CLI backend boundary" in report_text
    assert "movement_enabled=false" in report_text
    assert persisted["semantic_substeps"] == []
    assert persisted["agibot_sdk_runner"]["gdk_imported_by_roboclaws"] is False
    assert is_cleanup_run_result_artifact(run_dir)
    assert rerender_cleanup_report_from_artifact_path(run_dir) == run_dir / "report.html"


def _completed_context() -> dict:
    return json.loads(COMPLETED_CONTEXT_FIXTURE.read_text(encoding="utf-8"))
