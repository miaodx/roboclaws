# 0091. Use Canonical MolmoSpaces Preflight Import

Date: 2026-05-10

## Status

Accepted

## Context

Phase 99 added a proof-bundle local runtime preflight, but the first pass used
the colloquial project name `molmospaces` as the import check. The actual
installed Python package from upstream is `molmo_spaces`, and the local
runtime already imports that canonical package successfully.

Using the wrong import name turns a ready local runtime into false blocked
evidence.

## Decision

Use `import molmo_spaces` as the proof-bundle local runtime preflight check.
Rename the emitted check and blocker codes to `molmo_spaces_import`,
`molmo_spaces_import_failed`, and `molmo_spaces_import_timeout`.

Keep the report section and manifest field from Phase 99. This phase corrects
the package identity, not the local-dev handoff architecture.

## Consequences

- The local runtime preflight matches the upstream package layout.
- Existing report/checker behavior remains intact.
- A local ready preflight can be recorded without running any proof commands
  when selection produces zero commands.

## Evidence

Implemented in Phase 100 on 2026-05-10.

Verification:

- `/tmp/roboclaws-molmospaces-spike/.venv/bin/python -c "import molmo_spaces; print('molmo_spaces import ok')"`
- `.venv/bin/ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase94-seeded-source-candidate-seed9/run_result.json --output-dir output/debug-phase100-local-runtime-preflight-ready --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 600 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --prior-proof-bundle-manifest output/debug-phase95-seeded-selected-proof-execution/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --exclude-prior-covered --generate-fallback-requests --execute-probes`
