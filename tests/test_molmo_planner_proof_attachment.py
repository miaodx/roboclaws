from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.molmo_cleanup.manipulation_provenance import (
    MANIPULATION_PROBE_CONTRACT,
    PLANNER_BACKED_PROVENANCE,
    planner_backed_probe_evidence,
)
from roboclaws.molmo_cleanup.planner_proof_attachment import (
    PLANNER_PROOF_ATTACHMENT_SCHEMA,
    attach_planner_proof,
    validate_planner_proof_attachment,
)


def test_attach_planner_proof_validates_and_copies_strict_images(tmp_path: Path) -> None:
    proof_path = _write_strict_planner_proof(tmp_path / "proof")
    cleanup_dir = tmp_path / "cleanup"

    attachment = attach_planner_proof(
        proof_run_result_path=proof_path,
        cleanup_run_dir=cleanup_dir,
    )

    validate_planner_proof_attachment(attachment)
    assert attachment["schema"] == PLANNER_PROOF_ATTACHMENT_SCHEMA
    assert attachment["status"] == PLANNER_BACKED_PROVENANCE
    assert attachment["planner_backed"] is True
    assert attachment["strict_proof_eligible"] is True
    assert attachment["steps_executed"] == 2
    assert attachment["max_abs_qpos_delta"] == 0.01
    assert (cleanup_dir / attachment["image_artifacts"]["initial"]).is_file()
    assert (cleanup_dir / attachment["image_artifacts"]["final"]).is_file()


def test_attach_planner_proof_rejects_non_strict_probe(tmp_path: Path) -> None:
    proof_path = _write_strict_planner_proof(tmp_path / "proof")
    data = json.loads(proof_path.read_text(encoding="utf-8"))
    data["manipulation_evidence"]["max_abs_qpos_delta"] = 0.0
    proof_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="not strict planner-backed evidence"):
        attach_planner_proof(
            proof_run_result_path=proof_path,
            cleanup_run_dir=tmp_path / "cleanup",
        )


def test_attach_planner_proof_preserves_cleanup_primitive_binding(tmp_path: Path) -> None:
    binding = {
        "schema": "planner_probe_cleanup_primitive_binding_v1",
        "object_id": "observed_001",
        "target_receptacle_id": "sink_01",
        "tools": ["navigate_to_object", "pick", "navigate_to_receptacle", "place"],
    }
    proof_path = _write_strict_planner_proof(tmp_path / "proof", cleanup_binding=binding)

    attachment = attach_planner_proof(
        proof_run_result_path=proof_path,
        cleanup_run_dir=tmp_path / "cleanup",
    )

    assert attachment["cleanup_primitive_binding"] == binding


def _write_strict_planner_proof(
    base: Path,
    *,
    cleanup_binding: dict[str, object] | None = None,
) -> Path:
    base.mkdir(parents=True)
    views = base / "planner_views"
    views.mkdir()
    (views / "initial_wrist_camera.png").write_bytes(b"initial")
    (views / "final_wrist_camera.png").write_bytes(b"final")
    evidence = planner_backed_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="franka",
        task="pick_and_place",
        probe_mode="execute",
        upstream_policy_class="PickAndPlacePlannerPolicy",
        steps_requested=2,
        steps_executed=2,
        max_abs_qpos_delta=0.01,
        image_artifacts={
            "initial": "planner_views/initial_wrist_camera.png",
            "final": "planner_views/final_wrist_camera.png",
        },
    )
    evidence["runtime_diagnostics"] = {"renderer_adapter_enabled": True}
    evidence["worker_payload"] = {"renderer_adapter": {"camera": "wrist"}}
    if cleanup_binding is not None:
        evidence["cleanup_primitive_binding"] = cleanup_binding
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": PLANNER_BACKED_PROVENANCE,
        "primitive_provenance": PLANNER_BACKED_PROVENANCE,
        "manipulation_evidence": evidence,
    }
    path = base / "run_result.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path
