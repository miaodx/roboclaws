#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.molmo_cleanup.planner_proof_bundle_runner_checker import (
    assert_runner_result as _assert_runner_result,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MolmoSpaces planner proof bundle runner artifacts."
    )
    parser.add_argument("path", type=Path, help="proof_bundle_run_manifest.json or output dir")
    parser.add_argument("--require-proof-outputs", action="store_true")
    parser.add_argument("--require-cleanup-rerun-output", action="store_true")
    parser.add_argument("--min-selected-requests", type=int)
    parser.add_argument("--max-selected-requests", type=int)
    parser.add_argument("--require-prior-covered-exclusion", action="store_true")
    parser.add_argument("--require-proof-execution-horizon", action="store_true")
    parser.add_argument("--require-proof-quality", action="store_true")
    parser.add_argument("--require-planner-backed-proof-min-steps", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = args.path / "proof_bundle_run_manifest.json" if args.path.is_dir() else args.path
    data = json.loads(path.read_text(encoding="utf-8"))
    _assert_runner_result(
        data,
        path.parent,
        require_proof_outputs=args.require_proof_outputs,
        require_cleanup_rerun_output=args.require_cleanup_rerun_output,
        min_selected_requests=args.min_selected_requests,
        max_selected_requests=args.max_selected_requests,
        require_prior_covered_exclusion=args.require_prior_covered_exclusion,
        require_proof_execution_horizon=args.require_proof_execution_horizon,
        require_proof_quality=args.require_proof_quality,
        planner_backed_proof_min_steps=args.require_planner_backed_proof_min_steps,
    )
    print(f"molmo-planner-proof-bundle-runner ok: {path}")


if __name__ == "__main__":
    main()
