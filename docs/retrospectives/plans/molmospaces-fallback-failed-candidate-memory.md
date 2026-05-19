# MolmoSpaces Fallback Failed Candidate Memory

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0057-remember-failed-fallback-candidates.md`
**GSD phase:** `.planning/milestones/v1.98-phases/66-molmospaces-fallback-failed-candidate-memory/`

## Problem

Phase 65 showed that discovered runtime-sibling fallback commands are executable
but not all useful. Some aliases are non-root bodies, and some object/target
pairs are already task-feasibility blocked. Without candidate memory, the next
fallback generation pass can waste local-dev cycles retrying known-bad commands.

## Scope

- Carry prior discovered runtime aliases forward from a prior proof-bundle
  manifest.
- Detect prior generated fallback proofs that failed because the object alias
  is not a root body.
- Detect prior generated fallback object/target pairs that already failed with
  task-feasibility blockers.
- Filter those aliases and pairs before command generation.
- Render filtered pairs in the proof-bundle runner report and validate them
  through the checker.
- Dry-run the current cleanup artifact using the Phase 65 executed bundle as
  prior evidence.

## Result

The proof-bundle runner now remembers failed generated fallback candidates when
using a prior proof-bundle manifest.

The Phase 66 dry-run against
`output/debug-phase65-discovered-runtime-fallback-execute/proof_bundle_run_manifest.json`
generated two commands instead of retrying all four Phase 65 commands. The
report shows:

- five carried discovered aliases;
- six filtered aliases, including two `prior_non_root_body_alias` rows;
- two filtered pairs with reason `prior_task_feasibility_blocked_pair`;
- two remaining generated commands for the untried book runtime sibling
  `book_be4d759484637aeb579b28e6a954b18d_1_2_8`.

The next local-dev slice is executing those two remaining commands with warmup.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase66-failed-fallback-candidate-memory-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase65-discovered-runtime-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase66-failed-fallback-candidate-memory-dry-run`
