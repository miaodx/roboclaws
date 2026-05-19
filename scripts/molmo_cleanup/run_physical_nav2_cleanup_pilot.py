#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from roboclaws.molmo_cleanup.nav2_adapter import (
    DirectNav2Adapter,
    Nav2ActionResult,
    Nav2Goal,
)
from roboclaws.molmo_cleanup.physical_nav2_pilot import run_physical_nav2_cleanup_pilot


class DeterministicNav2Client:
    def __init__(self, status: str) -> None:
        self.status = status

    def navigate_to_pose(self, goal: Nav2Goal) -> Nav2ActionResult:
        if self.status == "succeeded":
            return Nav2ActionResult(status="succeeded", final_pose=goal.pose, elapsed_s=0.1)
        if self.status == "timeout":
            return Nav2ActionResult(
                status="timeout",
                final_pose=goal.pose,
                message="deterministic pilot timeout",
                elapsed_s=goal.timeout_s,
            )
        return Nav2ActionResult(
            status="failed",
            final_pose=goal.pose,
            failure_type="deterministic_nav2_failure",
            message="deterministic pilot failure",
            elapsed_s=0.1,
        )

    def cancel(self, goal_id: str) -> Nav2ActionResult:
        return Nav2ActionResult(
            status="canceled",
            failure_type="cancel_requested",
            message=f"cancel accepted for {goal_id}",
            cancel_accepted=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the first physical Nav2 cleanup navigation/perception pilot."
    )
    parser.add_argument(
        "--map-bundle-dir",
        type=Path,
        required=True,
        help="Prebuilt Nav2 map bundle directory to load and snapshot.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/molmo/physical-nav2-pilot"),
        help="Root output directory for timestamped pilot artifacts.",
    )
    parser.add_argument("--run-dir", type=Path, help="Exact output run directory.")
    parser.add_argument("--robot-profile-id", default="rby1m")
    parser.add_argument(
        "--mock-nav2-status",
        choices=("succeeded", "timeout", "failed"),
        default="succeeded",
        help=(
            "Deterministic Nav2 client status. Replace the client in Python for a "
            "real ROS/Nav2 run."
        ),
    )
    args = parser.parse_args()

    run_dir = args.run_dir or args.output_dir / _stamp()
    adapter = DirectNav2Adapter(
        DeterministicNav2Client(args.mock_nav2_status),
        operator_stop_channel_configured=True,
    )
    result = run_physical_nav2_cleanup_pilot(
        run_dir=run_dir,
        map_bundle_dir=args.map_bundle_dir,
        adapter=adapter,
        robot_profile_id=args.robot_profile_id,
        backend_name=f"deterministic_nav2_{args.mock_nav2_status}",
    )
    print(json.dumps({"run_dir": str(run_dir), "status": result["cleanup_status"]}, indent=2))
    return 0


def _stamp() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
