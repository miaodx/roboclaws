#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.grasp_generation_setup import (  # noqa: E402
    load_availability_preflight_from_manifest,
    run_grasp_generation_setup,
)
from roboclaws.molmo_cleanup.subprocess_backend import DEFAULT_MOLMOSPACES_PYTHON  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set up local MolmoSpaces rigid grasp-generation prerequisites."
    )
    parser.add_argument("--molmospaces-python", type=Path, default=DEFAULT_MOLMOSPACES_PYTHON)
    parser.add_argument("--molmospaces-root", type=Path)
    parser.add_argument(
        "--preflight-manifest",
        type=Path,
        help="Proof-bundle manifest containing grasp_cache_availability_preflight.",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-python-prereqs", action="store_true")
    parser.add_argument("--skip-manifold", action="store_true")
    parser.add_argument("--parallel-jobs", type=int)
    parser.add_argument("--command-timeout-s", type=float, default=900.0)
    parser.add_argument("--preflight-timeout-s", type=float, default=30.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    availability_preflight = (
        load_availability_preflight_from_manifest(args.preflight_manifest)
        if args.preflight_manifest
        else None
    )
    result = run_grasp_generation_setup(
        molmospaces_python=args.molmospaces_python,
        molmospaces_root=args.molmospaces_root,
        availability_preflight=availability_preflight,
        output_dir=args.output_dir,
        include_python_prereqs=not args.skip_python_prereqs,
        include_manifold=not args.skip_manifold,
        dry_run=args.dry_run,
        parallel_jobs=args.parallel_jobs,
        command_timeout_s=args.command_timeout_s,
        preflight_timeout_s=args.preflight_timeout_s,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps({"status": result["status"], "output": str(args.output or "")}))


if __name__ == "__main__":
    main()
