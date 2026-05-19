from __future__ import annotations

import json
from pathlib import Path

from roboclaws.molmo_cleanup.nav2_adapter import (
    BLOCKED_CAPABILITY_PROVENANCE,
    NAV2_ACTION_PROVENANCE,
    DirectNav2Adapter,
    Nav2ActionResult,
    Nav2Goal,
)
from roboclaws.molmo_cleanup.physical_nav2_pilot import (
    BLOCKED_MANIPULATION_TOOLS,
    run_physical_nav2_cleanup_pilot,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PREBUILT_BUNDLE = REPO_ROOT / "assets" / "maps" / "molmo-cleanup-default-7"


class RecordingNav2Client:
    def __init__(self) -> None:
        self.goals: list[Nav2Goal] = []
        self.canceled: list[str] = []

    def navigate_to_pose(self, goal: Nav2Goal) -> Nav2ActionResult:
        self.goals.append(goal)
        return Nav2ActionResult(status="succeeded", final_pose=goal.pose, elapsed_s=0.05)

    def cancel(self, goal_id: str) -> Nav2ActionResult:
        self.canceled.append(goal_id)
        return Nav2ActionResult(status="canceled", cancel_accepted=True)


def test_physical_nav2_pilot_attempts_map_waypoints_and_blocks_manipulation(
    tmp_path: Path,
) -> None:
    client = RecordingNav2Client()
    adapter = DirectNav2Adapter(client, operator_stop_channel_configured=True)

    run_result = run_physical_nav2_cleanup_pilot(
        run_dir=tmp_path,
        map_bundle_dir=PREBUILT_BUNDLE,
        adapter=adapter,
    )

    metric_map = run_result["agent_view"]["metric_map"]
    fixture_hints = run_result["agent_view"]["fixture_hints"]
    fixtures = [
        fixture
        for room in fixture_hints["rooms"]
        for fixture in room["fixtures"]
        if fixture.get("fixture_id")
    ]
    readiness = run_result["real_robot_readiness"]
    physical = run_result["physical_nav2_pilot"]
    report_text = (tmp_path / "report.html").read_text(encoding="utf-8")
    persisted = json.loads((tmp_path / "run_result.json").read_text(encoding="utf-8"))

    assert run_result["cleanup_profile"] == "real_robot_cleanup_v1"
    assert run_result["primitive_provenance"] == NAV2_ACTION_PROVENANCE
    assert readiness["status"] == "physical_navigation_pilot_complete"
    assert readiness["physical_navigation_pilot"] is True
    assert readiness["physical_cleanup_ready"] is False
    assert readiness["map_bundle_snapshot_present"] is True
    assert readiness["robot_profile_id"] == "rby1m"
    assert readiness["inspection_waypoint_attempt_count"] == len(metric_map["inspection_waypoints"])
    assert readiness["fixture_preferred_waypoint_attempt_count"] == len(fixtures)
    assert readiness["observed_reached_waypoint_count"] == (
        len(metric_map["inspection_waypoints"]) + len(fixtures)
    )
    assert readiness["navigation_backend_summary"][NAV2_ACTION_PROVENANCE] == len(client.goals)
    assert readiness["manipulation_blocked"] is True
    assert {goal.source for goal in client.goals} == {
        "inspection_waypoint",
        "fixture_preferred_waypoint",
    }
    assert all(item["ok"] for item in physical["inspection_attempts"])
    assert all(item["ok"] for item in physical["fixture_preferred_waypoint_attempts"])
    assert all(
        item["primitive_provenance"] == BLOCKED_CAPABILITY_PROVENANCE
        for item in physical["blocked_manipulation_results"]
    )
    assert [item["tool"] for item in physical["blocked_manipulation_results"]] == list(
        BLOCKED_MANIPULATION_TOOLS
    )
    assert (tmp_path / "map_bundle" / "map.yaml").is_file()
    assert (tmp_path / "map_bundle" / "profiles" / "rby1m.yaml").is_file()
    assert persisted["real_robot_readiness"]["physical_navigation_pilot"] is True
    assert "physical_navigation_pilot=true" in report_text
    assert "physical_cleanup_ready=false" in report_text
    assert "Nav2 Map Bundle" in report_text
