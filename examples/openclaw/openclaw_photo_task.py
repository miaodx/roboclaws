#!/usr/bin/env python3
"""Photo-task autonomous OpenClaw smoke — the ``walk-the-room-and-photograph-each-chair``
test, automated.

This is the test the operator's been running by hand: open the appliance
Control UI in a browser, type the Chinese prompt below, and watch the
agent walk around taking photos of every chair / sofa. The plumbing
(Gateway + MCP + observe(label=...) + AI2-THOR) is already exercised by
the existing CI integration jobs, but the *behavior* under a complex
multi-target instruction is not. This file lifts that hand-test into a
scriptable form so it can run on push-to-main with ``KIMI_API_KEY``.

Pass criterion is filesystem-grounded — see
``scripts/openclaw/check_photo_task.py`` for the oracle. The agent does not have
to perfectly photograph every chair (real VLMs vary). It has to:

  1. Call ``roboclaws__observe`` with a non-empty ``label`` at least N
     times — each labeled call writes a labeled PNG triple to the
     agent's snapshots dir per SKILL.md, and
  2. Call ``roboclaws__done`` (terminating cleanly rather than running
     the wall-clock out) with a reason that mentions the photographed
     targets.

The kickoff prompt is the operator's verbatim Chinese prompt followed by a
small preamble pointing at the base navigator skill and the task-specific
capture-object-photo skill.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openclaw_nav_autonomous import run_autonomous_navigation  # noqa: E402

# The verbatim hand-test prompt the operator's been typing into the chat.
# Kept Chinese-as-input — this script is the truer reproduction of what
# we've been smoke-testing manually on the appliance.
_OPERATOR_PROMPT_VERBATIM = (
    "麻烦给这个屋子里面的每个沙发以及椅子拍个照片，"
    "走到他们的正前方拍，确保视野中只有一把沙发或者椅子，"
    "所有都拍完后，统一发给我\n"
    "你可能需要走遍这个屋子才能确保都拍到，"
    "注意下 grid map，最好远离障碍物，防止你自己被卡住"
)


def photo_task_kickoff_prompt(max_moves: int) -> str:
    """Compose the kickoff message sent to the agent on this run."""
    return (
        "You are an OpenClaw agent operating an AI2-THOR robot. "
        "Read skills/ai2thor-navigator/SKILL.md for base tool semantics, then "
        "read skills/capture-object-photo/SKILL.md and follow that task skill.\n\n"
        "Use the roboclaws MCP tools named by those skills. For this AI2-THOR "
        "demo, scene_objects and goto are privileged helpers you may use for "
        "efficient photo capture; do not describe them as real-robot perception "
        "or real-robot navigation.\n\n"
        "When you take a photo, call roboclaws__observe with a descriptive label "
        "(e.g. label='sofa-1', 'chair-1'). The labeled observe writes durable "
        "PNGs under the agent workspace; the operator's scorer counts those "
        "files at the end. Do NOT use unlabeled observe for photos — the scorer "
        "ignores the unlabeled latest.*.png files.\n\n"
        f"Move budget: ~{max_moves} physical moves plus the wall-clock cap. "
        "Pace yourself.\n\n"
        "Once every target is photographed, call roboclaws__done with a "
        "reason summarising what you photographed (target labels + counts).\n\n"
        "--- Operator request (do this) ---\n"
        f"{_OPERATOR_PROMPT_VERBATIM}\n"
        "--- end operator request ---"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the autonomous photo-task OpenClaw smoke (real Kimi/VLM).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--scene", default="FloorPlan201")
    parser.add_argument("--max-moves", type=int, default=200)
    # Photo task is more open-ended than bare nav — agents need to
    # circulate, plan, observe-with-label per target. 15 min is the
    # local hand-test sweet spot.
    parser.add_argument("--wall-budget", type=float, default=900.0)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Reuse an already-running Gateway instead of bootstrapping/removing the container.",
    )
    return parser.parse_args(argv)


def _default_output_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M")
    return Path(f"output/openclaw-photo-task/{stamp}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    args = _parse_args()
    output_dir = args.output_dir or _default_output_dir()

    result = run_autonomous_navigation(
        scene=args.scene,
        max_moves=args.max_moves,
        wall_budget=args.wall_budget,
        output_dir=output_dir,
        skip_bootstrap=args.skip_bootstrap,
        kickoff_prompt_builder=photo_task_kickoff_prompt,
    )
    print(f"terminated_by: {result['terminated_by']}")
    print(f"wallclock_s: {result['wallclock_s']:.1f}")
    print(f"artifacts at {result['output_dir']}")


if __name__ == "__main__":
    main()
