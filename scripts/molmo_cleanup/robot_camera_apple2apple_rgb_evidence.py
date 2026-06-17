from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

from scripts.molmo_cleanup import robot_camera_apple2apple_image_metrics as image_metrics

PROTECTED_TARGET_REGION_MEAN_ABS_RGB_THRESHOLD = 35.0
PROTECTED_TARGET_REGION_GT40_FRACTION_THRESHOLD = 0.5
PROTECTED_TARGET_REGION_RENDER_RESIDUAL_MEAN_ABS_RGB_THRESHOLD = 40.0


def object_rgb_view_evidence(
    *,
    kind: str,
    target_id: str,
    locations: list[dict[str, Any]],
    output_dir: Path | None,
) -> dict[str, Any]:
    selected = None
    for item in locations:
        if not isinstance(item, dict):
            continue
        target = _dict(item.get("target"))
        same_kind = str(target.get("kind") or "") == kind
        same_target = str(target.get("target_id") or "") == target_id
        if same_kind and same_target:
            selected = item
            break
    if selected is None:
        return {
            "status": "not_captured_in_selected_views",
            "selected_target": False,
            "target_coverage_status": "not_captured_in_selected_views",
            "view_status_counts": {},
        }
    views = []
    for backend_id in ("mujoco", "isaac"):
        backend_views = _dict(_dict(selected.get("views")).get(backend_id))
        for view_key in ("fpv", "chase"):
            image_path = str(backend_views.get(view_key) or "")
            evidence = _image_nonblank_evidence(image_path=image_path, output_dir=output_dir)
            views.append(
                {
                    "backend": backend_id,
                    "view": view_key,
                    "image_path": image_path,
                    **evidence,
                }
            )
    status_counts = _status_counts(item.get("status") for item in views)
    if views and all(item.get("status") == "nonblank_rgb" for item in views):
        status = "selected_views_nonblank"
    elif any(item.get("status") == "blank_rgb" for item in views):
        status = "selected_views_blank_rgb"
    elif any(str(item.get("status") or "").startswith("missing") for item in views):
        status = "selected_views_missing_image"
    else:
        status = "selected_views_unverified"
    target_coverage = _selected_target_coverage_evidence(
        kind=kind,
        target_id=target_id,
        location=selected,
    )
    visual_state_evidence = _selected_target_visual_state_evidence(
        kind=kind,
        target_id=target_id,
        location=selected,
        output_dir=output_dir,
    )
    return {
        "schema": "robot_camera_object_rgb_view_evidence_v1",
        "status": status,
        "selected_target": True,
        **target_coverage,
        **visual_state_evidence,
        "view_status_counts": status_counts,
        "views": views,
        "interpretation": (
            "Selected target FPV/chase image evidence checks whether the rendered RGB "
            "views are present and nonblank. Target coverage checks whether the selected "
            "location's robot pose and focus contracts are centered on the same object or "
            "receptacle. It is not per-pixel shape parity without segmentation/bbox evidence."
        ),
    }


def _selected_target_visual_state_evidence(
    *,
    kind: str,
    target_id: str,
    location: dict[str, Any],
    output_dir: Path | None,
) -> dict[str, Any]:
    if kind != "object":
        return {"target_visual_state_status": "not_applicable"}
    bbox = _selected_target_mujoco_fpv_bbox(location, target_id=target_id)
    if bbox is None:
        return {
            "target_visual_state_status": "missing_target_bbox",
            "target_visual_state_bbox_source": "mujoco_fpv_visibility",
        }
    views = _dict(location.get("views"))
    mujoco_fpv = str(_dict(views.get("mujoco")).get("fpv") or "")
    isaac_fpv = str(_dict(views.get("isaac")).get("fpv") or "")
    crop_delta = _image_crop_delta(
        left_image_path=mujoco_fpv,
        right_image_path=isaac_fpv,
        bbox=bbox,
        output_dir=output_dir,
    )
    if str(crop_delta.get("status") or "") != "computed":
        return {
            "target_visual_state_status": "target_region_unverified",
            "target_visual_state_bbox": bbox,
            "target_visual_state_delta": crop_delta,
        }
    mean_abs = float(crop_delta.get("mean_abs_rgb") or 0.0)
    gt40 = float(crop_delta.get("diff_gt_40_fraction") or 0.0)
    if (
        mean_abs <= PROTECTED_TARGET_REGION_MEAN_ABS_RGB_THRESHOLD
        and gt40 <= PROTECTED_TARGET_REGION_GT40_FRACTION_THRESHOLD
    ):
        status = "selected_object_visual_state_aligned"
        alignment_mode = "strict_raw_rgb"
    elif (
        mean_abs <= PROTECTED_TARGET_REGION_RENDER_RESIDUAL_MEAN_ABS_RGB_THRESHOLD
        and gt40 <= PROTECTED_TARGET_REGION_GT40_FRACTION_THRESHOLD
    ):
        status = "selected_object_visual_state_aligned"
        alignment_mode = "moderate_render_residual"
    else:
        status = "selected_object_visual_state_delta"
        alignment_mode = "raw_rgb_delta"
    return {
        "target_visual_state_status": status,
        "target_visual_state_alignment_mode": alignment_mode,
        "target_visual_state_bbox": bbox,
        "target_visual_state_delta": crop_delta,
        "target_visual_state_thresholds": {
            "mean_abs_rgb_max": PROTECTED_TARGET_REGION_MEAN_ABS_RGB_THRESHOLD,
            "diff_gt_40_fraction_max": PROTECTED_TARGET_REGION_GT40_FRACTION_THRESHOLD,
            "render_residual_mean_abs_rgb_max": (
                PROTECTED_TARGET_REGION_RENDER_RESIDUAL_MEAN_ABS_RGB_THRESHOLD
            ),
        },
    }


def _selected_target_mujoco_fpv_bbox(
    location: dict[str, Any],
    *,
    target_id: str,
) -> list[int] | None:
    focus = _dict(_dict(_dict(location.get("contracts")).get("mujoco")).get("focus"))
    if str(focus.get("object_id") or "") != target_id:
        return None
    visibility = _dict(focus.get("fpv_visibility"))
    for raw_box in visibility.get("boxes") or []:
        box = _dict(raw_box)
        bbox = box.get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            try:
                return [int(value) for value in bbox]
            except (TypeError, ValueError):
                return None
    return None


def _image_crop_delta(
    *,
    left_image_path: str,
    right_image_path: str,
    bbox: list[int],
    output_dir: Path | None,
) -> dict[str, Any]:
    left_path = _resolve_output_path(left_image_path, output_dir)
    right_path = _resolve_output_path(right_image_path, output_dir)
    if left_path is None or right_path is None:
        return {"status": "missing_image_path"}
    if not left_path.exists() or not right_path.exists():
        return {
            "status": "missing_image_file",
            "left_exists": left_path.exists(),
            "right_exists": right_path.exists(),
        }
    try:
        with Image.open(left_path) as left_raw, Image.open(right_path) as right_raw:
            left = left_raw.convert("RGB")
            right = right_raw.convert("RGB")
            if right.size != left.size:
                right = right.resize(left.size)
            safe_bbox = _safe_image_bbox(bbox, left.size)
            if safe_bbox is None:
                return {"status": "invalid_bbox", "bbox": bbox, "image_size": list(left.size)}
            left_crop = left.crop(tuple(safe_bbox))
            right_crop = right.crop(tuple(safe_bbox))
            diff = ImageChops.difference(left_crop, right_crop)
            stat = ImageStat.Stat(diff)
            mean_abs = sum(stat.mean) / len(stat.mean)
            rms = sum(value * value for value in stat.rms) ** 0.5 / len(stat.rms)
            pixel_count = max(left_crop.size[0] * left_crop.size[1], 1)
            nonzero = 0
            diff_gt_40 = 0
            diff_gt_80 = 0
            for pixel in diff.getdata():
                if pixel != (0, 0, 0):
                    nonzero += 1
                mean_pixel_delta = sum(pixel) / 3.0
                if mean_pixel_delta > 40.0:
                    diff_gt_40 += 1
                if mean_pixel_delta > 80.0:
                    diff_gt_80 += 1
            return {
                "status": "computed",
                "bbox": safe_bbox,
                "crop_size": list(left_crop.size),
                "mean_abs_rgb": round(float(mean_abs), 4),
                "rms_rgb": round(float(rms), 4),
                "nonzero_fraction": round(nonzero / pixel_count, 6),
                "diff_gt_40_fraction": round(diff_gt_40 / pixel_count, 6),
                "diff_gt_80_fraction": round(diff_gt_80 / pixel_count, 6),
            }
    except Exception as exc:
        return {
            "status": "unreadable_image",
            "error": type(exc).__name__,
            "reason": str(exc),
        }


def _resolve_output_path(image_path: str, output_dir: Path | None) -> Path | None:
    if not image_path:
        return None
    path = Path(image_path)
    if not path.is_absolute() and output_dir is not None:
        path = output_dir / path
    return path


def _safe_image_bbox(bbox: list[int], size: tuple[int, int]) -> list[int] | None:
    if len(bbox) != 4:
        return None
    width, height = size
    left = max(0, min(int(bbox[0]), width))
    top = max(0, min(int(bbox[1]), height))
    right = max(0, min(int(bbox[2]), width))
    bottom = max(0, min(int(bbox[3]), height))
    if right <= left or bottom <= top:
        return None
    return [left, top, right, bottom]


def _selected_target_coverage_evidence(
    *,
    kind: str,
    target_id: str,
    location: dict[str, Any],
) -> dict[str, Any]:
    robot_pose = _dict(location.get("robot_pose"))
    pose_request = _dict(robot_pose.get("pose_request"))
    pose_target_object_id = str(
        robot_pose.get("target_object_id") or pose_request.get("target_object_id") or ""
    )
    pose_target_receptacle_id = str(
        robot_pose.get("target_receptacle_id") or pose_request.get("target_receptacle_id") or ""
    )
    focus_evidence = _selected_target_focus_evidence(
        kind=kind, target_id=target_id, location=location
    )
    pose_status = "missing_robot_pose_target"
    if kind == "object":
        pose_status = (
            "object_centered_pose"
            if pose_target_object_id == target_id
            else "support_or_receptacle_centered_pose"
            if pose_target_receptacle_id
            else "missing_object_centered_pose"
        )
    elif kind == "receptacle":
        pose_status = (
            "receptacle_centered_pose"
            if pose_target_receptacle_id == target_id
            else "missing_receptacle_centered_pose"
        )
    focus_status = str(focus_evidence.get("focus_status") or "")
    if (
        kind == "object"
        and pose_status == "object_centered_pose"
        and focus_status
        in {
            "selected_object_focus",
            "missing_focus_contract",
        }
    ):
        coverage_status = "selected_object_centered_coverage"
    elif (
        kind == "receptacle"
        and pose_status == "receptacle_centered_pose"
        and focus_status
        in {
            "selected_receptacle_focus",
            "missing_focus_contract",
        }
    ):
        coverage_status = "selected_receptacle_centered_coverage"
    else:
        coverage_status = "selected_target_coverage_gap"
    return {
        "target_coverage_status": coverage_status,
        "robot_pose_target_status": pose_status,
        "robot_pose_target_object_id": pose_target_object_id,
        "robot_pose_target_receptacle_id": pose_target_receptacle_id,
        "robot_pose_target_position": robot_pose.get("target_position")
        or pose_request.get("target_position"),
        **focus_evidence,
    }


def _selected_target_focus_evidence(
    *,
    kind: str,
    target_id: str,
    location: dict[str, Any],
) -> dict[str, Any]:
    focus_rows = []
    for backend_id in ("mujoco", "isaac"):
        focus = _dict(
            _dict(_dict(location.get("contracts")).get(backend_id)).get("focus")
        ) or _dict(_dict(_dict(location.get("provenance")).get(backend_id)).get("focus"))
        if not focus:
            continue
        focus_rows.append(
            {
                "backend": backend_id,
                "object_id": focus.get("object_id"),
                "receptacle_id": focus.get("receptacle_id"),
                "focus_mode": focus.get("focus_mode"),
                "source": focus.get("source") or focus.get("provenance"),
                "fpv_visibility_status": _dict(focus.get("fpv_visibility")).get("status"),
                "visibility_status": _dict(focus.get("visibility")).get("status"),
            }
        )
    if not focus_rows:
        return {
            "focus_status": "missing_focus_contract",
            "focus_contracts": [],
        }
    if kind == "object":
        status = (
            "selected_object_focus"
            if all(str(row.get("object_id") or "") == target_id for row in focus_rows)
            else "selected_focus_mismatch"
        )
    else:
        status = (
            "selected_receptacle_focus"
            if all(str(row.get("receptacle_id") or "") == target_id for row in focus_rows)
            else "selected_focus_mismatch"
        )
    return {
        "focus_status": status,
        "focus_contracts": focus_rows,
    }


def _image_nonblank_evidence(*, image_path: str, output_dir: Path | None) -> dict[str, Any]:
    if not image_path:
        return {"status": "missing_image_path"}
    path = Path(image_path)
    if not path.is_absolute() and output_dir is not None:
        path = output_dir / path
    if not path.exists():
        return {"status": "missing_image_file"}
    try:
        with Image.open(path) as raw:
            metrics = image_metrics.image_visual_metrics(raw.convert("RGB"))
    except OSError as exc:
        return {"status": "unreadable_image", "error": str(exc)}
    nonblank = (
        metrics.get("mean_luminance", 0.0) > 1.0
        or metrics.get("edge_mean", 0.0) > 0.1
        or metrics.get("overexposed_fraction", 0.0) > 0.0
    )
    return {
        "status": "nonblank_rgb" if nonblank else "blank_rgb",
        "mean_luminance": metrics.get("mean_luminance"),
        "edge_mean": metrics.get("edge_mean"),
        "overexposed_fraction": metrics.get("overexposed_fraction"),
        "underexposed_fraction": metrics.get("underexposed_fraction"),
    }


def _status_counts(values: Any) -> dict[str, int]:
    collected = [str(value) for value in values if value]
    return {name: collected.count(name) for name in sorted(set(collected))}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
