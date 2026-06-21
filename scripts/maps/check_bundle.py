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

from roboclaws.maps.bundle import (  # noqa: E402
    validate_base_navigation_map_v1_bundle,
    validate_nav2_map_bundle,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a prebuilt Base Navigation Map v1 bundle before agent runtime."
    )
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("--json", action="store_true", help="Print machine-readable validation.")
    parser.add_argument(
        "--legacy-nav2",
        action="store_true",
        help="Validate only the older broad Nav2 bundle contract. Not valid for product launch.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = (
        validate_nav2_map_bundle(args.bundle_dir)
        if args.legacy_nav2
        else validate_base_navigation_map_v1_bundle(args.bundle_dir)
    )
    label = "legacy-nav2-map-bundle" if args.legacy_nav2 else "base-navigation-map-v1-bundle"
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    elif result.ok:
        meta = result.metadata
        print(
            f"{label} ok: "
            f"{args.bundle_dir} "
            f"rooms={meta.get('room_count', 0)} "
            f"fixtures={meta.get('static_landmark_count', 0)} "
            f"waypoints={meta.get('waypoint_count', 0)}"
        )
    else:
        print(f"{label} invalid: {args.bundle_dir}", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
