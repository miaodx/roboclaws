# Phase 95-01: Seeded Selected Proof Execution

## Goal

Execute the four proof commands selected from the patched seed 9 MolmoSpaces
source artifact and record whether any produce strict planner-backed cleanup
primitive evidence.

## Tasks

- Run `scripts/run_molmo_planner_proof_bundle_from_requests.py` with
  `--execute-probes` against
  `output/debug-phase94-seeded-source-candidate-seed9/run_result.json`.
- Preserve Phase90 prior memory and Phase94 selection flags.
- Use RBY1M execute mode, low CuRobo memory profile, wide placement profile,
  renderer device 0, and warmup.
- Validate the resulting manifest/report with the proof-bundle checker.
- Update ADR, plan, CONTEXT, and planning state with the actual outcome.

## Acceptance

- The executed proof-bundle manifest exists under
  `output/debug-phase95-seeded-selected-proof-execution/`.
- The manifest records four executed selected commands or records a concrete
  execution blocker.
- The runner report renders proof result evidence for review.
- The checker accepts the manifest.
- The phase is committed with docs and any needed code/test changes.

## Result

Complete on 2026-05-10.

The executed proof-bundle manifest is:

`output/debug-phase95-seeded-selected-proof-execution/proof_bundle_run_manifest.json`

Execution result:

- `proof_003`: blocked as `grasp_feasibility`;
- `proof_005`: blocked as `grasp_feasibility`;
- `proof_006`: blocked as `grasp_feasibility`;
- `proof_010`: blocked as `grasp_feasibility`.

The bundle checker accepts the manifest, and the runner report renders proof
selection, prior proof evidence, and proof result evidence. No newly selected
proof became planner-backed, so a cleanup rerun would not add planner-backed
primitive coverage yet.

Verification:

- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase95-seeded-selected-proof-execution/proof_bundle_run_manifest.json --min-selected-requests 1`
