# Phase 89 Plan: MolmoSpaces Planner-Object Proof Selection Memory

## Goal

Use broader ADR-0003 cleanup artifacts as new proof-request sources while
preserving prior blocker memory for internal planner object/target pairs.

## Tasks

1. Produce a broader exact-scene cleanup source artifact with more generated
   mess objects and proof requests.
2. Guard proof-selection request-ID matches so IDs remain local to their source
   manifest unless the cleanup or planner pair also matches.
3. Add planner-object/public-target prior memory to filter known internal
   grasp-infeasible pairs that reappear under different observed handles.
4. Add regression coverage for request-ID collision and planner-object prior
   matching.
5. Validate a dry-run that selects new broader candidates while filtering known
   blocked internal pairs.
6. Record the result in ADR, plan, CONTEXT, ROADMAP, and STATE.

## Acceptance Checks

- The broader source artifact has 10 ready proof requests and robot-view
  evidence.
- Selection keeps genuinely new requests even when their local proof IDs
  collide with prior manifests.
- Selection excludes the known book/shelf and bowl/sink internal planner pairs
  by `planner_object_target` match.
- Focused ruff checks pass for changed selector/test files.
- Focused format checks pass for changed selector/test files.
- Focused pytest passes for proof-request selection tests.
- The Phase89 dry-run manifest passes the proof-bundle runner checker.

## Result

Implemented.

The proof request selector now treats request IDs as manifest-local unless
their public cleanup pair or planner-object/public-target pair also matches.
It also carries a private planner-object/public-target index for prior results,
so changed public observed handles do not reopen known internal blocked pairs.

The broader source artifact at
`output/debug-phase89-broader-candidate-source/` emitted 10 ready proof
requests and 176 robot-view images. The post-fix dry-run at
`output/debug-phase89-planner-pair-selection-dry-run/` selected 8 new proof
commands while excluding only the two known `grasp_feasibility` blocked
internal planner object/target pairs.

Focused validation passed:

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase89-broader-candidate-source/run_result.json`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase89-planner-pair-selection-dry-run/proof_bundle_run_manifest.json`

## Status

Complete.
