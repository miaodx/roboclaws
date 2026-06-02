from __future__ import annotations

import pytest

from roboclaws.household.cleanup_primitive_evidence import (
    CLEANUP_PRIMITIVE_GATE_SCHEMA,
    cleanup_primitive_evidence_from_substeps,
    validate_cleanup_primitive_evidence,
)


def test_cleanup_primitive_evidence_blocks_api_semantic_subphases() -> None:
    evidence = cleanup_primitive_evidence_from_substeps(
        [
            {
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "steps": [
                    _step("navigate_to_object", "api_semantic"),
                    _step("pick", "api_semantic"),
                    _step("navigate_to_receptacle", "api_semantic"),
                    _step("place", "api_semantic"),
                ],
            }
        ]
    )

    validate_cleanup_primitive_evidence(evidence, accept_blocked_capability=True)
    assert evidence["schema"] == CLEANUP_PRIMITIVE_GATE_SCHEMA
    assert evidence["status"] == "blocked_capability"
    assert evidence["planner_backed"] is False
    assert evidence["strict_proof_eligible"] is False
    assert evidence["primitive_provenance_summary"] == {"api_semantic": 4}
    assert len(evidence["blockers"]) == 4
    with pytest.raises(AssertionError):
        validate_cleanup_primitive_evidence(evidence, require_planner_backed=True)


def test_cleanup_primitive_evidence_accepts_all_planner_backed_subphases() -> None:
    evidence = cleanup_primitive_evidence_from_substeps(
        [
            {
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "steps": [
                    _step("navigate_to_object", "planner_backed"),
                    _step("pick", "planner_backed"),
                    _step("navigate_to_receptacle", "planner_backed"),
                    _step("open_receptacle", "planner_backed"),
                    _step("place_inside", "planner_backed"),
                ],
            }
        ]
    )

    validate_cleanup_primitive_evidence(evidence, require_planner_backed=True)
    assert evidence["status"] == "planner_backed"
    assert evidence["planner_backed"] is True
    assert evidence["strict_proof_eligible"] is True
    assert evidence["primitive_provenance_summary"] == {"planner_backed": 5}
    assert not evidence["blockers"]


def test_cleanup_primitive_evidence_rejects_planner_backed_without_executor_evidence() -> None:
    evidence = cleanup_primitive_evidence_from_substeps(
        [
            {
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "steps": [
                    {
                        "phase": "pick",
                        "tool": "pick",
                        "status": "ok",
                        "primitive_provenance": "planner_backed",
                    }
                ],
            }
        ]
    )

    validate_cleanup_primitive_evidence(evidence, accept_blocked_capability=True)
    assert evidence["status"] == "blocked_capability"
    assert evidence["blockers"][0]["code"] == (
        "cleanup_subphase_missing_planner_primitive_evidence"
    )


def test_cleanup_primitive_evidence_rejects_object_mismatched_executor_evidence() -> None:
    evidence = cleanup_primitive_evidence_from_substeps(
        [
            {
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "steps": [
                    _step(
                        "pick",
                        "planner_backed",
                        evidence_object_id="observed_999",
                    )
                ],
            }
        ]
    )

    validate_cleanup_primitive_evidence(evidence, accept_blocked_capability=True)
    assert evidence["status"] == "blocked_capability"
    assert evidence["blockers"][0]["code"] == "cleanup_subphase_planner_object_mismatch"
    assert evidence["objects"][0]["subphases"][0]["object_id_matches"] is False


def test_cleanup_primitive_evidence_rejects_target_mismatched_executor_evidence() -> None:
    evidence = cleanup_primitive_evidence_from_substeps(
        [
            {
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "steps": [
                    _step(
                        "place",
                        "planner_backed",
                        evidence_target_receptacle_id="bookshelf_01",
                    )
                ],
            }
        ]
    )

    validate_cleanup_primitive_evidence(evidence, accept_blocked_capability=True)
    assert evidence["status"] == "blocked_capability"
    assert evidence["blockers"][0]["code"] == "cleanup_subphase_planner_target_mismatch"
    assert evidence["objects"][0]["subphases"][0]["target_receptacle_id_matches"] is False


def _step(
    phase: str,
    provenance: str,
    *,
    evidence_object_id: str = "observed_001",
    evidence_target_receptacle_id: str = "sink_01",
) -> dict[str, object]:
    step: dict[str, object] = {
        "phase": phase,
        "tool": phase,
        "status": "ok",
        "primitive_provenance": provenance,
        "state_mutation": "test_mutation",
    }
    if provenance == "planner_backed":
        step["planner_primitive_evidence"] = _planner_primitive_evidence(
            phase,
            object_id=evidence_object_id,
            target_receptacle_id=evidence_target_receptacle_id,
        )
    return step


def _planner_primitive_evidence(
    phase: str,
    *,
    object_id: str,
    target_receptacle_id: str,
) -> dict[str, object]:
    return {
        "schema": "planner_cleanup_primitive_executor_v1",
        "tool": phase,
        "object_id": object_id,
        "target_receptacle_id": target_receptacle_id,
        "status": "ok",
        "primitive_provenance": "planner_backed",
        "planner_backed": True,
        "strict_proof_eligible": True,
        "exact_tool_match": True,
        "executor": "unit-test",
        "evidence": {"planner_run_id": f"{phase}-proof"},
        "blockers": [],
    }
