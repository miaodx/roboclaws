from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_PATH = REPO_ROOT / "examples" / "molmospaces_realworld_cleanup.py"
CHECKER_PATH = REPO_ROOT / "scripts" / "check_molmo_realworld_cleanup_result.py"
SMOKE_PATH = REPO_ROOT / "scripts" / "run_molmo_realworld_agent_mcp_smoke.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_checker_accepts_single_realworld_run(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    data, path = checker._load_run_results(tmp_path / "run_result.json")[0]
    checker._assert_result(
        data,
        path.parent,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        min_generated_mess_count=5,
    )


def test_checker_rejects_too_small_generated_mess_set(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
            min_generated_mess_count=6,
        )


def test_checker_accepts_realworld_mcp_smoke_policy(tmp_path: Path) -> None:
    smoke = _load_module(SMOKE_PATH, "run_molmo_realworld_agent_mcp_smoke")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = smoke.run_smoke(output_dir=tmp_path, seed=7)

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        expect_policy="realworld_contract_smoke_agent",
        expect_mcp_server="molmo_cleanup_realworld",
        min_generated_mess_count=5,
    )


def test_checker_can_require_robot_view_report_artifacts(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)
    robot_views = tmp_path / "robot_views"
    robot_views.mkdir()
    for name in ("step.fpv.png", "step.chase.png", "step.map.png", "step.verify.png"):
        (robot_views / name).write_bytes(b"placeholder")
    report = tmp_path / "report.html"
    report.write_text(
        report.read_text(encoding="utf-8") + "\n<section><h2>Robot View Timeline</h2></section>",
        encoding="utf-8",
    )
    result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
    result["artifacts"]["robot_views"] = str(robot_views)
    result["robot_view_steps"] = [
        _robot_step("navigate_to_object observed_001"),
        _robot_step("pick observed_001"),
        _robot_step("navigate_to_receptacle refrigerator_01"),
        _robot_step("open_receptacle refrigerator_01"),
        _robot_step("place_inside observed_001"),
        _robot_step("place observed_002"),
    ]

    checker._assert_result(
        result,
        tmp_path,
        expect_task=None,
        expect_backend="api_semantic_synthetic",
        require_robot_views=True,
    )


def test_checker_rejects_agent_view_private_leak(tmp_path: Path) -> None:
    demo = _load_module(DEMO_PATH, "molmospaces_realworld_cleanup")
    checker = _load_module(CHECKER_PATH, "check_molmo_realworld_cleanup_result")

    result = demo.run_realworld_cleanup(output_dir=tmp_path, seed=7)
    result["agent_view"]["generated_mess_set"] = ["leak"]

    with pytest.raises(AssertionError):
        checker._assert_result(
            result,
            tmp_path,
            expect_task=None,
            expect_backend="api_semantic_synthetic",
        )


def _robot_step(action: str) -> dict[str, object]:
    return {
        "action": action,
        "room_outline_count": 1,
        "views": {
            "fpv": "robot_views/step.fpv.png",
            "chase": "robot_views/step.chase.png",
            "map": "robot_views/step.map.png",
            "verify": "robot_views/step.verify.png",
        },
        "focus": {
            "has_focus": True,
            "fpv_visibility": {"status": "ok"},
            "visibility": {"status": "ok"},
        },
    }
