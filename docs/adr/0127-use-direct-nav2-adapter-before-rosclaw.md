# 0127. Use Direct Nav2 Adapter Before ROSClaw

Date: 2026-05-18

## Status

Accepted

## Decision

For the first physical-robot Navigation + Perception Pilot, Roboclaws will add a
direct ROS 2/Nav2 backend adapter behind the existing cleanup MCP contract
before routing physical robot execution through ROSClaw or another OpenClaw ROS
bridge.

OpenClaw, Codex, and Claude remain valid agent drivers above MCP, but the first
robot backend should establish one clear baseline: `navigate_to_waypoint` and
fixture navigation resolve to Nav2-style goals, while manipulation tools remain
honestly `blocked_capability` until a separate physical manipulation gate exists.

Agents should not directly control ROS topics, services, or actions in the
canonical pilot profile. ROS 2/Nav2 calls are backend adapter implementation
details behind MCP cleanup tools so Agent View, trace provenance, and safety
boundaries remain auditable.

The pilot backend must expose bounded navigation execution: per-goal timeout,
maximum accepted goal distance when configured, action cancel support, visible
failure states, and a report field for whether an operator stop channel was
configured. Hardware E-stop or teleop override remains outside MCP, but the run
must not hide whether that safety channel existed.

## Consequences

- Roboclaws gets a measurable Nav2 baseline without adding a second bridge layer
  before the robot contract is proven.
- ROSClaw remains a later ecosystem integration option rather than the first
  physical deployment dependency.
- Real-robot reports must keep provenance explicit: `nav2_action` for successful
  physical navigation, `blocked_capability` for unimplemented manipulation, and
  no claim of full cleanup until planner-backed or real manipulation proof is
  available.
