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
REBUILT_SCENE_GAUSSIAN = (
    "data/robot-data-lab/scene-engine/data/2rd_floor_seperated/storey_1/scene_gs.usda"
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
        "scene_partitions": [
            {
                "name": "storey_1",
                "gaussian_layer": {
                    "path": REBUILT_SCENE_GAUSSIAN,
                    "exists": True,
                },
            }
        ],
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


def test_alignment_summary_cli_rejects_malformed_readiness_source(tmp_path: Path) -> None:
    readiness_path = tmp_path / "readiness.json"
    output_path = tmp_path / "summary.json"
    readiness_path.write_text("{bad json\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--readiness-artifact",
            str(readiness_path),
            "--output",
            str(output_path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert "readiness artifact source must contain valid JSON object" in completed.stderr
    assert str(readiness_path) in completed.stderr
    assert not output_path.exists()


def test_alignment_manifest_records_lightweight_contract_without_fusion_claim(
    tmp_path: Path,
) -> None:
    module = _load_script()
    readiness = _readiness_with_gaussian_inventory()
    readiness["b1_root"] = "data/B1"
    readiness["map12_root"] = "vendors/agibot_sdk/artifacts/maps/robot_map_12"
    readiness["map12_overlay"] = {
        "status": "candidate",
        "transform_status": "unverified",
        "source_bounds": {"valid": True, "min": [0, 0, 0], "max": [2, 4, 0]},
        "target_bounds": {"valid": True, "min": [-4, -8, 0], "max": [-2, -6, 0]},
        "transform": {
            "method": "bbox_fit_navigation_memory_nav_goals_to_scene_usd_bounds",
            "scale_x": 0.5,
            "scale_y": 0.5,
            "translate_x": -4.0,
            "translate_y": -8.0,
            "source_frame": "robot_map_12_map",
            "target_frame": "b1_rebuilt_scene_usd_world_candidate",
        },
        "residual_evidence": {"status": "not_available", "matched_anchor_count": 0},
        "candidate_waypoints": [
            {
                "source_anchor_id": "sink_kitchen_1",
                "waypoint_id": "b1_overlay_sink_kitchen_1",
                "label": "sink",
                "semantic_source": "robot_map_12_navigation_memory_overlay",
                "map12_nav_goal": {"x": 2.0, "y": 1.0, "yaw": 0.0, "z": 0.0},
                "b1_pose": {
                    "frame": "b1_rebuilt_scene_usd_world_candidate",
                    "x": -3.0,
                    "y": -7.5,
                    "z": 0.0,
                    "yaw_deg": 0.0,
                },
            }
        ],
    }
    navigation = navigation_payload(tmp_path)
    navigation["validation"] = {"status": "passed", "errors": []}

    manifest = module.build_alignment_manifest(
        readiness,
        navigation,
        readiness_artifact="output/run/readiness_with_navigation.json",
        navigation_artifact="output/run/navigation_smoke.json",
        evidence_summary_artifact="output/run/alignment_evidence_summary.json",
        map_bundle="vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot",
        alignment_id="b1-map12-test",
    )

    assert manifest["schema"] == "scene_gaussian_map_alignment_manifest_v1"
    assert manifest["alignment_id"] == "b1-map12-test"
    assert "not a fused USD/Gaussian scene" in manifest["contract_note"]
    assert manifest["source_assets"]["map_bundle"] == (
        "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot"
    )
    assert manifest["frames"]["map_frame"] == "robot_map_12_map"
    assert manifest["frames"]["scene_frame"] == "b1_rebuilt_scene_usd_world_candidate"
    assert manifest["transform"]["status"] == "unverified"
    assert manifest["transform"]["parameters"] == {
        "scale_x": 0.5,
        "scale_y": 0.5,
        "translate_x": -4.0,
        "translate_y": -8.0,
    }
    assert manifest["candidate_correspondences"][0]["usd_binding_status"] == "not_bound"
    assert manifest["evidence"]["alignment_tier"] == "runtime_proven"
    assert manifest["evidence"]["planner_backed"] is False
    assert manifest["semantics"]["semantic_anchors_are_usd_truth"] is False
    assert manifest["gaussian_assets"]["render_status"] == "inventoried_only"
    assert "semantic_usd_truth" in manifest["promotion_requirements"]


def test_alignment_manifest_cli_rejects_non_object_summary_source(tmp_path: Path) -> None:
    readiness_path = tmp_path / "readiness.json"
    summary_path = tmp_path / "alignment_evidence_summary.json"
    output_path = tmp_path / "alignment_manifest.json"
    readiness_path.write_text(json.dumps(_readiness_with_gaussian_inventory()), encoding="utf-8")
    summary_path.write_text("[]\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "manifest",
            "--readiness-artifact",
            str(readiness_path),
            "--evidence-summary",
            str(summary_path),
            "--map-bundle",
            "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot",
            "--output",
            str(output_path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert "alignment evidence summary source must contain a JSON object" in completed.stderr
    assert str(summary_path) in completed.stderr
    assert not output_path.exists()


def test_alignment_manifest_cli_writes_json(tmp_path: Path) -> None:
    readiness_path = tmp_path / "readiness.json"
    navigation_path = tmp_path / "navigation_smoke.json"
    output_path = tmp_path / "alignment_manifest.json"
    readiness = _readiness_with_gaussian_inventory()
    readiness["map12_overlay"] = {
        "status": "candidate",
        "transform_status": "unverified",
        "transform": {
            "method": "bbox_fit_navigation_memory_nav_goals_to_scene_usd_bounds",
            "scale_x": 0.5,
            "scale_y": 0.5,
            "translate_x": -4.0,
            "translate_y": -8.0,
            "source_frame": "robot_map_12_map",
            "target_frame": "b1_rebuilt_scene_usd_world_candidate",
        },
        "candidate_waypoints": [],
    }
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
    navigation = navigation_payload(tmp_path)
    navigation["validation"] = {"status": "passed", "errors": []}
    navigation_path.write_text(json.dumps(navigation), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "manifest",
            "--readiness-artifact",
            str(readiness_path),
            "--navigation-artifact",
            str(navigation_path),
            "--map-bundle",
            "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot",
            "--output",
            str(output_path),
        ],
        check=True,
    )

    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "scene_gaussian_map_alignment_manifest_v1"
    assert manifest["source_assets"]["map_bundle"] == (
        "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot"
    )
    assert manifest["evidence"]["alignment_tier"] == "runtime_proven"
