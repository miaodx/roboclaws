#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_DRAFT = Path("docs/status/active/b1-map12-scene-correspondences-draft.json")
DEFAULT_OUTPUT = Path(
    "output/b1-map12/manual-draft-alignment/b1-map12-scene-correspondences.verification-only.json"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create an explicit verification-only accepted manifest from the manual B1/Map12 "
            "draft anchors. This is not the final accepted correspondence asset."
        )
    )
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_verification_manifest(
        json.loads(args.draft.read_text(encoding="utf-8")),
        source_draft=args.draft,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": payload.get("schema"),
                "verification_only": payload["verification_only"],
                "accepted_anchor_count": len(payload["anchors"]),
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


def build_verification_manifest(
    draft: dict[str, Any], *, source_draft: Path = DEFAULT_DRAFT
) -> dict[str, Any]:
    anchors = [
        dict(anchor)
        for anchor in draft.get("anchors") or []
        if isinstance(anchor, dict) and has_explicit_picks(anchor)
    ]
    if not anchors:
        raise ValueError("manual draft has no anchors with explicit map_xy and scene_xyz picks")
    promoted = []
    for index, anchor in enumerate(anchors, start=1):
        item = dict(anchor)
        item["review_status"] = "accepted"
        item["anchor_role"] = "alignment"
        item["confidence"] = item.get("confidence") or 0.8
        evidence = dict(item.get("evidence") or {})
        evidence["verification_note"] = (
            "Verification-only promotion from proposed manual draft anchors. "
            "These anchors verify map-scene geometry only, not room semantics."
        )
        item["evidence"] = evidence
        promoted.append(item)
    return {
        "schema": draft.get("schema"),
        "source_map_frame": draft.get("source_map_frame"),
        "target_scene_frame": draft.get("target_scene_frame"),
        "bbox_seed_policy": draft.get("bbox_seed_policy"),
        "scene_projection_policy": draft.get("scene_projection_policy"),
        "verification_only": True,
        "source_draft": source_draft.as_posix(),
        "notes": [
            "Generated for local residual verification after automatic alignment failed.",
            "Do not commit this as assets/maps/b1-map12-scene-correspondences.json.",
            "Do not use alignment anchors as room semantic evidence.",
        ],
        "anchors": promoted,
    }


def has_explicit_picks(anchor: dict[str, Any]) -> bool:
    return (
        isinstance(anchor.get("map_xy"), list)
        and len(anchor["map_xy"]) == 2
        and isinstance(anchor.get("scene_xyz"), list)
        and len(anchor["scene_xyz"]) == 3
    )


if __name__ == "__main__":
    raise SystemExit(main())
