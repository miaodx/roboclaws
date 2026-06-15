---
refactor_scope: python-quality-backend-entropy
status: PAUSED
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-15
completed_ledger: docs/plans/refactor-python-quality-backend-entropy-completed.md
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

PAUSED. Code execution is paused while the repo has many parallel changes.
This file is the unfinished active plan only. Completed work lives in
`docs/plans/refactor-python-quality-backend-entropy-completed.md`.

Checkpoint quality signal from `python scripts/dev/check_python_quality_ratchet.py
--summary --top 30` on 2026-06-15, before later parallel repo changes:

- 19 Ruff complexity violations.
- 56 oversized modules.
- Remaining complexity is test-heavy; remaining file-size debt is split between
  large production modules and large behavior tests.

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

Severity: P1. Remaining complexity is now mostly in tests, led by
`test_isaac_lab_backend.py`, `test_molmo_cleanup_report.py`,
`test_molmo_realworld_contract.py`, checker tests, and apple-to-apple tests.
Use fixture builders and focused assertion helpers; do not split only for line
count. Owner: `intuitive-tests`. Proof: focused pytest, ruff, ratchet summary.

### B: Contract And Report Hard-Ceiling Split

Severity: P1. `roboclaws/household/realworld_contract.py` and
`roboclaws/household/report.py` are still over 6000 lines. Split only around
real ownership boundaries: payload builders, policy/event families, section
renderers, or artifact envelopes. Preserve public schemas and rendered report
shape. Owner: `intuitive-refactor`.

### C: Backend Worker Hard-Ceiling Split

Severity: P1. `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` and
`scripts/molmo_cleanup/molmospaces_subprocess_worker.py` remain far above the
2000-line ceiling. Split command families, runtime metadata, render/camera
helpers, and state writeback without importing Isaac into normal Roboclaws
processes. Owner: `intuitive-refactor`.

### D: Visual Comparison Pipeline Split

Severity: P1. `roboclaws/household/scene_camera_comparison.py` and
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` remain
oversized. Prefer capture-lane stages, diagnostics builders, manifest/artifact
setup helpers, and report-specific modules. Real renderer claims still require
separate local proof. Owner: `intuitive-refactor`.

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

### G: Scene-Sampler Readiness Drift

Severity: P1. Scene-sampler readiness work still leaves
`roboclaws/launch/scene_sampler.py` over the hard 2000-line ceiling, and the
readiness-export test remains the largest remaining test complexity row. The
first scanner-evidence extraction removed current production complexity rows
from `scene_sampler.py`, so the next useful work is another ownership split or
focused readiness-export fixtures instead of accepting the oversized file as
stable. Owner: `intuitive-refactor` / `intuitive-tests`. Proof: focused
scene-sampler tests, ruff, and ratchet summary.

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
