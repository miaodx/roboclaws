#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from roboclaws.maps.room_semantics import (  # noqa: E402
    apply_room_semantic_overlay_to_bundle,
    build_scene_room_semantic_overlay,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a public room semantic overlay from scene-engine Gaussian/USD "
            "asset partitions, with optional Nav2 bundle application."
        )
    )
    parser.add_argument("scene_root", type=Path)
    parser.add_argument("--source-bundle-dir", type=Path)
    parser.add_argument("--overrides-json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--apply-to-bundle",
        type=Path,
        help=(
            "Optional output bundle dir. Copies --source-bundle-dir and replaces "
            "public room labels."
        ),
    )
    parser.add_argument("--no-validate-bundle", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    overrides = (
        json.loads(args.overrides_json.read_text(encoding="utf-8"))
        if args.overrides_json is not None
        else None
    )
    overlay = build_scene_room_semantic_overlay(
        args.scene_root,
        source_bundle_dir=args.source_bundle_dir,
        overrides=overrides,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    application = None
    if args.apply_to_bundle is not None:
        if args.source_bundle_dir is None:
            raise SystemExit("--apply-to-bundle requires --source-bundle-dir")
        application = apply_room_semantic_overlay_to_bundle(
            args.source_bundle_dir,
            args.apply_to_bundle,
            overlay,
            validate=not args.no_validate_bundle,
        )
    print(
        "scene room semantic overlay exported: "
        f"{args.output} rooms={overlay['summary']['room_count']} "
        f"review={overlay['summary']['review_count']}"
    )
    if application is not None:
        print(
            "scene room semantic bundle exported: "
            f"{application['output_bundle_dir']} rooms={application['room_count']} "
            f"valid={application['validation']['ok']}"
        )


if __name__ == "__main__":
    main()
