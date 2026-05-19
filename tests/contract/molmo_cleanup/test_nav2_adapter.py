from __future__ import annotations

from roboclaws.molmo_cleanup.nav2_adapter import (
    BLOCKED_CAPABILITY_PROVENANCE,
    NAV2_ACTION_PROVENANCE,
    DirectNav2Adapter,
    Nav2ActionResult,
    Nav2Goal,
    Nav2Pose,
)


class MockNav2Client:
    def __init__(self, result: Nav2ActionResult) -> None:
        self.result = result
        self.goals: list[Nav2Goal] = []
        self.canceled: list[str] = []

    def navigate_to_pose(self, goal: Nav2Goal) -> Nav2ActionResult:
        self.goals.append(goal)
        return self.result

    def cancel(self, goal_id: str) -> Nav2ActionResult:
        self.canceled.append(goal_id)
        return Nav2ActionResult(
            status="canceled",
            failure_type="cancel_requested",
            message="cancel accepted",
            cancel_accepted=True,
        )


def test_direct_nav2_adapter_reports_success_as_nav2_action() -> None:
    client = MockNav2Client(
        Nav2ActionResult(
            status="succeeded",
            final_pose=Nav2Pose(frame_id="map", x=1.0, y=2.0, yaw=0.5),
            elapsed_s=4.2,
        )
    )
    adapter = DirectNav2Adapter(client, operator_stop_channel_configured=True)

    result = adapter.navigate_to_waypoint(
        waypoint_id="kitchen_scan_1",
        waypoint_pose={"frame_id": "map", "x": 1.0, "y": 2.0, "yaw": 0.5},
    )

    assert result["ok"] is True
    assert result["navigation_backend"] == NAV2_ACTION_PROVENANCE
    assert result["primitive_provenance"] == NAV2_ACTION_PROVENANCE
    assert result["operator_stop_channel_configured"] is True
    assert result["pose_source"] == "inspection_waypoint"
    assert result["physical_navigation_pilot"] is True
    assert result["physical_cleanup_ready"] is False
    assert result["manipulation_ready"] is False
    assert client.goals[0].goal_id == "waypoint:kitchen_scan_1"


def test_direct_nav2_adapter_times_out_and_cancels_goal() -> None:
    client = MockNav2Client(Nav2ActionResult(status="timeout", message="planner exceeded 1s"))
    adapter = DirectNav2Adapter(client)

    result = adapter.navigate_to_waypoint(
        waypoint_id="kitchen_scan_1",
        waypoint_pose={"frame_id": "map", "x": 1.0, "y": 2.0, "yaw": 0.0},
        timeout_s=1.0,
    )

    assert result["ok"] is False
    assert result["navigation_backend"] == BLOCKED_CAPABILITY_PROVENANCE
    assert result["failure_type"] == "timeout"
    assert result["cancel_accepted"] is True
    assert client.canceled == ["waypoint:kitchen_scan_1"]


def test_direct_nav2_adapter_allows_operator_cancel_before_dispatch() -> None:
    client = MockNav2Client(Nav2ActionResult(status="succeeded"))
    adapter = DirectNav2Adapter(client)

    result = adapter.navigate_to_waypoint(
        waypoint_id="hall_scan_1",
        waypoint_pose={"frame_id": "map", "x": 0.0, "y": 0.0, "yaw": 0.0},
        cancel_requested=True,
    )

    assert result["ok"] is False
    assert result["failure_type"] == "cancel_requested"
    assert result["cancel_accepted"] is True
    assert client.goals == []
    assert client.canceled == ["waypoint:hall_scan_1"]


def test_direct_nav2_adapter_rejects_unreachable_goal_distance() -> None:
    client = MockNav2Client(Nav2ActionResult(status="succeeded"))
    adapter = DirectNav2Adapter(client, max_goal_distance_m=1.0)

    result = adapter.navigate_to_waypoint(
        waypoint_id="far_scan_1",
        waypoint_pose={"frame_id": "map", "x": 3.0, "y": 4.0, "yaw": 0.0},
        current_pose={"frame_id": "map", "x": 0.0, "y": 0.0, "yaw": 0.0},
    )

    assert result["ok"] is False
    assert result["failure_type"] == "goal_distance_exceeded"
    assert result["navigation_backend"] == BLOCKED_CAPABILITY_PROVENANCE
    assert result["physical_navigation_pilot"] is True
    assert result["physical_cleanup_ready"] is False
    assert client.goals == []


def test_direct_nav2_adapter_navigates_to_fixture_preferred_waypoint() -> None:
    client = MockNav2Client(
        Nav2ActionResult(
            status="succeeded",
            final_pose=Nav2Pose(frame_id="map", x=2.0, y=3.0, yaw=1.0),
        )
    )
    adapter = DirectNav2Adapter(client)

    result = adapter.navigate_to_fixture_preferred_waypoint(
        fixture_id="sink_01",
        fixture={"preferred_manipulation_waypoint_id": "sink_scan_1"},
        waypoints_by_id={
            "sink_scan_1": {
                "waypoint_id": "sink_scan_1",
                "frame_id": "map",
                "x": 2.0,
                "y": 3.0,
                "yaw": 1.0,
            }
        },
    )

    assert result["ok"] is True
    assert result["tool"] == "navigate_to_receptacle"
    assert result["fixture_id"] == "sink_01"
    assert result["preferred_waypoint_id"] == "sink_scan_1"
    assert result["goal_source"] == "fixture_preferred_waypoint"
    assert result["navigation_backend"] == NAV2_ACTION_PROVENANCE
    assert result["manipulation_ready"] is False
    assert client.goals[0].source == "fixture_preferred_waypoint"


def test_direct_nav2_adapter_blocks_fixture_without_preferred_waypoint() -> None:
    client = MockNav2Client(Nav2ActionResult(status="succeeded"))
    adapter = DirectNav2Adapter(client)

    result = adapter.navigate_to_fixture_preferred_waypoint(
        fixture_id="sink_01",
        fixture={},
        waypoints_by_id={},
    )

    assert result["ok"] is False
    assert result["tool"] == "navigate_to_receptacle"
    assert result["failure_type"] == "missing_fixture_preferred_waypoint"
    assert result["navigation_backend"] == BLOCKED_CAPABILITY_PROVENANCE
    assert result["manipulation_ready"] is False
    assert client.goals == []


def test_direct_nav2_adapter_reports_blocked_manipulation() -> None:
    client = MockNav2Client(Nav2ActionResult(status="succeeded"))
    adapter = DirectNav2Adapter(client)

    result = adapter.blocked_manipulation(tool="pick")

    assert result["ok"] is False
    assert result["primitive_provenance"] == BLOCKED_CAPABILITY_PROVENANCE
    assert result["error_reason"] == "blocked_capability"
    assert result["physical_navigation_pilot"] is True
    assert result["physical_cleanup_ready"] is False
