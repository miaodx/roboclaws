#!/usr/bin/env python3
"""Filesystem-grounded oracle for the photo-task smoke run.

Runs against the artifact dir produced by ``examples/openclaw_photo_task.py``.
We deliberately do **not** judge how well the agent photographed each
target — real VLMs vary too much for that to be a stable CI signal. We
only check the contracts the agent actually controls:

  1. The agent emitted ≥ ``--min-targets`` distinct labeled snapshots.
     Per ``skills/ai2thor-navigator/SKILL.md``, ``observe(label="X")``
     writes ``<label>-NNN.fpv.png`` etc. into the per-agent snapshots dir.
     Distinct ``X`` prefixes ⇒ distinct photographed targets.
  2. The agent terminated cleanly via ``roboclaws__done`` rather than
     exhausting wall-clock or erroring out. ``run_result.json``'s
     ``terminated_by`` carries this.

Both must pass for exit 0. Anything else exits 1 with a one-line reason.

Use:

    python scripts/check_photo_task.py --run-dir output/openclaw-photo-task/<stamp>
    python scripts/check_photo_task.py --run-dir <dir> --min-targets 2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_LABELED_PNG_RE = re.compile(r"^(?P<label>.+?)-\d+\.(?:fpv|map|chase)\.png$")
# These are the unlabeled "live viewer" PNGs every observe writes — stable
# names so the make chat-view tab can poll them. They must NOT count
# toward the labeled-snapshot tally.
_UNLABELED_NAMES = {"latest.fpv.png", "latest.map.png", "latest.chase.png"}


def _distinct_labels(snapshots_dir: Path) -> set[str]:
    if not snapshots_dir.is_dir():
        return set()
    labels: set[str] = set()
    for entry in snapshots_dir.iterdir():
        if not entry.is_file():
            continue
        if entry.name in _UNLABELED_NAMES:
            continue
        match = _LABELED_PNG_RE.match(entry.name)
        if match:
            labels.add(match.group("label"))
    return labels


def _terminated_by(run_dir: Path) -> str | None:
    payload_path = run_dir / "run_result.json"
    if not payload_path.is_file():
        return None
    try:
        return json.loads(payload_path.read_text(encoding="utf-8")).get("terminated_by")
    except (json.JSONDecodeError, OSError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score a photo-task run by labeled-snapshot count + termination reason.",
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--agent-id", type=int, default=0)
    parser.add_argument(
        "--min-targets",
        type=int,
        default=2,
        help=(
            "Minimum distinct labeled snapshots required. Default 2 — "
            "FloorPlan201 has multiple chairs/sofas, but real VLMs miss "
            "some, so 2 is a conservative pass bar that still catches "
            "a regression where the agent doesn't photograph anything."
        ),
    )
    args = parser.parse_args(argv)

    run_dir: Path = args.run_dir.resolve()
    snapshots_dir = run_dir / "snapshots" / f"agent-{args.agent_id}"
    labels = _distinct_labels(snapshots_dir)
    terminated = _terminated_by(run_dir)

    print(f"run_dir         : {run_dir}")
    print(f"snapshots_dir   : {snapshots_dir}")
    print(f"distinct labels : {sorted(labels)} (count={len(labels)})")
    print(f"terminated_by   : {terminated}")
    print(f"min-targets     : {args.min_targets}")

    failures: list[str] = []
    if len(labels) < args.min_targets:
        failures.append(
            f"only {len(labels)} distinct labeled snapshot(s) — need ≥ {args.min_targets}"
        )
    if terminated != "agent_done":
        failures.append(
            f"terminated_by={terminated!r} — expected 'agent_done' "
            "(agent should call roboclaws__done, not run out of wall-clock)"
        )

    if failures:
        print("\nFAIL:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
