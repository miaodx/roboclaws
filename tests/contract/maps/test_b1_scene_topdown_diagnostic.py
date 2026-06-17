from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.maps.render_b1_scene_topdown_diagnostic import (
    DIAGNOSTIC_SCHEMA,
    build_scene_topdown_diagnostic,
    validate_scene_topdown_diagnostic,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "maps" / "render_b1_scene_topdown_diagnostic.py"
SCENE_ROOT = (
    REPO_ROOT / "data" / "robot-data-lab" / "scene-engine" / "data" / ("2rd_floor_seperated")
)


def test_b1_scene_topdown_diagnostic_lists_partitions_and_labels(tmp_path: Path) -> None:
    packet = build_scene_topdown_diagnostic(scene_root=SCENE_ROOT, output_dir=tmp_path)

    assert packet["schema"] == DIAGNOSTIC_SCHEMA
    assert packet["up_axis"] == "z"
    assert packet["horizontal_axes"] == ["x", "y"]
    assert packet["geometry_status"] == "label_inventory_only"
    assert "not a Gaussian asset topdown" in packet["geometry_honesty"]
    assert "cannot verify map-scene alignment" in packet["geometry_honesty"]
    assert packet["partition_count"] >= 6
    partition_ids = {partition["partition_id"] for partition in packet["partitions"]}
    assert {"meeting_room_a", "meeting_room_b", "meeting_room_c"}.issubset(partition_ids)
    assert packet["high_signal_object_labels"]
    assert packet["topdown_image"].endswith("scene_topdown_diagnostic.png")
    assert Path(packet["topdown_image"]).is_file()
    assert validate_scene_topdown_diagnostic(packet) == []


def test_b1_scene_topdown_diagnostic_cli_writes_packet_and_report(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--scene-root",
            str(SCENE_ROOT),
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    packet = json.loads((tmp_path / "scene_topdown_diagnostic.json").read_text(encoding="utf-8"))
    assert summary["schema"] == DIAGNOSTIC_SCHEMA
    assert summary["status"] == "passed"
    assert summary["geometry_status"] == "label_inventory_only"
    assert (tmp_path / "scene_topdown_diagnostic.html").is_file()
    html = (tmp_path / "scene_topdown_diagnostic.html").read_text(encoding="utf-8")
    assert "B1 Scene Label Inventory Diagnostic" in html
    assert "not a Gaussian asset topdown" in html
    assert packet["validation"]["status"] == "passed"
