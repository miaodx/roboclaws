from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import imageio  # type: ignore[import-untyped]

    _HAS_IMAGEIO = True
except ImportError:
    _HAS_IMAGEIO = False

_AGENT_COLOURS: list[tuple[int, int, int]] = [
    (220, 50, 50),  # red
    (50, 120, 220),  # blue
    (50, 180, 50),  # green
    (220, 150, 50),  # orange
    (150, 50, 220),  # purple
    (50, 200, 200),  # cyan
    (220, 220, 50),  # yellow
    (200, 100, 160),  # pink
]

_BACKGROUND_COLOUR: tuple[int, int, int] = (255, 255, 255)
_GRID_LINE_COLOUR: tuple[int, int, int] = (200, 200, 200)
_COVERED_COLOUR: tuple[int, int, int] = (200, 240, 200)  # light green (coverage game)
_STRUCTURED_REACHABLE_COLOUR: tuple[int, int, int] = (230, 230, 230)
_STRUCTURED_UNREACHABLE_COLOUR: tuple[int, int, int] = (60, 60, 60)
_STRUCTURED_COVERED_COLOUR: tuple[int, int, int] = (180, 230, 180)
_STRUCTURED_MARGIN_PX: int = 2

_SOUL_COLOURS: dict[str, tuple[int, int, int]] = {
    "aggressive": (220, 50, 50),  # red
    "defensive": (50, 120, 220),  # blue
    "cooperative": (50, 180, 50),  # green
    "default": (130, 130, 130),  # grey
}

_CELL_TINT_ALPHA: int = 140

_RESAMPLE = Image.Resampling.BILINEAR


class GameVisualizer:
    """Generate overhead maps, composites, and GIF-ready frames."""

    def __init__(
        self,
        grid_rows: int = 20,
        grid_cols: int = 20,
        cell_px: int = 20,
        agent_count: int = 2,
        agent_labels: list[str] | None = None,
    ) -> None:
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.cell_px = cell_px
        self.agent_count = agent_count
        self.agent_labels: list[str] = agent_labels or []
        self._map_w = grid_cols * cell_px
        self._map_h = grid_rows * cell_px

    def render_overhead_map(
        self,
        *,
        agent_positions: list[tuple[int, int]],
        claimed_cells: dict[int, list[tuple[int, int]]] | None = None,
        covered_cells: list[tuple[int, int]] | None = None,
        base_frame: np.ndarray | None = None,
    ) -> Image.Image:
        """Render a 2-D overhead grid map."""
        if base_frame is not None:
            bg = (
                Image.fromarray(base_frame)
                .convert("RGB")
                .resize((self._map_w, self._map_h), _RESAMPLE)
            )
        else:
            bg = Image.new("RGB", (self._map_w, self._map_h), _BACKGROUND_COLOUR)

        overlay = Image.new("RGBA", (self._map_w, self._map_h), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        if covered_cells:
            tint = (*_COVERED_COLOUR, _CELL_TINT_ALPHA)
            for row, col in covered_cells:
                self._fill_cell(odraw, row, col, tint)

        if claimed_cells:
            for agent_id, cells in claimed_cells.items():
                base_colour = self._agent_colour(agent_id)
                tint = (*_lighten(base_colour, 60), _CELL_TINT_ALPHA)
                for row, col in cells:
                    self._fill_cell(odraw, row, col, tint)

        bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(bg)
        self._draw_grid(draw)

        for idx, (row, col) in enumerate(agent_positions):
            colour = self._agent_colour(idx)
            soul_label = self.agent_labels[idx] if idx < len(self.agent_labels) else ""
            badge = soul_label[0].upper() if soul_label else str(idx)
            self._draw_agent_marker(draw, row, col, colour, label=badge)

        return bg

    def render_world_overhead_map(
        self,
        *,
        agent_positions: list[tuple[int, int]],
        claimed_cells: dict[int, list[tuple[int, int]]] | None = None,
        covered_cells: list[tuple[int, int]] | None = None,
        world_bbox: tuple[int, int, int, int],
        base_frame: np.ndarray | None = None,
        camera_pose: dict[str, object] | None = None,
        grid_size: float = 0.25,
    ) -> Image.Image:
        """Render the photographic overhead view on the same world grid as map-v2."""
        min_ix, min_iz, max_ix, max_iz = world_bbox
        cols = max_ix - min_ix + 1
        rows = max_iz - min_iz + 1
        projected = (
            base_frame is not None
            and camera_pose is not None
            and _supports_projected_overhead(camera_pose)
        )
        if projected:
            bg = Image.fromarray(base_frame).convert("RGB")
        else:
            bg = self._make_world_background(
                cols=cols,
                rows=rows,
                base_frame=base_frame,
                background_colour=_BACKGROUND_COLOUR,
            )

        overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        if covered_cells:
            tint = (*_COVERED_COLOUR, _CELL_TINT_ALPHA)
            for ix, iz in covered_cells:
                if projected:
                    self._fill_projected_world_cell(
                        odraw,
                        ix=ix,
                        iz=iz,
                        camera_pose=camera_pose,
                        image_size=bg.size,
                        grid_size=grid_size,
                        colour=tint,
                    )
                else:
                    self._fill_world_cell(odraw, ix, iz, min_ix, min_iz, tint)

        if claimed_cells:
            for agent_id, cells in claimed_cells.items():
                base_colour = self._agent_colour(agent_id)
                tint = (*_lighten(base_colour, 60), _CELL_TINT_ALPHA)
                for ix, iz in cells:
                    if projected:
                        self._fill_projected_world_cell(
                            odraw,
                            ix=ix,
                            iz=iz,
                            camera_pose=camera_pose,
                            image_size=bg.size,
                            grid_size=grid_size,
                            colour=tint,
                        )
                    else:
                        self._fill_world_cell(odraw, ix, iz, min_ix, min_iz, tint)

        bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(bg)
        if projected:
            self._draw_projected_world_grid(
                draw,
                world_bbox=world_bbox,
                camera_pose=camera_pose,
                image_size=bg.size,
                grid_size=grid_size,
            )
        else:
            self._draw_structured_grid(draw, cols=cols, rows=rows)

        for idx, (ix, iz) in enumerate(agent_positions):
            colour = self._agent_colour(idx)
            soul_label = self.agent_labels[idx] if idx < len(self.agent_labels) else ""
            badge = soul_label[0].upper() if soul_label else str(idx)
            if projected:
                self._draw_projected_world_agent_marker(
                    draw,
                    ix=ix,
                    iz=iz,
                    camera_pose=camera_pose,
                    image_size=bg.size,
                    grid_size=grid_size,
                    colour=colour,
                    label=badge,
                )
            else:
                self._draw_world_agent_marker(
                    draw,
                    ix=ix,
                    iz=iz,
                    min_ix=min_ix,
                    min_iz=min_iz,
                    colour=colour,
                    label=badge,
                )

        return bg

    def render_structured_map(
        self,
        *,
        agent_positions: list[tuple[int, int]],
        agent_rotations: list[dict[str, float]],
        reachable_cells: set[tuple[int, int]],
        claimed_cells: dict[int, list[tuple[int, int]]] | None = None,
        covered_cells: list[tuple[int, int]] | None = None,
        world_bbox: tuple[int, int, int, int],
        path_history: list[list[tuple[int, int]]] | None = None,
    ) -> Image.Image:
        """Render a pure grid map from world-grid coordinates."""
        min_ix, min_iz, max_ix, max_iz = world_bbox
        cols = max_ix - min_ix + 1
        rows = max_iz - min_iz + 1
        width, height = self._world_canvas_size(cols=cols, rows=rows)
        img = Image.new("RGB", (width, height), _STRUCTURED_UNREACHABLE_COLOUR)
        draw = ImageDraw.Draw(img)

        claimed_lookup = self._build_claimed_lookup(claimed_cells)
        covered_lookup = set(covered_cells or [])

        for iz in range(min_iz, max_iz + 1):
            for ix in range(min_ix, max_ix + 1):
                cell = (ix, iz)
                colour = self._structured_cell_colour(
                    cell=cell,
                    reachable_cells=reachable_cells,
                    covered_lookup=covered_lookup,
                    claimed_lookup=claimed_lookup,
                )
                self._fill_world_cell(draw, ix, iz, min_ix, min_iz, colour)

        self._draw_structured_grid(draw, cols=cols, rows=rows)

        if path_history:
            for agent_idx, path in enumerate(path_history):
                if len(path) >= 2:
                    self._draw_path_trail_world(
                        draw,
                        path=path,
                        min_ix=min_ix,
                        min_iz=min_iz,
                        colour=self._agent_colour(agent_idx),
                    )

        for idx, (ix, iz) in enumerate(agent_positions):
            rotation = agent_rotations[idx] if idx < len(agent_rotations) else {"y": 0.0}
            self._draw_heading_marker(
                draw,
                ix=ix,
                iz=iz,
                min_ix=min_ix,
                min_iz=min_iz,
                yaw_deg=float(rotation.get("y", 0.0)),
                colour=self._agent_colour(idx),
                label=str(idx),
            )

        return img

    def render_projected_structured_map(
        self,
        *,
        agent_positions: list[tuple[int, int]],
        agent_rotations: list[dict[str, float]],
        reachable_cells: set[tuple[int, int]],
        claimed_cells: dict[int, list[tuple[int, int]]] | None = None,
        covered_cells: list[tuple[int, int]] | None = None,
        world_bbox: tuple[int, int, int, int],
        camera_pose: dict[str, object],
        image_size: tuple[int, int],
        grid_size: float = 0.25,
        path_history: list[list[tuple[int, int]]] | None = None,
    ) -> Image.Image:
        """Render map-v2 into the projected overhead camera frame."""
        img = Image.new("RGB", image_size, _BACKGROUND_COLOUR)
        draw = ImageDraw.Draw(img)

        claimed_lookup = self._build_claimed_lookup(claimed_cells)
        covered_lookup = set(covered_cells or [])

        min_ix, min_iz, max_ix, max_iz = world_bbox
        for iz in range(min_iz, max_iz + 1):
            for ix in range(min_ix, max_ix + 1):
                cell = (ix, iz)
                colour = self._structured_cell_colour(
                    cell=cell,
                    reachable_cells=reachable_cells,
                    covered_lookup=covered_lookup,
                    claimed_lookup=claimed_lookup,
                )
                self._fill_projected_world_cell(
                    draw,
                    ix=ix,
                    iz=iz,
                    camera_pose=camera_pose,
                    image_size=image_size,
                    grid_size=grid_size,
                    colour=colour,
                )

        self._draw_projected_world_grid(
            draw,
            world_bbox=world_bbox,
            camera_pose=camera_pose,
            image_size=image_size,
            grid_size=grid_size,
        )

        if path_history:
            for agent_idx, path in enumerate(path_history):
                if len(path) >= 2:
                    self._draw_projected_path_trail(
                        draw,
                        path=path,
                        camera_pose=camera_pose,
                        image_size=image_size,
                        grid_size=grid_size,
                        colour=self._agent_colour(agent_idx),
                    )

        for idx, (ix, iz) in enumerate(agent_positions):
            rotation = agent_rotations[idx] if idx < len(agent_rotations) else {"y": 0.0}
            self._draw_projected_heading_marker(
                draw,
                ix=ix,
                iz=iz,
                yaw_deg=float(rotation.get("y", 0.0)),
                camera_pose=camera_pose,
                image_size=image_size,
                grid_size=grid_size,
                colour=self._agent_colour(idx),
                label=str(idx),
            )

        return img

    def _agent_colour(self, agent_id: int) -> tuple[int, int, int]:
        """Return the configured SOUL colour or the default palette colour."""
        if agent_id < len(self.agent_labels):
            soul = self.agent_labels[agent_id]
            return _SOUL_COLOURS.get(soul, _SOUL_COLOURS["default"])
        return _AGENT_COLOURS[agent_id % len(_AGENT_COLOURS)]

    def _build_claimed_lookup(
        self,
        claimed_cells: dict[int, list[tuple[int, int]]] | None,
    ) -> dict[tuple[int, int], int]:
        return {
            cell: agent_id for agent_id, cells in (claimed_cells or {}).items() for cell in cells
        }

    def _structured_cell_colour(
        self,
        *,
        cell: tuple[int, int],
        reachable_cells: set[tuple[int, int]],
        covered_lookup: set[tuple[int, int]],
        claimed_lookup: dict[tuple[int, int], int],
    ) -> tuple[int, int, int]:
        if cell in claimed_lookup:
            return self._agent_colour(claimed_lookup[cell])
        if cell in covered_lookup:
            return _STRUCTURED_COVERED_COLOUR
        if cell in reachable_cells:
            return _STRUCTURED_REACHABLE_COLOUR
        return _STRUCTURED_UNREACHABLE_COLOUR

    def _fill_cell(
        self,
        draw: ImageDraw.ImageDraw,
        row: int,
        col: int,
        colour: tuple[int, ...],
    ) -> None:
        x0 = col * self.cell_px
        y0 = row * self.cell_px
        draw.rectangle([x0, y0, x0 + self.cell_px - 1, y0 + self.cell_px - 1], fill=colour)

    def _fill_world_cell(
        self,
        draw: ImageDraw.ImageDraw,
        ix: int,
        iz: int,
        min_ix: int,
        min_iz: int,
        colour: tuple[int, ...],
    ) -> None:
        x0 = _STRUCTURED_MARGIN_PX + (ix - min_ix) * self.cell_px
        y0 = _STRUCTURED_MARGIN_PX + (iz - min_iz) * self.cell_px
        draw.rectangle([x0, y0, x0 + self.cell_px - 1, y0 + self.cell_px - 1], fill=colour)

    def _world_canvas_size(self, *, cols: int, rows: int) -> tuple[int, int]:
        return (
            cols * self.cell_px + _STRUCTURED_MARGIN_PX * 2,
            rows * self.cell_px + _STRUCTURED_MARGIN_PX * 2,
        )

    def _make_world_background(
        self,
        *,
        cols: int,
        rows: int,
        base_frame: np.ndarray | None,
        background_colour: tuple[int, int, int],
    ) -> Image.Image:
        width, height = self._world_canvas_size(cols=cols, rows=rows)
        if base_frame is None:
            return Image.new("RGB", (width, height), background_colour)
        bg = Image.fromarray(base_frame).convert("RGB")
        bg = _trim_uniform_border(bg)
        return bg.resize((width, height), _RESAMPLE)

    def _fill_projected_world_cell(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        ix: int,
        iz: int,
        camera_pose: dict[str, object],
        image_size: tuple[int, int],
        grid_size: float,
        colour: tuple[int, ...],
    ) -> None:
        points = [
            self._project_overhead_world_point(
                x=(ix + dx) * grid_size,
                z=(iz + dz) * grid_size,
                camera_pose=camera_pose,
                image_size=image_size,
            )
            for dx, dz in [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]
        ]
        draw.polygon(points, fill=colour)

    def _draw_grid(self, draw: ImageDraw.ImageDraw) -> None:
        _draw_grid_lines(
            draw,
            cols=self.grid_cols,
            rows=self.grid_rows,
            cell_px=self.cell_px,
            x0=0,
            y0=0,
        )

    def _draw_structured_grid(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        cols: int,
        rows: int,
    ) -> None:
        _draw_grid_lines(
            draw,
            cols=cols,
            rows=rows,
            cell_px=self.cell_px,
            x0=_STRUCTURED_MARGIN_PX,
            y0=_STRUCTURED_MARGIN_PX,
        )

    def _draw_agent_marker(
        self,
        draw: ImageDraw.ImageDraw,
        row: int,
        col: int,
        colour: tuple[int, int, int],
        label: str,
    ) -> None:
        cx = col * self.cell_px + self.cell_px // 2
        cy = row * self.cell_px + self.cell_px // 2
        r = max(self.cell_px // 2 - 2, 4)
        _draw_labeled_circle(draw, center=(cx, cy), radius=r, colour=colour, label=label)

    def _draw_heading_marker(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        ix: int,
        iz: int,
        min_ix: int,
        min_iz: int,
        yaw_deg: float,
        colour: tuple[int, int, int],
        label: str,
    ) -> None:
        cx, cy = self._world_marker_center(ix=ix, iz=iz, min_ix=min_ix, min_iz=min_iz)
        length = max(self.cell_px * 0.7, 6.0)
        half_width = max(self.cell_px * 0.33, 4.0)

        # AI2-THOR yaw=0 faces +z. On the rendered grid, +z points downward.
        yaw_rad = np.deg2rad(yaw_deg)
        dx = float(np.sin(yaw_rad))
        dy = float(np.cos(yaw_rad))
        px = -dy
        py = dx

        tip = (cx + dx * length, cy + dy * length)
        base_center = (cx - dx * length * 0.45, cy - dy * length * 0.45)
        left = (base_center[0] + px * half_width, base_center[1] + py * half_width)
        right = (base_center[0] - px * half_width, base_center[1] - py * half_width)

        _draw_labeled_triangle(
            draw,
            points=[tip, left, right],
            label_center=(cx, cy),
            colour=colour,
            label=label,
        )

    def _draw_world_agent_marker(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        ix: int,
        iz: int,
        min_ix: int,
        min_iz: int,
        colour: tuple[int, int, int],
        label: str,
    ) -> None:
        cx, cy = self._world_marker_center(ix=ix, iz=iz, min_ix=min_ix, min_iz=min_iz)
        r = max(self.cell_px // 2 - 2, 4)
        _draw_labeled_circle(draw, center=(cx, cy), radius=r, colour=colour, label=label)

    def _draw_projected_world_agent_marker(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        ix: int,
        iz: int,
        camera_pose: dict[str, object],
        image_size: tuple[int, int],
        grid_size: float,
        colour: tuple[int, int, int],
        label: str,
    ) -> None:
        cx, cy = self._project_overhead_world_point(
            x=ix * grid_size,
            z=iz * grid_size,
            camera_pose=camera_pose,
            image_size=image_size,
        )
        edge_a = self._project_overhead_world_point(
            x=(ix - 0.5) * grid_size,
            z=iz * grid_size,
            camera_pose=camera_pose,
            image_size=image_size,
        )
        edge_b = self._project_overhead_world_point(
            x=(ix + 0.5) * grid_size,
            z=iz * grid_size,
            camera_pose=camera_pose,
            image_size=image_size,
        )
        cell_diameter = max(abs(edge_b[0] - edge_a[0]), abs(edge_b[1] - edge_a[1]), 8.0)
        r = max(int(cell_diameter * 0.4), 4)
        _draw_labeled_circle(draw, center=(cx, cy), radius=r, colour=colour, label=label)

    def _draw_projected_heading_marker(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        ix: int,
        iz: int,
        yaw_deg: float,
        camera_pose: dict[str, object],
        image_size: tuple[int, int],
        grid_size: float,
        colour: tuple[int, int, int],
        label: str,
    ) -> None:
        yaw_rad = np.deg2rad(yaw_deg)
        forward_x = float(np.sin(yaw_rad))
        forward_z = float(np.cos(yaw_rad))
        perp_x = -forward_z
        perp_z = forward_x

        center_x = ix * grid_size
        center_z = iz * grid_size
        tip_world = (
            center_x + forward_x * grid_size * 0.45,
            center_z + forward_z * grid_size * 0.45,
        )
        base_center_world = (
            center_x - forward_x * grid_size * 0.22,
            center_z - forward_z * grid_size * 0.22,
        )
        left_world = (
            base_center_world[0] + perp_x * grid_size * 0.28,
            base_center_world[1] + perp_z * grid_size * 0.28,
        )
        right_world = (
            base_center_world[0] - perp_x * grid_size * 0.28,
            base_center_world[1] - perp_z * grid_size * 0.28,
        )
        center = self._project_overhead_world_point(
            x=center_x,
            z=center_z,
            camera_pose=camera_pose,
            image_size=image_size,
        )
        tip = self._project_overhead_world_point(
            x=tip_world[0],
            z=tip_world[1],
            camera_pose=camera_pose,
            image_size=image_size,
        )
        left = self._project_overhead_world_point(
            x=left_world[0],
            z=left_world[1],
            camera_pose=camera_pose,
            image_size=image_size,
        )
        right = self._project_overhead_world_point(
            x=right_world[0],
            z=right_world[1],
            camera_pose=camera_pose,
            image_size=image_size,
        )
        _draw_labeled_triangle(
            draw,
            points=[tip, left, right],
            label_center=center,
            colour=colour,
            label=label,
        )

    def _draw_projected_world_grid(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        world_bbox: tuple[int, int, int, int],
        camera_pose: dict[str, object],
        image_size: tuple[int, int],
        grid_size: float,
    ) -> None:
        min_ix, min_iz, max_ix, max_iz = world_bbox
        z_top = (min_iz - 0.5) * grid_size
        z_bottom = (max_iz + 0.5) * grid_size
        for boundary_ix in range(min_ix, max_ix + 2):
            x = (boundary_ix - 0.5) * grid_size
            start = self._project_overhead_world_point(
                x=x,
                z=z_top,
                camera_pose=camera_pose,
                image_size=image_size,
            )
            end = self._project_overhead_world_point(
                x=x,
                z=z_bottom,
                camera_pose=camera_pose,
                image_size=image_size,
            )
            draw.line([start, end], fill=_GRID_LINE_COLOUR)

        x_left = (min_ix - 0.5) * grid_size
        x_right = (max_ix + 0.5) * grid_size
        for boundary_iz in range(min_iz, max_iz + 2):
            z = (boundary_iz - 0.5) * grid_size
            start = self._project_overhead_world_point(
                x=x_left,
                z=z,
                camera_pose=camera_pose,
                image_size=image_size,
            )
            end = self._project_overhead_world_point(
                x=x_right,
                z=z,
                camera_pose=camera_pose,
                image_size=image_size,
            )
            draw.line([start, end], fill=_GRID_LINE_COLOUR)

    def _draw_path_trail_world(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        path: list[tuple[int, int]],
        min_ix: int,
        min_iz: int,
        colour: tuple[int, int, int],
    ) -> None:
        points = [
            self._world_marker_center(ix=ix, iz=iz, min_ix=min_ix, min_iz=min_iz) for ix, iz in path
        ]
        _draw_path_lines(draw, points=points, colour=colour)

    def _draw_projected_path_trail(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        path: list[tuple[int, int]],
        camera_pose: dict[str, object],
        image_size: tuple[int, int],
        grid_size: float,
        colour: tuple[int, int, int],
    ) -> None:
        points = [
            self._project_overhead_world_point(
                x=ix * grid_size,
                z=iz * grid_size,
                camera_pose=camera_pose,
                image_size=image_size,
            )
            for ix, iz in path
        ]
        _draw_path_lines(draw, points=points, colour=colour)

    def _world_marker_center(
        self,
        *,
        ix: int,
        iz: int,
        min_ix: int,
        min_iz: int,
    ) -> tuple[float, float]:
        cx = _STRUCTURED_MARGIN_PX + (ix - min_ix) * self.cell_px + self.cell_px / 2.0
        cy = _STRUCTURED_MARGIN_PX + (iz - min_iz) * self.cell_px + self.cell_px / 2.0
        return (cx, cy)

    def _project_overhead_world_point(
        self,
        *,
        x: float,
        z: float,
        camera_pose: dict[str, object],
        image_size: tuple[int, int],
    ) -> tuple[float, float]:
        width, height = image_size
        if width <= 0 or height <= 0:
            return (0.0, 0.0)
        position = camera_pose.get("position")
        if not isinstance(position, dict):
            return (0.0, 0.0)
        cam_x = float(position.get("x", 0.0))
        cam_z = float(position.get("z", 0.0))
        orthographic_size = float(camera_pose.get("orthographicSize", 1.0))
        half_height = max(orthographic_size, 1e-6)
        half_width = half_height * (width / height)
        px = ((x - cam_x) / half_width + 1.0) * 0.5 * width
        py = (-(z - cam_z) / half_height + 1.0) * 0.5 * height
        return (px, py)

    def composite_frame(
        self,
        agent_frames: list[np.ndarray],
        overhead_map: Image.Image,
        *,
        frame_height: int = 240,
    ) -> Image.Image:
        """Tile agent frames beside the overhead map with label bars."""
        panels: list[Image.Image] = []

        for i, frame in enumerate(agent_frames):
            img = Image.fromarray(frame).convert("RGB")
            aspect = img.width / img.height
            new_w = max(1, int(frame_height * aspect))
            img = img.resize((new_w, frame_height), _RESAMPLE)
            colour = _AGENT_COLOURS[i % len(_AGENT_COLOURS)]
            label_bar = _make_label_bar(new_w, f"Agent {i}", colour)
            panels.append(_vstack([label_bar, img]))

        oh_aspect = overhead_map.width / overhead_map.height
        oh_w = max(1, int(frame_height * oh_aspect))
        oh_scaled = overhead_map.resize((oh_w, frame_height), _RESAMPLE)
        label_bar = _make_label_bar(oh_w, "Overhead", (80, 80, 80))
        panels.append(_vstack([label_bar, oh_scaled]))

        return _hstack(panels)

    @staticmethod
    def save_png(image: Image.Image, path: str | Path) -> None:
        """Save a PIL Image as PNG."""
        image.save(str(path), format="PNG")

    @staticmethod
    def frame_to_array(image: Image.Image) -> np.ndarray:
        """Convert a PIL Image to a (H, W, 3) uint8 numpy array."""
        return np.asarray(image.convert("RGB"), dtype=np.uint8)

    @staticmethod
    def save_gif(
        frames: list[Image.Image | np.ndarray],
        path: str | Path,
        fps: float = 4.0,
    ) -> None:
        """Save a sequence of frames as an animated GIF via imageio."""
        if not _HAS_IMAGEIO:
            raise ImportError("imageio is required for GIF output: pip install imageio")
        arrays: list[np.ndarray] = []
        for f in frames:
            if isinstance(f, np.ndarray):
                arrays.append(f)
            else:
                arrays.append(np.asarray(f.convert("RGB"), dtype=np.uint8))
        duration_ms = int(1000 / fps)
        imageio.mimsave(str(path), arrays, duration=duration_ms)


def _lighten(colour: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in colour)  # type: ignore[return-value]


def _trim_uniform_border(image: Image.Image, tolerance: int = 10, padding: int = 2) -> Image.Image:
    """Crop away a uniform border when the corner pixels agree closely."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    if width < 3 or height < 3:
        return rgb

    arr = np.asarray(rgb, dtype=np.int16)
    corners = np.asarray(
        [arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]],
        dtype=np.int16,
    )
    if np.abs(corners - corners[0]).max() > tolerance:
        return rgb

    background = corners.mean(axis=0)
    mask = np.abs(arr - background).max(axis=2) > tolerance
    if not mask.any():
        return rgb

    ys, xs = np.where(mask)
    top = max(0, int(ys.min()) - padding)
    bottom = min(height, int(ys.max()) + padding + 1)
    left = max(0, int(xs.min()) - padding)
    right = min(width, int(xs.max()) + padding + 1)
    if top == 0 and left == 0 and bottom == height and right == width:
        return rgb
    return rgb.crop((left, top, right, bottom))


def _supports_projected_overhead(
    camera_pose: dict[str, object],
    tolerance_deg: float = 1.0,
) -> bool:
    """Return ``True`` when the pose matches AI2-THOR's axis-aligned top-down camera."""
    rotation = camera_pose.get("rotation")
    if not isinstance(rotation, dict):
        return False
    rot_x = float(rotation.get("x", 0.0))
    rot_y = float(rotation.get("y", 0.0))
    rot_z = float(rotation.get("z", 0.0))
    return (
        abs(rot_x - 90.0) <= tolerance_deg
        and abs(rot_y) <= tolerance_deg
        and abs(rot_z) <= tolerance_deg
    )


def _make_label_bar(width: int, text: str, bg_colour: tuple[int, int, int]) -> Image.Image:
    bar = Image.new("RGB", (width, 20), bg_colour)
    draw = ImageDraw.Draw(bar)
    _draw_label(draw, position=(4, 2), label=text)
    return bar


def _draw_grid_lines(
    draw: ImageDraw.ImageDraw,
    *,
    cols: int,
    rows: int,
    cell_px: int,
    x0: int,
    y0: int,
) -> None:
    x1 = x0 + cols * cell_px
    y1 = y0 + rows * cell_px
    for col in range(cols + 1):
        x = x0 + col * cell_px
        draw.line([(x, y0), (x, y1)], fill=_GRID_LINE_COLOUR)
    for row in range(rows + 1):
        y = y0 + row * cell_px
        draw.line([(x0, y), (x1, y)], fill=_GRID_LINE_COLOUR)


def _draw_label(
    draw: ImageDraw.ImageDraw,
    *,
    position: tuple[float, float],
    label: str,
) -> None:
    try:
        draw.text(position, label, fill=(255, 255, 255), font=ImageFont.load_default())
    except Exception:
        pass


def _draw_labeled_circle(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[float, float],
    radius: int,
    colour: tuple[int, int, int],
    label: str,
) -> None:
    cx, cy = center
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=colour,
        outline=(0, 0, 0),
    )
    _draw_label(draw, position=(cx - radius // 2, cy - radius // 2), label=label)


def _draw_labeled_triangle(
    draw: ImageDraw.ImageDraw,
    *,
    points: list[tuple[float, float]],
    label_center: tuple[float, float],
    colour: tuple[int, int, int],
    label: str,
) -> None:
    draw.polygon(points, fill=colour, outline=(0, 0, 0))
    _draw_label(draw, position=(label_center[0] - 3, label_center[1] - 4), label=label)


def _draw_path_lines(
    draw: ImageDraw.ImageDraw,
    *,
    points: list[tuple[float, float]],
    colour: tuple[int, int, int],
) -> None:
    for start, end in pairwise(points):
        draw.line([start, end], fill=colour, width=2)


def _vstack(images: list[Image.Image]) -> Image.Image:
    """Vertically stack PIL images; left-align if widths differ."""
    w = max(img.width for img in images)
    total_h = sum(img.height for img in images)
    out = Image.new("RGB", (w, total_h), (0, 0, 0))
    y = 0
    for img in images:
        out.paste(img, (0, y))
        y += img.height
    return out


def _hstack(images: list[Image.Image]) -> Image.Image:
    """Horizontally stack PIL images; top-align if heights differ."""
    total_w = sum(img.width for img in images)
    h = max(img.height for img in images)
    out = Image.new("RGB", (total_w, h), (0, 0, 0))
    x = 0
    for img in images:
        out.paste(img, (x, 0))
        x += img.width
    return out
