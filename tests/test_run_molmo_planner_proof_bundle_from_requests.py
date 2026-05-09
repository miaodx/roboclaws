from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from roboclaws.molmo_cleanup.planner_proof_requests import PLANNER_PROOF_REQUESTS_SCHEMA

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_molmo_planner_proof_bundle_from_requests.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "run_molmo_planner_proof_bundle_from_requests",
        SCRIPT_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runner_writes_dry_run_manifest_and_report_from_inline_requests(tmp_path: Path) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    cleanup_run_result.write_text(
        json.dumps(
            {
                "seed": 7,
                "backend": "api_semantic_synthetic",
                "fixture_hint_mode": "room_only",
                "perception_mode": "visible_object_detections",
                "requested_generated_mess_count": 10,
                "planner_proof_requests": _proof_requests(),
            }
        ),
        encoding="utf-8",
    )

    result = runner.run_from_cleanup_result(
        cleanup_run_result=cleanup_run_result,
        output_dir=tmp_path / "bundle",
        runner_python=Path("python"),
        probe_script=Path("probe.py"),
        cleanup_script=Path("cleanup.py"),
        molmospaces_python=None,
        molmospaces_root=None,
        embodiment="rby1m",
        probe_mode="execute",
        steps=2,
        timeout_s=600.0,
        renderer_device_id=0,
        torch_extensions_dir=Path("torch_ext"),
        rby1m_curobo_memory_profile="low",
    )

    manifest = result["manifest"]
    assert result["status"] == "dry_run"
    assert manifest["schema"] == "planner_cleanup_proof_bundle_run_manifest_v1"
    assert manifest["report"].endswith("report.html")
    assert manifest["proof_request_count"] == 1
    assert manifest["ready_request_count"] == 1
    assert manifest["command_count"] == 1
    command = manifest["commands"][0]["command"]
    assert command[:2] == ["python", "probe.py"]
    assert "--cleanup-object-id" in command
    assert "observed_001" in command
    assert "--cleanup-planner-target-receptacle-id" in command
    assert "sink/body" in command
    assert manifest["commands"][0]["report"].endswith("report.html")
    assert Path(result["manifest_path"]).is_file()
    assert Path(result["report_path"]).is_file()
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Planner Proof Bundle Runner" in report
    assert "Proof Probe Commands" in report
    assert "Cleanup Rerun Command" in report
    assert "observed_001" in report
    assert "--cleanup-object-id" in report
    assert "sink/body" in report


def test_runner_loads_request_artifact_from_run_result(tmp_path: Path) -> None:
    runner = _load_module()
    cleanup_dir = tmp_path / "cleanup"
    cleanup_dir.mkdir()
    (cleanup_dir / "planner_proof_requests.json").write_text(
        json.dumps(_proof_requests()),
        encoding="utf-8",
    )
    cleanup_run_result = cleanup_dir / "run_result.json"
    cleanup_run_result.write_text(
        json.dumps({"artifacts": {"planner_proof_requests": "planner_proof_requests.json"}}),
        encoding="utf-8",
    )

    result = runner.run_from_cleanup_result(
        cleanup_run_result=cleanup_run_result,
        output_dir=tmp_path / "bundle",
        runner_python=Path("python"),
        probe_script=Path("probe.py"),
        cleanup_script=Path("cleanup.py"),
        molmospaces_python=None,
        molmospaces_root=None,
        embodiment="franka",
        probe_mode="config_import",
        steps=1,
        timeout_s=30.0,
        renderer_device_id=-1,
        torch_extensions_dir=None,
        rby1m_curobo_memory_profile="none",
    )

    command = result["manifest"]["commands"][0]["command"]
    assert "--embodiment" in command
    assert "franka" in command
    assert "--probe-mode" in command
    assert "config_import" in command


def test_runner_records_cleanup_rerun_artifacts_when_rerun_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    cleanup_run_result.write_text(
        json.dumps(
            {
                "seed": 7,
                "backend": "api_semantic_synthetic",
                "fixture_hint_mode": "room_only",
                "perception_mode": "visible_object_detections",
                "requested_generated_mess_count": 10,
                "planner_proof_requests": _proof_requests(),
            }
        ),
        encoding="utf-8",
    )
    commands_run: list[list[str]] = []

    def fake_run_command(command: list[str]) -> None:
        commands_run.append(list(command))
        output_dir = Path(command[command.index("--output-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "run_result.json").write_text("{}", encoding="utf-8")
        (output_dir / "report.html").write_text("<h1>report</h1>", encoding="utf-8")

    monkeypatch.setattr(runner, "_run_command", fake_run_command)

    result = runner.run_from_cleanup_result(
        cleanup_run_result=cleanup_run_result,
        output_dir=tmp_path / "bundle",
        runner_python=Path("python"),
        probe_script=Path("probe.py"),
        cleanup_script=Path("cleanup.py"),
        molmospaces_python=None,
        molmospaces_root=None,
        embodiment="rby1m",
        probe_mode="execute",
        steps=2,
        timeout_s=600.0,
        renderer_device_id=0,
        torch_extensions_dir=Path("torch_ext"),
        rby1m_curobo_memory_profile="low",
        execute_probes=True,
        rerun_cleanup=True,
        cleanup_output_dir=tmp_path / "rerun",
    )

    manifest = result["manifest"]
    assert result["status"] == "cleanup_rerun"
    assert len(commands_run) == 2
    assert commands_run[-1][:2] == ["python", "cleanup.py"]
    assert "--planner-proof-run-result" in commands_run[-1]
    cleanup_rerun = manifest["cleanup_rerun"]
    assert cleanup_rerun["output_dir"] == str(tmp_path / "rerun")
    assert cleanup_rerun["run_result"] == str(tmp_path / "rerun" / "run_result.json")
    assert cleanup_rerun["report"] == str(tmp_path / "rerun" / "report.html")
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Cleanup Rerun Artifact" in report
    assert str(tmp_path / "rerun" / "run_result.json") in report


def test_runner_requires_planner_proof_requests(tmp_path: Path) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "run_result.json"
    cleanup_run_result.write_text(json.dumps({"artifacts": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="planner proof requests"):
        runner.run_from_cleanup_result(
            cleanup_run_result=cleanup_run_result,
            output_dir=tmp_path / "bundle",
            runner_python=Path("python"),
            probe_script=Path("probe.py"),
            cleanup_script=Path("cleanup.py"),
            molmospaces_python=None,
            molmospaces_root=None,
            embodiment="rby1m",
            probe_mode="execute",
            steps=2,
            timeout_s=600.0,
            renderer_device_id=0,
            torch_extensions_dir=None,
            rby1m_curobo_memory_profile="low",
        )


def test_runner_cli_prints_manifest_report_and_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    cleanup_run_result.write_text(
        json.dumps({"planner_proof_requests": _proof_requests()}),
        encoding="utf-8",
    )
    output_dir = tmp_path / "bundle"
    monkeypatch.setattr(
        runner.sys,
        "argv",
        [
            "run_molmo_planner_proof_bundle_from_requests.py",
            str(cleanup_run_result),
            "--output-dir",
            str(output_dir),
            "--runner-python",
            "python",
            "--probe-script",
            "probe.py",
            "--cleanup-script",
            "cleanup.py",
        ],
    )

    runner.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "dry_run"
    assert payload["manifest"].endswith("proof_bundle_run_manifest.json")
    assert payload["report"].endswith("report.html")
    assert (output_dir / "report.html").is_file()


def _proof_requests() -> dict[str, object]:
    return {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "request_count": 1,
        "ready_count": 1,
        "agent_view_exposed": False,
        "blockers": [],
        "requests": [
            {
                "request_id": "proof_001",
                "ready": True,
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "source_receptacle_id": "counter_01",
                "planner_probe_args": {
                    "--cleanup-object-id": "observed_001",
                    "--cleanup-target-receptacle-id": "sink_01",
                    "--cleanup-source-receptacle-id": "counter_01",
                    "--cleanup-tools": "navigate_to_object,pick,navigate_to_receptacle,place",
                    "--cleanup-planner-object-id": "pickup/body",
                    "--cleanup-planner-target-receptacle-id": "sink/body",
                },
            }
        ],
    }
