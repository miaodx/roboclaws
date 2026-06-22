from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from scripts.molmo_cleanup import robot_camera_apple2apple_materials as material_checks

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_CAMERA_COMPARISON_PATH = (
    REPO_ROOT / "scripts" / "molmo_cleanup" / "run_robot_camera_apple2apple_comparison.py"
)


def _load_run_camera_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_robot_camera_apple2apple_comparison_prior_probe_sources",
        RUN_CAMERA_COMPARISON_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_robot_camera_light_shadow_probe_manifest_source_errors(tmp_path: Path) -> None:
    run_camera = _load_run_camera_module()

    missing = run_camera._load_light_shadow_probe_manifest(
        tmp_path / "missing.json",
        output_dir=tmp_path,
    )
    assert missing == {"status": "missing_manifest", "path": "missing.json"}

    for name, contents, expected in (
        (
            "malformed_probe",
            "{not-json}\n",
            "robot camera prior probe manifest source must contain valid JSON object",
        ),
        (
            "non_object_probe",
            "[]\n",
            "robot camera prior probe manifest source must contain a JSON object",
        ),
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(contents, encoding="utf-8")

        result = run_camera._load_light_shadow_probe_manifest(path, output_dir=tmp_path)

        assert result["status"] == "read_failed"
        assert result["path"] == path.name
        assert expected in result["error"]


def test_robot_camera_material_probe_manifest_source_errors(tmp_path: Path) -> None:
    assert material_checks._load_probe_manifest(
        tmp_path / "missing.json",
        output_dir=tmp_path,
    ) == {"status": "missing_manifest", "path": "missing.json"}

    for name, contents, expected in (
        (
            "malformed_probe",
            "{not-json}\n",
            "robot camera prior probe manifest source must contain valid JSON object",
        ),
        (
            "non_object_probe",
            "[]\n",
            "robot camera prior probe manifest source must contain a JSON object",
        ),
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(contents, encoding="utf-8")

        result = material_checks._load_probe_manifest(path, output_dir=tmp_path)

        assert result["status"] == "read_failed"
        assert result["path"] == path.name
        assert expected in result["error"]


def test_robot_camera_prior_probe_manifest_source_valid_object(tmp_path: Path) -> None:
    path = tmp_path / "probe.json"
    path.write_text(
        json.dumps(
            {
                "scene": {"scene_source": "procthor-10k-val", "seed": 7},
                "summary": {"location_count": 1, "fpv_mean_abs_rgb_avg": 12.5},
            }
        ),
        encoding="utf-8",
    )

    result = material_checks._load_probe_manifest(path, output_dir=tmp_path)

    assert result["status"] == "loaded"
    assert result["path"] == "probe.json"
    assert result["scene"]["scene_source"] == "procthor-10k-val"
    assert result["fpv_mean_abs_rgb_avg"] == 12.5
