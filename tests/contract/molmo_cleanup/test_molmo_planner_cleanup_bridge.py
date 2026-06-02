from __future__ import annotations

import pytest

from roboclaws.household.cleanup_primitive_evidence import (
    cleanup_primitive_evidence_from_substeps,
)
from roboclaws.household.planner_cleanup_bridge import (
    PLANNER_CLEANUP_BRIDGE_SCHEMA,
    planner_cleanup_bridge_evidence,
    validate_planner_cleanup_bridge_evidence,
)


def test_bridge_blocks_when_cleanup_subphases_are_api_semantic() -> None:
    evidence = planner_cleanup_bridge_evidence(
        planner_proof_attachment=_attachment(),
        cleanup_primitive_evidence=cleanup_primitive_evidence_from_substeps(
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
        ),
    )

    validate_planner_cleanup_bridge_evidence(evidence, accept_blocked_capability=True)
    assert evidence["schema"] == PLANNER_CLEANUP_BRIDGE_SCHEMA
    assert evidence["status"] == "blocked_capability"
    assert evidence["target_runtime_ready"] is True
    assert evidence["cleanup_primitives_ready"] is False
    assert evidence["blockers"][0]["code"] == "cleanup_subphases_not_planner_backed"
    with pytest.raises(AssertionError):
        validate_planner_cleanup_bridge_evidence(evidence, require_ready=True)


def test_bridge_accepts_target_and_cleanup_primitives_ready() -> None:
    evidence = planner_cleanup_bridge_evidence(
        planner_proof_attachment=_attachment(),
        cleanup_primitive_evidence=cleanup_primitive_evidence_from_substeps(
            [
                {
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "steps": [
                        _step("navigate_to_object", "planner_backed"),
                        _step("pick", "planner_backed"),
                        _step("navigate_to_receptacle", "planner_backed"),
                        _step("place", "planner_backed"),
                    ],
                }
            ]
        ),
    )

    validate_planner_cleanup_bridge_evidence(evidence, require_ready=True)
    assert evidence["status"] == "planner_backed"
    assert evidence["target_runtime_ready"] is True
    assert evidence["cleanup_primitives_ready"] is True
    assert evidence["blockers"] == []


def test_bridge_accepts_target_proof_bundle_and_cleanup_primitives_ready() -> None:
    evidence = planner_cleanup_bridge_evidence(
        planner_proof_attachment={
            "schema": "planner_backed_cleanup_proof_bundle_v1",
            "status": "planner_backed",
            "primitive_provenance": "planner_backed",
            "planner_backed": True,
            "strict_proof_eligible": True,
            "proof_count": 2,
            "attachments": [_attachment(), _attachment()],
        },
        cleanup_primitive_evidence=cleanup_primitive_evidence_from_substeps(
            [
                {
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "steps": [
                        _step("navigate_to_object", "planner_backed"),
                        _step("pick", "planner_backed"),
                        _step("navigate_to_receptacle", "planner_backed"),
                        _step("place", "planner_backed"),
                    ],
                }
            ]
        ),
    )

    validate_planner_cleanup_bridge_evidence(evidence, require_ready=True)
    assert evidence["target_runtime"]["schema"] == "planner_backed_cleanup_proof_bundle_v1"
    assert evidence["target_runtime"]["proof_count"] == 2
    assert evidence["status"] == "planner_backed"


def test_bridge_rejects_franka_proof_as_target_ready() -> None:
    evidence = planner_cleanup_bridge_evidence(
        planner_proof_attachment=_attachment(
            embodiment="franka",
            upstream_policy_class="PickAndPlacePlannerPolicy",
            curobo_available=False,
        ),
        cleanup_primitive_evidence=cleanup_primitive_evidence_from_substeps(
            [
                {
                    "object_id": "observed_001",
                    "target_receptacle_id": "sink_01",
                    "steps": [_step("place", "planner_backed")],
                }
            ]
        ),
    )

    validate_planner_cleanup_bridge_evidence(evidence, accept_blocked_capability=True)
    assert evidence["target_runtime_ready"] is False
    assert evidence["blockers"][0]["code"] == "target_runtime_not_rby1m_curobo_ready"


def _attachment(
    *,
    embodiment: str = "rby1m",
    upstream_policy_class: str = "CuroboPickAndPlacePlannerPolicy",
    curobo_available: bool = True,
) -> dict[str, object]:
    return {
        "schema": "planner_backed_cleanup_attachment_v1",
        "status": "planner_backed",
        "primitive_provenance": "planner_backed",
        "planner_backed": True,
        "strict_proof_eligible": True,
        "embodiment": embodiment,
        "task": "pick_and_place",
        "probe_mode": "execute",
        "upstream_policy_class": upstream_policy_class,
        "steps_executed": 2,
        "max_abs_qpos_delta": 0.01,
        "image_artifacts": {
            "initial": "planner_proof/initial.png",
            "final": "planner_proof/final.png",
        },
        "runtime_diagnostics": {
            "modules": {"curobo": {"available": curobo_available}},
        },
    }


def _step(phase: str, provenance: str) -> dict[str, object]:
    step: dict[str, object] = {
        "phase": phase,
        "tool": phase,
        "status": "ok",
        "primitive_provenance": provenance,
    }
    if provenance == "planner_backed":
        step["planner_primitive_evidence"] = {
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
    return step
