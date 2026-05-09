from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from roboclaws.molmo_cleanup.planner_proof_requests import (
    PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA,
    proof_request_selection_from_summary,
    proof_result_summary_from_commands,
)
from roboclaws.molmo_cleanup.report import render_planner_proof_bundle_runner_report

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER_PATH = REPO_ROOT / "scripts" / "check_molmo_planner_proof_bundle_runner_result.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_molmo_planner_proof_bundle_runner_result",
        CHECKER_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_checker_accepts_valid_runner_artifact(tmp_path: Path) -> None:
    checker = _load_checker()
    manifest = _write_runner_artifact(tmp_path)

    checker._assert_runner_result(manifest, tmp_path)


def test_checker_accepts_directory_path_via_main(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checker = _load_checker()
    _write_runner_artifact(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_molmo_planner_proof_bundle_runner_result.py", str(tmp_path)],
    )

    checker.main()

    assert "molmo-planner-proof-bundle-runner ok" in capsys.readouterr().out


def test_checker_accepts_paths_relative_to_current_working_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checker = _load_checker()
    monkeypatch.chdir(tmp_path)
    base = Path("bundle")
    base.mkdir()
    manifest = _write_runner_artifact(base)

    checker._assert_runner_result(manifest, base)


def test_checker_rejects_missing_report(tmp_path: Path) -> None:
    checker = _load_checker()
    manifest = _write_runner_artifact(tmp_path)
    (tmp_path / "report.html").unlink()

    with pytest.raises(AssertionError):
        checker._assert_runner_result(manifest, tmp_path)


def test_checker_rejects_missing_command_report_path(tmp_path: Path) -> None:
    checker = _load_checker()
    manifest = _runner_manifest(tmp_path)
    del manifest["commands"][0]["report"]
    _write_manifest_and_report(tmp_path, manifest)

    with pytest.raises(AssertionError):
        checker._assert_runner_result(manifest, tmp_path)


def test_checker_can_require_expected_proof_outputs(tmp_path: Path) -> None:
    checker = _load_checker()
    manifest = _write_runner_artifact(tmp_path)

    with pytest.raises(AssertionError):
        checker._assert_runner_result(manifest, tmp_path, require_proof_outputs=True)

    proof_dir = tmp_path / "proofs" / "001_observed_001_to_sink_01"
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "run_result.json").write_text("{}", encoding="utf-8")
    (proof_dir / "report.html").write_text("<h1>proof</h1>", encoding="utf-8")
    manifest["proof_result_summary"] = proof_result_summary_from_commands(manifest["commands"])
    _write_manifest_and_report(tmp_path, manifest)

    checker._assert_runner_result(manifest, tmp_path, require_proof_outputs=True)


def test_checker_accepts_generated_fallback_commands(tmp_path: Path) -> None:
    checker = _load_checker()
    manifest = _runner_manifest(tmp_path)
    manifest["ready_request_count"] = 0
    manifest["commands"][0]["request_id"] = "proof_001_fallback_01"
    manifest["commands"][0]["command"].extend(
        [
            "--cleanup-planner-object-id",
            "pickup/alt",
            "--cleanup-planner-target-receptacle-id",
            "sink/alt",
        ]
    )
    manifest["proof_request_selection"] = {
        "schema": "planner_cleanup_proof_request_selection_v1",
        "mode": "exclude_task_feasibility_blocked_with_fallbacks",
        "ready_request_count": 1,
        "selected_count": 1,
        "excluded_count": 1,
        "generated_fallback_request_count": 1,
        "fallback_required": False,
        "selected_request_ids": ["proof_001_fallback_01"],
        "selected_requests": [
            {
                "request_id": "proof_001_fallback_01",
                "request_type": "fallback_generated",
                "source_request_id": "proof_001",
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "prior_task_feasibility_status": "blocked",
            }
        ],
        "excluded_requests": [
            {
                "request_id": "proof_001",
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "reason": "prior_task_feasibility_blocked",
                "prior_task_feasibility_status": "blocked",
                "prior_blockers": [{"code": "HouseInvalidForTask"}],
            }
        ],
        "fallback_generation": {
            "schema": "planner_cleanup_proof_request_fallback_generation_v1",
            "enabled": True,
            "generated_request_count": 1,
            "filtered_alias_count": 1,
            "generated_requests": [
                {
                    "request_id": "proof_001_fallback_01",
                    "source_request_id": "proof_001",
                    "ready": True,
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "planner_probe_args": {
                        "--cleanup-planner-object-id": "pickup/alt",
                        "--cleanup-planner-target-receptacle-id": "sink/alt",
                    },
                    "fallback_request": {
                        "source_request_id": "proof_001",
                        "reason": "prior_task_feasibility_blocked",
                        "prior_blockers": [{"code": "HouseInvalidForTask"}],
                    },
                }
            ],
            "filtered_aliases": [
                {
                    "source_request_id": "proof_001",
                    "axis": "target",
                    "alias": "Sink|1|2",
                    "reason": "not_exact_scene_runtime_alias",
                }
            ],
        },
    }
    manifest["proof_result_summary"] = proof_result_summary_from_commands(manifest["commands"])
    (tmp_path / "proof_bundle_run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_planner_proof_bundle_runner_report(output_dir=tmp_path, manifest=manifest)

    checker._assert_runner_result(manifest, tmp_path)


def test_checker_requires_timeout_stage_evidence_in_report(tmp_path: Path) -> None:
    checker = _load_checker()
    manifest = _runner_manifest(tmp_path)
    proof_dir = tmp_path / "proofs" / "001_observed_001_to_sink_01"
    proof_dir.mkdir(parents=True)
    (proof_dir / "planner_probe_stdout.txt").write_text("stdout", encoding="utf-8")
    (proof_dir / "planner_probe_stderr.txt").write_text("stderr", encoding="utf-8")
    (proof_dir / "report.html").write_text("<h1>proof</h1>", encoding="utf-8")
    (proof_dir / "run_result.json").write_text(
        json.dumps(
            {
                "status": "blocked_capability",
                "artifacts": {
                    "stdout": "planner_probe_stdout.txt",
                    "stderr": "planner_probe_stderr.txt",
                },
                "manipulation_evidence": {
                    "execution_attempted": False,
                    "blockers": [{"code": "timeout", "message": "Probe exceeded 1.0s"}],
                    "last_worker_stage": "rby1m_config_import",
                    "worker_stage_events": [
                        {"elapsed_s": 0.1, "event": "worker_start", "stage": "worker_start"},
                        {
                            "elapsed_s": 3.2,
                            "event": "rby1m_config_import_start",
                            "stage": "rby1m_config_import",
                        },
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    _write_manifest_and_report(tmp_path, manifest)

    checker._assert_runner_result(manifest, tmp_path, require_proof_outputs=True)


def test_checker_accepts_visible_warmup_artifact(tmp_path: Path) -> None:
    checker = _load_checker()
    manifest = _runner_manifest(tmp_path)
    warmup_dir = tmp_path / "rby1m_curobo_warmup"
    manifest["warmup"] = {
        "kind": "rby1m_curobo_config_import",
        "output_dir": str(warmup_dir),
        "run_result": str(warmup_dir / "run_result.json"),
        "report": str(warmup_dir / "report.html"),
        "command": [
            "python",
            "probe.py",
            "--output-dir",
            str(warmup_dir),
            "--probe-mode",
            "config_import",
            "--torch-extensions-dir",
            str(tmp_path / "torch_extensions"),
        ],
    }
    _write_manifest_and_report(tmp_path, manifest)

    checker._assert_runner_result(manifest, tmp_path)

    with pytest.raises(AssertionError):
        checker._assert_runner_result(manifest, tmp_path, require_proof_outputs=True)

    warmup_dir.mkdir()
    (warmup_dir / "run_result.json").write_text("{}", encoding="utf-8")
    (warmup_dir / "report.html").write_text("<h1>warmup</h1>", encoding="utf-8")
    proof_dir = tmp_path / "proofs" / "001_observed_001_to_sink_01"
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "run_result.json").write_text("{}", encoding="utf-8")
    (proof_dir / "report.html").write_text("<h1>proof</h1>", encoding="utf-8")
    manifest["proof_result_summary"] = proof_result_summary_from_commands(manifest["commands"])
    _write_manifest_and_report(tmp_path, manifest)

    checker._assert_runner_result(manifest, tmp_path, require_proof_outputs=True)


def test_checker_requires_cleanup_rerun_outputs_for_cleanup_rerun_status(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    cleanup_dir = tmp_path / "cleanup_rerun"
    manifest = _runner_manifest(tmp_path)
    manifest["status"] = "cleanup_rerun"
    manifest["cleanup_command"] = [
        "python",
        "cleanup.py",
        "--output-dir",
        str(cleanup_dir),
    ]
    manifest["cleanup_rerun"] = {
        "output_dir": str(cleanup_dir),
        "run_result": str(cleanup_dir / "run_result.json"),
        "report": str(cleanup_dir / "report.html"),
    }
    _write_manifest_and_report(tmp_path, manifest)

    with pytest.raises(AssertionError):
        checker._assert_runner_result(manifest, tmp_path)

    cleanup_dir.mkdir()
    (cleanup_dir / "run_result.json").write_text("{}", encoding="utf-8")
    (cleanup_dir / "report.html").write_text("<h1>cleanup</h1>", encoding="utf-8")

    checker._assert_runner_result(manifest, tmp_path)
    checker._assert_runner_result(
        manifest,
        tmp_path,
        require_cleanup_rerun_output=True,
    )


def _write_runner_artifact(base: Path) -> dict[str, object]:
    manifest = _runner_manifest(base)
    _write_manifest_and_report(base, manifest)
    return manifest


def _write_manifest_and_report(base: Path, manifest: dict[str, object]) -> None:
    manifest["proof_request_selection"] = proof_request_selection_from_summary(
        {
            "schema": "planner_cleanup_proof_requests_v1",
            "requests": [
                {
                    "request_id": command["request_id"],
                    "object_id": command["object_id"],
                    "target_receptacle_id": command["target_receptacle_id"],
                    "ready": True,
                }
                for command in manifest["commands"]
            ],
        }
    )
    manifest["proof_result_summary"] = proof_result_summary_from_commands(manifest["commands"])
    (base / "proof_bundle_run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_planner_proof_bundle_runner_report(output_dir=base, manifest=manifest)


def _runner_manifest(base: Path) -> dict[str, object]:
    proof_dir = base / "proofs" / "001_observed_001_to_sink_01"
    command = [
        "python",
        "probe.py",
        "--output-dir",
        str(proof_dir),
        "--cleanup-object-id",
        "observed_001",
        "--cleanup-target-receptacle-id",
        "sink_01",
    ]
    return {
        "schema": PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA,
        "status": "dry_run",
        "cleanup_run_result": str(base / "cleanup" / "run_result.json"),
        "output_dir": str(base),
        "proof_request_count": 1,
        "ready_request_count": 1,
        "command_count": 1,
        "commands": [
            {
                "request_id": "proof_001",
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "output_dir": str(proof_dir),
                "run_result": str(proof_dir / "run_result.json"),
                "report": str(proof_dir / "report.html"),
                "command": command,
            }
        ],
        "cleanup_command": [],
        "report": str(base / "report.html"),
    }
