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


def _step(phase: str, provenance: str) -> dict[str, object]:
    return {
        "phase": phase,
        "tool": phase,
        "status": "ok",
        "primitive_provenance": provenance,
        "state_mutation": "test_mutation",
    }
