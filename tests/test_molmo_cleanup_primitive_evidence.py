from __future__ import annotations

import pytest

from roboclaws.molmo_cleanup.cleanup_primitive_evidence import (
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


def _step(phase: str, provenance: str) -> dict[str, object]:
    step: dict[str, object] = {
        "phase": phase,
        "tool": phase,
        "status": "ok",
        "primitive_provenance": provenance,
        "state_mutation": "test_mutation",
    }
    if provenance == "planner_backed":
        step["planner_primitive_evidence"] = _planner_primitive_evidence(phase)
    return step


def _planner_primitive_evidence(phase: str) -> dict[str, object]:
    return {
        "schema": "planner_cleanup_primitive_executor_v1",
        "tool": phase,
        "object_id": "observed_001",
        "target_receptacle_id": "sink_01",
        "status": "ok",
        "primitive_provenance": "planner_backed",
        "planner_backed": True,
        "strict_proof_eligible": True,
        "exact_tool_match": True,
        "executor": "unit-test",
        "evidence": {"planner_run_id": f"{phase}-proof"},
        "blockers": [],
    }
