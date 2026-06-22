from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_raw_fpv_perception_probe.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_raw_fpv_perception_probe", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _raw_run_dir(base: Path) -> Path:
    run_dir = base / "household-cleanup" / "codex-camera-raw" / "0606_1537" / "seed-7"
    robot_views = run_dir / "robot_views"
    robot_views.mkdir(parents=True)
    Image.new("RGB", (120, 90), color=(30, 20, 80)).save(robot_views / "0001_raw_fpv_001.fpv.png")
    (run_dir / "agent_view.json").write_text(
        json.dumps(
            {
                "raw_fpv_observations": [
                    {
                        "observation_id": "raw_fpv_001",
                        "waypoint_id": "generated_exploration_001",
                        "room_id": "generated_area",
                        "perception_mode": "raw_fpv_only",
                        "structured_detections_available": False,
                        "image_artifacts": {"fpv": "robot_views/0001_raw_fpv_001.fpv.png"},
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return run_dir


@pytest.mark.parametrize("arg_style", ["split", "equals"])
def test_raw_fpv_probe_rejects_explicit_missing_runtime_map_prior(
    tmp_path: Path,
    arg_style: str,
) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    missing_prior = tmp_path / "missing_runtime_metric_map.json"
    prior_args = (
        ["--runtime-map-prior", str(missing_prior)]
        if arg_style == "split"
        else [f"--runtime-map-prior={missing_prior}"]
    )

    try:
        probe.run_probe(
            probe.parse_args(
                [
                    "--raw-run-dir",
                    str(run_dir),
                    "--contrast-run-dir",
                    str(tmp_path / "missing-contrast"),
                    *prior_args,
                    "--output-dir",
                    str(tmp_path / "out"),
                    "--run-id",
                    "missing-runtime-prior",
                    "--prompt-variant",
                    "baseline_json",
                ]
            )
        )
    except FileNotFoundError as exc:
        assert "RAW-FPV runtime map prior does not exist" in str(exc)
        assert "missing_runtime_metric_map.json" in str(exc)
    else:  # pragma: no cover - explicit missing prior should fail aloud
        raise AssertionError("expected explicit missing runtime map prior to fail aloud")


def test_raw_fpv_probe_allows_missing_default_runtime_map_prior(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    args = probe.parse_args(
        [
            "--raw-run-dir",
            str(run_dir),
            "--contrast-run-dir",
            str(tmp_path / "missing-contrast"),
            "--output-dir",
            str(tmp_path / "out"),
            "--run-id",
            "missing-default-runtime-prior",
            "--prompt-variant",
            "baseline_json",
        ]
    )
    args.runtime_map_prior = tmp_path / "missing_default_runtime_metric_map.json"

    report = probe.run_probe(args)

    assert report["runtime_map_context"]["provided"] is False
