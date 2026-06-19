from __future__ import annotations

import copy
import json
from pathlib import Path

from PIL import Image

from scripts.isaac_lab_cleanup.check_b1_map12_asset_visual_comparison import (
    ASSET_VISUAL_COMPARISON_SCHEMA,
    build_asset_visual_comparison,
)
from tests.contract.maps.test_b1_map12_digital_twin_readiness import (
    _write_reviewable_image,
    navigation_payload,
)


def test_asset_visual_comparison_accepts_custom_scene_same_pose_evidence(
    tmp_path: Path,
) -> None:
    baseline_path = _write_custom_scene_navigation(
        tmp_path / "v1",
        scene_usd="output/assets/v1/default.usda",
    )
    candidate_path = _write_custom_scene_navigation(
        tmp_path / "v2",
        scene_usd="output/assets/v2/default.usda",
    )
    contact_sheet = tmp_path / "contact_sheet.png"
    _write_reviewable_image(contact_sheet, offset=80)

    artifact = build_asset_visual_comparison(
        baseline_name="v1",
        baseline_navigation_path=baseline_path,
        candidate_name="v2",
        candidate_navigation_path=candidate_path,
        contact_sheet=contact_sheet,
    )

    assert artifact["schema"] == ASSET_VISUAL_COMPARISON_SCHEMA
    assert artifact["status"] == "passed"
    assert artifact["comparison_ready"] is True
    assert artifact["navigation_smoke_pass_required"] is False
    assert artifact["default_visual_route_required"] is False
    assert artifact["baseline"]["navigation_status"] == "blocked"
    assert artifact["candidate"]["navigation_status"] == "blocked"
    assert artifact["waypoint_count"] == 2
    assert artifact["validation"]["errors"] == []


def test_asset_visual_comparison_rejects_pose_mismatch(tmp_path: Path) -> None:
    baseline_path = _write_custom_scene_navigation(
        tmp_path / "v1",
        scene_usd="output/assets/v1/default.usda",
    )
    candidate = _custom_scene_navigation_payload(
        tmp_path / "v2",
        scene_usd="output/assets/v2/default.usda",
    )
    candidate["waypoint_evidence"][0]["robot_pose"]["x"] += 0.25
    candidate_path = tmp_path / "v2" / "navigation_smoke.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    artifact = build_asset_visual_comparison(
        baseline_name="v1",
        baseline_navigation_path=baseline_path,
        candidate_name="v2",
        candidate_navigation_path=candidate_path,
    )

    assert artifact["status"] == "failed"
    assert any("wp_1 pose mismatch for x" in error for error in artifact["validation"]["errors"])


def test_asset_visual_comparison_can_keep_low_detail_as_warning(tmp_path: Path) -> None:
    baseline_path = _write_custom_scene_navigation(
        tmp_path / "v1",
        scene_usd="output/assets/v1/default.usda",
    )
    candidate_path = _write_custom_scene_navigation(
        tmp_path / "v2",
        scene_usd="output/assets/v2/default.usda",
    )
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    _write_low_detail_nonblank_image(Path(candidate["waypoint_evidence"][0]["views"]["fpv"]))

    artifact = build_asset_visual_comparison(
        baseline_name="v1",
        baseline_navigation_path=baseline_path,
        candidate_name="v2",
        candidate_navigation_path=candidate_path,
        allow_low_detail=True,
    )

    assert artifact["status"] == "passed"
    assert artifact["validation"]["errors"] == []
    assert any("image has too little visual detail" in warning for warning in artifact["warnings"])


def _write_custom_scene_navigation(run_dir: Path, *, scene_usd: str) -> Path:
    payload = _custom_scene_navigation_payload(run_dir, scene_usd=scene_usd)
    path = run_dir / "navigation_smoke.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _custom_scene_navigation_payload(run_dir: Path, *, scene_usd: str) -> dict[str, object]:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = copy.deepcopy(navigation_payload(run_dir))
    payload["status"] = "blocked"
    payload["robot_navigation_supported"] = False
    payload["b1_scene_usd"] = scene_usd
    payload["visual_route"] = {
        "scene_id": Path(scene_usd).stem,
        "scene_usd": scene_usd,
        "selected": False,
        "status": "custom_render_scene_verified",
    }
    payload["child_failures"] = []
    payload["validation"] = {
        "status": "failed",
        "errors": ["navigation artifact must render the verified B1_floor2_slow visual route"],
    }
    for index, row in enumerate(payload["waypoint_evidence"], start=1):
        view_dir = run_dir / f"waypoint_{index:02d}_views"
        view_dir.mkdir(parents=True, exist_ok=True)
        chase = view_dir / f"{row['waypoint_id']}.chase.png"
        _write_reviewable_image(chase, offset=60 + index)
        row["scene_usd"] = scene_usd
        row["views"]["chase"] = str(chase)
    return payload


def _write_low_detail_nonblank_image(path: Path) -> None:
    image = Image.new("RGB", (32, 24))
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            value = 73 + ((x + y) % 2)
            pixels[x, y] = (value, value, value)
    image.save(path)
