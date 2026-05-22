from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from roboclaws.molmo_cleanup.agibot_contract_rehearsal import (
    BLOCKED_MANIPULATION_TOOLS,
    CLEANUP_ACTION_CONFIDENCE_LAYER,
    CONFIDENCE_LAYER,
    EXECUTION_BACKEND,
    NAVIGATION_PROVENANCE,
    REHEARSAL_MODE_CLEANUP_ACTIONS,
    RUNTIME_FIXTURE,
    run_molmospaces_agibot_contract_rehearsal,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "molmo_cleanup" / ("run_molmospaces_agibot_contract_rehearsal.py")


def test_molmospaces_agibot_contract_rehearsal_writes_simulated_report(
    tmp_path: Path,
) -> None:
    sys.modules.pop("agibot_gdk", None)

    result = run_molmospaces_agibot_contract_rehearsal(run_dir=tmp_path / "run")

    run_dir = tmp_path / "run"
    run_result = json.loads((run_dir / "run_result.json").read_text(encoding="utf-8"))
    runtime_export = json.loads(
        (run_dir / "runtime" / "runtime_export.json").read_text(encoding="utf-8")
    )
    report_text = (run_dir / "report.html").read_text(encoding="utf-8")
    serialized = json.dumps(run_result, sort_keys=True)

    assert result["confidence_layer"] == CONFIDENCE_LAYER
    assert run_result["report_title"] == CONFIDENCE_LAYER
    assert run_result["cleanup_profile"] == "real_robot_cleanup_v1"
    assert run_result["simulated"] is True
    assert run_result["physical_robot"] is False
    assert run_result["execution_backend"] == EXECUTION_BACKEND
    assert run_result["navigation_backend"] == EXECUTION_BACKEND
    assert run_result["primitive_provenance"] == NAVIGATION_PROVENANCE
    assert run_result["agibot_sdk_runner"]["runtime"] == RUNTIME_FIXTURE
    assert run_result["agibot_sdk_runner"]["gdk_imported_by_roboclaws"] is False
    assert run_result["agibot_sdk_runner"]["real_movement_enabled"] is False
    assert run_result["molmospaces_agibot_contract_rehearsal"]["physical_robot"] is False
    assert run_result["molmospaces_scene"]["runtime"] == RUNTIME_FIXTURE
    assert run_result["molmospaces_scene"]["scene_source"] == "deterministic_fixture_projection"
    assert run_result["molmospaces_scene"]["scenario_id"] == "molmo-cleanup-default-7"
    assert runtime_export["simulated"] is True
    assert runtime_export["physical_robot"] is False
    assert runtime_export["observation"]["ok"] is True
    assert runtime_export["navigation"]["navigation_status"] == "succeeded"
    assert runtime_export["navigation"]["navigation_backend"] == EXECUTION_BACKEND
    assert [item["tool"] for item in runtime_export["blocked_manipulation_results"]] == list(
        BLOCKED_MANIPULATION_TOOLS
    )
    assert all(
        item["status"] == "blocked_capability"
        for item in runtime_export["blocked_manipulation_results"]
    )
    assert [item["stage"] for item in run_result["agibot_sdk_runner"]["subphase_reports"]] == [
        "agent_view_export",
        "observe",
        "navigate_waypoint",
        "blocked_manipulation",
    ]

    for relpath in (
        "preflight/agent_view.json",
        "preflight/metric_map.json",
        "preflight/fixture_hints.json",
        "preflight/scene_identity.json",
        "preflight/molmospaces_metric_map.png",
        "preflight/waypoint_sequence.json",
        "preflight/runner_task_input.json",
        "runtime/observation.json",
        "runtime/navigation.json",
        "runtime/blocked_manipulation.json",
        "runtime/runtime_export.json",
        "runtime/policy_observation.png",
        "subphases/01-agent-view/report.html",
        "subphases/02-observe/report.html",
        "subphases/03-navigate-waypoint/report.html",
        "subphases/04-blocked-manipulation/report.html",
    ):
        assert (run_dir / relpath).is_file(), relpath

    assert "MolmoSpaces Agibot Contract Rehearsal" in report_text
    assert "MolmoSpaces Scene &amp; Map" in report_text
    assert "deterministic_fixture_projection" in report_text
    assert "molmo-cleanup-default-7" in report_text
    assert "preflight/molmospaces_metric_map.png" in report_text
    assert "CI-safe fixture runtime" in report_text
    assert "AgiBot-Shaped Sim Evidence" in report_text
    assert "MolmoSpaces contract rehearsal" in report_text
    assert "not Agibot Map Visual Dry Run" in report_text
    assert "not Agibot SDK Dry Run" in report_text
    assert "semantic cleanup mock evidence" in report_text
    assert "real Agibot GDK execution" in report_text
    assert "blocked_capability" in report_text
    assert "pick, place, place_inside, open_receptacle, close_receptacle" in report_text
    assert "Raw FPV Observations" in report_text
    assert "No semantic cleanup actions recorded" in report_text
    assert "agibot_gdk_normal_navi" not in serialized
    assert "agibot_gdk_normal_navi" not in report_text
    assert "agibot_gdk" not in sys.modules


def test_molmospaces_agibot_contract_rehearsal_cli_runs_without_gdk(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "cli-run"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--runtime",
            RUNTIME_FIXTURE,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    summary = json.loads(completed.stdout)
    run_result = json.loads((run_dir / "run_result.json").read_text(encoding="utf-8"))

    assert summary["confidence_layer"] == CONFIDENCE_LAYER
    assert summary["simulated"] is True
    assert summary["physical_robot"] is False
    assert Path(summary["report"]).is_file()
    assert run_result["agibot_sdk_runner"]["gdk_imported_by_roboclaws"] is False
    assert run_result["execution_backend"] == EXECUTION_BACKEND
    assert "agibot_gdk_normal_navi" not in json.dumps(run_result, sort_keys=True)


def test_molmospaces_agibot_cleanup_action_rehearsal_records_simulated_substeps(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "cleanup-actions"

    result = run_molmospaces_agibot_contract_rehearsal(
        run_dir=run_dir,
        rehearsal_mode=REHEARSAL_MODE_CLEANUP_ACTIONS,
        cleanup_object_count=2,
    )

    run_result = json.loads((run_dir / "run_result.json").read_text(encoding="utf-8"))
    runtime_export = json.loads(
        (run_dir / "runtime" / "runtime_export.json").read_text(encoding="utf-8")
    )
    cleanup_actions = json.loads(
        (run_dir / "runtime" / "cleanup_actions.json").read_text(encoding="utf-8")
    )
    report_text = (run_dir / "report.html").read_text(encoding="utf-8")
    serialized = json.dumps(run_result, sort_keys=True)

    assert result["report_title"] == CLEANUP_ACTION_CONFIDENCE_LAYER
    assert run_result["rehearsal_mode"] == REHEARSAL_MODE_CLEANUP_ACTIONS
    assert run_result["simulated"] is True
    assert run_result["physical_robot"] is False
    assert run_result["execution_backend"] == EXECUTION_BACKEND
    assert run_result["primitive_provenance"] == "api_semantic"
    assert run_result["manipulation_evidence"]["planner_backed"] is False
    assert run_result["manipulation_evidence"]["physical_robot"] is False
    assert run_result["cleanup_primitive_evidence"]["planner_backed"] is False
    assert cleanup_actions["attempted_object_count"] == 2
    assert cleanup_actions["completed_object_count"] == 2
    assert runtime_export["rehearsal_mode"] == REHEARSAL_MODE_CLEANUP_ACTIONS
    assert runtime_export["attempted_object_count"] == 2
    assert runtime_export["completed_object_count"] == 2
    assert runtime_export["semantic_substeps"]

    phases = [
        step["phase"]
        for item in runtime_export["semantic_substeps"]
        for step in item.get("steps", [])
    ]
    assert "pick" in phases
    assert {"place", "place_inside"} & set(phases)
    assert run_result["final_locations"]
    for target in cleanup_actions["selected_targets"]:
        object_id = target["internal_object_id"]
        assert run_result["final_locations"][object_id] == target["target_receptacle_id"]

    assert (run_dir / "runtime" / "cleanup_actions.json").is_file()
    assert (run_dir / "subphases" / "04-cleanup-actions" / "report.html").is_file()
    assert CLEANUP_ACTION_CONFIDENCE_LAYER in report_text
    assert "api_semantic" in report_text
    assert "No semantic cleanup actions recorded" not in report_text
    assert "agibot_gdk_normal_navi" not in serialized
    assert "agibot_gdk_normal_navi" not in report_text
