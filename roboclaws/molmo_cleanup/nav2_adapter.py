from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol

NAV2_ACTION_PROVENANCE = "nav2_action"
BLOCKED_CAPABILITY_PROVENANCE = "blocked_capability"


@dataclass(frozen=True)
class Nav2Pose:
    frame_id: str
    x: float
    y: float
    yaw: float

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> Nav2Pose:
        return cls(
            frame_id=str(value.get("frame_id") or "map"),
            x=float(value.get("x") or 0.0),
            y=float(value.get("y") or 0.0),
            yaw=float(value.get("yaw") or 0.0),
        )


@dataclass(frozen=True)
class Nav2Goal:
    goal_id: str
    pose: Nav2Pose
    source: str
    timeout_s: float


@dataclass(frozen=True)
class Nav2ActionResult:
    status: str
    final_pose: Nav2Pose | None = None
    failure_type: str = ""
    message: str = ""
    elapsed_s: float = 0.0
    cancel_accepted: bool = False


class Nav2ActionClient(Protocol):
    def navigate_to_pose(self, goal: Nav2Goal) -> Nav2ActionResult:
        """Send one NavigateToPose-style goal and return a normalized result."""

    def cancel(self, goal_id: str) -> Nav2ActionResult:
        """Cancel the active goal when the operator or timeout path requests it."""


class DirectNav2Adapter:
    """Thin direct ROS 2/Nav2 boundary with no ROS dependency in CI."""

    def __init__(
        self,
        client: Nav2ActionClient,
        *,
        operator_stop_channel_configured: bool = False,
        max_goal_distance_m: float | None = None,
    ) -> None:
        self.client = client
        self.operator_stop_channel_configured = operator_stop_channel_configured
        self.max_goal_distance_m = max_goal_distance_m

    def navigate_to_waypoint(
        self,
        *,
        waypoint_id: str,
        waypoint_pose: dict[str, Any],
        current_pose: dict[str, Any] | None = None,
        timeout_s: float = 30.0,
        cancel_requested: bool = False,
        goal_source: str = "inspection_waypoint",
    ) -> dict[str, Any]:
        target_pose = Nav2Pose.from_mapping(waypoint_pose)
        current = Nav2Pose.from_mapping(current_pose or {"frame_id": target_pose.frame_id})
        goal_id = f"waypoint:{waypoint_id}"
        if cancel_requested:
            canceled = self.client.cancel(goal_id)
            return self._blocked_response(
                waypoint_id=waypoint_id,
                target_pose=target_pose,
                current_pose=current,
                failure_type=canceled.failure_type or "cancel_requested",
                backend_error_summary=canceled.message or "Nav2 goal canceled before dispatch.",
                cancel_accepted=canceled.cancel_accepted,
                goal_source=goal_source,
            )
        if self.max_goal_distance_m is not None:
            distance = _pose_distance(current, target_pose)
            if distance > self.max_goal_distance_m:
                return self._blocked_response(
                    waypoint_id=waypoint_id,
                    target_pose=target_pose,
                    current_pose=current,
                    failure_type="goal_distance_exceeded",
                    backend_error_summary=(
                        f"Goal is {distance:.3f}m away; configured limit is "
                        f"{self.max_goal_distance_m:.3f}m."
                    ),
                    goal_source=goal_source,
                )
        goal = Nav2Goal(
            goal_id=goal_id,
            pose=target_pose,
            source=goal_source,
            timeout_s=timeout_s,
        )
        result = self.client.navigate_to_pose(goal)
        if result.status == "succeeded":
            return {
                "ok": True,
                "tool": "navigate_to_waypoint",
                "waypoint_id": waypoint_id,
                "navigation_backend": NAV2_ACTION_PROVENANCE,
                "primitive_provenance": NAV2_ACTION_PROVENANCE,
                "navigation_status": "succeeded",
                "goal_source": goal_source,
                "goal_pose": _pose_payload(target_pose),
                "current_pose": _pose_payload(result.final_pose or target_pose),
                "pose_source": goal_source,
                "elapsed_s": result.elapsed_s,
                "operator_stop_channel_configured": self.operator_stop_channel_configured,
                "physical_navigation_pilot": True,
                "physical_cleanup_ready": False,
                "manipulation_ready": False,
            }
        if result.status == "timeout":
            canceled = self.client.cancel(goal_id)
            return self._blocked_response(
                waypoint_id=waypoint_id,
                target_pose=target_pose,
                current_pose=result.final_pose or current,
                failure_type="timeout",
                backend_error_summary=result.message or "Nav2 goal timed out.",
                cancel_accepted=canceled.cancel_accepted,
                goal_source=goal_source,
            )
        return self._blocked_response(
            waypoint_id=waypoint_id,
            target_pose=target_pose,
            current_pose=result.final_pose or current,
            failure_type=result.failure_type or result.status or "nav2_failure",
            backend_error_summary=result.message or "Nav2 goal failed.",
            cancel_accepted=result.cancel_accepted,
            goal_source=goal_source,
        )

    def navigate_to_fixture_preferred_waypoint(
        self,
        *,
        fixture_id: str,
        fixture: dict[str, Any],
        waypoints_by_id: dict[str, dict[str, Any]],
        current_pose: dict[str, Any] | None = None,
        timeout_s: float = 30.0,
        cancel_requested: bool = False,
    ) -> dict[str, Any]:
        waypoint_id = str(
            fixture.get("preferred_manipulation_waypoint_id")
            or fixture.get("preferred_inspection_waypoint_id")
            or ""
        )
        waypoint = waypoints_by_id.get(waypoint_id)
        if not waypoint:
            fallback_pose = Nav2Pose.from_mapping(current_pose or {"frame_id": "map"})
            response = self._blocked_response(
                waypoint_id=waypoint_id,
                target_pose=fallback_pose,
                current_pose=fallback_pose,
                failure_type="missing_fixture_preferred_waypoint",
                backend_error_summary=(
                    f"Fixture {fixture_id!r} does not resolve to a public preferred waypoint."
                ),
                goal_source="fixture_preferred_waypoint",
            )
            response["tool"] = "navigate_to_receptacle"
            response["fixture_id"] = fixture_id
            response["receptacle_id"] = fixture_id
            response["preferred_waypoint_id"] = waypoint_id
            return response
        response = self.navigate_to_waypoint(
            waypoint_id=waypoint_id,
            waypoint_pose=waypoint,
            current_pose=current_pose,
            timeout_s=timeout_s,
            cancel_requested=cancel_requested,
            goal_source="fixture_preferred_waypoint",
        )
        response = dict(response)
        response["tool"] = "navigate_to_receptacle"
        response["fixture_id"] = fixture_id
        response["receptacle_id"] = fixture_id
        response["preferred_waypoint_id"] = waypoint_id
        response["manipulation_ready"] = False
        response["physical_navigation_pilot"] = True
        response["physical_cleanup_ready"] = False
        return response

    def blocked_manipulation(
        self,
        *,
        tool: str,
        reason: str = "physical_manipulation_unproven",
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "tool": tool,
            "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
            "error_reason": "blocked_capability",
            "failure_type": reason,
            "physical_navigation_pilot": True,
            "physical_cleanup_ready": False,
            "manipulation_ready": False,
        }

    def _blocked_response(
        self,
        *,
        waypoint_id: str,
        target_pose: Nav2Pose,
        current_pose: Nav2Pose,
        failure_type: str,
        backend_error_summary: str,
        goal_source: str,
        cancel_accepted: bool = False,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "tool": "navigate_to_waypoint",
            "waypoint_id": waypoint_id,
            "navigation_backend": BLOCKED_CAPABILITY_PROVENANCE,
            "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
            "navigation_status": "blocked",
            "goal_source": goal_source,
            "goal_pose": _pose_payload(target_pose),
            "current_pose": _pose_payload(current_pose),
            "pose_source": goal_source,
            "failure_type": failure_type,
            "backend_error_summary": backend_error_summary,
            "cancel_accepted": cancel_accepted,
            "operator_stop_channel_configured": self.operator_stop_channel_configured,
            "physical_navigation_pilot": True,
            "physical_cleanup_ready": False,
            "manipulation_ready": False,
        }


def _pose_payload(pose: Nav2Pose) -> dict[str, Any]:
    return {
        "frame_id": pose.frame_id,
        "x": pose.x,
        "y": pose.y,
        "yaw": pose.yaw,
    }


def _pose_distance(a: Nav2Pose, b: Nav2Pose) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)
