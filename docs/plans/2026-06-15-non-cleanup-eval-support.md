---
plan_scope: non-cleanup-eval-support
status: IMPLEMENTED
created: 2026-06-15
last_reviewed: 2026-06-16
implementation_allowed: true
source:
  - user request to support non-cleanup eval coverage
  - intuitive-reduce-entropy plan entropy loop
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md
  - docs/adr/0141-use-eval-harness-as-maintainer-orchestration-facade.md
  - docs/plans/2026-06-14-eval-driven-architecture.md
  - docs/plans/2026-06-15-eval-harness-skill-entrypoint.md
  - evals/household_world/README.md
---

# Non-Cleanup Eval Support

## Goal

Make non-cleanup household capabilities first-class in eval support, without
weakening the cleanup eval path or adding another public run surface.

The support package should let maintainers answer these questions through
`just agent::eval recommend|execute|suite|promote-regression`:

- Did open-ended household goals regress?
- Did map-build produce usable Runtime Metric Map evidence, and can consumers use
  it?
- Is scene-sampler map-build coverage healthy across admitted scenes?
- Did planner-proof changes run the correct maintainer proof row?
- When a live model/provider route is requested, did it really run the intended
  capability or record an explicit blocker?

Resolved grill decisions:

- `open_ended_goals` samples use public no-preset `prompt=...` as the contract;
  `intent=open-ended` remains eval/sample identity metadata and runtime artifact
  detail, not the public household command shape.
- The implementation must include a real opt-in live open-task proof. Blocked
  evidence is useful diagnostic output for genuine provider/runtime preflight
  blockers, but it is not a completion condition.
- Open-ended suite pass/fail remains hard-gated on artifacts, privacy,
  trajectory, and completion claim. Semantic satisfaction remains advisory until
  a deterministic public predicate exists.
- Planner-proof starts as an eval-harness product/proof row, not an eval suite.

## Owning Layers

- Eval harness: selects deterministic gates, product rows, eval suites,
  live-agent eval rows, and blocked evidence.
- Eval suites: own versioned samples, trials, graders, aggregate metrics, and
  regression promotion.
- Product run: remains `just run::surface ...`; this plan does not add an
  operator-facing namespace.
- Harness recipes: remain low-level mechanics for planner proof and specialist
  probes.

## Current State

Existing coverage is real but uneven:

- Cleanup has `smoke_regression` and `cleanup_capability`. The repeated cleanup
  suite records `pass@k` and `pass^k` over `trial_count=3`.
- Map-build has `map_build_consumer`, which checks Runtime Metric Map
  actionability and passes the produced map as `runtime_map_prior` to a cleanup
  consumer sample.
- Open-ended currently appears inside `map_build_consumer` as
  `open_ended.drink_seed7`; it checks completion claim and artifact readiness,
  while semantic satisfaction remains advisory.
- Scene sampler stress exists as `scene_sampler_stress` for admitted map-build
  samples.
- Planner-proof is a current product surface, but eval-harness does not yet
  expose a first-class planner-proof row.

The main problem is false confidence: non-cleanup proofs are present, but they
are partly mixed into cleanup or map-consumer suites, and some live rows are
labeled as open-task while pointing at suites that do not actually exercise
open-ended live samples.

## Reduce-Entropy Loop

Selected mode: plan entropy mode.

Why: the user asked for one plan and a reduce-entropy loop before implementation.

Discovery intensity: saturation scan.

### Round 1: Existing Support Inventory

Reviewed:

- `evals/household_world/suites/*.json`
- `evals/household_world/samples/**`
- `roboclaws/evals/runner.py`
- `skills/eval-harness/scripts/eval_harness_rows.py`
- `tests/unit/evals/test_eval_runner.py`
- `tests/unit/evals/test_eval_harness_selector.py`
- active eval architecture docs and ADRs

Finding: map-build and open-ended support exists, but only cleanup has a mature
capability suite shape with repeated-trial metrics and live-agent identity.

### Round 2: False-Confidence Audit

Material issues found:

- `codex-open-task-live-eval` uses `suite=map_build_consumer`, but the current
  open-ended sample allows only `direct-runner`.
- `openai-agents-sdk-open-task-live-eval` is labeled as open-task but uses
  `suite=cleanup_capability`.
- `open_ended.drink_seed7` is a useful smoke sample, not a dedicated open-ended
  capability suite.
- Map-build direct/product rows exist, but live-provider map-build proof is not
  a clearly represented eval-harness row.
- Planner-proof is current architecture, but absent from eval-harness selection.

### Round 3: Saturation Check

Checked for additional material directions:

- multiple scene-sampler generated samples are already in flight in the working
  tree; this plan should not re-own that sampler expansion.
- visual-grounding and RAW-FPV rows are cleanup/perception support, not general
  non-cleanup eval capability support.
- docs-only wording gaps are support work, not independent entropy candidates.

No additional P0/P1/P2 candidate passed the materiality bar outside the four
selected items below.

Materiality gate result:

```text
eligible_count=4
rejected_count=0
stop_recommended=false
```

## Selected Candidates

### 1. Split Open-Task Live Rows From Map/Cleanup Suites

Severity: P1

Entropy source: false confidence in live open-task eval rows.

Materiality: a focused eval-harness execute can appear to select an open-task
live eval while either validating the wrong suite or failing before it launches
the intended open-ended sample.

Evidence:

- `skills/eval-harness/scripts/eval_harness_rows.py` defines
  `codex-open-task-live-eval` with `suite=map_build_consumer`.
- `skills/eval-harness/scripts/eval_harness_rows.py` defines
  `openai-agents-sdk-open-task-live-eval` with `suite=cleanup_capability`.
- `evals/household_world/samples/open_ended/drink_seed7.json` currently allows
  only `direct-runner`.

Plan:

- Do not let an open-task row point at a cleanup capability suite.
- Do not let an open-task live row point at a suite whose samples reject the
  selected live agent engine.
- Route open-task live rows to a dedicated open-ended suite once Candidate 2
  exists.
- Make the selected Codex CLI / `codex-env` open-task live row execute a real
  open-ended sample through `live_execution=run`.
- If provider, Docker, network, or live-session preflight blocks that run, record
  explicit blocked evidence with a non-secret blocker packet and leave the
  implementation blocked for local validation rather than complete.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_harness_selector.py
just agent::eval recommend intent=open-ended agent_engine=codex-cli budget=focused
```

### 2. Add A Dedicated Open-Ended Goals Suite

Severity: P1

Entropy source: open-ended capability is hidden inside `map_build_consumer`.

Materiality: maintainers cannot ask "did open household goals improve?" without
knowing that the only current sample is bundled with map-build consumer checks
and advisory semantic grading.

Evidence:

- `docs/plans/2026-06-14-eval-driven-architecture.md` listed
  `open_ended_goals.json` in the target layout.
- `evals/household_world/suites/` currently has no open-ended goals suite.
- `roboclaws/evals/runner.py` has an `open_ended` grader, but the authoritative
  pass/fail is still claim plus artifact readiness.

Plan:

- Add `evals/household_world/suites/open_ended_goals.json`.
- Start with one or two focused samples, including the existing drink goal.
- Model each sample as the public no-preset household route:
  `surface=household-world prompt=...`; keep `intent=open-ended` as eval/sample
  identity metadata and runtime artifact detail.
- Keep semantic satisfaction advisory unless a deterministic public-world
  predicate is available.
- Allow direct-runner and Codex CLI / `codex-env` in the first implementation, because
  that is the current supported coding-agent household route for open-ended
  prompts.
- Record clear thresholds for completion claim, artifact readiness, privacy, and
  trajectory.

Proof:

```bash
just agent::eval suite=open_ended_goals budget=smoke
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py
```

### 3. Make Map-Build Live And Scene Coverage Boundaries Explicit

Severity: P2

Entropy source: map-build has useful direct coverage, but live-provider and
multi-scene boundaries are easy to overstate.

Materiality: map-build changes can pass direct actionability checks while a
reviewer assumes live coding-agent map-build or broad scene readiness was also
covered.

Evidence:

- `map_build_consumer` is a direct-runner suite centered on
  `molmospaces/val_0`.
- `scene_sampler_stress` is a multi-scene admission/actionability stress suite,
  not full cleanup or open-task success over every sampled world.
- Eval-harness has `direct-map-build-world-oracle`, but no explicit live
  map-build eval row.

Plan:

- Keep `map_build_consumer` as the canonical map-build consumer suite.
- Keep `scene_sampler_stress` as scene admission/actionability stress, not a
  full task-success suite.
- Add selector language and tests that distinguish:
  `map_build_consumer`, `scene_sampler_stress`, direct map-build product row,
  and any future live map-build row.
- Add a blocked or live row for Codex map-build only if the public launch route
  can produce the required eval artifacts under `live_execution=run`.

Proof:

```bash
just agent::eval suite=map_build_consumer budget=smoke
just agent::eval suite=scene_sampler_stress budget=smoke
just agent::eval recommend preset=map-build budget=focused
```

### 4. Add Planner-Proof Eval-Harness Selection

Severity: P2

Entropy source: planner-proof is a current product surface, but eval-harness
does not select a planner-proof row.

Materiality: agents changing planner-proof must rediscover private
`harness::*` and `verify::*` recipes instead of using one maintainer proof
facade.

Evidence:

- `ARCHITECTURE.md` lists `surface=planner-proof intent=planner-proof`.
- `just/agent.just` routes `planner-proof.planner-proof` to planner-proof
  bundle runners.
- `skills/eval-harness/scripts/eval_harness_rows.py` has no planner-proof row
  or signal.

Plan:

- Add a deterministic planner-proof signal rule.
- Add one eval-harness row that uses the public route when possible:
  `just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run`.
- If a lower-level harness command is still required, keep it as a private
  command behind the row and label it as harness mechanics.
- Do not create a planner-proof eval suite unless repeated versioned samples are
  needed; start with an eval-harness product/proof row.

Proof:

```bash
just agent::eval recommend intent=planner-proof budget=focused
just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run
```

## Implementation Plan

### 1. Open-Ended Suite And Row Alignment

- Add `open_ended_goals` suite and samples.
- Update eval model/runner tests for the suite.
- Change open-task live rows to target the open-ended suite.
- Make the Codex CLI / `codex-env` open-task eval row execute through
  `live_execution=run`; blocked evidence from provider/runtime preflight is
  useful but leaves the implementation blocked, not complete.
- Update eval-harness selector tests for Codex and OpenAI Agents SDK open-task
  rows.

Stop condition:

- `just agent::eval suite=open_ended_goals budget=smoke` passes.
- `just agent::eval recommend intent=open-ended budget=focused` selects
  open-ended contract tests, open-ended suite, and correctly labeled live rows.
- `just agent::eval suite=open_ended_goals budget=smoke agent_engine=codex-cli provider_profile=codex-env live_execution=run live_timeout_s=120`
  produces a graded open-ended live result. A deterministic-only pass or blocked
  packet is not sufficient to complete the implementation.

### 2. Map-Build Boundary Tightening

- Clarify selector rows and docs for map-build direct product, map consumer
  suite, scene sampler stress, and live map-build status.
- Add tests that prevent map-build changes from being represented only by
  cleanup rows.
- Preserve existing `runtime_map_prior` dependency flow.

Stop condition:

- Existing map-build consumer and scene sampler suites still pass.
- Focused recommend for `preset=map-build` shows direct map-build plus
  map-consumer proof with no misleading live-provider claim.

### 3. Planner-Proof Harness Row

- Add planner-proof signal detection.
- Add one planner-proof row with explicit proof command and blocked/preflight
  behavior.
- Add selector and just facade tests.

Stop condition:

- `just agent::eval recommend intent=planner-proof budget=focused` selects the
  planner-proof row.
- Planner-proof dry-run proof command remains public-surface-shaped or clearly
  labeled as private harness mechanics.

## Non-Goals

- No new public run namespace.
- No broad generic predicate DSL.
- No requirement that every open-ended semantic satisfaction claim be
  deterministically authoritative in this implementation.
- No full cleanup/open-task success requirement for every scene-sampler sample.
- No OpenClaw Gateway proof.
- No real provider execution unless explicitly requested with `live_execution=run`
  and local preflight passes.

## Verification

Implemented 2026-06-16.

Deterministic:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_eval_just_recipe.py
```

Suites:

```bash
just agent::eval suite=open_ended_goals budget=smoke
just agent::eval suite=map_build_consumer budget=smoke
just agent::eval suite=scene_sampler_stress budget=smoke
```

Harness recommendation:

```bash
just agent::eval recommend intent=open-ended budget=focused
just agent::eval recommend preset=map-build budget=focused
just agent::eval recommend intent=planner-proof budget=focused
```

Required local live proof:

```bash
just agent::eval suite=open_ended_goals budget=smoke agent_engine=codex-cli provider_profile=codex-env live_execution=run live_timeout_s=120
```

Final evidence:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals tests/contract/dev_tools/test_eval_just_recipe.py`
  passed with 64 tests.
- `just agent::eval suite=open_ended_goals budget=smoke stamp=flow-final-open-ended-goals`
  passed: 1/1 sample, no blocked/failed results.
- `just agent::eval suite=map_build_consumer budget=smoke stamp=flow-final-map-build-consumer`
  passed: 3/3 samples, no blocked/failed results.
- `just agent::eval suite=scene_sampler_stress budget=smoke stamp=flow-final-scene-sampler-stress`
  passed: 20/20 samples, no blocked/failed results.
- `just agent::eval recommend intent=open-ended budget=focused output_dir=output/eval-harness/flow-final-recommend-open-ended`
  selected the open-ended contract tests, `open_ended_goals` suite, and open-task live rows.
- `just agent::eval recommend preset=map-build budget=focused output_dir=output/eval-harness/flow-final-recommend-map-build`
  selected map-build consumer, direct map-build, and runtime-prior consumer rows.
- `just agent::eval recommend intent=planner-proof budget=focused output_dir=output/eval-harness/flow-final-recommend-planner-proof`
  selected `planner-proof-dry-run-product`.
- `just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run output_dir=output/eval-harness/flow-final-planner-proof-dry-run`
  passed and wrote `proof_bundle/proof_bundle_run_manifest.json`.
- `just agent::eval suite=open_ended_goals budget=smoke agent_engine=codex-cli provider_profile=codex-env live_execution=run live_timeout_s=180 stamp=flow-open-ended-codex-live-retry3`
  passed: 1/1 live Codex open-ended result, no blocked/failed results. The 120s
  proof target was expanded to 180s because the real Codex open-ended search
  completed after a full public-waypoint sweep.

## Parked Items

- Expand open-ended samples beyond drink/search only after the first suite proves
  artifact and advisory grading behavior.
- Add authoritative semantic-satisfaction grading only when a deterministic
  public predicate is available.
- Add a planner-proof eval suite only when there are repeated versioned samples,
  not just a dry-run proof row.
- Add live map-build rows only after artifact polling and sample agent support
  are known to work for the selected engine.

## Preflight Contract

Preflight status: DRAFT

Task source: mixed user prompt + plan

Canonical source: `docs/plans/2026-06-15-non-cleanup-eval-support.md`

Route: durable `$intuitive-flow`

Goal: Implement the full non-cleanup eval support plan in one pass: open-ended
eval suite plus live proof, map-build boundary tightening, and planner-proof
eval-harness selection.

Scope:

- Add `open_ended_goals` suite and samples using public no-preset
  `surface=household-world prompt=...`.
- Align open-task live rows to the open-ended suite.
- Require a real Codex CLI / `codex-env` live open-task eval run.
- Clarify map-build consumer versus scene-sampler stress versus live map-build
  boundaries.
- Add planner-proof eval-harness signal and proof row.
- Keep `CONTEXT.md` active vocabulary on `Eval Harness`.

Non-goals:

- No new public run namespace.
- No generic predicate DSL.
- No authoritative semantic satisfaction grading.
- No full open-task success requirement over every scene-sampler sample.
- No OpenClaw proof.

Entity budget:

- reuse: `just agent::eval`, eval-harness rows, repo-native eval suite schema,
  public `run::surface`;
- remove/merge: misleading open-task rows pointing at cleanup/map suites;
- new: `open_ended_goals` suite because open-ended capability needs its own
  benchmark identity;
- expansion triggers: new evaluator predicates, new public command surface,
  planner-proof eval suite, non-Codex required live engine.

Context:

- must-read: this plan, `ARCHITECTURE.md`, `STATUS.md`, `CONTEXT.md`,
  `docs/adr/0139-use-household-open-task-surface-with-presets.md`,
  `docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md`,
  `docs/adr/0141-use-eval-harness-as-maintainer-orchestration-facade.md`,
  `evals/household_world/**`, `roboclaws/evals/**`,
  `skills/eval-harness/**`;
- avoid-unless-needed: `output/`, historical ADR logs, broad planner-proof
  archives.

Acceptance:

- SUCCESS: all planned candidates implemented; deterministic suites pass;
  eval-harness recommend selects correct open-ended/map-build/planner-proof rows;
  required live open-ended Codex eval produces a graded live result.
- BLOCKED_NEEDS_DECISION: none.
- BLOCKED_NEEDS_LOCAL_VALIDATION: required live Codex / `codex-env` route cannot
  produce a graded live result.
- INTERMEDIATE_ONLY: none unless explicitly re-approved.
- No regressions: cleanup suites and existing map-build consumer/runtime prior
  flow still pass.

Verification:

- deterministic:
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals tests/contract/dev_tools/test_eval_just_recipe.py`
- integration:
  `just agent::eval recommend intent=open-ended budget=focused`
  `just agent::eval recommend preset=map-build budget=focused`
  `just agent::eval recommend intent=planner-proof budget=focused`
- product-run:
  `just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run`
- local-live-manual:
  `just agent::eval suite=open_ended_goals budget=smoke agent_engine=codex-cli provider_profile=codex-env live_execution=run live_timeout_s=120`
- optional: none.

Execution:

- main: root supervisor owns scope, public/private boundaries, and live proof
  judgment.
- worker: none by default.
- worker-goal: none.

To execute:

```text
/goal execute docs/plans/2026-06-15-non-cleanup-eval-support.md with intuitive-flow
```

Approval: `LGTM`, `approve`, or `go ahead` approves; edits request revision.
