from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import imageio  # type: ignore[import-untyped]

    _HAS_IMAGEIO = True
except ImportError:
    _HAS_IMAGEIO = False


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

# Per-agent colours (RGB), up to 8 agents.
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

# SOUL → badge colour mapping. Unknown souls fall back to grey.
_SOUL_COLOURS: dict[str, tuple[int, int, int]] = {
    "aggressive": (220, 50, 50),  # red
    "defensive": (50, 120, 220),  # blue
    "cooperative": (50, 180, 50),  # green
    "default": (130, 130, 130),  # grey
}

# Alpha for cell tints so a photographic base frame remains visible underneath.
_CELL_TINT_ALPHA: int = 140

_RESAMPLE = Image.Resampling.BILINEAR


# ---------------------------------------------------------------------------
# GameVisualizer
# ---------------------------------------------------------------------------


class GameVisualizer:
    """Generate overhead grid maps and composite frames for game visualizations.

    Args:
        grid_rows: Number of rows in the logical game grid.
        grid_cols: Number of columns in the logical game grid.
        cell_px: Pixel size of each grid cell in the rendered map.
        agent_count: Number of agents (determines colour palette size hint).
    """

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
        # Per-agent SOUL labels (e.g. ["aggressive", "defensive"]).
        # When set, agent sprites get a SOUL badge and trail cells are tinted
        # in the SOUL colour instead of the generic agent colour.
        self.agent_labels: list[str] = agent_labels or []
        self._map_w = grid_cols * cell_px
        self._map_h = grid_rows * cell_px

    # ------------------------------------------------------------------
    # Overhead map
    # ------------------------------------------------------------------

    def render_overhead_map(
        self,
        *,
        agent_positions: list[tuple[int, int]],
        claimed_cells: dict[int, list[tuple[int, int]]] | None = None,
        covered_cells: list[tuple[int, int]] | None = None,
        base_frame: np.ndarray | None = None,
    ) -> Image.Image:
        """Render a 2-D overhead grid map.

        Args:
            agent_positions: (row, col) grid position for each agent.
                             Index ``i`` corresponds to agent ``i``.
            claimed_cells: Territory game — mapping ``agent_id`` →
                           list of (row, col) cells that agent has claimed.
                           Each agent's cells are tinted with their colour.
            covered_cells: Coverage game — list of (row, col) cells that have
                           been within any agent's field of view.
            base_frame: Optional AI2-THOR top-down frame (H, W, 3) uint8 to
                        use as background.  When ``None``, a white canvas is used.

        Returns:
            PIL Image (RGB) of size ``(grid_cols * cell_px, grid_rows * cell_px)``.
        """
        if base_frame is not None:
            bg = (
                Image.fromarray(base_frame)
                .convert("RGB")
                .resize((self._map_w, self._map_h), _RESAMPLE)
            )
        else:
            bg = Image.new("RGB", (self._map_w, self._map_h), _BACKGROUND_COLOUR)

        # Draw cell tints on a separate RGBA overlay so the base frame shows
        # through — solid fills would hide the AI2-THOR floorplan behind.
        overlay = Image.new("RGBA", (self._map_w, self._map_h), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        # Covered cells (cooperative coverage game)
        if covered_cells:
            tint = (*_COVERED_COLOUR, _CELL_TINT_ALPHA)
            for row, col in covered_cells:
                self._fill_cell(odraw, row, col, tint)

        # Claimed cells (territory game) — per-agent tint
        if claimed_cells:
            for agent_id, cells in claimed_cells.items():
                base_colour = self._agent_colour(agent_id)
                tint = (*_lighten(base_colour, 60), _CELL_TINT_ALPHA)
                for row, col in cells:
                    self._fill_cell(odraw, row, col, tint)

        bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(bg)

        # Grid lines
        self._draw_grid(draw)

        # Agent markers — colour and badge from SOUL label when available
        for idx, (row, col) in enumerate(agent_positions):
            colour = self._agent_colour(idx)
            soul_label = self.agent_labels[idx] if idx < len(self.agent_labels) else ""
            badge = soul_label[0].upper() if soul_label else str(idx)
            self._draw_agent_marker(draw, row, col, colour, label=badge)

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
    ) -> Image.Image:
        """Render a pure grid map from world-grid coordinates.

        ``world_bbox`` is ``(min_ix, min_iz, max_ix, max_iz)``.
        """
        min_ix, min_iz, max_ix, max_iz = world_bbox
        cols = max_ix - min_ix + 1
        rows = max_iz - min_iz + 1
        width = cols * self.cell_px + _STRUCTURED_MARGIN_PX * 2
        height = rows * self.cell_px + _STRUCTURED_MARGIN_PX * 2
        img = Image.new("RGB", (width, height), _STRUCTURED_UNREACHABLE_COLOUR)
        draw = ImageDraw.Draw(img)

        claimed_lookup: dict[tuple[int, int], int] = {}
        for agent_id, cells in (claimed_cells or {}).items():
            for cell in cells:
                claimed_lookup[cell] = agent_id
        covered_lookup = set(covered_cells or [])

        for iz in range(min_iz, max_iz + 1):
            for ix in range(min_ix, max_ix + 1):
                cell = (ix, iz)
                colour = _STRUCTURED_UNREACHABLE_COLOUR
                if cell in reachable_cells:
                    colour = _STRUCTURED_REACHABLE_COLOUR
                if cell in covered_lookup:
                    colour = _STRUCTURED_COVERED_COLOUR
                if cell in claimed_lookup:
                    colour = self._agent_colour(claimed_lookup[cell])
                self._fill_world_cell(draw, ix, iz, min_ix, min_iz, colour)

        self._draw_structured_grid(draw, cols=cols, rows=rows)

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

    def _agent_colour(self, agent_id: int) -> tuple[int, int, int]:
        """Return the colour for an agent.

        When ``agent_labels`` is set for this agent, use the SOUL colour
        (unknown souls fall back to grey).  When no label is set, use the
        generic agent palette so unlabelled games look the same as before.
        """
        if agent_id < len(self.agent_labels):
            soul = self.agent_labels[agent_id]
            return _SOUL_COLOURS.get(soul, _SOUL_COLOURS["default"])
        return _AGENT_COLOURS[agent_id % len(_AGENT_COLOURS)]

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
        colour: tuple[int, int, int],
    ) -> None:
        x0 = _STRUCTURED_MARGIN_PX + (ix - min_ix) * self.cell_px
        y0 = _STRUCTURED_MARGIN_PX + (iz - min_iz) * self.cell_px
        draw.rectangle([x0, y0, x0 + self.cell_px - 1, y0 + self.cell_px - 1], fill=colour)

    def _draw_grid(self, draw: ImageDraw.ImageDraw) -> None:
        for col in range(self.grid_cols + 1):
            x = col * self.cell_px
            draw.line([(x, 0), (x, self._map_h)], fill=_GRID_LINE_COLOUR)
        for row in range(self.grid_rows + 1):
            y = row * self.cell_px
            draw.line([(0, y), (self._map_w, y)], fill=_GRID_LINE_COLOUR)

    def _draw_structured_grid(
        self,
        draw: ImageDraw.ImageDraw,
        *,
        cols: int,
        rows: int,
    ) -> None:
        x0 = _STRUCTURED_MARGIN_PX
        y0 = _STRUCTURED_MARGIN_PX
        x1 = x0 + cols * self.cell_px
        y1 = y0 + rows * self.cell_px
        for col in range(cols + 1):
            x = x0 + col * self.cell_px
            draw.line([(x, y0), (x, y1)], fill=_GRID_LINE_COLOUR)
        for row in range(rows + 1):
            y = y0 + row * self.cell_px
            draw.line([(x0, y), (x1, y)], fill=_GRID_LINE_COLOUR)

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
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour, outline=(0, 0, 0))
        try:
            font = ImageFont.load_default()
            draw.text((cx - r // 2, cy - r // 2), label, fill=(255, 255, 255), font=font)
        except Exception:
            pass

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
        cx = _STRUCTURED_MARGIN_PX + (ix - min_ix) * self.cell_px + self.cell_px / 2.0
        cy = _STRUCTURED_MARGIN_PX + (iz - min_iz) * self.cell_px + self.cell_px / 2.0
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

        draw.polygon([tip, left, right], fill=colour, outline=(0, 0, 0))
        try:
            font = ImageFont.load_default()
            draw.text((cx - 3, cy - 4), label, fill=(255, 255, 255), font=font)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Composite frame
    # ------------------------------------------------------------------

    def composite_frame(
        self,
        agent_frames: list[np.ndarray],
        overhead_map: Image.Image,
        *,
        frame_height: int = 240,
    ) -> Image.Image:
        """Tile agent first-person frames side-by-side next to the overhead map.

        Each panel gets a small coloured label bar on top.  The resulting image
        has ``len(agent_frames) + 1`` panels arranged horizontally.

        Args:
            agent_frames: RGB numpy arrays (H, W, 3) uint8, one per agent.
            overhead_map: PIL Image of the overhead grid map.
            frame_height: Target height (pixels) for every panel.
                          Label bars add 20 px on top, so total height is
                          ``frame_height + 20``.

        Returns:
            Single PIL Image with all panels arranged left-to-right.
        """
        panels: list[Image.Image] = []

        for i, frame in enumerate(agent_frames):
            img = Image.fromarray(frame).convert("RGB")
            aspect = img.width / img.height
            new_w = max(1, int(frame_height * aspect))
            img = img.resize((new_w, frame_height), _RESAMPLE)
            colour = _AGENT_COLOURS[i % len(_AGENT_COLOURS)]
            label_bar = _make_label_bar(new_w, f"Agent {i}", colour)
            panels.append(_vstack([label_bar, img]))

        # Overhead map panel
        oh_aspect = overhead_map.width / overhead_map.height
        oh_w = max(1, int(frame_height * oh_aspect))
        oh_scaled = overhead_map.resize((oh_w, frame_height), _RESAMPLE)
        label_bar = _make_label_bar(oh_w, "Overhead", (80, 80, 80))
        panels.append(_vstack([label_bar, oh_scaled]))

        return _hstack(panels)

    # ------------------------------------------------------------------
    # I/O helpers
    # ------------------------------------------------------------------

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
        """Save a sequence of frames as an animated GIF via imageio.

        Args:
            frames: Sequence of PIL Images or numpy arrays (H, W, 3) uint8.
            path: Output ``.gif`` file path.
            fps: Frames per second.

        Raises:
            ImportError: If ``imageio`` is not installed.
        """
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


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _lighten(colour: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in colour)  # type: ignore[return-value]


def _make_label_bar(width: int, text: str, bg_colour: tuple[int, int, int]) -> Image.Image:
    bar = Image.new("RGB", (width, 20), bg_colour)
    draw = ImageDraw.Draw(bar)
    try:
        font = ImageFont.load_default()
        draw.text((4, 2), text, fill=(255, 255, 255), font=font)
    except Exception:
        pass
    return bar


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
