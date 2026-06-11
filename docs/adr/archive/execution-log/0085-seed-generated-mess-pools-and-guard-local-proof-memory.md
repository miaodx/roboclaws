# 0085. Seed Generated Mess Pools and Guard Local Proof Memory

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0080 made proof-selection memory aware of internal planner objects so a
broader cleanup source artifact could avoid retrying known blocked planner
object/target pairs. ADR-0083 then added prior-covered filtering so the already
passing `proof_008` remote-control proof is not rerun.

After ADR-0084 repaired stale report rendering through the shared underlay, the
next broader-source rotation exposed two remaining identity gaps:

- the MolmoSpaces subprocess worker accepted `--seed`, but generated-mess
  target selection always chose the first eligible objects by semantic rule, so
  seeds 7, 8, and 9 produced different scenario IDs with the same internal
  proof pool;
- once generated-mess selection was made seed-aware, prior proof selection still
  let matching local `request_id` plus local `observed_*`/target pairs exclude
  a new planner object, because those public IDs are regenerated per cleanup
  artifact.

That made the architecture look rotated while still reusing stale proof-memory
identity. It also left the next exact-scene proof slice with zero commands even
when the source artifact contained genuinely new planner objects.

## Decision

Make the MolmoSpaces Generated Mess Set seed own source-pool diversity.

`select_generated_mess_targets(..., seed=...)` now deterministically shuffles
eligible objects inside each semantic cleanup rule before selecting the hidden
mess set. Target receptacle priority stays stable: dishes still route to sink,
books to shelving, food to fridge, remotes to TV stand, and pillows to bed. This
keeps ADR-0003 public target inference comparable and avoids leaking private
target truth to Agent View.

The MolmoSpaces subprocess worker passes its run seed into that selector.

Tighten proof-selection memory at the same boundary: request-ID and public
cleanup-pair prior matches are rejected when both the current request and prior
result expose complete planner object/public-target identity and those planner
pairs differ. The dedicated planner-object/public-target matcher remains the
way to carry forward known blockers across regenerated public handles.

## Consequences

- Rotating `--seed` on a fixed MolmoSpaces scene now changes the generated
  object pool instead of only changing metadata.
- Local `proof_###` and `observed_###` IDs cannot hide new planner objects when
  private planner binding evidence is available.
- The report and runner architecture stay unified: source cleanup artifacts,
  proof request selection, proof bundle reports, and regenerated cleanup reports
  all continue through the existing shared modules.
- The next phase can execute the newly selected broader proof commands instead
  of retrying the exhausted Phase90 pool.

## Evidence

Phase 94 validates the decision with:

- unit coverage for same-seed deterministic target selection and cross-seed
  source-pool diversity;
- unit coverage that same local `request_id` plus same local `observed_*`/target
  does not exclude a request when the planner object changed;
- a patched seed 9 cleanup artifact at
  `output/debug-phase94-seeded-source-candidate-seed9/` with 10 generated
  objects, 44 robot timeline steps, and new planner objects including mug,
  plate, lettuce, and new pillow IDs;
- a prior-aware proof-bundle dry run at
  `output/debug-phase94-seeded-source-candidate-selection-dry-run-after-id-fix/`
  selecting 4 commands (`proof_003`, `proof_005`, `proof_006`, `proof_010`)
  while excluding 5 known grasp-feasibility blockers and 1 prior-covered proof.

Verification on 2026-05-10:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/generated_mess.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/molmospaces_subprocess_worker.py tests/test_molmo_cleanup_subprocess_backend.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_subprocess_backend.py::test_worker_select_targets_uses_seed_for_source_pool_diversity tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_ignores_local_ids_when_planner_object_differs tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_ignores_colliding_request_id_for_different_pair tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_matches_prior_result_by_planner_object_target`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase94-seeded-source-candidate-seed9/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase94-seeded-source-candidate-selection-dry-run-after-id-fix/proof_bundle_run_manifest.json --min-selected-requests 1`
