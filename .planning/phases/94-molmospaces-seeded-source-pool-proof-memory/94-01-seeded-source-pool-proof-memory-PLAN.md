# Phase 94-01: Seeded Source Pool and Proof Memory

## Goal

Make broader MolmoSpaces source-pool rotation real by tying generated-mess
object selection to the run seed and preventing local proof IDs from excluding
new planner objects.

## Tasks

- Thread the MolmoSpaces subprocess seed into generated-mess target selection.
- Keep target fixture preference stable while shuffling eligible objects inside
  each semantic cleanup rule.
- Tighten proof-selection prior matching so local `proof_###` and
  `observed_###` collisions do not override conflicting planner-object identity.
- Add focused regression tests for seeded source diversity and local-ID proof
  memory collisions.
- Validate a patched seed 9 cleanup artifact and prior-aware proof-selection dry
  run against Phase90 evidence.

## Acceptance

- Seeded generated-mess selection is deterministic for the same seed and can
  differ across seeds.
- Same local public IDs with different planner objects remain selectable.
- The patched seed 9 cleanup artifact passes the real cleanup checker.
- The patched seed 9 proof-bundle dry run selects at least one command.
- Focused lint and pytest pass.

## Result

Complete on 2026-05-10.

Evidence:

- `output/debug-phase94-seeded-source-candidate-seed9/run_result.json`:
  10 generated objects, 44 robot-view steps, 10 ready proof requests.
- `output/debug-phase94-seeded-source-candidate-selection-dry-run-after-id-fix/proof_bundle_run_manifest.json`:
  4 selected proof commands and 6 excluded prior-memory results.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/generated_mess.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/molmospaces_subprocess_worker.py tests/test_molmo_cleanup_subprocess_backend.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_subprocess_backend.py::test_worker_select_targets_uses_seed_for_source_pool_diversity tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_ignores_local_ids_when_planner_object_differs tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_ignores_colliding_request_id_for_different_pair tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_matches_prior_result_by_planner_object_target`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase94-seeded-source-candidate-seed9/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase94-seeded-source-candidate-selection-dry-run-after-id-fix/proof_bundle_run_manifest.json --min-selected-requests 1`
