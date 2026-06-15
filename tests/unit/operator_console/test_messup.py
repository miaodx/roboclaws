from __future__ import annotations

from pathlib import Path

from roboclaws.operator_console.messup import (
    _molmospaces_scene_ref,
    _resolve_molmospaces_inventory_scene_xml,
    preview_messup_from_inventory,
)


def test_messup_preview_reports_ready_when_requested_targets_are_available() -> None:
    payload = preview_messup_from_inventory(
        objects=[
            {"object_id": "cup", "category": "Cup"},
            {"object_id": "book", "category": "Book"},
            {"object_id": "apple", "category": "Apple"},
        ],
        receptacles=[
            {"receptacle_id": "sink", "category": "Sink"},
            {"receptacle_id": "desk", "category": "Desk"},
            {"receptacle_id": "fridge", "category": "Fridge"},
        ],
        world_id="molmospaces/val_test",
        backend_id="mujoco",
        scenario_setup="relocate-cleanup-related-objects",
        requested_count=3,
        seed=7,
    )

    assert payload["schema"] == "operator_console_messup_preview_v1"
    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["requested_count"] == 3
    assert payload["selected_count"] == 3
    assert payload["eligible_count"] == 3


def test_messup_preview_explains_partial_scene_without_blocking_baseline() -> None:
    payload = preview_messup_from_inventory(
        objects=[
            {"object_id": "bowl", "category": "Bowl"},
            {"object_id": "remote", "category": "RemoteControl"},
            {"object_id": "cell", "category": "CellPhone"},
        ],
        receptacles=[
            {"receptacle_id": "sink", "category": "Sink"},
        ],
        world_id="molmospaces/val_test",
        backend_id="mujoco",
        scenario_setup="relocate-cleanup-related-objects",
        requested_count=2,
        seed=7,
    )

    assert payload["ok"] is False
    assert payload["status"] == "partial"
    assert payload["requested_count"] == 2
    assert payload["selected_count"] == 1
    assert payload["eligible_count"] == 1
    assert "selected route can still run" in payload["message"]
    remote_rule = next(
        row for row in payload["rule_diagnostics"] if row["object_categories"] == ["RemoteControl"]
    )
    assert remote_rule["object_count"] == 1
    assert remote_rule["target_receptacle_count"] == 0


def test_messup_preview_scene_ref_accepts_source_aware_world_id() -> None:
    assert _molmospaces_scene_ref("molmospaces/ithor/3") == ("ithor", 3)


def test_messup_preview_inventory_resolves_source_aware_scene_path(tmp_path: Path) -> None:
    scenes_root = tmp_path / "scenes"

    def fake_get_scenes(dataset_name: str, split: str):
        assert dataset_name == "ithor"
        assert split == "train"
        return {"train": {1: "ithor/FloorPlan1_physics.xml"}}

    scene_xml = _resolve_molmospaces_inventory_scene_xml(
        "molmospaces/ithor/1",
        get_scenes=fake_get_scenes,
        get_scenes_root=lambda: scenes_root,
    )

    assert scene_xml == scenes_root / "ithor" / "FloorPlan1_physics.xml"
    assert "val_1.xml" not in str(scene_xml)
