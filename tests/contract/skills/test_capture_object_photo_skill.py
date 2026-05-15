from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "capture-object-photo" / "scripts" / "plan_capture_route.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("plan_capture_route", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capture_route_plan_sorts_labels_and_preserves_tool_boundary() -> None:
    module = _load_script()
    payload = {
        "objects": [
            {"objectId": "Chair|2", "objectType": "Chair", "distance_xz": 3.0},
            {"objectId": "Sofa|1", "objectType": "Sofa", "distance_xz": 1.2},
            {"objectId": "ArmChair|1", "objectType": "ArmChair", "distance_xz": 2.4},
            {"objectId": "Table|1", "objectType": "DiningTable", "distance_xz": 0.5},
        ]
    }

    plan = module.build_capture_plan(payload, filter_types="Sofa,Chair,ArmChair")

    assert plan["schema"] == "roboclaws_capture_object_photo_plan_v1"
    assert plan["profile"] == "ai2thor_navigation_v1"
    assert plan["privileged_tools_used"] == ["scene_objects", "goto"]
    assert plan["canonical_tools_used"] == ["observe_archived", "done"]
    assert [target["label"] for target in plan["targets"]] == [
        "sofa-1",
        "armchair-1",
        "chair-1",
    ]
    assert [target["object_id"] for target in plan["targets"]] == [
        "Sofa|1",
        "ArmChair|1",
        "Chair|2",
    ]
    assert plan["targets"][0]["actions"][0] == {
        "tool": "goto",
        "classification": "privileged_tool",
        "arguments": {"object_id": "Sofa|1", "distance": 1.0, "face": True},
    }
    assert plan["targets"][0]["actions"][1] == {
        "tool": "observe_archived",
        "classification": "canonical",
        "arguments": {"label": "sofa-1"},
    }


def test_capture_route_cli_reads_stdin_and_emits_json() -> None:
    payload = {"objects": [{"objectId": "Chair|1", "objectType": "Chair", "distance_xz": 1.0}]}

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            "-",
            "--filter-types",
            "Chair",
            "--standoff",
            "1.5",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )

    plan = json.loads(result.stdout)
    assert plan["target_count"] == 1
    assert plan["targets"][0]["label"] == "chair-1"
    assert plan["targets"][0]["actions"][0]["arguments"]["distance"] == 1.5
    assert plan["targets"][0]["actions"][1]["tool"] == "observe_archived"


def test_capture_route_can_opt_into_inline_observe_for_vision_models() -> None:
    module = _load_script()
    payload = {"objects": [{"objectId": "Sofa|1", "objectType": "Sofa", "distance_xz": 1.0}]}

    plan = module.build_capture_plan(payload, filter_types="Sofa", capture_tool="observe")

    assert plan["canonical_tools_used"] == ["observe", "done"]
    assert plan["optional_tools"] == ["observe_archived", "move"]
    assert plan["targets"][0]["actions"][1] == {
        "tool": "observe",
        "classification": "canonical",
        "arguments": {"label": "sofa-1"},
    }
