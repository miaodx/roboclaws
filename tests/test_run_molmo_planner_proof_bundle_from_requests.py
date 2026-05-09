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
    assert manifest["proof_request_selection"]["mode"] == "all_ready"
    assert manifest["proof_request_selection"]["selected_request_ids"] == ["proof_001"]
    command = manifest["commands"][0]["command"]
    assert command[:2] == ["python", "probe.py"]
    assert "--cleanup-object-id" in command
    assert "observed_001" in command
    assert "--cleanup-planner-target-receptacle-id" in command
    assert "sink/body" in command
    assert "--cleanup-scene-xml" in command
    assert "/tmp/molmospaces-scene.xml" in command
    assert manifest["commands"][0]["report"].endswith("report.html")
    assert manifest["planner_scene"]["scene_xml"] == "/tmp/molmospaces-scene.xml"
    assert manifest["proof_result_summary"]["expected_count"] == 1
    assert manifest["proof_result_summary"]["results"][0]["task_feasibility_status"] == "not_run"
    assert Path(result["manifest_path"]).is_file()
    assert Path(result["report_path"]).is_file()
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Planner Proof Bundle Runner" in report
    assert "Proof Request Selection" in report
    assert "Proof Probe Commands" in report
    assert "Proof Probe Results" in report
    assert "not_run" in report
    assert "Cleanup Rerun Command" in report
    assert "observed_001" in report
    assert "--cleanup-object-id" in report
    assert "sink/body" in report
    assert "/tmp/molmospaces-scene.xml" in report


def test_runner_excludes_prior_task_feasibility_blocked_requests(tmp_path: Path) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    requests = _proof_requests()
    requests["request_count"] = 2
    requests["ready_count"] = 2
    requests["requests"] = [
        requests["requests"][0],
        {
            "request_id": "proof_002",
            "ready": True,
            "object_id": "observed_002",
            "target_receptacle_id": "shelf_01",
            "source_receptacle_id": "table_01",
            "planner_probe_args": {
                "--cleanup-object-id": "observed_002",
                "--cleanup-target-receptacle-id": "shelf_01",
                "--cleanup-planner-object-id": "book/body",
                "--cleanup-planner-target-receptacle-id": "shelf/body",
            },
        },
    ]
    cleanup_run_result.write_text(
        json.dumps({"planner_proof_requests": requests}), encoding="utf-8"
    )
    prior = tmp_path / "prior" / "proof_bundle_run_manifest.json"
    prior.parent.mkdir()
    prior.write_text(
        json.dumps(
            {
                "proof_result_summary": {
                    "schema": "planner_cleanup_proof_result_summary_v1",
                    "results": [
                        {
                            "request_id": "proof_001",
                            "status": "blocked_capability",
                            "task_feasibility_status": "blocked",
                            "blockers": [{"code": "HouseInvalidForTask"}],
                        }
                    ],
                }
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
        torch_extensions_dir=None,
        rby1m_curobo_memory_profile="low",
        prior_proof_bundle_manifest=prior,
        exclude_task_feasibility_blocked=True,
    )

    selection = result["manifest"]["proof_request_selection"]
    assert selection["mode"] == "exclude_task_feasibility_blocked"
    assert selection["selected_request_ids"] == ["proof_002"]
    assert selection["excluded_requests"][0]["request_id"] == "proof_001"
    assert result["manifest"]["command_count"] == 1
    assert result["manifest"]["commands"][0]["request_id"] == "proof_002"
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Proof Request Selection" in report
    assert "prior_task_feasibility_blocked" in report
    assert "HouseInvalidForTask" in report


def test_runner_marks_fallback_required_when_all_prior_requests_blocked(tmp_path: Path) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    cleanup_run_result.write_text(
        json.dumps({"planner_proof_requests": _proof_requests()}),
        encoding="utf-8",
    )
    prior = tmp_path / "prior" / "proof_bundle_run_manifest.json"
    prior.parent.mkdir()
    prior.write_text(
        json.dumps(
            {
                "proof_result_summary": {
                    "schema": "planner_cleanup_proof_result_summary_v1",
                    "results": [
                        {
                            "request_id": "proof_001",
                            "status": "blocked_capability",
                            "task_feasibility_status": "blocked",
                            "blockers": [{"code": "HouseInvalidForTask"}],
                        }
                    ],
                }
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
        torch_extensions_dir=None,
        rby1m_curobo_memory_profile="low",
        prior_proof_bundle_manifest=prior,
        exclude_task_feasibility_blocked=True,
    )

    assert result["manifest"]["command_count"] == 0
    selection = result["manifest"]["proof_request_selection"]
    assert selection["fallback_required"] is True
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Fallback required" in report
    assert "No proof requests selected" in report


def test_runner_generates_fallback_requests_from_prior_blocked_aliases(
    tmp_path: Path,
) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    requests = _proof_requests()
    request = requests["requests"][0]
    request["binding"] = {
        "candidate_pickup_names": ["pickup/body", "pickup/alt", "Pickup|surface|1|1"],
        "candidate_place_receptacle_names": ["sink/body", "sink/alt", "Sink|1|2"],
    }
    cleanup_run_result.write_text(
        json.dumps({"planner_proof_requests": requests}),
        encoding="utf-8",
    )
    prior = tmp_path / "prior" / "proof_bundle_run_manifest.json"
    prior.parent.mkdir()
    prior.write_text(
        json.dumps(
            {
                "proof_result_summary": {
                    "schema": "planner_cleanup_proof_result_summary_v1",
                    "results": [
                        {
                            "request_id": "proof_001",
                            "status": "blocked_capability",
                            "task_feasibility_status": "blocked",
                            "blockers": [{"code": "HouseInvalidForTask"}],
                        }
                    ],
                }
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
        torch_extensions_dir=None,
        rby1m_curobo_memory_profile="low",
        prior_proof_bundle_manifest=prior,
        exclude_task_feasibility_blocked=True,
        generate_fallback_requests=True,
        fallback_alias_limit=2,
    )

    manifest = result["manifest"]
    selection = manifest["proof_request_selection"]
    assert manifest["command_count"] == 2
    assert selection["fallback_required"] is False
    assert selection["generated_fallback_request_count"] == 2
    assert manifest["commands"][0]["request_id"] == "proof_001_fallback_01"
    assert manifest["commands"][0]["object_id"] == "observed_001"
    assert manifest["commands"][0]["target_receptacle_id"] == "sink_01"
    assert "sink/alt" in manifest["commands"][0]["command"]
    assert "pickup/alt" in manifest["commands"][1]["command"]
    assert selection["fallback_generation"]["filtered_alias_count"] == 2
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Generated Fallback Requests" in report
    assert "Filtered Fallback Aliases" in report
    assert "proof_001_fallback_01" in report
    assert "Pickup|surface|1|1" in report
    assert "Sink|1|2" in report


def test_runner_discovers_runtime_aliases_from_prior_fallback_keyerrors(
    tmp_path: Path,
) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    requests = _proof_requests()
    request = requests["requests"][0]
    request["target_receptacle_id"] = "shelf_01"
    request["planner_probe_args"] = {
        "--cleanup-object-id": "observed_001",
        "--cleanup-target-receptacle-id": "shelf_01",
        "--cleanup-planner-object-id": "book_beef_1_0_8",
        "--cleanup-planner-target-receptacle-id": "shelf_cafe_1_0_2",
    }
    request["binding"] = {
        "candidate_pickup_names": ["book_beef_1_0_8", "Book|surface|8|79"],
        "candidate_place_receptacle_names": ["shelf_cafe_1_0_2", "ShelvingUnit|2|3"],
    }
    cleanup_run_result.write_text(
        json.dumps({"planner_proof_requests": requests}),
        encoding="utf-8",
    )
    prior = tmp_path / "prior" / "proof_bundle_run_manifest.json"
    prior.parent.mkdir()
    valid_names = [
        "book_beef_1_0_8",
        "book_beef_1_1_8",
        "shelf_cafe_1_0_2",
        "shelf_cafe_1_1_2",
    ]
    prior.write_text(
        json.dumps(
            {
                "proof_request_selection": {
                    "excluded_requests": [
                        {
                            "request_id": "proof_001",
                            "prior_status": "blocked_capability",
                            "prior_task_feasibility_status": "blocked",
                            "prior_blockers": [{"code": "HouseInvalidForTask"}],
                        }
                    ]
                },
                "proof_result_summary": {
                    "schema": "planner_cleanup_proof_result_summary_v1",
                    "results": [
                        {
                            "request_id": "proof_001_fallback_01",
                            "status": "blocked_capability",
                            "task_feasibility_status": "blocked",
                            "cleanup_task_config": {
                                "planner_object_id": "book_beef_1_0_8",
                                "planner_target_receptacle_id": "ShelvingUnit|2|3",
                            },
                            "blockers": [
                                {
                                    "code": "KeyError",
                                    "message": (
                                        f"\"Invalid name 'ShelvingUnit|2|3'. "
                                        f'Valid names: {valid_names}"'
                                    ),
                                }
                            ],
                        }
                    ],
                },
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
        torch_extensions_dir=None,
        rby1m_curobo_memory_profile="low",
        prior_proof_bundle_manifest=prior,
        exclude_task_feasibility_blocked=True,
        generate_fallback_requests=True,
    )

    manifest = result["manifest"]
    selection = manifest["proof_request_selection"]
    assert manifest["command_count"] == 1
    assert selection["selected_request_ids"] == ["proof_001_fallback_01"]
    assert selection["fallback_generation"]["discovered_alias_count"] == 1
    assert "shelf_cafe_1_1_2" in manifest["commands"][0]["command"]
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Discovered Runtime Aliases" in report
    assert "shelf_cafe_1_1_2" in report
    assert "proof_001_fallback_01" in report


def test_runner_carries_prior_failed_runtime_fallback_candidates(
    tmp_path: Path,
) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    requests = _proof_requests()
    request = requests["requests"][0]
    request["target_receptacle_id"] = "shelf_01"
    request["planner_probe_args"] = {
        "--cleanup-object-id": "observed_001",
        "--cleanup-target-receptacle-id": "shelf_01",
        "--cleanup-planner-object-id": "book_beef_1_0_8",
        "--cleanup-planner-target-receptacle-id": "shelf_cafe_1_0_2",
    }
    request["binding"] = {
        "candidate_pickup_names": ["book_beef_1_0_8", "Book|surface|8|79"],
        "candidate_place_receptacle_names": ["shelf_cafe_1_0_2", "ShelvingUnit|2|3"],
    }
    cleanup_run_result.write_text(
        json.dumps({"planner_proof_requests": requests}),
        encoding="utf-8",
    )
    prior = tmp_path / "prior" / "proof_bundle_run_manifest.json"
    prior.parent.mkdir()
    prior.write_text(
        json.dumps(
            {
                "proof_request_selection": {
                    "excluded_requests": [
                        {
                            "request_id": "proof_001",
                            "prior_status": "blocked_capability",
                            "prior_task_feasibility_status": "blocked",
                            "prior_blockers": [{"code": "HouseInvalidForTask"}],
                        }
                    ],
                    "fallback_generation": {
                        "discovered_aliases": [
                            {
                                "source_request_id": "proof_001",
                                "axis": "object",
                                "alias": "book_beef_1_1_8",
                                "derived_from": "proof_001_fallback_02",
                                "invalid_alias": "Book|surface|8|79",
                                "reason": "valid_name_sibling_from_prior_keyerror",
                            },
                            {
                                "source_request_id": "proof_001",
                                "axis": "object",
                                "alias": "book_beef_1_2_8",
                                "derived_from": "proof_001_fallback_02",
                                "invalid_alias": "Book|surface|8|79",
                                "reason": "valid_name_sibling_from_prior_keyerror",
                            },
                            {
                                "source_request_id": "proof_001",
                                "axis": "target",
                                "alias": "shelf_cafe_1_1_2",
                                "derived_from": "proof_001_fallback_01",
                                "invalid_alias": "ShelvingUnit|2|3",
                                "reason": "valid_name_sibling_from_prior_keyerror",
                            },
                        ]
                    },
                },
                "proof_result_summary": {
                    "schema": "planner_cleanup_proof_result_summary_v1",
                    "results": [
                        {
                            "request_id": "proof_001_fallback_01",
                            "status": "blocked_capability",
                            "task_feasibility_status": "blocked",
                            "cleanup_task_config": {
                                "planner_object_id": "book_beef_1_0_8",
                                "planner_target_receptacle_id": "shelf_cafe_1_1_2",
                            },
                            "blockers": [{"code": "HouseInvalidForTask"}],
                        },
                        {
                            "request_id": "proof_001_fallback_02",
                            "status": "blocked_capability",
                            "task_feasibility_status": "blocked",
                            "cleanup_task_config": {
                                "planner_object_id": "book_beef_1_1_8",
                                "planner_target_receptacle_id": "shelf_cafe_1_0_2",
                            },
                            "blockers": [
                                {
                                    "code": "AssertionError",
                                    "message": "Object is not a root body",
                                }
                            ],
                        },
                    ],
                },
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
        torch_extensions_dir=None,
        rby1m_curobo_memory_profile="low",
        prior_proof_bundle_manifest=prior,
        exclude_task_feasibility_blocked=True,
        generate_fallback_requests=True,
        fallback_alias_limit=4,
    )

    manifest = result["manifest"]
    selection = manifest["proof_request_selection"]
    assert manifest["command_count"] == 0
    assert selection["fallback_required"] is True
    assert selection["fallback_generation"]["filtered_pair_count"] == 1
    assert selection["fallback_generation"]["filtered_alias_count"] == 4
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Filtered Fallback Pairs" in report
    assert "prior_task_feasibility_blocked_pair" in report
    assert "prior_non_root_body_alias" in report
    assert "not_pickup_root_body_alias" in report


def test_runner_can_add_visible_warmup_with_output_local_cache(tmp_path: Path) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    cleanup_run_result.write_text(
        json.dumps({"planner_proof_requests": _proof_requests()}),
        encoding="utf-8",
    )
    output_dir = tmp_path / "bundle"

    result = runner.run_from_cleanup_result(
        cleanup_run_result=cleanup_run_result,
        output_dir=output_dir,
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
        warmup_rby1m_curobo=True,
    )

    manifest = result["manifest"]
    warmup = manifest["warmup"]
    shared_cache = str(output_dir / "torch_extensions")
    assert warmup["run_result"].endswith("rby1m_curobo_warmup/run_result.json")
    assert "--probe-mode" in warmup["command"]
    assert "config_import" in warmup["command"]
    assert "--torch-extensions-dir" in warmup["command"]
    assert shared_cache in warmup["command"]
    proof_command = manifest["commands"][0]["command"]
    assert "--torch-extensions-dir" in proof_command
    assert shared_cache in proof_command
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "RBY1M/CuRobo Warmup" in report
    assert "rby1m_curobo_warmup/run_result.json" in report
    assert "config_import" in report


def test_runner_executes_warmup_before_proof_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_module()
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    cleanup_run_result.write_text(
        json.dumps({"planner_proof_requests": _proof_requests()}),
        encoding="utf-8",
    )
    commands_run: list[list[str]] = []

    def fake_run_command(command: list[str]) -> None:
        commands_run.append(list(command))
        output_dir = Path(command[command.index("--output-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        if "--cleanup-object-id" in command:
            (output_dir / "run_result.json").write_text(
                json.dumps(
                    {
                        "status": "planner_backed",
                        "manipulation_evidence": {
                            "execution_attempted": True,
                            "cleanup_primitive_binding": {
                                "object_id": "observed_001",
                                "target_receptacle_id": "sink_01",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
        else:
            (output_dir / "run_result.json").write_text(
                json.dumps({"status": "blocked_capability"}),
                encoding="utf-8",
            )
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
        torch_extensions_dir=None,
        rby1m_curobo_memory_profile="low",
        execute_probes=True,
        warmup_rby1m_curobo=True,
    )

    assert result["status"] == "probes_executed"
    assert len(commands_run) == 2
    assert "--probe-mode" in commands_run[0]
    assert "config_import" in commands_run[0]
    assert "--cleanup-object-id" not in commands_run[0]
    assert "--cleanup-object-id" in commands_run[1]
    shared_cache = str(tmp_path / "bundle" / "torch_extensions")
    assert shared_cache in commands_run[0]
    assert shared_cache in commands_run[1]
    assert result["manifest"]["proof_result_summary"]["planner_backed_count"] == 1


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


def test_runner_enriches_legacy_requests_with_source_scene(tmp_path: Path) -> None:
    runner = _load_module()
    requests = dict(_proof_requests())
    requests.pop("planner_scene", None)
    cleanup_run_result = tmp_path / "cleanup" / "run_result.json"
    cleanup_run_result.parent.mkdir()
    cleanup_run_result.write_text(
        json.dumps(
            {
                "backend": "molmospaces_subprocess",
                "molmospaces_runtime": {"scene_xml": "/tmp/source-scene.xml"},
                "planner_proof_requests": requests,
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
        torch_extensions_dir=None,
        rby1m_curobo_memory_profile="low",
    )

    command = result["manifest"]["commands"][0]["command"]
    assert result["manifest"]["planner_scene"]["scene_xml"] == "/tmp/source-scene.xml"
    assert "--cleanup-scene-xml" in command
    assert "/tmp/source-scene.xml" in command


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
        if "--cleanup-object-id" in command:
            (output_dir / "run_result.json").write_text(
                json.dumps(
                    {
                        "status": "blocked_capability",
                        "manipulation_evidence": {
                            "execution_attempted": True,
                            "blockers": [
                                {
                                    "code": "HouseInvalidForTask",
                                    "message": "robot placement failed",
                                }
                            ],
                            "requested_cleanup_primitive_binding": {
                                "planner_object_id": "pickup/body",
                                "planner_target_receptacle_id": "sink/body",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
        else:
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
    summary = manifest["proof_result_summary"]
    assert summary["result_count"] == 1
    assert summary["task_feasibility_blocked_count"] == 1
    assert summary["results"][0]["task_feasibility_status"] == "blocked"
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Proof Probe Results" in report
    assert "HouseInvalidForTask" in report
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
        "planner_scene": {
            "schema": "planner_cleanup_proof_scene_v1",
            "available": True,
            "scene_xml": "/tmp/molmospaces-scene.xml",
            "backend": "molmospaces_subprocess",
        },
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
