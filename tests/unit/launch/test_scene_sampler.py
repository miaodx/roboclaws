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

    procthor = projection["scene_sources"]["procthor-10k-val"]
    assert procthor["target_count"] == 10
    assert procthor["ready_count"] == 5
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
    procthor = report["sources"]["procthor-10k-val"]
    assert procthor["ui_needed_count"] == 0
    assert procthor["eval_needed_count"] == 5
    assert procthor["next_ui_scan_world_ids"] == []
    assert procthor["next_eval_scan_world_ids"] == [
        "molmospaces/procthor-10k-val/6",
        "molmospaces/procthor-10k-val/8",
    ]
    assert procthor["rejected_candidate_indices"] == [1, 4, 7]

    ithor = report["sources"]["ithor"]
    assert ithor["ui_needed_count"] == 3
    assert ithor["eval_needed_count"] == 10
    assert ithor["next_ui_scan_world_ids"] == [
        "molmospaces/ithor/0",
        "molmospaces/ithor/1",
        "molmospaces/ithor/2",
    ]
    assert ithor["next_eval_scan_world_ids"][:3] == ithor["next_ui_scan_world_ids"]


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

    ithor = report["sources"]["ithor"]
    assert ithor["molmospaces_get_scenes_call"] == 'get_scenes("ithor", "train")'
    assert ithor["next_scan_world_ids"][:3] == [
        "molmospaces/ithor/0",
        "molmospaces/ithor/1",
        "molmospaces/ithor/2",
    ]
    assert ithor["install_candidates"][0]["world_id"] == "molmospaces/ithor/0"
    assert ithor["install_candidates"][0]["primary_path"] == ""
    assert "mapping[0]" in ithor["install_candidates"][0]["install_command"]
    assert any(
        command["name"] == "rerun_readiness_after_prep"
        for command in ithor["operator_commands"]
    )


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
    assert candidate["world_id"] == "molmospaces/ithor/0"
    assert candidate["scanner_status"] == "blocked_missing_resources"
    assert candidate["install_command"].startswith(".venv/bin/python - <<'PY'")
    assert "render_scene_previews.py --world molmospaces/ithor/0" in candidate[
        "preview_command"
    ]
    assert "world=molmospaces/ithor/0" in candidate["map_build_product_smoke_command"]
