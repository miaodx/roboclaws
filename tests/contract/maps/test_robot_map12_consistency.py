from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.maps.check_robot_map12_consistency import check_robot_map12_consistency

REPO_ROOT = Path(__file__).resolve().parents[3]
ROBOT_MAP_12_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "actionable_semantic_map" / "robot_map_12"
SCRIPT = REPO_ROOT / "scripts" / "maps" / "check_robot_map12_consistency.py"


def test_robot_map12_consistency_checks_agibot_map_and_navigation_memory_only() -> None:
    result = check_robot_map12_consistency(ROBOT_MAP_12_FIXTURE)

    assert result["ok"] is True
    assert result["scope"] == "agibot_nav2_occupancy_and_navigation_memory_only"
    assert result["excluded_inputs"] == ["scene_root", "gaussian_map", "b1_alignment_review"]
    assert result["map"] == {
        "frame_id": "map",
        "height": 716,
        "origin": {"x": -35.1000022888, "y": -22.3000011444, "yaw": 0.0},
        "resolution_m": 0.0500000007451,
        "width": 913,
    }
    assert result["navigation_memory"]["item_count"] == 9
    assert result["errors"] == []
    assert result["warnings"] == ["fridge_main nav_goal is in occupied/unknown cell"]
    assert all(anchor["pose"]["in_bounds"] for anchor in result["anchors"])
    assert all(anchor["nav_goal"]["in_bounds"] for anchor in result["anchors"])


def test_robot_map12_consistency_script_writes_json() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(ROBOT_MAP_12_FIXTURE), "--json"],
        check=True,
        text=True,
        capture_output=True,
    )

    result = json.loads(completed.stdout)
    assert result["ok"] is True
    assert result["navigation_memory"]["item_count"] == 9
