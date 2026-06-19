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

from roboclaws.launch.map_bundles import molmospaces_nav2_map_bundle_path  # noqa: E402
from roboclaws.maps.bundle import (  # noqa: E402
    static_landmarks_from_fixture_projection,
    validate_nav2_map_bundle,
    write_nav2_map_bundle,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a Nav2 cleanup map bundle from a public cleanup agent view. "
            "This is a preparation step; live cleanup runs should consume the bundle."
        )
    )
    parser.add_argument("--run-result", type=Path, help="run_result.json with agent_view.")
    parser.add_argument(
        "--agent-view",
        type=Path,
        help="agent_view.json with metric_map and static fixture artifact payload.",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--molmospaces-scene-source",
        help=(
            "MolmoSpaces scene source; selects the canonical output path when "
            "--output-dir is omitted."
        ),
    )
    parser.add_argument(
        "--molmospaces-scene-index",
        type=int,
        help=(
            "MolmoSpaces scene index; selects the canonical output path when "
            "--output-dir is omitted."
        ),
    )
    parser.add_argument(
        "--map-asset-root",
        type=Path,
        help="Asset root for canonical scene output; defaults to assets/maps.",
    )
    parser.add_argument("--no-validate", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if bool(args.run_result) == bool(args.agent_view):
        raise SystemExit("provide exactly one of --run-result or --agent-view")
    output_dir = _output_dir(args)
    agent_view = _load_agent_view(run_result=args.run_result, agent_view=args.agent_view)
    metric_map = (
        agent_view.get("metric_map") if isinstance(agent_view.get("metric_map"), dict) else {}
    )
    static_fixture_projection = (
        agent_view.get("static_fixture_projection")
        if isinstance(agent_view.get("static_fixture_projection"), dict)
        else {}
    )
    if not metric_map or not static_fixture_projection:
        raise SystemExit("agent view must contain metric_map and static_fixture_projection")
    snapshot = write_nav2_map_bundle(
        output_dir,
        metric_map=metric_map,
        static_landmarks=static_landmarks_from_fixture_projection(static_fixture_projection),
    )
    if not args.no_validate:
        validate_nav2_map_bundle(output_dir).raise_for_errors()
    print(
        "nav2-map-bundle exported: "
        f"{output_dir} map_id={snapshot.get('map_id')} "
        f"parameter_hash={snapshot.get('parameter_hash')}"
    )


def _output_dir(args: argparse.Namespace) -> Path:
    if args.output_dir is not None:
        return args.output_dir
    if args.molmospaces_scene_source is None or args.molmospaces_scene_index is None:
        raise SystemExit(
            "provide --output-dir or both --molmospaces-scene-source and --molmospaces-scene-index"
        )
    return molmospaces_nav2_map_bundle_path(
        scene_source=args.molmospaces_scene_source,
        scene_index=args.molmospaces_scene_index,
        asset_root=args.map_asset_root or Path("assets") / "maps",
    )


def _load_agent_view(*, run_result: Path | None, agent_view: Path | None) -> dict[str, Any]:
    if run_result is not None:
        data = _load_json_source(run_result, label="run result")
        if not isinstance(data, dict):
            raise SystemExit(
                f"run result payload must be a JSON object: {run_result} "
                f"(got {type(data).__name__})"
            )
        loaded = data.get("agent_view")
    else:
        assert agent_view is not None
        loaded = _load_json_source(agent_view, label="agent view")
    if not isinstance(loaded, dict):
        raise SystemExit("agent view payload must be a JSON object")
    return loaded


def _load_json_source(path: Path, *, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"{label} source is unreadable: {path}: {type(exc).__name__}: {exc}"
        ) from exc


if __name__ == "__main__":
    main()
