#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.agibot_contract_rehearsal import (  # noqa: E402
    RUNTIME_FIXTURE,
    RUNTIME_MOLMOSPACES_SUBPROCESS,
    run_molmospaces_agibot_contract_rehearsal,
)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_dir = args.run_dir or args.output_dir / _stamp()
    result = run_molmospaces_agibot_contract_rehearsal(
        run_dir=run_dir,
        seed=args.seed,
        generated_mess_count=args.generated_mess_count,
        runtime=args.runtime,
        waypoint_id=args.waypoint_id,
        molmospaces_python=args.molmospaces_python,
        include_robot=args.include_robot,
        robot_name=args.robot_name,
    )
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "status": result["cleanup_status"],
                "confidence_layer": result["confidence_layer"],
                "runtime": result["runtime"],
                "simulated": result["simulated"],
                "physical_robot": result["physical_robot"],
                "report": str(run_dir / "report.html"),
                "runtime_export": str(run_dir / "runtime" / "runtime_export.json"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the MolmoSpaces Agibot Contract Rehearsal: Agibot-shaped "
            "preflight artifacts, simulated observe, simulated waypoint "
            "navigation, and visibly blocked manipulation."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/agibot/molmospaces-contract-rehearsal"),
        help="Root output directory for timestamped rehearsal artifacts.",
    )
    parser.add_argument("--run-dir", type=Path, help="Exact output run directory.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generated-mess-count", type=int, default=5)
    parser.add_argument("--waypoint-id", help="Waypoint id to use for simulated navigation.")
    parser.add_argument(
        "--runtime",
        choices=(RUNTIME_FIXTURE, RUNTIME_MOLMOSPACES_SUBPROCESS),
        default=RUNTIME_FIXTURE,
        help=(
            "fixture is CI-safe and dependency-light; molmospaces-subprocess uses "
            "the real MolmoSpaces subprocess backend when the optional runtime is installed."
        ),
    )
    parser.add_argument(
        "--molmospaces-python",
        type=Path,
        help="Python executable for the optional MolmoSpaces subprocess runtime.",
    )
    parser.add_argument(
        "--include-robot",
        action="store_true",
        help="When using molmospaces-subprocess, include the configured robot in the scene.",
    )
    parser.add_argument("--robot-name", default="rby1m")
    return parser.parse_args(argv)


def _stamp() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
