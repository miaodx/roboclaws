# 0122. Render Proof Execution Horizon In Runner Reports

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0118 and ADR-0119 made proof strength explicit after execution, and
ADR-0120 made prior-covered selection respect the requested coverage horizon.
The remaining gap was pre-execution visibility: a proof-bundle runner could
reselect a one-step prior proof for a stricter horizon, but the runner report
did not show whether the new commands were actually requesting enough executed
steps to satisfy that horizon.

## Decision

Proof-bundle runner manifests now include a `proof_execution_horizon` block.
It records:

- generated command step count;
- command quality target (`one_step_motion` or `multi_step_motion`);
- prior-covered minimum executed-step horizon;
- prior-covered quality floor; and
- blocker rows when command steps are lower than the coverage horizon.

Runner reports render this as `Proof Execution Horizon` before proof request
selection. The runner checker can require the section with
`--require-proof-execution-horizon`.

## Consequences

- Reviewers can see the intended proof-strength target before local proof
  execution.
- A dry-run report now exposes misconfigured stronger proof attempts where
  selection asks for a higher horizon than commands will execute.
- Post-execution proof quality remains authoritative; the horizon is intent and
  configuration evidence, not proof success.

## Evidence

Implemented in Phase 131 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_excludes_prior_covered_requests tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_reports_misaligned_proof_execution_horizon tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_can_require_proof_execution_horizon`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase131-proof-execution-horizon-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase131-proof-execution-horizon-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1`
