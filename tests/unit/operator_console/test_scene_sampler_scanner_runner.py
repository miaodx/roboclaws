from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "justfile").is_file():
            return parent
    raise AssertionError("could not locate repo root")


REPO_ROOT = _repo_root()
RUNNER_PATH = REPO_ROOT / "scripts" / "operator_console" / "run_scene_sampler_scanner_plan.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("scene_sampler_scanner_runner", RUNNER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_plan(path: Path, candidates: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "molmospaces_scene_sampler_scanner_execution_plan_v1",
                "sources": {
                    "ithor": {
                        "candidates": candidates,
                    }
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_worklist(
    path: Path,
    *,
    next_action: str = "run_scanner_plan_for_ready_candidates",
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "molmospaces_scene_sampler_next_flow_worklist_v1",
                "sources": {
                    "ithor": {
                        "scene_source": "ithor",
                        "next_action": next_action,
                        "next_scan_world_ids": ["molmospaces/ithor/1"],
                        "scanner_ready_world_ids": ["molmospaces/ithor/1"]
                        if next_action == "run_scanner_plan_for_ready_candidates"
                        else [],
                    }
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _candidate(*, scanner_status: str = "blocked_missing_resources") -> dict[str, object]:
    return {
        "scene_family": "ithor",
        "scene_split": "not_applicable",
        "scene_source": "ithor",
        "scene_index": 1,
        "world_id": "molmospaces/ithor/1",
        "scanner_status": scanner_status,
        "admission_status": "blocked",
        "readiness_status": "blocked",
        "lanes": [],
        "failure_class": "environment_blocked",
        "blocked_reason": "source assets missing",
        "selected_reason": "scanner_candidate_ready_for_product_smoke",
        "room_count": 4,
        "waypoint_count": 4,
        "category_provenance": "prepared_visual_label_manifest",
        "preview_statuses": {
            "fpv": "reviewable",
            "map": "reviewable",
            "chase": "reviewable",
            "topdown": "reviewable",
        },
        "passed_gates": ["preview_metadata", "public_room_count"],
        "required_gates": [
            "source_asset_available",
            "preview_metadata",
            "public_room_count",
            "public_waypoints",
            "trusted_category_provenance",
            "map_build_artifacts",
        ],
        "missing_gates": (
            ["source_asset_available"] if scanner_status != "ready_for_product_smoke" else []
        ),
        "missing_paths": ["/tmp/FloorPlan1_physics.xml"]
        if scanner_status != "ready_for_product_smoke"
        else [],
        "candidate_file": {
            "exists": scanner_status == "ready_for_product_smoke",
            "path": "/tmp/FloorPlan1_physics.xml",
        },
        "primary_path": "/tmp/FloorPlan1_physics.xml",
        "path_status": "available",
        "preview_command": (
            ".venv/bin/python scripts/operator_console/render_scene_previews.py "
            "--world molmospaces/ithor/1"
        ),
        "map_build_product_smoke_command": (
            "just run::surface surface=household-world world=molmospaces/ithor/1 "
            "backend=mujoco preset=map-build agent_engine=direct-runner "
            "evidence_lane=world-public-labels"
        ),
    }


def test_scanner_runner_skips_blocked_candidates_without_running_commands(tmp_path: Path) -> None:
    runner = _load_runner()
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "scanner_run.json"
    _write_plan(plan_path, [_candidate()])
    calls = []

    result = runner.run_scanner_plan(
        plan_path=plan_path,
        output_path=output_path,
        run_command=lambda *_args, **_kwargs: calls.append(_args),
    )

    assert result["schema"] == "molmospaces_scene_sampler_scanner_run_v1"
    assert result["status"] == "no_ready_candidates"
    assert result["skipped_candidate_count"] == 1
    assert result["sources"]["ithor"] == {
        "scene_source": "ithor",
        "status": "no_ready_candidates",
        "candidate_count": 1,
        "ready_candidate_count": 0,
        "executed_candidate_count": 0,
        "skipped_candidate_count": 1,
        "failed_candidate_count": 0,
        "world_ids": ["molmospaces/ithor/1"],
    }
    assert result["rows"][0]["status"] == "skipped_blocked_candidate"
    assert result["rows"][0]["scene_family"] == "ithor"
    assert result["rows"][0]["failure_class"] == "environment_blocked"
    assert result["rows"][0]["room_count"] == 4
    assert result["rows"][0]["waypoint_count"] == 4
    assert result["rows"][0]["category_provenance"] == "prepared_visual_label_manifest"
    assert result["rows"][0]["preview_statuses"]["fpv"] == "reviewable"
    assert result["rows"][0]["candidate_file"]["path"] == "/tmp/FloorPlan1_physics.xml"
    assert calls == []
    assert json.loads(output_path.read_text(encoding="utf-8")) == result


def test_scanner_runner_dry_run_records_ready_commands_without_execution(tmp_path: Path) -> None:
    runner = _load_runner()
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "scanner_run.json"
    _write_plan(plan_path, [_candidate(scanner_status="ready_for_product_smoke")])
    calls = []

    result = runner.run_scanner_plan(
        plan_path=plan_path,
        output_path=output_path,
        dry_run=True,
        run_command=lambda *_args, **_kwargs: calls.append(_args),
    )

    assert result["status"] == "dry_run"
    assert result["ready_candidate_count"] == 1
    assert result["sources"]["ithor"]["status"] == "ready_not_executed"
    assert result["sources"]["ithor"]["ready_candidate_count"] == 1
    assert result["sources"]["ithor"]["executed_candidate_count"] == 0
    assert [item["name"] for item in result["rows"][0]["commands"]] == [
        "preview",
        "map_build_product_smoke",
    ]
    assert {item["status"] for item in result["rows"][0]["commands"]} == {"dry_run"}
    assert calls == []


def test_scanner_runner_records_worklist_alignment(tmp_path: Path) -> None:
    runner = _load_runner()
    plan_path = tmp_path / "plan.json"
    worklist_path = tmp_path / "next_flow_worklist.json"
    output_path = tmp_path / "scanner_run.json"
    _write_plan(plan_path, [_candidate(scanner_status="ready_for_product_smoke")])
    _write_worklist(worklist_path)

    result = runner.run_scanner_plan(
        plan_path=plan_path,
        worklist_path=worklist_path,
        output_path=output_path,
        dry_run=True,
    )

    alignment = result["worklist_alignment"]
    assert alignment["schema"] == "molmospaces_scene_sampler_runner_worklist_alignment_v1"
    assert alignment["runner"] == "scanner"
    assert alignment["status"] == "aligned"
    assert alignment["sources"]["ithor"]["status"] == "aligned"
    assert alignment["sources"]["ithor"]["expected_world_ids"] == ["molmospaces/ithor/1"]
    assert alignment["sources"]["ithor"]["run_world_ids"] == ["molmospaces/ithor/1"]


def test_scanner_runner_marks_run_before_worklist_action(tmp_path: Path) -> None:
    runner = _load_runner()
    plan_path = tmp_path / "plan.json"
    worklist_path = tmp_path / "next_flow_worklist.json"
    output_path = tmp_path / "scanner_run.json"
    _write_plan(plan_path, [_candidate(scanner_status="blocked_missing_resources")])
    _write_worklist(worklist_path, next_action="run_manual_source_prep")

    result = runner.run_scanner_plan(
        plan_path=plan_path,
        worklist_path=worklist_path,
        output_path=output_path,
    )

    alignment = result["worklist_alignment"]
    assert alignment["status"] == "ran_before_worklist_action"
    assert alignment["sources"]["ithor"]["status"] == "ran_before_worklist_action"
    assert alignment["sources"]["ithor"]["worklist_next_action"] == "run_manual_source_prep"


def test_scanner_runner_executes_ready_preview_then_map_build(tmp_path: Path) -> None:
    runner = _load_runner()
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "scanner_run.json"
    _write_plan(plan_path, [_candidate(scanner_status="ready_for_product_smoke")])
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    result = runner.run_scanner_plan(
        plan_path=plan_path,
        output_path=output_path,
        run_command=fake_run,
    )

    assert result["status"] == "success"
    assert result["executed_candidate_count"] == 1
    assert result["sources"]["ithor"]["status"] == "executed"
    assert result["sources"]["ithor"]["executed_candidate_count"] == 1
    assert result["sources"]["ithor"]["failed_candidate_count"] == 0
    assert result["rows"][0]["status"] == "passed"
    assert [item["name"] for item in result["rows"][0]["commands"]] == [
        "preview",
        "map_build_product_smoke",
    ]
    assert len(calls) == 2
    assert calls[0][0][:2] == [
        ".venv/bin/python",
        "scripts/operator_console/render_scene_previews.py",
    ]
    assert calls[1][0][:2] == ["just", "run::surface"]


def test_scanner_runner_source_summary_records_failures(tmp_path: Path) -> None:
    runner = _load_runner()
    plan_path = tmp_path / "plan.json"
    output_path = tmp_path / "scanner_run.json"
    _write_plan(plan_path, [_candidate(scanner_status="ready_for_product_smoke")])

    def fake_run(argv, **kwargs):
        return SimpleNamespace(returncode=17, stdout="", stderr="preview failed")

    result = runner.run_scanner_plan(
        plan_path=plan_path,
        output_path=output_path,
        run_command=fake_run,
    )

    assert result["status"] == "failed"
    assert result["failed_candidate_count"] == 1
    assert result["sources"]["ithor"]["status"] == "failed"
    assert result["sources"]["ithor"]["executed_candidate_count"] == 1
    assert result["sources"]["ithor"]["failed_candidate_count"] == 1
    assert result["rows"][0]["failed_command"] == "preview"
