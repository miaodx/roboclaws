---
plan_scope: eval-harness-skill-entrypoint
status: Implemented
created: 2026-06-15
last_reviewed: 2026-06-15
implementation_allowed: true
source:
  - user request to replace the agent-validation-matrix skill with an eval-harness skill
  - user decision that no backward compatibility is required
  - agent-planning-loop scout pass on 2026-06-15
  - grill-with-docs-batch decisions accepted on 2026-06-15
  - intuitive-preflight contract drafted on 2026-06-15
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - AGENTS.md
  - CLAUDE.md
  - docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md
  - docs/human/evaluation.md
  - docs/human/agent-task-command-taxonomy.md
  - docs/human/ut_ci_design.md
  - docs/human/local-runtime.md
  - skills/README.md
  - skills/agent-validation-matrix/SKILL.md
  - skills/agent-validation-matrix/skill.json
  - docs/plans/2026-06-11-agent-validation-matrix-skill.md
  - docs/plans/2026-06-14-eval-driven-architecture.md
---

# Eval Harness Skill Entrypoint

## Goal

Replace the repo-local `agent-validation-matrix` user-facing skill with a single
`eval-harness` skill and maintainer facade.

The new entrypoint should let a user say:

```text
@eval-harness verify this plan
@eval-harness check this diff for agent capability regression
@eval-harness run the cleanup capability eval
```

and get one coherent answer:

```text
plan or diff
  -> selected deterministic gates
  -> selected product runs
  -> selected eval suites
  -> selected live-agent evals
  -> run / skipped / blocked rationale
  -> linked reports and regression-promotion guidance
```

The target is less user-facing process, not less evidence. `eval-harness` is the
single maintainer orchestration facade. Versioned `eval_suite` remains the
benchmark concept inside the facade; `run::surface` remains the product-run
surface; lower `harness::*` recipes remain private execution mechanics.

## Planning Loop

Planning loop charter:

- Goal: decide the scope for replacing `agent-validation-matrix` with
  `eval-harness` before implementation.
- Non-goals: implement code, preserve old user-facing command names, or change
  product `run::surface` semantics.
- Context inspected: active docs, current skill metadata, just recipes, eval
  runner surface, and the eval-driven architecture plan.
- Allowed worker actions: read-only planning scouts; no live providers, no paid
  probes, no file edits.
- User-review gates: final command name and live-provider default policy.
- Stop when: one plan has clear scope, acceptance, and verification.

Scout results:

- Entropy scout confirmed the material issue is not missing eval code; it is
  recurring rediscovery and false-confidence risk around which entrypoint owns
  plan/diff validation versus agent capability eval.
- Grill scout found an architectural tension: ADR-0140 currently separates
  validation matrix and eval suite as distinct layers. This plan must therefore
  update or supersede that wording, rather than pretend the change is only a
  folder rename.
- Main-session decision: keep the user's no-compatibility direction. Delete or
  rename active `agent-validation-matrix` surfaces instead of adding a shim.
  Preserve the useful selector logic only as implementation inside
  `eval-harness`.

## Grill Batch Decisions

Accepted on 2026-06-15:

- Add a new ADR that supersedes or amends ADR-0140's maintainer-facade section.
  Do not silently rewrite the prior accepted separation between validation
  matrix and eval suite.
- Use `@eval-harness` as the user-facing skill name and
  `just agent::eval recommend|execute|suite|promote-regression ...` as the
  canonical command family.
- Hard-delete the active `agent-validation` route and
  `agent-validation-matrix` skill during implementation. Do not keep a
  compatibility shim.
- For `focused` and `full`, selected required live-provider rows run by
  default after non-secret preflight. Guard, key, runtime, or provider failures
  are explicit blocked evidence, not deterministic fallback success.
- Keep `just agent::eval suite=...` as a lower-level suite runner and debugging
  path under the same command family. It is not a second user-facing skill.
- Add selector parity tests before deleting the old selector scripts so useful
  rule-table coverage is preserved under the new harness.
- Eval-harness manifests may link maintainer-only private artifacts, but must
  not inline private scorer truth, hidden targets, acceptable destinations,
  generated mess sets, `private_goal_reference`, `private_evaluation`, or raw
  provider logs.

## Current State

Implemented today:

- `skills/agent-validation-matrix/` owns a deterministic selector and runner
  for plan/diff validation gates.
- `just agent::harness agent-validation recommend|execute ...` is the active
  validation-matrix command shape.
- `roboclaws.evals` owns eval suite/sample/trial/result schemas, deterministic
  runner, live-runtime bridge, reports, and regression promotion.
- `just agent::eval suite=...` runs versioned eval suites.
- `docs/human/evaluation.md`, `ARCHITECTURE.md`, and ADR-0140 describe product
  run, validation matrix, eval suite, and harness recipe as separate layers.

Problem:

- Users now have to choose between two maintainer abstractions:
  `agent-validation-matrix` for "what gates should this change run?" and
  `agent::eval` for "did capability improve or regress?"
- That split causes recurring explanation burden and can create false
  confidence. If a user asks for agent eval and the workflow defaults to
  deterministic-only direct-runner suites, the result can look like agent
  validation while never exercising the live agent path.

## Decision

Create `eval-harness` as the single user-facing maintainer skill and facade.

No backward compatibility is required:

- remove or rename `skills/agent-validation-matrix`;
- remove active docs that present `agent-validation-matrix` as the primary
  entrypoint;
- remove or replace `just agent::harness agent-validation ...` as a current
  public maintainer route;
- update tests to the new names instead of preserving old command contracts.

Keep the internal conceptual distinction:

- Product runs: `just run::surface ...`
- Eval harness: selects and executes required validation and eval rows for a
  plan, diff, or explicit request.
- Eval suites: versioned benchmark definitions and graders used by the harness.
- Harness recipes: private low-level execution mechanics.

A new ADR must supersede or amend ADR-0140 in the same implementation slice.
The new wording should say that Roboclaws no longer exposes a separate
`agent-validation-matrix` maintainer entrypoint; `eval-harness` owns the
orchestration facade while eval suites remain first-class benchmark artifacts.

## Command Shape

Preferred user-facing skill:

```text
@eval-harness
```

Preferred maintainer command family:

```bash
just agent::eval recommend plan=docs/plans/example.md budget=focused
just agent::eval execute since=origin/main budget=focused
just agent::eval suite=cleanup_capability budget=smoke
just agent::eval promote-regression eval_results=output/evals/<suite>/<stamp>/eval_results.json ...
```

Rationale: keep one `agent::eval` facade instead of adding a second
`agent::eval-harness` command beside the existing suite runner. The command can
route by first argument or key:

- `recommend`: select rows and write an eval-harness manifest, but run nothing.
- `execute`: select rows and execute required rows according to budget and
  environment.
- `suite=<suite>`: run one versioned suite directly as a lower-level harness
  row or debugging path.
- `promote-regression`: promote failed, blocked, or inconclusive eval evidence
  into a durable regression sample.

Command grammar:

- First positional tokens `recommend`, `execute`, and `promote-regression`
  select harness subcommands.
- `suite=<suite>` with no subcommand stays direct suite-run mode.
- `recommend` and `execute` reject `suite=<suite>` unless the implementation
  deliberately supports a single-suite selection mode.
- `promote-regression` keeps the existing key/value arguments.
- Unknown positional commands fail with a clear usage error.
- `ROBOCLAWS_JUST_TRACE=1 just agent::eval ...` prints the resolved
  `roboclaws.cli.main eval` command without running it, preserving the current
  dev-tool recipe testing pattern.

Do not introduce a parallel public `just agent::eval-harness ...` command unless
implementation proves the `agent::eval` family impossible. If that exception is
needed, record it as a plan update before shipping.

## Budget And Live Defaults

The default must not silently turn agent eval into deterministic-only proof.

Budget policy:

- `recommend`: no execution; selected live rows are listed with commands and
  expected preflight requirements.
- `execute budget=smoke`: cheap deterministic confidence only. Live rows are
  recorded as `required_skipped_by_user_budget` when selected. This is allowed
  only because the user explicitly chose smoke.
- `execute budget=focused`: default execution mode. Run required deterministic
  gates, required product rows, required eval suites, and selected required
  live-agent evals after preflight.
- `execute budget=full`: run all selected required and recommended rows unless
  blocked by environment, network, provider, hardware, or explicit guard.

Live policy:

- Focused/full selected required live rows must either run or produce explicit
  blocked evidence. Do not downgrade them to deterministic direct-runner
  success.
- Before live rows, run non-secret preflight for network guard, repo-local
  `.env` key presence, Docker/runtime availability when needed, and route
  allowability.
- Work-network rules from `AGENTS.md` still apply. OpenClaw and
  system-provider Claude Code remain blocked on the work network. Codex
  `codex-env` may run there only when repo-local `CODEX_BASE_URL` and
  `CODEX_API_KEY` are configured.
- Provider 5xx/429/model-service failures classify as
  `model_or_provider_unavailable`.
- Missing simulator/runtime/Docker/hardware classifies as
  `environment_blocked`.
- Unknown runner exceptions classify as `harness_bug_unclassified` until
  investigated.

## Target Layout

Skill layout:

```text
skills/eval-harness/
  SKILL.md
  skill.json
  scripts/select_eval_harness.py
  scripts/run_eval_harness.py
```

Remove active `skills/agent-validation-matrix/` after the new skill reaches
parity. Do not keep a compatibility alias.

Output layout:

```text
output/eval-harness/<stamp>/
  eval_harness.json
  eval_harness.md
  eval_harness.html
  rows/<row-id>/
  evals/<suite-id>/<stamp>/...
```

Existing `output/evals/<suite>/<stamp>/` may remain the suite runner's raw
output root. Eval-harness manifests should link to those suite outputs rather
than duplicate large artifacts.

Private-data rule:

- `eval_harness.json`, `eval_harness.md`, and `eval_harness.html` may link to
  maintainer-only private artifacts as post-run evidence.
- They must not inline `private_goal_reference`, `private_evaluation`, hidden
  target lists, acceptable destinations, generated mess sets, private
  manifests, or raw provider logs.
- Agent-facing product inputs, MCP profile metadata, and skill metadata must
  remain free of private scorer truth.

Manifest schema:

```text
roboclaws_eval_harness_manifest_v1
```

Each row records:

- row id and kind: `deterministic_gate`, `product_run`, `eval_suite`,
  `live_agent_eval`, `regression_promotion`, or `manual_review`;
- selected command;
- source signals from plan, diff, explicit axes, or user request;
- required/recommended/optional classification;
- budget behavior;
- status: ran, failed, blocked, skipped by budget, skipped irrelevant, or not
  run;
- blocker category and non-secret preflight metadata when blocked;
- artifacts and report links.

## Selection Rules

Start by porting the existing deterministic rule-table selector. Do not add an
LLM classifier in the first pass.

Initial selection directions:

| Signal | Eval-harness behavior |
| --- | --- |
| `roboclaws/evals/**`, eval CLI, eval reports | Run eval unit tests and `smoke_regression`; run affected suite if obvious. |
| Runtime Metric Map, map-build, map consumers, actionability | Select `map_build_consumer`. |
| Cleanup prompt, cleanup MCP policy, manipulation loop, done readiness | Select cleanup contract gates plus `cleanup_capability`; focused/full selects live agent eval. |
| Live runtime, provider profile, Codex/Claude/OpenAI Agents SDK launcher | Select route trace/preflight plus focused live eval for affected engine/profile. |
| Visual grounding, camera labeler, RAW-FPV | Select relevant perception/camera gates and product rows. |
| Docs-only command taxonomy or skill guidance | Select docs/lint/link-style checks and recommend eval rows only when docs claim behavior changed. |

Every selected row must explain why it was selected. Every skipped row must
explain why it was skipped.

## Implementation Slices

### Slice 0: Contract And ADR

Scope:

- add a new ADR that supersedes or amends ADR-0140's maintainer-facade
  language and makes `eval-harness` the orchestration facade;
- clarify that eval suites remain the benchmark layer under the facade;
- update `ARCHITECTURE.md`, `docs/human/evaluation.md`, and
  `docs/human/agent-task-command-taxonomy.md` with the new entrypoint.

Acceptance:

- a new agent can explain when to use `@eval-harness`;
- active docs no longer ask the user to choose between
  `agent-validation-matrix` and eval suites as separate maintainer entrypoints;
- product `run::surface` and private `harness::*` boundaries remain intact.

### Slice 1: Skill Rename And Instructions

Scope:

- replace `skills/agent-validation-matrix/` with `skills/eval-harness/`;
- rewrite `SKILL.md` trigger metadata around plan/diff validation,
  capability regression checks, selected eval suites, live-agent eval, blocked
  rationale, and regression promotion;
- update `skill.json` role, scripts, outputs, lifecycle notes, and evidence
  outputs;
- update `skills/README.md`.

Acceptance:

- only `eval-harness` appears in maintained skill docs as the validation/eval
  orchestration skill;
- the skill body is concise and leaves deterministic mechanics in scripts;
- no compatibility alias or stale maintained `agent-validation-matrix` skill
  remains.

### Slice 2: Eval-Harness Selector And Runner

Scope:

- port `select_validation_matrix.py` to `select_eval_harness.py`;
- port `run_validation_matrix.py` to `run_eval_harness.py`;
- add eval-suite row kinds and calls into `roboclaws.evals.runner`;
- add live-agent eval row execution with focused/full default live behavior;
- write `eval_harness.json`, `.md`, and `.html` under
  `output/eval-harness/<stamp>/`;
- remove current public `agent-validation` route.
- add `roboclaws.evals.cli` support for `recommend` and `execute`, not only
  `suite=...` and `promote-regression`.

Acceptance:

- `recommend` emits deterministic gates, product rows, eval-suite rows,
  live-agent eval rows, skipped rows, blocked rows, commands, rationale, and
  artifact paths;
- `execute budget=focused` runs selected live-agent eval rows when preflight
  passes;
- focused/full never record selected live evals as deterministic-only success;
- blocked live rows carry `model_or_provider_unavailable`,
  `environment_blocked`, or route-specific guard categories.
- selector parity tests prove the existing validation-matrix rule table was
  preserved or intentionally replaced by named eval-harness rules.
- manifest tests cover `roboclaws_eval_harness_manifest_v1` row kinds,
  statuses, linked artifacts, and redaction of private scorer truth.

### Slice 3: Command And Test Migration

Scope:

- update `just/agent.just`, `just/harness.just`, `just/README.md`, `AGENTS.md`,
  and `CLAUDE.md`;
- update or replace tests that mention `agent-validation-matrix`,
  `validation_matrix`, or `agent-validation`;
- update output path expectations from `output/agent-validation-matrix/` to
  `output/eval-harness/`;
- preserve raw eval suite execution as a mode of the eval facade.
- remove the active `agent-validation` route rather than preserving a shim.

Acceptance:

- `just --summary` shows the intended public maintainer route;
- no active first-read docs recommend `just agent::harness agent-validation`;
- tests assert the new route and intentionally do not require the old route.
- negative command-surface tests prove `just agent::harness agent-validation`
  is no longer an allowed active route.

### Slice 4: Regression Promotion And Closeout

Scope:

- expose regression promotion through the eval-harness skill and command
  family;
- update examples showing how to promote failed, blocked, or inconclusive eval
  results;
- run the new harness against this plan file as its own proof.

Acceptance:

- a failed/blocked eval row can be promoted without leaving the eval-harness
  workflow;
- this plan's final verification includes a focused `recommend` and either a
  focused live run or an explicit environment/provider blocked live row.

## Verification Plan

Deterministic checks:

```bash
ruff check .
git diff --check
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools
```

Focused migrated checks:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_eval_just_recipe.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/evals/test_eval_harness_selector.py
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/evals/test_eval_harness_manifest.py
```

Existing suite proofs:

```bash
just agent::eval suite=smoke_regression budget=smoke
just agent::eval suite=map_build_consumer budget=smoke
just agent::eval suite=cleanup_capability budget=smoke
```

New harness proofs:

```bash
just agent::eval recommend \
  plan=docs/plans/2026-06-15-eval-harness-skill-entrypoint.md \
  budget=focused

just agent::eval execute \
  plan=docs/plans/2026-06-15-eval-harness-skill-entrypoint.md \
  budget=focused
```

The focused execute proof must either run a selected live-agent eval or record
an explicit live blocker. It must not silently downgrade live-agent rows to
deterministic-only success.

Optional broad proof:

```bash
just agent::verify ci-required
```

## Risks And Stop Gates

Risks:

- Terminology collapse: `eval-harness` could blur eval suites, validation
  selection, product runs, and low-level harness mechanics.
- Cost/safety regression: focused/full live defaults can spend provider budget
  or hit guarded routes unless preflight is strict.
- Selection regression: deleting `agent-validation-matrix` too early could lose
  useful deterministic rule-table coverage.
- Documentation churn: historical plans contain many old references; updating
  all history would create noise.

Stop gates:

- Stop if the new ADR cannot supersede or amend ADR-0140 coherently.
- Stop if the command shape creates two equally prominent user-facing eval
  entrypoints.
- Stop if focused/full live behavior cannot distinguish ran, blocked, and
  budget-skipped rows.
- Stop if private evaluator truth would become visible in skill metadata,
  MCP profiles, or agent-facing product inputs.

Historical references policy:

- Update active docs, agent guidance, skill docs, just docs, tests, and current
  plans.
- Do not rewrite shipped retrospectives or old plan history solely to rename
  `agent-validation-matrix`.

## Non-Goals

- Do not preserve a user-facing `agent-validation-matrix` route or skill.
- Do not change product `run::surface` grammar.
- Do not make lower `harness::*` recipes public.
- Do not make deterministic direct-runner suites stand in for selected live
  agent eval.
- Do not add an LLM selector in the first implementation.
- Do not expose private generated mess sets, acceptable destinations, or hidden
  scorer truth to agent-facing inputs.

## Preflight Contract

Preflight status: DRAFT

Task source: plan path

Canonical source:
`docs/plans/2026-06-15-eval-harness-skill-entrypoint.md`

Route: durable `$intuitive-flow`

Goal: replace `agent-validation-matrix` with `eval-harness` as the single
maintainer validation/eval orchestration entrypoint.

Scope:

- Add a new ADR superseding or amending ADR-0140's maintainer-facade contract.
- Replace `skills/agent-validation-matrix` with `skills/eval-harness`.
- Move selector/runner behavior to eval-harness with eval-suite and live-agent
  row kinds.
- Extend `just agent::eval` / `roboclaws.evals.cli` with `recommend` and
  `execute`.
- Remove active `agent-validation` route with no shim.
- Update active docs, agent guidance, tests, output schema/path expectations.

Non-goals:

- No compatibility route for `agent-validation-matrix`.
- No product `run::surface` grammar change.
- No public `harness::*` promotion.
- No deterministic-only fallback for selected live-agent eval.
- No LLM selector in the first implementation.

Context:

- must-read: this plan, `README.md`, `ARCHITECTURE.md`, `STATUS.md`,
  `AGENTS.md`, `CLAUDE.md`, ADR-0140, `docs/human/evaluation.md`,
  `docs/human/agent-task-command-taxonomy.md`,
  `skills/agent-validation-matrix/**`, `roboclaws/evals/**`,
  `just/agent.just`, and `just/harness.just`;
- useful: `tests/contract/dev_tools/test_eval_just_recipe.py`, old selector
  tests, and `docs/plans/2026-06-14-eval-driven-architecture.md`;
- avoid unless needed: historical retrospectives, generated `output/**`, and
  old `.planning/**`.

Acceptance:

- SUCCESS: `@eval-harness` and
  `just agent::eval recommend|execute|suite|promote-regression` are documented
  and working; old active route removed; new ADR in place; harness manifests
  record selected/running/blocked/skipped rows without private-truth leakage.
- BLOCKED_NEEDS_DECISION: none expected.
- BLOCKED_NEEDS_LOCAL_VALIDATION: focused live-provider proof cannot run
  because provider/runtime/network/Docker/simulator is unavailable.
- INTERMEDIATE_ONLY: only if implementation lands docs/schema/selector without
  final execute proof.
- No regressions: existing raw `just agent::eval suite=...` and
  `promote-regression` keep working.

Verification:

- deterministic: `ruff check .`; `git diff --check`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools`;
- integration: new selector parity tests; new manifest/redaction tests;
  updated `test_eval_just_recipe.py`; negative test for removed
  `just agent::harness agent-validation`;
- product-run:
  `just agent::eval recommend plan=docs/plans/2026-06-15-eval-harness-skill-entrypoint.md budget=focused`;
- local-live-manual:
  `just agent::eval execute plan=docs/plans/2026-06-15-eval-harness-skill-entrypoint.md budget=focused`,
  expecting live rows to run or produce explicit blocked evidence;
- optional: `just agent::verify ci-required`.

Execution:

- main: supervise scope, ADR contract, deletion/no-shim decision, and final
  verification.
- worker: optional skill-runner/Paseo worker for implementation under
  `$intuitive-flow`.
- worker-goal: implement the plan end to end, stopping on ADR incoherence,
  command split, live row status ambiguity, or private-truth leakage.

To execute:

```text
/goal execute docs/plans/2026-06-15-eval-harness-skill-entrypoint.md with intuitive-flow
```

Approval: `LGTM`, `approve`, or `go ahead` approves this preflight; edits
request revision.

## Next Execution Route

Use durable `intuitive-flow` for implementation. This is a cross-cutting
command, skill, docs, and tests change with live-provider guard semantics; it
is too broad for a one-off direct edit.

## Implementation Evidence

Status: Implemented - deterministic gates pass; focused execute proof ran
selected live-agent eval rows and exposed live-agent failures or blockers
instead of downgrading them to deterministic success.

Shipped changes:

- Added ADR-0141, making `eval-harness` the maintainer orchestration facade and
  amending ADR-0140's separate validation-matrix wording.
- Replaced `skills/agent-validation-matrix/` with `skills/eval-harness/`.
- Added `roboclaws_eval_harness_manifest_v1` rows for deterministic gates,
  product runs, eval suites, live-agent evals, and blocked/skipped/failure
  rationale.
- Extended `just agent::eval` / `roboclaws.evals.cli` with
  `recommend` and `execute`; direct `suite=...` and `promote-regression`
  remain under the same facade.
- Removed the active `just agent::harness agent-validation ...` route with no
  compatibility shim.
- Updated active docs, agent guidance, skill docs, command tests, selector
  parity tests, manifest/redaction tests, and output paths.

Verification evidence:

- `ruff check .` passed.
- `git diff --check` passed.
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals` passed.
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools` passed.
- After the final aggregate-classification/reporting fix,
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_harness_manifest.py tests/unit/evals/test_eval_harness_selector.py`
  passed.
- Existing suite proofs passed:
  - `just agent::eval suite=smoke_regression budget=smoke stamp=20260615_verify_smoke`
  - `just agent::eval suite=map_build_consumer budget=smoke stamp=20260615_verify_map`
  - `just agent::eval suite=cleanup_capability budget=smoke stamp=20260615_verify_cleanup`
- Focused recommend proofs wrote
  `output/eval-harness/20260615_plan_recommend/eval_harness.json` with selected
  deterministic, product, eval-suite, and live-agent eval rows. The final
  patched recommend proof wrote
  `output/eval-harness/20260615_plan_recommend_after_render_fix/eval_harness.json`.
- Final focused execute proof wrote
  `output/eval-harness/20260615_plan_execute_after_render_fix/eval_harness.json`
  and
  `output/eval-harness/20260615_plan_execute_after_render_fix/eval_harness.html`.
  It selected 13 rows: deterministic gates, direct product rows, and direct
  eval-suite rows passed; selected live-agent rows ran or recorded explicit
  live blockers. `codex-cleanup-live-eval` and
  `openai-agents-sdk-open-task-live-eval` ran and recorded
  `outcome=failed` with `failure_class=harness_bug_unclassified`; the
  `codex-cleanup-camera-raw-fpv-live-product` row recorded
  `status=blocked`, `outcome=blocked`, and
  `blocker_category=environment_blocked`. The harness exited nonzero because
  failed live eval aggregates are now treated as failed harness outcomes even
  when the suite subprocess itself exits 0.
- The final `eval_harness.md` / `.html` reports show row `Outcome` and
  `Failure class`, so failed aggregates are visible in the review surface and
  not hidden behind execution-state `status=ran`.
- A redaction grep over the final top-level `eval_harness.json` and
  `eval_harness.md` found no private scorer truth or provider secret matches.
