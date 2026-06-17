---
plan_scope: drop-world-oracle-labels
status: PROPOSED
created: 2026-06-16
last_reviewed: 2026-06-16
implementation_allowed: false
source:
  - user request to aggressively simplify evidence lanes by dropping world-oracle-labels
related_context:
  - README.md
  - ARCHITECTURE.md
  - AGENTS.md
  - docs/adr/0143-drop-world-oracle-labels-evidence-lane.md
  - docs/plans/refactor-evidence-lane-naming.md
  - roboclaws/household/profiles.py
  - roboclaws/household/realworld_contract.py
  - roboclaws/operator_console/routes.py
  - skills/eval-harness/scripts/eval_harness_rows.py
---

# Drop World Oracle Labels

## Goal

Delete `world-oracle-labels` as an active household evidence lane. The simulator
structured-label path that remains is `world-public-labels`: structured public
detections with destination/tool oracle hints and pre-confirmed navigation
authorization removed.

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
`world-oracle-labels` parts of `docs/plans/refactor-evidence-lane-naming.md`.
The two-axis model `evidence_lane` plus `camera_labeler` remains valid; only the
privileged world lane is removed.

## Pushback Resolved

Deleting Oracle removes a useful upper-bound diagnostic. That is acceptable here
because the ongoing architecture direction values honest public agent inputs
over a privileged cleanup baseline. If later work needs an upper-bound
diagnostic, it should be introduced as a private eval fixture or scorer-only
control, not as an agent-visible evidence lane.

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

## Owning Layers

- Runnable surfaces and presets: `surface=household-world` and its cleanup,
  map-build, and open-ended defaults move to `world-public-labels`.
- Capability profile / MCP contract: agent-visible world detections use the
  sanitized public policy.
- Thin runtime / server adapters: launch and operator-console defaults stop
  accepting Oracle.
- Eval harness and eval suites: product rows, samples, and row ids use Public.
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

- Change `household-world` default profile to `world-public-labels`.
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
- Keep Isaac support rules accurate after Public becomes the structured
  world-label lane.

### 5. Eval Harness And Eval Suites

- Rename eval-harness row ids such as `household-direct-world-oracle-product`
  and `direct-map-build-world-oracle` to Public equivalents.
- Change eval sample JSON files from Oracle to Public.
- Change runtime-map-prior references that include Oracle row ids.
- Ensure cleanup/product gates still check waypoint honesty, real-robot
  alignment, semantic accepted count, and sweep coverage where they remain
  relevant for Public.
- Remove tests that compare Oracle against Public as separate active lanes.

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
- Keep tests that prove Public omits destination/tool oracle fields.
- Remove or rewrite Oracle-specific prompt, report, checker, operator-console,
  eval-harness, and CI-live expectations.
- Update README, ARCHITECTURE, AGENTS, CLAUDE, `just/README.md`, and current
  human docs to remove Oracle from active commands.
- Mark historical plan references as historical when they are not current run
  guidance; do not bulk-rewrite shipped retrospectives or old evidence logs.

## Non-Goals

- No compatibility alias from `world-oracle-labels` to `world-public-labels`.
- No maintainer-only Oracle lane.
- No new replacement `sim-oracle-upper-bound` lane in this slice.
- No changes to `camera-grounded-labels` producer semantics.
- No changes to `camera-raw-fpv` model-declared observation semantics.
- No private scorer truth removal.
- No bulk rewrite of historical output artifacts.

## Execution Order

1. Update the evidence-lane registry and focused profile tests first.
2. Make structured world-label contract behavior default to sanitized Public.
3. Update launch routing, just recipes, and operator console defaults.
4. Update eval-harness rows and eval sample JSON.
5. Update Agibot, scene-sampler, CI-live, checker, report, and prompt surfaces.
6. Update docs and agent guidance.
7. Run focused tests, then run a global search for active Oracle references and
   classify remaining hits as historical-only or unrelated rendering diagnostics.

## Acceptance Criteria

- `world-oracle-labels` is not accepted by public launch routes, private current
  household implementation routes, operator console, eval samples, eval-harness
  current rows, or active household MCP/map-build servers.
- `cleanup_evidence_lane_names()` returns exactly
  `("world-public-labels", "camera-grounded-labels", "camera-raw-fpv")`.
- A structured world-label run emits `evidence_lane=world-public-labels`.
- Agent-visible detections from structured world-label runs omit destination and
  tool oracle fields.
- README, ARCHITECTURE, AGENTS, CLAUDE, and `just/README.md` no longer present
  Oracle as active run guidance.
- Remaining `world-oracle-labels` text is limited to historical plans,
  retrospectives, old output references, or an explicit negative test asserting
  rejection.

## Verification

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
```

Allowed static-check survivors:

- explicit negative tests asserting `world-oracle-labels` is rejected;
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

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/plans/2026-06-16-drop-world-oracle-labels.md`, ADR-0143,
and the 2026-06-16 discussion requesting aggressive deletion.

Canonical source: `docs/plans/2026-06-16-drop-world-oracle-labels.md`

Route: durable `$intuitive-flow`; this is refactor-shaped cleanup and should
execute with `$intuitive-refactor` discipline inside the flow.

Goal: delete `world-oracle-labels` as an active household evidence lane and
make `world-public-labels` the sole structured world-label path.

Scope:

- Registry and contract: remove Oracle lane constants/metadata, make Public the
  inferred structured world-label lane, reject Oracle input, and keep
  agent-visible structured labels sanitized.
- Launch and runtime: update `run::surface`, private current just recipes,
  smoke lowering, coding-agent kickoff defaults, CI-live matrix metadata, and
  report/checker expectations.
- Operator console: remove Oracle from dropdowns, route ids, defaults, launch
  args, UI fallbacks, and route/history fixtures.
- Eval and samples: migrate eval-harness rows, eval sample JSON, row ids,
  runtime-map-prior references, scene-sampler templates, and related tests to
  Public.
- Agibot and helper side doors: remove Oracle from accepted active lane lists,
  pre-hardware rehearsal normalization, scanner commands, and current
  household evidence-lane catalogs.
- Docs: update current orientation docs, current human runbooks, and active
  plan surfaces; mark historical-only references instead of bulk-rewriting old
  retrospectives or output evidence.
- Worktree hygiene: preserve unrelated existing dirty changes and stage only
  files that belong to this task.

Non-goals:

- No compatibility alias from `world-oracle-labels` to `world-public-labels`.
- No maintainer-only Oracle lane and no replacement `sim-oracle-upper-bound`.
- No changes to `camera-grounded-labels`, `camera-raw-fpv`, private scorer
  truth, camera labeler semantics, or unrelated rendering oracle diagnostics.
- No weakening of structured-world product gates just to make Public pass.
- No bulk historical-output rewrite.

Entity budget: reuse=`evidence_lane`, `camera_labeler`,
`world-public-labels`, sanitized payload policy, existing eval harness,
operator console, report/checker surfaces; remove/merge=`world-oracle-labels`
lane, Oracle constants, active examples, eval rows, route ids, samples, and
defaults; new=none for implementation because ADR-0143 and this plan already
exist; expansion triggers=any compatibility alias, new evidence lane,
maintainer-only upper-bound route, gate weakening, private-truth exposure, or
new public command surface requires re-approval.

Context: must-read=`docs/plans/2026-06-16-drop-world-oracle-labels.md`,
`docs/adr/0143-drop-world-oracle-labels-evidence-lane.md`,
`ARCHITECTURE.md`, `AGENTS.md`, `roboclaws/household/profiles.py`,
`roboclaws/household/realworld_contract.py`,
`roboclaws/household/realworld_contract_init.py`,
`roboclaws/household/tasks.py`, `just/agent.just`, `just/molmo.just`,
`roboclaws/operator_console/routes.py`,
`skills/eval-harness/scripts/eval_harness_rows.py`;
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
  detections omit destination/tool oracle fields; focused tests, static checks,
  and required product-run gates pass.
- BLOCKED_NEEDS_DECISION: none expected; trigger if implementation requires a
  compatibility alias, maintainer-only upper-bound lane, synthetic evidence
  lane, or relaxed Public gates.
- BLOCKED_NEEDS_LOCAL_VALIDATION: required product-run or operator-console
  proof cannot run because local dependencies, simulator assets, browser, or
  Docker/provider environment is unavailable.
- INTERMEDIATE_ONLY: code/test/docs migration without product-run proof is only
  an incomplete checkpoint and must report missing gates.
- No regressions: `camera-grounded-labels` still requires `camera_labeler`;
  `camera-raw-fpv` remains image/observation-driven; private scorer truth stays
  report/grader-only; current public command grammar remains
  `just run::surface ... evidence_lane=...`.

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
  tests/unit/molmo_cleanup/test_ci_live_reports.py
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
  preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels \
  seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5 \
  output_dir=output/verification/drop-world-oracle/cleanup-public
```

Verification: local-live-manual=operator console browser/manual check is
required if console files change: run `just console::run`, open the local
console, confirm the Evidence lane dropdown omits `world-oracle-labels`, and
confirm selected route launch args use `evidence_lane=world-public-labels`.
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

### Saturation Check

No further P0/P1/P2 candidates passed the materiality bar after the five rounds.
Unrelated uses of the word `oracle` in rendering diagnostics or private scorer
language are not part of this plan unless they reference the household evidence
lane string or constants.

## Recommended Next Action

Approve the preflight contract above, then execute it through
`$intuitive-flow`.

Shortcut: `LGTM`
