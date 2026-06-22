from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.household.report_sections_isaac import _load_isaac_scene_index_artifact


def test_load_isaac_scene_index_artifact_returns_object_payload(tmp_path: Path) -> None:
    source = tmp_path / "isaac_scene_index.json"
    payload = {"schema": "isaac_scene_index_artifact_v1", "agent_facing": False}
    source.write_text(json.dumps(payload), encoding="utf-8")

    assert _load_isaac_scene_index_artifact(tmp_path, "isaac_scene_index.json") == payload


@pytest.mark.parametrize("source", ["{", "[]"])
def test_load_isaac_scene_index_artifact_keeps_empty_on_bad_sources(
    tmp_path: Path,
    source: str,
) -> None:
    path = tmp_path / "isaac_scene_index.json"
    path.write_text(source, encoding="utf-8")

    assert _load_isaac_scene_index_artifact(tmp_path, "isaac_scene_index.json") == {}
    assert _load_isaac_scene_index_artifact(tmp_path, "missing.json") == {}
