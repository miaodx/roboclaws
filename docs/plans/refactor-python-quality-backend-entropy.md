---
refactor_scope: python-quality-backend-entropy
status: PAUSED
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-16
completed_ledger: docs/plans/refactor-python-quality-backend-entropy-completed.md
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

PAUSED. Code execution is paused while the repo has many parallel changes.
This file is the unfinished active plan only. Completed work lives in
`docs/plans/refactor-python-quality-backend-entropy-completed.md`.

Checkpoint quality signal from `python scripts/dev/check_python_quality_ratchet.py
--summary --top 40` on 2026-06-16, after the latest verified visual-comparison
lighting-diagnostics slice:

- 0 Ruff complexity violations.
- 62 oversized modules.
- Remaining work is file-size and ownership-boundary debt split between large
  production modules and large behavior tests.
- `roboclaws/household/scene_camera_comparison.py` is down to 5476 lines after
  the first USD render-contract, image-metrics, and lighting-diagnostics
  splits, but remains a P1 hard-ceiling candidate.
- `roboclaws/household/realworld_contract.py` is down to 5637 lines after the
  first contract projection split, but remains a P1 hard-ceiling candidate.
- `roboclaws/household/report.py` is down to 5816 lines after the Isaac
  runtime diagnostics section split, and is currently the largest P1
  hard-ceiling candidate.
- Backend workers are no longer hard-ceiling blockers:
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` is 1990 lines and
  `scripts/molmo_cleanup/molmospaces_subprocess_worker.py` is 1811 lines.

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

## Refactor Strategy

Future slices may use deeper design refactors when they reduce entropy. Good
patterns for this repo include backend facade/protocol boundaries, typed
evidence envelopes, strategy tables, command catalogs, pipeline/stage objects,
report section renderers, artifact builders, fixture builders, and scenario
factories.

Preserve public CLI flags, launch axes, artifact schemas, report output,
agent-facing contracts, and private/public evaluation boundaries unless a slice
explicitly declares and verifies a migration.

## Current Target

Continue the Python code-size and complexity cleanup with stronger file-size
pressure than the earlier ratchet-only loop. Complexity has fallen quickly;
the next useful work should prioritize hard-ceiling files, test fixture debt,
and backend/report/evidence boundaries that prevent branching from returning.

## Active Candidates

### A: Behavior-Test Fixture Builders

Severity: P2 unless a file crosses the hard ceiling or blocks a product
boundary. Ruff complexity rows are currently zero, but several large behavior
test modules still obscure setup ownership. Use fixture builders and focused
assertion helpers only when they make the tested behavior easier to scan; do
not split only for line count. Owner: `intuitive-tests`. Proof: focused pytest,
ruff, ratchet summary.

### B: Contract And Report Hard-Ceiling Split

Severity: P1. `roboclaws/household/realworld_contract.py` is no longer the
largest module after the first projection helper split, but it remains above
the hard ceiling; `roboclaws/household/report.py` is now below 6000 lines
after the first Isaac runtime renderer split, but remains above the hard
ceiling. Continue only around real ownership boundaries: payload builders,
policy/event families, section renderers, or artifact envelopes. Preserve
public schemas and rendered report shape. Owner: `intuitive-refactor`.

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

## Evidence Ladder

- Static: `ruff check <touched files>`, `ruff format --check <touched files>`,
  and `python scripts/dev/check_python_quality_ratchet.py`.
- Focused tests: use `./scripts/dev/run_pytest_standalone.sh <tests> -q`.
- Contract/report changes: include the relevant contract or report tests.
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
