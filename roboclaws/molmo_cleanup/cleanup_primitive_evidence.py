from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from roboclaws.molmo_cleanup.manipulation_provenance import (
    BLOCKED_CAPABILITY_PROVENANCE,
    PLANNER_BACKED_PROVENANCE,
)
from roboclaws.molmo_cleanup.planner_primitive_executor import (
    PLANNER_PRIMITIVE_EXECUTOR_SCHEMA,
)
from roboclaws.molmo_cleanup.semantic_timeline import SEMANTIC_SUBPHASE_LABELS

CLEANUP_PRIMITIVE_GATE_SCHEMA = "planner_backed_cleanup_primitives_v1"
CLEANUP_PRIMITIVE_REQUIRED_PHASES = frozenset(SEMANTIC_SUBPHASE_LABELS)


def cleanup_primitive_evidence_from_substeps(
    substeps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize per-subphase cleanup primitive provenance."""
    objects = []
    blockers = []
    provenance_counts: Counter[str] = Counter()
    subphase_count = 0
    for item in substeps:
        object_rows = []
        for step in item.get("steps") or []:
            phase = str(step.get("phase") or "")
            if phase not in CLEANUP_PRIMITIVE_REQUIRED_PHASES:
                continue
            label, detail = SEMANTIC_SUBPHASE_LABELS[phase]
            provenance = str(step.get("primitive_provenance") or "missing")
            planner_backed = provenance == PLANNER_BACKED_PROVENANCE
            status = str(step.get("status") or "unknown")
            planner_primitive_evidence = _planner_primitive_evidence(step)
            strict_primitive_evidence = _strict_planner_primitive_evidence(
                planner_primitive_evidence,
                phase=phase,
            )
            strict_proof_eligible = planner_backed and status == "ok" and strict_primitive_evidence
            row = {
                "phase": phase,
                "label": label,
                "detail": detail,
                "tool": step.get("tool") or phase,
                "status": status,
                "primitive_provenance": provenance,
                "planner_backed": planner_backed,
                "strict_proof_eligible": strict_proof_eligible,
                "planner_primitive_evidence": planner_primitive_evidence,
                "state_mutation": step.get("state_mutation"),
                "state_sync_provenance": step.get("state_sync_provenance"),
            }
            object_rows.append(row)
            provenance_counts[provenance] += 1
            subphase_count += 1
            if not planner_backed:
                blockers.append(
                    {
                        "code": "cleanup_subphase_not_planner_backed",
                        "object_id": str(item.get("object_id", "")),
                        "phase": phase,
                        "primitive_provenance": provenance,
                        "message": (
                            f"{phase} used primitive_provenance={provenance}; "
                            "strict planner-backed cleanup requires planner_backed."
                        ),
                    }
                )
            elif status != "ok":
                blockers.append(
                    {
                        "code": "cleanup_subphase_not_ok",
                        "object_id": str(item.get("object_id", "")),
                        "phase": phase,
                        "status": status,
                        "message": (
                            f"{phase} status is {status}; strict planner-backed cleanup "
                            "requires status=ok."
                        ),
                    }
                )
            elif not strict_primitive_evidence:
                blockers.append(
                    {
                        "code": "cleanup_subphase_missing_planner_primitive_evidence",
                        "object_id": str(item.get("object_id", "")),
                        "phase": phase,
                        "message": (
                            f"{phase} is labeled planner_backed but lacks strict "
                            "planner_cleanup_primitive_executor_v1 evidence."
                        ),
                    }
                )
        objects.append(
            {
                "object_id": str(item.get("object_id", "")),
                "target_receptacle_id": str(item.get("target_receptacle_id", "")),
                "subphases": object_rows,
                "planner_backed": bool(object_rows)
                and all(row["planner_backed"] for row in object_rows),
                "strict_proof_eligible": bool(object_rows)
                and all(row["strict_proof_eligible"] for row in object_rows),
            }
        )
    planner_backed = subphase_count > 0 and not blockers
    status = PLANNER_BACKED_PROVENANCE if planner_backed else BLOCKED_CAPABILITY_PROVENANCE
    return {
        "schema": CLEANUP_PRIMITIVE_GATE_SCHEMA,
        "status": status,
        "primitive_provenance": status,
        "planner_backed": planner_backed,
        "strict_proof_eligible": planner_backed,
        "required_phases": sorted(CLEANUP_PRIMITIVE_REQUIRED_PHASES),
        "object_count": len(objects),
        "subphase_count": subphase_count,
        "primitive_provenance_summary": dict(sorted(provenance_counts.items())),
        "objects": objects,
        "blockers": blockers,
        "evidence_note": (
            "Strict cleanup primitive proof requires each cleanup-loop subphase "
            "to carry primitive_provenance=planner_backed. Attached standalone "
            "planner proof does not satisfy this gate."
        ),
    }


def validate_cleanup_primitive_evidence(
    evidence: dict[str, Any],
    *,
    require_planner_backed: bool = False,
    accept_blocked_capability: bool = False,
) -> None:
    assert evidence.get("schema") == CLEANUP_PRIMITIVE_GATE_SCHEMA, evidence
    assert int(evidence.get("subphase_count") or 0) >= 1, evidence
    assert evidence.get("objects"), evidence
    if require_planner_backed:
        assert evidence.get("status") == PLANNER_BACKED_PROVENANCE, evidence
        assert evidence.get("primitive_provenance") == PLANNER_BACKED_PROVENANCE, evidence
        assert evidence.get("planner_backed") is True, evidence
        assert evidence.get("strict_proof_eligible") is True, evidence
        assert not evidence.get("blockers"), evidence
        for item in evidence.get("objects") or []:
            assert item.get("planner_backed") is True, item
            for step in item.get("subphases") or []:
                assert step.get("primitive_provenance") == PLANNER_BACKED_PROVENANCE, step
                assert step.get("planner_backed") is True, step
                assert step.get("strict_proof_eligible") is True, step
                assert _strict_planner_primitive_evidence(
                    _planner_primitive_evidence(step),
                    phase=str(step.get("phase") or ""),
                ), step
        return
    if accept_blocked_capability:
        assert evidence.get("status") in {
            BLOCKED_CAPABILITY_PROVENANCE,
            PLANNER_BACKED_PROVENANCE,
        }, evidence
        if evidence.get("status") == BLOCKED_CAPABILITY_PROVENANCE:
            assert evidence.get("planner_backed") is False, evidence
            assert evidence.get("strict_proof_eligible") is False, evidence
            assert evidence.get("blockers"), evidence


def _planner_primitive_evidence(step: Mapping[str, Any]) -> dict[str, Any]:
    raw = step.get("planner_primitive_evidence") or {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def _strict_planner_primitive_evidence(
    evidence: Mapping[str, Any],
    *,
    phase: str,
) -> bool:
    payload = evidence.get("evidence") or {}
    return (
        evidence.get("schema") == PLANNER_PRIMITIVE_EXECUTOR_SCHEMA
        and evidence.get("tool") == phase
        and evidence.get("primitive_provenance") == PLANNER_BACKED_PROVENANCE
        and evidence.get("planner_backed") is True
        and evidence.get("strict_proof_eligible") is True
        and evidence.get("exact_tool_match") is True
        and isinstance(payload, Mapping)
        and bool(payload)
        and not evidence.get("blockers")
    )
