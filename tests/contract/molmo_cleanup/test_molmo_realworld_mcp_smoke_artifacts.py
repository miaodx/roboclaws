from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from roboclaws.household.realworld_contract import REALWORLD_CONTRACT
from roboclaws.household.realworld_mcp_server import MCP_SERVER_NAME

REPO_ROOT = Path(__file__).resolve().parents[3]
SMOKE_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_molmo_realworld_agent_mcp_smoke.py"


def test_realworld_mcp_smoke_writes_agent_artifacts(tmp_path: Path) -> None:
    smoke = _load_smoke_module()

    run_result = smoke.run_smoke(output_dir=tmp_path, seed=7)
    trace_text = (tmp_path / "trace.jsonl").read_text(encoding="utf-8")
    report_text = (tmp_path / "report.html").read_text(encoding="utf-8")

    _assert_smoke_run_result(run_result)
    _assert_smoke_report_and_artifacts(tmp_path, trace_text=trace_text, report_text=report_text)


def _load_smoke_module() -> Any:
    spec = importlib.util.spec_from_file_location("run_molmo_realworld_agent_mcp_smoke", SMOKE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _assert_smoke_run_result(run_result: dict[str, Any]) -> None:
    assert run_result["contract"] == REALWORLD_CONTRACT
    assert run_result["adr_0003_satisfied"] is True
    assert run_result["agent_driven"] is True
    assert run_result["policy"] == "realworld_contract_smoke_agent"
    assert run_result["policy_uses_private_truth"] is False
    assert run_result["planner_uses_private_manifest"] is False
    assert run_result["mcp_server"] == MCP_SERVER_NAME
    assert run_result["generated_mess_count"] == 5
    assert run_result["semantic_substeps"]
    assert run_result["tool_event_counts"]["metric_map:request"] == 1
    assert "static_fixture_projection:request" not in run_result["tool_event_counts"]
    assert run_result["tool_event_counts"]["observe:request"] >= 1
    assert run_result["agent_diagnostics"]["premature_done"] is False
    assert run_result["agent_diagnostics"]["premature_done_source"] == "sweep_coverage_rate"
    assert run_result["agent_diagnostics"]["semantic_order_errors"] == 0
    assert run_result["advisory_evaluation"]["authoritative"] is False
    assert run_result["advisory_evaluation"]["object_reviews"]
    assert run_result["agent_view"]["observed_objects"]
    assert run_result["cleanup_policy_trace"]["loop_style"] == "interleaved_cleanup_loop"
    assert run_result["cleanup_policy_trace"]["first_cleanup_before_full_survey"] is True
    assert run_result["cleanup_policy_trace"]["post_place_observe_complete"] is True
    assert run_result["real_robot_readiness"]["schema"] == "real_robot_readiness_v1"
    assert run_result["real_robot_readiness"]["semantic_navigation_only"] is True
    assert run_result["real_robot_readiness"]["map_bundle_snapshot_present"] is True
    assert "planner_object_id" not in str(run_result["agent_view"])
    assert run_result["planner_proof_requests"]["schema"] == "planner_cleanup_proof_requests_v1"
    assert run_result["planner_proof_requests"]["agent_view_exposed"] is False
    assert run_result["artifacts"]["planner_proof_requests"].endswith("planner_proof_requests.json")
    assert run_result["nav2_map_bundle"]["snapshot_complete"] is True


def _assert_smoke_report_and_artifacts(
    output_dir: Path, *, trace_text: str, report_text: str
) -> None:
    assert "Planner Proof Requests" in report_text
    assert "Waypoint Honesty & Cleanup Loop" in report_text
    assert "Real-Robot Readiness" in report_text
    assert "Base Navigation Map Preview" in report_text
    assert "Nav2 Map Bundle" in report_text
    assert "map_bundle/map.yaml" in report_text
    assert "report_only_simulation_view" in report_text
    assert "metric_map" in trace_text
    assert '"tool": "scene_objects"' not in trace_text
    assert "Agent View" in report_text
    assert "Private Evaluation" in report_text
    assert (output_dir / "agent_view.json").is_file()
    assert (output_dir / "private_evaluation.json").is_file()
    assert (output_dir / "advisory_evaluation.json").is_file()
    assert (output_dir / "planner_proof_requests.json").is_file()
    assert (output_dir / "map_bundle" / "map.yaml").is_file()
    assert (output_dir / "map_bundle" / "map.pgm").is_file()
    assert (output_dir / "map_bundle" / "semantics.json").is_file()
    assert (output_dir / "map_bundle" / "preview.png").is_file()
