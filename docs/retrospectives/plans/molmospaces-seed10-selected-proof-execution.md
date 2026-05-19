# MolmoSpaces Seed 10 Selected Proof Execution

**Status:** Completed under GSD Phase 102 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0093, Phase 101 selected proof commands
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 101 showed that seed 10 can produce five selected proof commands after
prior-memory filtering, but dry-run selection does not prove planner-backed
coverage. The selected commands needed local execution before any cleanup rerun
or coverage claim.

## Decision

Execute the Phase 101 selected seed 10 commands through the proof-bundle runner
with RBY1M/CuRobo warmup, local runtime preflight, the low-memory CuRobo
profile, and the wide task-sampler robot-placement profile.

## Non-Goals

- Do not rerun cleanup unless proof execution produces promoted cleanup
  binding.
- Do not change selection logic or proof-runner report code.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- The proof-bundle runner manifest validates with required proof outputs.
- The manifest records execution attempted for all selected commands.
- The phase records planner-backed count, cleanup-binding promotion count, and
  blocker classification.
- If all selected proofs block, the phase documents why no cleanup rerun is
  justified.

## Result

Complete on 2026-05-10.

Evidence:

- Executed bundle: `output/debug-phase102-seed10-selected-proof-execution/proof_bundle_run_manifest.json`
- Runner report: `output/debug-phase102-seed10-selected-proof-execution/report.html`
- Warmup artifact: `output/debug-phase102-seed10-selected-proof-execution/rby1m_curobo_warmup/run_result.json`

Observed results:

- status: `probes_executed`
- selected commands: 5
- execution attempted: 5
- planner-backed count: 0
- cleanup-binding-promoted count: 0
- blocked count: 5
- task-feasibility-blocked count: 5
- grasp-feasibility-blocked count: 5
- timeout count: 0
- proof view artifact count: 5

Per-proof outcome:

| Request | Cleanup object | Target | Outcome |
| --- | --- | --- | --- |
| `proof_001` | `observed_001` | `refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2` | `grasp_feasibility` blocked |
| `proof_003` | `observed_003` | `refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2` | `grasp_feasibility` blocked |
| `proof_005` | `observed_005` | `sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_5` | `grasp_feasibility` blocked |
| `proof_008` | `observed_008` | `stand_6bc09b7e2670723819cfaf03855284c1_1_0_3` | `grasp_feasibility` blocked |
| `proof_010` | `observed_010` | `bed_8f5567bbd792fad0b4ee3c2ca65e25b0_1_0_6` | `grasp_feasibility` blocked |

Each proof recorded 17 grasp failures, 15 candidate-removal calls, and one
diagnostic view artifact. No cleanup rerun is justified because no selected
proof promoted cleanup binding.

Verification:

- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase102-seed10-selected-proof-execution/proof_bundle_run_manifest.json --min-selected-requests 0 --require-proof-outputs`
