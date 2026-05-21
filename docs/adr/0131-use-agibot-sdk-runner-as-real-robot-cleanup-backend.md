# 0131. Use Agibot SDK Runner As Real Robot Cleanup Backend

Date: 2026-05-21

## Status

Accepted

## Decision

Roboclaws should integrate Agibot G2 as a backend for the existing
`real_robot_cleanup_v1` MCP contract, not as a separate public MCP surface and
not as a report-only path. The agent-facing tools remain backend-neutral:
`metric_map`, `fixture_hints`, `observe`, `navigate_to_waypoint`,
`navigate_to_receptacle`, and `done` should mean the same things across sim-only,
Nav2, Agibot, and future robot backends.

Roboclaws hosts the MCP server and owns the agent-facing session state. The
Agibot SDK owns the robot-side runner, GDK calls, map artifacts, navigation
evidence, and camera capture artifacts. Roboclaws calls the SDK runner through a
coarse CLI boundary at semantic tool granularity. For example,
`navigate_to_waypoint` may invoke one SDK runner command that performs map
checks, target preparation, optional `--execute` navigation, wait-for-arrival
logic, and arrival observation capture. Roboclaws must not import live GDK
modules into its Python runtime for the first version.

The real robot movement gate is session-level. Starting an Agibot MCP backend
without a real-movement enablement flag should make navigation dry-run,
rehearsal, or blocked-capability only. Starting it with an explicit real-movement
flag allows agent tool calls to dispatch SDK runner commands with `--execute`.
Individual agent tool calls should not need a second confirmation, but the
operator must choose whether the MCP session may move the robot.

`observe` in the Agibot backend should actively capture a current robot
observation, while navigation may also capture arrival observations for
evidence. `metric_map` and `fixture_hints` should come from the SDK agent-view
export; full cleanup semantics are optional for navigation and observation.
`navigate_to_receptacle` may execute only by resolving a public fixture
preferred waypoint. Object and visual-candidate navigation remain blocked unless
already waypoint-resolved.

Roboclaws should still support report-only import of Agibot SDK run directories,
but that path is evidence review, not the main live backend. MolmoSpaces Agibot
contract rehearsal should reuse `real_robot_cleanup_v1` and Agibot-shaped
preflight/runtime artifacts while declaring simulated backend and provenance
labels. It validates contract shape and agent flow, not physical Agibot map or
PNC behavior.

## Consequences

- The same cleanup agent API can operate sim-only, Nav2, Agibot, and later robot
  backends.
- Agibot-specific GDK/runtime details stay in the SDK runner and artifacts.
- Roboclaws keeps Python 3.12 while the current Agibot GDK runtime can remain
  CPython 3.10.
- Report-only artifact import remains useful for off-machine real robot runs and
  historical debugging, but it is not the primary integration route.
