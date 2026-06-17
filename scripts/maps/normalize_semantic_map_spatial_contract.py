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

from roboclaws.maps.spatial_contract import (  # noqa: E402
    ALIGNMENT_STATUS_NATIVE,
    GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
    POLYGON_ROLE_NAVIGATION_AREA,
    normalize_spatial_rooms,
    source_frame_spatial_contract,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add first-slice source-frame spatial contract metadata to map bundles."
    )
    parser.add_argument("bundle_dirs", type=Path, nargs="+")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for bundle_dir in args.bundle_dirs:
        _normalize_bundle(bundle_dir)
        print(f"normalized spatial contract: {bundle_dir}")
    return 0


def _normalize_bundle(bundle_dir: Path) -> None:
    semantics_path = Path(bundle_dir) / "semantics.json"
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    if not isinstance(semantics, dict):
        raise SystemExit(f"semantics.json must be a JSON object: {semantics_path}")
    frame_id = str((semantics.get("frame_ids") or {}).get("map") or "map")
    alignment_status = ALIGNMENT_STATUS_NATIVE
    semantics["spatial_contract"] = source_frame_spatial_contract(
        frame_id=frame_id,
        alignment_status=alignment_status,
    )
    semantics["display_frame"] = None
    semantics["rooms"] = normalize_spatial_rooms(
        semantics.get("rooms") or [],
        frame_id=frame_id,
        polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
        geometry_source=GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
        alignment_status=alignment_status,
        semantic_label_status=alignment_status,
    )
    semantics_path.write_text(
        json.dumps(semantics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
