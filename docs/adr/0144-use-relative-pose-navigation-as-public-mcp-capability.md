# ADR-0144: Use Relative Pose Navigation As Public MCP Capability

Status: Accepted

Date: 2026-06-16

Plan:
[`docs/plans/2026-06-16-operator-relative-navigation-control.md`](../plans/2026-06-16-operator-relative-navigation-control.md)

## Context

The operator console needs direct debugging controls for active robot runs:
small forward/backward/lateral nudges and left/right turns. Existing mechanisms
do not cleanly cover this need:

- `navigate_to_waypoint` means navigation to a public Metric Map inspection
  waypoint, not a robot-local nudge.
- `adjust_camera` changes bounded camera yaw/pitch but does not move the base.
- `check_operator_messages` is a delayed active-run steering checkpoint for the
  agent, not immediate operator control.

Reusing waypoint navigation for direction buttons would blur Metric Map
semantics and make traces look as if a public inspection waypoint had been
selected. A separate relative movement capability preserves reviewability and
can later be used by agents when short local motion is necessary.

## Decision

Add `navigate_to_relative_pose` as a public household-world MCP navigation
capability.

The tool shape is:

```python
navigate_to_relative_pose(
    forward_m: float = 0.0,
    lateral_m: float = 0.0,
    yaw_delta_deg: float = 0.0,
)
```

Semantics:

- The frame is robot-local at call time.
- Positive `forward_m` moves forward; negative moves backward.
- Positive `lateral_m` moves left; negative moves right.
- Positive `yaw_delta_deg` turns left; negative turns right.
- The response must report requested and applied deltas, backend provenance,
  safety/clamp metadata, and `requires_reobserve=true`.
- Hidden simulator coordinates, private scoring truth, and generated mess truth
  must not be exposed in the public response.

`navigate_to_relative_pose` belongs to the `household_world` navigation family,
beside `navigate_to_waypoint`. It is not a manipulation capability.

Operator-console button calls are operator interventions and must be attributed
as `actor=operator`. Agent-initiated calls through normal MCP traces remain
agent actions. Assisted runs are not accepted as autonomous behavior proof.

First implementation support must include MolmoSpaces/MuJoCo and B1 Map 12
Isaac digital twin routes. Agibot and physical-robot support remains blocked or
safety-gated until a separate physical movement proof exists.

## Rejected Alternatives

- Reuse `navigate_to_waypoint` with generated hidden waypoints. Rejected
  because it would corrupt the public waypoint contract and make traces
  misleading.
- Keep this operator-only and never agent-facing. Rejected because short local
  movement is a reusable robot capability, not just a UI shortcut.
- Use a generic browser-to-MCP proxy. Rejected because the operator console must
  not expose arbitrary MCP tool calls or shell-like control.
- Enable physical relative movement by default. Rejected because physical
  movement needs real-movement gates, localization, command enablement, E-stop
  readiness, and local proof.

## Consequences

- `household_world` profile metadata, MCP tool registration, prompts, and docs
  should distinguish relative pose navigation from waypoint navigation.
- Operator-console direct control must use a narrow allowlist endpoint, not a
  generic MCP proxy.
- Movement invalidates local observation evidence enough that callers must
  re-observe before making perception-dependent decisions.
- Eval/report code must surface operator interventions separately from
  autonomous agent behavior.
- Isaac support is part of the first delivery target because B1 / Map 12
  digital twin is the active Isaac route.
