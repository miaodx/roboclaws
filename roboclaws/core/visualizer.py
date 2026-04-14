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
    ) -> None:
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.cell_px = cell_px
        self.agent_count = agent_count
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
                base_colour = _AGENT_COLOURS[agent_id % len(_AGENT_COLOURS)]
                tint = (*_lighten(base_colour, 60), _CELL_TINT_ALPHA)
                for row, col in cells:
                    self._fill_cell(odraw, row, col, tint)

        bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(bg)

        # Grid lines
        self._draw_grid(draw)

        # Agent markers
        for idx, (row, col) in enumerate(agent_positions):
            colour = _AGENT_COLOURS[idx % len(_AGENT_COLOURS)]
            self._draw_agent_marker(draw, row, col, colour, label=str(idx))

        return bg

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

    def _draw_grid(self, draw: ImageDraw.ImageDraw) -> None:
        for col in range(self.grid_cols + 1):
            x = col * self.cell_px
            draw.line([(x, 0), (x, self._map_h)], fill=_GRID_LINE_COLOUR)
        for row in range(self.grid_rows + 1):
            y = row * self.cell_px
            draw.line([(0, y), (self._map_w, y)], fill=_GRID_LINE_COLOUR)

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
