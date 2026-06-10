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

from roboclaws.household.agibot_map_bundle import write_agibot_nav2_map_bundle  # noqa: E402
from roboclaws.household.agibot_map_defaults import (  # noqa: E402
    DEFAULT_AGIBOT_CONTEXT_JSON,
    DEFAULT_AGIBOT_MAP_ARTIFACT_DIR,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the Agibot robot_map_12 artifact as a Nav2-shaped map bundle."
    )
    parser.add_argument("--source-map-dir", type=Path, default=DEFAULT_AGIBOT_MAP_ARTIFACT_DIR)
    parser.add_argument("--context-json", type=Path, default=DEFAULT_AGIBOT_CONTEXT_JSON)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    snapshot = write_agibot_nav2_map_bundle(
        source_map_dir=args.source_map_dir,
        context_json=args.context_json,
        bundle_dir=args.output_dir,
    )
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
