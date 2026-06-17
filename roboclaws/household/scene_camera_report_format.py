from __future__ import annotations

import html
import json
from typing import Any

from roboclaws.household import scene_camera_render_domain

MOLMOSPACES_LANE_ID = scene_camera_render_domain.MOLMOSPACES_LANE_ID
ISAAC_LANE_ID = scene_camera_render_domain.ISAAC_LANE_ID


def _lane_order(manifest: dict[str, Any]) -> list[str]:
    lanes = manifest.get("lanes") if isinstance(manifest.get("lanes"), dict) else {}
    registry = (
        manifest.get("lane_registry") if isinstance(manifest.get("lane_registry"), dict) else {}
    )
    ordered: list[str] = []
    baseline = registry.get("baseline")
    if isinstance(baseline, str):
        ordered.append(baseline)
    candidates = registry.get("candidates") if isinstance(registry.get("candidates"), list) else []
    for lane_id in candidates:
        if isinstance(lane_id, str) and lane_id not in ordered:
            ordered.append(lane_id)
    for fallback in (MOLMOSPACES_LANE_ID, ISAAC_LANE_ID):
        if fallback in lanes and fallback not in ordered:
            ordered.append(fallback)
    for lane_id in lanes:
        if isinstance(lane_id, str) and lane_id not in ordered:
            ordered.append(lane_id)
    return ordered


def _is_room_view(manifest: dict[str, Any], view_id: str) -> bool:
    if view_id.startswith("room_"):
        return True
    for item in manifest.get("canonical_camera_views") or []:
        if (
            isinstance(item, dict)
            and str(item.get("view_id") or "") == view_id
            and str(item.get("anchor_kind") or "") == "room"
        ):
            return True
    return False


def _safe_id(value: Any) -> str:
    text = str(value or "scene").lower()
    safe = "".join(ch if ch.isalnum() else "_" for ch in text).strip("_")
    return safe or "scene"


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_vec3(value: Any) -> bool:
    return isinstance(value, list) and len(value) >= 3


def _image_button(src: str, alt: str, *, css_class: str = "") -> str:
    escaped_src = html.escape(src, quote=True)
    escaped_alt = html.escape(alt)
    class_attr = f' class="{html.escape(css_class, quote=True)}"' if css_class else ""
    return (
        '<button type="button" class="image-open-button" '
        f'data-image-src="{escaped_src}" data-image-title="{escaped_alt}" '
        f'aria-label="Open image: {escaped_alt}">'
        f'<img{class_attr} src="{escaped_src}" alt="{escaped_alt}">'
        "</button>"
    )


def _image_modal_html() -> str:
    return """
<dialog class="image-modal" id="image-modal" aria-label="Image preview">
  <div class="image-modal-header">
    <div class="image-modal-title" id="image-modal-title"></div>
    <button type="button" class="image-modal-close" id="image-modal-close">Close</button>
  </div>
  <img id="image-modal-img" src="" alt="">
</dialog>
<script>
(() => {
  const modal = document.getElementById("image-modal");
  const modalImage = document.getElementById("image-modal-img");
  const modalTitle = document.getElementById("image-modal-title");
  const closeButton = document.getElementById("image-modal-close");
  if (!modal || !modalImage || !modalTitle || !closeButton) return;
  document.querySelectorAll("[data-image-src]").forEach((button) => {
    button.addEventListener("click", () => {
      const src = button.getAttribute("data-image-src") || "";
      const title = button.getAttribute("data-image-title") || src;
      modalImage.src = src;
      modalImage.alt = title;
      modalTitle.textContent = title;
      if (typeof modal.showModal === "function") {
        modal.showModal();
      }
    });
  });
  closeButton.addEventListener("click", () => modal.close());
  modal.addEventListener("click", (event) => {
    if (event.target === modal) modal.close();
  });
})();
</script>
"""


def _missing_figure(message: str, lane_id: str) -> str:
    return (
        f'<figure><div class="missing">{html.escape(message)}</div>'
        f"<figcaption><strong>{html.escape(lane_id)}</strong></figcaption></figure>"
    )


def _dimension_text(dimensions: dict[str, Any]) -> str:
    width = dimensions.get("width")
    height = dimensions.get("height")
    channels = dimensions.get("channels")
    if not width or not height:
        return "dimensions unavailable"
    suffix = f", {channels} channels" if channels else ""
    return f"{width} x {height}{suffix}"


def _vec_text(value: Any) -> str:
    if not isinstance(value, list) or len(value) < 2:
        return ""
    return "[" + ", ".join(f"{float(item):.3f}" for item in value[:3]) + "]"


def _meters_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.3f} m"
    except (TypeError, ValueError):
        return str(value)


def _ratio_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _float_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _rgb_text(value: Any) -> str:
    if not isinstance(value, list) or len(value) < 3:
        return ""
    try:
        return "[" + ", ".join(f"{float(item):.1f}" for item in value[:3]) + "]"
    except (TypeError, ValueError):
        return str(value)


def _percent_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value) * 100.0:.2f}%"
    except (TypeError, ValueError):
        return str(value)


def _pixels_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.3f} px"
    except (TypeError, ValueError):
        return str(value)


def _short_list_text(value: Any, *, limit: int = 4) -> str:
    if not isinstance(value, list):
        return ""
    items = [str(item) for item in value if item is not None and str(item) != ""]
    if len(items) <= limit:
        return ", ".join(items)
    return f"{', '.join(items[:limit])}, ... (+{len(items) - limit})"


def _cell_text(value: Any) -> str:
    if isinstance(value, list):
        return _short_list_text(value, limit=6)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return "" if value is None else str(value)


def _badges(items: list[tuple[str, Any]]) -> str:
    parts = []
    for label, value in items:
        if value is None or value == "":
            continue
        parts.append(
            f'<span class="badge">{html.escape(str(label))}: '
            f"<strong>{html.escape(str(value))}</strong></span>"
        )
    return "".join(parts)


def _short_commit(value: Any) -> str:
    text = str(value or "")
    return text[:12] if text else ""
