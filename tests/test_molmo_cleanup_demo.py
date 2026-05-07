from __future__ import annotations

import importlib.util
import json
from pathlib import Path

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
    assert run_result["primitive_provenance"] == "api_semantic"
    assert run_result["score"]["restored_count"] == 5
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
