---
plan_scope: drop-world-oracle-labels
status: IMPLEMENTED
created: 2026-06-16
last_reviewed: 2026-06-16
implemented: 2026-06-16
implementation_allowed: true
source:
  - user request to aggressively simplify evidence lanes by dropping world-oracle-labels
  - 2026-06-16 follow-up: simulator defaults should stay as close to real-robot deployment as possible
  - 2026-06-16 follow-up: fake visual-grounding transports must not substitute for deployable sidecars
related_context:
  - README.md
  - ARCHITECTURE.md
  - AGENTS.md
  - docs/adr/0143-drop-world-oracle-labels-evidence-lane.md
  - docs/adr/0138-use-detector-only-visual-grounding-sidecar.md
  - docs/plans/refactor-evidence-lane-naming.md
  - docs/human/molmospaces-visual-grounding-results.md
  - docs/human/agibot-g2-cleanup-pilot.md
  - roboclaws/household/profiles.py
  - roboclaws/household/realworld_contract.py
  - roboclaws/operator_console/routes.py
  - skills/eval-harness/scripts/eval_harness_rows.py
---

# Drop World Oracle Labels And Align Camera Defaults

## Goal

Delete `world-oracle-labels` as an active household evidence lane. The simulator
structured-label path that remains is `world-public-labels`: structured public
detections with destination/tool oracle hints and pre-confirmed navigation
authorization removed.

Also make deployment-like simulator defaults use the same perception route as a
real robot: `evidence_lane=camera-grounded-labels` with
`camera_labeler=grounding-dino`, especially for `preset=map-build`.
`world-public-labels` remains the deterministic structured-simulator contract
baseline for CI, smoke, and cheap debugging, not the product proof default for
real-robot-facing map evidence.

This is intentionally more aggressive than making Oracle maintainer-only. The
project has no backward-compatibility requirement for obsolete demo surfaces,
and the current public/private boundary is clearer if the privileged upper-bound
lane disappears instead of being renamed or hidden.

## Decision

Current public evidence lanes become exactly:

```text
world-public-labels
camera-grounded-labels
camera-raw-fpv
```

`smoke` remains a synthetic verification preset, not an evidence lane. Smoke
runs should emit `preset=smoke` plus `evidence_lane=world-public-labels`.

ADR-0143 records the durable contract decision. This plan supersedes the
`world-oracle-labels` parts of `docs/plans/refactor-evidence-lane-naming.md`
and the ADR-0138 wording that still treated sim/fake labelers as current
runtime choices. The two-axis model `evidence_lane` plus `camera_labeler`
remains valid; only the privileged world lane is removed.

Active camera labelers become deployable producers only. `grounding-dino` is
the default real camera labeler. `yoloe`, `yolo-world`, and `omdet-turbo`
remain comparison producers. `sim-projected-labels`, `fake-http`, and
`contract-fake` are removed from public/operator/product support because they
cannot run on a real robot and would let simulator validation pass through a
non-deployable path. Runnable fake sidecar or benchmark routes must not remain
as current validation proof. Delete or disable runnable fake service paths such
as selectable fake sidecar pipelines, fake harness defaults, and fake benchmark
defaults; do not keep them as a hidden shortcut for "contract validation." If
any low-level unit test still needs fixture data, keep that as private static
test data, not as a selectable `camera_labeler`, sidecar pipeline, harness
default, or launch route.

Default routing after this plan:

```text
CI/smoke/contract baseline:
  evidence_lane=world-public-labels

Simulator product map-build and real-robot-facing proof:
  evidence_lane=camera-grounded-labels camera_labeler=grounding-dino

Simulator cleanup structured baseline for this slice:
  evidence_lane=world-public-labels

Camera-only ablation:
  evidence_lane=camera-raw-fpv
```

## Pushback Resolved

Deleting Oracle removes a useful upper-bound diagnostic. That is acceptable here
because the ongoing architecture direction values honest public agent inputs
over a privileged cleanup baseline. If later work needs an upper-bound
diagnostic, it should be introduced as a private eval fixture or scorer-only
control, not as an agent-visible evidence lane.

Deleting `sim-projected-labels`, `fake-http`, and `contract-fake` removes a
convenient deterministic camera-grounded control. That is acceptable, and
intentional: if the simulator cannot run the deployable perception path, the
real robot has no credible path to success. Camera-grounded routes must fail
aloud and early when the real sidecar is missing or unhealthy, not hide the
problem behind fake candidates, contract fake responses, or simulator
projection.

## Grill Decisions

- ADR treatment: create ADR-0143 because deleting Oracle changes the durable
  public evidence-lane contract and supersedes accepted ADR-0136 wording.
- Smoke metadata: use `preset=smoke` plus
  `evidence_lane=world-public-labels`; do not introduce a synthetic evidence
  lane and do not omit evidence-lane identity from smoke artifacts.
- Verification strictness: Public inherits the current structured-world product
  gates where relevant, including waypoint honesty, real-robot alignment,
  semantic accepted count, and sweep coverage.
- Private oracle language: private scorer truth and unrelated rendering
  diagnostics may keep the word `oracle`, but they must not accept or expose
  `world-oracle-labels` as an agent evidence lane.
- Historical docs: do not bulk-rewrite old implemented plans, retrospectives,
  or output evidence. Update current orientation docs, active plan surfaces,
  tests, and runbooks.
- Realism default: simulator product/default map-build routes should prefer
  `camera-grounded-labels` + `grounding-dino`; `world-public-labels` is the
  deterministic structured-world baseline.
- Fake/sim camera labels: remove `sim-projected-labels`, `fake-http`, and
  `contract-fake` from active public/operator camera-labeler support and from
  runnable current validation routes. Tests should either exercise the
  deployable sidecar path, use private non-runnable static payloads for parser
  coverage, or fail/skip with explicit blocked evidence.
- ADR-0138 supersession: ADR-0143 narrows ADR-0138's detector-only sidecar
  contract by removing the sim/fake labelers it previously allowed as current
  runtime choices.
- Map-build vs cleanup default: product/default simulator `preset=map-build`
  uses `camera-grounded-labels camera_labeler=grounding-dino`; cleanup
  structured baselines use `world-public-labels` in this slice because physical
  cleanup still has blocked manipulation proof.
- Missing sidecar semantics: Grounding-DINO product proof routes fail clearly,
  preferably with blocked/missing-sidecar evidence. Eval-harness rows may
  record blocked preflight packets. Neither path may silently fall back to sim
  projection or fake transport.

## Owning Layers

- Runnable surfaces and presets: `surface=household-world` structured-world
  baselines move to `world-public-labels`; simulator product map-build and
  real-robot-facing proof defaults move to `camera-grounded-labels` with
  `camera_labeler=grounding-dino`.
- Capability profile / MCP contract: agent-visible world detections use the
  sanitized public policy.
- Thin runtime / server adapters: launch and operator-console defaults stop
  accepting Oracle and stop selecting simulator-projected camera labels.
- Eval harness and eval suites: product rows, samples, and row ids use Public.
- Visual grounding sidecar: active camera-labeler defaults use the detector-only
  sidecar route recorded in ADR-0138, with `grounding-dino` as the real default.
  ADR-0143 supersedes ADR-0138's older sim/fake runtime-choice wording.
- Verification gates: camera-grounded product and eval gates require real
  sidecar readiness. Missing sidecar is a blocker, not a fake fallback.
- Reports and checkers: report metadata and validation expectations no longer
  describe Oracle as a current lane.
- Human docs and agent guidance: examples and lane lists remove Oracle.

## Current Evidence

- `roboclaws/household/profiles.py` registers both `WORLD_ORACLE_LABELS_LANE`
  and `WORLD_PUBLIC_LABELS_LANE`. Oracle metadata says the agent receives
  cleanup-ready destination hints; Public metadata says those hints are
  withheld.
- `roboclaws/household/realworld_contract_init.py` sets
  `sanitize_world_labels` only when `evidence_lane == world-public-labels`.
- `roboclaws/household/realworld_contract.py` has sanitized payload code that
  removes `candidate_fixture_id`, `candidate_fixture_category`,
  `cleanup_recommended`, and `recommended_tool`.
- `roboclaws/household/tasks.py`, `just/agent.just`, `just/molmo.just`,
  `roboclaws/operator_console/routes.py`, and
  `roboclaws/operator_console/static/app.js` default to Oracle in multiple
  paths.
- `roboclaws/operator_console/routes.py` sets `SIMULATION_CAMERA_LABELER` to
  `sim-projected-labels`, so simulator camera-grounded routes currently default
  to a non-deployable perception producer.
- `docs/human/molmospaces-visual-grounding-results.md` records
  `camera_labeler=grounding-dino` as the default real camera labeler and keeps
  `sim-projected-labels` only as a control baseline.
- `docs/human/agibot-g2-cleanup-pilot.md` already treats
  `camera-grounded-labels` + `grounding-dino` as the hardware-facing map-build
  acceptance route.
- Eval samples under `evals/household_world/samples/**`, eval-harness rows, CI
  live report rows, scene-sampler helpers, and many tests assert Oracle names.

## Scope

### 1. Registry And Metadata

- Remove `WORLD_ORACLE_LABELS_LANE` as a selectable lane.
- Remove `WORLD_LABELS_PROFILE` as an alias for Oracle, or rename compatibility
  constants to public names instead of keeping misleading Oracle-shaped names.
- Make `cleanup_evidence_lane_names()` return only:
  `world-public-labels`, `camera-grounded-labels`, `camera-raw-fpv`.
- Make `evidence_lane("world-oracle-labels")` fail.
- Make `infer_evidence_lane_name(...)` return `world-public-labels` for
  structured world-label backends.
- Make `evidence_lane_metadata_for_run(...)` emit Public metadata for structured
  world-label runs, including synthetic smoke unless smoke gets a separate
  synthetic preset marker.
- Remove `SIM_PROJECTED_LABELS_CAMERA_LABELER` from the active public
  `CAMERA_LABELERS` set. Keep any simulator-projection helper only as private
  test/support code if needed.
- Remove `fake-http` and `contract-fake` from the active public
  `CAMERA_LABELERS` set and current launch/operator/eval surfaces.
- Remove runnable `fake-http` / `contract-fake` sidecar, pipeline, harness, and
  benchmark defaults from current validation proof. Contract/parser tests may
  keep private static fixture payloads, but those fixtures must not be
  selectable through `camera_labeler`, sidecar pipeline ids, just recipes,
  benchmark defaults, or operator-console routes.
- Make `grounding-dino` the default real camera labeler for active simulator and
  real-robot-facing `camera-grounded-labels` routes.

### 2. Contract Behavior

- Ensure structured world-label agent-visible payloads are sanitized by default.
- Remove branches where the non-sanitized world-label path exposes destination
  or tool hints to the agent.
- Preserve public destination policy fields when they are category-affordance
  policy, not hidden target truth.
- Preserve private scorer truth and report-only private artifacts outside the
  agent view.
- Remove `_target_candidate_evidence_lane()` fallback to Oracle.

### 3. Launch And Runtime

- Change `household-world` structured-world default profile to
  `world-public-labels`.
- Change simulator product map-build defaults and examples to
  `evidence_lane=camera-grounded-labels camera_labeler=grounding-dino`.
- Keep cleanup structured-baseline defaults on `world-public-labels` for this
  slice; do not make physical cleanup claims until manipulation proof is no
  longer blocked.
- Do not silently fall back from `grounding-dino` to `sim-projected-labels` when
  the visual-grounding sidecar is unavailable. Product proof routes should fail
  non-zero after writing blocked/missing-sidecar evidence when possible; eval
  harness rows should record blocked preflight packets.
- Remove Oracle from `run::surface`, private `molmo::household-world-impl`, and
  related validation error messages.
- Decide and encode smoke lowering:
  `run_preset=smoke` uses `preset=smoke` plus
  `evidence_lane=world-public-labels`.
- Replace Oracle-specific default seed/output-directory branches with Public or
  remove the special case.
- Update coding-agent kickoff prompts so the default lane is Public.
- Update CI live matrix entries from Oracle to Public, including generated-mess
  defaults and status labels.

### 4. Operator Console

- Remove Oracle from evidence-lane dropdown options.
- Change console route ids, defaults, launch args, history fixtures, and UI
  fallback value to `world-public-labels`.
- Keep `camera-grounded-labels` requiring `camera_labeler`.
- Change MolmoSpaces simulator camera-grounded defaults from
  `sim-projected-labels` to `grounding-dino`.
- Remove `sim-projected-labels` from operator-visible camera-labeler choices.
- Surface missing visual-grounding sidecar readiness as a blocker for
  `grounding-dino` routes instead of degrading to simulator projection.
- Keep Isaac support rules accurate after Public becomes the structured
  world-label lane.

### 5. Eval Harness And Eval Suites

- Rename eval-harness row ids such as `household-direct-world-oracle-product`
  and `direct-map-build-world-oracle` to Public equivalents.
- Add or promote a deployment-like map-build product/eval row:
  `camera-grounded-labels` + `grounding-dino`. This is the real-robot-facing
  proof row; Public remains the deterministic structured-world baseline row.
- Change eval sample JSON files from Oracle to Public.
- Change runtime-map-prior references that include Oracle row ids.
- Ensure cleanup/product gates still check waypoint honesty, real-robot
  alignment, semantic accepted count, and sweep coverage where they remain
  relevant for Public.
- Remove tests that compare Oracle against Public as separate active lanes.
- Remove `sim-projected-labels` rows from active eval/product recommendations.
- Remove `fake-http` and `contract-fake` rows from active eval/product
  recommendations. If the real sidecar is unavailable, the camera-grounded row
  must be reported as blocked, not replaced by a fake row.
- Remove fake visual-grounding defaults from benchmark and harness recipes; a
  visual-grounding benchmark either uses a deployable producer or records
  blocked/missing-sidecar evidence. Do not preserve runnable fake service paths
  as current "contract validation" proof.

### 6. Agibot And Scene-Sampler Helpers

- Remove Oracle from Agibot map-build accepted lane lists and pre-hardware
  rehearsal lane normalization.
- Update scene-sampler scanner commands and generated sample templates to
  Public.
- Update apple2apple and model-matrix catalog references only where they refer
  to household evidence lanes; leave unrelated rendering oracle diagnostics
  alone.

### 7. Tests And Docs

- Update tests to assert the active lane set is exactly Public, camera-grounded,
  and raw-FPV.
- Update tests to assert the active product camera-labeler default is
  `grounding-dino` and that `sim-projected-labels`, `fake-http`, and
  `contract-fake` are rejected by public launch and operator-console paths.
- Keep tests that prove Public omits destination/tool oracle fields.
- Remove or rewrite Oracle-specific prompt, report, checker, operator-console,
  eval-harness, and CI-live expectations.
- Remove current runbook instructions that start `fake-http` or `contract-fake`
  services as validation evidence. Historical result tables may keep them only
  when clearly labeled as historical or non-product evidence, and any schema
  tests should use private static payloads rather than a runnable fake service.
- Update README, ARCHITECTURE, AGENTS, CLAUDE, `just/README.md`, and current
  human docs to remove Oracle from active commands.
- Mark historical plan references as historical when they are not current run
  guidance; do not bulk-rewrite shipped retrospectives or old evidence logs.

## Non-Goals

- No operator-console cleanup setup readiness, mess-up capacity/count gating,
  baseline/no-mess-up acknowledgement, or start-blocking cleanup-readiness UX.
  That is a separate follow-up plan.
- No compatibility alias from `world-oracle-labels` to `world-public-labels`.
- No maintainer-only Oracle lane.
- No new replacement `sim-oracle-upper-bound` lane in this slice.
- No change to the `camera-grounded-labels` observation/declaration contract
  shape. This plan does change the active camera-labeler set and defaults.
- No changes to `camera-raw-fpv` model-declared observation semantics.
- No private scorer truth removal.
- No bulk rewrite of historical output artifacts.

## Execution Order

1. Update the evidence-lane registry and focused profile tests first.
2. Make structured world-label contract behavior default to sanitized Public.
3. Remove `sim-projected-labels`, `fake-http`, and `contract-fake` from active
   public camera-labeler support; remove fake sidecar/harness validation
   defaults; and switch deployment-like simulator defaults to
   `camera-grounded-labels` + `grounding-dino`.
4. Update launch routing, just recipes, and operator console defaults.
5. Update eval-harness rows and eval sample JSON, preserving both the Public
   baseline row and the Grounding-DINO deployment-like row where useful.
6. Update Agibot, scene-sampler, CI-live, checker, report, and prompt surfaces.
7. Update docs and agent guidance.
8. Run focused tests, then run global searches for active Oracle, sim
   projection, and fake transport references and classify remaining hits as
   historical-only, negative tests, private non-runnable test fixtures, or
   unrelated rendering diagnostics.

## Acceptance Criteria

- `world-oracle-labels` is not accepted by public launch routes, private current
  household implementation routes, operator console, eval samples, eval-harness
  current rows, or active household MCP/map-build servers.
- `cleanup_evidence_lane_names()` returns exactly
  `("world-public-labels", "camera-grounded-labels", "camera-raw-fpv")`.
- A structured world-label run emits `evidence_lane=world-public-labels`.
- Agent-visible detections from structured world-label runs omit destination and
  tool oracle fields.
- Simulator product map-build defaults and docs use
  `evidence_lane=camera-grounded-labels camera_labeler=grounding-dino`.
- `sim-projected-labels` is not accepted by public launch routes, operator
  console, active eval rows, or current product docs.
- `fake-http` and `contract-fake` are not accepted by public launch routes,
  operator console, active eval rows, current product docs, current runbooks, or
  visual-grounding benchmark/harness defaults. No runnable fake sidecar command
  remains as current validation proof.
- `grounding-dino` routes fail clearly when the External Visual Grounding
  Service is unavailable; they do not fall back to simulator projection,
  `fake-http`, or `contract-fake`. Product proof routes fail non-zero when they
  cannot write usable blocked evidence; eval rows may record blocked preflight
  packets.
- README, ARCHITECTURE, AGENTS, CLAUDE, and `just/README.md` no longer present
  Oracle as active run guidance.
- Remaining `world-oracle-labels` text is limited to historical plans,
  retrospectives, old output references, or an explicit negative test asserting
  rejection.
- Remaining `sim-projected-labels` text is limited to historical plans,
  old output references, private test helper code, or explicit negative tests.
- Remaining `fake-http` / `contract-fake` text is limited to historical plans,
  old output references, explicit negative tests, or private static fixture
  payloads that cannot be launched as robot validation.
- ADR-0138 contains a clear note that ADR-0143 supersedes its older sim/fake
  runtime-choice wording.

## Verification

Pre-implementation risk probes:

```bash
# Public baseline must already be viable before Oracle is deleted.
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=map-build agent_engine=direct-runner evidence_lane=world-public-labels \
  seed=7 scenario_setup=baseline

# Deployment-like simulator map-build must use the real detector sidecar.
# If the sidecar is missing or unhealthy, this should fail/block loudly.
# For a passing product proof, start the real sidecar in a separate terminal:
#   UV_PROJECT_ENVIRONMENT="$PWD/.venv-visual-grounding" \
#     uv sync --project sidecars/visual-grounding --extra cuda
#   VISUAL_GROUNDING_DEVICE=auto \
#   VISUAL_GROUNDING_TORCH_DTYPE=auto \
#   VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base \
#   VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25 \
#   VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20 \
#     .venv-visual-grounding/bin/python \
#       scripts/visual_grounding/serve_visual_grounding_service.py \
#       --pipeline real-router --adapter-mode real
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=map-build agent_engine=direct-runner \
  evidence_lane=camera-grounded-labels camera_labeler=grounding-dino \
  seed=7 scenario_setup=baseline

# Inventory active non-deployable camera-labeler dependencies before editing.
rg -n "sim-projected-labels|SIM_PROJECTED_LABELS_CAMERA_LABELER|fake-http|contract-fake" \
  README.md ARCHITECTURE.md AGENTS.md CLAUDE.md just roboclaws scripts \
  skills/eval-harness evals tests docs/human
```

Do not start broad deletion work if the Grounding-DINO route cannot run or
cleanly report a blocked sidecar. Fix the sidecar/readiness path first. A fake
or simulator-projected camera-labeler substitute is not an acceptable
pre-implementation proof.

Focused first pass:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/unit/operator_console/test_routes.py \
  tests/unit/operator_console/test_launcher.py \
  tests/unit/evals/test_eval_harness_selector.py \
  tests/unit/evals/test_eval_runner.py
```

Route smoke:

```bash
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=map-build agent_engine=direct-runner evidence_lane=world-public-labels \
  seed=7 scenario_setup=baseline

ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=map-build agent_engine=direct-runner \
  evidence_lane=camera-grounded-labels camera_labeler=grounding-dino \
  seed=7 scenario_setup=baseline

ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels \
  seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5
```

Eval-harness recommendation:

```bash
just agent::eval recommend plan=docs/plans/2026-06-16-drop-world-oracle-labels.md budget=focused
```

Static cleanup check:

```bash
rg -n "world-oracle-labels|WORLD_ORACLE_LABELS|WORLD_LABELS_PROFILE" \
  README.md ARCHITECTURE.md AGENTS.md CLAUDE.md just roboclaws scripts \
  skills/eval-harness evals tests docs/human

rg -n "sim-projected-labels|SIM_PROJECTED_LABELS_CAMERA_LABELER" \
  README.md ARCHITECTURE.md AGENTS.md CLAUDE.md just roboclaws scripts \
  skills/eval-harness evals tests docs/human

rg -n "fake-http|contract-fake" \
  README.md ARCHITECTURE.md AGENTS.md CLAUDE.md just roboclaws scripts \
  skills/eval-harness evals tests docs/human
```

Allowed static-check survivors:

- explicit negative tests asserting `world-oracle-labels` is rejected;
- explicit negative tests asserting `sim-projected-labels` is rejected by
  public/product paths;
- explicit negative tests asserting `fake-http` / `contract-fake` are rejected
  by public/product paths;
- private static fixture payloads for parser/error handling only when no
  runnable route, sidecar pipeline, benchmark default, fake service command, or
  just recipe can select them;
- historical plans, retrospectives, and old output paths outside current
  orientation/runbook surfaces;
- private scorer terminology or unrelated rendering diagnostics that use the
  word `oracle` without accepting the household evidence-lane string.

## Stop Conditions

- Stop if Public cannot pass the deterministic direct cleanup smoke without
  adding runner-side lane-specific policy. That would mean the Public skill/MCP
  contract is not ready to be the sole structured world-label lane.
- Stop if implementation needs a compatibility alias to keep tests green. That
  violates the goal.
- Stop if removing Oracle exposes private scorer truth through Public as a
  shortcut. Fix the public contract instead.
- Stop if removing `sim-projected-labels` forces loss of all deterministic
  camera-grounded contract coverage and no real-sidecar gate or static
  non-runnable unit fixture can replace it.
- Stop if a `grounding-dino` route silently falls back to simulator projection
  when the sidecar is unavailable. That would recreate the false-confidence
  problem.
- Stop if any active product/eval route still accepts `fake-http` or
  `contract-fake`. Fake camera labels are not a valid substitute for a
  deployable perception path.
- Stop if a visual-grounding harness, benchmark, sidecar command, or current
  runbook still defaults to `fake-http` / `contract-fake` as validation proof.
- Stop if deleting fake sidecar commands would leave no private static fixture
  coverage for visual-grounding parser/schema error handling.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/plans/2026-06-16-drop-world-oracle-labels.md`, ADR-0143,
and the 2026-06-16 discussion requesting aggressive deletion.

Canonical source: `docs/plans/2026-06-16-drop-world-oracle-labels.md`

Route: durable `$intuitive-flow`; this is refactor-shaped cleanup and should
execute with `$intuitive-refactor` discipline inside the flow.

Goal: delete `world-oracle-labels` as an active household evidence lane, make
`world-public-labels` the sole structured world-label baseline, remove
non-deployable camera labelers from active routes, and make deployment-like
simulator map-build defaults use
`camera-grounded-labels` + `camera_labeler=grounding-dino`.

Standalone boundary: this preflight is only for the Oracle/Public evidence-lane
and non-deployable camera-labeler migration. It explicitly does not implement
operator-console cleanup setup readiness, mess-up capacity checks, baseline
acknowledgement, or cleanup start-blocking readiness logic.

Scope:

- Registry and contract: remove Oracle lane constants/metadata, make Public the
  inferred structured world-label lane, reject Oracle input, and keep
  agent-visible structured labels sanitized.
- Camera labelers: remove `sim-projected-labels` from active public/operator
  support; remove `fake-http` and `contract-fake` from active public/operator
  support; keep `grounding-dino` as the default real camera labeler. Tests that
  cannot run the real sidecar should fail/skip loudly with blocked evidence
  instead of substituting fake camera labels. Delete or disable runnable fake
  sidecar pipelines, fake harness defaults, fake benchmark defaults, and fake
  service commands from current validation proof; parser tests may use only
  private static payloads that cannot be selected by launch, sidecar, or
  harness routes.
- Launch and runtime: update `run::surface`, private current just recipes,
  smoke lowering, coding-agent kickoff defaults, CI-live matrix metadata, and
  report/checker expectations. Product/default map-build examples should use
  `camera-grounded-labels camera_labeler=grounding-dino`; CI/smoke contract
  examples should use `world-public-labels`; cleanup structured-baseline
  examples should remain on `world-public-labels` in this slice.
- Operator console: remove Oracle from dropdowns, route ids, defaults, launch
  args, UI fallbacks, and route/history fixtures. Change simulator
  camera-grounded defaults from `sim-projected-labels` to `grounding-dino`.
  This is evidence-lane/catalog migration only, not cleanup setup readiness.
- Eval and samples: migrate eval-harness rows, eval sample JSON, row ids,
  runtime-map-prior references, scene-sampler templates, and related tests to
  Public where they are structured-world baselines; add/promote
  Grounding-DINO camera-grounded rows for deployment-like map-build proof.
- Agibot and helper side doors: remove Oracle from accepted active lane lists,
  pre-hardware rehearsal normalization, scanner commands, and current
  household evidence-lane catalogs.
- Docs: update current orientation docs, current human runbooks, and active
  plan surfaces; mark historical-only references instead of bulk-rewriting old
  retrospectives or output evidence.
- ADRs: update ADR-0138 with a supersession note and keep ADR-0143 as the
  durable current contract for removing Oracle, sim projection, and fake camera
  inputs.
- Worktree hygiene: preserve unrelated existing dirty changes and stage only
  files that belong to this task.

Non-goals:

- No operator-console cleanup setup readiness, mess-up count/capacity handling,
  baseline/no-mess-up acknowledgement, or cleanup start-blocking readiness UX.
- No compatibility alias from `world-oracle-labels` to `world-public-labels`.
- No maintainer-only Oracle lane and no replacement `sim-oracle-upper-bound`.
- No fake camera-labeler fallback and no product/operator `fake-http` or
  `contract-fake` route. No runnable fake sidecar, fake service command,
  harness default, or benchmark default may stand in for real visual-grounding
  validation.
- No changes to the `camera-grounded-labels` MCP observation/declaration
  contract shape.
- No changes to `camera-raw-fpv`, private scorer truth, or unrelated rendering
  oracle diagnostics.
- No weakening of structured-world product gates just to make Public pass.
- No bulk historical-output rewrite.

Entity budget: reuse=`evidence_lane`, `camera_labeler`,
`world-public-labels`, `camera-grounded-labels`, `grounding-dino`,
sanitized payload policy, existing eval harness, operator console,
report/checker surfaces; remove/merge=`world-oracle-labels` lane, Oracle
constants, `sim-projected-labels` active support, `fake-http` / `contract-fake`
active support, runnable fake sidecar/service/harness validation defaults,
active examples, eval rows, route ids, samples, and defaults;
new=none for implementation because ADR-0143, ADR-0138, and this plan already
exist; expansion triggers=any compatibility alias, new evidence lane,
maintainer-only upper-bound route, sim-projection fallback, fake camera-labeler
fallback, gate weakening, private-truth exposure, or new public command surface
requires re-approval.

Context: must-read=`docs/plans/2026-06-16-drop-world-oracle-labels.md`,
`docs/adr/0143-drop-world-oracle-labels-evidence-lane.md`,
`docs/adr/0138-use-detector-only-visual-grounding-sidecar.md`,
`ARCHITECTURE.md`, `AGENTS.md`, `roboclaws/household/profiles.py`,
`roboclaws/household/realworld_contract.py`,
`roboclaws/household/realworld_contract_init.py`,
`roboclaws/household/tasks.py`, `just/agent.just`, `just/molmo.just`,
`roboclaws/operator_console/routes.py`,
`skills/eval-harness/scripts/eval_harness_rows.py`,
`scripts/visual_grounding/serve_visual_grounding_service.py`,
`scripts/visual_grounding/serve_fake_visual_grounding.py`,
`scripts/visual_grounding/run_visual_grounding_benchmark.py`,
`tests/contract/visual_grounding/test_visual_grounding_service.py`,
`tests/contract/visual_grounding/test_visual_grounding_benchmark.py`,
`docs/human/molmospaces-visual-grounding-results.md`,
`docs/human/agibot-g2-cleanup-pilot.md`;
useful=`README.md`, `CLAUDE.md`, `just/README.md`,
`roboclaws/agents/prompts/household_cleanup.py`,
`scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`,
`roboclaws/household/agibot_map_build_mcp_server.py`,
`roboclaws/household/agibot_contract_rehearsal.py`,
`roboclaws/launch/scene_sampler.py`,
`roboclaws/launch/scene_sampler_scanner.py`,
`roboclaws/household/ci_live_reports.py`, focused tests named below;
avoid-unless-needed=historical retrospectives, generated `output/**`, old
implemented plans except when classifying allowed static-check survivors.

Acceptance:

- SUCCESS: `world-oracle-labels` is rejected by active launch, console, eval,
  MCP/map-build, and current helper routes; active lane registry is exactly
  `world-public-labels`, `camera-grounded-labels`, `camera-raw-fpv`;
  structured world-label artifacts emit `evidence_lane=world-public-labels`;
  smoke emits `preset=smoke` plus `evidence_lane=world-public-labels`; public
  detections omit destination/tool oracle fields; simulator product map-build
  defaults use `camera-grounded-labels camera_labeler=grounding-dino`;
  simulator cleanup structured baselines use `world-public-labels`;
  `sim-projected-labels`, `fake-http`, and `contract-fake` are rejected by
  public/product routes; no current runbook, sidecar command, harness default,
  or benchmark default uses fake visual-grounding as validation proof; focused
  tests, static checks, and required product-run gates pass.
- BLOCKED_NEEDS_DECISION: none expected; trigger if implementation requires a
  compatibility alias, maintainer-only upper-bound lane, synthetic evidence
  lane, `sim-projected-labels` product fallback, fake camera-labeler fallback,
  or relaxed Public gates.
- BLOCKED_NEEDS_LOCAL_VALIDATION: required product-run or operator-console
  proof cannot run because local dependencies, simulator assets, browser, or
  Docker/provider/GPU/DINO sidecar environment is unavailable.
- INTERMEDIATE_ONLY: code/test/docs migration without product-run proof is only
  an incomplete checkpoint and must report missing gates; it is not complete,
  merge-ready, or no-regression.
- No regressions: `camera-grounded-labels` still requires `camera_labeler`;
  `grounding-dino` routes require a real sidecar or explicit failure evidence;
  fake camera-labeler routes are not accepted as product/operator/harness
  validation; cleanup default is not silently promoted to a physical-cleanup
  claim while manipulation remains blocked;
  `camera-raw-fpv` remains image/observation-driven; private scorer truth stays
  report/grader-only; current public command grammar remains
  `just run::surface ... evidence_lane=... camera_labeler=...`.

Verification: deterministic=

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py \
  tests/contract/reports/test_molmo_cleanup_report.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/dev_tools/test_eval_just_recipe.py \
  tests/unit/operator_console/test_routes.py \
  tests/unit/operator_console/test_launcher.py \
  tests/unit/evals/test_eval_harness_selector.py \
  tests/unit/evals/test_eval_models.py \
  tests/unit/evals/test_eval_runner.py \
  tests/unit/launch/test_environment_setup_catalog.py \
  tests/unit/launch/test_scene_sampler.py \
  tests/unit/molmo_cleanup/test_ci_live_reports.py \
  tests/unit/molmo_cleanup/test_visual_grounding.py \
  tests/contract/visual_grounding/test_visual_grounding_service.py \
  tests/contract/visual_grounding/test_visual_grounding_benchmark.py
ruff check <changed-python-files>
ruff format --check <changed-python-files>
git diff --check
```

Verification: integration=

```bash
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=cleanup agent_engine=direct-runner run_preset=smoke \
  evidence_lane=world-public-labels seed=7

ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=cleanup agent_engine=codex-cli provider_profile=codex-env \
  evidence_lane=world-public-labels seed=7

just agent::eval recommend \
  plan=docs/plans/2026-06-16-drop-world-oracle-labels.md budget=focused

rg -n "world-oracle-labels|WORLD_ORACLE_LABELS|WORLD_LABELS_PROFILE" \
  README.md ARCHITECTURE.md AGENTS.md CLAUDE.md just roboclaws scripts \
  skills/eval-harness evals tests docs/human

rg -n "sim-projected-labels|SIM_PROJECTED_LABELS_CAMERA_LABELER" \
  README.md ARCHITECTURE.md AGENTS.md CLAUDE.md just roboclaws scripts \
  skills/eval-harness evals tests docs/human

rg -n "fake-http|contract-fake" \
  README.md ARCHITECTURE.md AGENTS.md CLAUDE.md just roboclaws scripts \
  skills/eval-harness evals tests docs/human
```

Verification: product-run=

```bash
just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=map-build agent_engine=direct-runner evidence_lane=world-public-labels \
  seed=7 scenario_setup=baseline \
  output_dir=output/verification/drop-world-oracle/map-build-public

just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=map-build agent_engine=direct-runner \
  evidence_lane=camera-grounded-labels camera_labeler=grounding-dino \
  seed=7 scenario_setup=baseline \
  output_dir=output/verification/drop-world-oracle/map-build-grounding-dino

just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels \
  seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5 \
  output_dir=output/verification/drop-world-oracle/cleanup-public
```

Verification: local-live-manual=operator console browser/manual check is
required if console files change: run `just console::run`, open the local
console, confirm the Evidence lane dropdown omits `world-oracle-labels`,
confirm selected structured-world route launch args use
`evidence_lane=world-public-labels`, and confirm map-build product/default
camera-grounded route args use
`evidence_lane=camera-grounded-labels camera_labeler=grounding-dino`.
Live Codex/Claude provider cleanup is optional exploratory proof, not required
for this refactor unless implementation changes provider execution behavior.

Verification: optional=

```bash
just agent::eval execute \
  plan=docs/plans/2026-06-16-drop-world-oracle-labels.md budget=focused
```

Execution: main=root supervisor owns scope, dirty-worktree protection, edits,
and final complete/blocked judgment; worker=none by default; worker-goal=none.

To execute:

```text
/goal execute docs/plans/2026-06-16-drop-world-oracle-labels.md with intuitive-flow
```

Optional tracking: none.

Approval: LGTM/approve/go ahead approves; edits request revision.

## Reduce-Entropy Loop

Selected mode: plan entropy mode.

Why: the user asked for one plan, then an intuitive-reduce-entropy loop on that
plan before implementation.

Discovery intensity: saturation scan.

### Round 1: Public Surface Drift

Finding: Oracle is embedded in public defaults, private current recipes,
operator-console route ids, and first-read guidance. Changing only
`cleanup_evidence_lane_names()` would leave live routes and docs claiming the
old lane.

Plan impact: Scope includes registry, launch, console, eval rows, and root docs
as one deletion package.

### Round 2: Smoke Preset Ambiguity

Finding: smoke is not an evidence lane, but current smoke metadata lowers to
`world-oracle-labels`. Dropping Oracle without deciding smoke semantics would
leave a hidden Oracle alias.

Plan impact: Smoke must lower to Public metadata or carry only explicit
synthetic preset metadata. No Oracle string may survive in smoke output.

### Round 3: Eval False Confidence

Finding: eval samples and eval-harness row ids use Oracle heavily. If these are
not migrated, focused eval recommendations would continue selecting the deleted
lane.

Plan impact: Eval samples, row ids, runtime-map-prior row references, and
relevant tests are in scope.

### Round 4: Misleading Constant Names

Finding: keeping `WORLD_LABELS_PROFILE` as an alias for Public would remove the
string but preserve the conceptual confusion. Future agents would rediscover
the old split through code names.

Plan impact: Rename or remove Oracle-shaped constants instead of aliasing them
to Public.

### Round 5: Agibot And Scene-Sampler Side Doors

Finding: Agibot map-build validation and scene-sampler generated samples accept
or emit Oracle outside the main launch registry. These are likely to reintroduce
the lane after the main route is cleaned.

Plan impact: Agibot helpers, scene-sampler templates, generated eval samples,
and scanner tests are in scope.

### Round 6: Public Baseline Can Masquerade As Deployment Default

Finding: moving every default from Oracle to Public would remove privileged
destination/tool hints, but it would still default simulator map-build to a
structured-world input a real robot cannot obtain. That would keep the product
proof misaligned with the real-robot target.

Plan impact: Public is explicitly scoped to CI/smoke/contract baselines.
Simulator product map-build and real-robot-facing proof default to
`camera-grounded-labels camera_labeler=grounding-dino`.

### Round 7: Sim Projection Recreates The Oracle Pattern

Finding: `sim-projected-labels` is less privileged than full world labels, but
it still depends on simulator-only projection. Leaving it selectable as the
simulation default would produce camera-looking evidence that a real robot
cannot reproduce.

Plan impact: Remove `sim-projected-labels`, `fake-http`, and `contract-fake`
from active public/operator support. Use `grounding-dino` for deployment-like
perception proof. If the real sidecar is unavailable, mark the route blocked
instead of manufacturing fake camera candidates.

### Round 8: Fake Sidecars Can Survive Outside Camera Labelers

Finding: `fake-http` and `contract-fake` can survive outside the
`camera_labeler` registry as sidecar pipeline ids, benchmark defaults, harness
examples, or runbook commands. That would still let a simulator or benchmark
run produce green-looking camera-grounded evidence without a deployable
perception producer.

Plan impact: Remove fake camera transports from current validation routes, not
only from public labeler choices. Keep only private non-runnable static payloads
for parser/error tests, and make missing real sidecar evidence block or fail
aloud.

### Grill Batch 1: Accepted Contract Tightening

Accepted answers:

- ADR-0143 supersedes ADR-0138's older sim/fake runtime-choice wording, and
  ADR-0138 should carry a short supersession note.
- Remove runnable fake validation paths, not only public camera-labeler
  choices. Fake parser/schema coverage may remain only as private static
  payloads that cannot be launched as robot validation.
- Product/default simulator `preset=map-build` uses
  `camera-grounded-labels camera_labeler=grounding-dino`, even if that means a
  missing sidecar blocks or fails early.
- Cleanup structured baselines remain on `world-public-labels` in this slice;
  do not turn cleanup defaults into physical-cleanup claims while manipulation
  proof is still blocked.
- Missing Grounding-DINO sidecar semantics split by owner: product proof routes
  fail clearly, preferably after writing blocked/missing-sidecar evidence; eval
  harness rows may record blocked preflight packets. Neither may fall back to
  sim projection or fake transport.

### Saturation Check

No further P0/P1/P2 candidates passed the materiality bar after the eight
rounds. Unrelated uses of the word `oracle` in rendering diagnostics or private
scorer language are not part of this plan unless they reference the household
evidence lane string or constants. Historical `sim-projected-labels`,
`fake-http`, or `contract-fake` references outside current run guidance are also
not part of active cleanup unless they remain reachable as product/operator
choices, runnable sidecar pipeline ids, harness defaults, or current validation
runbook commands.

## Recommended Next Action

Implemented. Use the closeout block below as the current execution status; the
preflight contract above is retained as historical scope and verification
context.

## Implementation Closeout

Status: implemented on 2026-06-16.

Owned layers updated:

- Runnable surfaces and presets now use `world-public-labels` for structured
  world-label baselines and `camera-grounded-labels camera_labeler=grounding-dino`
  for deployment-like map-build examples.
- Capability profile, launch, operator-console, eval, report/checker, helper,
  docs, and visual-grounding sidecar surfaces no longer expose
  `world-oracle-labels`, `sim-projected-labels`, `fake-http`, or
  `contract-fake` as active product or validation routes.
- Visual-grounding fake service support was removed from runnable code; parser
  and rejection coverage now uses negative tests and private static fixture
  helpers only.

Verification evidence:

- Registry probe: `cleanup_evidence_lane_names()` returns exactly
  `("world-public-labels", "camera-grounded-labels", "camera-raw-fpv")`; active
  camera labelers are exactly `("grounding-dino", "yoloe", "omdet-turbo",
  "yolo-world")`; retired lane/labeler ids are rejected.
- Product runs:
  - `output/verification/drop-world-oracle/map-build-public/0616_1923/seed-7/run_result.json`
  - `output/verification/drop-world-oracle/map-build-grounding-dino/0616_1924/seed-7/run_result.json`
  - `output/verification/drop-world-oracle/cleanup-public/0616_1926/seed-7/run_result.json`
- Eval-harness recommendation:
  `output/eval-harness/20260616T112215Z/eval_harness.json`.
- Operator-console browser/API check:
  `just console::run 127.0.0.1 8766` loaded successfully in headless Chromium;
  the visible Evidence lane dropdown contained exactly `world-public-labels`,
  `camera-grounded-labels`, and `camera-raw-fpv`; the route API returned zero
  matches for retired tokens; the selected launch command used
  `evidence_lane=world-public-labels`; browser console reported no errors and
  page/API/static requests returned 200.
- Focused tests and checks passed:
  visual-grounding contract tests, the plan's broader deterministic focused
  suite, changed-file Ruff checks, `git diff --check`, focused console/just
  static tests after closeout edits, and static scans classifying remaining
  retired-id text as historical evidence, old output provenance, explicit
  negative tests, or private static fixture coverage.

Remaining notes:

- Historical docs, old output paths, and diagnostic status capsules may still
  contain retired ids as old evidence. They are not active launch, operator,
  eval, benchmark, or runbook surfaces.
