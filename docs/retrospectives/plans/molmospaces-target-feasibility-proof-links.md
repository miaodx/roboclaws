# MolmoSpaces Target Feasibility Proof Links

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0065-preserve-target-feasibility-proof-links.md`
**GSD phase:** `.planning/milestones/v1.98-phases/74-molmospaces-target-feasibility-proof-links/`

## Problem

Phase 73 narrowed the current fallback blocker to target-side task feasibility,
but the report still made reviewers hunt through older output directories to
find which proof established each filtered pair.

There is also a merge hazard: fallback request IDs are generated per run, so
the same ID can refer to different planner aliases in different prior
manifests.

## Scope

- Preserve distinct prior fallback attempts by merging fallback results on
  request ID plus planner object/target aliases.
- Enrich `prior_task_feasibility_blocked_pair` rows with proof artifact paths,
  prior status, task-feasibility status, worker stage, and execution-attempted
  state.
- Render those fields in the proof-bundle runner report.
- Validate report text for pair artifact fields when present.
- Dry-run with the executed Phase 65 and Phase 67 prior manifests so the report
  shows the exact target-feasibility proof links.

## Result

The Phase 74 dry-run reports two target-feasibility blocked pairs. Both rows
now include the prior Phase 65 proof report path and `worker_exception` stage,
while preserving the existing blocker classification:

- `target_task_feasibility_blocked_pairs`
- `no_fallback_candidate_available`

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase74-target-feasibility-proof-links-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase65-discovered-runtime-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase67-filtered-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 4`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase74-target-feasibility-proof-links-dry-run`
