---
plan_scope: operator-relative-navigation-control
status: IMPLEMENTED
created: 2026-06-16
last_reviewed: 2026-06-16
implementation_allowed: true
source:
  - user request for operator UI buttons to move/turn the robot during debugging
  - user decision to add a new reusable relative navigation interface instead of reusing waypoint navigation
  - intuitive-reduce-entropy plan entropy loop
  - grill-with-docs-batch public contract decisions
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - docs/human/mcp-skills-and-semantic-profiles.md
  - docs/human/coding-agent-nav-server.md
  - docs/plans/operator-console-agent-interaction.md
  - roboclaws/operator_console/
  - roboclaws/household/realworld_mcp_server.py
  - roboclaws/household/realworld_mcp_semantic_tools.py
  - roboclaws/household/backend_contract.py
  - roboclaws/mcp/profiles.py
  - scripts/molmo_cleanup/molmospaces_worker_cli.py
  - scripts/molmo_cleanup/molmospaces_worker_protocol.py
  - scripts/molmo_cleanup/molmospaces_actions.py
  - scripts/isaac_lab_cleanup/isaac_worker_cli.py
  - scripts/isaac_lab_cleanup/isaac_worker_commands.py
related_adrs:
  - docs/adr/0144-use-relative-pose-navigation-as-public-mcp-capability.md
---

# Operator Relative Navigation Control

## Goal

Add a reusable relative robot movement capability and expose it in the
standalone Operator Console as direct debugging controls.

The operator should be able to nudge the robot during an active simulator run
without waiting for the agent to choose a better viewpoint:

- forward / backward;
- strafe left / strafe right when the backend supports lateral motion;
- turn left / turn right;
- observe after movement.

The same movement primitive should be named and shaped well enough to become an
agent-facing MCP capability when task skills need short, bounded local motion.
ADR-0144 records the durable public MCP contract.

## Non-Goals

- Do not add waypoint point-and-click navigation. The user explicitly does not
  need a waypoint chooser for this slice.
- Do not overload `navigate_to_waypoint` with generated hidden waypoints or
  one-off UI poses.
- Do not add arbitrary browser-submitted shell commands.
- Do not make direct control count as autonomous agent success in evals.
- Do not enable physical robot relative movement by default.
- Do not implement continuous joystick/WebSocket driving in the first slice.
  Discrete button presses are enough.

## Owning Layers

- MCP Capability Contract And Tools: owns the new
  `navigate_to_relative_pose` public capability shape.
- Backend Runtime / Environment Primitive: owns backend-specific execution,
  collision/safety checks, limits, and blocked-capability responses.
- Thin Runtime / Server Adapter: the operator console may route an active-run
  operator control request to the live MCP server and render the result. It must
  stay thin: no cleanup/search strategy, private scorer truth, or opaque task
  shortcuts.
- Operator Console UI: owns buttons, disabled states, status copy, and links to
  resulting artifacts.
- Artifacts, reports, and eval suites: own attribution. Operator movement must
  be visible as operator intervention evidence and must not be graded as agent
  behavior.

## Proposed Interface

Tool name:

```text
navigate_to_relative_pose
```

MCP arguments:

```python
navigate_to_relative_pose(
    forward_m: float = 0.0,
    lateral_m: float = 0.0,
    yaw_delta_deg: float = 0.0,
)
```

Semantics:

- The frame is robot-local at call time.
- `forward_m > 0` moves forward; `forward_m < 0` moves backward.
- `lateral_m > 0` moves left; `lateral_m < 0` moves right.
- `yaw_delta_deg > 0` turns left; `yaw_delta_deg < 0` turns right.
- Calls may combine translation and yaw, but the UI should start with one-axis
  presets.
- Backends clamp or reject movement outside configured limits.
- Backends must return structured `blocked_capability` when relative navigation
  is unavailable or unsafe.
- The response must include enough public state for review without exposing
  private simulator/scorer truth:
  - `tool`;
  - `ok`;
  - `status`;
  - `frame_id="base_link"` or equivalent robot-local frame declaration;
  - normalized requested and applied deltas;
  - clamp or safety metadata;
  - `requires_reobserve=true`;
  - backend provenance such as `api_semantic`, `sim_planner`, `nav2_action`,
    `agibot_gdk_normal_navi`, or `blocked_capability`.

This belongs beside `navigate_to_waypoint` in `household_world` navigation
capabilities. It does not belong to `household_manipulation` because it moves
the base/pose, not objects.

Grill decision: register the tool as a public MCP capability in the first
implementation. Prompts should expose it conservatively where short local
motion is useful; cleanup skills do not need to prefer it by default.

## Operator Console Behavior

Add a compact `Manual Control` panel for active runs whose route advertises
relative navigation support.

First button set:

| UI action | Tool call |
| --- | --- |
| Forward | `navigate_to_relative_pose(forward_m=step_m)` |
| Back | `navigate_to_relative_pose(forward_m=-step_m)` |
| Left | `navigate_to_relative_pose(lateral_m=step_m)` |
| Right | `navigate_to_relative_pose(lateral_m=-step_m)` |
| Turn left | `navigate_to_relative_pose(yaw_delta_deg=turn_deg)` |
| Turn right | `navigate_to_relative_pose(yaw_delta_deg=-turn_deg)` |
| Observe | `observe()` |

Default presets:

- `step_m=0.25`;
- `turn_deg=15`;
- optional UI selectors can be added later; do not add sliders in the first
  pass unless backend proof shows the fixed presets are inadequate.

Control states:

- Hidden or disabled when no active run is attached.
- Disabled for terminal runs.
- Disabled when route/backend does not advertise support.
- Disabled while a direct-control request is in flight.
- Physical/real-movement routes require the same real-movement gates as launch;
  first implementation may keep physical routes blocked.

The UI should show the latest result succinctly: applied movement, blocked
reason, or error. It should not imply that the agent chose the action.

## Console API Shape

Add a narrow active-run endpoint:

```text
POST /api/runs/<run_id>/control
```

Payload:

```json
{
  "action": "navigate_to_relative_pose",
  "forward_m": 0.25,
  "lateral_m": 0.0,
  "yaw_delta_deg": 0.0
}
```

Rules:

- Only allow an explicit allowlist: `navigate_to_relative_pose` and `observe`.
- Derive the active route and MCP endpoint from first-class run state fields,
  not by parsing shell-like command text.
- Reject unknown runs, terminal runs, unsupported routes, unsupported tools, and
  values outside console-side limits before contacting MCP.
- Record an operator-control artifact row before and after the MCP call.
- The endpoint must not accept arbitrary MCP tool names or arbitrary shell
  commands.

Implementation note: current `Steer` writes `operator_messages.jsonl` for the
agent to read later. Direct control is different. It must call the live MCP
server or equivalent active-run control bridge immediately; otherwise buttons
would only become text steering and would not solve the debugging problem.
`operator_state.json` should persist `mcp_host`, `mcp_port`, and `mcp_url` at
launch time so `/control` does not need to infer them from `argv`.

## Backend Plan

### Shared Contract

Add `navigate_to_relative_pose` to:

- MCP semantic tool registration and dispatch;
- `RealWorldCleanupContract`;
- `CleanupBackendSession`;
- MCP profile metadata under `household_world`;
- agent-facing prompt/profile docs where tool lists are enumerated.

Contract-level behavior:

- Validate numeric inputs.
- Reject all-zero no-op requests.
- Console-side excessive deltas are rejected before the MCP call. Backend-side
  safety clamps are allowed only when the response explicitly reports
  `clamped=true` and the applied delta.
- Reset bounded camera adjustment after base movement, matching waypoint
  navigation behavior.
- Mark `requires_reobserve=true`.
- Keep hidden simulator coordinates out of the public response.
- Write tool request/response trace events like other MCP calls.

### MolmoSpaces / MuJoCo

First supported implementation target.

The backend should execute relative movement through the existing persistent
worker/state path, not by fabricating a public waypoint. The worker owns
collision/state mutation and can return blocked movement if the step is unsafe.
Implementation must update each MolmoSpaces worker layer that currently routes
`navigate_to_waypoint`: CLI parser, protocol kwargs, command handler, mutating
command set, and action implementation.

If the underlying runtime initially lacks true local motion, a temporary
simulator-backed implementation may update the robot pose in the same state
model used by `navigate_to_waypoint`, but the response must still be labeled
`navigate_to_relative_pose` and `pose_source=relative_robot_frame`, not
`inspection_waypoint`.

### Isaac Lab

Required first-slice implementation target for the active B1 / Map 12 digital
twin route.

Mirror the MolmoSpaces contract shape through the Isaac worker. The B1 digital
twin route must support `navigate_to_relative_pose` enough for operator-console
dogfood and focused tests. Runtime modes that cannot execute real relative
movement may still return structured `blocked_capability`, but that does not
complete the B1 digital-twin acceptance gate. Implementation must touch the
Isaac worker CLI parser and command handler path, not only the Python backend
wrapper.

### Agibot / Physical Robots

Do not enable by default.

The first implementation may return `blocked_capability` for Agibot. A later
physical slice must add:

- real-movement gate reuse;
- localization and command-enable checks;
- velocity/step limits;
- collision or planner feedback;
- visible E-stop/manual-stop status;
- local live proof off the work network when applicable.

## Trace, Report, And Eval Attribution

Direct operator movement must be auditable.

Required artifacts:

- `trace.jsonl` contains `navigate_to_relative_pose` request/response events.
- Operator-console artifacts contain a control row with `actor="operator"`.
- Run state exposes latest direct-control result.
- Report or run summary includes an `operator_interventions` count and list
  when nonzero.

Eval rule:

- Operator interventions do not fail a run by default, because they are useful
  for manual debugging.
- Automated evals and live-agent proof rows must either not use the manual
  endpoint or must label the run as assisted. Assisted runs are not accepted as
  autonomous behavior proof.

Agent-facing future rule:

- If an agent calls `navigate_to_relative_pose` itself, the actor is `agent`
  through the normal MCP trace. Console-originated calls remain `operator`.

## Grill Decisions

Accepted on 2026-06-16:

- `navigate_to_relative_pose` is a public `household_world` MCP navigation
  capability, not an operator-only private helper.
- `POST /api/runs/<run_id>/control` allowlists both
  `navigate_to_relative_pose` and `observe`.
- Console-side movement values outside the accepted range are rejected. Backend
  safety clamps remain allowed only when explicit in the response.
- First implementation support includes both MolmoSpaces/MuJoCo and B1 Map 12
  Isaac digital twin. Agibot and physical robots remain blocked or safety-gated.
- ADR-0144 records the durable public contract; this plan owns execution
  details.

## Reduce-Entropy Loop

Selected mode: plan entropy mode.

Why: the user approved a new relative navigation interface and asked for a plan
plus an intuitive reduce-entropy loop before implementation.

Redirect: none.

Discovery intensity: saturation scan.

### Round 1: Demand And Reuse Gate

Demand gate: pass.

Reason: the current UI has `Steer`, but `Steer` is delayed until an agent safe
checkpoint and cannot reliably reposition the robot or camera for immediate
debugging. Reusing `navigate_to_waypoint` would blur public inspection-waypoint
semantics with local teleop nudges. A distinct relative navigation capability
removes this surprise and can later be reused by agents.

Rejected reuse:

- `navigate_to_waypoint`: wrong semantic target; public map waypoint rather
  than robot-local pose delta.
- `adjust_camera`: useful for viewpoint yaw/pitch only; it does not move the
  base.
- `operator_messages.jsonl`: delayed steering channel, not direct control.

### Round 2: Contract Gaps Found

Selected candidates:

1. **Actor attribution is mandatory.**
   Severity: P1. Without it, manual movement can create false confidence in
   agent autonomy and eval results.

2. **Console endpoint must be allowlisted.**
   Severity: P1. A generic browser-to-MCP proxy would violate the console's
   no-arbitrary-command constraint and would make server logic too broad.

3. **Physical movement must stay gated or blocked.**
   Severity: P1. The name is intentionally future agent-facing, but first
   implementation proof should not imply safe physical relative motion.

4. **No hidden waypoint compatibility shim.**
   Severity: P2. It would make traces misleading and weaken the Base Navigation
   Map / Runtime Metric Map contract.

5. **Reobserve requirement must be explicit.**
   Severity: P2. After local movement or turn, previous camera/object evidence
   may be stale; responses should nudge both UI and agent callers toward
   `observe`.

6. **MCP endpoint must be persisted as run state.**
   Severity: P2. The current console stores launch `argv`, but direct-control
   code should not parse command strings to discover the active MCP endpoint.

7. **Worker routing layers are in scope.**
   Severity: P2. MolmoSpaces and Isaac each route actions through CLI/protocol
   command tables before backend wrappers. Missing those tables would create a
   false-green Python contract with no live backend execution.

### Round 3: Saturation Check

Checked adjacent surfaces:

- `docs/human/mcp-skills-and-semantic-profiles.md` already names waypoint
  navigation and camera adjustment as public capabilities.
- `docs/plans/operator-console-agent-interaction.md` already fixes active-run
  text steering as `check_operator_messages`; this plan must not mutate that
  contract.
- `roboclaws/operator_console/server.py` currently has start/stop/message APIs,
  not a direct MCP call endpoint.
- `roboclaws/operator_console/state.py` can surface latest state and controls,
  but needs a new control availability field.
- `roboclaws/mcp/profiles.py` owns public profile metadata and should include
  the new tool when it becomes agent-facing.
- `roboclaws/operator_console/launcher.py` writes `operator_state.json` with
  `argv`, but not first-class `mcp_host`, `mcp_port`, or `mcp_url`.
- `scripts/molmo_cleanup/molmospaces_worker_cli.py`,
  `scripts/molmo_cleanup/molmospaces_worker_protocol.py`, and
  `scripts/molmo_cleanup/molmospaces_actions.py` are the MolmoSpaces command
  path for movement primitives.
- `scripts/isaac_lab_cleanup/isaac_worker_cli.py` and
  `scripts/isaac_lab_cleanup/isaac_worker_commands.py` are the Isaac command
  path for movement primitives.

No additional material P0/P1/P2 findings remain after the selected candidates.
Remaining details are implementation defaults for the preflight phase.

## Implementation Slices

### Slice 1: Contract And Simulator Support

- Add `navigate_to_relative_pose` to semantic MCP tools and dispatch.
- Add contract method and backend session method.
- Implement MolmoSpaces worker support with real relative movement or a
  clearly labeled blocked response while preserving the public contract.
- Implement B1 Map 12 Isaac digital-twin relative movement support through the
  Isaac worker path.
- Persist active MCP endpoint fields in operator run state during launch.
- Update profile metadata and docs.
- Add focused contract/unit tests.

### Slice 2: Operator Console Direct-Control UI

- Add route metadata such as `supports_relative_navigation_control`.
- Add `POST /api/runs/<run_id>/control` with strict allowlist and value limits.
- Add `Manual Control` buttons and latest-result display.
- Add state payload controls for visibility/disabled state.
- Add static/unit tests for DOM ids, endpoint rejection, and route gating.

### Slice 3: Attribution And Report Evidence

- Add operator-control artifact rows.
- Add `operator_interventions` summary to run state/report when present.
- Ensure eval/report code can distinguish assisted runs from autonomous runs.

## Verification

Focused deterministic gates:

```bash
node --check roboclaws/operator_console/static/app.js
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/mcp/test_semantic_profiles.py
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
ruff check roboclaws/operator_console roboclaws/household roboclaws/mcp tests/unit/operator_console tests/contract/mcp tests/contract/molmo_cleanup
```

Optional local dogfood:

```bash
just console::run
```

Then start a MolmoSpaces console run, press each manual control button once,
observe, and verify:

- FPV/top-down artifacts change or a structured blocked reason is shown;
- `trace.jsonl` includes `navigate_to_relative_pose`;
- operator-control artifact rows include `actor="operator"`;
- the report labels the run as assisted when manual movement occurred.

Run the same direct-control smoke against the B1 Map 12 Isaac digital-twin
route before marking implementation complete.

Eval-harness recommendation before implementation:

```bash
just agent::eval recommend plan=docs/plans/2026-06-16-operator-relative-navigation-control.md budget=focused
```

## Preflight Contract

Preflight status: IMPLEMENTED

Task source: mixed user prompt + plan

Canonical source:
`docs/plans/2026-06-16-operator-relative-navigation-control.md`

Route: durable `$intuitive-flow`

Goal: implement `navigate_to_relative_pose` as a public household-world MCP
navigation capability and expose it as operator-console manual controls for
MolmoSpaces/MuJoCo and B1 Isaac digital twin.

Scope:

- Add `navigate_to_relative_pose(forward_m, lateral_m, yaw_delta_deg)` through
  MCP semantic tools, dispatch, contract, backend session, and profile metadata.
- Implement MolmoSpaces/MuJoCo worker path support.
- Implement B1 Map 12 Isaac digital-twin worker path support.
- Add console `POST /api/runs/<run_id>/control` with an allowlist for
  `navigate_to_relative_pose` and `observe`.
- Add Manual Control buttons, route/state gating, latest result display, and
  operator attribution artifacts.
- Persist `mcp_host`, `mcp_port`, and `mcp_url` in `operator_state.json`.
- Surface `operator_interventions` in run/report evidence enough to distinguish
  assisted from autonomous runs.
- Update prompts/docs only where needed to reflect the public tool.

Non-goals:

- No waypoint picker.
- No hidden waypoint shim.
- No generic browser-to-MCP proxy.
- No continuous joystick/WebSocket driving.
- No physical/Agibot relative movement enablement in this slice.

Entity budget:

- reuse: `household_world`, MCP semantic tool stack, existing workers, operator
  console state/API, report artifacts.
- remove/merge: none.
- new: `navigate_to_relative_pose`, narrow `/control` endpoint, operator-control
  artifact rows.
- expansion triggers: physical robot enablement, arbitrary MCP proxying,
  continuous control, or changing public route axes requires re-approval.

Context:

- must-read: this plan, ADR-0144, `docs/human/domain.md`, `ARCHITECTURE.md`,
  `roboclaws/household/realworld_mcp_semantic_tools.py`,
  `roboclaws/household/realworld_contract.py`,
  `roboclaws/household/backend_contract.py`,
  `roboclaws/operator_console/server.py`, `roboclaws/operator_console/state.py`,
  `scripts/molmo_cleanup/*worker*`, and `scripts/isaac_lab_cleanup/*worker*`.
- useful: `docs/plans/operator-console-agent-interaction.md`,
  `docs/human/coding-agent-nav-server.md`.
- avoid-unless-needed: old historical plans/reports.

Acceptance:

- SUCCESS: direction buttons trigger immediate active-run movement/observe
  through the live MCP path; trace/report/state distinguish `actor=operator`;
  MolmoSpaces and B1 Isaac direct-control dogfood pass.
- BLOCKED_NEEDS_DECISION: none.
- BLOCKED_NEEDS_LOCAL_VALIDATION: required if B1 Isaac digital-twin runtime or
  local simulator resources are unavailable.
- INTERMEDIATE_ONLY: none unless explicitly approved later.
- No regressions: existing `navigate_to_waypoint`, `adjust_camera`,
  `Steer/check_operator_messages`, stop/emergency-stop, and launch catalog
  behavior remain intact.

Verification:

- deterministic:
  `node --check roboclaws/operator_console/static/app.js`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console tests/contract/mcp/test_semantic_profiles.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`;
  `ruff check roboclaws/operator_console roboclaws/household roboclaws/mcp tests/unit/operator_console tests/contract/mcp tests/contract/molmo_cleanup`.
- integration: focused worker tests for MolmoSpaces and Isaac relative movement
  command routing.
- product-run: `just console::run`, then manual MolmoSpaces active-run control
  smoke.
- local-live-manual: required B1 Map 12 Isaac digital-twin console control
  smoke; unavailable runtime blocks full completion.
- optional:
  `just agent::eval recommend plan=docs/plans/2026-06-16-operator-relative-navigation-control.md budget=focused`.

Execution:

- main: root session supervises implementation and validation.
- worker: none initially.
- worker-goal: none.

To execute:

```text
/goal execute docs/plans/2026-06-16-operator-relative-navigation-control.md with intuitive-flow
```

Optional tracking: none.

Approval: `LGTM`, `approve`, or `go ahead` approves; edits request revision.

## Open Questions For Preflight

No user-facing contract questions remain after grill-batch. Preflight should
apply this default: register the public tool in Slice 1, expose it in prompts
only where short local motion is useful, and do not make cleanup skills prefer
it by default.

## Recommended Next Action

Use the Manual Control panel in `just console::run` for active MolmoSpaces and
B1 Map 12 Isaac debugging. Keep future physical movement, continuous control,
and arbitrary MCP proxying behind separate review.

## Shipped Evidence

Implemented and dogfooded on 2026-06-16 in the local checkout.

What shipped:

- Added public MCP capability `navigate_to_relative_pose` through
  `household_world` profile metadata, semantic tool dispatch,
  `RealWorldCleanupContract`, `CleanupBackendSession`, MolmoSpaces/MuJoCo
  worker routing, and B1 Isaac worker routing.
- Added Operator Console `POST /api/runs/<run_id>/control` with an allowlist
  for `navigate_to_relative_pose` and `observe`.
- Added Manual Control UI buttons, route/state gating, latest-result display,
  and operator attribution artifacts:
  `operator_control.jsonl`, `operator_interventions.json`, and
  `operator_state.json.latest_operator_control`.
- Kept operator movement classified as assisted evidence:
  `operator_interventions.assisted=true` and
  `autonomous_behavior_proof=false`.
- Fixed live dogfood regressions found during validation:
  targetless Molmo open-task runs now initialize robot pose when
  `include_robot` is true, and relative-navigation responses strip private
  backend pose fields before returning `backend_pose_mutation`.

Focused deterministic verification:

```bash
uv sync --extra dev
node --check roboclaws/operator_console/static/app.js
.venv/bin/python -m py_compile roboclaws/household/realworld_contract.py scripts/molmo_cleanup/molmospaces_worker_state.py roboclaws/operator_console/control.py roboclaws/operator_console/server.py roboclaws/operator_console/state.py roboclaws/operator_console/routes.py
ruff check roboclaws/operator_console/control.py roboclaws/operator_console/routes.py roboclaws/operator_console/server.py roboclaws/operator_console/state.py roboclaws/household/realworld_contract.py roboclaws/household/realworld_mcp_semantic_tools.py roboclaws/household/backend_contract.py roboclaws/mcp/profiles.py scripts/molmo_cleanup/molmospaces_worker_state.py scripts/molmo_cleanup/molmospaces_worker_cli.py scripts/molmo_cleanup/molmospaces_worker_protocol.py scripts/molmo_cleanup/molmospaces_actions.py scripts/isaac_lab_cleanup/isaac_worker_cli.py scripts/isaac_lab_cleanup/isaac_worker_commands.py tests/unit/molmo_cleanup/test_molmospaces_worker_state.py tests/unit/molmo_cleanup/test_relative_navigation_worker_routing.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/unit/molmo_cleanup/test_molmospaces_worker_state.py tests/unit/molmo_cleanup/test_relative_navigation_worker_routing.py
./scripts/dev/run_pytest_standalone.sh -q tests/contract/mcp/test_semantic_profiles.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_operator_console.py::test_operator_console_control_endpoint_is_allowlisted_and_records_operator_rows tests/unit/operator_console/test_operator_console.py::test_operator_console_control_endpoint_rejects_unsupported_route tests/unit/operator_console/test_operator_console.py::test_operator_console_control_endpoint_rejects_terminal_run tests/unit/operator_console/test_static_assets.py::test_static_app_wires_manual_relative_navigation_controls
```

Live dogfood proof:

- MolmoSpaces/MuJoCo:
  `output/operator-console/runs/20260616-191632-molmospaces-val_0-mujoco-open-task-codex-cli-world-public-labels`
  contains operator `navigate_to_relative_pose` and `observe` rows, both `ok`,
  with nested `0616_1916/seed-7/trace.jsonl` containing two
  `navigate_to_relative_pose` events and two `observe` events.
- B1 Map 12 Isaac:
  `output/operator-console/runs/20260616-191804-b1-map12-isaaclab-open-task-codex-cli-world-public-labels`
  contains operator `navigate_to_relative_pose` and `observe` rows, both `ok`,
  with nested `0616_1918/seed-7/trace.jsonl` containing two
  `navigate_to_relative_pose` events and two `observe` events.

Verification caveat:

- Full `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console`
  still fails in
  `test_operator_console_routes_endpoint_exposes_evidence_lane_matrix` on an
  existing route evidence-lane matrix expectation unrelated to relative
  navigation control. The control-specific console tests above pass.

Cleanup state after dogfood:

- `output/operator-console/locks/` is empty.
- No process is listening on `127.0.0.1:8765` after stopping the dogfood
  console.

## Remaining Work

- Physical robot relative movement remains blocked until a separate safety
  gate, localization/command-enable check, E-stop status, and local proof exist.
- Continuous joystick/WebSocket driving remains out of scope.
- Arbitrary browser-to-MCP proxying remains rejected by ADR-0144.
