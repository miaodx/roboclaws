from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from roboclaws.launch.catalog import resolve_surface_launch
from roboclaws.launch.scene_sampler import (
    EVAL_STRESS_LANE,
    READINESS_BLOCKED,
    READINESS_REJECTED,
    UI_LANE,
    MolmoSpacesSceneRef,
    candidate_profile_report,
    candidate_readiness_report,
    eval_projection_metadata,
    eval_sample_id,
    eval_sample_payload,
    eval_sample_ref,
    eval_sampler_rows,
    eval_suite_payload,
    legacy_molmospaces_world_ids,
    parse_molmospaces_world_id,
    readiness_report,
    sampler_manifest,
    sampler_rows,
    scanner_admission_report,
    scanner_execution_plan,
    selection_gap_report,
    source_availability_report,
    source_prep_report,
    ui_molmospaces_world_ids,
    validate_sampler_manifest,
)
from roboclaws.launch.worlds import (
    MOLMOSPACES_CONSOLE_WORLD_IDS,
    MOLMOSPACES_LAUNCH_ALIAS_WORLD_IDS,
    WORLD_SPECS,
    world_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_scene_sampler_manifest_separates_ui_eval_and_alias_worlds() -> None:
    validate_sampler_manifest()

    assert ui_molmospaces_world_ids() == (
        "molmospaces/val_0",
        "molmospaces/val_2",
        "molmospaces/val_5",
        "molmospaces/procthor-objaverse-val/0",
        "molmospaces/procthor-objaverse-val/1",
        "molmospaces/procthor-objaverse-val/10",
    )
    assert MOLMOSPACES_CONSOLE_WORLD_IDS == ui_molmospaces_world_ids()
    assert MOLMOSPACES_LAUNCH_ALIAS_WORLD_IDS == legacy_molmospaces_world_ids()
    assert legacy_molmospaces_world_ids() == (
        "molmospaces/val_0",
        "molmospaces/val_1",
        "molmospaces/val_2",
        "molmospaces/val_3",
        "molmospaces/val_4",
        "molmospaces/val_5",
        "molmospaces/val_7",
        "molmospaces/val_9",
    )

    ui_rows = [row for row in sampler_rows() if row.ui_ready]
    eval_rows = eval_sampler_rows()
    assert [(row.scene_source, row.scene_index) for row in ui_rows] == [
        ("procthor-10k-val", 0),
        ("procthor-10k-val", 2),
        ("procthor-10k-val", 5),
        ("procthor-objaverse-val", 0),
        ("procthor-objaverse-val", 1),
        ("procthor-objaverse-val", 10),
    ]
    assert [(row.scene_source, row.scene_index) for row in eval_rows] == [
        ("procthor-10k-val", 0),
        ("procthor-10k-val", 2),
        ("procthor-10k-val", 3),
        ("procthor-10k-val", 5),
        ("procthor-10k-val", 9),
        ("procthor-10k-val", 10),
        ("procthor-10k-val", 11),
        ("procthor-10k-val", 12),
        ("procthor-10k-val", 13),
        ("procthor-10k-val", 15),
        ("procthor-objaverse-val", 0),
        ("procthor-objaverse-val", 1),
        ("procthor-objaverse-val", 4),
        ("procthor-objaverse-val", 5),
        ("procthor-objaverse-val", 7),
        ("procthor-objaverse-val", 10),
        ("procthor-objaverse-val", 11),
        ("procthor-objaverse-val", 12),
        ("procthor-objaverse-val", 13),
        ("procthor-objaverse-val", 14),
    ]
    assert all(UI_LANE in row.lanes for row in ui_rows)
    assert all(EVAL_STRESS_LANE in row.lanes for row in eval_rows)

    hidden_alias = WORLD_SPECS["molmospaces/val_9"]
    assert hidden_alias.availability == "hidden"
    assert hidden_alias.sampler_metadata
    assert hidden_alias.sampler_metadata["lanes"] == [EVAL_STRESS_LANE]
    assert WORLD_SPECS["molmospaces/val_4"].availability == "hidden"
    assert WORLD_SPECS["molmospaces/val_4"].sampler_metadata["lanes"] == []


def test_scene_sampler_ui_selection_is_seeded_and_room_diverse() -> None:
    manifest = sampler_manifest()
    policy = manifest["selection_policy"]

    assert policy["schema"] == "molmospaces_scene_sampler_selection_policy_v1"
    assert policy["selection_seed"] == "2026-06-16.source-diverse-selection-v1"
    assert policy["selection_strategy"] == (
        "deterministic_seeded_random_order_with_room_count_diversity_first"
    )
    assert policy["sources"]["procthor-10k-val"]["ui"]["selected_indices"] == [2, 5, 0]
    assert policy["sources"]["procthor-10k-val"]["ui"]["selected_room_counts"] == [10, 4, 7]
    assert policy["sources"]["procthor-objaverse-val"]["ui"]["selected_indices"] == [10, 0, 1]
    assert policy["sources"]["procthor-objaverse-val"]["ui"]["selected_room_counts"] == [
        5,
        4,
        7,
    ]


def test_legacy_molmospaces_alias_worlds_remain_launchable() -> None:
    for world_id in legacy_molmospaces_world_ids():
        plan = resolve_surface_launch(
            [
                "surface=household-world",
                f"world={world_id}",
                "backend=mujoco",
                "preset=map-build",
                "agent_engine=direct-runner",
                "evidence_lane=world-oracle-labels",
            ]
        )

        assert plan.world == world_id
        assert "scene_source=procthor-10k-val" in plan.overrides


def test_source_aware_candidate_worlds_are_launchable_but_not_default_visible() -> None:
    world_id = "molmospaces/ithor/1"

    spec = world_spec(world_id)
    plan = resolve_surface_launch(
        [
            "surface=household-world",
            f"world={world_id}",
            "backend=mujoco",
            "preset=map-build",
            "agent_engine=direct-runner",
            "evidence_lane=world-oracle-labels",
        ]
    )

    assert world_id not in WORLD_SPECS
    assert world_id not in MOLMOSPACES_CONSOLE_WORLD_IDS
    assert spec.availability == "hidden"
    assert spec.sampler_metadata["selected_reason"] == "dynamic_source_aware_scanner_candidate"
    assert plan.world == world_id
    assert "scene_source=ithor" in plan.overrides
    assert "scene_index=1" in plan.overrides
    assert "map_bundle=none" in plan.overrides


def test_scene_sampler_parses_legacy_and_source_aware_world_ids() -> None:
    assert parse_molmospaces_world_id("molmospaces/val_9") == MolmoSpacesSceneRef(
        scene_source="procthor-10k-val",
        scene_index=9,
    )
    assert parse_molmospaces_world_id("molmospaces/ithor/3") == MolmoSpacesSceneRef(
        scene_source="ithor",
        scene_index=3,
    )
    assert parse_molmospaces_world_id("molmospaces/holodeck-objaverse-val/12") == (
        MolmoSpacesSceneRef(scene_source="holodeck-objaverse-val", scene_index=12)
    )


def test_scene_sampler_rejects_unknown_source_aware_world_ids() -> None:
    with pytest.raises(ValueError, match="unsupported MolmoSpaces scene_source"):
        parse_molmospaces_world_id("molmospaces/unknown-source/1")
    with pytest.raises(ValueError, match="unsupported MolmoSpaces scene index"):
        parse_molmospaces_world_id("molmospaces/ithor/not-an-index")
    with pytest.raises(ValueError, match="negative MolmoSpaces scene index"):
        parse_molmospaces_world_id("molmospaces/ithor/-1")


def test_scene_sampler_records_partial_and_blocked_source_projection() -> None:
    projection = eval_projection_metadata()

    _assert_scene_sampler_projection_summary(projection)
    _assert_complete_projection_source(
        projection["scene_sources"]["procthor-10k-val"],
        scene_source="procthor-10k-val",
        expected_rejected_indices={1, 4, 7},
    )
    _assert_complete_projection_source(
        projection["scene_sources"]["procthor-objaverse-val"],
        scene_source="procthor-objaverse-val",
        expected_rejected_indices={2, 3, 6, 8, 9},
    )
    _assert_rejected_ithor_projection_source(projection["scene_sources"]["ithor"])
    _assert_rejected_holodeck_projection_source(
        projection["scene_sources"]["holodeck-objaverse-val"]
    )


def _assert_scene_sampler_projection_summary(projection: dict[str, object]) -> None:
    assert projection["summary"] == {
        "source_count": 4,
        "target_sample_count": 40,
        "ready_sample_count": 20,
        "partial_source_count": 0,
        "rejected_source_count": 2,
        "blocked_source_count": 0,
        "complete_source_count": 2,
        "blocked_row_count": 0,
        "rejected_row_count": 40,
        "blocked_or_rejected_row_count": 40,
        "remaining_sample_count": 20,
    }


def _assert_complete_projection_source(
    source_projection: dict[str, object],
    *,
    scene_source: str,
    expected_rejected_indices: set[int],
) -> None:
    assert source_projection["target_count"] == 10
    assert source_projection["ready_count"] == 10
    assert source_projection["partial_gap_count"] == 0
    assert source_projection["needed_count"] == 0
    assert source_projection["blocked_count"] == 0
    assert source_projection["rejected_count"] == len(expected_rejected_indices)
    assert source_projection["blocked_or_rejected_row_count"] == len(expected_rejected_indices)
    assert source_projection["support_status"] == "complete"
    assert source_projection["status"] == "complete"
    assert source_projection["sample_ids"] == [
        eval_sample_id(row) for row in eval_sampler_rows() if row.scene_source == scene_source
    ]
    blocked_indices = {
        row["scene_index"]
        for row in source_projection["blocked_rows"]
        if row["readiness_status"] == READINESS_REJECTED
    }
    assert blocked_indices == expected_rejected_indices
    if scene_source == "procthor-10k-val":
        assert any(
            row["scene_index"] == 4 and row["blocked_reason"] == "preview_not_reviewable"
            for row in source_projection["blocked_rows"]
        )


def _assert_rejected_ithor_projection_source(source_projection: dict[str, object]) -> None:
    assert source_projection["ready_count"] == 0
    assert source_projection["partial_gap_count"] == 10
    assert source_projection["needed_count"] == 10
    assert source_projection["blocked_count"] == 0
    assert source_projection["rejected_count"] == 12
    assert source_projection["blocked_or_rejected_row_count"] == 12
    assert source_projection["support_status"] == "rejected"
    assert source_projection["status"] == "rejected"
    assert {row["scene_index"] for row in source_projection["blocked_rows"]} == set(range(1, 13))
    assert all(
        row["readiness_status"] == READINESS_REJECTED for row in source_projection["blocked_rows"]
    )
    assert all(
        row["failure_class"] == "map_actionability_failure"
        for row in source_projection["blocked_rows"]
    )


def _assert_rejected_holodeck_projection_source(source_projection: dict[str, object]) -> None:
    assert source_projection["ready_count"] == 0
    assert source_projection["partial_gap_count"] == 10
    assert source_projection["needed_count"] == 10
    assert source_projection["blocked_count"] == 0
    assert source_projection["rejected_count"] == 20
    assert source_projection["blocked_or_rejected_row_count"] == 20
    assert source_projection["support_status"] == "rejected"
    assert source_projection["status"] == "rejected"
    assert {row["scene_index"] for row in source_projection["blocked_rows"]} == set(range(20))
    assert all(
        row["readiness_status"] == READINESS_REJECTED for row in source_projection["blocked_rows"]
    )
    assert all(
        row["failure_class"] == "map_actionability_failure"
        for row in source_projection["blocked_rows"]
    )


def test_scene_sampler_eval_suite_payload_matches_committed_fixture() -> None:
    fixture = json.loads(
        (REPO_ROOT / "evals/household_world/suites/scene_sampler_stress.json").read_text(
            encoding="utf-8"
        )
    )

    assert eval_suite_payload() == fixture


def test_scene_sampler_eval_sample_payloads_match_committed_fixtures() -> None:
    for row in eval_sampler_rows():
        fixture_path = REPO_ROOT / eval_sample_ref(row)
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

        assert eval_sample_payload(row) == fixture


def test_scene_sampler_eval_sample_payload_rejects_non_eval_rows() -> None:
    rejected = next(row for row in sampler_rows() if row.scene_index == 1)

    with pytest.raises(ValueError, match="eval-ready sampler row"):
        eval_sample_payload(rejected)


def test_scene_sampler_rejects_heuristic_room_category_provenance() -> None:
    manifest = copy.deepcopy(sampler_manifest())
    ready_row = next(
        row
        for row in manifest["rows"]
        if row["readiness_status"] == "ready" and row["scene_index"] == 0
    )
    ready_row["category_provenance"] = "heuristic_room_count"

    with pytest.raises(ValueError, match="trusted room-category provenance"):
        validate_sampler_manifest(manifest)


def test_scene_sampler_requires_exactly_three_ui_rows_per_visible_source() -> None:
    manifest = copy.deepcopy(sampler_manifest())
    row = next(row for row in manifest["rows"] if row["scene_index"] == 3)
    row["readiness_status"] = "ready"
    row["lanes"] = [UI_LANE, EVAL_STRESS_LANE]

    with pytest.raises(ValueError, match="more than 3 UI samples"):
        validate_sampler_manifest(manifest)


def test_scene_sampler_limits_eval_stress_rows_per_source() -> None:
    manifest = copy.deepcopy(sampler_manifest())
    template = next(
        row
        for row in manifest["rows"]
        if row["readiness_status"] == "ready" and row["scene_index"] == 0
    )
    manifest["rows"] = [
        {
            **template,
            "world_id": f"molmospaces/val_0/eval-{index}",
            "legacy_world_id": f"molmospaces/val_0/eval-{index}",
            "lanes": [EVAL_STRESS_LANE],
        }
        for index in range(11)
    ]

    with pytest.raises(ValueError, match="more than 10 eval-stress samples"):
        validate_sampler_manifest(manifest)


def test_scene_sampler_readiness_report_is_per_source() -> None:
    report = readiness_report()

    assert report["schema"] == "molmospaces_scene_sampler_readiness_report_v1"
    assert report["summary"]["source_count"] == 4
    assert report["summary"]["ui_supported_source_count"] == 2
    assert report["summary"]["eval_complete_source_count"] == 2
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["ui_status"] == "ready"
    assert procthor["ui_ready_count"] == 3
    assert procthor["eval_status"] == "complete"
    assert procthor["eval_ready_count"] == 10

    objaverse = report["sources"]["procthor-objaverse-val"]
    assert objaverse["ui_status"] == "ready"
    assert objaverse["ui_ready_count"] == 3
    assert objaverse["eval_status"] == "complete"
    assert objaverse["eval_ready_count"] == 10
    assert {row["scene_index"] for row in objaverse["blocked_rows"]} == {2, 3, 6, 8, 9}

    ithor = report["sources"]["ithor"]
    assert ithor["ui_status"] == "not_visible"
    assert ithor["ui_ready_count"] == 0
    assert ithor["eval_status"] == "partial_or_blocked"
    assert ithor["eval_ready_count"] == 0
    assert {row["scene_index"] for row in ithor["blocked_rows"]} == set(range(1, 13))
    assert all(row["failure_class"] == "map_actionability_failure" for row in ithor["blocked_rows"])

    holodeck = report["sources"]["holodeck-objaverse-val"]
    assert holodeck["ui_status"] == "not_visible"
    assert holodeck["ui_ready_count"] == 0
    assert holodeck["eval_status"] == "partial_or_blocked"
    assert holodeck["eval_ready_count"] == 0
    assert {row["scene_index"] for row in holodeck["blocked_rows"]} == set(range(20))
    assert all(
        row["failure_class"] == "map_actionability_failure" for row in holodeck["blocked_rows"]
    )


def test_scene_sampler_source_availability_reports_missing_molmospaces_module(
    monkeypatch,
) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )

    report = source_availability_report(candidate_indices=(0, 2))

    assert report["schema"] == "molmospaces_scene_source_availability_report_v1"
    assert report["probe_mode"] == "no_download_no_vlm"
    assert report["python_executable"]
    assert report["python_version"]
    assert report["molmospaces_module_available"] is False
    assert "molmospaces_module_stdout" in report
    assert "scene_root_stdout" in report
    assert report["summary"] == {
        "source_count": 4,
        "available_source_count": 0,
        "blocked_source_count": 4,
        "scene_root_available_source_count": 0,
        "source_dir_available_count": 0,
        "scene_index_map_available_count": 0,
        "missing_candidate_count": 8,
        "invalid_candidate_count": 0,
    }
    for source in ("ithor", "procthor-objaverse-val", "holodeck-objaverse-val"):
        source_report = report["sources"][source]
        assert source_report["status"] == "blocked"
        assert source_report["failure_class"] == "environment_blocked"
        assert "module is not importable" in source_report["blocked_reason"]
        assert source_report["candidate_indices"] == [0, 2]


def test_scene_sampler_candidate_readiness_keeps_ready_rejected_and_blocked_rows(
    monkeypatch,
) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )

    report = candidate_readiness_report(candidate_indices=(0, 1, 2))

    assert report["schema"] == "molmospaces_scene_sampler_candidate_readiness_v1"
    assert report["summary"] == {
        "source_count": 4,
        "candidate_count": 61,
        "ready_candidate_count": 20,
        "blocked_candidate_count": 1,
        "rejected_candidate_count": 40,
        "ui_ready_count": 6,
        "ui_needed_count": 6,
        "eval_ready_count": 20,
        "eval_needed_count": 20,
        "ui_supported_source_count": 2,
        "eval_complete_source_count": 2,
        "blocked_source_count": 1,
    }
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["ui_ready_count"] == 3
    assert procthor["eval_ready_count"] == 10
    assert procthor["candidate_count"] == 13
    assert procthor["ready_candidate_count"] == 10
    assert procthor["rejected_candidate_count"] == 3
    val_1 = next(item for item in procthor["candidates"] if item["scene_index"] == 1)
    assert val_1["readiness_status"] == READINESS_REJECTED
    assert val_1["blocked_reason"] == "fewer_than_three_public_navigation_areas"

    objaverse = report["sources"]["procthor-objaverse-val"]
    assert objaverse["ui_ready_count"] == 3
    assert objaverse["eval_ready_count"] == 10
    assert objaverse["candidate_count"] == 15
    assert objaverse["ready_candidate_count"] == 10
    assert objaverse["rejected_candidate_count"] == 5
    assert {
        item["scene_index"]
        for item in objaverse["candidates"]
        if item["readiness_status"] == READINESS_REJECTED
    } == {2, 3, 6, 8, 9}

    ithor = report["sources"]["ithor"]
    assert ithor["blocked_candidate_count"] == 1
    assert ithor["rejected_candidate_count"] == 12
    assert ithor["candidates"][0]["world_id"] == "molmospaces/ithor/0"
    assert ithor["candidates"][0]["failure_class"] == "environment_blocked"
    assert {
        item["scene_index"]
        for item in ithor["candidates"]
        if item["readiness_status"] == READINESS_REJECTED
    } == set(range(1, 13))

    holodeck = report["sources"]["holodeck-objaverse-val"]
    assert holodeck["blocked_candidate_count"] == 0
    assert holodeck["rejected_candidate_count"] == 20
    assert {
        item["scene_index"]
        for item in holodeck["candidates"]
        if item["readiness_status"] == READINESS_REJECTED
    } == set(range(20))


def test_scene_sampler_selection_gap_report_prioritizes_missing_samples(
    monkeypatch,
) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )

    report = selection_gap_report(candidate_indices=tuple(range(10)))

    assert report["schema"] == "molmospaces_scene_sampler_selection_gaps_v1"
    assert report["summary"]["ui_needed_count"] == 6
    assert report["summary"]["eval_needed_count"] == 20
    assert report["summary"]["candidate_range_sufficient_source_count"] == 0
    assert report["summary"]["candidate_range_insufficient_source_count"] == 0
    assert report["summary"]["source_prep_required_count"] == 0
    assert report["summary"]["next_actions"] == {
        "do_not_scan_without_new_human_curation": 2,
    }
    assert report["summary"]["worklist"][0] == {
        "scene_source": "ithor",
        "next_action": "do_not_scan_without_new_human_curation",
        "selection_capacity_status": "rejected_exhausted",
        "source_availability_status": "blocked",
        "ui_needed_count": 3,
        "ui_scan_candidate_count": 0,
        "eval_needed_count": 10,
        "eval_scan_candidate_count": 0,
        "next_scan_world_ids": [],
    }
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["ui_needed_count"] == 0
    assert procthor["eval_needed_count"] == 0
    assert procthor["selection_capacity_status"] == "complete"
    assert procthor["next_action"] == "none"
    assert procthor["next_ui_scan_world_ids"] == []
    assert procthor["next_eval_scan_world_ids"] == []
    assert procthor["rejected_candidate_indices"] == [1, 4, 7]

    objaverse = report["sources"]["procthor-objaverse-val"]
    assert objaverse["ui_needed_count"] == 0
    assert objaverse["eval_needed_count"] == 0
    assert objaverse["selection_capacity_status"] == "complete"
    assert objaverse["next_action"] == "none"
    assert objaverse["next_ui_scan_world_ids"] == []
    assert objaverse["next_eval_scan_world_ids"] == []
    assert objaverse["rejected_candidate_indices"] == [2, 3, 6, 8, 9]

    ithor = report["sources"]["ithor"]
    assert ithor["ui_needed_count"] == 3
    assert ithor["eval_needed_count"] == 10
    assert ithor["selection_capacity_status"] == "rejected_exhausted"
    assert ithor["next_action"] == "do_not_scan_without_new_human_curation"
    assert ithor["next_ui_scan_world_ids"] == []
    assert ithor["next_eval_scan_world_ids"] == []

    holodeck = report["sources"]["holodeck-objaverse-val"]
    assert holodeck["ui_needed_count"] == 3
    assert holodeck["eval_needed_count"] == 10
    assert holodeck["selection_capacity_status"] == "rejected_exhausted"
    assert holodeck["next_action"] == "do_not_scan_without_new_human_curation"
    assert holodeck["next_ui_scan_world_ids"] == []
    assert holodeck["next_eval_scan_world_ids"] == []
    assert holodeck["rejected_candidate_indices"] == list(range(20))


def test_scene_sampler_selection_gap_report_records_expanded_range_capacity(
    monkeypatch,
) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )

    report = selection_gap_report(candidate_indices=tuple(range(20)))

    assert report["summary"]["candidate_range_insufficient_source_count"] == 0
    assert report["summary"]["candidate_range_sufficient_source_count"] == 0
    assert report["summary"]["source_prep_required_count"] == 0
    assert report["summary"]["next_actions"] == {
        "do_not_scan_without_new_human_curation": 2,
    }
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["selection_capacity_status"] == "complete"
    assert procthor["next_action"] == "none"
    assert procthor["eval_scan_candidate_count"] == 0
    assert procthor["next_eval_scan_world_ids"] == []
    assert report["sources"]["procthor-objaverse-val"]["selection_capacity_status"] == "complete"
    assert (
        report["sources"]["holodeck-objaverse-val"]["selection_capacity_status"]
        == "rejected_exhausted"
    )


def test_scene_sampler_selection_gap_marks_ithor_rejected_when_assets_are_visible() -> None:
    report = selection_gap_report(candidate_indices=tuple(range(13)))

    ithor = report["sources"]["ithor"]
    assert ithor["selection_capacity_status"] == "rejected_exhausted"
    assert ithor["next_action"] == "do_not_scan_without_new_human_curation"
    assert ithor["next_ui_scan_world_ids"] == []
    assert ithor["next_eval_scan_world_ids"] == []
    assert ithor["rejected_candidate_indices"] == list(range(1, 13))

    prep = source_prep_report(candidate_indices=tuple(range(13)))
    assert prep["sources"]["ithor"]["prep_status"] == "rejected_exhausted"
    assert prep["sources"]["ithor"]["install_candidates"] == []
    assert prep["sources"]["ithor"]["missing_resources"] == []


def test_scene_sampler_candidate_profile_lists_metadata_first_worklists() -> None:
    report = candidate_profile_report(candidate_indices=tuple(range(10)))

    assert report["schema"] == "molmospaces_scene_sampler_candidate_profile_v1"
    assert report["probe_mode"] == "no_download_no_backend_no_vlm"
    assert report["download_policy"] == "manual_operator_only"
    assert report["summary"]["source_count"] == 4
    assert report["summary"]["metadata_worklist_source_count"] == 2
    assert report["summary"]["metadata_worklist_candidate_count"] == 20
    assert report["summary"]["next_actions"] == {
        "metadata_first_human_curation": 2,
    }
    assert report["sources"]["procthor-10k-val"]["profile_status"] == "complete"
    assert report["sources"]["procthor-objaverse-val"]["profile_status"] == "complete"

    ithor = report["sources"]["ithor"]
    assert ithor["profile_status"] == "metadata_worklist_ready"
    assert ithor["next_action"] == "metadata_first_human_curation"
    assert ithor["known_rejected_indices"] == list(range(1, 13))
    assert ithor["metadata_worklist_candidate_count"] == 10
    assert all(index not in range(1, 13) for index in ithor["metadata_worklist_indices"])
    assert ithor["metadata_worklist_world_ids"][0].startswith("molmospaces/ithor/")
    assert ithor["metadata_worklist_candidates"][0]["admission_effect"] == "none_profile_only"

    holodeck = report["sources"]["holodeck-objaverse-val"]
    assert holodeck["profile_status"] == "metadata_worklist_ready"
    assert holodeck["next_action"] == "metadata_first_human_curation"
    assert holodeck["known_rejected_indices"] == list(range(20))
    assert holodeck["metadata_worklist_candidate_count"] == 10
    assert min(holodeck["metadata_worklist_indices"]) >= 20
    assert holodeck["metadata_worklist_world_ids"][0].startswith(
        "molmospaces/holodeck-objaverse-val/"
    )


def test_scene_sampler_source_prep_report_lists_manual_prep_steps(monkeypatch) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )

    report = source_prep_report(candidate_indices=tuple(range(10)))

    assert report["schema"] == "molmospaces_scene_sampler_source_prep_v1"
    assert report["probe_mode"] == "no_download_no_vlm"
    assert report["download_policy"] == "manual_operator_only"
    assert report["summary"]["source_count"] == 4
    assert report["summary"]["missing_resource_summary"]["by_resource_type"] == {}
    assert report["summary"]["missing_resource_summary"]["by_reason"] == {}
    assert report["summary"]["prep_status_counts"] == {
        "complete": 2,
        "rejected_exhausted": 2,
    }
    assert report["summary"]["worklist"][0]["scene_source"] == "ithor"
    assert report["summary"]["worklist"][0]["next_action"] == "metadata_first_human_curation"
    assert report["summary"]["worklist"][0]["metadata_worklist_candidate_count"] == 10
    assert report["summary"]["worklist"][0]["install_candidate_count"] == 0

    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["prep_status"] == "complete"
    assert procthor["recommended_candidate_range"] == "0:9"
    assert procthor["molmospaces_get_scenes_call"] == 'get_scenes("procthor-10k", "val")'
    assert procthor["scene_index_map_status"] == "blocked"
    assert procthor["scene_index_map_reason"] == "molmo_spaces_module_unavailable"
    assert procthor["candidate_scene_refs"] == []
    assert procthor["missing_resources"] == []
    assert procthor["missing_resource_summary"]["by_resource_type"] == {}

    objaverse = report["sources"]["procthor-objaverse-val"]
    assert objaverse["prep_status"] == "complete"
    assert objaverse["recommended_candidate_range"] == "0:9"
    assert objaverse["molmospaces_get_scenes_call"] == ('get_scenes("procthor-objaverse", "val")')
    assert objaverse["missing_resources"] == []

    ithor = report["sources"]["ithor"]
    assert ithor["molmospaces_get_scenes_call"] == 'get_scenes("ithor", "train")'
    assert ithor["prep_status"] == "rejected_exhausted"
    assert ithor["candidate_profile_status"] == "metadata_worklist_ready"
    assert ithor["candidate_profile_next_action"] == "metadata_first_human_curation"
    assert ithor["metadata_worklist_candidate_count"] == 10
    assert ithor["next_scan_world_ids"] == []
    assert ithor["install_candidates"] == []
    assert any(
        command["name"] == "rerun_readiness_after_prep" for command in ithor["operator_commands"]
    )

    holodeck = report["sources"]["holodeck-objaverse-val"]
    assert holodeck["prep_status"] == "rejected_exhausted"
    assert holodeck["install_candidates"] == []
    assert holodeck["missing_resources"] == []


def test_scene_sampler_source_prep_install_command_resolves_dict_scene_refs() -> None:
    from roboclaws.launch.scene_sampler_prep import install_candidate_command

    command = install_candidate_command(
        dataset_name="procthor-10k",
        split="val",
        scene_index=4,
    )

    assert 'mapping = get_scenes("procthor-10k", "val")["val"]' in command
    assert "scene_ref = mapping[4]" in command
    assert "_scene_xml_path_from_ref(scene_ref, get_scenes_root())" in command
    assert "for role in ('base', 'physics', 'ceiling')" in command
    assert "install_scene_with_objects_and_grasps_from_path(scene_path)" in command


def test_scene_sampler_scanner_admission_report_records_missing_gates(monkeypatch) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )

    report = scanner_admission_report(candidate_indices=tuple(range(10)))

    assert report["schema"] == "molmospaces_scene_sampler_scanner_admission_v1"
    assert report["probe_mode"] == "no_download_no_backend_no_vlm"
    assert report["summary"]["admitted_count"] == 20
    assert report["summary"]["blocked_count"] == 3
    assert report["summary"]["rejected_count"] == 40
    assert report["summary"]["missing_gate_counts"]["source_asset_available"] == 3
    assert report["summary"]["missing_gate_counts"]["preview_metadata"] == 3
    procthor = report["sources"]["procthor-10k-val"]
    val_0 = next(item for item in procthor["admission_rows"] if item["scene_index"] == 0)
    assert val_0["admission_status"] == "admitted"
    assert val_0["lanes"] == [UI_LANE, EVAL_STRESS_LANE]
    val_1 = next(item for item in procthor["admission_rows"] if item["scene_index"] == 1)
    assert val_1["admission_status"] == "rejected"
    assert val_1["failure_class"] == "map_actionability_failure"

    objaverse = report["sources"]["procthor-objaverse-val"]
    objaverse_0 = next(item for item in objaverse["admission_rows"] if item["scene_index"] == 0)
    assert objaverse_0["admission_status"] == "admitted"
    assert objaverse_0["category_provenance"] == "source_metadata"
    objaverse_2 = next(item for item in objaverse["admission_rows"] if item["scene_index"] == 2)
    assert objaverse_2["admission_status"] == "rejected"
    assert objaverse_2["failure_class"] == "map_actionability_failure"

    holodeck = report["sources"]["holodeck-objaverse-val"]
    holodeck_0 = next(item for item in holodeck["admission_rows"] if item["scene_index"] == 0)
    assert holodeck_0["admission_status"] == "rejected"
    assert holodeck_0["failure_class"] == "map_actionability_failure"
    assert holodeck_0["blocked_reason"] == "fewer_than_three_public_navigation_areas"
    assert holodeck_0["category_provenance"] == "source_metadata"
    assert holodeck_0["missing_gates"] == []
    assert holodeck_0["next_action"] == "do_not_scan_without_new_human_curation"

    ithor = report["sources"]["ithor"]
    assert ithor["needed_ui_count"] == 3
    assert ithor["needed_eval_count"] == 10
    assert ithor["admission_rows"][0]["world_id"] == "molmospaces/ithor/0"
    assert ithor["admission_rows"][0]["admission_status"] == "blocked"
    ithor_1 = next(item for item in ithor["admission_rows"] if item["scene_index"] == 1)
    assert ithor_1["admission_status"] == "rejected"
    assert ithor_1["blocked_reason"] == "fewer_than_three_public_navigation_areas"


def test_scene_sampler_scanner_admission_accepts_reviewable_prepared_label_packets(
    monkeypatch,
) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "candidate_readiness_report",
        lambda *, candidate_indices: {
            "sources": {
                source: {
                    "ui_ready_count": 0,
                    "eval_ready_count": 0,
                    "candidates": []
                    if source != "ithor"
                    else [
                        {
                            "scene_family": "ithor",
                            "scene_split": "not_applicable",
                            "scene_source": "ithor",
                            "scene_index": 1,
                            "world_id": "molmospaces/ithor/1",
                            "readiness_status": READINESS_BLOCKED,
                            "lanes": [],
                            "eval_ready": False,
                            "failure_class": "environment_blocked",
                            "blocked_reason": "map build product smoke pending",
                            "selected_reason": "scanner_candidate_ready_for_product_smoke",
                            "room_count": 4,
                            "waypoint_count": 4,
                            "category_provenance": "prepared_visual_label_manifest",
                            "preview_statuses": {
                                "fpv": "reviewable",
                                "map": "reviewable",
                                "chase": "reviewable",
                                "topdown": "reviewable",
                            },
                            "candidate_file": {
                                "exists": True,
                                "path": "/tmp/FloorPlan1_physics.xml",
                            },
                        }
                    ],
                }
                for source in scene_sampler.SUPPORTED_SCENE_SOURCES
            }
        },
    )
    monkeypatch.setattr(
        scene_sampler,
        "selection_gap_report",
        lambda *, candidate_indices: {
            "sources": {
                source: {
                    "ui_needed_count": 3 if source == "ithor" else 0,
                    "eval_needed_count": 10 if source == "ithor" else 0,
                    "next_scan_candidates": [],
                }
                for source in scene_sampler.SUPPORTED_SCENE_SOURCES
            }
        },
    )

    report = scanner_admission_report(candidate_indices=(1,))
    row = report["sources"]["ithor"]["admission_rows"][0]

    assert row["admission_status"] == "blocked"
    assert row["passed_gates"] == [
        "source_asset_available",
        "preview_metadata",
        "public_room_count",
        "public_waypoints",
        "trusted_category_provenance",
    ]
    assert row["missing_gates"] == ["map_build_artifacts"]
    assert row["next_action"] == "run_map_build_product_smoke_before_eval_admission"


def test_scene_sampler_scanner_execution_plan_skips_rejected_exhausted_sources(
    monkeypatch,
) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )

    plan = scanner_execution_plan(candidate_indices=tuple(range(11)))
    ithor = plan["sources"]["ithor"]

    assert plan["schema"] == "molmospaces_scene_sampler_scanner_execution_plan_v1"
    assert plan["download_policy"] == "manual_operator_only"
    assert plan["summary"]["candidate_count"] == 0
    assert plan["summary"]["ready_for_product_smoke_count"] == 0
    assert plan["summary"]["blocked_count"] == 0
    assert plan["summary"]["blocked_source_count"] == 0
    assert ithor["prep_status"] == "rejected_exhausted"
    assert ithor["candidates"] == []
