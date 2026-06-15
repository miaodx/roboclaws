from __future__ import annotations

import json
from pathlib import Path

from scripts.isaac_lab_cleanup.check_b1_map12_readiness import (
    READINESS_SCHEMA,
    SEMANTIC_SOURCE,
    SEMANTIC_USD_BLOCKED,
    readiness_artifact_with_navigation,
)
from scripts.isaac_lab_cleanup.render_b1_map12_navigation_report import main as render_main
from tests.contract.maps.test_b1_map12_digital_twin_readiness import (
    _write_reviewable_image,
    navigation_payload,
    static_readiness_payload,
)


def test_b1_map12_navigation_report_renders_reviewable_artifact(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    navigation = navigation_payload(run_dir)
    for index, waypoint in enumerate(navigation["waypoint_evidence"], start=1):
        views = waypoint["views"]
        view_dir = run_dir / f"waypoint_{index:02d}_views"
        view_dir.mkdir()
        for view_name in ("chase", "map", "verify"):
            path = view_dir / f"{waypoint['waypoint_id']}.{view_name}.png"
            _write_reviewable_image(path, offset=20 * index)
            views[view_name] = str(path)
    navigation["b1_scene_usd"] = (
        "data/robot-data-lab/scene-engine/data/"
        "2rd_floor_seperated/storey_1/configuration/scene_base.usd"
    )
    navigation["validation"] = {"status": "passed", "errors": []}
    readiness = readiness_artifact_with_navigation(
        static_readiness_payload(),
        navigation,
        navigation_artifact_path=run_dir / "navigation_smoke.json",
    )
    readiness["schema"] = READINESS_SCHEMA
    readiness["semantic_source"] = SEMANTIC_SOURCE
    readiness["semantic_usd_binding_status"] = SEMANTIC_USD_BLOCKED
    readiness["validation"] = {"status": "passed", "errors": []}
    (run_dir / "navigation_smoke.json").write_text(
        json.dumps(navigation, indent=2),
        encoding="utf-8",
    )
    (run_dir / "readiness_with_navigation.json").write_text(
        json.dumps(readiness, indent=2),
        encoding="utf-8",
    )

    rc = render_main(["--run-dir", str(run_dir)])

    report = (run_dir / "report.html").read_text(encoding="utf-8")
    assert rc == 0
    assert "B1 / Map 12 Navigation Smoke" in report
    assert "navigation_ready" in report
    assert "kinematic_pose_driven" in report
    assert "blocked_until_segmentation_or_manifest" in report
    assert "manipulation: unsupported" in report
    assert "planner-backed" not in report
    assert "first.fpv.png" in report
    assert "wp_1.chase.png" in report
    assert "navigation_smoke.json" in report
    assert "readiness_with_navigation.json" in report
