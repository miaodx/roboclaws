# MolmoSpaces Prior Covered Proof Selection Memory

**Status:** Completed for Phase 92 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0083-exclude-prior-covered-planner-proofs.md`

## Goal

Prevent broader proof-bundle dry-runs from selecting cleanup requests that
already have strict planner-backed proof and promoted cleanup binding.

## Problem

After Phase91, `proof_008` is useful evidence but not future work. The proof
selector remembered grasp-infeasible requests, but it did not exclude already
covered requests. That made the next local proof run vulnerable to spending
time on `proof_008` again instead of expanding coverage.

## Scope

- Add `--exclude-prior-covered` to the proof-bundle runner.
- Treat prior `planner_backed && cleanup_binding_promoted` as covered.
- Render covered exclusions in the existing runner report.
- Add runner checker requirements for covered exclusions and selected-count
  bounds.
- Dry-run the Phase89 broader source against the Phase90 prior bundle to prove
  the current seed has no remaining commands.

## Non-Goals

- Do not execute more RBY1M/CuRobo proof probes in this slice.
- Do not claim full planner-backed cleanup readiness.
- Do not create another report renderer.
- Do not commit generated `output/` artifacts.

## Acceptance Criteria

- Covered prior proof requests are excluded with reason
  `prior_planner_proof_covered`.
- Covered exclusions do not create fallback commands.
- The runner report shows the covered count and prior proof visuals.
- The runner checker can require at least one covered exclusion and zero
  selected commands for the exhausted current source.
- Focused lint, format, pytest, and dry-run checker gates pass.

## Result

Implemented.

The Phase92 dry-run at
`output/debug-phase92-covered-proof-memory-dry-run/` consumed the Phase89
broader source and Phase90 prior bundle. It selected zero commands:

- `proof_008` was excluded as `prior_planner_proof_covered`;
- nine remaining requests were excluded as `grasp_feasibility` blocked;
- fallback status was `exhausted`;
- Prior Proof Evidence rendered the Phase90 planner-view images for the
  passing proof.

The next coverage-expansion slice should rotate to a different broader cleanup
source artifact.
