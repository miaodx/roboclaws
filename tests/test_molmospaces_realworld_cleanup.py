from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from roboclaws.molmo_cleanup.realworld_contract import REALWORLD_CONTRACT

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PATH = REPO_ROOT / "examples" / "molmospaces_realworld_cleanup.py"


def _load_demo_module():
    spec = importlib.util.spec_from_file_location("molmospaces_realworld_cleanup", DEMO_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_realworld_cleanup_demo_writes_public_private_artifacts(tmp_path: Path) -> None:
    demo = _load_demo_module()

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    trace_lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()

    assert result["cleanup_status"] == "success"
    assert result["contract"] == REALWORLD_CONTRACT
    assert result["adr_0003_satisfied"] is True
    assert run_result["policy"] == "deterministic_sweep_baseline"
    assert run_result["policy_uses_private_truth"] is False
    assert run_result["planner_uses_private_manifest"] is False
    assert run_result["fixture_hint_mode"] == "room_only"
    assert run_result["requested_generated_mess_count"] == 10
    assert run_result["generated_mess_count"] == 5
    assert run_result["mess_restoration_rate"] >= 0.70
    assert run_result["sweep_coverage_rate"] >= 0.90
    assert run_result["disturbance_count"] <= 2
    assert run_result["semantic_loop_variant"] == "navigate-pick-navigate-open-place"
    for item in run_result["semantic_substeps"]:
        phases = [step["phase"] for step in item["steps"]]
        assert phases[:3] == ["navigate_to_object", "pick", "navigate_to_receptacle"]
        assert phases[-1] in {"place", "place_inside"}
    assert run_result["agent_view"]["observed_objects"]
    assert "generated_mess_set" not in run_result["agent_view"]
    assert "acceptable_destination_sets" not in run_result["agent_view"]
    assert run_result["private_evaluation"]["generated_mess_set"]
    assert run_result["private_evaluation"]["requested_generated_mess_count"] == 10
    assert run_result["advisory_evaluation"]["authoritative"] is False
    assert run_result["advisory_evaluation"]["object_reviews"]
    assert (tmp_path / "agent_view.json").is_file()
    assert (tmp_path / "private_evaluation.json").is_file()
    assert (tmp_path / "advisory_evaluation.json").is_file()
    assert (tmp_path / "before.png").is_file()
    assert (tmp_path / "after.png").is_file()
    assert (tmp_path / "report.html").is_file()
    assert any('"tool": "metric_map"' in line for line in trace_lines)
    assert any('"tool": "observe"' in line for line in trace_lines)
    assert not any('"tool": "scene_objects"' in line for line in trace_lines)


def test_realworld_cleanup_report_separates_agent_view_and_private_eval(
    tmp_path: Path,
) -> None:
    demo = _load_demo_module()

    demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    report = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Agent View" in report
    assert "Private Evaluation" in report
    assert "Advisory Review" in report
    assert "Generated mess" in report
    assert "ADR-0003 real-world-style cleanup run" in report
