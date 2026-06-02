from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "make_robot_camera_rgb_gain_profile.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rgb_gain_profile_fits_global_fpv_gain(tmp_path: Path) -> None:
    profile = _load_module(SCRIPT_PATH, "make_robot_camera_rgb_gain_profile")
    left = tmp_path / "left.png"
    right = tmp_path / "right.png"
    Image.new("RGB", (2, 1), color=(10, 20, 30)).save(left)
    Image.new("RGB", (2, 1), color=(20, 10, 15)).save(right)
    manifest = tmp_path / "comparison_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "locations": [
                    {
                        "status": "success",
                        "target": {"target_id": "bed_1"},
                        "image_diffs": {
                            "fpv": {
                                "left": str(left),
                                "right": str(right),
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "profile.json"
    summary_output = tmp_path / "summary.json"

    summary = profile.make_rgb_gain_profile(
        manifest_path=manifest,
        output_profile_path=output,
        summary_output=summary_output,
    )

    written = json.loads(output.read_text(encoding="utf-8"))
    assert summary["schema"] == "roboclaws_robot_camera_rgb_gain_profile_v1"
    assert summary["status"] == "ready"
    assert summary["comparison_only"] is True
    assert summary["used_pair_count"] == 1
    assert written["backend_rgb_gain"]["isaaclab_subprocess"] == [0.5, 2.0, 2.0]
    assert json.loads(summary_output.read_text(encoding="utf-8"))["status"] == "ready"


def test_rgb_gain_profile_filters_targets(tmp_path: Path) -> None:
    profile = _load_module(SCRIPT_PATH, "make_robot_camera_rgb_gain_profile_filter")
    left_a = tmp_path / "left_a.png"
    right_a = tmp_path / "right_a.png"
    left_b = tmp_path / "left_b.png"
    right_b = tmp_path / "right_b.png"
    Image.new("RGB", (1, 1), color=(10, 20, 30)).save(left_a)
    Image.new("RGB", (1, 1), color=(20, 10, 15)).save(right_a)
    Image.new("RGB", (1, 1), color=(90, 80, 70)).save(left_b)
    Image.new("RGB", (1, 1), color=(10, 20, 70)).save(right_b)
    manifest = tmp_path / "comparison_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "locations": [
                    {
                        "status": "success",
                        "target": {"target_id": "bed_1"},
                        "image_diffs": {"fpv": {"left": str(left_a), "right": str(right_a)}},
                    },
                    {
                        "status": "success",
                        "target": {"target_id": "bowl_1"},
                        "image_diffs": {"fpv": {"left": str(left_b), "right": str(right_b)}},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "profile.json"

    summary = profile.make_rgb_gain_profile(
        manifest_path=manifest,
        output_profile_path=output,
        target_ids=["bed_1"],
    )

    assert summary["used_pair_count"] == 1
    assert summary["target_ids"] == ["bed_1"]
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["backend_rgb_gain"]["isaaclab_subprocess"] == [0.5, 2.0, 2.0]


def test_rgb_gain_profile_no_pairs_does_not_write_profile(tmp_path: Path) -> None:
    profile = _load_module(SCRIPT_PATH, "make_robot_camera_rgb_gain_profile_no_pairs")
    manifest = tmp_path / "comparison_manifest.json"
    manifest.write_text(json.dumps({"locations": []}), encoding="utf-8")
    output = tmp_path / "profile.json"

    summary = profile.make_rgb_gain_profile(
        manifest_path=manifest,
        output_profile_path=output,
    )

    assert summary["status"] == "no_pairs"
    assert summary["used_pair_count"] == 0
    assert not output.exists()
