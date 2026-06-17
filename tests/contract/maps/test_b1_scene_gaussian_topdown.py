from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

from scripts.maps.render_b1_scene_gaussian_topdown import (
    TOPDOWN_RENDER_SCHEMA,
    build_topdown_camera_request,
    prepare_nurec_crop_max_z_scene_usd,
    topdown_render_packet,
    validate_topdown_render_packet,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "maps" / "render_b1_scene_gaussian_topdown.py"
SCENE_BOUNDS = (-2.0, -1.0, 4.0, 5.0)


def test_topdown_request_records_explicit_height_and_ray_plane_mapping() -> None:
    request = build_topdown_camera_request(
        scene_bounds=SCENE_BOUNDS,
        width=960,
        height=640,
        camera_height_m=28.0,
        camera_y_offset_m=0.05,
        target_z_m=0.6,
        fov_deg=65.0,
        camera_mode="near-vertical-topdown",
    )

    view = request["views"][0]
    assert view["view_id"] == "top2down"
    assert view["camera_mode"] == "near_vertical_topdown_perspective"
    assert view["eye"] == [1.0, 1.95, 28.0]
    assert view["target"] == [1.0, 2.0, 0.6]
    assert view["up"] == [0.0, 0.0, 1.0]
    assert view["topdown_camera_policy"]["camera_y_offset_m"] == 0.05
    assert request["topdown_pixel_to_scene_xyz"]["status"] == "perspective_ray_plane_z0"
    assert request["topdown_pixel_to_scene_xyz"]["formula"].startswith("ray =")


def test_topdown_packet_requires_captured_gaussian_image(tmp_path: Path) -> None:
    request = build_topdown_camera_request(
        scene_bounds=SCENE_BOUNDS,
        width=2,
        height=2,
        camera_height_m=28.0,
        camera_y_offset_m=0.05,
        target_z_m=0.6,
        fov_deg=65.0,
        camera_mode="near-vertical-topdown",
    )
    image_path = tmp_path / "views" / "top2down.png"
    image_path.parent.mkdir()
    Image.new("RGB", (2, 2), color=(40, 80, 120)).save(image_path)

    packet = topdown_render_packet(
        scene_usd=tmp_path / "scene_gs.usda",
        prepared_scene_usd=tmp_path / "scene_gs.unpacked_nurec.usda",
        scene_bounds=SCENE_BOUNDS,
        request=request,
        request_path=tmp_path / "camera_request.json",
        output_dir=tmp_path,
        nurec_crop={"status": "applied", "source": "explicit_nurec_crop_max_z"},
        capture_result={
            "ok": True,
            "result_path": str(tmp_path / "capture_result.json"),
            "capture": {"images": {"top2down": str(image_path)}},
        },
    )

    assert packet["schema"] == TOPDOWN_RENDER_SCHEMA
    assert packet["geometry_status"] == "rendered_gaussian_scene_topdown"
    assert packet["scene_visibility_policy"]["status"] == "applied"
    assert packet["topdown_image"] == str(image_path)
    assert (
        packet["pixel_to_scene_xyz"]["source"] == "rendered_gaussian_scene_topdown_ray_plane_pick"
    )
    assert validate_topdown_render_packet(packet) == []


def test_topdown_packet_without_capture_is_not_valid_for_review(tmp_path: Path) -> None:
    request = build_topdown_camera_request(
        scene_bounds=SCENE_BOUNDS,
        width=2,
        height=2,
        camera_height_m=28.0,
        camera_y_offset_m=0.05,
        target_z_m=0.6,
        fov_deg=65.0,
        camera_mode="near-vertical-topdown",
    )

    packet = topdown_render_packet(
        scene_usd=tmp_path / "scene_gs.usda",
        prepared_scene_usd=tmp_path / "scene_gs.unpacked_nurec.usda",
        scene_bounds=SCENE_BOUNDS,
        request=request,
        request_path=tmp_path / "camera_request.json",
        output_dir=tmp_path,
        nurec_crop=None,
        capture_result=None,
    )

    assert packet["geometry_status"] == "render_required"
    assert packet["scene_visibility_policy"]["status"] == "not_requested"
    assert "topdown render must be captured before review" in validate_topdown_render_packet(packet)


def test_explicit_nurec_crop_writes_reproducible_review_usd(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    nurec_path = source_dir / "xm_large_scene.nurec"
    nurec_path.write_bytes(b"nurec")
    (source_dir / "default.usda").write_text(
        "#usda 1.0\n\n"
        'def Xform "World"\n'
        "{\n"
        '    over "gauss" (prepend references = @gauss.usda@) {}\n'
        "}\n",
        encoding="utf-8",
    )
    (source_dir / "gauss.usda").write_text(
        "#usda 1.0\n\n"
        'def Volume "gauss"\n'
        "{\n"
        "    custom float3 omni:nurec:crop:maxBounds = (9.281567, 7.441333, 4.3845134)\n"
        "    custom float3 omni:nurec:crop:minBounds = (-37.12612, -20.122812, -0.71673876)\n"
        "    custom asset filePath = @./xm_large_scene.nurec@\n"
        "}\n",
        encoding="utf-8",
    )
    scene = source_dir / "scene_gs.unpacked_nurec.usda"
    scene.write_text(
        "#usda 1.0\n\n"
        'def Xform "combined"\n'
        "{\n"
        '    def Xform "gs" (prepend references = @'
        f"{(source_dir / 'default.usda').as_posix()}"
        "@) {}\n"
        "}\n",
        encoding="utf-8",
    )

    cropped_scene, policy = prepare_nurec_crop_max_z_scene_usd(
        scene,
        crop_max_z=1.8,
        output_dir=tmp_path / "out",
    )

    assert cropped_scene.is_file()
    assert policy["status"] == "applied"
    assert policy["crop_max_z"] == 1.8
    cropped_gauss = Path(policy["cropped_gauss_usd"])
    text = cropped_gauss.read_text(encoding="utf-8")
    assert "custom float3 omni:nurec:crop:maxBounds = (9.281567, 7.441333, 1.8)" in text
    assert f"@{nurec_path.resolve().as_posix()}@" in text


def test_topdown_cli_requires_explicit_scene_bounds(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--scene-xy-bounds is required" in completed.stderr


def test_topdown_cli_can_write_request_without_capture(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            f"--scene-xy-bounds={','.join(str(value) for value in SCENE_BOUNDS)}",
            "--scene-usd",
            str(tmp_path / "scene_gs.usda"),
            "--output-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert completed.returncode == 2
    assert summary["schema"] == TOPDOWN_RENDER_SCHEMA
    assert summary["geometry_status"] == "render_required"
    assert (tmp_path / "camera_request.json").is_file()
    assert (tmp_path / "scene_gaussian_topdown.json").is_file()
