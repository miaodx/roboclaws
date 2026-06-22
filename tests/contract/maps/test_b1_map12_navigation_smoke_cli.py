from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "run_b1_map12_navigation_smoke.py"


@pytest.mark.parametrize(
    ("source", "message"),
    (
        ("{not-json\n", "readiness artifact must contain valid JSON object"),
        ("[]\n", "readiness artifact must contain a JSON object"),
    ),
)
def test_navigation_smoke_cli_rejects_malformed_readiness_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    readiness_path = tmp_path / "readiness.json"
    readiness_path.write_text(source, encoding="utf-8")
    waypoint_path = tmp_path / "waypoint_pose_requests.json"
    waypoint_path.write_text(json.dumps(_ready_waypoint_pose_requests()), encoding="utf-8")
    output_dir = tmp_path / "navigation-smoke"

    completed = _run_smoke(
        readiness_path=readiness_path,
        waypoint_path=waypoint_path,
        output_dir=output_dir,
    )

    assert completed.returncode != 0
    assert message in completed.stderr
    assert not (output_dir / "navigation_smoke.json").exists()


def test_navigation_smoke_cli_rejects_missing_readiness_source(tmp_path: Path) -> None:
    readiness_path = tmp_path / "missing_readiness.json"
    waypoint_path = tmp_path / "waypoint_pose_requests.json"
    waypoint_path.write_text(json.dumps(_ready_waypoint_pose_requests()), encoding="utf-8")
    output_dir = tmp_path / "navigation-smoke"

    completed = _run_smoke(
        readiness_path=readiness_path,
        waypoint_path=waypoint_path,
        output_dir=output_dir,
    )

    assert completed.returncode != 0
    assert "readiness artifact missing:" in completed.stderr
    assert not (output_dir / "navigation_smoke.json").exists()


@pytest.mark.parametrize(
    ("source", "message"),
    (
        ("{not-json\n", "waypoint pose request artifact must contain valid JSON object"),
        ("[]\n", "waypoint pose request artifact must contain a JSON object"),
    ),
)
def test_navigation_smoke_cli_rejects_malformed_waypoint_request_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    readiness_path = tmp_path / "readiness.json"
    readiness_path.write_text(json.dumps(_readiness()), encoding="utf-8")
    waypoint_path = tmp_path / "waypoint_pose_requests.json"
    waypoint_path.write_text(source, encoding="utf-8")
    output_dir = tmp_path / "navigation-smoke"

    completed = _run_smoke(
        readiness_path=readiness_path,
        waypoint_path=waypoint_path,
        output_dir=output_dir,
    )

    assert completed.returncode != 0
    assert message in completed.stderr
    assert not (output_dir / "navigation_smoke.json").exists()


def test_navigation_smoke_cli_rejects_missing_waypoint_request_source(tmp_path: Path) -> None:
    readiness_path = tmp_path / "readiness.json"
    readiness_path.write_text(json.dumps(_readiness()), encoding="utf-8")
    waypoint_path = tmp_path / "missing_waypoint_pose_requests.json"
    output_dir = tmp_path / "navigation-smoke"

    completed = _run_smoke(
        readiness_path=readiness_path,
        waypoint_path=waypoint_path,
        output_dir=output_dir,
    )

    assert completed.returncode != 0
    assert "waypoint pose request artifact missing:" in completed.stderr
    assert not (output_dir / "navigation_smoke.json").exists()


def _run_smoke(
    *,
    readiness_path: Path,
    waypoint_path: Path,
    output_dir: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--readiness-artifact",
            str(readiness_path),
            "--waypoint-pose-requests",
            str(waypoint_path),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
    )


def _readiness() -> dict[str, object]:
    return {"schema": "b1_map12_digital_twin_readiness_v1"}


def _ready_waypoint_pose_requests() -> dict[str, object]:
    return {
        "schema": "b1_map12_waypoint_pose_requests_v1",
        "status": "ready",
        "semantic_source": "b1_map12_reviewed_alignment_overlay",
        "alignment_transform_source": "reviewed_correspondence_fit",
        "planner_backed": False,
        "physical_robot": False,
        "robot_navigation_supported": False,
        "waypoint_count": 2,
        "blocked_request_count": 0,
        "blocked_requests": [],
        "waypoints": [
            {
                "waypoint_id": "manual_point_a",
                "alignment_transform_source": "reviewed_correspondence_fit",
                "alignment_artifact": "alignment_residuals.json",
                "b1_pose": {"x": 1.0, "y": 2.0},
            },
            {
                "waypoint_id": "manual_point_b",
                "alignment_transform_source": "reviewed_correspondence_fit",
                "alignment_artifact": "alignment_residuals.json",
                "b1_pose": {"x": 2.0, "y": 3.0},
            },
        ],
    }
