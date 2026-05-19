# MolmoSpaces Broader Selected Proof Execution

**Status:** Completed for Phase 90 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/0081-record-broader-selected-proof-execution.md`

## Goal

Execute the eight broader exact-scene proof candidates selected in Phase89 and
record which, if any, become strict planner-backed cleanup primitive evidence.

## Problem

Phase89 selected eight new candidates from a broader cleanup artifact while
filtering known internal blocked pairs. Those selected commands were only
candidate handoff evidence. The broader path still needed real RBY1M/CuRobo
execution to classify each candidate and determine whether any proof could
promote cleanup binding.

## Scope

- Run the proof-bundle runner against
  `output/debug-phase89-broader-candidate-source/run_result.json`.
- Use Phase88 carried prior evidence to keep known internal blocked pairs
  excluded.
- Enable RBY1M/CuRobo warmup, the wide task-sampler robot-placement profile,
  and `--execute-probes`.
- Validate the executed manifest with `--require-proof-outputs`.
- Record the per-proof result summary, planner views, and next blocker.
- Keep bundle-runner proof-result view images on the shared report path
  architecture: manifest paths remain traceable, and HTML image sources resolve
  relative to the runner report.

## Non-Goals

- Do not rerun final cleanup in this slice.
- Do not claim full planner-backed cleanup readiness from one passing proof.
- Do not expose planner aliases to Agent View.
- Do not commit generated output artifacts.

## Acceptance Criteria

- The runner executes all eight selected broader proof candidates.
- The executed runner manifest passes the checker with required proof outputs.
- The report renders proof selection, prior evidence, warmup, commands, proof
  results, and planner views for any passing proof.
- Any passing proof records cleanup binding promotion.
- Any blocked proof records an explicit task-feasibility blocker.

## Result

Implemented.

The executed bundle at
`output/debug-phase90-broader-selected-proof-execution/` ran all eight selected
broader candidates. Seven candidates are still `grasp_feasibility` blocked with
`17 grasp failures; 15 candidate-removal calls`.

`proof_008` succeeded as a strict `planner_backed` proof for
`observed_008` / `stand_6bc09b7e2670723819cfaf03855284c1_1_0_3`. It promoted
cleanup primitive binding for `navigate_to_object`, `navigate_to_receptacle`,
`pick`, and `place`, matched the sampled upstream task, and recorded initial
and final planner head-camera views. The runner report now renders those
planner-view image sources as report-relative `proofs/.../planner_views/...`
paths, matching the standalone proof report visual behavior.

Verification:

- Dependency preflight passed with `uv pip install -e ".[dev]"`.
- AI2-THOR import preflight passed.
- The Phase90 proof-bundle execution completed with `status=probes_executed`.
- The executed manifest passed
  `scripts/check_molmo_planner_proof_bundle_runner_result.py` with
  `--require-proof-outputs`.
- Focused report renderer/checker lint, format, and pytest coverage passed for
  the report-relative proof-result image path fix.
