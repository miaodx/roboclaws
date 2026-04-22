from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from coverage_game import _parse_args as parse_coverage_args  # noqa: E402
from openclaw_demo import _parse_args as parse_openclaw_args  # noqa: E402
from territory_game import _parse_args as parse_territory_args  # noqa: E402

from roboclaws.core.views import (  # noqa: E402
    VIEW_VARIANTS,
    build_prompt_images,
    compute_world_bbox,
    image_labels_for_variant,
)


def _frame(value: int) -> np.ndarray:
    return np.full((8, 8, 3), value, dtype=np.uint8)


def test_build_prompt_images_baseline_returns_two_images() -> None:
    images = build_prompt_images(
        variant="baseline",
        fpv_frame=_frame(10),
        baseline_overhead_frame=_frame(20),
    )
    assert len(images) == 2
    assert int(images[1][0, 0, 0]) == 20


def test_build_prompt_images_map_v2_returns_structured_map() -> None:
    images = build_prompt_images(
        variant="map-v2",
        fpv_frame=_frame(10),
        baseline_overhead_frame=_frame(20),
        structured_overhead_frame=_frame(30),
    )
    assert len(images) == 2
    assert int(images[1][0, 0, 0]) == 30


def test_build_prompt_images_map_v2_chase_returns_three_images() -> None:
    images = build_prompt_images(
        variant="map-v2+chase",
        fpv_frame=_frame(10),
        baseline_overhead_frame=_frame(20),
        structured_overhead_frame=_frame(30),
        chase_cam_frame=_frame(40),
    )
    assert len(images) == 3
    assert int(images[2][0, 0, 0]) == 40


def test_image_labels_match_variant_sizes() -> None:
    for variant in VIEW_VARIANTS:
        labels = image_labels_for_variant(variant)
        expected = 3 if variant == "map-v2+chase" else 2
        assert len(labels) == expected


def test_compute_world_bbox_spans_all_cells() -> None:
    bbox = compute_world_bbox({(0, 1), (2, -1)}, [(-3, 4)])
    assert bbox == (-3, -1, 2, 4)


@pytest.mark.parametrize(
    ("parser", "name"),
    [
        (parse_openclaw_args, "openclaw_demo"),
        (parse_territory_args, "territory_game"),
        (parse_coverage_args, "coverage_game"),
    ],
)
def test_examples_accept_views_flag(parser, name: str) -> None:
    args = parser(["--views", "map-v2+chase"])
    assert args.views == "map-v2+chase", name
