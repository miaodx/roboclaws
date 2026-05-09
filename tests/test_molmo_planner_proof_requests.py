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
    planner_proof_requests_from_substeps,
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
