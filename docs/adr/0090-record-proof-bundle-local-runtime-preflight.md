# 0090. Record Proof-Bundle Local Runtime Preflight

Date: 2026-05-10

## Status

Accepted

## Context

The broader MolmoSpaces plan is ready to rotate proof sources or reduce the
shared RBY1M grasp-feasibility blocker, but real proof execution is a local-dev
operation. The configured default MolmoSpaces Python path can exist while the
canonical `molmo_spaces` package import is unavailable, which causes execution
attempts to fail before the proof-bundle runner writes a reviewable
manifest/report.

That makes the next local action ambiguous: did selection fail, did RBY1M/CuRobo
fail, or is the local Python runtime not ready?

## Decision

Add a proof-bundle local runtime preflight before executing real proof commands.
When `--execute-probes` is requested, the runner checks whether the configured
MolmoSpaces Python can import the canonical package, `molmo_spaces`.

If the check fails:

- the runner writes the normal proof-bundle manifest and report;
- status becomes `local_runtime_blocked`;
- proof commands and warmup commands are not executed;
- the report renders a `Local Runtime Preflight` panel with the Python path,
  command, return code, and blocker.

Dry-run command generation remains unchanged.

## Consequences

- Missing or stale local MolmoSpaces runtimes become first-class evidence
  instead of an exception before artifact creation.
- Local proof execution still requires a real working MolmoSpaces Python;
  this phase does not install or repair that environment.
- The proof-bundle checker accepts `local_runtime_blocked` only when the
  preflight evidence is present.

## Evidence

Implemented in Phase 99 on 2026-05-10.

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase94-seeded-source-candidate-seed9/run_result.json --output-dir output/debug-phase99-local-runtime-preflight-blocked --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 600 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --prior-proof-bundle-manifest output/debug-phase95-seeded-selected-proof-execution/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --exclude-prior-covered --generate-fallback-requests --execute-probes`
