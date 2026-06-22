from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.maps.render_b1_map12_label_tool import (
    LABEL_DRAFT_MANIFEST_SCHEMA,
    LABEL_TOOL_PACKET_SCHEMA,
    SourceMapTransform,
    build_label_tool_packet,
    draft_manifest_from_shapes,
    label_tool_template,
    label_tool_template_path,
    label_tool_url,
    materialize_scene_evidence_artifacts,
    pixel_to_world,
    render_label_tool_html,
    validate_label_draft_manifest,
    world_to_pixel,
    write_label_tool_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MAP_BUNDLE = REPO_ROOT / "vendors" / "agibot_sdk" / "artifacts" / "maps" / (
    "robot_map_12"
) / "agibot"
REVIEW_MANIFEST = REPO_ROOT / "assets" / "maps" / "b1-map12-alignment-review.json"
SCRIPT = REPO_ROOT / "scripts" / "maps" / "render_b1_map12_label_tool.py"
REMOVED_AUTHORED_BUNDLE = REPO_ROOT / "assets" / "maps" / "agibot-robot-map-12"


def test_map12_label_tool_pixel_world_roundtrip() -> None:
    transform = SourceMapTransform(
        width_px=913,
        height_px=716,
        resolution_m=0.0500000007451,
        origin_x=-35.1000022888,
        origin_y=-22.3000011444,
    )
    source_point = {"x": -7.1, "y": 2.65}

    pixel = world_to_pixel(source_point["x"], source_point["y"], transform)
    restored = pixel_to_world(pixel["x"], pixel["y"], transform)

    assert restored["x"] == pytest.approx(source_point["x"])
    assert restored["y"] == pytest.approx(source_point["y"])


def test_label_tool_packet_seeds_candidate_source_map_shapes() -> None:
    packet = build_label_tool_packet(
        map_bundle=MAP_BUNDLE,
        review_manifest_path=REVIEW_MANIFEST,
    )

    assert packet["schema"] == LABEL_TOOL_PACKET_SCHEMA
    assert packet["draft_manifest_schema"] == LABEL_DRAFT_MANIFEST_SCHEMA
    assert packet["map_bundle"].endswith("vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot")
    assert packet["review_manifest"].endswith("assets/maps/b1-map12-alignment-review.json")
    assert packet["scene_root"].endswith(
        "data/robot-data-lab/scene-engine/data/2rd_floor_seperated"
    )
    assert packet["source_map_frame_policy"] == "raw_source_map_frame_no_rectified_display_frame"
    assert packet["draft_policy"] == {
        "review_status": "draft",
        "export_alignment_status": "candidate",
        "verified_status_allowed": False,
        "source_map_mutated": False,
    }
    assert packet["map"]["image_width_px"] == 913
    assert packet["map"]["image_height_px"] == 716
    assert packet["shapes"]
    assert all(shape["alignment_status"] == "candidate" for shape in packet["shapes"])
    assert {shape["review_status"] for shape in packet["shapes"]} == {
        "accepted",
        "blocked_shared_area",
        "draft",
    }
    assert all(shape["source_map_frame_id"] == "map" for shape in packet["shapes"])

    manifest = packet["initial_draft_manifest"]
    assert validate_label_draft_manifest(manifest) == []
    assert manifest["source_map_mutated"] is False
    assert manifest["verified_status_allowed"] is False
    assert all(label["alignment_status"] == "candidate" for label in manifest["labels"])


def test_label_tool_defaults_to_vendor_map12_without_authored_semantics() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE)

    assert packet["map_bundle"].endswith("vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot")
    assert packet["source_semantics"].endswith(
        "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot/semantics.json"
    )
    assert packet["review_manifest"] == ""
    assert packet["shapes"] == []
    assert packet["source_map_layers"] == {
        "coordinate_policy": "map_native_layers_use_source_map_frame_coordinates_only",
        "driveable_ways": [],
        "fixtures": [],
        "inspection_waypoints": [],
    }
    assert len(packet["navigation_memory_layer"]["items"]) == 9
    assert packet["initial_draft_manifest"]["labels"] == []


def test_authored_map12_bundle_stays_removed() -> None:
    assert not REMOVED_AUTHORED_BUNDLE.exists()


def test_label_tool_packet_has_empty_source_map_layers_without_authored_bundle() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE)
    layers = packet["source_map_layers"]

    assert layers["coordinate_policy"] == "map_native_layers_use_source_map_frame_coordinates_only"
    assert layers["fixtures"] == []
    assert layers["inspection_waypoints"] == []
    assert layers["driveable_ways"] == []


def test_label_tool_packet_exposes_navigation_memory_layer() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE)
    layer = packet["navigation_memory_layer"]
    items = {item["id"]: item for item in layer["items"]}

    assert layer["coordinate_policy"] == "navigation_memory_pose_and_nav_goal_are_map_frame_priors"
    assert len(items) == 9
    assert items["kitchen_center"]["kind"] == "room"
    assert items["kitchen_center"]["label"] == "厨房/吧台区域"
    assert items["kitchen_center"]["pose"]["frame_id"] == "map"
    assert items["kitchen_center"]["nav_goal"]["frame_id"] == "map"
    assert items["fridge_main"]["pose"]["x"] == pytest.approx(1.6879071220842632)
    assert items["fridge_main"]["nav_goal"]["x"] == pytest.approx(1.125)


def test_label_tool_packet_excludes_scene_evidence_by_default() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE)

    assert "scene_evidence" not in packet


def test_label_tool_packet_marks_shared_room_polygon_conflicts() -> None:
    packet = build_label_tool_packet(
        map_bundle=MAP_BUNDLE,
        review_manifest_path=REVIEW_MANIFEST,
    )
    shapes_by_id = {shape["shape_id"]: shape for shape in packet["shapes"]}
    overlapping = [
        shapes_by_id["reception_area_a"],
        shapes_by_id["short_corridor_a"],
        shapes_by_id["storage_room_a"],
    ]

    assert {shape["semantic_source"] for shape in overlapping} == {
        "human_alignment_review_manifest"
    }
    assert all(shape["geometry_conflict"]["status"] == "shared_polygon" for shape in overlapping)
    assert all(
        shape["geometry_conflict"]["room_ids"]
        == ["reception_area_a", "short_corridor_a", "storage_room_a"]
        for shape in overlapping
    )
    assert shapes_by_id["short_corridor_a"]["render_review_recommended"] is True
    assert shapes_by_id["reception_area_a"]["review_status"] == "blocked_shared_area"
    assert shapes_by_id["storage_room_a"]["review_status"] == "blocked_shared_area"


def test_label_tool_packet_exposes_scene_evidence_without_scene_object_coordinates() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE, include_gaussian_scene=True)
    scene_evidence = packet["scene_evidence"]
    room = scene_evidence["rooms"]["meeting_room_a"]

    assert (
        scene_evidence["coordinate_policy"]
        == "do_not_project_scene_or_gaussian_objects_without_verified_transform"
    )
    assert room["candidate_scene_partition_id"] == "meeting_room_a"
    assert room["alignment_status"] == "candidate"
    assert room["identity_status"] == "candidate_name_match_not_verified_identity"
    assert room["coordinate_status"] == "scene_evidence_has_no_map_coordinates"
    assert room["object_name_counts"]["chair"] == 22
    assert "object_map_coordinates" not in json.dumps(scene_evidence)


def test_label_tool_materializes_repo_local_scene_evidence_artifacts(tmp_path: Path) -> None:
    packet = {
        "scene_evidence": {
            "rooms": {
                "meeting_room_a": {
                    "evidence_artifacts": [
                        "output/operator-console/missing.png",
                        str(Path("/etc/passwd")),
                    ]
                }
            }
        }
    }

    repo_local = REPO_ROOT / "output" / "b1-map12" / "label-tool-test-source.png"
    repo_local.parent.mkdir(parents=True, exist_ok=True)
    repo_local.write_bytes(b"repo local fake image")
    try:
        packet["scene_evidence"]["rooms"]["meeting_room_a"]["evidence_artifacts"][0] = str(
            repo_local.relative_to(REPO_ROOT)
        )
        materialize_scene_evidence_artifacts(packet, output_dir=tmp_path)
    finally:
        repo_local.unlink(missing_ok=True)

    links = packet["scene_evidence"]["rooms"]["meeting_room_a"]["evidence_artifact_links"]
    assert links[0]["available"] is True
    assert links[0]["href"].startswith("evidence/")
    assert (tmp_path / links[0]["href"]).is_file()
    assert links[1] == {
        "source_path": "/etc/passwd",
        "available": False,
        "href": "",
    }


def test_label_tool_html_template_is_external_and_supports_shape_moves() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE)
    html = render_label_tool_html(packet, image_data_url_value="data:image/png;base64,abc")

    assert label_tool_template_path().name == "b1_map12_label_tool_template.html"
    assert label_tool_template().startswith("<!doctype html>")
    assert "function moveShapeByDelta" in html
    assert "startGeometry: cloneGeometry(hit.shape.geometry)" in html
    assert "shape.geometry.polygon = geometry.polygon.map" in html


def test_label_tool_rotates_polygons_without_rotated_box_schema() -> None:
    packet = build_label_tool_packet(
        map_bundle=MAP_BUNDLE,
        review_manifest_path=REVIEW_MANIFEST,
    )
    html = render_label_tool_html(packet, image_data_url_value="data:image/png;base64,abc")

    assert "function polygonRotateHandle" in html
    assert "function rotatePolygonDrag" in html
    assert 'data-angle-field="polygon_angle"' in html
    assert '"rotated_box"' not in html
    assert packet["initial_draft_manifest"]["labels"][0]["geometry"]["kind"] == "polygon"


def test_label_tool_supports_global_tilt_without_display_frame_contract() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE)
    html = render_label_tool_html(packet, image_data_url_value="data:image/png;base64,abc")

    assert 'id="globalTiltAngle"' in html
    assert 'id="globalTiltScope"' in html
    assert 'id="globalTiltPivot"' in html
    assert "function applyGlobalTilt" in html
    assert "function rotateShapeAround" in html
    assert "function rotateSourceMapLayersAround" in html
    assert "state.sourceMapLayers = cloneSourceMapLayers" in html
    assert "rotateSourceMapLayersAround(pivot, angleRad)" in html
    assert '"rotated_box"' not in html
    assert '"display_frame":' not in html
    assert '"display_frame_transform"' not in html
    assert packet["source_map_frame_policy"] == "raw_source_map_frame_no_rectified_display_frame"


def test_label_tool_draws_map_native_layers_from_tilted_display_state() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE)
    html = render_label_tool_html(packet, image_data_url_value="data:image/png;base64,abc")

    assert "const fixtures = state.sourceMapLayers.fixtures || []" in html
    assert "const waypoints = state.sourceMapLayers.inspection_waypoints || []" in html
    assert "const ways = state.sourceMapLayers.driveable_ways || []" in html
    assert "drawNavigationMemory" in html
    assert "state.navigationMemoryLayer.items || []" in html
    assert "PACKET.source_map_layers?.fixtures || []" not in html
    assert "PACKET.source_map_layers?.inspection_waypoints || []" not in html
    assert "PACKET.source_map_layers?.driveable_ways || []" not in html


def test_label_tool_html_exposes_layer_toggles_and_candidate_scene_panel() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE)
    html = render_label_tool_html(packet, image_data_url_value="data:image/png;base64,abc")

    assert 'data-layer="rooms"' in html
    assert 'data-layer="fixtures"' in html
    assert 'data-layer="waypoints"' in html
    assert 'data-layer="driveableWays"' in html
    assert 'data-layer="memoryNavGoals"' in html
    assert 'data-layer="memoryObjects"' in html
    assert "function drawFixtures" in html
    assert "function drawWaypoints" in html
    assert "function drawDriveableWays" in html
    assert "function renderSceneEvidence" in html
    assert "geometry conflict" in html
    assert "review geometry/source" in html
    assert "sceneEvidenceSection" in html
    assert "candidate_name_match_not_verified_identity" not in html
    assert "do_not_project_scene_or_gaussian_objects_without_verified_transform" not in html
    assert '"scene_evidence"' not in html
    assert '"object_map_coordinates"' not in html
    assert "Geometry source" not in html
    assert 'data-field="geometry_source"' not in html


def test_label_tool_html_can_include_candidate_scene_panel_when_requested() -> None:
    packet = build_label_tool_packet(map_bundle=MAP_BUNDLE, include_gaussian_scene=True)
    html = render_label_tool_html(packet, image_data_url_value="data:image/png;base64,abc")

    assert "evidence_artifact_links" in html
    assert "candidate_name_match_not_verified_identity" in html
    assert "do_not_project_scene_or_gaussian_objects_without_verified_transform" in html


def test_label_draft_manifest_keeps_circle_candidate_and_review_only() -> None:
    manifest = draft_manifest_from_shapes(
        [
            {
                "shape_id": "hand_circle_001",
                "label": "uncertain lounge area",
                "category": "living_room",
                "navigation_area_id": "south_fixture_area",
                "asset_partition_id": "reception_area_a",
                "source_room_id": "",
                "source_map_frame_id": "map",
                "geometry": {
                    "kind": "circle",
                    "center": {"x": 0.7, "y": -3.8},
                    "radius_m": 0.85,
                },
                "map_center": {"x": 0.7, "y": -3.8},
                "polygon_role": "navigation_area",
                "geometry_source": "scene_engine_partition",
                "alignment_status": "verified",
                "review_status": "accepted",
            }
        ],
        source_packet={
            "source_map_frame_id": "map",
            "map_bundle": str(MAP_BUNDLE),
            "source_semantics": str(MAP_BUNDLE / "semantics.json"),
            "source_image": str(MAP_BUNDLE / "map.pgm"),
        },
    )

    assert validate_label_draft_manifest(manifest) == []
    label = manifest["labels"][0]
    assert label["geometry"]["kind"] == "circle"
    assert label["geometry"]["radius_m"] == pytest.approx(0.85)
    assert label["geometry_source"] == "operator_authored_navigation_zone"
    assert label["alignment_status"] == "candidate"
    assert label["review_status"] == "draft"


def test_label_draft_manifest_rejects_verified_export() -> None:
    packet = build_label_tool_packet(
        map_bundle=MAP_BUNDLE,
        review_manifest_path=REVIEW_MANIFEST,
    )
    manifest = json.loads(json.dumps(packet["initial_draft_manifest"]))
    manifest["labels"][0]["alignment_status"] = "verified"
    manifest["labels"][0]["review_status"] = "accepted"

    errors = validate_label_draft_manifest(manifest)

    assert "label meeting_room_a alignment_status must remain candidate" in errors
    assert "label meeting_room_a review_status must remain draft" in errors


def test_label_tool_cli_writes_standalone_html_and_packet(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
    )

    packet = json.loads((tmp_path / "label_tool_packet.json").read_text(encoding="utf-8"))
    html = (tmp_path / "label_tool.html").read_text(encoding="utf-8")

    assert packet["schema"] == LABEL_TOOL_PACKET_SCHEMA
    assert packet["initial_draft_manifest"]["schema"] == LABEL_DRAFT_MANIFEST_SCHEMA
    assert "data:image/png;base64," in html
    assert "B1 / Map 12 Label Tool" in html


def test_label_tool_can_prepare_served_artifacts(tmp_path: Path) -> None:
    artifacts = write_label_tool_artifacts(
        map_bundle=MAP_BUNDLE,
        output_dir=tmp_path,
    )

    assert artifacts["shape_count"] == 0
    assert artifacts["html_path"] == tmp_path / "label_tool.html"
    assert artifacts["packet_path"] == tmp_path / "label_tool_packet.json"
    assert (tmp_path / "label_tool.html").is_file()
    packet = json.loads((tmp_path / "label_tool_packet.json").read_text(encoding="utf-8"))
    assert "scene_evidence" not in packet
    assert label_tool_url("0.0.0.0", 8765) == "http://127.0.0.1:8765/label_tool.html"
    assert label_tool_url("127.0.0.1", 8765) == "http://127.0.0.1:8765/label_tool.html"


def test_label_tool_cli_exposes_serve_mode() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--serve" in result.stdout
    assert "--include-gaussian-scene" in result.stdout
    assert "--host" in result.stdout
    assert "--port" in result.stdout
