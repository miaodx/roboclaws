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
RUNNER_PATH = REPO_ROOT / "scripts" / "operator_console" / "run_scene_sampler_source_prep.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("scene_sampler_source_prep_runner", RUNNER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_prep(path: Path, candidates: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "molmospaces_scene_sampler_source_prep_v1",
                "sources": {
                    "ithor": {
                        "install_candidates": candidates,
                    }
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_worklist(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "molmospaces_scene_sampler_next_flow_worklist_v1",
                "sources": {
                    "ithor": {
                        "scene_source": "ithor",
                        "next_action": "run_manual_source_prep",
                        "next_scan_world_ids": [
                            "molmospaces/ithor/1",
                            "molmospaces/ithor/2",
                        ],
                        "scanner_ready_world_ids": [],
                    }
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _candidate(scene_index: int = 1) -> dict[str, object]:
    return {
        "scene_source": "ithor",
        "scene_index": scene_index,
        "world_id": f"molmospaces/ithor/{scene_index}",
        "primary_path": f"/tmp/FloorPlan{scene_index}_physics.xml",
        "path_status": "available",
        "missing_paths": [f"/tmp/FloorPlan{scene_index}_physics.xml"],
        "install_command": (".venv/bin/python - <<'PY'\nprint('install scene')\nPY"),
    }


def test_source_prep_runner_dry_run_records_install_commands(tmp_path: Path) -> None:
    runner = _load_runner()
    prep_path = tmp_path / "source_prep.json"
    output_path = tmp_path / "source_prep_run.json"
    _write_prep(prep_path, [_candidate()])
    calls = []

    result = runner.run_source_prep(
        prep_path=prep_path,
        output_path=output_path,
        run_command=lambda *_args, **_kwargs: calls.append(_args),
    )

    assert result["schema"] == "molmospaces_scene_sampler_source_prep_run_v1"
    assert result["status"] == "dry_run"
    assert result["execute"] is False
    assert result["candidate_count"] == 1
    assert result["executed_candidate_count"] == 0
    assert result["sources"]["ithor"]["status"] == "dry_run_ready"
    assert result["rows"][0]["status"] == "dry_run_ready"
    assert result["rows"][0]["commands"][0]["status"] == "dry_run"
    assert calls == []
    assert json.loads(output_path.read_text(encoding="utf-8")) == result


def test_source_prep_runner_execute_runs_install_commands(tmp_path: Path) -> None:
    runner = _load_runner()
    prep_path = tmp_path / "source_prep.json"
    output_path = tmp_path / "source_prep_run.json"
    _write_prep(prep_path, [_candidate()])
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    result = runner.run_source_prep(
        prep_path=prep_path,
        output_path=output_path,
        execute=True,
        run_command=fake_run,
    )

    assert result["status"] == "success"
    assert result["executed_candidate_count"] == 1
    assert result["sources"]["ithor"]["status"] == "executed"
    assert result["rows"][0]["status"] == "passed"
    assert calls[0][0].startswith(".venv/bin/python")
    assert calls[0][1]["shell"] is True


def test_source_prep_runner_filters_by_world(tmp_path: Path) -> None:
    runner = _load_runner()
    prep_path = tmp_path / "source_prep.json"
    output_path = tmp_path / "source_prep_run.json"
    _write_prep(prep_path, [_candidate(1), _candidate(2)])

    result = runner.run_source_prep(
        prep_path=prep_path,
        output_path=output_path,
        worlds=("molmospaces/ithor/2",),
    )

    assert result["candidate_count"] == 1
    assert result["rows"][0]["world_id"] == "molmospaces/ithor/2"


def test_source_prep_runner_records_worklist_alignment(tmp_path: Path) -> None:
    runner = _load_runner()
    prep_path = tmp_path / "source_prep.json"
    worklist_path = tmp_path / "next_flow_worklist.json"
    output_path = tmp_path / "source_prep_run.json"
    _write_prep(prep_path, [_candidate(1), _candidate(2)])
    _write_worklist(worklist_path)

    result = runner.run_source_prep(
        prep_path=prep_path,
        worklist_path=worklist_path,
        output_path=output_path,
        sources=("ithor",),
    )

    alignment = result["worklist_alignment"]
    assert alignment["schema"] == "molmospaces_scene_sampler_runner_worklist_alignment_v1"
    assert alignment["runner"] == "source_prep"
    assert alignment["status"] == "aligned"
    assert alignment["sources"]["ithor"]["status"] == "aligned"
    assert alignment["sources"]["ithor"]["expected_world_ids"] == [
        "molmospaces/ithor/1",
        "molmospaces/ithor/2",
    ]
    assert alignment["sources"]["ithor"]["run_world_ids"] == [
        "molmospaces/ithor/1",
        "molmospaces/ithor/2",
    ]


def test_source_prep_runner_records_failures(tmp_path: Path) -> None:
    runner = _load_runner()
    prep_path = tmp_path / "source_prep.json"
    output_path = tmp_path / "source_prep_run.json"
    _write_prep(prep_path, [_candidate()])

    def fake_run(argv, **kwargs):
        return SimpleNamespace(returncode=17, stdout="", stderr="install failed")

    result = runner.run_source_prep(
        prep_path=prep_path,
        output_path=output_path,
        execute=True,
        run_command=fake_run,
    )

    assert result["status"] == "failed"
    assert result["failed_candidate_count"] == 1
    assert result["sources"]["ithor"]["status"] == "failed"
    assert result["rows"][0]["failed_command"] == "install_scene_assets"
