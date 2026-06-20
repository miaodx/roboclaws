from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "summarize_robot_camera_visual_parity.py"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("argv_flag", "filename", "source", "message"),
    (
        (
            "--baseline-manifest",
            "baseline.json",
            "{not-json\n",
            "robot camera comparison manifest must contain valid JSON object",
        ),
        (
            "--baseline-manifest",
            "baseline.json",
            "[]\n",
            "robot camera comparison manifest must contain a JSON object",
        ),
        (
            "--raw-fpv-run-result",
            "raw_fpv.json",
            "{not-json\n",
            "RAW-FPV run result must contain valid JSON object",
        ),
        (
            "--calibration-manifest",
            "calibration.json",
            "[]\n",
            "calibration manifest must contain a JSON object",
        ),
        (
            "--prepared-usd-summary",
            "prepared.json",
            "{not-json\n",
            "prepared USD summary must contain valid JSON object",
        ),
    ),
)
def test_visual_parity_summary_cli_rejects_bad_source_json(
    tmp_path: Path,
    argv_flag: str,
    filename: str,
    source: str,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary = _load_module(f"visual_parity_source_{filename.replace('.', '_')}")
    source_path = tmp_path / filename
    output_dir = tmp_path / "summary"
    source_path.write_text(source, encoding="utf-8")

    rc = summary.main(
        [
            "--output-dir",
            str(output_dir),
            argv_flag,
            str(source_path),
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert message in captured.err
    assert str(source_path) in captured.err
    assert not (output_dir / "visual_parity_summary.json").exists()
    assert not (output_dir / "report.html").exists()


def test_visual_parity_summary_rejects_bad_probe_manifest_source_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary = _load_module("visual_parity_bad_probe_source")
    probe_path = tmp_path / "probe.json"
    output_dir = tmp_path / "summary"
    probe_path.write_text("[]\n", encoding="utf-8")

    rc = summary.main(
        [
            "--output-dir",
            str(output_dir),
            "--probe-manifest",
            f"bad_probe={probe_path}",
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert "robot camera comparison manifest must contain a JSON object" in captured.err
    assert str(probe_path) in captured.err
    assert not (output_dir / "visual_parity_summary.json").exists()
    assert not (output_dir / "report.html").exists()


@pytest.mark.parametrize(
    ("argv_flag", "filename", "message"),
    (
        (
            "--calibration-manifest",
            "missing_calibration.json",
            "calibration manifest missing",
        ),
        (
            "--prepared-usd-summary",
            "missing_prepared_usd.json",
            "prepared USD summary missing",
        ),
    ),
)
def test_visual_parity_summary_cli_rejects_missing_declared_optional_sources(
    tmp_path: Path,
    argv_flag: str,
    filename: str,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary = _load_module(f"visual_parity_missing_{filename.replace('.', '_')}")
    source_path = tmp_path / filename
    output_dir = tmp_path / "summary"

    rc = summary.main(
        [
            "--output-dir",
            str(output_dir),
            argv_flag,
            str(source_path),
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert message in captured.err
    assert str(source_path) in captured.err
    assert not (output_dir / "visual_parity_summary.json").exists()
    assert not (output_dir / "report.html").exists()


def test_visual_parity_summary_rejects_bad_rgb_gain_source_manifest(
    tmp_path: Path,
) -> None:
    summary = _load_module("visual_parity_bad_rgb_gain_source")
    baseline = _write_robot_camera_manifest(tmp_path / "baseline" / "comparison_manifest.json")
    probe = _write_robot_camera_manifest(tmp_path / "probe" / "comparison_manifest.json")
    source_manifest = tmp_path / "source_manifest.json"
    source_manifest.write_text("[]\n", encoding="utf-8")
    (probe.parent / "isaac_state.json").write_text(
        json.dumps(
            {
                "robot_view_color_profile_override": {
                    "backend_rgb_gain": {"isaaclab_subprocess": [0.94, 0.84, 0.82]},
                    "backend_rgb_gain_source": (
                        f"{source_manifest} global least-squares FPV RGB gain"
                    ),
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"robot camera comparison manifest must contain a JSON object: .*source_manifest",
    ):
        summary.build_summary(
            output_dir=tmp_path / "summary",
            baseline_manifest_paths=[baseline],
            probe_specs=[f"probe={probe}"],
            raw_fpv_run_result_paths=[],
            calibration_manifest_paths=[],
            prepared_usd_summary_paths=[],
            required_scene_count=1,
            required_seed_count=1,
        )


def _write_robot_camera_manifest(path: Path) -> Path:
    path.parent.mkdir(parents=True)
    payload = {
        "schema": "roboclaws_robot_camera_apple2apple_comparison_v1",
        "status": "success",
        "scene": {
            "scene_source": "procthor-10k-val",
            "scene_index": 1,
            "seed": 7,
            "generated_mess_count": 2,
            "render_width": 540,
            "render_height": 360,
            "scene_usd_path": "scene.usda",
        },
        "summary": {
            "location_count": 1,
            "successful_location_count": 1,
            "fpv_mean_abs_rgb_avg": 38.0,
            "chase_mean_abs_rgb_avg": 64.0,
            "camera_contract_diagnostics": {
                "status": "fpv_contract_shared_with_static_head_camera_pitch_correction",
                "fpv_head_camera_contract_count": 1,
                "fpv_lens_delta_summary": {"status": "fpv_lens_aligned"},
                "fpv_world_pose_delta_summary": {"status": "fpv_world_pose_aligned"},
            },
            "render_domain_checks": {"status": "render_domain_delta_confirmed", "checks": []},
            "render_contract_diagnostics": {"status": "target_material_texture_or_binding_gap"},
            "target_selection": {
                "status": "isaac_bound_targets_selected",
                "selected_count": 1,
                "dropped_unbound_target_count": 0,
            },
        },
        "locations": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
