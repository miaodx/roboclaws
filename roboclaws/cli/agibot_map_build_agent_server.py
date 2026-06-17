#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

from roboclaws.household.agibot_map_build_mcp_server import (
    AGIBOT_MAP_BUILD_POLICY,
    DEFAULT_HOST,
    DEFAULT_PORT,
    MCP_SERVER_NAME,
    make_agibot_map_build_mcp,
)
from roboclaws.household.profiles import (
    CAMERA_GROUNDED_LABELS_LANE,
    camera_labeler_names,
    evidence_lane_names,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expose Agibot intent=map-build tools to Codex or another MCP agent."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--context-json", type=Path, required=True)
    parser.add_argument("--policy", default=AGIBOT_MAP_BUILD_POLICY)
    parser.add_argument(
        "--task",
        default="Build a Runtime Metric Map from Agibot G2 public navigation and camera evidence.",
    )
    parser.add_argument("--runner-python")
    parser.add_argument("--runner-script", type=Path)
    parser.add_argument("--agibot-map-artifact-dir", type=Path)
    parser.add_argument("--real-movement-enabled", action="store_true")
    parser.add_argument(
        "--evidence-lane",
        choices=evidence_lane_names(),
        default=CAMERA_GROUNDED_LABELS_LANE,
    )
    parser.add_argument(
        "--camera-labeler",
        choices=camera_labeler_names(),
        default="grounding-dino",
    )
    parser.add_argument(
        "--visual-grounding-timeout-s",
        type=float,
        help="Timeout for External Visual Grounding Service requests.",
    )
    return parser.parse_args(argv)


def default_output_dir(policy: str) -> Path:
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M%S")
    return Path("output") / "agibot" / "map-build-agent" / policy / stamp


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_dir = args.output_dir or default_output_dir(args.policy)
    server = make_agibot_map_build_mcp(
        run_dir=run_dir,
        context_json=args.context_json,
        host=args.host,
        port=args.port,
        policy=args.policy,
        task_prompt=args.task,
        runner_python=args.runner_python,
        runner_script=args.runner_script,
        agibot_map_artifact_dir=args.agibot_map_artifact_dir,
        real_movement_enabled=args.real_movement_enabled,
        evidence_lane=args.evidence_lane,
        visual_grounding_pipeline_id=args.camera_labeler,
        visual_grounding_timeout_s=args.visual_grounding_timeout_s,
    )
    url = f"http://{args.host}:{args.port}/mcp"
    print("\nAgibot intent=map-build MCP server is ready.")
    print(f"MCP URL      : {url}")
    print(f"Artifacts    : {run_dir}")
    print(f"Policy label : {args.policy}")
    print(f"MCP server   : {MCP_SERVER_NAME}")
    print(f"Movement     : {'enabled' if args.real_movement_enabled else 'dry-run'}")
    print("\nAgent task:")
    print("  Call metric_map first and use public map anchors plus observations.")
    print("  Navigate only to public waypoint ids, observe with head_color, then call done.")
    print("  Do not call static_fixture_projection, raw Agibot GDK tools, or invent coordinates.\n")
    sys.stdout.flush()

    try:
        thread = server.run_in_thread()
        while thread.is_alive() and not server.done_event.is_set():
            time.sleep(0.25)
    except KeyboardInterrupt:
        return 130
    finally:
        server.close()

    summary = {
        "run_dir": str(run_dir),
        "run_result": str(run_dir / "run_result.json"),
        "report": str(run_dir / "report.html"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
