from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.household.scene_camera_usda_contract import prepared_scene_summary


def test_prepared_scene_summary_returns_object_payload(tmp_path: Path) -> None:
    scene = tmp_path / "scene.usda"
    scene.write_text("#usda 1.0\n", encoding="utf-8")
    payload = {"status": "ready", "visual_physics_status": "frozen_static_visual_usd"}
    (tmp_path / "summary.json").write_text(json.dumps(payload), encoding="utf-8")

    assert prepared_scene_summary(scene) == payload


@pytest.mark.parametrize("source", ["{", "[]"])
def test_prepared_scene_summary_keeps_empty_on_bad_optional_sources(
    tmp_path: Path,
    source: str,
) -> None:
    scene = tmp_path / "scene.usda"
    scene.write_text("#usda 1.0\n", encoding="utf-8")
    (tmp_path / "summary.json").write_text(source, encoding="utf-8")

    assert prepared_scene_summary(scene) == {}
    assert prepared_scene_summary(tmp_path / "missing_summary_dir" / "scene.usda") == {}
