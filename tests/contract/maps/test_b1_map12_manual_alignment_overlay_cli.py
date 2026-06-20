from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "maps" / "render_b1_map12_manual_alignment_overlay.py"
VENDOR_MAP12_BUNDLE = (
    REPO_ROOT / "vendors" / "agibot_sdk" / "artifacts" / "maps" / "robot_map_12" / "agibot"
)


@pytest.mark.parametrize(
    ("source_path_name", "source", "message"),
    (
        (
            "scene_gaussian_topdown.json",
            "{not-json\n",
            "scene topdown render must contain valid JSON object",
        ),
        (
            "scene_gaussian_topdown.json",
            "[]\n",
            "scene topdown render must be a JSON object",
        ),
    ),
)
def test_manual_alignment_overlay_cli_rejects_bad_scene_topdown_render(
    tmp_path: Path,
    source_path_name: str,
    source: str,
    message: str,
) -> None:
    scene_topdown_render = tmp_path / source_path_name
    alignment_artifact = tmp_path / "alignment_residuals.json"
    output_dir = tmp_path / "overlay"
    scene_topdown_render.write_text(source, encoding="utf-8")
    alignment_artifact.write_text(json.dumps(_alignment_artifact()), encoding="utf-8")

    completed = _run_overlay_cli(
        scene_topdown_render=scene_topdown_render,
        alignment_artifact=alignment_artifact,
        output_dir=output_dir,
    )

    assert completed.returncode == 2
    assert message in completed.stderr
    assert str(scene_topdown_render) in completed.stderr
    assert not (output_dir / "map12_on_gaussian_topdown.json").exists()
    assert not (output_dir / "map12_on_gaussian_topdown.png").exists()


def test_manual_alignment_overlay_cli_rejects_missing_scene_topdown_render(
    tmp_path: Path,
) -> None:
    scene_topdown_render = tmp_path / "missing_scene_gaussian_topdown.json"
    alignment_artifact = tmp_path / "alignment_residuals.json"
    output_dir = tmp_path / "overlay"
    alignment_artifact.write_text(json.dumps(_alignment_artifact()), encoding="utf-8")

    completed = _run_overlay_cli(
        scene_topdown_render=scene_topdown_render,
        alignment_artifact=alignment_artifact,
        output_dir=output_dir,
    )

    assert completed.returncode == 2
    assert "scene topdown render missing" in completed.stderr
    assert str(scene_topdown_render) in completed.stderr
    assert not (output_dir / "map12_on_gaussian_topdown.json").exists()
    assert not (output_dir / "map12_on_gaussian_topdown.png").exists()


@pytest.mark.parametrize(
    ("source_path_name", "source", "message"),
    (
        (
            "alignment_residuals.json",
            "{not-json\n",
            "alignment artifact must contain valid JSON object",
        ),
        (
            "alignment_residuals.json",
            "[]\n",
            "alignment artifact must be a JSON object",
        ),
    ),
)
def test_manual_alignment_overlay_cli_rejects_bad_alignment_artifact(
    tmp_path: Path,
    source_path_name: str,
    source: str,
    message: str,
) -> None:
    scene_topdown_render = tmp_path / "scene_gaussian_topdown.json"
    alignment_artifact = tmp_path / source_path_name
    output_dir = tmp_path / "overlay"
    scene_topdown_render.write_text(json.dumps(_scene_topdown_render()), encoding="utf-8")
    alignment_artifact.write_text(source, encoding="utf-8")

    completed = _run_overlay_cli(
        scene_topdown_render=scene_topdown_render,
        alignment_artifact=alignment_artifact,
        output_dir=output_dir,
    )

    assert completed.returncode == 2
    assert message in completed.stderr
    assert str(alignment_artifact) in completed.stderr
    assert not (output_dir / "map12_on_gaussian_topdown.json").exists()
    assert not (output_dir / "map12_on_gaussian_topdown.png").exists()


def test_manual_alignment_overlay_cli_rejects_missing_alignment_artifact(
    tmp_path: Path,
) -> None:
    scene_topdown_render = tmp_path / "scene_gaussian_topdown.json"
    alignment_artifact = tmp_path / "missing_alignment_residuals.json"
    output_dir = tmp_path / "overlay"
    scene_topdown_render.write_text(json.dumps(_scene_topdown_render()), encoding="utf-8")

    completed = _run_overlay_cli(
        scene_topdown_render=scene_topdown_render,
        alignment_artifact=alignment_artifact,
        output_dir=output_dir,
    )

    assert completed.returncode == 2
    assert "alignment artifact missing" in completed.stderr
    assert str(alignment_artifact) in completed.stderr
    assert not (output_dir / "map12_on_gaussian_topdown.json").exists()
    assert not (output_dir / "map12_on_gaussian_topdown.png").exists()


def _run_overlay_cli(
    *,
    scene_topdown_render: Path,
    alignment_artifact: Path,
    output_dir: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--map-bundle",
            str(VENDOR_MAP12_BUNDLE),
            "--scene-topdown-render",
            str(scene_topdown_render),
            "--alignment-artifact",
            str(alignment_artifact),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
    )


def _scene_topdown_render() -> dict[str, object]:
    return {
        "schema": "b1_scene_gaussian_topdown_render_v1",
        "topdown_image": "missing-image.png",
    }


def _alignment_artifact() -> dict[str, object]:
    return {
        "global_alignment_status": "verified",
        "selected_transform": {
            "type": "rigid_2d",
            "source": "reviewed_correspondence_fit",
        },
        "residuals": [{"scene_xy": [0.0, 0.0], "map_xy": [0.0, 0.0]}],
    }
