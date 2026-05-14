"""Generate demo ``report.html`` files without requiring AI2-THOR.

Used by CI so every push produces a browsable HTML artifact showing what the
visualization system renders for each example. Mocks :class:`MultiAgentEngine`
so Unity / xvfb are not needed, and drives both the territory and coverage
examples end-to-end with the ``mock`` VLM provider. Also writes an A/B
comparison page.

Usage::

    python scripts/reports/generate_demo_report.py --output-dir output/demo --steps 20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "examples" / "games"))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "reports"))

from write_pages_index import write_index as _write_index  # noqa: E402

from roboclaws.core.engine import AgentState  # noqa: E402
from roboclaws.core.reporter import compare as _compare_reports  # noqa: E402
from roboclaws.core.reporter import generate as _generate_report  # noqa: E402

# ---------------------------------------------------------------------------
# Fake engine
# ---------------------------------------------------------------------------

_FRAME_H, _FRAME_W = 96, 128
_OVERHEAD_H, _OVERHEAD_W = 300, 300


def _synth_overhead_frame() -> np.ndarray:
    """Create a synthetic floorplan-ish overhead image for the demo reports.

    A uniform beige "floor" with a few muted rectangles standing in for
    furniture, so the mock demo map isn't a solid black or white background.
    """
    frame = np.full((_OVERHEAD_H, _OVERHEAD_W, 3), (232, 222, 198), dtype=np.uint8)
    # Walls
    frame[:8, :, :] = (160, 140, 110)
    frame[-8:, :, :] = (160, 140, 110)
    frame[:, :8, :] = (160, 140, 110)
    frame[:, -8:, :] = (160, 140, 110)
    # Sofa (left)
    frame[80:140, 20:90, :] = (120, 150, 180)
    # Coffee table (centre)
    frame[130:170, 130:200, :] = (170, 130, 90)
    # Rug (under table)
    frame[110:200, 110:220, :] = (210, 180, 150)
    frame[130:170, 130:200, :] = (170, 130, 90)  # table on top of rug
    # TV cabinet (right)
    frame[60:90, 230:290, :] = (90, 90, 90)
    # Plant (bottom-left)
    frame[230:270, 40:80, :] = (80, 140, 80)
    return frame


def _synth_frame(agent_id: int, step: int) -> np.ndarray:
    """Create a small RGB frame tinted by agent_id so the report is visually distinct."""
    frame = np.zeros((_FRAME_H, _FRAME_W, 3), dtype=np.uint8)
    palette = [(70, 130, 220), (220, 90, 90), (90, 200, 110)]
    r, g, b = palette[agent_id % len(palette)]
    # Step-dependent gradient so frames differ step to step.
    shift = (step * 7) % 60
    frame[:, :, 0] = np.clip(r - shift, 0, 255)
    frame[:, :, 1] = np.clip(g + shift // 2, 0, 255)
    frame[:, :, 2] = np.clip(b + shift // 3, 0, 255)
    # Horizontal band that tracks the step, as a "motion" cue.
    band_y = (step * 3) % _FRAME_H
    frame[band_y : band_y + 4, :, :] = 255
    return frame


class _FakeEngine:
    """Minimal in-process stand-in for :class:`MultiAgentEngine`.

    Agents walk in a deterministic pseudo-random pattern so the overhead map
    actually changes between steps, producing an interesting demo report.
    """

    _STEP_BY_ACTION: dict[str, tuple[float, float]] = {
        "MoveAhead": (0.0, 0.25),
        "MoveBack": (0.0, -0.25),
        "MoveLeft": (-0.25, 0.0),
        "MoveRight": (0.25, 0.0),
        "RotateLeft": (0.0, 0.0),
        "RotateRight": (0.0, 0.0),
        "LookUp": (0.0, 0.0),
        "LookDown": (0.0, 0.0),
    }

    def __init__(
        self,
        scene: str,
        agent_count: int,
        grid_size: float = 0.25,
        **_kwargs: object,
    ) -> None:
        self.scene = scene
        self.agent_count = agent_count
        self.grid_size = grid_size
        self.field_of_view = 90
        self._step_counter = 0
        self._overhead_frame = _synth_overhead_frame()
        # Spread agents along +x so they start on distinct cells.
        self._positions: list[dict[str, float]] = [
            {"x": float(i) * grid_size * 2.0, "y": 0.9, "z": 0.0} for i in range(agent_count)
        ]
        self._rotations: list[dict[str, float]] = [
            {"x": 0.0, "y": 0.0, "z": 0.0} for _ in range(agent_count)
        ]
        self._chase_cam_ids: dict[int, int] = {}

    def _build_state(
        self,
        agent_id: int,
        last_action_success: bool = True,
        last_action_error: str = "",
    ) -> AgentState:
        return AgentState(
            agent_id=agent_id,
            frame=_synth_frame(agent_id, self._step_counter),
            position=dict(self._positions[agent_id]),
            rotation=dict(self._rotations[agent_id]),
            camera_horizon=0.0,
            visible_objects=[],
            last_action_success=last_action_success,
            last_action_error=last_action_error,
        )

    def get_all_agent_states(self) -> list[AgentState]:
        return [self._build_state(i) for i in range(self.agent_count)]

    def get_agent_state(self, agent_id: int) -> AgentState:
        return self._build_state(agent_id)

    def step(self, agent_id: int, action: str, **_kw: object) -> AgentState:
        dx, dz = self._STEP_BY_ACTION.get(action, (0.0, 0.0))
        # Keep agents inside a small square so the overhead map stays populated.
        new_x = max(-4.0, min(4.0, self._positions[agent_id]["x"] + dx))
        new_z = max(-4.0, min(4.0, self._positions[agent_id]["z"] + dz))
        self._positions[agent_id]["x"] = new_x
        self._positions[agent_id]["z"] = new_z
        self._step_counter += 1
        return self._build_state(agent_id)

    def get_overhead_frame(self) -> np.ndarray:
        return self._overhead_frame.copy()

    def get_reachable_positions(self) -> set[tuple[int, int]]:
        # Match the ±4 m box agents move within in ``step()``.
        span = int(round(4.0 / self.grid_size))
        return {(ix, iz) for ix in range(-span, span + 1) for iz in range(-span, span + 1)}

    def add_chase_cam(self, agent_id: int) -> int:
        if agent_id not in self._chase_cam_ids:
            self._chase_cam_ids[agent_id] = len(self._chase_cam_ids)
        return self._chase_cam_ids[agent_id]

    def update_chase_cam(self, agent_id: int) -> None:
        self.add_chase_cam(agent_id)

    def get_chase_cam_frame(self, agent_id: int) -> np.ndarray:
        # Offset the synthetic frame by one step so chase-cam panels are visually
        # distinct from first-person panels in generated HTML reports.
        return _synth_frame(agent_id, self._step_counter + 1)

    def close(self) -> None:  # pragma: no cover - nothing to release
        pass


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------


def _run_territory_demo(output_dir: Path, agents: int, steps: int) -> Path:
    from territory_game import run_territory_game  # noqa: PLC0415

    with patch("territory_game.MultiAgentEngine", _FakeEngine):
        result = run_territory_game(
            scene="FloorPlan201",
            agent_count=agents,
            steps=steps,
            model="mock",
            output_dir=str(output_dir),
        )
    replay_dir = Path(result["output_dir"])
    _generate_report(
        replay_dir,
        rerun_command=(
            "just task::run territory script visual "
            f"agents={agents} steps={steps} output_dir={output_dir}"
        ),
    )
    return replay_dir


def _run_coverage_demo(output_dir: Path, agents: int, steps: int) -> Path:
    from coverage_game import run_coverage_game  # noqa: PLC0415

    with patch("coverage_game.MultiAgentEngine", _FakeEngine):
        result = run_coverage_game(
            scene="FloorPlan201",
            agent_count=agents,
            steps=steps,
            model="mock",
            output_dir=str(output_dir),
        )
    replay_dir = Path(result["output_dir"])
    _generate_report(
        replay_dir,
        rerun_command=(
            "just task::run coverage script visual "
            f"agents={agents} steps={steps} output_dir={output_dir}"
        ),
    )
    return replay_dir


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--output-dir",
        default="output/demo",
        help="Root directory under which per-case replay folders are written.",
    )
    p.add_argument("--agents", type=int, default=2, help="Number of agents per game")
    p.add_argument("--steps", type=int, default=20, help="Steps per game")
    args = p.parse_args(argv)

    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)

    print(f"[demo] Writing territory replay to {root / 'territory'}")
    territory_dir = _run_territory_demo(root / "territory", args.agents, args.steps)

    print(f"[demo] Writing coverage replay to {root / 'coverage'}")
    coverage_dir = _run_coverage_demo(root / "coverage", args.agents, args.steps)

    compare_out = root / "report_compare.html"
    print(f"[demo] Writing A/B comparison to {compare_out}")
    _compare_reports(
        territory_dir,
        coverage_dir,
        output_path=compare_out,
        rerun_command=(
            "just task::run territory script visual "
            f"agents={args.agents} steps={args.steps} output_dir={root / 'territory'} && "
            "just task::run coverage script visual "
            f"agents={args.agents} steps={args.steps} output_dir={root / 'coverage'}"
        ),
    )

    print(f"[demo] Writing landing index to {root / 'index.html'}")
    index_out = _write_index(root, include_smoke=False)

    print("[demo] Done. Reports:")
    print(f"  - {territory_dir / 'report.html'}")
    print(f"  - {coverage_dir / 'report.html'}")
    print(f"  - {compare_out}")
    print(f"  - {index_out}")


if __name__ == "__main__":
    main()
