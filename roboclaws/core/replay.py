from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

try:
    import imageio  # type: ignore[import-untyped]

    _HAS_IMAGEIO = True
except ImportError:
    _HAS_IMAGEIO = False


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class StepRecord:
    """Data captured for a single game step."""

    step: int
    agent_id: int
    agent_frames: list[np.ndarray]  # one (H, W, 3) uint8 array per agent
    overhead_frame: np.ndarray  # (H, W, 3) uint8
    game_state: dict[str, Any]
    vlm_prompt_state: dict[str, Any]
    vlm_response: dict[str, Any]
    provider_status: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplaySummary:
    """High-level summary produced after a game session."""

    game: str
    agent_count: int
    total_steps: int
    duration_seconds: float
    vlm_cost_usd: float
    final_scores: dict[str, Any] = field(default_factory=dict)
    termination_reason: str = "unknown"
    provider_status: dict[str, Any] = field(default_factory=dict)

    def print(self) -> None:
        """Print a human-readable summary to stdout."""
        print(f"Game          : {self.game}")
        print(f"Agents        : {self.agent_count}")
        print(f"Steps         : {self.total_steps}")
        print(f"Duration      : {self.duration_seconds:.1f}s")
        print(f"VLM cost      : ${self.vlm_cost_usd:.6f}")
        print(f"Termination   : {self.termination_reason}")
        if self.final_scores:
            print(f"Final scores  : {self.final_scores}")
        if self.provider_status:
            print(f"Provider      : {self.provider_status}")


# ---------------------------------------------------------------------------
# ReplayRecorder
# ---------------------------------------------------------------------------


class ReplayRecorder:
    """Records per-step game data and saves it to disk for replay and analysis.

    Usage::

        recorder = ReplayRecorder(agent_count=2, game="territory")
        # inside the game loop:
        recorder.record_step(
            step=step_num,
            agent_id=agent_id,
            agent_frames=[frame0, frame1],
            overhead_frame=overhead,
            game_state=game.get_state(),
            vlm_prompt_state=prompt_state,
            vlm_response=vlm_response,
        )
        # after the game:
        recorder.save("output/run_001", vlm_cost_usd=provider.cumulative_cost)
    """

    def __init__(self, agent_count: int, game: str = "unknown") -> None:
        self._agent_count = agent_count
        self._game = game
        self._steps: list[StepRecord] = []
        self._start_time = time.time()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_step(
        self,
        *,
        step: int,
        agent_id: int,
        agent_frames: list[np.ndarray],
        overhead_frame: np.ndarray,
        game_state: dict[str, Any],
        vlm_prompt_state: dict[str, Any],
        vlm_response: dict[str, Any],
        provider_status: dict[str, Any] | None = None,
    ) -> None:
        """Append one step's worth of data to the internal buffer.

        Args:
            step: Global step counter.
            agent_id: Which agent acted this step.
            agent_frames: First-person RGB frames for every agent (H, W, 3) uint8.
            overhead_frame: Top-down RGB frame from the scene camera (H, W, 3) uint8.
            game_state: Structured state dict from the game (e.g. ``game.get_state()``).
            vlm_prompt_state: State dict actually sent to the VLM as context.
            vlm_response: Dict returned by the VLM (must contain at least ``"action"``).
        """
        self._steps.append(
            StepRecord(
                step=step,
                agent_id=agent_id,
                agent_frames=[f.copy() for f in agent_frames],
                overhead_frame=overhead_frame.copy(),
                game_state=game_state,
                vlm_prompt_state=vlm_prompt_state,
                vlm_response=vlm_response,
                provider_status=dict(provider_status or {}),
            )
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(
        self,
        output_dir: str | Path,
        *,
        vlm_cost_usd: float = 0.0,
        final_scores: dict[str, Any] | None = None,
        termination_reason: str = "unknown",
        generate_gif: bool = True,
        gif_fps: float = 4.0,
        generate_report: bool = False,
        provider_status: dict[str, Any] | None = None,
    ) -> Path:
        """Persist all recorded data to *output_dir*.

        Directory layout::

            output_dir/
            ├── replay.json           — full manifest (metadata + every step)
            ├── replay.gif            — animated composite GIF (optional)
            ├── frames/               — composite PNG per step
            │   ├── 0000_composite.png
            │   └── …
            ├── agent_frames/         — per-agent PNG per step
            │   ├── 0000_agent0.png
            │   └── …
            └── overhead/             — overhead-map PNG per step
                ├── 0000_overhead.png
                └── …

        Args:
            output_dir: Root directory to write into (created if absent).
            vlm_cost_usd: Total VLM spend for this session (from provider).
            final_scores: Game-specific final scores dict.
            termination_reason: Why the game ended ("max_steps", "coverage_reached", …).
            generate_gif: Write ``replay.gif`` when ``imageio`` is available.
            gif_fps: Frames per second for the output GIF.
            generate_report: Generate a self-contained ``report.html`` via
                :mod:`roboclaws.core.reporter` after saving. Defaults to ``False``.

        Returns:
            Resolved ``Path`` to the output directory.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "frames").mkdir(exist_ok=True)
        (out / "agent_frames").mkdir(exist_ok=True)
        (out / "overhead").mkdir(exist_ok=True)

        composite_frames: list[np.ndarray] = []
        steps_data: list[dict[str, Any]] = []

        for rec in self._steps:
            tag = f"{rec.step:04d}"

            # Per-agent first-person frames
            for aid, frame in enumerate(rec.agent_frames):
                Image.fromarray(frame).save(str(out / "agent_frames" / f"{tag}_agent{aid}.png"))

            # Overhead frame
            Image.fromarray(rec.overhead_frame).save(str(out / "overhead" / f"{tag}_overhead.png"))

            # Composite frame (agent frames + overhead side-by-side)
            composite_img = _make_composite(rec.agent_frames, rec.overhead_frame)
            composite_img.save(str(out / "frames" / f"{tag}_composite.png"))
            composite_frames.append(np.asarray(composite_img.convert("RGB"), dtype=np.uint8))

            steps_data.append(
                {
                    "step": rec.step,
                    "agent_id": rec.agent_id,
                    "game_state": _jsonify(rec.game_state),
                    "vlm_prompt_state": _jsonify(rec.vlm_prompt_state),
                    "vlm_response": _jsonify(rec.vlm_response),
                    "provider_status": _jsonify(rec.provider_status),
                }
            )

        duration = time.time() - self._start_time
        scores = final_scores or {}
        manifest: dict[str, Any] = {
            "metadata": {
                "game": self._game,
                "agent_count": self._agent_count,
                "total_steps": len(self._steps),
                "duration_seconds": round(duration, 2),
                "vlm_cost_usd": round(vlm_cost_usd, 6),
            },
            "summary": {
                "final_scores": _jsonify(scores),
                "total_steps": len(self._steps),
                "vlm_cost_usd": round(vlm_cost_usd, 6),
                "step_count": len(self._steps),
                "game_duration_seconds": round(duration, 2),
                "termination_reason": termination_reason,
                "provider_status": _jsonify(provider_status or {}),
            },
            "steps": steps_data,
        }
        (out / "replay.json").write_text(json.dumps(manifest, indent=2))

        if generate_gif and composite_frames and _HAS_IMAGEIO:
            self.generate_gif(composite_frames, out / "replay.gif", fps=gif_fps)

        if generate_report:
            from roboclaws.core.reporter import generate as _gen_report  # noqa: PLC0415

            _gen_report(out)

        return out

    # ------------------------------------------------------------------
    # GIF helpers
    # ------------------------------------------------------------------

    @staticmethod
    def generate_gif(
        frames: list[np.ndarray | Image.Image],
        path: str | Path,
        fps: float = 4.0,
    ) -> None:
        """Save *frames* as an animated GIF.

        Args:
            frames: Sequence of numpy arrays (H, W, 3) uint8 or PIL Images.
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

    @staticmethod
    def generate_gif_from_dir(
        replay_dir: str | Path,
        output_path: str | Path | None = None,
        fps: float = 4.0,
    ) -> Path:
        """Generate a GIF from composite frames in an existing replay directory.

        Args:
            replay_dir: Directory created by :meth:`save`.
            output_path: Output ``.gif`` path; defaults to ``replay_dir/replay.gif``.
            fps: Frames per second.

        Returns:
            Path to the written GIF.

        Raises:
            FileNotFoundError: If no composite frames are found.
            ImportError: If ``imageio`` is not installed.
        """
        replay_dir = Path(replay_dir)
        frames_dir = replay_dir / "frames"
        frame_paths = sorted(frames_dir.glob("*_composite.png"))
        if not frame_paths:
            raise FileNotFoundError(f"No composite frames found in {frames_dir}")
        frames = [np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8) for p in frame_paths]
        gif_path = Path(output_path) if output_path else replay_dir / "replay.gif"
        ReplayRecorder.generate_gif(frames, gif_path, fps=fps)
        return gif_path

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(
        self,
        *,
        vlm_cost_usd: float = 0.0,
        final_scores: dict[str, Any] | None = None,
        termination_reason: str = "unknown",
        provider_status: dict[str, Any] | None = None,
    ) -> ReplaySummary:
        """Return a :class:`ReplaySummary` for the recorded session.

        Args:
            vlm_cost_usd: Total VLM spend (from the provider's cumulative counter).
            final_scores: Game-specific final scores (e.g. cells claimed per agent).
            termination_reason: Reason the game ended.

        Returns:
            :class:`ReplaySummary` instance.
        """
        duration = time.time() - self._start_time
        return ReplaySummary(
            game=self._game,
            agent_count=self._agent_count,
            total_steps=len(self._steps),
            duration_seconds=round(duration, 2),
            vlm_cost_usd=round(vlm_cost_usd, 6),
            final_scores=final_scores or {},
            termination_reason=termination_reason,
            provider_status=provider_status or {},
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _make_composite(
    agent_frames: list[np.ndarray],
    overhead_frame: np.ndarray,
    target_height: int = 240,
) -> Image.Image:
    """Create a side-by-side composite of agent frames and overhead map."""
    panels: list[Image.Image] = []
    for frame in agent_frames:
        img = Image.fromarray(frame).convert("RGB")
        aspect = img.width / img.height if img.height > 0 else 1.0
        new_w = max(1, int(target_height * aspect))
        panels.append(img.resize((new_w, target_height), Image.Resampling.BILINEAR))

    oh_img = Image.fromarray(overhead_frame).convert("RGB")
    oh_aspect = oh_img.width / oh_img.height if oh_img.height > 0 else 1.0
    oh_w = max(1, int(target_height * oh_aspect))
    panels.append(oh_img.resize((oh_w, target_height), Image.Resampling.BILINEAR))

    total_w = sum(p.width for p in panels)
    h = max(p.height for p in panels)
    out = Image.new("RGB", (total_w, h), (0, 0, 0))
    x = 0
    for panel in panels:
        out.paste(panel, (x, 0))
        x += panel.width
    return out


def _jsonify(obj: Any) -> Any:
    """Recursively convert numpy scalars/arrays to JSON-serialisable types."""
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
