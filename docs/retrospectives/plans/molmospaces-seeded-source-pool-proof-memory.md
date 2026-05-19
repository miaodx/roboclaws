# MolmoSpaces Seeded Source Pool and Proof Memory

**Status:** Completed under GSD Phase 94 on 2026-05-10
**Created:** 2026-05-10
**Source:** `CONTEXT.md`, ADR-0003, ADR-0080, ADR-0083, ADR-0084, Phase93
seed-rotation evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

After the cleanup report adapter made stale reports reuse the shared underlay,
the next broader-source rotation still selected zero proof commands. Local seed
8 and seed 9 runs validated as full ADR-0003 artifacts, but they produced the
same planner object/target identities as the Phase90 source pool.

There were two causes:

- generated-mess target selection did not use the MolmoSpaces subprocess seed;
- proof-selection memory could still treat local `request_id` and local
  `observed_*` handles as enough identity even when planner object evidence
  showed the current request was different.

## Decision

Make `--seed` deterministic source-pool identity for generated mess objects and
guard public/local proof-memory matches with planner-object identity.

This phase:

- passes the subprocess seed into generated-mess target selection;
- shuffles eligible objects within each semantic cleanup rule while preserving
  stable target fixture semantics;
- rejects request-ID and cleanup-pair prior matches when current and prior
  planner object/public-target pairs are both complete and different;
- records the local seeded artifact and dry-run selection evidence.

## Non-Goals

- Do not execute the newly selected proof commands in this slice.
- Do not randomize target fixture semantics, since that would change the public
  ADR-0003 target inference contract.
- Do not change report rendering, private scoring, or Agent View exposure.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- Same seed produces the same generated-mess object pool; different seeds can
  produce different object identities on the same fixed scene.
- A same local `request_id`/`observed_*`/target match does not exclude a current
  proof request when the planner object differs from prior evidence.
- A real patched seed 9 MolmoSpaces cleanup artifact validates with 10 generated
  objects and robot views.
- Prior-aware proof selection against Phase90 evidence produces nonzero selected
  commands from the patched seed 9 artifact.
- Focused lint and pytest pass.

## Result

Complete on 2026-05-10.

Key evidence:

- `output/debug-phase94-seeded-source-candidate-seed9/run_result.json` validates
  with `generated_mess_count=10`, `robot_view_step_count=44`, and 10 ready proof
  requests.
- Its proof pool includes new planner objects such as
  `lettuce_6ca27...`, `plate_ac6a...`, `mug_3ebc...`, and new pillow IDs.
- `output/debug-phase94-seeded-source-candidate-selection-dry-run-after-id-fix/proof_bundle_run_manifest.json`
  selects four commands: `proof_003`, `proof_005`, `proof_006`, and
  `proof_010`.
- The remaining exclusions are five prior `grasp_feasibility` blockers and one
  prior-covered `proof_008`.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/generated_mess.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/molmospaces_subprocess_worker.py tests/test_molmo_cleanup_subprocess_backend.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_subprocess_backend.py::test_worker_select_targets_uses_seed_for_source_pool_diversity tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_ignores_local_ids_when_planner_object_differs tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_ignores_colliding_request_id_for_different_pair tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_matches_prior_result_by_planner_object_target`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase94-seeded-source-candidate-seed9/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase94-seeded-source-candidate-selection-dry-run-after-id-fix/proof_bundle_run_manifest.json --min-selected-requests 1`
