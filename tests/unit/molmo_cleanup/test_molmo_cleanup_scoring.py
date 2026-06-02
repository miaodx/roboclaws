from __future__ import annotations

from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.scoring import score_cleanup


def test_score_cleanup_succeeds_at_three_of_five_targets() -> None:
    scenario = build_cleanup_scenario(seed=7)
    final_locations = scenario.object_locations()
    final_locations.update(
        {
            "mug_01": "sink_01",
            "book_01": "bookshelf_01",
            "towel_01": "laundry_hamper_01",
        }
    )

    score = score_cleanup(final_locations, scenario.private_manifest)

    assert score.status == "success"
    assert score.restored_count == 3
    assert score.total_targets == 5
    assert set(score.restored_object_ids) == {"mug_01", "book_01", "towel_01"}
    assert set(score.missed_object_ids) == {"apple_01", "toy_car_01"}


def test_score_cleanup_reports_partial_and_failed_states() -> None:
    scenario = build_cleanup_scenario(seed=7)
    partial_locations = scenario.object_locations()
    partial_locations["apple_01"] = "fridge_01"

    partial = score_cleanup(partial_locations, scenario.private_manifest)
    failed = score_cleanup({}, scenario.private_manifest)

    assert partial.status == "partial_success"
    assert partial.restored_count == 1
    assert failed.status == "failed"
    assert failed.restored_count == 0
    assert {row["actual_location_id"] for row in failed.object_results} == {None}


def test_score_cleanup_serializes_to_run_result_shape() -> None:
    scenario = build_cleanup_scenario(seed=7)
    final_locations = {
        "mug_01": "sink_01",
        "book_01": "bookshelf_01",
        "towel_01": "laundry_hamper_01",
        "apple_01": "fridge_01",
        "toy_car_01": "toy_bin_01",
    }

    payload = score_cleanup(final_locations, scenario.private_manifest).to_dict()

    assert payload["status"] == "success"
    assert payload["restored_count"] == 5
    assert payload["success_threshold"] == 3
    assert len(payload["object_results"]) == 5
