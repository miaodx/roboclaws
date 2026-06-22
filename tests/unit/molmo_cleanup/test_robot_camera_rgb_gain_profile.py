from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
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


def test_rgb_gain_profile_can_write_view_specific_gains(tmp_path: Path) -> None:
    profile = _load_module(SCRIPT_PATH, "make_robot_camera_rgb_gain_profile_view")
    fpv_left = tmp_path / "fpv_left.png"
    fpv_right = tmp_path / "fpv_right.png"
    chase_left = tmp_path / "chase_left.png"
    chase_right = tmp_path / "chase_right.png"
    Image.new("RGB", (1, 1), color=(10, 20, 30)).save(fpv_left)
    Image.new("RGB", (1, 1), color=(20, 10, 15)).save(fpv_right)
    Image.new("RGB", (1, 1), color=(30, 40, 50)).save(chase_left)
    Image.new("RGB", (1, 1), color=(15, 20, 25)).save(chase_right)
    manifest = tmp_path / "comparison_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "locations": [
                    {
                        "status": "success",
                        "target": {"target_id": "bed_1"},
                        "image_diffs": {
                            "fpv": {"left": str(fpv_left), "right": str(fpv_right)},
                            "chase": {
                                "left": str(chase_left),
                                "right": str(chase_right),
                            },
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
        view="fpv",
        view_gain_specs=[f"fpv={manifest}", f"chase={manifest}"],
    )

    written = json.loads(output.read_text(encoding="utf-8"))
    assert summary["status"] == "ready"
    assert written["backend_rgb_gain"]["isaaclab_subprocess"] == [0.5, 2.0, 2.0]
    assert written["backend_view_rgb_gain"]["isaaclab_subprocess"]["fpv"] == [
        0.5,
        2.0,
        2.0,
    ]
    assert written["backend_view_rgb_gain"]["isaaclab_subprocess"]["chase"] == [
        2.0,
        2.0,
        2.0,
    ]
    assert summary["view_fits"][0]["view"] == "fpv"
    assert summary["view_fits"][1]["view"] == "chase"
    assert json.loads(summary_output.read_text(encoding="utf-8"))["backend_view_rgb_gain"][
        "isaaclab_subprocess"
    ]["chase"] == [2.0, 2.0, 2.0]


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


def test_rgb_gain_profile_rejects_missing_manifest_source(tmp_path: Path) -> None:
    profile = _load_module(SCRIPT_PATH, "make_robot_camera_rgb_gain_profile_missing")

    with pytest.raises(
        FileNotFoundError,
        match=(
            r"robot-camera RGB gain comparison manifest source is missing: "
            r".*comparison_manifest\.json"
        ),
    ):
        profile.make_rgb_gain_profile(
            manifest_path=tmp_path / "comparison_manifest.json",
            output_profile_path=tmp_path / "profile.json",
        )


def test_rgb_gain_profile_rejects_malformed_manifest_source(tmp_path: Path) -> None:
    profile = _load_module(SCRIPT_PATH, "make_robot_camera_rgb_gain_profile_malformed")
    manifest = tmp_path / "comparison_manifest.json"
    manifest.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            r"robot-camera RGB gain comparison manifest source must contain valid JSON object: "
            r".*comparison_manifest\.json"
        ),
    ):
        profile.make_rgb_gain_profile(
            manifest_path=manifest,
            output_profile_path=tmp_path / "profile.json",
        )


def test_rgb_gain_profile_rejects_non_object_manifest_source(tmp_path: Path) -> None:
    profile = _load_module(SCRIPT_PATH, "make_robot_camera_rgb_gain_profile_non_object")
    manifest = tmp_path / "comparison_manifest.json"
    manifest.write_text("[]\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            r"robot-camera RGB gain comparison manifest source must contain a JSON object: "
            r".*comparison_manifest\.json"
        ),
    ):
        profile.make_rgb_gain_profile(
            manifest_path=manifest,
            output_profile_path=tmp_path / "profile.json",
        )
