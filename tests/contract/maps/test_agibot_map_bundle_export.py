from __future__ import annotations

from pathlib import Path

import pytest

from roboclaws.household.agibot_map_defaults import DEFAULT_AGIBOT_MAP_ARTIFACT_DIR
from roboclaws.maps.bundle import validate_nav2_map_bundle
from scripts.maps.export_agibot_map_bundle import main as export_main


def test_export_agibot_map12_nav2_bundle(tmp_path: Path) -> None:
    if not _agibot_map_artifact_available(DEFAULT_AGIBOT_MAP_ARTIFACT_DIR):
        pytest.skip("Agibot robot_map_12 artifact is unavailable in this checkout")

    bundle_dir = tmp_path / "agibot-robot-map-12"

    rc = export_main(["--output-dir", str(bundle_dir)])

    validation = validate_nav2_map_bundle(bundle_dir)
    assert rc == 0
    assert validation.errors == ()
    assert validation.metadata["map_id"] == "agibot-robot-map-12_semantic_map"
    assert validation.metadata["room_count"] == 4
    assert validation.metadata["waypoint_count"] == 5
    assert (bundle_dir / "preview.png").is_file()


def _agibot_map_artifact_available(path: Path) -> bool:
    artifact_dir = path / "agibot" if (path / "agibot").is_dir() else path
    return (artifact_dir / "source.json").is_file()
