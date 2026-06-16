---
refactor_scope: python-quality-backend-entropy
status: ACTIVE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-16
completed_ledger: docs/plans/refactor-python-quality-backend-entropy-completed.md
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

ACTIVE. Continue one verified, non-overlapping slice at a time while unrelated
scene-sampler/operator-console changes remain dirty in the worktree. This file
is the unfinished active plan only. Completed work lives in
`docs/plans/refactor-python-quality-backend-entropy-completed.md`.

Refreshed quality signal from `python scripts/dev/check_python_quality_ratchet.py
--summary --top 40` on 2026-06-16 in the current dirty checkout:

- 1 Ruff complexity violation:
  `tests/unit/operator_console/test_scene_sampler_readiness_export.py::_assert_next_flow`
  at `54>50`.
- 62 oversized modules.
- Remaining work is file-size and ownership-boundary debt split between large
  production modules and large behavior tests.
- `roboclaws/household/realworld_contract.py` is down to 4930 lines after the
  projection, agent-view boundary, visual-candidate, runtime-map contract, and
  done-readiness helper splits, but remains a P1 hard-ceiling candidate.
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` is down
  to 4900 lines after the report renderer split, but remains a P1
  hard-ceiling candidate.
- `roboclaws/household/scene_camera_comparison.py` is down to 4693 lines after
  the first USD render-contract, image-metrics, lighting-diagnostics, and
  render-domain diagnostics splits, but remains a P1 hard-ceiling candidate.
- `roboclaws/household/report.py` is down to 3820 lines after the Nav2 map,
  semantic-map artifact, and agent/perception section splits, but remains a P1
  hard-ceiling candidate.
- Backend workers are no longer hard-ceiling blockers:
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` is 1990 lines and
  `scripts/molmo_cleanup/molmospaces_subprocess_worker.py` is 1811 lines.
- Scene-sampler drift is active again in the current dirty worktree:
  `roboclaws/launch/scene_sampler.py` is 2444 lines. Treat this as owned by the
  current scene-sampler/eval work until it lands; if it remains above 2000 lines
  at the next clean checkpoint, reopen it as a P1 cleanup slice here.
- `roboclaws/household/agibot_contract_rehearsal.py` is now 1949 lines after
  the evidence/readiness payload split, below the hard ceiling.

Do not treat these counts as current during execution. Refresh the repo-wide
summary before selecting or completing a slice.

## Two-Document Contract

- Active unfinished plan: this file.
- Completed concise ledger:
  `docs/plans/refactor-python-quality-backend-entropy-completed.md`.
- Do not create a third related plan, scratch log, or per-slice history file
  for this cleanup stream.
- Do not paste full command logs into either file. Keep only decision-relevant
  metrics, ownership, and proof class.

## Fixed Maintenance Action

Run this compaction step every 3-5 accepted slices, before pausing/committing a
checkpoint, or whenever this active plan grows beyond about 250 lines:

1. Refresh the ratchet summary.
2. Move completed active items into the completed ledger as compact bullets.
3. Trim this file back to unresolved decisions, current candidates, proof
   gates, and stop conditions.
4. Keep completed entries short: one slice or bundle, one effect, one proof
   level, and the metric delta if it matters.
5. If the completed ledger grows too large, compress older rows in place
   instead of creating another document.

Entry size rule: active candidates should usually fit in 6-8 lines; completed
ledger entries should usually fit in 2-4 lines.

## Out-of-Plan Drift Guard

Before each implementation slice, and again before marking the slice complete:

1. Run `python scripts/dev/check_python_quality_ratchet.py --summary --top 40`.
2. Compare the summary against this active plan, not only against touched
   files.
3. If new files outside the active candidates cross 2000 lines, gain new Ruff
   complexity rows, or cause the repo totals to regress, pause execution and
   update `## Active Candidates` before continuing.
4. Promote new drift to P1 when it crosses the hard file-size ceiling, adds
   production/shared complexity, or hides a false-green gate. Promote to P2
   when it is test-only or local workflow friction with clear ownership.
5. If the drift belongs to another active plan, reference that plan in one line
   here instead of duplicating detail.
6. If no new material drift appears, record only the refreshed totals in the
   completed ledger during the next compaction.

This guard is intentionally repo-wide. A slice that improves one planned file
should not finish while newly changed, plan-external files quietly become the
largest quality debt.

## Quality Standard

- Default target: Python modules stay under 800 lines.
- Justified larger modules: 800-1200 lines may be acceptable with one cohesive
  owner and a documented reason.
- Warning band: 1200-2000 lines requires an explicit split rationale and stays
  tracked as active debt.
- Hard ceiling: non-generated, non-vendor Python files over 2000 lines are P1
  entropy candidates unless a maintainer records a narrow exception. Do not
  normalize application or test files above 2000 lines as a stable end state.
- Complexity target: production/shared code trends toward zero ratcheted Ruff
  complexity rows. Test complexity is reduced through fixture builders, data
  factories, behavior-focused split tests, and shared assertions.
- Line-count relief is evidence, not the goal. Prefer fewer concepts, clearer
  owners, and less branching over extraction that only moves code around.

## Refactor Strategy

Use `$intuitive-refactor` ratchet mode for this stream. A slice may simplify
architecture and delete or change old internal behavior when that removes stale
surfaces or duplicate concepts. Preserve only current public launch axes,
artifact schemas, report claims, agent-facing contracts, and private/public
evaluation boundaries unless the slice explicitly declares and verifies a
migration.

Good patterns for this repo include backend facade/protocol boundaries, typed
evidence envelopes, strategy tables, command catalogs, pipeline/stage objects,
report section renderers, artifact builders, fixture builders, and scenario
factories. Bad patterns are compatibility shims for retired names, wrappers
that only preserve old call shapes, and splits that leave the same branching in
a different file.

## Current Target

Continue the Python code-size and complexity cleanup with stronger file-size
pressure than the earlier ratchet-only loop. Complexity has fallen quickly;
the next useful work should prioritize hard-ceiling files, test fixture debt,
and backend/report/evidence boundaries that prevent branching from returning.

Next execution should start from a clean or explicitly scoped dirty checkpoint:
first settle the current scene-sampler/eval changes or make them own their
ratchet fallout, then choose one P1 hard-ceiling architecture slice. Do not
continue by shaving isolated lines from many files.

## Execution Preflight

Preflight status: DRAFT.
Task source: plan path.
Canonical source: `docs/plans/refactor-python-quality-backend-entropy.md`.
Route: `$intuitive-refactor` ratchet mode.
Goal: Continue this cleanup with one architecture-simplifying slice, starting
by resolving or explicitly scoping current scene-sampler/eval ratchet fallout.

Scope:

- Refresh ratchet signal before edits.
- Treat current `scene_sampler.py` / operator-console test complexity drift as
  the first checkpoint.
- If that dirty work is active and in scope, reduce it below the hard ceiling
  or record a follow-up exception in this plan.
- Otherwise choose one P1 hard-ceiling architecture slice from this plan and
  execute it vertically: code, callers, tests, stale internal paths, proof.

Non-goals: broad repo cleanup, line-count shaving across many files,
preserving obsolete internal wrappers, live/provider/simulator proof unless the
chosen slice changes that route.

Entity budget: reuse this plan, existing owners, tests, and helpers;
remove/merge obsolete internal compatibility paths when callers move; add a new
module or helper only around a named architecture boundary; re-approve if a
slice would change a public launch, artifact, report, or agent contract.

Context: must-read root orientation docs, this active plan, the completed
ledger, current ratchet summary, touched module tests, and call sites. Avoid
old retrospectives, parked `TODOS.md` / `THOUGHTS.md`, and full historical
phase logs unless needed.

Acceptance:

- Success: one accepted slice reduces architecture friction, updates callers
  and tests, removes or parks stale surfaces, and leaves ratchet totals
  non-regressed.
- Blocked needs decision: public behavior, schema, report contract, or
  agent-facing contract would change beyond this plan.
- Blocked needs local validation: only if the chosen slice affects simulator,
  live provider, or hardware behavior that cannot be proven locally.
- Intermediate only: none unless explicitly approved before execution.
- No regressions: current public launch axes, artifact schemas, report claims,
  agent-facing contracts, and private/public eval boundaries remain intact
  unless explicitly migrated.

Verification: deterministic gates are `ruff check <touched files>`,
`ruff format --check <touched files>`,
`python scripts/dev/check_python_quality_ratchet.py --summary --top 40`, and
focused pytest via `./scripts/dev/run_pytest_standalone.sh <tests> -q`.
If eval, launch, or agent-facing files change, use
`just agent::eval recommend plan=docs/plans/refactor-python-quality-backend-entropy.md budget=focused`
or `just agent::eval execute ...` for gate selection. Product-run and
local-live-manual gates are required only when the selected slice changes a
public route or real simulator/provider claim.

Execution: main session supervises and verifies one slice; no delegated worker
by default.
To execute:
`/goal execute docs/plans/refactor-python-quality-backend-entropy.md with intuitive-flow`.
Approval: LGTM/approve/go ahead approves; edits request revision.

## Active Candidates

### A: Behavior-Test Fixture Builders

Severity: P2, promoted to P1 when a test file crosses the 2000-line hard
ceiling or hides a false-green gate. The current lone complexity row is
operator-console scene-sampler readiness test fallout; keep it with the active
scene-sampler/eval work unless it survives the next clean checkpoint. Use
fixture builders and focused assertion helpers only when they make behavior
ownership easier to scan. Owner: `intuitive-tests`. Proof: focused pytest,
ruff, ratchet summary.

### B: Contract And Report Hard-Ceiling Split

Severity: P1. `roboclaws/household/realworld_contract.py` is now 4930 lines
after the projection, agent-view boundary, visual-candidate, runtime-map
contract, and done-readiness helper splits and remains above the hard ceiling;
`roboclaws/household/report.py` is now 3820 lines after the Isaac runtime,
grasp diagnostics, proof request-selection renderer, Nav2 map bundle renderer,
semantic-map artifact writer, and agent/perception section splits, but remains
above the hard ceiling. Continue only around real ownership boundaries: payload
builders, policy/event families, section renderers, or artifact envelopes.
Preserve current public schemas and report claims, but remove obsolete internal
compatibility paths when current callers and tests move to the cleaner owner.
Owner: `intuitive-refactor`.

### C: Backend Worker Hard-Ceiling Split

Status: cleared on 2026-06-16; see the completed ledger. Keep reopened only
for fresh backend-worker hard-ceiling regressions or wrapper/import drift that
pushes either worker back above 2000 lines.

### D: Visual Comparison Pipeline Split

Severity: P1. `roboclaws/household/scene_camera_comparison.py` and
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` remain
oversized. Prefer capture-lane stages, diagnostics builders, manifest/artifact
setup helpers, and report-specific modules. Real renderer claims still require
separate local proof. Owner: `intuitive-refactor`.
Latest metric: `scene_camera_comparison.py` is down to 5476 lines after the
USD render-contract, image-metrics, and lighting-diagnostics helper splits, but
remains above the hard ceiling.
Current metric: `scene_camera_comparison.py` is down to 4693 lines after the
render-domain diagnostics split; `run_robot_camera_apple2apple_comparison.py`
is down to 4900 lines after the report renderer split. Both remain P1
hard-ceiling files.

### E: Backend Evidence And Live Runtime Normalization

Severity: P2. The facade work is useful but backend metadata/evidence still
appears across live-agent, Agibot, and run-result paths. Normalize evidence
envelopes and backend identity where this removes repeated branching. Watch
`openai_agents_live.py`, `run_live_openai_agents_cleanup.py`, and
`agibot_contract_rehearsal.py`. Owner: `intuitive-refactor`.

### F: Agent Guidance Skill-Router Drift

Severity: P2. `AGENTS.md` and `CLAUDE.md` still mention
`hybrid-phase-pipeline`, while this environment exposes `intuitive-flow`.
Fix only if startup rediscovery continues to cost time; keep it separate from
code-size slices. Owner: `intuitive-init`.

### G: Scene Sampler Hard-Ceiling Drift

Status: conditionally reopened by the current dirty checkout. The ratchet now
reports `roboclaws/launch/scene_sampler.py` at 2444 lines plus one related
operator-console test complexity row. If the active scene-sampler/eval work is
about to land, that work should either split the facade back below 2000 lines or
record why the drift belongs to a follow-up. If the dirty work is parked, reopen
this plan candidate as P1 before taking another unrelated hard-ceiling slice.

## Evidence Ladder

- Static: `ruff check <touched files>`, `ruff format --check <touched files>`,
  and `python scripts/dev/check_python_quality_ratchet.py`.
- Focused tests: use `./scripts/dev/run_pytest_standalone.sh <tests> -q`.
- Contract/report changes: include the relevant contract or report tests.
- Changed-code review: after implementation, run `$intuitive-refactor`
  changed-code review on the changed scope before final verification when the
  slice is not docs-only.
- Agent-facing/eval/launch changes: prefer `just agent::eval recommend` or
  `just agent::eval execute` for gate selection instead of hand-writing a fixed
  eval list.
- Simulator/live claims: only claim them after an explicit local run on a ready
  environment.

## Stop Condition

Stop this cleanup stream when:

- Non-generated, non-vendor files above 2000 lines are either split below the
  ceiling or have a recorded narrow exception.
- Production/shared Ruff complexity rows are at or near zero.
- Remaining test complexity is fixture-builder debt with clear ownership, not
  one-off long test bodies.
- Backend id, runtime metadata, artifacts, and evidence attachments use common
  surfaces instead of repeated concrete-class or `backend == ...` branching.
- A fresh reduce-entropy round finds no P0/P1 or material P2 candidate in this
  code-size/backend-complexity class.
