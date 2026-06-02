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

from roboclaws.household.ci_live_reports import utc_timestamp  # noqa: E402
from roboclaws.household.subprocess_backend import (  # noqa: E402
    MolmoSpacesSubprocessBackend,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prewarm the MolmoSpaces scene/robot assets used by live CI cleanup."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--scene-source", default="procthor-10k-val")
    parser.add_argument("--scene-index", type=int, default=0)
    parser.add_argument("--robot-name", default="rby1m")
    parser.add_argument("--generated-mess-count", type=int, default=5)
    parser.add_argument("--record-robot-view", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "prewarm_manifest.json"
    payload: dict[str, Any] = {
        "schema": "molmospaces_ci_asset_prewarm_v1",
        "created_at": utc_timestamp(),
        "status": "dry_run" if args.dry_run else "running",
        "seed": args.seed,
        "scene_source": args.scene_source,
        "scene_index": args.scene_index,
        "robot_name": args.robot_name,
        "generated_mess_count": args.generated_mess_count,
        "cache_roots": {
            "uv": "~/.cache/uv",
            "molmospaces": "~/.cache/molmospaces",
            "molmo_spaces_resources": "~/.cache/molmo-spaces-resources",
        },
    }
    if args.dry_run:
        manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"molmospaces-ci-prewarm dry-run: {manifest_path}")
        return 0

    try:
        backend = MolmoSpacesSubprocessBackend(
            run_dir=args.output_dir,
            seed=args.seed,
            scene_source=args.scene_source,
            scene_index=args.scene_index,
            include_robot=True,
            robot_name=args.robot_name,
            generated_mess_count=args.generated_mess_count,
        )
        payload.update(
            {
                "status": "success",
                "scene_xml": str(backend.scene_xml),
                "runtime": backend.runtime,
                "generated_mess_count_actual": backend.generated_mess_count,
                "metadata_object_count": backend.metadata_object_count,
                "robot": backend.robot,
            }
        )
        if args.record_robot_view:
            view_dir = args.output_dir / "robot_views"
            payload["robot_view"] = backend.write_robot_views(view_dir, label="prewarm")
    except Exception as exc:
        payload["status"] = "failed"
        payload["reason"] = str(exc)
        manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        raise

    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"molmospaces-ci-prewarm ok: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
