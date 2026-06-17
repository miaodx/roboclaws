from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from roboclaws.launch.scene_sampler import MolmoSpacesSceneRef
from scripts.operator_console.render_scene_previews import (
    B1_MAP12_WORLD_ID,
    PREVIEW_METADATA_SCHEMA,
    _first_public_waypoint,
    _molmospaces_scene_ref,
    _preview_metadata,
    _promote_b1_camera_previews,
    _scene_alignment,
    _scene_center_and_span,
    _topdown_camera_request,
    render_b1_map12_preview,
)


def test_topdown_preview_request_uses_scene_camera_not_semantic_map() -> None:
    state = {
        "room_outlines": [
            {"center": [1.0, 2.0, 0.0], "half_extents": [2.0, 3.0]},
            {"center": [5.0, 4.0, 0.0], "half_extents": [1.0, 1.5]},
        ],
        "objects": {"mug_01": {"position": [6.0, 5.0, 0.8]}},
        "receptacles": {"sink_01": {"position": [-1.0, -1.0, 0.9]}},
    }

    request = _topdown_camera_request(state, width=900, height=560)

    view = request["views"][0]
    assert request["camera_model"] == "canonical_eye_target_camera_v1"
    assert request["render_resolution"] == {"width": 900, "height": 560}
    assert view["view_id"] == "topdown_scene"
    assert view["camera_basis"] == "whole_scene_true_topdown_aligned_to_scene_bounds"
    assert view["eye"][2] > view["target"][2]
    assert view["eye"][:2] == pytest.approx(view["target"][:2])
    assert view["azimuth"] == pytest.approx(90.0)
    assert view["scene_alignment"]["schema"] == "operator_console_scene_alignment_v1"


def test_preview_metadata_marks_topdown_as_rendered_scene_not_map_fallback(
    tmp_path: Path,
) -> None:
    fpv_path = tmp_path / "molmospaces-val_9-fpv.png"
    map_path = tmp_path / "molmospaces-val_9-map.png"
    chase_path = tmp_path / "molmospaces-val_9-chase.png"
    topdown_path = tmp_path / "molmospaces-val_9-topdown.png"
    Image.new("RGB", (8, 8), (20, 30, 40)).save(fpv_path)
    Image.new("RGB", (8, 8), (30, 40, 50)).save(map_path)
    Image.new("RGB", (8, 8), (100, 120, 140)).save(chase_path)
    Image.new("RGB", (8, 8), (60, 90, 120)).save(topdown_path)
    scene_alignment = {
        "schema": "operator_console_scene_alignment_v1",
        "bounds": {"min_x": 0.0, "max_x": 4.0, "min_y": 0.0, "max_y": 3.0},
        "center": [2.0, 1.5, 0.4],
        "span_x_m": 4.0,
        "span_y_m": 3.0,
        "camera_span_m": 4.0,
        "screen_coordinate_convention": "screen_x_world_positive_x_screen_y_world_negative_y",
        "topdown_azimuth_deg": 90.0,
    }

    metadata = _preview_metadata(
        world_id="molmospaces/val_9",
        scene_source="procthor-10k-val",
        scene_index=9,
        seed=7,
        width=900,
        height=560,
        waypoint={"waypoint_id": "generated_exploration_001"},
        navigation={"status": "ok"},
        robot_views={
            "camera_diagnostics": {
                "views": {
                    "fpv": {"status": "ready", "camera_name": "robot_0/head_camera"},
                    "chase": {
                        "status": "ready",
                        "camera_name": "robot_0/camera_follower",
                    },
                }
            }
        },
        topdown_result={
            "views": [
                {
                    "view_id": "topdown_scene",
                    "eye": [1.0, 2.0, 10.0],
                    "target": [1.0, 2.0, 0.4],
                    "azimuth": 90.0,
                    "elevation": -90.0,
                    "distance": 9.6,
                }
            ]
        },
        topdown_request={"camera_model": "canonical_eye_target_camera_v1"},
        fpv_path=fpv_path,
        map_path=map_path,
        chase_path=chase_path,
        chase_waypoint={"waypoint_id": "generated_exploration_004"},
        chase_navigation={"status": "ok"},
        chase_robot_views={
            "camera_diagnostics": {
                "views": {
                    "chase": {
                        "status": "ready",
                        "camera_name": "robot_0/camera_follower",
                    }
                }
            }
        },
        chase_selection={
            "status": "alternate_waypoint_reviewable",
            "candidate_count_evaluated": 4,
        },
        topdown_path=topdown_path,
        scene_alignment=scene_alignment,
    )

    assert metadata["schema"] == PREVIEW_METADATA_SCHEMA
    assert metadata["scene_source"] == "procthor-10k-val"
    assert metadata["views"]["fpv"]["view"] == "raw_fpv"
    assert metadata["views"]["fpv"]["provenance"] == (
        "mujoco_robot_head_camera_first_public_waypoint"
    )
    assert metadata["views"]["chase"]["view"] == "chase_camera"
    assert metadata["views"]["chase"]["provenance"] == (
        "mujoco_robot_camera_follower_public_waypoint"
    )
    assert metadata["views"]["chase"]["waypoint_id"] == "generated_exploration_004"
    assert metadata["views"]["chase"]["selection_status"] == "alternate_waypoint_reviewable"
    assert metadata["views"]["chase"]["candidate_count_evaluated"] == 4
    assert metadata["views"]["chase"]["path"].endswith("-chase.png")
    assert metadata["views"]["chase"]["camera_diagnostics"]["camera_name"] == (
        "robot_0/camera_follower"
    )
    assert metadata["views"]["map"]["view"] == "base_navigation_map_preview"
    assert metadata["views"]["map"]["provenance"] == "map_bundle_preview_png"
    assert "scene_alignment" not in metadata["views"]["map"]
    assert "semantic_projection" not in metadata["views"]["map"]
    assert metadata["views"]["topdown"]["view"] == "topdown_scene_render"
    assert metadata["views"]["topdown"]["camera_pose"]["azimuth"] == pytest.approx(90.0)
    assert metadata["views"]["topdown"]["scene_alignment"] == scene_alignment
    assert metadata["views"]["topdown"]["semantic_map_fallback"] is False
    assert metadata["views"]["topdown"]["path"].endswith("-topdown.png")
    assert metadata["views"]["topdown"]["image_diagnostics"]["visual_status"] == "low_detail"


def test_molmospaces_preview_scene_ref_preserves_legacy_alias_source() -> None:
    assert _molmospaces_scene_ref("molmospaces/val_9") == MolmoSpacesSceneRef(
        scene_source="procthor-10k-val",
        scene_index=9,
    )


def test_molmospaces_preview_scene_ref_accepts_source_aware_world_id() -> None:
    assert _molmospaces_scene_ref("molmospaces/ithor/3") == MolmoSpacesSceneRef(
        scene_source="ithor",
        scene_index=3,
    )
    assert _molmospaces_scene_ref("molmospaces/procthor-objaverse-val/12") == (
        MolmoSpacesSceneRef(scene_source="procthor-objaverse-val", scene_index=12)
    )


def test_molmospaces_preview_scene_ref_rejects_unknown_source_or_index() -> None:
    with pytest.raises(ValueError, match="unsupported MolmoSpaces scene_source"):
        _molmospaces_scene_ref("molmospaces/unknown-source/1")
    with pytest.raises(ValueError, match="unsupported MolmoSpaces scene index"):
        _molmospaces_scene_ref("molmospaces/ithor/not-an-index")
    with pytest.raises(ValueError, match="negative MolmoSpaces scene index"):
        _molmospaces_scene_ref("molmospaces/ithor/-1")


def test_b1_map12_preview_uses_static_map_bundle_assets(tmp_path: Path, monkeypatch) -> None:
    import scripts.operator_console.render_scene_previews as render_scene_previews

    bundle, review = _write_b1_preview_inputs(tmp_path)
    _patch_b1_preview_inputs(render_scene_previews, monkeypatch, tmp_path, bundle, review)

    result = render_b1_map12_preview(output_dir=tmp_path, width=320, height=200)

    assert result["world_id"] == B1_MAP12_WORLD_ID
    assert result["status"] == "rendered"
    for view_name in ("map", "topdown"):
        path = tmp_path / f"b1-map12-{view_name}.png"
        assert path.is_file()
        assert Image.open(path).size == (320, 200)
    assert not (tmp_path / "b1-map12-fpv.png").exists()
    assert not (tmp_path / "b1-map12-chase.png").exists()
    metadata = json.loads((tmp_path / "b1-map12-preview.json").read_text(encoding="utf-8"))
    assert metadata["schema"] == PREVIEW_METADATA_SCHEMA
    assert metadata["backend"] == "isaaclab"
    assert metadata["renderer"] == "static_b1_map12_digital_twin_overview"
    assert "fpv" not in metadata["views"]
    assert "chase" not in metadata["views"]
    assert metadata["review_manifest"] == str(review)
    assert metadata["runtime_map_bundle"] == str(tmp_path / "runtime-map-bundle")
    assert metadata["views"]["topdown"]["review_label_count"] == 1
    assert metadata["views"]["topdown"]["inspection_waypoint_count"] == 2


def test_b1_map12_preview_promotes_real_isaac_camera_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import scripts.operator_console.render_scene_previews as render_scene_previews

    bundle, review = _write_b1_preview_inputs(tmp_path)
    _patch_b1_preview_inputs(render_scene_previews, monkeypatch, tmp_path, bundle, review)
    run_dir = tmp_path / "run"
    views_dir = run_dir / "robot_views"
    views_dir.mkdir(parents=True)
    _write_pattern_image(views_dir / "0001_observe.fpv.png", accent=(220, 220, 220))
    _write_pattern_image(views_dir / "0001_observe.chase.png", accent=(120, 90, 60))
    artifact = run_dir / "run_result.json"
    artifact.write_text(
        json.dumps(
            {
                "contract": "realworld_cleanup_v1",
                "robot_view_steps": [
                    {
                        "action": "observe",
                        "label": "0001_observe",
                        "waypoint_id": "generated_exploration_002",
                        "camera_control_contract": {
                            "agent_facing_fpv": {
                                "camera_prim_path": "/World/robot_0/head_camera",
                                "robot_mounted": True,
                                "source": "isaac_lab_camera_rgb_robot_mounted_head_camera:fpv",
                            },
                            "report_chase_view": {
                                "source": "isaac_lab_camera_rgb_scene_camera:chase",
                            },
                        },
                        "views": {
                            "fpv": "robot_views/0001_observe.fpv.png",
                            "chase": "robot_views/0001_observe.chase.png",
                        },
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = render_b1_map12_preview(
        output_dir=tmp_path,
        width=320,
        height=200,
        camera_artifact=artifact,
    )

    assert result["status"] == "rendered"
    for view_name in ("fpv", "chase", "map", "topdown"):
        assert (tmp_path / f"b1-map12-{view_name}.png").is_file()
    metadata = json.loads((tmp_path / "b1-map12-preview.json").read_text(encoding="utf-8"))
    assert metadata["renderer"] == "static_b1_map12_with_isaac_runtime_camera_previews"
    assert metadata["camera_preview_artifact"]["path"] == str(artifact)
    assert metadata["views"]["fpv"]["provenance"] == ("isaac_runtime_robot_mounted_head_camera_fpv")
    assert metadata["views"]["fpv"]["camera"] == "/World/robot_0/head_camera"
    assert metadata["views"]["fpv"]["waypoint_id"] == "generated_exploration_002"
    assert metadata["views"]["chase"]["provenance"] == "isaac_runtime_report_chase_camera"
    assert metadata["views"]["chase"]["source"] == "isaac_lab_camera_rgb_scene_camera:chase"


def test_b1_camera_promotion_rejects_low_detail_pairs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    views_dir = run_dir / "robot_views"
    views_dir.mkdir(parents=True)
    Image.new("RGB", (64, 48), (120, 120, 120)).save(views_dir / "flat.fpv.png")
    _write_pattern_image(views_dir / "flat.chase.png", accent=(120, 90, 60))
    artifact = run_dir / "run_result.json"
    artifact.write_text(
        json.dumps(
            {
                "robot_view_steps": [
                    {
                        "label": "flat",
                        "views": {
                            "fpv": "robot_views/flat.fpv.png",
                            "chase": "robot_views/flat.chase.png",
                        },
                    }
                ]
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = _promote_b1_camera_previews(
        camera_artifact=artifact,
        fpv_path=tmp_path / "b1-map12-fpv.png",
        chase_path=tmp_path / "b1-map12-chase.png",
        width=320,
        height=200,
    )

    assert result["status"] == "no_usable_camera_pair"
    assert result["evaluated_candidates"][0]["status"] == "quality_rejected"
    assert any(
        error.startswith("fpv:") for error in result["evaluated_candidates"][0]["quality_errors"]
    )


def test_b1_map12_skip_existing_rewrites_stale_camera_preview_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import scripts.operator_console.render_scene_previews as render_scene_previews

    bundle, review = _write_b1_preview_inputs(tmp_path)
    _patch_b1_preview_inputs(render_scene_previews, monkeypatch, tmp_path, bundle, review)
    Image.new("RGB", (16, 16), (1, 2, 3)).save(tmp_path / "b1-map12-fpv.png")
    Image.new("RGB", (16, 16), (4, 5, 6)).save(tmp_path / "b1-map12-chase.png")
    metadata_path = tmp_path / "b1-map12-preview.json"
    metadata_path.write_text(
        json.dumps(
            {
                "schema": PREVIEW_METADATA_SCHEMA,
                "views": {
                    "fpv": {"path": "b1-map12-fpv.png"},
                    "chase": {"path": "b1-map12-chase.png"},
                    "map": {"path": "b1-map12-map.png"},
                    "topdown": {"path": "b1-map12-topdown.png"},
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = render_b1_map12_preview(
        output_dir=tmp_path,
        width=320,
        height=200,
        skip_existing=True,
    )

    assert result["status"] == "rendered"
    assert not (tmp_path / "b1-map12-fpv.png").exists()
    assert not (tmp_path / "b1-map12-chase.png").exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert "fpv" not in metadata["views"]
    assert "chase" not in metadata["views"]


def test_b1_map12_preserves_prepared_nurec_camera_preview_renderer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import scripts.operator_console.render_scene_previews as render_scene_previews

    bundle, review = _write_b1_preview_inputs(tmp_path)
    _patch_b1_preview_inputs(render_scene_previews, monkeypatch, tmp_path, bundle, review)
    Image.new("RGB", (16, 16), (80, 90, 100)).save(tmp_path / "b1-map12-fpv.png")
    Image.new("RGB", (16, 16), (100, 90, 80)).save(tmp_path / "b1-map12-chase.png")
    metadata_path = tmp_path / "b1-map12-preview.json"
    metadata_path.write_text(
        json.dumps(
            {
                "schema": PREVIEW_METADATA_SCHEMA,
                "renderer": "static_b1_map12_with_prepared_nurec_camera_previews",
                "views": {
                    "fpv": {
                        "path": "b1-map12-fpv.png",
                        "provenance": "prepared_b1_nurec_scene_camera_preview",
                    },
                    "chase": {
                        "path": "b1-map12-chase.png",
                        "provenance": "prepared_b1_nurec_scene_camera_preview",
                    },
                    "map": {"path": "b1-map12-map.png"},
                    "topdown": {"path": "b1-map12-topdown.png"},
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = render_b1_map12_preview(output_dir=tmp_path, width=320, height=200)

    assert result["status"] == "rendered"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["renderer"] == "static_b1_map12_with_prepared_nurec_camera_previews"
    assert metadata["views"]["fpv"]["provenance"] == "prepared_b1_nurec_scene_camera_preview"
    assert metadata["views"]["chase"]["provenance"] == "prepared_b1_nurec_scene_camera_preview"


def test_b1_map12_skip_existing_rewrites_missing_real_camera_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import scripts.operator_console.render_scene_previews as render_scene_previews

    bundle, review = _write_b1_preview_inputs(tmp_path)
    _patch_b1_preview_inputs(render_scene_previews, monkeypatch, tmp_path, bundle, review)
    Image.new("RGB", (16, 16), (10, 20, 30)).save(tmp_path / "b1-map12-map.png")
    Image.new("RGB", (16, 16), (30, 20, 10)).save(tmp_path / "b1-map12-topdown.png")
    metadata_path = tmp_path / "b1-map12-preview.json"
    metadata_path.write_text(
        json.dumps(
            {
                "schema": PREVIEW_METADATA_SCHEMA,
                "views": {
                    "fpv": {
                        "path": "b1-map12-fpv.png",
                        "provenance": "isaac_runtime_robot_mounted_head_camera_fpv",
                    },
                    "chase": {
                        "path": "b1-map12-chase.png",
                        "provenance": "isaac_runtime_report_chase_camera",
                    },
                    "map": {"path": "b1-map12-map.png"},
                    "topdown": {"path": "b1-map12-topdown.png"},
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = render_b1_map12_preview(
        output_dir=tmp_path,
        width=320,
        height=200,
        skip_existing=True,
    )

    assert result["status"] == "rendered"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["renderer"] == "static_b1_map12_digital_twin_overview"
    assert "fpv" not in metadata["views"]
    assert "chase" not in metadata["views"]


def _patch_b1_preview_inputs(
    render_scene_previews,
    monkeypatch,
    tmp_path: Path,
    bundle: Path,
    review: Path,
) -> None:
    monkeypatch.setattr(render_scene_previews, "B1_MAP_BUNDLE_DIR", bundle)
    monkeypatch.setattr(
        render_scene_previews,
        "B1_NAVIGATION_MEMORY",
        bundle.parent / "navigation_memory.json",
    )
    monkeypatch.setattr(render_scene_previews, "B1_SCENE_ROOT", tmp_path)
    monkeypatch.setattr(render_scene_previews, "B1_ALIGNMENT_REVIEW_MANIFEST", review)
    monkeypatch.setattr(
        render_scene_previews,
        "B1_RUNTIME_PREVIEW_BUNDLE_DIR",
        tmp_path / "runtime-map-bundle",
    )


def _write_b1_preview_inputs(tmp_path: Path) -> tuple[Path, Path]:
    bundle = _write_b1_map_bundle(tmp_path)
    review = _write_b1_review_manifest(tmp_path, bundle)
    return bundle, review


def _write_b1_map_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "robot_map_12" / "agibot"
    bundle.mkdir(parents=True)
    (bundle / "nav2.yaml").write_text(
        "\n".join(
            [
                "image: occupancy.pgm",
                "resolution: 0.050000",
                "origin: [-1.000000, -1.000000, 0.000000]",
                "negate: 0",
                "occupied_thresh: 0.650000",
                "free_thresh: 0.250000",
                "",
            ]
        ),
        encoding="utf-8",
    )
    image = Image.new("L", (120, 90), 255)
    for x in range(120):
        image.putpixel((x, 0), 0)
        image.putpixel((x, 89), 0)
    for y in range(90):
        image.putpixel((0, y), 0)
        image.putpixel((119, y), 0)
    image.save(bundle / "occupancy.pgm")
    (bundle / "source.json").write_text(
        json.dumps({"schema": "agibot.map_fetch.source.v1"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (bundle / "raw_map.json.gz").write_bytes(b"test raw map")
    (tmp_path / "robot_map_12" / "navigation_memory.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "items": [
                    {
                        "id": "table_anchor",
                        "label": "Table anchor",
                        "kind": "surface",
                        "pose": {"x": 1.0, "y": 1.0, "yaw": 0.0},
                        "nav_goal": {"x": 1.0, "y": 1.0, "yaw": 0.0},
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return bundle


def _write_b1_review_manifest(tmp_path: Path, bundle: Path) -> Path:
    review = tmp_path / "b1-map12-alignment-review.json"
    review.write_text(
        json.dumps(
            {
                "schema": "b1_map12_alignment_review_v1",
                "source_assets": {
                    "map_bundle": str(bundle),
                    "scene_root": str(tmp_path),
                    "scene_usd_path": "scene_base.usd",
                },
                "display_adjustment": {
                    "global_tilt_deg": 0.0,
                    "status": "review_display_only",
                },
                "labels": [
                    {
                        "label_id": "meeting_room_a",
                        "scene_partition_id": "meeting_room_a",
                        "room_label": "Meeting room A",
                        "category": "meeting_room",
                        "map_area_id": "meeting_room_a",
                        "review_status": "accepted",
                        "geometry": {
                            "type": "map_polygon",
                            "source": "manual_review",
                            "frame_id": "map",
                            "points": [
                                {"x": 0.0, "y": 0.0},
                                {"x": 4.0, "y": 0.0},
                                {"x": 4.0, "y": 3.0},
                                {"x": 0.0, "y": 3.0},
                            ],
                        },
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return review


def _write_pattern_image(path: Path, *, accent: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (96, 64), (48, 56, 64))
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            if (x // 6 + y // 4) % 2 == 0:
                pixels[x, y] = accent
            elif x == y or x + y == image.width - 1:
                pixels[x, y] = (20, 24, 28)
    image.save(path)


def test_preview_helpers_use_first_public_waypoint_and_scene_bounds() -> None:
    waypoint = _first_public_waypoint(
        {"inspection_waypoints": [{"waypoint_id": "first"}, {"waypoint_id": "second"}]}
    )
    center, span = _scene_center_and_span(
        {"room_outlines": [{"center": [2.0, 3.0], "half_extents": [1.0, 2.0]}]}
    )

    assert waypoint["waypoint_id"] == "first"
    assert center == pytest.approx([2.0, 3.0, 0.4])
    assert span >= 4.0


def test_scene_alignment_expands_bounds_to_preview_aspect() -> None:
    alignment = _scene_alignment(
        {"room_outlines": [{"center": [2.0, 3.0], "half_extents": [1.0, 2.0]}]},
        width=900,
        height=560,
    )

    assert alignment["schema"] == "operator_console_scene_alignment_v1"
    assert (
        alignment["screen_coordinate_convention"]
        == "screen_x_world_positive_x_screen_y_world_negative_y"
    )
    assert alignment["topdown_azimuth_deg"] == pytest.approx(90.0)
    assert alignment["span_x_m"] / alignment["span_y_m"] == pytest.approx(900 / 560)
