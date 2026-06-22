from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from scripts.operator_console.render_scene_previews import (
    PREVIEW_METADATA_SCHEMA,
    render_b1_map12_preview,
)


@pytest.mark.parametrize(
    ("source_text", "expected_reason"),
    [
        ("{", "B1 preview metadata source must contain valid JSON object"),
        ("[]", "B1 preview metadata source must contain a JSON object"),
    ],
)
def test_b1_preview_skip_existing_rejects_unreadable_metadata_without_rewrite(
    tmp_path: Path,
    source_text: str,
    expected_reason: str,
) -> None:
    metadata_path = tmp_path / "b1-map12-preview.json"
    metadata_path.write_text(source_text, encoding="utf-8")
    for suffix in ("fpv", "chase", "map", "topdown"):
        Image.new("RGB", (16, 16), (suffix.count("p"), 2, 3)).save(
            tmp_path / f"b1-map12-{suffix}.png"
        )

    result = render_b1_map12_preview(
        output_dir=tmp_path,
        width=320,
        height=200,
        skip_existing=True,
    )

    assert result["status"] == "metadata_unreadable"
    assert result["metadata"] == str(metadata_path)
    assert expected_reason in result["reason"]
    assert metadata_path.read_text(encoding="utf-8") == source_text
    for suffix in ("fpv", "chase", "map", "topdown"):
        assert (tmp_path / f"b1-map12-{suffix}.png").is_file()


@pytest.mark.parametrize(
    ("source_text", "expected_reason"),
    [
        ("{", "B1 camera preview artifact source must contain valid JSON object"),
        ("[]", "B1 camera preview artifact source must contain a JSON object"),
    ],
)
def test_b1_preview_reports_unreadable_camera_artifact_as_source_error(
    tmp_path: Path,
    source_text: str,
    expected_reason: str,
) -> None:
    camera_artifact = tmp_path / "run" / "run_result.json"
    camera_artifact.parent.mkdir()
    camera_artifact.write_text(source_text, encoding="utf-8")

    result = render_b1_map12_preview(
        output_dir=tmp_path,
        width=320,
        height=200,
        camera_artifact=camera_artifact,
    )

    assert result["status"] == "camera_preview_unavailable"
    assert result["camera_artifact"] == str(camera_artifact)
    assert result["camera_result"]["status"] == "artifact_unreadable"
    assert result["camera_result"]["artifact_path"] == str(camera_artifact)
    assert expected_reason in result["camera_result"]["reason"]
    assert not (tmp_path / "b1-map12-fpv.png").exists()
    assert not (tmp_path / "b1-map12-chase.png").exists()
    metadata = json.loads((tmp_path / "b1-map12-preview.json").read_text(encoding="utf-8"))
    assert metadata["schema"] == PREVIEW_METADATA_SCHEMA
    assert metadata["views"] == {}
