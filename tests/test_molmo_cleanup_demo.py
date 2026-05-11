from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from roboclaws.molmo_cleanup.semantic_timeline import (
    CANONICAL_INSIDE_CLEANUP_PHASES,
    CURRENT_CONTRACT_SEMANTIC_LOOP_VARIANT,
    NAVIGATE_TO_OBJECT_PHASE,
    OBJECT_DONE_PHASE,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PATH = REPO_ROOT / "examples" / "molmospaces_cleanup_demo.py"


def _load_demo_module():
    spec = importlib.util.spec_from_file_location("molmospaces_cleanup_demo", DEMO_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_molmospaces_cleanup_demo_writes_success_artifacts(tmp_path: Path) -> None:
    demo = _load_demo_module()

    result = demo.run_demo(output_dir=tmp_path, seed=7, restore_count=5)

    run_result = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))
    trace_lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()

    assert result["cleanup_status"] == "success"
    assert result["backend"] == "api_semantic_synthetic"
    assert run_result["primitive_provenance"] == "api_semantic"
    assert run_result["planner"] == "scripted_reference"
    assert run_result["planner_uses_private_manifest"] is True
    assert run_result["score"]["restored_count"] == 5
    assert run_result["score"]["semantic_acceptability"]["accepted_count"] == 5
    assert run_result["semantic_loop_variant"] == CURRENT_CONTRACT_SEMANTIC_LOOP_VARIANT
    assert run_result["semantic_substeps"][0]["steps"][0]["phase"] == NAVIGATE_TO_OBJECT_PHASE
    assert any(f'"tool": "{NAVIGATE_TO_OBJECT_PHASE}"' in line for line in trace_lines)
    assert (tmp_path / "scenario.json").is_file()
    assert (tmp_path / "private_manifest.json").is_file()
    assert (tmp_path / "before.png").is_file()
    assert (tmp_path / "after.png").is_file()
    assert (tmp_path / "report.html").is_file()
    assert any('"tool": "place"' in line and '"event": "response"' in line for line in trace_lines)


def test_molmospaces_cleanup_demo_can_exercise_partial_failure(tmp_path: Path) -> None:
    demo = _load_demo_module()

    result = demo.run_demo(output_dir=tmp_path, seed=7, restore_count=2)

    assert result["cleanup_status"] == "partial_success"
    assert result["score"]["restored_count"] == 2


def test_molmospaces_cleanup_demo_runs_public_prompt_planner(tmp_path: Path) -> None:
    demo = _load_demo_module()

    result = demo.run_demo(
        output_dir=tmp_path,
        seed=7,
        planner="public_heuristic",
        task_prompt="帮我整理这个房间",
    )

    trace_lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()

    assert result["cleanup_status"] == "success"
    assert result["backend"] == "api_semantic_synthetic"
    assert result["task_prompt"] == "帮我整理这个房间"
    assert result["planner"] == "public_heuristic"
    assert result["planner_uses_private_manifest"] is False
    assert result["score"]["restored_count"] == 5
    assert result["score"]["semantic_acceptability"]["accepted_count"] == 5
    fridge_steps = [
        item
        for item in result["semantic_substeps"]
        if item["target_receptacle_category"] == "Fridge"
    ]
    assert fridge_steps
    assert [step["phase"] for step in fridge_steps[0]["steps"]] == [
        *CANONICAL_INSIDE_CLEANUP_PHASES,
        OBJECT_DONE_PHASE,
    ]
    assert result["final_containment"]["apple_01"]["location_relation"] == "inside"
    assert {action["object_id"] for action in result["cleanup_plan"]} == {
        "mug_01",
        "book_01",
        "towel_01",
        "apple_01",
        "toy_car_01",
    }
    assert any('"tool": "scene_objects"' in line for line in trace_lines)
