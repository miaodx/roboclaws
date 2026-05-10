from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

PLANNER_PROOF_QUALITY_SCHEMA = "planner_proof_quality_v1"
PLANNER_PROOF_QUALITY_SUMMARY_SCHEMA = "planner_proof_quality_summary_v1"

QUALITY_TIER_UNKNOWN = "unknown"
QUALITY_TIER_EXECUTION_WITHOUT_MOTION = "execution_without_motion"
QUALITY_TIER_ONE_STEP_MOTION = "one_step_motion"
QUALITY_TIER_MULTI_STEP_MOTION = "multi_step_motion"
QUALITY_TIER_CONTAINMENT_PROVEN = "containment_proven"

QUALITY_TIER_ORDER = {
    QUALITY_TIER_UNKNOWN: 0,
    QUALITY_TIER_EXECUTION_WITHOUT_MOTION: 1,
    QUALITY_TIER_ONE_STEP_MOTION: 2,
    QUALITY_TIER_MULTI_STEP_MOTION: 3,
    QUALITY_TIER_CONTAINMENT_PROVEN: 4,
}


def planner_proof_quality_evidence(proof: Mapping[str, Any]) -> dict[str, Any]:
    """Classify how much a planner proof actually demonstrates."""
    existing = proof.get("proof_quality")
    if isinstance(existing, Mapping) and existing.get("schema") == PLANNER_PROOF_QUALITY_SCHEMA:
        return dict(existing)

    steps_executed = _int_or_zero(proof.get("steps_executed"))
    max_abs_qpos_delta = _float_or_zero(proof.get("max_abs_qpos_delta"))
    one_step_motion = steps_executed >= 1 and max_abs_qpos_delta > 0.0
    multi_step_motion = steps_executed >= 2 and max_abs_qpos_delta > 0.0
    containment_proven = _containment_proven(proof)
    object_state_evidence_present = _object_state_evidence_present(proof)
    quality_tier = _quality_tier(
        steps_executed=steps_executed,
        max_abs_qpos_delta=max_abs_qpos_delta,
        multi_step_motion=multi_step_motion,
        one_step_motion=one_step_motion,
        containment_proven=containment_proven,
    )
    return {
        "schema": PLANNER_PROOF_QUALITY_SCHEMA,
        "quality_tier": quality_tier,
        "steps_executed": steps_executed,
        "max_abs_qpos_delta": max_abs_qpos_delta,
        "one_step_motion": one_step_motion,
        "multi_step_motion": multi_step_motion,
        "object_state_evidence_present": object_state_evidence_present,
        "containment_proven": containment_proven,
        "cleanup_primitive_binding_present": bool(proof.get("cleanup_primitive_binding")),
        "evidence_note": _evidence_note(
            quality_tier=quality_tier,
            containment_proven=containment_proven,
        ),
    }


def planner_proof_quality_summary(proofs: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    qualities = [planner_proof_quality_evidence(proof) for proof in proofs]
    tiers = Counter(
        str(quality.get("quality_tier") or QUALITY_TIER_UNKNOWN) for quality in qualities
    )
    steps = [int(quality.get("steps_executed") or 0) for quality in qualities]
    deltas = [float(quality.get("max_abs_qpos_delta") or 0.0) for quality in qualities]
    lowest_tier = min(
        tiers,
        key=lambda tier: QUALITY_TIER_ORDER.get(tier, 0),
        default=QUALITY_TIER_UNKNOWN,
    )
    return {
        "schema": PLANNER_PROOF_QUALITY_SUMMARY_SCHEMA,
        "proof_count": len(qualities),
        "quality_tier_counts": dict(sorted(tiers.items())),
        "lowest_quality_tier": lowest_tier,
        "min_steps_executed": min(steps, default=0),
        "max_steps_executed": max(steps, default=0),
        "max_abs_qpos_delta": max(deltas, default=0.0),
        "all_containment_proven": bool(qualities)
        and all(bool(quality.get("containment_proven")) for quality in qualities),
        "any_containment_proven": any(
            bool(quality.get("containment_proven")) for quality in qualities
        ),
    }


def validate_planner_proof_quality_evidence(
    quality: Mapping[str, Any],
    *,
    min_steps_executed: int = 1,
) -> None:
    assert quality.get("schema") == PLANNER_PROOF_QUALITY_SCHEMA, quality
    tier = str(quality.get("quality_tier") or "")
    assert tier in QUALITY_TIER_ORDER, quality
    assert int(quality.get("steps_executed") or 0) >= min_steps_executed, quality
    if min_steps_executed >= 1:
        assert bool(quality.get("one_step_motion")) is True, quality
    assert float(quality.get("max_abs_qpos_delta") or 0.0) > 0.0, quality


def format_quality_tier_counts(summary: Mapping[str, Any]) -> str:
    counts = summary.get("quality_tier_counts") or {}
    if not isinstance(counts, Mapping) or not counts:
        return QUALITY_TIER_UNKNOWN
    return ", ".join(f"{tier}={count}" for tier, count in sorted(counts.items()))


def _quality_tier(
    *,
    steps_executed: int,
    max_abs_qpos_delta: float,
    multi_step_motion: bool,
    one_step_motion: bool,
    containment_proven: bool,
) -> str:
    if containment_proven:
        return QUALITY_TIER_CONTAINMENT_PROVEN
    if multi_step_motion:
        return QUALITY_TIER_MULTI_STEP_MOTION
    if one_step_motion:
        return QUALITY_TIER_ONE_STEP_MOTION
    if steps_executed >= 1 and max_abs_qpos_delta <= 0.0:
        return QUALITY_TIER_EXECUTION_WITHOUT_MOTION
    return QUALITY_TIER_UNKNOWN


def _containment_proven(proof: Mapping[str, Any]) -> bool:
    if proof.get("containment_proven") is True:
        return True
    evidence = proof.get("object_state_evidence")
    if isinstance(evidence, Mapping) and evidence.get("containment_proven") is True:
        return True
    return False


def _object_state_evidence_present(proof: Mapping[str, Any]) -> bool:
    evidence = proof.get("object_state_evidence")
    if isinstance(evidence, Mapping) and evidence:
        return True
    return proof.get("containment_proven") is True


def _evidence_note(*, quality_tier: str, containment_proven: bool) -> str:
    if containment_proven:
        return "Planner proof includes object-state containment evidence."
    if quality_tier == QUALITY_TIER_MULTI_STEP_MOTION:
        return (
            "Planner proof demonstrates multi-step robot motion, but does not by itself "
            "prove final cleanup containment."
        )
    if quality_tier == QUALITY_TIER_ONE_STEP_MOTION:
        return (
            "Planner proof demonstrates one executed robot-motion step, but does not "
            "by itself prove pick/place completion or final cleanup containment."
        )
    if quality_tier == QUALITY_TIER_EXECUTION_WITHOUT_MOTION:
        return "Planner execution was recorded, but robot-state motion was not proven."
    return "Planner proof quality could not be classified from recorded evidence."


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
