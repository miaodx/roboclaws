#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.maps.spatial_contract import (  # noqa: E402
    ALIGNMENT_STATUS_CANDIDATE,
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
    b1_overlay = _is_b1_room_semantic_bundle(bundle_dir, semantics)
    alignment_status = ALIGNMENT_STATUS_CANDIDATE if b1_overlay else ALIGNMENT_STATUS_NATIVE
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
    if b1_overlay:
        _attach_b1_correspondence(bundle_dir, semantics)
    semantics_path.write_text(
        json.dumps(semantics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_b1_room_semantic_bundle(bundle_dir: Path, semantics: dict[str, Any]) -> bool:
    if Path(bundle_dir).name == "b1-map12-room-semantics":
        return True
    provenance = (
        semantics.get("provenance") if isinstance(semantics.get("provenance"), dict) else {}
    )
    return bool(provenance.get("room_semantic_overlay_schema"))


def _attach_b1_correspondence(bundle_dir: Path, semantics: dict[str, Any]) -> None:
    overlay_path = Path(bundle_dir) / "room_semantic_overlay.json"
    if not overlay_path.is_file():
        return
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    by_partition = {
        str(item.get("asset_partition_id") or ""): item
        for item in overlay.get("scene_map_correspondence_v1") or []
        if isinstance(item, dict)
    }
    for room in semantics.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        match = by_partition.get(str(room.get("asset_partition_id") or ""))
        if not match:
            continue
        room["scene_map_correspondence"] = {
            "schema": "scene_map_correspondence_v1",
            "asset_partition_id": str(match.get("asset_partition_id") or ""),
            "navigation_area_id": str(match.get("navigation_area_id") or ""),
            "alignment_status": str(
                match.get("alignment_status")
                or room.get("alignment_status")
                or ALIGNMENT_STATUS_CANDIDATE
            ),
            "transform_source": str(match.get("transform_source") or ""),
            "evidence_artifacts": list(match.get("evidence_artifacts") or []),
            "map_polygon_provided": "map_polygon" in match,
        }


if __name__ == "__main__":
    raise SystemExit(main())
