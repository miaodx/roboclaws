from __future__ import annotations

import copy

import pytest

from roboclaws.launch.catalog import resolve_surface_launch
from roboclaws.launch.scene_sampler import (
    EVAL_STRESS_LANE,
    READINESS_BLOCKED,
    READINESS_REJECTED,
    UI_LANE,
    eval_projection_metadata,
    eval_sample_id,
    eval_sampler_rows,
    legacy_molmospaces_world_ids,
    sampler_manifest,
    sampler_rows,
    ui_molmospaces_world_ids,
    validate_sampler_manifest,
)
from roboclaws.launch.worlds import (
    MOLMOSPACES_CONSOLE_WORLD_IDS,
    MOLMOSPACES_LAUNCH_ALIAS_WORLD_IDS,
    WORLD_SPECS,
)


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

    with pytest.raises(ValueError, match="more than three UI samples"):
        validate_sampler_manifest(manifest)
