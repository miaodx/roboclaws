from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_openai_agents_agibot_map_build.py"


def test_agibot_sdk_map_build_server_arg_value_accepts_split_and_equals_forms() -> None:
    runner = _load_runner_module()

    assert (
        runner._server_arg_value(
            ["--evidence-lane", "camera-grounded-labels"],
            "--evidence-lane",
        )
        == "camera-grounded-labels"
    )
    assert (
        runner._server_arg_value(
            ["--camera-labeler=grounding-dino"],
            "--camera-labeler",
        )
        == "grounding-dino"
    )
    assert runner._server_arg_value([], "--missing") == ""


def test_agibot_sdk_map_build_run_result_reader_accepts_json_object(tmp_path: Path) -> None:
    runner = _load_runner_module()
    run_result_path = tmp_path / "run_result.json"
    run_result_path.write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")

    assert runner._read_agibot_map_build_run_result(run_result_path) == {"ok": True}


def test_agibot_sdk_map_build_run_result_reader_rejects_missing_source(tmp_path: Path) -> None:
    runner = _load_runner_module()

    with pytest.raises(FileNotFoundError, match="Agibot map-build run_result source is missing"):
        runner._read_agibot_map_build_run_result(tmp_path / "run_result.json")


def test_agibot_sdk_map_build_run_result_reader_rejects_malformed_json(tmp_path: Path) -> None:
    runner = _load_runner_module()
    run_result_path = tmp_path / "run_result.json"
    run_result_path.write_text("{not json", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Agibot map-build run_result source must contain valid JSON object",
    ):
        runner._read_agibot_map_build_run_result(run_result_path)


def test_agibot_sdk_map_build_run_result_reader_rejects_non_object_json(tmp_path: Path) -> None:
    runner = _load_runner_module()
    run_result_path = tmp_path / "run_result.json"
    run_result_path.write_text("[1, 2, 3]\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Agibot map-build run_result source must contain a JSON object",
    ):
        runner._read_agibot_map_build_run_result(run_result_path)


def test_agibot_sdk_map_build_runner_accepts_expected_result(tmp_path: Path) -> None:
    module = _load_runner_module()
    _write_run_result(
        tmp_path,
        {
            "mcp_server": module.MCP_SERVER_NAME,
            "backend_variant": "agibot_gdk",
            "agent_driven": True,
        },
    )
    runner = _make_runner(module, tmp_path)

    runner._check_result()


def test_agibot_sdk_map_build_runner_rejects_unexpected_mcp_server(tmp_path: Path) -> None:
    module = _load_runner_module()
    _write_run_result(
        tmp_path,
        {
            "mcp_server": "other",
            "backend_variant": "agibot_gdk",
            "agent_driven": True,
        },
    )
    runner = _make_runner(module, tmp_path)

    with pytest.raises(RuntimeError, match="run_result has unexpected mcp_server: other"):
        runner._check_result()


def test_agibot_sdk_map_build_runner_rejects_unexpected_backend_variant(
    tmp_path: Path,
) -> None:
    module = _load_runner_module()
    _write_run_result(
        tmp_path,
        {
            "mcp_server": module.MCP_SERVER_NAME,
            "backend_variant": "mujoco",
            "agent_driven": True,
        },
    )
    runner = _make_runner(module, tmp_path)

    with pytest.raises(RuntimeError, match="run_result has unexpected backend_variant: mujoco"):
        runner._check_result()


def test_agibot_sdk_map_build_runner_rejects_non_agent_driven_result(
    tmp_path: Path,
) -> None:
    module = _load_runner_module()
    _write_run_result(
        tmp_path,
        {
            "mcp_server": module.MCP_SERVER_NAME,
            "backend_variant": "agibot_gdk",
            "agent_driven": False,
        },
    )
    runner = _make_runner(module, tmp_path)

    with pytest.raises(RuntimeError, match="run_result is not marked agent_driven=true"):
        runner._check_result()


def _load_runner_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "run_live_openai_agents_agibot_map_build",
        RUNNER_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_runner(module: Any, run_dir: Path) -> Any:
    runner = object.__new__(module.LiveOpenAIAgentsAgibotMapBuildRunner)
    runner.run_dir = run_dir
    return runner


def _write_run_result(run_dir: Path, payload: dict[str, Any]) -> None:
    (run_dir / "run_result.json").write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
