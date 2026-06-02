#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.grasp_cache_generation import (  # noqa: E402
    load_generation_preflight_from_manifest,
)
from roboclaws.household.grasp_initial_contact_diagnostics import (  # noqa: E402
    run_grasp_initial_contact_diagnostics,
)
from roboclaws.household.report import (  # noqa: E402
    render_grasp_initial_contact_diagnostics_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run MolmoSpaces rigid-grasp initial contact/approach diagnostics."
    )
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--candidate-grasps-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--molmospaces-python", type=Path)
    parser.add_argument("--max-candidates", type=int, default=24)
    parser.add_argument("--approach-steps", type=int, default=30)
    parser.add_argument("--post-approach-steps", type=int, default=300)
    parser.add_argument("--close-steps", type=int, default=300)
    parser.add_argument("--timeout-s", type=float, default=900.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_grasp_initial_contact_diagnostics(
        generation_preflight=load_generation_preflight_from_manifest(args.preflight_manifest),
        output_dir=args.output_dir,
        candidate_grasps_path=args.candidate_grasps_path,
        molmospaces_python=args.molmospaces_python,
        max_candidates=args.max_candidates,
        approach_steps=args.approach_steps,
        post_approach_steps=args.post_approach_steps,
        close_steps=args.close_steps,
        timeout_s=args.timeout_s,
        dry_run=args.dry_run,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    report = render_grasp_initial_contact_diagnostics_report(
        output_dir=args.output_dir,
        result=result,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(args.output or ""),
                "report": str(report),
            }
        )
    )


if __name__ == "__main__":
    main()
