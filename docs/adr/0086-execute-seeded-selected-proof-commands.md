# 0086. Execute Seeded Selected Proof Commands

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0085 made MolmoSpaces source-pool rotation real by tying generated-mess
object selection to the subprocess seed and by preventing local
`proof_###`/`observed_###` identity collisions from hiding new planner objects.

The patched seed 9 source artifact validates as a full ADR-0003 cleanup run
with 10 ready proof requests and the canonical visual report surface. Its
prior-aware dry run selects four exact-scene proof commands:

- `proof_003`: lettuce to refrigerator, including `open_receptacle` and
  `place_inside`;
- `proof_005`: plate to sink;
- `proof_006`: pillow to bed;
- `proof_010`: pillow to bed.

Those commands are the next smallest step toward replacing more ADR-0003
cleanup subphases with strict planner-backed primitive evidence. Running them
is local-dev work because it depends on MolmoSpaces, RBY1M, CuRobo, renderer
device access, and the existing warmup/placement-profile gates.

## Decision

Execute the four selected proof commands as a proof-bundle run against the
patched seed 9 source artifact.

Keep this phase limited to proof execution and report validation. Do not rerun
the final cleanup artifact with any newly passing proofs in the same slice; if
one or more proofs pass and promote cleanup binding, consume them in a separate
cleanup-rerun phase so report changes remain reviewable.

Use the same runner architecture as prior proof bundles:

- source: `output/debug-phase94-seeded-source-candidate-seed9/run_result.json`;
- prior memory: `output/debug-phase90-broader-selected-proof-execution/proof_bundle_run_manifest.json`;
- selection flags: exclude prior task-feasibility blockers and prior covered
  proofs, with fallback generation enabled;
- execution flags: RBY1M, execute mode, one step, low CuRobo memory profile,
  wide robot-placement profile, warmup enabled.

## Consequences

- The proof-bundle runner report remains the visual review surface for all four
  attempts, including initial/final planner views, status, blockers, and task
  feasibility classification.
- If a command succeeds, the proof result becomes prior evidence for a later
  cleanup rerun.
- If all commands remain blocked, the blocker classification advances the
  broader CONTEXT plan without pretending the cleanup bridge is solved.
- Ignored `output/` artifacts remain local evidence and are not committed.

## Evidence

Phase 95 executed the four selected seed 9 proof commands at:

`output/debug-phase95-seeded-selected-proof-execution/proof_bundle_run_manifest.json`

The runner manifest and report validate, and each selected proof produced its
own `run_result.json` and `report.html`.

Outcome:

- `proof_003`: `blocked_capability`, `grasp_feasibility`;
- `proof_005`: `blocked_capability`, `grasp_feasibility`;
- `proof_006`: `blocked_capability`, `grasp_feasibility`;
- `proof_010`: `blocked_capability`, `grasp_feasibility`.

All four reached task sampling with the wide placement profile applied. Each
then failed with `17 grasp failures; 15 candidate-removal calls`, leaving
`planner_backed_count=0` and `cleanup_binding_promoted=0`.

Verification on 2026-05-10:

- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase94-seeded-source-candidate-seed9/run_result.json --output-dir output/debug-phase95-seeded-selected-proof-execution --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --warmup-rby1m-curobo --prior-proof-bundle-manifest output/debug-phase90-broader-selected-proof-execution/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --exclude-prior-covered --generate-fallback-requests --fallback-alias-limit 4 --execute-probes`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase95-seeded-selected-proof-execution/proof_bundle_run_manifest.json --min-selected-requests 1`
