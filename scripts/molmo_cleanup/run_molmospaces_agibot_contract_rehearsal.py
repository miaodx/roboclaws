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

from roboclaws.household.agibot_contract_rehearsal import (  # noqa: E402
    REHEARSAL_MODE_CLEANUP_ACTIONS,
    REHEARSAL_MODE_CONTRACT,
    RUNTIME_FIXTURE,
    RUNTIME_MOLMOSPACES_SUBPROCESS,
    run_molmospaces_agibot_contract_rehearsal,
    run_molmospaces_agibot_prehardware_rehearsal,
)
from roboclaws.household.profiles import camera_labeler_to_visual_grounding_pipeline  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_dir = args.run_dir or args.output_dir / _stamp()
    if args.flow == "prehardware":
        visual_grounding = (
            camera_labeler_to_visual_grounding_pipeline(args.camera_labeler)
            if args.camera_labeler
            else args.visual_grounding
        )
        result = run_molmospaces_agibot_prehardware_rehearsal(
            run_dir=run_dir,
            intent=args.intent,
            profile=args.profile,
            task_prompt=args.task_prompt,
            seed=args.seed,
            generated_mess_count=args.generated_mess_count,
            runtime=args.runtime,
            molmospaces_python=args.molmospaces_python,
            include_robot=args.include_robot,
            robot_name=args.robot_name,
            cleanup_object_count=args.cleanup_object_count,
            record_robot_views=args.record_robot_views,
            context_json=args.context_json,
            agibot_map_artifact_dir=args.agibot_map_artifact_dir,
            camera_labeler=args.camera_labeler,
            visual_grounding=visual_grounding,
            visual_grounding_base_url=args.visual_grounding_base_url,
            visual_grounding_timeout_s=args.visual_grounding_timeout_s,
        )
    else:
        result = run_molmospaces_agibot_contract_rehearsal(
            run_dir=run_dir,
            seed=args.seed,
            generated_mess_count=args.generated_mess_count,
            runtime=args.runtime,
            waypoint_id=args.waypoint_id,
            molmospaces_python=args.molmospaces_python,
            include_robot=args.include_robot,
            robot_name=args.robot_name,
            rehearsal_mode=args.rehearsal_mode,
            cleanup_object_count=args.cleanup_object_count,
            record_robot_views=args.record_robot_views,
            context_json=args.context_json,
            agibot_map_artifact_dir=args.agibot_map_artifact_dir,
        )
    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "status": result["cleanup_status"],
                "confidence_layer": result["confidence_layer"],
                "flow": args.flow,
                "intent": args.intent,
                "rehearsal_mode": result.get("rehearsal_mode", ""),
                "runtime": result["runtime"],
                "simulated": result["simulated"],
                "physical_robot": result["physical_robot"],
                "robot_view_steps": len(result.get("robot_view_steps") or []),
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
        "--flow",
        choices=("contract-rehearsal", "prehardware"),
        default="contract-rehearsal",
        help=(
            "contract-rehearsal runs the original one-waypoint contract smoke; "
            "prehardware runs the minimal-map online semantic-map/cleanup rehearsal."
        ),
    )
    parser.add_argument(
        "--intent",
        choices=("cleanup", "map-build", "open-ended"),
        default="cleanup",
        help="Public household intent to rehearse when --flow prehardware is selected.",
    )
    parser.add_argument(
        "--profile",
        choices=(
            "world-public-labels",
            "camera-raw-fpv",
            "camera-grounded-labels",
        ),
        default="camera-grounded-labels",
        help="Evidence lane for --flow prehardware.",
    )
    parser.add_argument(
        "--task-prompt",
        help=(
            "Override the task prompt recorded by the prehardware flow. Useful for "
            "testing open-ended evidence-refresh wording before a live G2 run."
        ),
    )
    parser.add_argument(
        "--camera-labeler",
        help=(
            "Public camera labeler for camera-grounded-labels. This is translated "
            "to the internal Visual Grounding Service pipeline id."
        ),
    )
    parser.add_argument(
        "--visual-grounding",
        default="grounding-dino",
        help=(
            "Internal Visual Grounding Service pipeline id for --flow prehardware. "
            "Prefer --camera-labeler on public routes."
        ),
    )
    parser.add_argument(
        "--visual-grounding-base-url",
        help="External Visual Grounding Service base URL for --flow prehardware.",
    )
    parser.add_argument(
        "--visual-grounding-timeout-s",
        type=float,
        help="External Visual Grounding Service timeout for --flow prehardware.",
    )
    parser.add_argument(
        "--rehearsal-mode",
        choices=(REHEARSAL_MODE_CONTRACT, REHEARSAL_MODE_CLEANUP_ACTIONS),
        default=REHEARSAL_MODE_CONTRACT,
        help=(
            "contract blocks manipulation; cleanup-actions performs opt-in "
            "simulated pick/place cleanup actions with explicit simulated labels."
        ),
    )
    parser.add_argument(
        "--cleanup-object-count",
        type=int,
        default=2,
        help="Maximum public observed cleanup candidates to act on in cleanup-actions mode.",
    )
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
    parser.add_argument(
        "--context-json",
        type=Path,
        help=(
            "Optional completed Agibot map context to record as reference evidence. "
            "It is not used as the MolmoSpaces scene source."
        ),
    )
    parser.add_argument(
        "--agibot-map-artifact-dir",
        type=Path,
        help=(
            "Optional Agibot map artifact root to record alongside --context-json "
            "for comparison-only evidence."
        ),
    )
    parser.add_argument(
        "--record-robot-views",
        action="store_true",
        help=(
            "Capture FPV/chase/map robot-view timeline frames. Requires "
            "--runtime molmospaces-subprocess --include-robot."
        ),
    )
    return parser.parse_args(argv)


def _stamp() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
