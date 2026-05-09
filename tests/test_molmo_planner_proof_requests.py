from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from roboclaws.molmo_cleanup.planner_observed_binding import (
    OBSERVED_HANDLE_PLANNER_BINDING_SCHEMA,
)
from roboclaws.molmo_cleanup.planner_proof_requests import (
    PLANNER_PROOF_REQUESTS_SCHEMA,
    build_probe_commands,
    build_probe_warmup_command,
    planner_proof_requests_from_substeps,
    proof_request_selection_from_summary,
    proof_result_summary_from_commands,
    write_planner_proof_requests,
)


def test_planner_proof_requests_preserve_bound_probe_args(tmp_path: Path) -> None:
    contract = _BindingContract()
    substeps = [
        {
            "object_id": "observed_001",
            "source_receptacle_id": "counter_01",
            "target_receptacle_id": "sink_01",
            "steps": [
                {"phase": "navigate_to_object"},
                {"phase": "pick"},
                {"phase": "navigate_to_receptacle"},
                {"phase": "place"},
                {"phase": "object_done"},
            ],
        }
    ]

    manifest = write_planner_proof_requests(
        output_path=tmp_path / "planner_proof_requests.json",
        contract=contract,
        substeps=substeps,
    )

    assert manifest["schema"] == PLANNER_PROOF_REQUESTS_SCHEMA
    assert manifest["request_count"] == 1
    assert manifest["ready_count"] == 1
    assert manifest["agent_view_exposed"] is False
    request = manifest["requests"][0]
    assert request["request_id"] == "proof_001"
    assert request["object_id"] == "observed_001"
    assert request["source_receptacle_id"] == "counter_01"
    assert request["target_receptacle_id"] == "sink_01"
    assert request["tools"] == [
        "navigate_to_object",
        "pick",
        "navigate_to_receptacle",
        "place",
    ]
    assert request["binding"]["schema"] == OBSERVED_HANDLE_PLANNER_BINDING_SCHEMA
    assert request["planner_probe_args"]["--cleanup-object-id"] == "observed_001"
    assert request["planner_probe_args"]["--cleanup-planner-object-id"] == "pickup/body"
    assert manifest["planner_scene"]["scene_xml"] == "/tmp/molmospaces-scene.xml"
    assert (tmp_path / "planner_proof_requests.json").is_file()


def test_planner_proof_requests_record_blocked_binding() -> None:
    manifest = planner_proof_requests_from_substeps(
        contract=object(),
        substeps=[
            {
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "steps": [{"phase": "place"}],
            }
        ],
    )

    assert manifest["ready_count"] == 0
    assert manifest["blockers"][0]["code"] == "planner_binding_unavailable"
    assert manifest["requests"][0]["ready"] is False


def test_build_probe_commands_uses_only_ready_requests(tmp_path: Path) -> None:
    manifest = {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "requests": [
            {
                "request_id": "proof_001",
                "ready": True,
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "planner_probe_args": {
                    "--cleanup-object-id": "observed_001",
                    "--cleanup-target-receptacle-id": "sink_01",
                    "--cleanup-planner-object-id": "pickup/body",
                },
            },
            {
                "request_id": "proof_002",
                "ready": False,
                "object_id": "observed_002",
                "target_receptacle_id": "desk_01",
                "planner_probe_args": {},
            },
        ],
        "planner_scene": {
            "schema": "planner_cleanup_proof_scene_v1",
            "available": True,
            "scene_xml": "/tmp/molmospaces-scene.xml",
            "backend": "molmospaces_subprocess",
        },
    }

    commands = build_probe_commands(
        manifest=manifest,
        output_dir=tmp_path,
        runner_python=Path("python"),
        probe_script=Path("probe.py"),
        molmospaces_python=None,
        molmospaces_root=None,
        torch_extensions_dir=Path("torch_ext"),
    )

    assert len(commands) == 1
    command = commands[0]["command"]
    assert command[:2] == ["python", "probe.py"]
    assert "--cleanup-object-id" in command
    assert "observed_001" in command
    assert "--cleanup-planner-object-id" in command
    assert "pickup/body" in command
    assert "--cleanup-scene-xml" in command
    assert "/tmp/molmospaces-scene.xml" in command
    assert commands[0]["run_result"].endswith("run_result.json")


def test_build_probe_warmup_command_uses_config_import_and_shared_cache(
    tmp_path: Path,
) -> None:
    warmup = build_probe_warmup_command(
        output_dir=tmp_path,
        runner_python=Path("python"),
        probe_script=Path("probe.py"),
        molmospaces_python=Path("molmo-python"),
        molmospaces_root=Path("molmospaces"),
        torch_extensions_dir=Path("torch_ext"),
        timeout_s=900.0,
    )

    command = warmup["command"]
    assert warmup["kind"] == "rby1m_curobo_config_import"
    assert warmup["run_result"].endswith("rby1m_curobo_warmup/run_result.json")
    assert command[:2] == ["python", "probe.py"]
    assert "--probe-mode" in command
    assert "config_import" in command
    assert "--python-executable" in command
    assert "molmo-python" in command
    assert "--molmospaces-root" in command
    assert "molmospaces" in command
    assert "--torch-extensions-dir" in command
    assert "torch_ext" in command
    assert "--timeout-s" in command
    assert "900.0" in command


def test_proof_request_selection_excludes_prior_task_feasibility_blocked(
    tmp_path: Path,
) -> None:
    manifest = {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "request_count": 2,
        "ready_count": 2,
        "requests": [
            {
                "request_id": "proof_001",
                "ready": True,
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "planner_probe_args": {"--cleanup-object-id": "observed_001"},
            },
            {
                "request_id": "proof_002",
                "ready": True,
                "object_id": "observed_002",
                "target_receptacle_id": "shelf_01",
                "planner_probe_args": {"--cleanup-object-id": "observed_002"},
            },
        ],
    }
    prior_summary = {
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

    selection = proof_request_selection_from_summary(
        manifest,
        prior_proof_result_summary=prior_summary,
        exclude_task_feasibility_blocked=True,
    )
    commands = build_probe_commands(
        manifest=manifest,
        output_dir=tmp_path,
        runner_python=Path("python"),
        probe_script=Path("probe.py"),
        request_selection=selection,
    )

    assert selection["schema"] == "planner_cleanup_proof_request_selection_v1"
    assert selection["selected_request_ids"] == ["proof_002"]
    assert selection["excluded_requests"][0]["request_id"] == "proof_001"
    assert selection["excluded_requests"][0]["reason"] == "prior_task_feasibility_blocked"
    assert selection["fallback_required"] is False
    assert len(commands) == 1
    assert commands[0]["request_id"] == "proof_002"


def test_proof_request_selection_marks_fallback_required_when_all_ready_blocked() -> None:
    manifest = {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "requests": [
            {
                "request_id": "proof_001",
                "ready": True,
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "planner_probe_args": {"--cleanup-object-id": "observed_001"},
            }
        ],
    }
    selection = proof_request_selection_from_summary(
        manifest,
        prior_proof_result_summary={
            "results": [
                {
                    "request_id": "proof_001",
                    "task_feasibility_status": "blocked",
                    "blockers": [{"code": "HouseInvalidForTask"}],
                }
            ]
        },
        exclude_task_feasibility_blocked=True,
    )

    assert selection["selected_count"] == 0
    assert selection["excluded_count"] == 1
    assert selection["fallback_required"] is True


def test_proof_request_selection_generates_fallback_alias_requests(
    tmp_path: Path,
) -> None:
    manifest = {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "requests": [
            {
                "request_id": "proof_001",
                "ready": True,
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "source_receptacle_id": "counter_01",
                "tools": ["navigate_to_object", "pick", "navigate_to_receptacle", "place"],
                "binding": {
                    "candidate_pickup_names": [
                        "pickup/body",
                        "pickup/alt",
                        "Pickup|surface|1|1",
                    ],
                    "candidate_place_receptacle_names": [
                        "sink/body",
                        "sink/alt",
                        "Sink|1|2",
                    ],
                    "backend_planner_task_binding": {
                        "candidate_pickup_names": [
                            "pickup/body",
                            "pickup/alt",
                            "Pickup|surface|1|1",
                        ],
                        "candidate_place_receptacle_names": [
                            "sink/body",
                            "sink/alt",
                            "Sink|1|2",
                        ],
                    },
                    "requested_cleanup_primitive_binding": {
                        "object_id": "observed_001",
                        "target_receptacle_id": "sink_01",
                        "planner_object_id": "pickup/body",
                        "planner_target_receptacle_id": "sink/body",
                    },
                },
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
    prior_summary = {
        "results": [
            {
                "request_id": "proof_001",
                "status": "blocked_capability",
                "task_feasibility_status": "blocked",
                "blockers": [{"code": "HouseInvalidForTask"}],
            }
        ]
    }

    selection = proof_request_selection_from_summary(
        manifest,
        prior_proof_result_summary=prior_summary,
        exclude_task_feasibility_blocked=True,
        generate_fallback_requests=True,
        fallback_alias_limit=2,
    )
    commands = build_probe_commands(
        manifest=manifest,
        output_dir=tmp_path,
        runner_python=Path("python"),
        probe_script=Path("probe.py"),
        request_selection=selection,
    )

    assert selection["mode"] == "exclude_task_feasibility_blocked_with_fallbacks"
    assert selection["fallback_required"] is False
    assert selection["excluded_count"] == 1
    assert selection["generated_fallback_request_count"] == 2
    assert selection["selected_request_ids"] == [
        "proof_001_fallback_01",
        "proof_001_fallback_02",
    ]
    generated = selection["fallback_generation"]["generated_requests"]
    assert generated[0]["source_request_id"] == "proof_001"
    assert generated[0]["object_id"] == "observed_001"
    assert generated[0]["target_receptacle_id"] == "sink_01"
    assert generated[0]["fallback_request"]["prior_blockers"][0]["code"] == ("HouseInvalidForTask")
    assert generated[0]["planner_probe_args"]["--cleanup-planner-target-receptacle-id"] == (
        "sink/alt"
    )
    assert generated[1]["planner_probe_args"]["--cleanup-planner-object-id"] == ("pickup/alt")
    assert selection["fallback_generation"]["filtered_alias_count"] == 2
    assert {
        (item["axis"], item["alias"])
        for item in selection["fallback_generation"]["filtered_aliases"]
    } == {
        ("object", "Pickup|surface|1|1"),
        ("target", "Sink|1|2"),
    }
    assert [item["request_id"] for item in commands] == selection["selected_request_ids"]
    assert "sink/alt" in commands[0]["command"]
    assert "pickup/alt" in commands[1]["command"]


def test_proof_request_selection_filters_non_runtime_fallback_aliases() -> None:
    manifest = {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "requests": [
            {
                "request_id": "proof_001",
                "ready": True,
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "binding": {
                    "candidate_pickup_names": ["pickup/body", "Pickup|surface|1|1"],
                    "candidate_place_receptacle_names": ["sink/body", "Sink|1|2"],
                },
                "planner_probe_args": {
                    "--cleanup-object-id": "observed_001",
                    "--cleanup-target-receptacle-id": "sink_01",
                    "--cleanup-planner-object-id": "pickup/body",
                    "--cleanup-planner-target-receptacle-id": "sink/body",
                },
            }
        ],
    }

    selection = proof_request_selection_from_summary(
        manifest,
        prior_proof_result_summary={
            "results": [
                {
                    "request_id": "proof_001",
                    "task_feasibility_status": "blocked",
                    "blockers": [{"code": "HouseInvalidForTask"}],
                }
            ]
        },
        exclude_task_feasibility_blocked=True,
        generate_fallback_requests=True,
    )

    assert selection["selected_count"] == 0
    assert selection["generated_fallback_request_count"] == 0
    assert selection["fallback_required"] is True
    fallback_generation = selection["fallback_generation"]
    assert fallback_generation["unavailable_source_request_count"] == 1
    assert fallback_generation["filtered_alias_count"] == 2
    assert {
        (item["axis"], item["alias"], item["reason"])
        for item in fallback_generation["filtered_aliases"]
    } == {
        ("object", "Pickup|surface|1|1", "not_exact_scene_runtime_alias"),
        ("target", "Sink|1|2", "not_exact_scene_runtime_alias"),
    }


def test_proof_request_selection_discovers_runtime_alias_siblings_from_keyerror() -> None:
    manifest = {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "requests": [
            {
                "request_id": "proof_001",
                "ready": True,
                "object_id": "observed_001",
                "target_receptacle_id": "shelf_01",
                "binding": {
                    "candidate_pickup_names": [
                        "book_beef_1_0_8",
                        "Book|surface|8|79",
                    ],
                    "candidate_place_receptacle_names": [
                        "shelf_cafe_1_0_2",
                        "ShelvingUnit|2|3",
                    ],
                },
                "planner_probe_args": {
                    "--cleanup-object-id": "observed_001",
                    "--cleanup-target-receptacle-id": "shelf_01",
                    "--cleanup-planner-object-id": "book_beef_1_0_8",
                    "--cleanup-planner-target-receptacle-id": "shelf_cafe_1_0_2",
                },
            }
        ],
    }
    valid_names = [
        "book_beef_1_0_8",
        "book_beef_1_1_8",
        "book_beef_1_2_8",
        "shelf_cafe_1_0_2",
        "shelf_cafe_1_1_2",
        "sink_other_1_1_5",
    ]
    prior_summary = {
        "results": [
            {
                "request_id": "proof_001",
                "status": "blocked_capability",
                "task_feasibility_status": "blocked",
                "blockers": [{"code": "HouseInvalidForTask"}],
            },
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
                            f"\"Invalid name 'ShelvingUnit|2|3'. Valid names: {valid_names}\""
                        ),
                    }
                ],
            },
            {
                "request_id": "proof_001_fallback_02",
                "status": "blocked_capability",
                "task_feasibility_status": "blocked",
                "cleanup_task_config": {
                    "planner_object_id": "Book|surface|8|79",
                    "planner_target_receptacle_id": "shelf_cafe_1_0_2",
                },
                "blockers": [
                    {
                        "code": "KeyError",
                        "message": (
                            f"\"Invalid name 'Book|surface|8|79'. Valid names: {valid_names}\""
                        ),
                    }
                ],
            },
        ]
    }

    selection = proof_request_selection_from_summary(
        manifest,
        prior_proof_result_summary=prior_summary,
        exclude_task_feasibility_blocked=True,
        generate_fallback_requests=True,
        fallback_alias_limit=2,
    )

    assert selection["fallback_required"] is False
    assert selection["generated_fallback_request_count"] == 2
    fallback_generation = selection["fallback_generation"]
    assert fallback_generation["discovered_alias_count"] == 3
    assert {
        (item["axis"], item["alias"], item["derived_from"])
        for item in fallback_generation["discovered_aliases"]
    } == {
        ("target", "shelf_cafe_1_1_2", "proof_001_fallback_01"),
        ("object", "book_beef_1_1_8", "proof_001_fallback_02"),
        ("object", "book_beef_1_2_8", "proof_001_fallback_02"),
    }
    generated = fallback_generation["generated_requests"]
    assert generated[0]["planner_probe_args"]["--cleanup-planner-target-receptacle-id"] == (
        "shelf_cafe_1_1_2"
    )
    assert generated[1]["planner_probe_args"]["--cleanup-planner-object-id"] == ("book_beef_1_1_8")


def test_proof_request_selection_keeps_fallback_required_when_no_alias_available() -> None:
    manifest = {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "requests": [
            {
                "request_id": "proof_001",
                "ready": True,
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "binding": {
                    "candidate_pickup_names": ["pickup/body"],
                    "candidate_place_receptacle_names": ["sink/body"],
                },
                "planner_probe_args": {
                    "--cleanup-object-id": "observed_001",
                    "--cleanup-target-receptacle-id": "sink_01",
                    "--cleanup-planner-object-id": "pickup/body",
                    "--cleanup-planner-target-receptacle-id": "sink/body",
                },
            }
        ],
    }

    selection = proof_request_selection_from_summary(
        manifest,
        prior_proof_result_summary={
            "results": [
                {
                    "request_id": "proof_001",
                    "task_feasibility_status": "blocked",
                    "blockers": [{"code": "HouseInvalidForTask"}],
                }
            ]
        },
        exclude_task_feasibility_blocked=True,
        generate_fallback_requests=True,
    )

    assert selection["selected_count"] == 0
    assert selection["generated_fallback_request_count"] == 0
    assert selection["fallback_required"] is True
    assert selection["fallback_generation"]["unavailable_source_request_count"] == 1


def test_proof_result_summary_classifies_task_feasibility_and_views(tmp_path: Path) -> None:
    proof_dir = tmp_path / "proofs" / "001_observed_001_to_sink_01"
    views_dir = proof_dir / "planner_views"
    views_dir.mkdir(parents=True)
    (views_dir / "initial.png").write_bytes(b"initial")
    (views_dir / "final.png").write_bytes(b"final")
    (proof_dir / "report.html").write_text("<h1>proof</h1>", encoding="utf-8")
    (proof_dir / "run_result.json").write_text(
        json.dumps(
            {
                "status": "blocked_capability",
                "manipulation_evidence": {
                    "execution_attempted": True,
                    "blockers": [
                        {
                            "code": "HouseInvalidForTask",
                            "message": "robot placement failed near object",
                        }
                    ],
                    "cleanup_task_config": {
                        "scene_xml": "/tmp/scene.xml",
                        "planner_object_id": "pickup/body",
                    },
                    "requested_cleanup_primitive_binding": {
                        "scene_xml": "/tmp/scene.xml",
                        "planner_object_id": "pickup/body",
                        "planner_target_receptacle_id": "sink/body",
                    },
                    "image_artifacts": {
                        "initial": "planner_views/initial.png",
                        "final": "planner_views/final.png",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    commands = [
        {
            "request_id": "proof_001",
            "object_id": "observed_001",
            "target_receptacle_id": "sink_01",
            "run_result": str(proof_dir / "run_result.json"),
            "report": str(proof_dir / "report.html"),
        },
        {
            "request_id": "proof_002",
            "object_id": "observed_002",
            "target_receptacle_id": "shelf_01",
            "run_result": str(tmp_path / "missing" / "run_result.json"),
            "report": str(tmp_path / "missing" / "report.html"),
        },
    ]

    summary = proof_result_summary_from_commands(commands)

    assert summary["schema"] == "planner_cleanup_proof_result_summary_v1"
    assert summary["expected_count"] == 2
    assert summary["result_count"] == 1
    assert summary["missing_result_count"] == 1
    assert summary["task_feasibility_blocked_count"] == 1
    assert summary["view_artifact_count"] == 2
    result = summary["results"][0]
    assert result["task_feasibility_status"] == "blocked"
    assert result["visual_status"] == "views_recorded"
    assert result["blockers"][0]["code"] == "HouseInvalidForTask"
    assert result["views"][0]["path"].endswith("planner_views/final.png")
    assert summary["results"][1]["task_feasibility_status"] == "not_run"


def test_proof_result_summary_surfaces_timeout_worker_stage_evidence(
    tmp_path: Path,
) -> None:
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
                        {
                            "event": "worker_start",
                            "stage": "worker_start",
                            "elapsed_s": 0.1,
                            "runtime_diagnostics": {"large": "omitted from bundle"},
                        },
                        {
                            "event": "rby1m_config_import_start",
                            "stage": "rby1m_config_import",
                            "elapsed_s": 3.2,
                        },
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    commands = [
        {
            "request_id": "proof_001_fallback_01",
            "object_id": "observed_001",
            "target_receptacle_id": "sink_01",
            "run_result": str(proof_dir / "run_result.json"),
            "report": str(proof_dir / "report.html"),
        }
    ]

    summary = proof_result_summary_from_commands(commands)

    assert summary["timeout_count"] == 1
    assert summary["rby1m_config_import_timeout_count"] == 1
    assert summary["execution_attempted_count"] == 0
    assert summary["worker_stage_event_count"] == 2
    assert summary["last_worker_stage_counts"] == {"rby1m_config_import": 1}
    result = summary["results"][0]
    assert result["task_feasibility_status"] == "not_reached"
    assert result["last_worker_stage"] == "rby1m_config_import"
    assert result["worker_stage_event_count"] == 2
    assert result["worker_stage_events"][0] == {
        "elapsed_s": 0.1,
        "event": "worker_start",
        "stage": "worker_start",
    }
    assert "runtime_diagnostics" not in result["worker_stage_events"][0]
    assert result["stdout"].endswith("planner_probe_stdout.txt")
    assert result["stderr"].endswith("planner_probe_stderr.txt")


class _BindingContract:
    backend = SimpleNamespace(
        backend="molmospaces_subprocess",
        scene_xml="/tmp/molmospaces-scene.xml",
    )

    def planner_observed_handle_binding(
        self,
        object_id: str,
        target_receptacle_id: str,
        *,
        source_receptacle_id: str = "",
        tools: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "schema": OBSERVED_HANDLE_PLANNER_BINDING_SCHEMA,
            "ok": True,
            "status": "ok",
            "object_id": object_id,
            "target_receptacle_id": target_receptacle_id,
            "source_receptacle_id": source_receptacle_id,
            "planner_object_id": "pickup/body",
            "planner_target_receptacle_id": "sink/body",
            "tools": list(tools or []),
            "planner_probe_args": {
                "--cleanup-object-id": object_id,
                "--cleanup-target-receptacle-id": target_receptacle_id,
                "--cleanup-source-receptacle-id": source_receptacle_id,
                "--cleanup-tools": ",".join(tools or []),
                "--cleanup-planner-object-id": "pickup/body",
                "--cleanup-planner-target-receptacle-id": "sink/body",
            },
            "blockers": [],
        }
