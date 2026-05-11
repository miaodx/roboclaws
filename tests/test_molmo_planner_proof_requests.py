from __future__ import annotations

from pathlib import Path

from roboclaws.molmo_cleanup.planner_observed_binding import (
    OBSERVED_HANDLE_PLANNER_BINDING_SCHEMA,
)
from roboclaws.molmo_cleanup.planner_proof_requests import (
    PLANNER_PROOF_REQUESTS_SCHEMA,
    build_probe_commands,
    planner_proof_requests_from_substeps,
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
    assert commands[0]["run_result"].endswith("run_result.json")


class _BindingContract:
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
