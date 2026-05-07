from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from roboclaws.core.scene_grid import (
    DEFAULT_GRID_SIZE,
    WorldCell,
    world_to_cell,
)
from roboclaws.core.scene_grid import (
    compute_world_bbox as _compute_world_bbox,
)
from roboclaws.core.visualizer import GameVisualizer

ViewVariant = Literal["map-v2+chase"]

_GRID_SIZE: float = DEFAULT_GRID_SIZE
_DEFAULT_GRID_ROWS: int = 40
_DEFAULT_GRID_COLS: int = 40

VIEW_VARIANTS: tuple[ViewVariant, ...] = ("map-v2+chase",)
_IMAGE_LABELS: dict[ViewVariant, tuple[str, ...]] = {
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
    fpv_frame: np.ndarray,
    structured_overhead_frame: np.ndarray,
    chase_cam_frame: np.ndarray,
) -> list[np.ndarray]:
    """Assemble the three prompt images: FPV, structured overhead, chase cam."""
    return [fpv_frame, structured_overhead_frame, chase_cam_frame]


def encode_prompt_images(
    *,
    image_frames: Sequence[np.ndarray],
    encoder: Callable[[np.ndarray], tuple[str, dict[str, Any]]],
) -> tuple[list[str], list[dict[str, Any]], float]:
    """Encode three prompt images while preserving per-image metric labels."""
    labels = _IMAGE_LABELS["map-v2+chase"]
    if len(image_frames) != len(labels):
        raise ValueError(f"map-v2+chase expects {len(labels)} images, got {len(image_frames)}.")
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
    return _compute_world_bbox(*cell_groups)


def pos_to_world_idx(pos: dict[str, float], *, grid_size: float = _GRID_SIZE) -> WorldCell:
    """Convert a continuous AI2-THOR ``(x, z)`` position to a world-grid cell."""
    return world_to_cell(pos, grid_size=grid_size)


def world_to_viz(
    ix: int,
    iz: int,
    origin_ix: int,
    origin_iz: int,
    *,
    grid_rows: int = _DEFAULT_GRID_ROWS,
    grid_cols: int = _DEFAULT_GRID_COLS,
) -> tuple[int, int]:
    """Map a world-grid cell to a centred visualizer ``(row, col)`` cell."""
    return (grid_rows // 2 + (iz - origin_iz), grid_cols // 2 + (ix - origin_ix))


def in_bounds(
    row: int,
    col: int,
    *,
    grid_rows: int = _DEFAULT_GRID_ROWS,
    grid_cols: int = _DEFAULT_GRID_COLS,
) -> bool:
    """Return ``True`` when a visualizer ``(row, col)`` lies inside the grid."""
    return 0 <= row < grid_rows and 0 <= col < grid_cols


@dataclass
class NavigationViewContext:
    """Stable scene-level inputs for navigation prompt rendering."""

    visualizer: GameVisualizer
    reachable_cells: set[WorldCell]
    world_bbox: tuple[int, int, int, int]
    origin_world: WorldCell
    overhead_background: np.ndarray | None = None
    overhead_camera_pose: dict[str, Any] | None = None
    visited_world: set[WorldCell] = field(default_factory=set)
    # Ordered path history per agent used to draw trails on the map.
    path_history: list[list[WorldCell]] = field(default_factory=list)


@dataclass
class NavigationPromptBundle:
    """Rendered prompt images plus trace-friendly metadata for one turn."""

    prompt_images: list[np.ndarray]
    raw_overhead_frame: np.ndarray
    trace_overhead_frame: np.ndarray
    image_labels: tuple[str, ...]
    agent_positions_world: list[WorldCell]
    structured_overhead_frame: np.ndarray | None = None
    chase_cam_frame: np.ndarray | None = None


def _optional_engine_value(engine: Any, getter_name: str) -> Any | None:
    try:
        return getattr(engine, getter_name)()
    except Exception:  # noqa: BLE001 - mock engines may omit the camera
        return None


def make_navigation_view_context(
    engine: Any,
    *,
    agent_count: int | None = None,
    agent_labels: list[str] | None = None,
    grid_rows: int = _DEFAULT_GRID_ROWS,
    grid_cols: int = _DEFAULT_GRID_COLS,
    cell_px: int = 15,
) -> NavigationViewContext:
    """Capture the reusable scene state needed to render navigation prompt views."""
    initial_states = list(engine.get_all_agent_states())
    if not initial_states:
        raise ValueError("navigation view context requires at least one agent state")
    reachable_cells = set(engine.get_reachable_positions())
    origin_world = pos_to_world_idx(initial_states[0].position)
    world_bbox = compute_world_bbox(
        reachable_cells,
        (pos_to_world_idx(state.position) for state in initial_states),
    )
    overhead_background = _optional_engine_value(engine, "get_overhead_frame")
    overhead_camera_pose = _optional_engine_value(engine, "get_overhead_camera_properties")

    effective_agent_count = agent_count if agent_count is not None else len(initial_states)
    visualizer = GameVisualizer(
        grid_rows=grid_rows,
        grid_cols=grid_cols,
        cell_px=cell_px,
        agent_count=effective_agent_count,
        agent_labels=agent_labels,
    )
    return NavigationViewContext(
        visualizer=visualizer,
        reachable_cells=reachable_cells,
        world_bbox=world_bbox,
        origin_world=origin_world,
        overhead_background=overhead_background,
        overhead_camera_pose=overhead_camera_pose,
    )


def mark_visited_world(
    visited_world: set[WorldCell],
    agent_states: Sequence[Any],
    path_history: list[list[WorldCell]] | None = None,
) -> bool:
    """Merge the agents' current cells into ``visited_world`` and report growth.

    If ``path_history`` is provided, each agent's ordered path is extended with
    the current cell (duplicates at the tail are suppressed).
    """
    before = len(visited_world)
    for i, state in enumerate(agent_states):
        cell = pos_to_world_idx(state.position)
        visited_world.add(cell)
        if path_history is not None:
            while len(path_history) <= i:
                path_history.append([])
            if not path_history[i] or path_history[i][-1] != cell:
                path_history[i].append(cell)
    return len(visited_world) > before


def render_navigation_prompt_bundle(
    *,
    engine: Any,
    context: NavigationViewContext,
    agent_states: Sequence[Any],
    current_agent: int,
) -> NavigationPromptBundle:
    """Render the three-view navigation prompt-image bundle for one control turn."""
    mark_visited_world(context.visited_world, agent_states, context.path_history)
    agent_positions_world = [pos_to_world_idx(state.position) for state in agent_states]
    covered_cells = list(context.visited_world)
    agent_rotations = [state.rotation for state in agent_states]
    path_history = context.path_history or None

    raw_map = context.visualizer.render_world_overhead_map(
        agent_positions=agent_positions_world,
        covered_cells=covered_cells,
        world_bbox=context.world_bbox,
        base_frame=context.overhead_background,
        camera_pose=context.overhead_camera_pose,
        grid_size=_GRID_SIZE,
    )
    raw_overhead_frame = np.asarray(raw_map.convert("RGB"), dtype=np.uint8)

    if context.overhead_camera_pose is not None and context.overhead_background is not None:
        structured_map = context.visualizer.render_projected_structured_map(
            agent_positions=agent_positions_world,
            agent_rotations=agent_rotations,
            reachable_cells=context.reachable_cells,
            covered_cells=covered_cells,
            world_bbox=context.world_bbox,
            camera_pose=context.overhead_camera_pose,
            image_size=(
                int(context.overhead_background.shape[1]),
                int(context.overhead_background.shape[0]),
            ),
            grid_size=_GRID_SIZE,
            path_history=path_history,
        )
    else:
        structured_map = context.visualizer.render_structured_map(
            agent_positions=agent_positions_world,
            agent_rotations=agent_rotations,
            reachable_cells=context.reachable_cells,
            covered_cells=covered_cells,
            world_bbox=context.world_bbox,
            path_history=path_history,
        )
    structured_overhead_frame = np.asarray(structured_map.convert("RGB"), dtype=np.uint8)

    engine.add_chase_cam(current_agent)
    engine.update_chase_cam(current_agent)
    chase_cam_frame = engine.get_chase_cam_frame(current_agent)

    prompt_images = build_prompt_images(
        fpv_frame=agent_states[current_agent].frame,
        structured_overhead_frame=structured_overhead_frame,
        chase_cam_frame=chase_cam_frame,
    )
    return NavigationPromptBundle(
        prompt_images=prompt_images,
        raw_overhead_frame=raw_overhead_frame,
        trace_overhead_frame=structured_overhead_frame,
        structured_overhead_frame=structured_overhead_frame,
        chase_cam_frame=chase_cam_frame,
        image_labels=_IMAGE_LABELS["map-v2+chase"],
        agent_positions_world=agent_positions_world,
    )


def render_game_prompt_bundle(
    *,
    engine: Any,
    visualizer: GameVisualizer,
    agent_states: Sequence[Any],
    current_agent: int,
    reachable_cells: set[WorldCell],
    world_bbox: tuple[int, int, int, int],
    overhead_background: np.ndarray | None = None,
    overhead_camera_pose: dict[str, Any] | None = None,
    claimed_cells: dict[int, Iterable[WorldCell]] | None = None,
    covered_cells: Iterable[WorldCell] | None = None,
    grid_size: float = _GRID_SIZE,
) -> NavigationPromptBundle:
    """Render the shared three-image game prompt bundle.

    Territory and coverage differ in whether the structured map receives
    claimed cells or covered cells, but both use the same normal navigation
    image contract: FPV, map-v2, chase.
    """
    agent_positions_world = [
        pos_to_world_idx(state.position, grid_size=grid_size) for state in agent_states
    ]
    agent_rotations = [state.rotation for state in agent_states]
    covered_cells_list = list(covered_cells or [])

    raw_map = visualizer.render_world_overhead_map(
        agent_positions=agent_positions_world,
        covered_cells=covered_cells_list,
        world_bbox=world_bbox,
        base_frame=overhead_background,
        camera_pose=overhead_camera_pose,
        grid_size=grid_size,
    )
    raw_overhead_frame = np.asarray(raw_map.convert("RGB"), dtype=np.uint8)

    if overhead_camera_pose is not None and overhead_background is not None:
        structured_map = visualizer.render_projected_structured_map(
            agent_positions=agent_positions_world,
            agent_rotations=agent_rotations,
            reachable_cells=reachable_cells,
            claimed_cells=claimed_cells,
            covered_cells=covered_cells_list,
            world_bbox=world_bbox,
            camera_pose=overhead_camera_pose,
            image_size=(
                int(overhead_background.shape[1]),
                int(overhead_background.shape[0]),
            ),
            grid_size=grid_size,
        )
    else:
        structured_map = visualizer.render_structured_map(
            agent_positions=agent_positions_world,
            agent_rotations=agent_rotations,
            reachable_cells=reachable_cells,
            claimed_cells=claimed_cells,
            covered_cells=covered_cells_list,
            world_bbox=world_bbox,
        )
    structured_overhead_frame = np.asarray(structured_map.convert("RGB"), dtype=np.uint8)

    engine.add_chase_cam(current_agent)
    engine.update_chase_cam(current_agent)
    chase_cam_frame = engine.get_chase_cam_frame(current_agent)

    return NavigationPromptBundle(
        prompt_images=build_prompt_images(
            fpv_frame=agent_states[current_agent].frame,
            structured_overhead_frame=structured_overhead_frame,
            chase_cam_frame=chase_cam_frame,
        ),
        raw_overhead_frame=raw_overhead_frame,
        trace_overhead_frame=structured_overhead_frame,
        structured_overhead_frame=structured_overhead_frame,
        chase_cam_frame=chase_cam_frame,
        image_labels=_IMAGE_LABELS["map-v2+chase"],
        agent_positions_world=agent_positions_world,
    )
