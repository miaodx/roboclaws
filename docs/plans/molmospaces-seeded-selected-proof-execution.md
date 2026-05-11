# MolmoSpaces Seeded Selected Proof Execution

**Status:** Completed under GSD Phase 95 on 2026-05-10
**Created:** 2026-05-10
**Source:** `CONTEXT.md`, ADR-0003, ADR-0085, Phase94 selected proof dry run
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 94 fixed source-pool rotation and proof-memory identity, but it stopped at
a dry-run manifest. The broader CONTEXT plan still needs real RBY1M/CuRobo proof
execution for the four selected seed 9 requests before any new planner-backed
cleanup rerun can be justified.

## Decision

Execute only the four selected proof commands from the patched seed 9 source
artifact:

- `proof_003`
- `proof_005`
- `proof_006`
- `proof_010`

Use the existing proof-bundle runner with warmup, low RBY1M CuRobo memory
profile, and wide task-sampler placement profile. Keep final cleanup rerun out
of scope for this phase.

## Non-Goals

- Do not change generated-mess selection or proof-selection identity again.
- Do not rerun ADR-0003 cleanup with newly passing proofs in this slice.
- Do not commit ignored `output/` artifacts.
- Do not claim planner-backed bridge completion unless execution evidence
  proves it.

## Acceptance Criteria

- The proof-bundle runner executes the selected four commands.
- The runner manifest and report exist and render the same visual proof views
  as prior proof bundles.
- The checker accepts the manifest.
- Any passing proofs are counted and named; any blockers are classified with
  report evidence.
- Focused lint/pytest/doc checks pass for any tracked changes.

## Result

Complete on 2026-05-10.

The proof-bundle runner executed all four selected commands and wrote:

`output/debug-phase95-seeded-selected-proof-execution/proof_bundle_run_manifest.json`

Result summary:

- `command_count=4`
- `result_count=4`
- `planner_backed_count=0`
- `task_feasibility_blocked_count=4`
- all four selected proofs are `grasp_feasibility` blocked with
  `17 grasp failures; 15 candidate-removal calls`

The runner report renders Proof Request Selection, Prior Proof Evidence, and
Proof Probe Results. Each selected proof also has a local `run_result.json` and
`report.html`.

Verification:

- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase95-seeded-selected-proof-execution/proof_bundle_run_manifest.json --min-selected-requests 1`
