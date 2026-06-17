---
plan_scope: operator-console-cleanup-setup-readiness
status: Draft; grill batch and oracle-boundary decisions accepted
created: 2026-06-16
last_reviewed: 2026-06-16
implementation_allowed: false
source:
  - user report that Cleanup was disabled for `molmospaces/val_2` while Try Mess-up succeeded
  - reduce-entropy pass on operator-console cleanup intent and mess-up preview drift
  - grill-batch Batch 1 accepted on 2026-06-16
  - 2026-06-16 follow-up: server and MCP must not expose simulator oracle truth;
    architecture and implementation should target real-robot deployment parity
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - docs/human/molmospaces-settings.md
  - docs/plans/2026-06-15-molmospaces-scene-sampler-readiness.md
  - roboclaws/operator_console/routes.py
  - roboclaws/operator_console/messup.py
  - roboclaws/operator_console/launcher.py
  - roboclaws/operator_console/static/app.js
architecture_layers:
  - Runnable Surfaces And Presets
  - Thin Runtime / Server Adapters
  - Backend Runtime / Environment Primitive
---

# Operator Console Cleanup Setup Readiness

## Problem

The operator console currently mixes two different concepts:

- Whether `Cleanup` is a selectable task intent for a UI-visible MolmoSpaces
  MuJoCo scene.
- Whether the selected cleanup environment setup can generate the requested
  relocated cleanup targets.

That creates a misleading UI state. `molmospaces/val_2` can pass the live
mess-up preview for 5 generated cleanup targets on this host, but the route
catalog disables `Cleanup` because it uses a stale static cleanup-ready scene
allowlist. Conversely, `molmospaces/val_5` is statically enabled for cleanup
while the live mess-up preview can currently generate only 4 targets for the
default count of 5.

## Contract Decision

`Cleanup` selection and cleanup setup readiness must be separate:

1. `Cleanup` should be selectable for every UI-visible MolmoSpaces MuJoCo scene.
2. For `Cleanup`, the operator must make an explicit setup choice before start:
   `Mess-up with N objects` or `No mess-up / baseline`.
3. If the operator chooses mess-up and the capacity check fails, `Start Agent
   Run` must be blocked until the operator reduces `relocation_count`, changes
   setup, or switches to baseline.
4. Baseline cleanup is allowed from the console, but the UI and recorded launch
   state must make clear that it is not a relocated cleanup challenge.
5. Mess-up readiness should be checked automatically when cleanup plus relocation
   is selected, with a manual recheck action available for operator confidence.
6. `relocation_count` is challenge scale only. It is not a maximum number of
   objects the agent may clean; cleanup may act on more public observed
   candidates than were relocated.
7. Server and MCP implementation must stay real-robot-oriented: no simulator
   oracle, hidden mess membership, hidden acceptable destinations, global
   movable-object inventory, or scorer truth may be used as agent-facing
   context, policy input, readiness hints, route metadata, or MCP tool output.
   Simulator-backed public labels may exist only as provenance-labeled
   perception/map evidence that could be replaced by a deployable camera/map
   backend.

## Scope

- Remove the static MolmoSpaces cleanup-ready scene allowlist from the operator
  console route catalog.
- Keep public `run::surface` semantics unchanged: `preset=cleanup`,
  `scenario_setup=baseline`, and relocation setups remain valid public inputs.
- Add cleanup setup readiness to the operator-console readiness path used by the
  browser and by `start_console_run`.
- Make frontend setup state explicit: relocation pending, relocation ready,
  relocation failed, or baseline acknowledged.
- Update focused operator-console tests around `val_2`, `val_5`, failed
  mess-up capacity, reduced `relocation_count`, and baseline acknowledgment.

## Non-Goals

- Do not make all MolmoSpaces scenes visible in the operator scene rail.
- Do not change the public launch-axis vocabulary.
- Do not expose private scorer truth or static hidden target manifests in the
  route catalog.
- Do not silently fall back from failed relocation to baseline.
- Do not add cleanup strategy to the server adapter; this is launch readiness
  and environment setup validation only.
- Do not couple `done()` hints or cleanup-readiness blockers to the generated
  mess set. Those hints must remain derived from public Agent View state,
  public observations, and public tool traces.

## Acceptance Gates

- `molmospaces/val_2` shows `Cleanup` as selectable in the operator console.
- Choosing cleanup plus relocation for `val_2` with `relocation_count=5` can
  pass setup readiness and enable start when the normal provider/port gates are
  also ready.
- Choosing cleanup plus relocation for a scene/count that cannot generate enough
  targets blocks start with a message that tells the operator to reduce the
  count or switch to baseline.
- Choosing baseline/no mess-up for cleanup is explicit and startable, and the
  launch payload uses `scenario_setup=baseline` with no `relocation_count`.
- Backend launch validation rejects an unchecked or failed relocation setup even
  if a browser bypasses frontend state.
- MCP active tools and server adapter launch metadata do not expose simulator
  oracle fields such as `generated_mess_set`, `acceptable_destination_sets`,
  `private_manifest`, `global_movable_object_inventory`, or
  `target_receptacle_id`.
- Cleanup `done()` blocked hints are based on public cleanup worklist, public
  sweep coverage, and public tool-trace evidence, not hidden setup/scorer truth.
- A cleanup run with `relocation_count=1` can still clean multiple public
  observed candidates when the agent observes plausible objects to tidy; only
  private relocated-target scoring remains bounded by the generated challenge.

## Verification

- Focused unit tests:
  - route catalog exposes cleanup for all UI-visible MolmoSpaces MuJoCo worlds;
  - cleanup setup readiness passes for a fixture with enough eligible targets;
  - cleanup setup readiness blocks for a fixture with too few eligible targets;
  - baseline cleanup drops relocation count;
  - `start_console_run` enforces the same setup readiness as the browser.
- Browser dogfood:
  - `molmospaces/val_2` cleanup with relocation count 5;
  - `molmospaces/val_5` cleanup with relocation count 5 then reduced count;
  - baseline cleanup explicit path.
- Privacy boundary checks:
  - agent-view checker still rejects forbidden private keys;
  - MCP tool list does not include `fixture_hints` as an active callable tool;
  - `done()` readiness blockers assert `policy_uses_private_truth=false`;
  - structured simulator evidence is clearly provenance-labeled and replaceable
    by deployable perception/map inputs.

## Open Implementation Defaults

- Cache or debounce automatic mess-up readiness checks if live inventory loading
  is slow.
- Keep the manual action label as `Recheck Mess-up` after the first automatic
  check.
- Store only non-sensitive setup readiness evidence in operator state.
