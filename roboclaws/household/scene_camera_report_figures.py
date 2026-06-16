from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from roboclaws.household import scene_camera_image_metrics, scene_camera_render_domain
from roboclaws.household.scene_camera_report_format import (
    _dimension_text,
    _float_text,
    _image_button,
    _is_room_view,
    _is_vec3,
    _lane_order,
    _missing_figure,
    _rgb_text,
    _safe_id,
    _vec_text,
)

MOLMOSPACES_LANE_ID = scene_camera_render_domain.MOLMOSPACES_LANE_ID
_image_visual_metrics = scene_camera_image_metrics.image_visual_metrics
_image_region_visual_metrics = scene_camera_image_metrics.image_region_visual_metrics


def _standalone_review_section(manifest: dict[str, Any], *, output_dir: Path) -> str:
    views = _view_sections(manifest, output_dir=output_dir, primary=True)
    if not views:
        return ""
    note = (
        "Primary visual review surface: each lane image is standalone and opens in the "
        "popup. The contact sheet below is only a secondary overview."
    )
    return f"""
<section class="panel review-panel">
  <h2>Standalone Image Review</h2>
  <p class="note">{html.escape(note)}</p>
</section>
{views}
"""


def _view_sections(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    primary: bool = False,
) -> str:
    views = [
        item
        for item in manifest.get("canonical_camera_views") or []
        if isinstance(item, dict) and item.get("view_id")
    ]
    if not views:
        views = [
            {
                "view_id": f"view_{index:02d}_{_safe_id(anchor.get('category'))}",
                **anchor,
            }
            for index, anchor in enumerate(
                [item for item in manifest.get("anchors") or [] if isinstance(item, dict)],
                start=1,
            )
        ]
    blocks = []
    for view in views:
        view_id = str(view.get("view_id") or "")
        room = html.escape(str(view.get("room_id") or "scene"))
        category = html.escape(str(view.get("category") or "view"))
        anchor_id = html.escape(str(view.get("anchor_id") or ""))
        basis = html.escape(str(view.get("camera_basis") or ""))
        figures = "\n".join(
            _figure(manifest, lane_id, view_id, output_dir=output_dir)
            for lane_id in _lane_order(manifest)
        )
        panel_class = "panel review-panel" if primary else "panel"
        blocks.append(
            f"""
<section class="{panel_class}">
  <h2>{room} {category}</h2>
  <p class="note">{anchor_id} {basis}</p>
  <div class="comparison-grid">
    {figures}
  </div>
</section>
"""
        )
    return "".join(blocks)


def _figure(manifest: dict[str, Any], lane_id: str, view_id: str, *, output_dir: Path) -> str:
    lane = (manifest.get("lanes") or {}).get(lane_id)
    if not isinstance(lane, dict):
        return _missing_figure("missing lane", lane_id)
    image = (
        (lane.get("images") or {}).get(view_id) if isinstance(lane.get("images"), dict) else None
    )
    view = _view_payload(lane, view_id)
    if not isinstance(image, dict):
        return _missing_figure(f"missing {view_id}", lane_id)
    path = str(image.get("path") or "")
    missing = "" if (output_dir / path).is_file() else " (missing on disk)"
    detail = _dimension_text(
        image.get("dimensions") if isinstance(image.get("dimensions"), dict) else {}
    )
    tone = _figure_tone_text(output_dir / path) if not missing else ""
    wall_tone = (
        _figure_wall_tone_text(output_dir / path)
        if not missing and _is_room_view(manifest, view_id)
        else ""
    )
    candidate_delta = _figure_candidate_delta_text(manifest, lane_id=lane_id, view_id=view_id)
    alt = f"{lane_id} {view_id}"
    target = view.get("target") or view.get("lookat")
    pose = f"eye={_vec_text(view.get('eye'))} target={_vec_text(target)}"
    backend_pose = _backend_pose_text(view)
    calibration = str(view.get("calibration_status") or lane.get("calibration_status") or "")
    return (
        f"<figure>{_image_button(path, alt)}"
        f"<figcaption><strong>{html.escape(lane_id)}</strong>"
        f"<span>{html.escape(detail + missing)}</span>"
        f"<span>{html.escape(tone)}</span>"
        f"<span>{html.escape(wall_tone)}</span>"
        f"<span>{html.escape(candidate_delta)}</span>"
        f"<span>{html.escape(pose)}</span>"
        f"<span>{html.escape(backend_pose)}</span>"
        f"<span>{html.escape(calibration)}</span>"
        "</figcaption></figure>"
    )


def _figure_tone_text(path: Path) -> str:
    metrics = _image_visual_metrics(path)
    return (
        f"tone lum={_float_text(metrics.get('mean_luminance'))} "
        f"rgb={_rgb_text(metrics.get('mean_rgb'))}"
    )


def _figure_wall_tone_text(path: Path) -> str:
    metrics = _image_region_visual_metrics(path, region_id="upper_center_wall_proxy")
    return f"wall-proxy lum={_float_text(metrics.get('mean_luminance'))}"


def _figure_candidate_delta_text(
    manifest: dict[str, Any],
    *,
    lane_id: str,
    view_id: str,
) -> str:
    registry = (
        manifest.get("lane_registry") if isinstance(manifest.get("lane_registry"), dict) else {}
    )
    baseline_id = str(registry.get("baseline") or MOLMOSPACES_LANE_ID)
    if lane_id == baseline_id:
        return "baseline tone reference"
    diagnostics = (
        manifest.get("candidate_visual_diagnostics")
        if isinstance(manifest.get("candidate_visual_diagnostics"), dict)
        else {}
    )
    for candidate in diagnostics.get("candidates") or []:
        if not isinstance(candidate, dict) or str(candidate.get("candidate") or "") != lane_id:
            continue
        for view in candidate.get("views") or []:
            if not isinstance(view, dict) or str(view.get("view_id") or "") != view_id:
                continue
            delta = view.get("delta") if isinstance(view.get("delta"), dict) else {}
            return (
                f"vs baseline lum_delta={_float_text(delta.get('mean_luminance_delta'))} "
                f"px_delta={_float_text(delta.get('mean_absolute_pixel_delta'))}"
            )
    return ""


def _view_payload(lane: dict[str, Any], view_id: str) -> dict[str, Any]:
    for item in lane.get("views") or []:
        if isinstance(item, dict) and str(item.get("view_id")) == view_id:
            return item
    return {}


def _backend_pose_text(view: dict[str, Any]) -> str:
    backend_eye = view.get("backend_eye")
    backend_target = view.get("backend_target")
    if _is_vec3(backend_eye) and _is_vec3(backend_target):
        return f"backend eye={_vec_text(backend_eye)} target={_vec_text(backend_target)}"
    return ""
