#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.maps.bundle_validation import parse_map_yaml
from scripts.maps.fit_b1_map12_scene_alignment import (
    GLOBAL_MAX_THRESHOLD_M,
    GLOBAL_MEAN_THRESHOLD_M,
    apply_transform_array,
    fit_similarity_transform,
    fit_transform_candidate,
    residual_metrics,
)
from scripts.maps.render_b1_scene_gaussian_topdown import validate_topdown_render_packet

AUTO_ALIGN_SCHEMA = "b1_map12_scene_auto_alignment_probe_v1"
DEFAULT_MAP_BUNDLE = Path("vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot")
DEFAULT_SCENE_TOPDOWN_RENDER = Path(
    "output/b1-map12/scene-gaussian-topdown-crop-z1p8/scene_gaussian_topdown.json"
)
DEFAULT_MANUAL_DRAFT = Path("tmp/b1-map12-scene-correspondences.draft.json")
DEFAULT_OUTPUT_DIR = Path("output/b1-map12/auto-alignment-probe")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe automatic Map12 to B1 scene topdown alignment. Writes candidate evidence "
            "only; does not update accepted correspondence manifests."
        )
    )
    parser.add_argument("--map-bundle", type=Path, default=DEFAULT_MAP_BUNDLE)
    parser.add_argument("--scene-topdown-render", type=Path, default=DEFAULT_SCENE_TOPDOWN_RENDER)
    parser.add_argument("--manual-draft", type=Path, default=DEFAULT_MANUAL_DRAFT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_auto_alignment_probe(
        map_bundle=args.map_bundle,
        scene_topdown_render=args.scene_topdown_render,
        manual_draft=args.manual_draft,
        output_dir=args.output_dir,
    )
    errors = validate_auto_alignment_probe(packet)
    packet["validation"] = {"status": "passed" if not errors else "failed", "errors": errors}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    packet_path = args.output_dir / "auto_alignment_probe.json"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": AUTO_ALIGN_SCHEMA,
                "status": packet["validation"]["status"],
                "auto_alignment_status": packet["auto_alignment_status"],
                "manual_draft_status": packet["manual_draft_reference"]["status"],
                "output": str(packet_path),
                "errors": errors,
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 2


def build_auto_alignment_probe(
    *,
    map_bundle: Path,
    scene_topdown_render: Path,
    manual_draft: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    map_context = load_map_context(map_bundle)
    scene_packet = load_scene_topdown(scene_topdown_render)
    auto = contour_alignment_candidate(
        map_context=map_context,
        scene_packet=scene_packet,
        output_dir=output_dir,
    )
    manual = manual_draft_reference(manual_draft, auto_transform=auto["transform"])
    write_probe_preview(
        manual.get("anchors") or [],
        auto_transform=auto["transform"],
        manual_transform=manual.get("selected_transform") or {},
        path=output_dir / "auto_vs_manual_residuals.png",
    )
    return {
        "schema": AUTO_ALIGN_SCHEMA,
        "map_bundle": str(map_bundle),
        "scene_topdown_render": str(scene_topdown_render),
        "manual_draft": str(manual_draft),
        "contract_note": (
            "Automatic contour alignment is a candidate seed only. It must not be promoted "
            "to accepted correspondences or verified alignment unless residual gates pass."
        ),
        "auto_alignment_status": auto["status"],
        "auto_contour_candidate": auto,
        "manual_draft_reference": manual,
        "preview": str(output_dir / "auto_vs_manual_residuals.png"),
    }


def load_map_context(map_bundle: Path) -> dict[str, Any]:
    map_yaml_path = map_bundle / "nav2.yaml"
    image_path = map_bundle / "occupancy.pgm"
    if not map_yaml_path.is_file():
        raise FileNotFoundError(f"Map12 nav2.yaml missing: {map_yaml_path}")
    if not image_path.is_file():
        raise FileNotFoundError(f"Map12 occupancy.pgm missing: {image_path}")
    map_yaml = parse_map_yaml(map_yaml_path.read_text(encoding="utf-8"))
    image = Image.open(image_path).convert("L")
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else []
    if len(origin) < 2:
        raise ValueError("Map12 nav2.yaml missing origin x/y")
    return {
        "image": image,
        "image_path": image_path,
        "resolution_m": float(map_yaml.get("resolution") or 0.05),
        "origin_x": float(origin[0]),
        "origin_y": float(origin[1]),
    }


def load_scene_topdown(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"scene topdown render missing: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_topdown_render_packet(packet)
    if errors:
        raise ValueError("invalid scene topdown render: " + "; ".join(errors))
    return packet


def contour_alignment_candidate(
    *,
    map_context: dict[str, Any],
    scene_packet: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    map_image = np.array(map_context["image"])
    scene_image = np.array(Image.open(scene_packet["topdown_image"]).convert("L"))
    map_mask = map_known_mask(map_image)
    scene_mask = scene_foreground_mask(scene_image)
    Image.fromarray(map_mask).save(output_dir / "map12_contour_mask.png")
    Image.fromarray(scene_mask).save(output_dir / "scene_topdown_contour_mask.png")
    map_contour = largest_contour(map_mask, "Map12")
    scene_contour = largest_contour(scene_mask, "scene topdown")
    map_box = map_rect_points(map_contour, map_context)
    scene_box = scene_rect_points(scene_contour, scene_packet)
    best = best_rect_fit(map_box, scene_box)
    transform = transform_payload("auto_contour_min_area_rect_similarity_seed", best)
    manual_eval = {}
    return {
        "status": "candidate_seed_only",
        "method": "min_area_rect_contour_similarity_seed",
        "map_mask": str(output_dir / "map12_contour_mask.png"),
        "scene_mask": str(output_dir / "scene_topdown_contour_mask.png"),
        "map_rect_points": round_points(map_box),
        "scene_rect_points": round_points(scene_box),
        "transform": transform,
        "rect_corner_residual_metrics": residual_metrics(
            [float(value) for value in best["residuals"]]
        ),
        "thresholds": {
            "mean_residual_m": GLOBAL_MEAN_THRESHOLD_M,
            "max_residual_m": GLOBAL_MAX_THRESHOLD_M,
        },
        "manual_draft_evaluation": manual_eval,
    }


def map_known_mask(image: np.ndarray) -> np.ndarray:
    mask = (image != 205).astype("uint8") * 255
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)


def scene_foreground_mask(image: np.ndarray) -> np.ndarray:
    mask = (image > 15).astype("uint8") * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)


def largest_contour(mask: np.ndarray, label: str) -> np.ndarray:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError(f"{label} mask has no contours")
    return max(contours, key=cv2.contourArea)


def map_rect_points(contour: np.ndarray, context: dict[str, Any]) -> np.ndarray:
    box = cv2.boxPoints(cv2.minAreaRect(contour))
    height = context["image"].height
    points = []
    for px, py in box:
        x = float(context["origin_x"]) + float(px) * float(context["resolution_m"])
        y = float(context["origin_y"]) + (height - 1.0 - float(py)) * float(context["resolution_m"])
        points.append([x, y])
    return np.array(points, dtype=float)


def scene_rect_points(contour: np.ndarray, packet: dict[str, Any]) -> np.ndarray:
    box = cv2.boxPoints(cv2.minAreaRect(contour))
    return np.array(
        [scene_pixel_to_xy(float(px), float(py), packet) for px, py in box],
        dtype=float,
    )


def scene_pixel_to_xy(px: float, py: float, packet: dict[str, Any]) -> list[float]:
    camera = packet["camera"]
    lens = camera["lens"]
    width = int(packet["width_px"])
    height = int(packet["height_px"])
    eye = np.array(camera["eye"], dtype=float)
    target = np.array(camera["target"], dtype=float)
    up = np.array(camera["up"], dtype=float)
    forward = target - eye
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    camera_up = np.cross(right, forward)
    camera_up = camera_up / np.linalg.norm(camera_up)
    focal_y = (height / 2.0) / math.tan(math.radians(float(lens["vertical_fov_deg"])) / 2.0)
    dx = (px - width / 2.0) / focal_y
    dy = -(py - height / 2.0) / focal_y
    ray = forward + dx * right + dy * camera_up
    t = (0.0 - eye[2]) / ray[2]
    point = eye + t * ray
    return [float(point[0]), float(point[1])]


def best_rect_fit(map_box: np.ndarray, scene_box: np.ndarray) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for reverse in (False, True):
        target = scene_box[::-1] if reverse else scene_box
        for shift in range(4):
            shifted = np.roll(target, shift, axis=0)
            transform = fit_similarity_transform(map_box, shifted)
            predicted = apply_transform_array(map_box, transform)
            residuals = np.linalg.norm(predicted - shifted, axis=1)
            score = float(residuals.mean() + residuals.max())
            candidate = {
                "score": score,
                "reverse": reverse,
                "shift": shift,
                "transform": transform,
                "residuals": residuals,
            }
            if best is None or score < best["score"]:
                best = candidate
    if best is None:
        raise ValueError("failed to fit rectangle candidate")
    return best


def transform_payload(source: str, candidate: dict[str, Any]) -> dict[str, Any]:
    transform = dict(candidate["transform"])
    transform["source"] = source
    transform["candidate_status"] = "candidate_seed_only"
    transform["rect_corner_order"] = {
        "reverse": bool(candidate["reverse"]),
        "shift": int(candidate["shift"]),
    }
    return transform


def manual_draft_reference(path: Path, *, auto_transform: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"manual draft correspondence file missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    anchors = [
        item
        for item in payload.get("anchors") or []
        if isinstance(item, dict) and valid_draft_anchor(item)
    ]
    if len(anchors) < 6:
        return {"status": "insufficient_manual_draft_anchors", "anchors": anchors}
    source = np.array([item["map_xy"] for item in anchors], dtype=float)
    target = np.array(
        [[item["scene_xyz"][0], item["scene_xyz"][1]] for item in anchors],
        dtype=float,
    )
    rigid = fit_transform_candidate("rigid_2d", source, target)
    similarity = fit_transform_candidate("similarity_2d", source, target)
    auto_predicted = apply_transform_array(source, auto_transform)
    auto_residuals = np.linalg.norm(auto_predicted - target, axis=1)
    auto_metrics = residual_metrics([float(value) for value in auto_residuals])
    auto_passed = (
        bool(auto_metrics)
        and float(auto_metrics["mean_residual_m"]) <= GLOBAL_MEAN_THRESHOLD_M
        and float(auto_metrics["max_residual_m"]) <= GLOBAL_MAX_THRESHOLD_M
    )
    selected = rigid if rigid["passes_residual_thresholds"] else similarity
    status = (
        "manual_draft_passes_thresholds"
        if selected["passes_residual_thresholds"]
        else "manual_draft_fails_thresholds"
    )
    return {
        "status": status,
        "anchor_count": len(anchors),
        "anchors": anchors,
        "selected_transform_type": selected["transform_type"]
        if selected["passes_residual_thresholds"]
        else "",
        "selected_transform": (
            selected["transform"] if selected["passes_residual_thresholds"] else {}
        ),
        "rigid_candidate": strip_transform_candidate(rigid),
        "similarity_candidate": strip_transform_candidate(similarity),
        "auto_contour_transform_residual_metrics": auto_metrics,
        "auto_contour_transform_passes_thresholds": auto_passed,
        "auto_contour_transform_status": (
            "candidate_failed_thresholds"
            if not auto_passed
            else "candidate_passed_thresholds_needs_review"
        ),
    }


def valid_draft_anchor(anchor: dict[str, Any]) -> bool:
    return (
        isinstance(anchor.get("map_xy"), list)
        and len(anchor["map_xy"]) == 2
        and isinstance(anchor.get("scene_xyz"), list)
        and len(anchor["scene_xyz"]) == 3
    )


def strip_transform_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "transform_type": candidate["transform_type"],
        "transform": candidate["transform"],
        "mean_residual_m": candidate.get("mean_residual_m"),
        "max_residual_m": candidate.get("max_residual_m"),
        "passes_residual_thresholds": candidate["passes_residual_thresholds"],
    }


def write_probe_preview(
    anchors: list[dict[str, Any]],
    *,
    auto_transform: dict[str, Any],
    manual_transform: dict[str, Any],
    path: Path,
) -> None:
    image = Image.new("RGB", (960, 720), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    if not anchors:
        draw.text((30, 30), "No manual draft anchors available", fill=(120, 30, 30))
        image.save(path)
        return
    source = np.array([item["map_xy"] for item in anchors], dtype=float)
    scene = np.array(
        [[item["scene_xyz"][0], item["scene_xyz"][1]] for item in anchors],
        dtype=float,
    )
    auto = apply_transform_array(source, auto_transform)
    manual = apply_transform_array(source, manual_transform) if manual_transform else auto
    points = np.vstack([scene, auto, manual])
    min_xy = points.min(axis=0)
    max_xy = points.max(axis=0)
    span = np.maximum(max_xy - min_xy, 1e-6)

    def canvas(point: np.ndarray) -> tuple[int, int]:
        return (
            int(round(70 + (point[0] - min_xy[0]) / span[0] * 820)),
            int(round(650 - (point[1] - min_xy[1]) / span[1] * 580)),
        )

    draw.text(
        (30, 24),
        "Blue: manual scene pick. Red: auto contour prediction. Green: manual-draft fit.",
        fill=(40, 45, 52),
    )
    for anchor, scene_point, auto_point, manual_point in zip(
        anchors, scene, auto, manual, strict=True
    ):
        sxy = canvas(scene_point)
        axy = canvas(auto_point)
        mxy = canvas(manual_point)
        draw.line((*axy, *sxy), fill=(196, 57, 42), width=2)
        draw.line((*mxy, *sxy), fill=(42, 128, 68), width=2)
        draw.ellipse((sxy[0] - 5, sxy[1] - 5, sxy[0] + 5, sxy[1] + 5), fill=(37, 99, 235))
        draw.rectangle((axy[0] - 5, axy[1] - 5, axy[0] + 5, axy[1] + 5), fill=(196, 57, 42))
        draw.rectangle((mxy[0] - 4, mxy[1] - 4, mxy[0] + 4, mxy[1] + 4), fill=(42, 128, 68))
        draw.text((sxy[0] + 7, sxy[1] - 7), str(anchor.get("anchor_id") or ""), fill=(35, 45, 58))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def validate_auto_alignment_probe(packet: dict[str, Any]) -> list[str]:
    errors = []
    if packet.get("schema") != AUTO_ALIGN_SCHEMA:
        errors.append("unexpected auto alignment probe schema")
    if packet.get("auto_alignment_status") != "candidate_seed_only":
        errors.append("auto alignment must remain candidate_seed_only")
    manual = packet.get("manual_draft_reference")
    if not isinstance(manual, dict):
        errors.append("manual draft reference missing")
    elif manual.get("status") not in {
        "manual_draft_passes_thresholds",
        "manual_draft_fails_thresholds",
        "insufficient_manual_draft_anchors",
    }:
        errors.append("unexpected manual draft status")
    if not Path(str(packet.get("preview") or "")).is_file():
        errors.append("auto alignment preview missing")
    return errors


def round_points(points: np.ndarray) -> list[list[float]]:
    return [[round(float(value), 6) for value in point] for point in points.tolist()]


if __name__ == "__main__":
    raise SystemExit(main())
