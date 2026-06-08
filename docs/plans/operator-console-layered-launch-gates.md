# Operator Console Layered Launch Gates

## Status

PLANNED

## Intuitive Preflight Result

Preflight status: DRAFT

Task source: this plan path.

Canonical source:
`docs/plans/operator-console-layered-launch-gates.md`

Execution route: durable `$intuitive-flow`.

Goal: implement layered operator-console launch gates so Start is not blocked by
vague manual Isaac/Agibot acknowledgements, while preserving hard launch
blockers and real-movement safety.

Execution command after approval:

```text
/goal execute docs/plans/operator-console-layered-launch-gates.md with intuitive-flow
```

Preflight scope:

- Make Isaac preflight advisory/non-blocking for Isaac Cleanup and Isaac Map
  Build.
- Remove or replace the required `Isaac preflight accepted` checkbox UX.
- Keep provider key, MCP port, backend lock, disabled routes, and required
  command inputs as hard blockers.
- Keep Agibot map context JSON required for the current Agibot map-build route.
- Make Agibot localization/run-enable/E-stop gates non-blocking for dry-run.
- Keep those Agibot gates blocking when `real_movement_enabled=true`.
- Update console readiness tests and UI/static tests as needed.

Preflight non-goals:

- No Isaac/GPU/Agibot hardware validation.
- No route id or task catalog rename.
- No full capability-mode runtime engine.
- No physical cleanup manipulation enablement.
- No removal of the Agibot map context requirement.

Preflight verification:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
.venv/bin/ruff check roboclaws/operator_console tests/unit/operator_console
```

## Goal

Make the operator console feel like a launch surface instead of a manual
preflight checklist. Operators should be able to start supported routes, then
see concrete diagnostics or capability prompts when a backend cannot proceed.

The console should block only actions that are immediately impossible or unsafe.
Backend readiness checks, Isaac runtime preflights, and real-robot operator
evidence should be surfaced as layered diagnostics or capability gates, not as
vague route-level acknowledgements.

## Source Context

- `roboclaws/operator_console/routes.py` currently represents provider keys,
  MCP port availability, Isaac preflight, Agibot context, localization, run
  enablement, and E-stop readiness as route gates.
- `roboclaws/operator_console/launcher.py` currently treats any incomplete
  route gate as a launch blocker in `route_readiness()` and
  `start_console_run()`.
- `roboclaws/operator_console/static/index.html` exposes an
  `Isaac preflight accepted` checkbox.
- `roboclaws/operator_console/static/app.js` lets local checkbox state mark
  gates as ready before launch.
- `tests/fixtures/agibot_map_context.completed.json` is an example completed
  Agibot map context artifact.
- `docs/plans/standalone-codex-operator-console.md` previously decided that
  Isaac Start is disabled until preflight/runtime-smoke evidence is accepted
  and Agibot G2 Start is disabled until context plus operator gate evidence is
  present. This plan supersedes that launch-gate behavior while preserving
  resource locks and real-movement safety.

## Problem

The current UX asks the operator to manually accept "Isaac preflight" before
starting Isaac routes. That label is too abstract for an operator. It also
duplicates what the backend can diagnose more concretely: missing Python 3.12,
missing `.venv-isaaclab`, unavailable `nvidia-smi`, package import failures,
USD scene load failures, nonblank renderer checks, and selected USD binding
failures.

The same pattern appears on real-robot routes. Context, localization, run
enablement, and E-stop readiness are important, but they are not all equivalent
route-level blockers. They should gate the capability that needs them. A dry-run
or observe/map-first route should be able to start and then prompt at the point
where motion or another higher-risk capability is requested.

## Agibot Context JSON Semantics

`context_json` means an Agibot map context artifact, not an operator acceptance
checkbox. Its schema is `agibot_gdk_map_context_authoring_v1`.

The file bridges a real Agibot GDK map into the Roboclaws public semantic map
contract. It supplies public room, fixture, and waypoint semantics for a known
Agibot map:

- `map_source`: Agibot map id/name and current-map metadata.
- `frame_id`: map coordinate frame.
- `robot_pose`: recorded robot pose provenance.
- `rooms`: public room ids, labels, and polygons.
- `fixtures`: static furniture/receptacle hints such as sofa/table/sink.
- `inspection_waypoints`: operator-recorded or verified waypoints the agent can
  use to inspect rooms and fixtures.
- `verification`: optional Agibot GDK navigation provenance for waypoints.

It must not contain private cleanup scoring truth, generated movable-object
targets, or hidden evaluator data. The current Agibot map-build route requires
this artifact because the MCP server uses it to expose `metric_map` and
`fixture_hints` before the agent can build or inspect the map.

## Product Principle

Block only dangerous or impossible actions, not the whole route surface.

- Hard launch blockers: missing provider route, occupied MCP port, active
  backend lock, disabled unsupported route, required command input missing.
- Advisory diagnostics: Isaac runtime/preflight evidence and smoke status.
- Capability gates: real movement, localization, E-stop/manual-stop visibility,
  and manipulation readiness.

## Decisions

1. Keep backend resource locks as hard blockers.
   `molmospaces_mujoco`, `isaac_gpu`, and `agibot_g2` are scarce local
   resources and conflicting starts remain invalid.

2. Keep provider route and MCP port as hard blockers.
   Without these, the console cannot launch the coding-agent route or MCP
   server successfully.

3. Make Isaac preflight non-blocking.
   The console should not require an `Isaac preflight accepted` checkbox before
   Start. Isaac readiness should appear as a diagnostic row. If the runtime is
   broken, the launched route should fail with concrete backend/preflight
   artifacts and fix guidance.

4. Keep Agibot `context_json` required for the current Agibot map-build route.
   The existing `backend=agibot_gdk semantic-map-build codex` command requires
   a completed Agibot map context artifact. Removing that requirement needs a
   deeper backend change and is out of this slice.

5. Make Agibot localization, run enablement, and E-stop evidence non-blocking
   for dry-run/observe-first launch.
   These checks should remain visible, but they should not prevent a dry-run
   route from starting.

6. Gate real movement on operator evidence.
   If `real_movement_enabled=true`, require localization, run enablement, and
   E-stop/manual-stop readiness before launch or before the first motion command.
   The implementation may choose launch-time enforcement for this slice because
   it is simpler and preserves safety.

7. Do not enable physical cleanup manipulation.
   `agibot-g2-cleanup` remains disabled because manipulation is still a blocked
   capability.

## Scope

- Update route-gate metadata to distinguish hard blockers from advisory or
  capability gates.
- Update `route_readiness()` so advisory gates do not set `can_start=false`.
- Remove or rename the Isaac checkbox from the required setup path.
- Update the UI gate list so non-blocking diagnostics do not read as required
  preconditions.
- Preserve route cards for unsupported/disabled routes with concrete reasons.
- Preserve existing backend locks and attach-to-existing-run behavior.
- Update tests that currently expect Isaac preflight and Agibot operator gates
  to block all starts.

## Non-Goals

- Do not run local Isaac, GPU, or Agibot hardware probes as part of this plan.
- Do not implement a full runtime capability engine.
- Do not change public task names or route ids.
- Do not make Isaac the default backend.
- Do not remove Agibot map context JSON from the Agibot GDK command path.
- Do not claim or enable physical manipulation.
- Do not weaken provider-key, MCP-port, or backend-lock checks.

## Expected Behavior

### Isaac Cleanup / Isaac Map Build

- Route can be selected and started without checking an Isaac preflight box.
- Setup shows Isaac runtime/preflight as diagnostic status, not a required
  acceptance checkbox.
- If an accepted marker exists at
  `output/isaaclab/runtime-preflight-accepted.json` or
  `output/isaaclab/runtime-smoke-accepted.json`, the diagnostic can show that
  evidence path.
- If no marker exists, Start is still available unless another hard blocker is
  present.
- Runtime failures should appear through existing run artifacts and launch logs.

### Agibot G2 Map Build

- Route still requires an Agibot map context JSON because the current command
  needs it.
- Dry-run launch does not require localization/run-enable/E-stop checkboxes.
- `real_movement_enabled=false` remains the default.
- If `real_movement_enabled=true`, localization, run enablement, and
  E-stop/manual-stop readiness must be accepted before the movement-capable run
  starts.

### Disabled Physical Cleanup

- Agibot G2 Cleanup remains disabled with a concrete blocked-capability reason.

## Acceptance Criteria

- Isaac Cleanup readiness returns `can_start=true` when provider and port are
  ready, no backend lock is held, and no accepted Isaac preflight marker exists.
- Isaac Map Build follows the same non-blocking preflight behavior.
- The UI no longer labels Isaac startup as needing a manual
  `Isaac preflight accepted` action.
- Agibot G2 Map Build readiness returns `can_start=true` for dry-run when
  provider, port, and Agibot map context JSON are present, even if
  localization, run-enable, and E-stop checkboxes are unset.
- Agibot G2 Map Build with `real_movement_enabled=true` remains blocked until
  localization, run-enable, and E-stop readiness are accepted.
- Backend locks still block conflicting launches and expose attachable runs.
- Provider and MCP-port failures still block launch with concrete messages.

## Verification

Run focused checks:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
.venv/bin/ruff check roboclaws/operator_console tests/unit/operator_console
```

If UI behavior changes materially, run the console locally and smoke the route
selection/readiness display:

```bash
just console::run
```

No Isaac or Agibot hardware run is required for this plan. The intent is to
correct launch UX and server-side readiness semantics, not to revalidate backend
runtime evidence.

## Implementation Notes

- `RouteGate.required` already exists but is not currently used by readiness.
  Reuse it or replace it with an explicit severity such as `blocking`,
  `advisory`, and `capability`.
- Avoid a frontend-only change. `start_console_run()` uses server-side
  readiness, so `launcher.py` must change with the UI.
- The UI can still show diagnostic rows for Isaac and Agibot. The important
  change is that these rows should not disable Start unless their capability is
  actually requested.
- For this slice, launch-time enforcement of real movement evidence is
  acceptable. A later capability-level runtime gate can move the check closer to
  the first motion tool call.

## Open Follow-Up

The deeper real-robot UX should eventually support layered route progression:

```text
connect -> observe-only -> map/localize -> navigation -> manipulation
```

This plan only changes the current console launch gates enough to stop
overblocking the operator while preserving obvious safety boundaries.
