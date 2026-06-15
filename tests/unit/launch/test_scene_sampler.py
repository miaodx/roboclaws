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
        "molmospaces/val_9",
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
    assert [row.scene_index for row in ui_rows] == [0, 2, 9]
    assert [row.scene_index for row in eval_rows] == [0, 2, 3, 5, 9]
    assert all(UI_LANE in row.lanes for row in ui_rows)
    assert all(EVAL_STRESS_LANE in row.lanes for row in eval_rows)

    hidden_alias = WORLD_SPECS["molmospaces/val_5"]
    assert hidden_alias.availability == "hidden"
    assert hidden_alias.sampler_metadata
    assert hidden_alias.sampler_metadata["lanes"] == [EVAL_STRESS_LANE]
    assert WORLD_SPECS["molmospaces/val_4"].availability == "hidden"
    assert WORLD_SPECS["molmospaces/val_4"].sampler_metadata["lanes"] == []


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

    assert projection["summary"] == {
        "source_count": 4,
        "target_sample_count": 40,
        "ready_sample_count": 5,
        "partial_source_count": 1,
        "blocked_source_count": 3,
        "complete_source_count": 0,
        "blocked_row_count": 3,
        "rejected_row_count": 3,
        "blocked_or_rejected_row_count": 6,
        "remaining_sample_count": 35,
    }

    procthor = projection["scene_sources"]["procthor-10k-val"]
    assert procthor["target_count"] == 10
    assert procthor["ready_count"] == 5
    assert procthor["partial_gap_count"] == 5
    assert procthor["needed_count"] == 5
    assert procthor["blocked_count"] == 0
    assert procthor["rejected_count"] == 3
    assert procthor["blocked_or_rejected_row_count"] == 3
    assert procthor["support_status"] == "partial"
    assert procthor["status"] == "partial_or_blocked"
    assert procthor["sample_ids"] == [eval_sample_id(row) for row in eval_sampler_rows()]
    blocked_indices = {
        row["scene_index"]
        for row in procthor["blocked_rows"]
        if row["readiness_status"] == READINESS_REJECTED
    }
    assert blocked_indices == {1, 4, 7}
    assert any(
        row["scene_index"] == 4 and row["blocked_reason"] == "preview_not_reviewable"
        for row in procthor["blocked_rows"]
    )

    for source in ("ithor", "procthor-objaverse-val", "holodeck-objaverse-val"):
        source_projection = projection["scene_sources"][source]
        assert source_projection["ready_count"] == 0
        assert source_projection["partial_gap_count"] == 10
        assert source_projection["needed_count"] == 10
        assert source_projection["blocked_count"] == 1
        assert source_projection["rejected_count"] == 0
        assert source_projection["blocked_or_rejected_row_count"] == 1
        assert source_projection["support_status"] == "blocked"
        assert source_projection["status"] == "partial_or_blocked"
        assert source_projection["blocked_rows"][0]["readiness_status"] == READINESS_BLOCKED
        assert source_projection["blocked_rows"][0]["failure_class"] == "environment_blocked"


def test_scene_sampler_eval_suite_payload_matches_committed_fixture() -> None:
    fixture = json.loads(
        (
            REPO_ROOT / "evals/household_world/suites/scene_sampler_stress.json"
        ).read_text(encoding="utf-8")
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
    assert report["summary"]["ui_supported_source_count"] == 1
    assert report["summary"]["eval_complete_source_count"] == 0
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["ui_status"] == "ready"
    assert procthor["ui_ready_count"] == 3
    assert procthor["eval_status"] == "partial_or_blocked"
    assert procthor["eval_ready_count"] == 5

    for source in ("ithor", "procthor-objaverse-val", "holodeck-objaverse-val"):
        source_report = report["sources"][source]
        assert source_report["ui_status"] == "not_visible"
        assert source_report["ui_ready_count"] == 0
        assert source_report["eval_status"] == "partial_or_blocked"
        assert source_report["eval_ready_count"] == 0
        assert source_report["blocked_rows"][0]["failure_class"] == "environment_blocked"


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
        "candidate_count": 12,
        "ready_candidate_count": 2,
        "blocked_candidate_count": 9,
        "rejected_candidate_count": 1,
        "ui_ready_count": 2,
        "ui_needed_count": 10,
        "eval_ready_count": 2,
        "eval_needed_count": 38,
        "ui_supported_source_count": 0,
        "eval_complete_source_count": 0,
        "blocked_source_count": 3,
    }
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["ui_ready_count"] == 2
    assert procthor["eval_ready_count"] == 2
    assert procthor["candidate_count"] == 3
    assert procthor["ready_candidate_count"] == 2
    assert procthor["rejected_candidate_count"] == 1
    val_1 = next(item for item in procthor["candidates"] if item["scene_index"] == 1)
    assert val_1["readiness_status"] == READINESS_REJECTED
    assert val_1["blocked_reason"] == "fewer_than_three_public_navigation_areas"

    ithor = report["sources"]["ithor"]
    assert ithor["blocked_candidate_count"] == 3
    assert ithor["candidates"][0]["world_id"] == "molmospaces/ithor/0"
    assert ithor["candidates"][0]["failure_class"] == "environment_blocked"


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
    assert report["summary"]["ui_needed_count"] == 9
    assert report["summary"]["eval_needed_count"] == 35
    assert report["summary"]["candidate_range_sufficient_source_count"] == 3
    assert report["summary"]["candidate_range_insufficient_source_count"] == 1
    assert report["summary"]["source_prep_required_count"] == 3
    assert report["summary"]["next_actions"] == {
        "expand_candidate_range": 1,
        "run_source_prep_before_scanner": 3,
    }
    assert report["summary"]["worklist"][0] == {
        "scene_source": "procthor-10k-val",
        "next_action": "expand_candidate_range",
        "selection_capacity_status": "candidate_range_insufficient",
        "source_availability_status": "blocked",
        "ui_needed_count": 0,
        "ui_scan_candidate_count": 0,
        "eval_needed_count": 5,
        "eval_scan_candidate_count": 2,
        "next_scan_world_ids": [
            "molmospaces/procthor-10k-val/6",
            "molmospaces/procthor-10k-val/8",
        ],
    }
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["ui_needed_count"] == 0
    assert procthor["eval_needed_count"] == 5
    assert procthor["selection_capacity_status"] == "candidate_range_insufficient"
    assert procthor["next_action"] == "expand_candidate_range"
    assert procthor["next_ui_scan_world_ids"] == []
    assert procthor["next_eval_scan_world_ids"] == [
        "molmospaces/procthor-10k-val/6",
        "molmospaces/procthor-10k-val/8",
    ]
    assert procthor["rejected_candidate_indices"] == [1, 4, 7]

    ithor = report["sources"]["ithor"]
    assert ithor["ui_needed_count"] == 3
    assert ithor["eval_needed_count"] == 10
    assert ithor["selection_capacity_status"] == "candidate_range_sufficient"
    assert ithor["next_action"] == "run_source_prep_before_scanner"
    assert ithor["next_ui_scan_world_ids"] == [
        "molmospaces/ithor/0",
        "molmospaces/ithor/1",
        "molmospaces/ithor/2",
    ]
    assert ithor["next_eval_scan_world_ids"][:3] == ithor["next_ui_scan_world_ids"]


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
    assert report["summary"]["candidate_range_sufficient_source_count"] == 4
    assert report["summary"]["source_prep_required_count"] == 4
    assert report["summary"]["next_actions"] == {"run_source_prep_before_scanner": 4}
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["selection_capacity_status"] == "candidate_range_sufficient"
    assert procthor["next_action"] == "run_source_prep_before_scanner"
    assert procthor["eval_scan_candidate_count"] == 5
    assert procthor["next_eval_scan_world_ids"][:5] == [
        "molmospaces/procthor-10k-val/6",
        "molmospaces/procthor-10k-val/8",
        "molmospaces/procthor-10k-val/10",
        "molmospaces/procthor-10k-val/11",
        "molmospaces/procthor-10k-val/12",
    ]


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
    assert report["summary"]["missing_resource_summary"]["by_resource_type"] == {
        "scene_source_dir": 4,
        "scene_xml": 40,
    }
    assert report["summary"]["missing_resource_summary"]["by_reason"] == {
        "candidate_xml_missing": 40,
        "source_dir_missing": 4,
    }
    assert report["summary"]["prep_status_counts"] == {
        "blocked_molmospaces_module": 4,
    }
    assert report["summary"]["worklist"][0]["scene_source"] == "procthor-10k-val"
    assert report["summary"]["worklist"][0]["next_action"] == "install_repo_dev_runtime"
    assert report["summary"]["worklist"][0]["install_candidate_count"] == 2

    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["prep_status"] == "blocked_molmospaces_module"
    assert procthor["recommended_candidate_range"] == "0:19"
    assert procthor["molmospaces_get_scenes_call"] == 'get_scenes("procthor-10k", "val")'
    assert procthor["scene_index_map_status"] == "blocked"
    assert procthor["scene_index_map_reason"] == "molmo_spaces_module_unavailable"
    assert procthor["candidate_scene_refs"] == []
    assert any(
        item["resource_type"] == "scene_xml" and item["scene_index"] == 6
        for item in procthor["missing_resources"]
    )
    assert procthor["missing_resource_summary"]["by_resource_type"] == {
        "scene_source_dir": 1,
        "scene_xml": 10,
    }

    ithor = report["sources"]["ithor"]
    assert ithor["molmospaces_get_scenes_call"] == 'get_scenes("ithor", "train")'
    assert ithor["next_scan_world_ids"][:3] == [
        "molmospaces/ithor/0",
        "molmospaces/ithor/1",
        "molmospaces/ithor/2",
    ]
    assert ithor["install_candidates"][0]["world_id"] == "molmospaces/ithor/0"
    assert ithor["install_candidates"][0]["primary_path"] == ""
    install_command = ithor["install_candidates"][0]["install_command"]
    assert "mapping[0]" in install_command
    assert "_scene_xml_path_from_ref(scene_ref, get_scenes_root())" in install_command
    assert "for role in ('base', 'physics', 'ceiling')" in install_command
    assert any(
        command["name"] == "rerun_readiness_after_prep"
        for command in ithor["operator_commands"]
    )


def test_scene_sampler_source_prep_install_command_resolves_dict_scene_refs() -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    command = scene_sampler._install_candidate_command(
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
    assert report["summary"]["admitted_count"] == 5
    assert report["summary"]["blocked_count"] == 32
    assert report["summary"]["rejected_count"] == 3
    assert report["summary"]["missing_gate_counts"]["source_asset_available"] == 32
    assert report["summary"]["missing_gate_counts"]["preview_metadata"] == 32
    procthor = report["sources"]["procthor-10k-val"]
    val_0 = next(item for item in procthor["admission_rows"] if item["scene_index"] == 0)
    assert val_0["admission_status"] == "admitted"
    assert val_0["lanes"] == [UI_LANE, EVAL_STRESS_LANE]
    val_1 = next(item for item in procthor["admission_rows"] if item["scene_index"] == 1)
    assert val_1["admission_status"] == "rejected"
    assert val_1["failure_class"] == "map_actionability_failure"
    val_6 = next(item for item in procthor["admission_rows"] if item["scene_index"] == 6)
    assert val_6["admission_status"] == "blocked"
    assert val_6["required_gates"] == [
        "source_asset_available",
        "preview_metadata",
        "public_room_count",
        "public_waypoints",
        "trusted_category_provenance",
        "map_build_artifacts",
    ]
    assert "source_asset_available" in val_6["missing_gates"]
    assert "preview_metadata" in val_6["missing_gates"]
    assert val_6["next_action"] == "run_manual_source_prep_before_scanner"

    ithor = report["sources"]["ithor"]
    assert ithor["needed_ui_count"] == 3
    assert ithor["needed_eval_count"] == 10
    assert ithor["admission_rows"][0]["world_id"] == "molmospaces/ithor/0"
    assert ithor["admission_rows"][0]["admission_status"] == "blocked"


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


def test_scene_sampler_scanner_execution_plan_records_commands(monkeypatch) -> None:
    import roboclaws.launch.scene_sampler as scene_sampler

    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )

    plan = scanner_execution_plan(candidate_indices=tuple(range(11)))
    ithor = plan["sources"]["ithor"]
    candidate = ithor["candidates"][0]

    assert plan["schema"] == "molmospaces_scene_sampler_scanner_execution_plan_v1"
    assert plan["download_policy"] == "manual_operator_only"
    assert plan["summary"]["candidate_count"] == 33
    assert plan["summary"]["ready_for_product_smoke_count"] == 0
    assert plan["summary"]["blocked_count"] == 33
    assert plan["summary"]["blocked_source_count"] == 4
    assert candidate["world_id"] == "molmospaces/ithor/0"
    assert candidate["scanner_status"] == "blocked_missing_resources"
    assert candidate["scene_family"] == "ithor"
    assert candidate["scene_split"] == "not_applicable"
    assert candidate["readiness_status"] == "blocked"
    assert candidate["failure_class"] == "environment_blocked"
    assert candidate["room_count"] == 0
    assert candidate["waypoint_count"] == 0
    assert candidate["category_provenance"] == "unavailable"
    assert candidate["required_gates"] == [
        "source_asset_available",
        "preview_metadata",
        "public_room_count",
        "public_waypoints",
        "trusted_category_provenance",
        "map_build_artifacts",
    ]
    assert "source_asset_available" in candidate["missing_gates"]
    assert candidate["candidate_file"]["source"] == "legacy_val_xml_path"
    assert candidate["install_command"].startswith(".venv/bin/python - <<'PY'")
    assert "render_scene_previews.py --world molmospaces/ithor/0" in candidate[
        "preview_command"
    ]
    assert "world=molmospaces/ithor/0" in candidate["map_build_product_smoke_command"]
