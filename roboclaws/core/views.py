from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any, Literal

import numpy as np

ViewVariant = Literal["baseline", "map-v2", "map-v2+chase"]

VIEW_VARIANTS: tuple[ViewVariant, ...] = ("baseline", "map-v2", "map-v2+chase")
_IMAGE_LABELS: dict[ViewVariant, tuple[str, ...]] = {
    "baseline": ("fpv", "overhead"),
    "map-v2": ("fpv", "map_v2"),
    "map-v2+chase": ("fpv", "map_v2", "chase"),
}


def validate_view_variant(variant: str) -> ViewVariant:
    """Return a validated view variant or raise ValueError."""
    if variant not in VIEW_VARIANTS:
        raise ValueError(f"Unknown view variant: {variant!r}. Choose from {VIEW_VARIANTS}.")
    return variant


def image_labels_for_variant(variant: str) -> tuple[str, ...]:
    """Return stable metric labels for the chosen image variant."""
    return _IMAGE_LABELS[validate_view_variant(variant)]


def build_prompt_images(
    *,
    variant: str,
    fpv_frame: np.ndarray,
    baseline_overhead_frame: np.ndarray,
    structured_overhead_frame: np.ndarray | None = None,
    chase_cam_frame: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Assemble prompt images for the requested variant."""
    validated = validate_view_variant(variant)
    if validated == "baseline":
        return [fpv_frame, baseline_overhead_frame]

    if structured_overhead_frame is None:
        raise ValueError(f"{validated} requires structured_overhead_frame")

    images = [fpv_frame, structured_overhead_frame]
    if validated == "map-v2+chase":
        if chase_cam_frame is None:
            raise ValueError("map-v2+chase requires chase_cam_frame")
        images.append(chase_cam_frame)
    return images


def encode_prompt_images(
    *,
    variant: str,
    image_frames: Sequence[np.ndarray],
    encoder: Callable[[np.ndarray], tuple[str, dict[str, Any]]],
) -> tuple[list[str], list[dict[str, Any]], float]:
    """Encode N prompt images while preserving per-image metric labels."""
    labels = image_labels_for_variant(variant)
    if len(image_frames) != len(labels):
        raise ValueError(f"{variant} expects {len(labels)} images, got {len(image_frames)}.")
    encoded: list[str] = []
    metrics: list[dict[str, Any]] = []
    total_encode_seconds = 0.0
    for label, frame in zip(labels, image_frames):
        encoded_frame, frame_metrics = encoder(frame)
        encoded.append(encoded_frame)
        metrics.append({"label": label, **frame_metrics})
        total_encode_seconds += float(frame_metrics.get("encode_seconds", 0.0))
    return encoded, metrics, total_encode_seconds


def compute_world_bbox(*cell_groups: Iterable[tuple[int, int]]) -> tuple[int, int, int, int]:
    """Return ``(min_ix, min_iz, max_ix, max_iz)`` across one or more cell sets."""
    cells = [cell for group in cell_groups for cell in group]
    if not cells:
        return (0, 0, 0, 0)
    xs = [cell[0] for cell in cells]
    zs = [cell[1] for cell in cells]
    return (min(xs), min(zs), max(xs), max(zs))
