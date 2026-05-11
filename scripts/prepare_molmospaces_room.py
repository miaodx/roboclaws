#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario, write_scenario_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a deterministic MolmoSpaces cleanup room.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = write_scenario_bundle(args.output_dir, build_cleanup_scenario(seed=args.seed))
    print(f"scenario: {paths['scenario']}")
    print(f"private_manifest: {paths['private_manifest']}")


if __name__ == "__main__":
    main()
