# 0128. Add Real Robot Cleanup Profile

Date: 2026-05-18

## Status

Accepted

## Decision

The first physical-robot cleanup-facing pilot will introduce a
`real_robot_cleanup_v1` contract profile instead of reusing
`molmospaces_cleanup_v1` for real hardware.

The new profile should preserve the ADR-0003 cleanup tool shape where practical:
public metric map, static fixture semantics, robot-local observations,
`observed_*` handles, navigation tools, manipulation tools, and `done`. The
difference is backend provenance, not task strategy: successful physical
navigation can report `nav2_action`, while unimplemented physical manipulation
must report `blocked_capability`.

The first hardware pilot should use a prebuilt Nav2 map plus a small
operator-authored fixture/waypoint semantic map. Runtime movable objects remain
robot-local observations or model-declared observations; live SLAM and live
fixture discovery are later capabilities.

For the day-one Navigation + Perception Pilot, expose the cleanup-shaped public
tool list but make only navigation and perception executable. Room, waypoint,
object, visual-candidate, and fixture navigation tools resolve public grounding
to bounded Nav2 goals when possible. Observation, active camera adjustment,
visual-candidate declaration, and object inspection stay grounded in public
camera artifacts. Physical `navigate_to_receptacle` means "navigate to the
fixture's preferred public waypoint" through Nav2; it does not require a held
object and does not imply manipulation readiness. Physical manipulation tools
such as `pick`, `place`, `place_inside`, `open_receptacle`, and
`close_receptacle` must return structured `blocked_capability` until a separate
manipulation gate proves them.

The default physical `observe()` input should be camera-derived labels from a
robot perception or detection service: `observed_*` handles, categories, boxes,
support estimates, confidence, source frame/time, and staleness. A `camera-raw`
profile may expose FPV artifacts and let the agent create model-declared
observations through the existing visual-candidate path. Full 3D object tracking
is not required for the first pilot.

The first pilot is accepted when an MCP-driven agent loads a prebuilt map bundle
and robot profile, reads `metric_map` and `fixture_hints`, attempts every public
inspection waypoint and fixture preferred waypoint, records either `nav2_action`
success or explained `blocked_capability` for each navigation attempt, observes
from every reached waypoint, keeps physical manipulation tools blocked, and
renders a report that separates `physical_navigation_pilot=true` from
`physical_cleanup_ready=false`.

## Consequences

- Reports can distinguish a MolmoSpaces simulator cleanup run from a physical
  robot navigation/perception pilot without overloading one profile name.
- The existing `molmo-realworld-cleanup` skill behavior can be reused and
  refined against the physical profile.
- Roboclaws still avoids a premature generic `robot_task_v1`; the first hardware
  contract remains cleanup/domain-specific.
