from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

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
    in_bounds,
    make_navigation_view_context,
    pos_to_world_idx,
    render_navigation_prompt_bundle,
    world_to_viz,
)


def _frame(value: int) -> np.ndarray:
    return np.full((8, 8, 3), value, dtype=np.uint8)


def test_build_prompt_images_returns_three_images() -> None:
    images = build_prompt_images(
        fpv_frame=_frame(10),
        structured_overhead_frame=_frame(30),
        chase_cam_frame=_frame(40),
    )
    assert len(images) == 3
    assert int(images[1][0, 0, 0]) == 30
    assert int(images[2][0, 0, 0]) == 40


def test_image_labels_match_variant_sizes() -> None:
    for variant in VIEW_VARIANTS:
        labels = image_labels_for_variant(variant)
        assert len(labels) == 3


def test_compute_world_bbox_spans_all_cells() -> None:
    bbox = compute_world_bbox({(0, 1), (2, -1)}, [(-3, 4)])
    assert bbox == (-3, -1, 2, 4)


def test_navigation_coordinate_helpers_match_example_math() -> None:
    assert pos_to_world_idx({"x": 0.50, "y": 0.9, "z": 0.75}) == (2, 3)
    assert world_to_viz(5, 3, 0, 0, grid_rows=40, grid_cols=40) == (23, 25)
    assert in_bounds(20, 20, grid_rows=40, grid_cols=40) is True
    assert in_bounds(-1, 0, grid_rows=40, grid_cols=40) is False


class _FakeNavigationEngine:
    def __init__(self) -> None:
        self.agent_count = 1
        self._overhead = _frame(20)
        self._chase = _frame(40)
        self.chase_updates = 0

    def get_all_agent_states(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                agent_id=0,
                frame=_frame(10),
                position={"x": 0.25, "y": 0.9, "z": 0.0},
                rotation={"x": 0.0, "y": 90.0, "z": 0.0},
            )
        ]

    def get_reachable_positions(self) -> set[tuple[int, int]]:
        return {(0, 0), (1, 0), (1, 1)}

    def get_overhead_frame(self) -> np.ndarray:
        return self._overhead

    def get_overhead_camera_properties(self) -> dict[str, object]:
        return {
            "position": {"x": 0.25, "y": 2.5, "z": 0.5},
            "rotation": {"x": 90.0, "y": 0.0, "z": 0.0},
            "orthographicSize": 0.5,
            "orthographic": True,
        }

    def add_chase_cam(self, agent_id: int) -> int:
        return agent_id

    def update_chase_cam(self, agent_id: int) -> None:
        self.chase_updates += 1

    def get_chase_cam_frame(self, agent_id: int) -> np.ndarray:
        return self._chase


def test_render_navigation_prompt_bundle_reuses_shared_surface() -> None:
    engine = _FakeNavigationEngine()
    context = make_navigation_view_context(engine, agent_count=1)
    bundle = render_navigation_prompt_bundle(
        engine=engine,
        context=context,
        agent_states=engine.get_all_agent_states(),
        current_agent=0,
    )

    assert bundle.image_labels == ("fpv", "map_v2", "chase")
    assert len(bundle.prompt_images) == 3
    assert bundle.structured_overhead_frame is not None
    assert bundle.trace_overhead_frame is bundle.structured_overhead_frame
    assert bundle.raw_overhead_frame.shape == engine.get_overhead_frame().shape
    assert bundle.structured_overhead_frame.shape == engine.get_overhead_frame().shape
    assert bundle.chase_cam_frame is not None
    assert context.visited_world == {(1, 0)}
    assert engine.chase_updates == 1


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
