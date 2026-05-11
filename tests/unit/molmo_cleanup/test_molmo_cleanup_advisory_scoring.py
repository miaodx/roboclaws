from __future__ import annotations

from roboclaws.molmo_cleanup.advisory_scoring import build_advisory_evaluation
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.scoring import score_cleanup
from roboclaws.molmo_cleanup.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)


def test_advisory_scoring_is_non_authoritative_and_object_level() -> None:
    scenario = build_cleanup_scenario(seed=7)
    final_locations = scenario.object_locations()
    final_locations["mug_01"] = "sink_01"
    final_locations["book_01"] = "desk_01"
    score = score_cleanup(final_locations, scenario.private_manifest).to_dict()
    annotated = annotate_score_with_semantic_acceptability(score, scenario)

    advisory = build_advisory_evaluation(score=annotated, scenario_id=scenario.scenario_id)

    assert advisory["schema_version"] == "advisory_cleanup_scoring_v1"
    assert advisory["authoritative"] is False
    assert advisory["status"] == "ok"
    assert advisory["counts"]["total_reviewed"] == len(advisory["object_reviews"])
    assert any(item["advisory_verdict"] == "supports_exact" for item in advisory["object_reviews"])
    assert any(
        item["advisory_verdict"] == "benign_disagreement" for item in advisory["object_reviews"]
    )
    assert "Deterministic score fields remain" in advisory["non_authoritative_note"]
