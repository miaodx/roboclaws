from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from tests.contract.maps.test_b1_map12_digital_twin_readiness import (
    navigation_payload,
    static_readiness_payload,
)

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    ROOT / "skills" / "scene-gaussian-map-alignment" / "scripts" / "summarize_alignment_evidence.py"
)


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("summarize_alignment_evidence", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _readiness_with_gaussian_inventory() -> dict[str, object]:
    readiness = static_readiness_payload()
    readiness["validation"] = {"status": "passed", "errors": []}
    readiness["b1_geometry"] = {
        "gaussian_point_clouds": [
            {
                "path": "data/B1/point_cloud/iteration_100/point_cloud.ply",
                "vertex_count": 6218138,
            }
        ],
        "local_geometry": {
            "local_referenced_layers": ["data/B1/usda/livingroom/gauss.usda"],
        },
    }
    return readiness


def test_alignment_summary_preserves_runtime_and_semantic_boundaries(tmp_path: Path) -> None:
    module = _load_script()
    readiness = _readiness_with_gaussian_inventory()
    navigation = navigation_payload(tmp_path)
    navigation["validation"] = {"status": "passed", "errors": []}

    summary = module.summarize_alignment_evidence(readiness, navigation)

    assert summary["schema"] == "scene_gaussian_map_alignment_evidence_summary_v1"
    assert summary["alignment_tier"] == "runtime_proven"
    assert summary["gaussian_assets"]["render_status"] == "inventoried_only"
    assert summary["gaussian_assets"]["usd_references_gaussian_layers"] is True
    assert summary["semantics"]["semantic_anchors_are_usd_truth"] is False
    assert summary["semantics"]["manipulation_supported"] is False
    assert summary["navigation"]["planner_backed"] is False
    assert "planner_backed navigation proof is missing" in summary["open_blockers"]
    assert "semantic anchors are not bound to USD/scene object truth" in summary["open_blockers"]


def test_alignment_summary_promotes_planner_backed_only_from_navigation_claim(
    tmp_path: Path,
) -> None:
    module = _load_script()
    readiness = _readiness_with_gaussian_inventory()
    navigation = navigation_payload(tmp_path)
    navigation["validation"] = {"status": "passed", "errors": []}
    navigation["planner_backed"] = True
    navigation["navigation_provenance"] = "nav2_planner"

    summary = module.summarize_alignment_evidence(readiness, navigation)

    assert summary["alignment_tier"] == "planner_backed"
    assert summary["navigation"]["navigation_provenance"] == "nav2_planner"
    assert "planner_backed navigation proof is missing" not in summary["open_blockers"]
    assert "Gaussian/splat rendering is not proven" in summary["open_blockers"]


def test_alignment_summary_cli_writes_json(tmp_path: Path) -> None:
    readiness_path = tmp_path / "readiness.json"
    navigation_path = tmp_path / "navigation_smoke.json"
    output_path = tmp_path / "summary.json"
    readiness_path.write_text(
        json.dumps(_readiness_with_gaussian_inventory()),
        encoding="utf-8",
    )
    navigation = navigation_payload(tmp_path)
    navigation["validation"] = {"status": "passed", "errors": []}
    navigation_path.write_text(json.dumps(navigation), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--readiness-artifact",
            str(readiness_path),
            "--navigation-artifact",
            str(navigation_path),
            "--output",
            str(output_path),
        ],
        check=True,
    )

    summary = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["alignment_tier"] == "runtime_proven"
    assert summary["source_artifacts"]["readiness_artifact"] == str(readiness_path)
