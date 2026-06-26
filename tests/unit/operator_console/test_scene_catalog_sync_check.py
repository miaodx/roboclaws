from __future__ import annotations

import shutil
from pathlib import Path

from scripts.operator_console import check_scene_catalog_sync


def test_scene_catalog_sync_check_passes_for_committed_scene_artifacts(tmp_path: Path) -> None:
    report = check_scene_catalog_sync.check_scene_catalog_sync(output_dir=tmp_path)

    assert report["status"] == "success"
    assert report["issues"] == []
    assert report["summary"]["molmospaces_console_world_count"] == 6


def test_scene_catalog_sync_check_reports_missing_generated_sample(
    monkeypatch,
    tmp_path: Path,
) -> None:
    committed_samples = tmp_path / "committed-samples"
    shutil.copytree(
        check_scene_catalog_sync.COMMITTED_SCENE_SAMPLER_SAMPLES,
        committed_samples,
    )
    (committed_samples / "procthor-10k-val_0_map_build.json").unlink()
    monkeypatch.setattr(
        check_scene_catalog_sync,
        "COMMITTED_SCENE_SAMPLER_SAMPLES",
        committed_samples,
    )

    report = check_scene_catalog_sync.check_scene_catalog_sync(output_dir=tmp_path / "generated")

    assert report["status"] == "failed"
    assert {(issue["check"], issue["message"]) for issue in report["issues"]} >= {
        (
            "scene_sampler_samples",
            "missing committed scene-sampler eval sample: procthor-10k-val_0_map_build.json",
        )
    }


def test_scene_catalog_sync_check_reports_incomplete_console_preview(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        check_scene_catalog_sync,
        "MOLMOSPACES_CONSOLE_WORLD_IDS",
        ("molmospaces/procthor-10k-val/11",),
    )
    monkeypatch.setattr(
        check_scene_catalog_sync,
        "WORLD_SPECS",
        {
            "molmospaces/procthor-10k-val/11": type(
                "World",
                (),
                {
                    "preview_assets": (
                        (
                            "map",
                            "/asset-previews/maps/molmospaces/procthor-10k-val/11/preview.png",
                        ),
                    )
                },
            )()
        },
    )

    report = check_scene_catalog_sync.check_scene_catalog_sync(output_dir=tmp_path)

    assert report["status"] == "failed"
    assert any(
        issue["check"] == "operator_console_previews"
        and issue["message"]
        == (
            "molmospaces/procthor-10k-val/11 preview assets are incomplete or missing: "
            "['fpv', 'chase', 'topdown']"
        )
        for issue in report["issues"]
    )
