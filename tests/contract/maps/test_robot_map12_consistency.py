from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.maps.check_robot_map12_consistency import check_robot_map12_consistency

REPO_ROOT = Path(__file__).resolve().parents[3]
ROBOT_MAP_12_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "runtime_map_prior" / "robot_map_12"
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


@pytest.mark.parametrize(
    ("navigation_memory", "expected_error"),
    [
        (
            [],
            "navigation_memory.json must contain a JSON object",
        ),
        (
            {},
            "navigation_memory.json must contain a non-empty items list "
            "or catalog.navigation_memory list",
        ),
        (
            {"items": []},
            "navigation_memory.json items must be a non-empty list",
        ),
        (
            {"items": [[]]},
            "navigation_memory.json item 1 must be a JSON object",
        ),
        (
            {"items": [{"id": "bad_anchor", "nav_goal": {"x": "bad", "y": 1.0}}]},
            "navigation_memory.json item bad_anchor nav_goal x must be a finite number",
        ),
    ],
)
def test_robot_map12_consistency_rejects_malformed_navigation_memory_sources(
    tmp_path: Path,
    navigation_memory: object,
    expected_error: str,
) -> None:
    map_dir = _copy_robot_map12_fixture(tmp_path)
    (map_dir / "navigation_memory.json").write_text(
        json.dumps(navigation_memory),
        encoding="utf-8",
    )

    result = check_robot_map12_consistency(map_dir)

    assert result["ok"] is False
    assert result["anchors"] == []
    assert result["navigation_memory"] == {"item_count": 0}
    assert any(expected_error in error for error in result["errors"])


def test_robot_map12_consistency_reports_malformed_navigation_memory_json(
    tmp_path: Path,
) -> None:
    map_dir = _copy_robot_map12_fixture(tmp_path)
    (map_dir / "navigation_memory.json").write_text("{not-json\n", encoding="utf-8")

    result = check_robot_map12_consistency(map_dir)

    assert result["ok"] is False
    assert result["anchors"] == []
    assert any(
        "navigation_memory.json must contain valid JSON object" in error
        and str(map_dir / "navigation_memory.json") in error
        for error in result["errors"]
    )


@pytest.mark.parametrize(
    ("raw_map", "expected_error"),
    [
        ("{not-json\n", "raw map source must contain valid JSON object"),
        ("[]\n", "raw map source must contain a JSON object"),
    ],
)
def test_robot_map12_consistency_rejects_malformed_raw_map_source(
    tmp_path: Path,
    raw_map: str,
    expected_error: str,
) -> None:
    map_dir = _copy_robot_map12_fixture(tmp_path)
    raw_map_path = map_dir / "agibot" / "raw_map.json.gz"
    with gzip.open(raw_map_path, "wt", encoding="utf-8") as handle:
        handle.write(raw_map)

    result = check_robot_map12_consistency(map_dir)

    assert result["ok"] is False
    assert result["anchors"] == []
    assert any(expected_error in error and str(raw_map_path) in error for error in result["errors"])
    assert not any("lacks occupancy_grid metadata" in error for error in result["errors"])


def test_robot_map12_consistency_accepts_catalog_navigation_memory_items(
    tmp_path: Path,
) -> None:
    map_dir = _copy_robot_map12_fixture(tmp_path)
    navigation_memory_path = map_dir / "navigation_memory.json"
    navigation_memory = json.loads(navigation_memory_path.read_text(encoding="utf-8"))
    items = navigation_memory.pop("items")
    navigation_memory["catalog"] = {"navigation_memory": items}
    navigation_memory_path.write_text(json.dumps(navigation_memory), encoding="utf-8")

    result = check_robot_map12_consistency(map_dir)

    assert result["ok"] is True
    assert result["navigation_memory"]["item_count"] == 9


def _copy_robot_map12_fixture(tmp_path: Path) -> Path:
    map_dir = tmp_path / "robot_map_12"
    shutil.copytree(ROBOT_MAP_12_FIXTURE, map_dir)
    return map_dir
