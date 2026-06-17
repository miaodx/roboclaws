**Status:** Implemented
**Created:** 2026-06-17
**Last reviewed:** 2026-06-17
**Current implementation contract:** Sim household map surfaces should expose one static start map, one runtime semantic evidence map, and one optional prior wrapper. Preview images are review assets, not map contracts.
**Related ADRs:** ADR-0136, ADR-0143
**Supersedes / Superseded by:** Narrows the display/report cleanup portion of `refactor-reduce-entropy-minimal-semantic-map.md`; does not replace the Actionable Semantic Map Snapshot contract plan.

# Sim Map Surface Simplification

## Problem

The sim household route currently makes several different things look like
"Semantic Map":

- `runtime_metric_map.json`, the actual current-run semantic evidence.
- `actionable_semantic_map_snapshot.json`, a wrapper for passing prior runtime
  map evidence to another run.
- `fixture_hints`, an old static fixture artifact that is no longer an active
  public MCP tool.
- `semantic_map.png`, `map_overlay.json`,
  `map_bundle/report_static_navigation_map.png`, and
  `map_bundle/preview.png`, which are report or operator-console review images.

This creates false confidence. The UI can show a plausible map even when the
run has little or no runtime semantic evidence. It also makes it hard to compare
the two product paths:

```text
Base Navigation Map -> cleanup/open-ended run
Base Navigation Map -> map-build -> Runtime Metric Map prior -> cleanup/open-ended run
```

## Goal

For sim only, make the map model boring and explicit:

```text
Base Navigation Map
Runtime Metric Map
Actionable Semantic Map Snapshot
```

Only `Runtime Metric Map` is the runtime semantic map. `Actionable Semantic Map
Snapshot` is a prior/wrapper, not a fourth map. Preview images remain linked as
review assets but stop presenting themselves as semantic-map truth.

## Non-Goals

- Do not change real-robot, Agibot hardware, Isaac/B1, Nav2 pilot, or physical
  cleanup behavior in this slice.
- Do not add a new map abstraction, registry, adapter, or taxonomy object.
- Do not remove `actionable_semantic_map_snapshot_v1`.
- Do not remove historical report rendering for archived artifacts unless it is
  needed to simplify current sim reports.
- Do not change private scoring truth boundaries.
- Do not run paid/live-provider, OpenClaw, hardware, or GPU validation.

## Proposed Contract

### Base Navigation Map

Static start-of-run context. In sim it may include:

- occupancy/free-space geometry;
- public room/category hints when available;
- generated exploration candidates or inspection waypoints;
- current robot pose.

It must not include private relocation truth, generated mess truth, hidden
acceptable destinations, or a full static movable-object inventory.

### Runtime Metric Map

The only current-run semantic map. It may be produced by `preset=map-build` or
incrementally during cleanup/open-ended observations. It owns:

- `public_semantic_anchors`;
- `observed_objects`;
- `target_candidates`;
- `generated_exploration_candidates`;
- `map_update_candidates`;
- producer/provenance summaries.

MapBuild is not a separate map type. It is one producer path for
`runtime_metric_map.json`.

### Actionable Semantic Map Snapshot

Prior handoff wrapper. It packages a Runtime Metric Map for reuse by another
run, including map-build output. Cleanup/open-ended consumers should unwrap it
to Runtime Metric Map semantics.

It is not displayed as an independent map type in the sim UI.

## Proposed Cuts

Apply the cuts in two phases, but treat both phases as in scope for the
implementation run. Phase 1 removes the user-visible false confidence with
minimal behavior risk. Phase 2 deletes the operator-console generated semantic
preview. If Phase 2 creates excessive checked-in preview JSON churn, stop at the
documented stop gate and report the exact remaining files instead of silently
dropping the phase.

### Phase 1: Report And Live Artifact Truth

Do cuts 1 and 2 together.

### 1. Stop Treating `semantic_map.png` As The Map

Current files:

- `roboclaws/household/report_semantic_map_artifacts.py`
- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/operator_console/state.py`
- `tests/contract/reports/test_molmo_cleanup_report.py`
- `tests/contract/molmo_cleanup/test_realworld_mcp_live_artifacts.py`

Change:

- Stop generating new `semantic_map.png` and `map_overlay.json` for current
  sim reports when the same information is already present in
  `runtime_metric_map.json` and report tables.
- Stop publishing `semantic_map.png` from live public artifact refresh for
  current sim runs.
- Operator console should not prefer `semantic_map.png` as the map slot for sim
  current runs.
- If old artifacts exist, label them as legacy preview images, not runtime
  semantic maps.

Keep:

- `runtime_metric_map.json` artifact link.
- `actionable_semantic_map_snapshot.json` as a prior artifact link labeled as a
  wrapper or Runtime Map Prior, not an image map slot.
- `map_bundle/preview.png` as the static map preview.
- `topdown` as scene visual evidence, not a map contract.

### 2. Collapse Static Preview Paths

Current files:

- `roboclaws/household/report_sections_nav2_map.py`
- `roboclaws/maps/bundle.py`

Change:

- Prefer `map_bundle/preview.png` as the static map image.
- Keep `map_bundle/report_static_navigation_map.png` only as a degenerate-frame
  fallback for current sim reports. A report should use `map_bundle/preview.png`
  when the source occupancy preview has usable framing.
- Rename report copy from "Semantic Map" to "Static Navigation Map" or "Base
  Navigation Map Preview".

Keep:

- `write_source_frame_bundle_preview()` as the single static preview writer.

### Phase 2: Operator-Console Preview Deletion

Do cut 3 after Phase 1 lands cleanly. It remains part of this plan's scope.

### 3. Delete Operator-Console Semantic Preview Projection

Current files:

- `scripts/operator_console/semantic_map_preview.py`
- `scripts/operator_console/render_scene_previews.py`
- `roboclaws/operator_console/static/previews/*.json`
- `tests/unit/operator_console/test_render_scene_previews.py`

Change:

- Remove the custom `operator_console_semantic_map_projection_v1` preview path
  for sim current routes after report/static-preview naming is cleaned up.
- Let the console show static map preview plus top-down scene view. Do not draw
  a third "semantic map" from simulator state.

Rationale:

The preview renderer blends simulator state, room outlines, receptacles,
objects, path, and generated waypoint projection. That is useful as a visual
debug overlay, but it is not the semantic map contract and makes the product
look more map-aware than the run evidence proves.

### 4. Keep `fixture_hints` Internal/Historical

Current files:

- `roboclaws/household/realworld_contract.py`
- `roboclaws/household/realworld_contract_payloads.py`
- `roboclaws/household/realworld_runtime_map_contract.py`
- report/tests that still display fixture hints.

Change:

- Do not count `fixture_hints` as a map type in current sim docs or UI.
- Keep it only where current code still needs it to construct Runtime Metric
  Map static payloads, visual-grounding helper inputs, or historical reports.
- Do not re-expose it as a public MCP tool.

## Acceptance Criteria

- Current sim UI/report names exactly these map concepts:
  - Base Navigation Map;
  - Runtime Metric Map;
  - Actionable Semantic Map Snapshot only when showing a prior artifact.
- New sim reports do not present `semantic_map.png` as the main map.
- Live public artifacts do not publish `semantic_map.png` as current sim map
  evidence.
- Operator console map slot does not prefer `semantic_map.png` for current sim
  runs.
- `actionable_semantic_map_snapshot.json` remains visible only as a prior
  artifact link, not as an independent map image or fourth map concept.
- Static map image source is `map_bundle/preview.png` by default. The only
  current fallback is `map_bundle/report_static_navigation_map.png` for
  degenerate source occupancy framing.
- Runtime semantic evidence is shown from `runtime_metric_map.json` counts and
  tables, not inferred from a drawn PNG.
- Cleanup/open-ended still runs without prior map-build output.
- Cleanup/open-ended can still consume a prior map-build Runtime Metric Map or
  Actionable Snapshot.
- `fixture_hints` remains absent from current public MCP tool lists.
- The existing `map_build_consumer` eval suite still exercises the prior flow:
  `map_build.baseline_seed7 -> cleanup.consume_map_seed7`.

## Verification

Use the eval harness first:

```bash
just agent::eval recommend plan=docs/plans/2026-06-17-sim-map-surface-simplification.md budget=focused
just agent::eval execute plan=docs/plans/2026-06-17-sim-map-surface-simplification.md budget=focused
```

Focused deterministic gates:

```bash
./scripts/dev/run_pytest_standalone.sh \
  tests/contract/reports/test_molmo_cleanup_report.py \
  tests/contract/maps/test_actionable_semantic_map_snapshot.py \
  tests/unit/operator_console/test_state.py \
  tests/unit/operator_console/test_render_scene_previews.py \
  tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py \
  tests/contract/molmo_cleanup/test_realworld_mcp_live_artifacts.py \
  tests/unit/evals/test_eval_runner.py \
  -q
```

Prior/no-prior comparison gate:

```bash
just agent::eval suite=map_build_consumer budget=smoke
```

Product smoke gates, if local sim runtime is available:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=grounding-dino seed=7 scenario_setup=baseline
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5
```

Manual review:

- Open the report and operator console artifact view.
- Confirm visual labels do not imply runtime semantic evidence when only static
  map preview exists.
- Compare no-prior cleanup/open-ended run against cleanup/open-ended with a
  map-build prior and record counts/trace summaries. Do not make improvement a
  hard gate for this refactor unless the existing `map_build_consumer` eval
  fails.

## Risks

- Some tests and docs currently assert `semantic_map.png` exists. Those should
  be rewritten to assert runtime map evidence and static preview links instead.
- `fixture_hints` is still an internal data path in sim. Removing it entirely is
  larger than this slice and would touch cleanup target resolution, visual
  grounding helpers, and historical report compatibility.
- Operator-console generated static preview JSON files may need regeneration or
  schema simplification.
- Deleting the operator-console semantic preview may produce noisy fixture
  churn. If that churn obscures review, the executor must stop and report
  `BLOCKED_NEEDS_DECISION` with the generated-file diff size and exact files,
  not mark the plan complete.

## Reduce-Entropy Review

Selected mode: plan entropy mode.
Discovery intensity: selection scan.

Selected candidates:

1. P1: Keep the static preview fallback bounded instead of deleting it outright.
   Demand gate: pass, because current report tests already cover degenerate
   occupancy framing and removing the fallback would trade one misleading map
   image for a broken report preview. Owner: implementation. Proof:
   `tests/contract/reports/test_molmo_cleanup_report.py`.
2. P1: Make the prior/no-prior comparison explicit. Demand gate: pass, because
   the user's core uncertainty is whether both sim paths still work and whether
   map-build prior improves behavior. Owner: eval/product verification. Proof:
   `just agent::eval suite=map_build_consumer budget=smoke` plus one no-prior
   cleanup/open-ended smoke when local sim is available.
3. P2: Split operator-console generated preview deletion if it creates large
   checked-in artifact churn. Demand gate: pass, because the deletion is useful
   but not required to remove the immediate report false confidence. Owner:
   implementation. Proof: focused operator-console tests and a before/after
   artifact view.

## Grill-Batch Decisions

Accepted on 2026-06-17:

- Add **Base Navigation Map** to `docs/human/domain.md` because ADR-0136 already
  uses it as a public contract term.
- Implement Phase 1 first, then Phase 2 in the same flow run. Phase 2 may stop
  only at the generated-preview churn gate.
- Stop the live MCP artifact refresh path from writing `semantic_map.png` for
  current sim map evidence.
- Keep prior/no-prior comparison lightweight: use existing `map_build_consumer`
  plus one no-prior comparison summary, not a new benchmark or metric system.
- Show `actionable_semantic_map_snapshot.json` only as a prior wrapper/runtime
  map prior artifact link, never as an independent map image slot.

Parked items:

- Full removal of internal `fixture_hints` remains out of scope.
- Real-robot, Agibot hardware, Isaac/B1, and physical Nav2 map preview behavior
  remain out of scope.

Recommended next action: execute the full preflight contract below with
`intuitive-flow`.

Shortcut: `execute this`

## Preflight Contract

Preflight status: DRAFT

Task source: plan path plus user confirmation that all phases should be
implemented.

Canonical source:
`docs/plans/2026-06-17-sim-map-surface-simplification.md`

Route: durable `$intuitive-flow`

Goal: Implement the full sim map surface simplification so current sim reports,
live artifacts, and operator-console map previews stop treating generated
preview images as semantic-map truth while preserving Runtime Metric Map and
prior-map flows.

Scope:

- Phase 1: stop current sim report/live artifact paths from publishing
  `semantic_map.png` / `map_overlay.json` as map truth.
- Phase 1: make static map preview naming use Base Navigation Map / Static
  Navigation Map language and prefer `map_bundle/preview.png` with the bounded
  `report_static_navigation_map.png` fallback only for degenerate source
  occupancy framing.
- Phase 1: make operator-console artifact selection stop preferring
  `semantic_map.png` for current sim map slots and keep
  `actionable_semantic_map_snapshot.json` as a prior wrapper artifact link.
- Phase 2: remove the sim operator-console
  `operator_console_semantic_map_projection_v1` generated preview path and
  associated tests/fixtures, unless the generated-preview churn stop gate
  triggers.
- Update focused tests and docs only where required to reflect the surviving
  concepts: Base Navigation Map, Runtime Metric Map, and Actionable Semantic
  Map Snapshot as prior wrapper.

Non-goals:

- No real-robot, Agibot hardware, Isaac/B1, Nav2 pilot, or physical cleanup
  behavior changes.
- No new map abstraction, registry, adapter, taxonomy object, or compatibility
  bridge.
- No removal of `actionable_semantic_map_snapshot_v1`.
- No full removal of internal/historical `fixture_hints`.
- No private scoring truth boundary change.
- No paid/live-provider, OpenClaw, hardware, or GPU validation as required
  proof for completion.

Entity budget:

- reuse: existing `runtime_metric_map.json`, `actionable_semantic_map_snapshot.json`,
  `map_bundle/preview.png`, Runtime Metric Map report tables, eval harness, and
  `map_build_consumer` suite.
- remove/merge: remove or narrow current-sim use of `semantic_map.png`,
  `map_overlay.json`, `report_static_navigation_map.png` as default preview,
  and `operator_console_semantic_map_projection_v1`.
- new: no new production entities. Test updates may add/rename focused test
  cases only if replacing old assertions.
- expansion triggers: any new map schema, new report artifact contract, new UI
  slot, broad fixture regeneration beyond Phase 2 files, or `fixture_hints`
  removal requires re-approval.

Context:

- must-read: `docs/plans/2026-06-17-sim-map-surface-simplification.md`,
  `docs/human/domain.md`, ADR-0136, ADR-0143,
  `roboclaws/household/report_semantic_map_artifacts.py`,
  `roboclaws/household/report_sections_nav2_map.py`,
  `roboclaws/household/realworld_mcp_server.py`,
  `roboclaws/operator_console/state.py`,
  `scripts/operator_console/semantic_map_preview.py`,
  `scripts/operator_console/render_scene_previews.py`,
  relevant report/operator-console/live-artifact tests.
- useful: `tests/contract/maps/test_actionable_semantic_map_snapshot.py`,
  `tests/unit/evals/test_eval_runner.py`,
  `evals/household_world/suites/map_build_consumer.json`,
  `evals/household_world/samples/cleanup/consume_map_seed7.json`.
- avoid-unless-needed: real-robot, Agibot hardware, Isaac/B1, visual-grounding
  benchmark, historical output folders, broad generated report fixtures.

Acceptance:

- SUCCESS: current sim reports and live public artifacts no longer present
  `semantic_map.png` or `map_overlay.json` as semantic-map truth; static preview
  language is Base/Static Navigation Map; Runtime Metric Map evidence remains
  visible from JSON/tables; Actionable Snapshot appears only as a prior wrapper
  artifact link; operator-console current sim map slot no longer prefers
  `semantic_map.png`; Phase 2 preview projection is removed or reaches the
  explicit churn stop gate.
- BLOCKED_NEEDS_DECISION: generated operator-console preview deletion produces
  broad checked-in fixture churn that would obscure review; any required new
  map/schema/UI surface appears; removing internal `fixture_hints` becomes
  necessary to proceed.
- BLOCKED_NEEDS_LOCAL_VALIDATION: local MolmoSpaces/MuJoCo product smoke cannot
  run in the execution environment. Code/test work may still be complete, but
  product-run proof is missing until local validation runs.
- INTERMEDIATE_ONLY: none unless explicitly approved later.
- No regressions: cleanup/open-ended still runs without prior map-build output;
  cleanup/open-ended still consumes raw Runtime Metric Map or Actionable
  Snapshot priors; `fixture_hints` remains absent from current public MCP tool
  lists; historical report reading is not intentionally broken.

Verification:

- deterministic:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py tests/contract/maps/test_actionable_semantic_map_snapshot.py tests/unit/operator_console/test_state.py tests/unit/operator_console/test_render_scene_previews.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/molmo_cleanup/test_realworld_mcp_live_artifacts.py tests/unit/evals/test_eval_runner.py -q`
- integration:
  `just agent::eval recommend plan=docs/plans/2026-06-17-sim-map-surface-simplification.md budget=focused`
  and
  `just agent::eval execute plan=docs/plans/2026-06-17-sim-map-surface-simplification.md budget=focused`
- product-run:
  `just agent::eval suite=map_build_consumer budget=smoke`
- local-live-manual:
  if local sim runtime is available, run the direct map-build and direct cleanup
  commands in this plan, then inspect report/operator-console artifact labels.
  If unavailable, report `BLOCKED_NEEDS_LOCAL_VALIDATION` for product smoke.
- optional:
  one no-prior vs prior cleanup/open-ended comparison summary; not a hard
  improvement gate unless existing `map_build_consumer` fails.

Execution:

- main: root supervisor owns the full flow, reviews diffs for scope creep, and
  makes the final complete/blocked judgment.
- worker: none by default.
- worker-goal: none.

To execute:
`/goal execute docs/plans/2026-06-17-sim-map-surface-simplification.md with intuitive-flow`

Optional tracking: none.

Approval: LGTM/approve/go ahead approves; edits request revision.

## Stop Condition

Stop when a maintainer looking only at a current sim report can answer:

```text
What map did the run start from?
What semantic evidence did the run build?
Was a prior map-build result consumed?
```

without reading a generated PNG as semantic truth.

## Implementation Closeout

Implemented on 2026-06-17.

- Current sim report/live artifact paths no longer generate or publish
  `semantic_map.png` or `map_overlay.json` as map evidence.
- Report and operator-console map copy now uses Base Navigation Map / Static
  Navigation Map language and prefers `map_bundle/preview.png`; the
  `report_static_navigation_map.png` path remains only as the degenerate-frame
  fallback.
- `actionable_semantic_map_snapshot.json` remains linked as `Runtime Map Prior`
  instead of an independent map image slot.
- The sim operator-console generated
  `operator_console_semantic_map_projection_v1` preview path was removed,
  along with its checked-in preview metadata.
- `docs/human/domain.md` now defines Base Navigation Map as the start-of-run
  map context.

Verification:

- `python -m py_compile` for touched report, MCP, operator-console, and preview
  modules: passed.
- Focused deterministic pytest gate from this plan: passed.
- `just agent::eval suite=map_build_consumer budget=smoke`: passed all 3
  samples, result
  `output/evals/household_world_map_build_consumer/20260617T160839/eval_results.json`.
- `just agent::eval recommend plan=docs/plans/2026-06-17-sim-map-surface-simplification.md budget=focused`:
  passed, manifest `output/eval-harness/20260617T080420Z/eval_harness.json`.
- `just agent::eval execute ...` was intentionally stopped because the harness
  selected live Codex/provider rows; live-provider validation is a non-goal for
  this plan.

Remaining proof not required for this slice:

- Direct MolmoSpaces product smoke can still be run locally for extra visual
  confidence, but paid/live-provider, OpenClaw, hardware, GPU, and broader
  simulator validation remain outside the required completion gate.
