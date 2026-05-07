from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

WorldCell = tuple[int, int]
DEFAULT_GRID_SIZE = 0.25


@dataclass(frozen=True)
class SceneGrid:
    """Shared AI2-THOR world/grid geometry contract."""

    grid_size: float = DEFAULT_GRID_SIZE

    def world_to_cell(self, position: dict[str, float]) -> WorldCell:
        return (
            round(float(position["x"]) / self.grid_size),
            round(float(position["z"]) / self.grid_size),
        )

    def cell_to_world(self, cell: WorldCell) -> dict[str, float]:
        return {"x": cell[0] * self.grid_size, "z": cell[1] * self.grid_size}

    def normalize_reachable_positions(
        self, positions: Iterable[dict[str, float]]
    ) -> set[WorldCell]:
        return {self.world_to_cell(position) for position in positions}

    def agent_footprint(self, position: dict[str, float]) -> set[WorldCell]:
        return {self.world_to_cell(position)}

    def object_footprint(self, obj: dict[str, Any]) -> set[WorldCell]:
        corners = _corner_points(obj)
        if corners:
            cells = {
                self.world_to_cell({"x": float(point[0]), "z": float(point[2])})
                for point in corners
                if len(point) >= 3
            }
            return _fill_cell_bbox(cells)

        position = obj.get("position")
        if isinstance(position, dict) and "x" in position and "z" in position:
            return {self.world_to_cell(position)}
        return set()


def default_scene_grid() -> SceneGrid:
    return SceneGrid()


def world_to_cell(position: dict[str, float], *, grid_size: float = DEFAULT_GRID_SIZE) -> WorldCell:
    return SceneGrid(grid_size=grid_size).world_to_cell(position)


def compute_world_bbox(*cell_groups: Iterable[WorldCell]) -> tuple[int, int, int, int]:
    cells = [cell for group in cell_groups for cell in group]
    if not cells:
        return (0, 0, 0, 0)
    xs = [cell[0] for cell in cells]
    zs = [cell[1] for cell in cells]
    return (min(xs), min(zs), max(xs), max(zs))


def _corner_points(obj: dict[str, Any]) -> list[list[float]]:
    for key in ("axisAlignedBoundingBox", "objectOrientedBoundingBox"):
        box = obj.get(key)
        if isinstance(box, dict) and isinstance(box.get("cornerPoints"), list):
            return box["cornerPoints"]
    return []


def _fill_cell_bbox(cells: set[WorldCell]) -> set[WorldCell]:
    if not cells:
        return set()
    min_x, min_z, max_x, max_z = compute_world_bbox(cells)
    return {(x, z) for x in range(min_x, max_x + 1) for z in range(min_z, max_z + 1)}
