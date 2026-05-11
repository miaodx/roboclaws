from __future__ import annotations

from collections import Counter
from typing import Any

ADVISORY_SCHEMA_VERSION = "advisory_cleanup_scoring_v1"
DEFAULT_ADVISORY_EVALUATOR = "deterministic_semantic_rubric_v1"
BENIGN_LEVELS = frozenset({"preferred", "acceptable"})
REVIEW_LEVELS = frozenset({"questionable", "unknown"})


def build_advisory_evaluation(
    *,
    score: dict[str, Any],
    scenario_id: str,
    evaluator: str = DEFAULT_ADVISORY_EVALUATOR,
) -> dict[str, Any]:
    """Return a non-authoritative post-run cleanup review.

    The default adapter is deterministic and CI-safe. It has the same output
    shape a future live LLM scorer must satisfy, but it deliberately never
    changes the authoritative deterministic score.
    """
    rows = [dict(row) for row in score.get("object_results") or []]
    reviews = [_object_review(row) for row in rows]
    counts = Counter(str(item["advisory_verdict"]) for item in reviews)
    disagreement_count = counts["disagrees"] + counts["needs_review"]
    benign_count = counts["benign_disagreement"]
    exact_support_count = counts["supports_exact"]
    total = len(reviews)
    verdict = _overall_verdict(counts, total)
    return {
        "schema_version": ADVISORY_SCHEMA_VERSION,
        "evaluator": evaluator,
        "authoritative": False,
        "status": "ok",
        "scenario_id": scenario_id,
        "overall_verdict": verdict,
        "summary": _summary_text(
            verdict=verdict,
            total=total,
            exact_support_count=exact_support_count,
            benign_count=benign_count,
            disagreement_count=disagreement_count,
        ),
        "counts": {
            "total_reviewed": total,
            "supports_exact": exact_support_count,
            "benign_disagreement": benign_count,
            "needs_review": counts["needs_review"],
            "disagrees": counts["disagrees"],
        },
        "object_reviews": reviews,
        "non_authoritative_note": (
            "Advisory review is post-run evidence only. Deterministic score fields "
            "remain the pass/fail source."
        ),
    }


def _object_review(row: dict[str, Any]) -> dict[str, Any]:
    exact = bool(row.get("exact_private_match", row.get("restored", False)))
    semantic = str(row.get("semantic_acceptability") or "unknown")
    object_id = str(row.get("object_id", ""))
    actual_location_id = row.get("actual_location_id")
    if exact:
        verdict = "supports_exact"
        rationale = "Final location matches the deterministic private scorer."
    elif semantic in BENIGN_LEVELS:
        verdict = "benign_disagreement"
        rationale = (
            "Private exact target missed, but semantic acceptability marks the placement "
            f"as {semantic}."
        )
    elif semantic in REVIEW_LEVELS:
        verdict = "needs_review"
        rationale = f"Placement is {semantic}; operator review is useful."
    else:
        verdict = "disagrees"
        rationale = "Placement is not a tidy-plausible destination under the advisory rubric."
    return {
        "object_id": object_id,
        "actual_location_id": actual_location_id,
        "exact_private_match": exact,
        "semantic_acceptability": semantic,
        "semantic_reason": row.get("semantic_reason", ""),
        "advisory_verdict": verdict,
        "rationale": rationale,
    }


def _overall_verdict(counts: Counter[str], total: int) -> str:
    if total == 0:
        return "no_targets"
    if counts["disagrees"]:
        return "disagrees"
    if counts["needs_review"]:
        return "needs_review"
    if counts["benign_disagreement"]:
        return "supports_with_benign_disagreements"
    return "supports_deterministic_score"


def _summary_text(
    *,
    verdict: str,
    total: int,
    exact_support_count: int,
    benign_count: int,
    disagreement_count: int,
) -> str:
    if total == 0:
        return "No generated mess targets were available for advisory review."
    return (
        f"{verdict}: {exact_support_count}/{total} exact private matches, "
        f"{benign_count} benign semantic disagreements, "
        f"{disagreement_count} placements needing review or disagreement."
    )
