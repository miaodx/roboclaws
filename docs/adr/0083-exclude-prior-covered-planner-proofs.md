# 0083. Exclude Prior Covered Planner Proofs

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0082 proved that the Phase90 `proof_008` artifact can drive one final
cleanup object through strict planner-backed subphases. The next broader proof
coverage work must not retry that solved object, but the proof-bundle selector
previously excluded only prior `task_feasibility_status=blocked` requests.

That left a bad local-dev failure mode: a later broader dry-run could select a
request that already had `planner_backed` proof and promoted cleanup binding,
spending another RBY1M/CuRobo execution on coverage we already had.

## Decision

Add an explicit `--exclude-prior-covered` selector mode for proof-bundle
generation. A prior result counts as covered only when it is both:

- `planner_backed=true`;
- `cleanup_binding_promoted=true`.

Covered requests are excluded with reason `prior_planner_proof_covered`. They
are not treated as task-feasibility blockers and do not generate fallback
commands.

The runner checker can now require this state with
`--require-prior-covered-exclusion` and can bound selected request counts with
`--min-selected-requests` / `--max-selected-requests`.

## Consequences

- Proof selection memory now distinguishes three states: ready-to-run,
  infeasible, and already-covered.
- The current broader seed is explicitly exhausted under prior memory:
  Phase92 dry-run selected zero commands, excluded `proof_008` as covered, and
  excluded the remaining nine requests as `grasp_feasibility` blocked.
- The next coverage-expansion slice should rotate to a new broader source
  cleanup artifact rather than retrying the Phase89/90/91 seed.
- Runner reports now show a `Covered` metric in Proof Request Selection and
  render `prior_planner_proof_covered` in the excluded request table.

## Evidence

Phase 92 validates prior covered-proof exclusion with:

- dry-run artifact at
  `output/debug-phase92-covered-proof-memory-dry-run/`;
- `proof_request_count=10`, `ready_request_count=10`, `command_count=0`;
- selection mode
  `exclude_task_feasibility_blocked_and_prior_covered_with_fallbacks`;
- `covered_request_count=1` for `proof_008`;
- `grasp_feasibility_blocker_count=9`;
- `fallback_generation.status=exhausted`;
- runner report rendering Prior Proof Evidence, including the `proof_008`
  initial/final planner views from Phase90.

Verification on 2026-05-10:

- `uv --version && uv pip install -e ".[dev]" || python -m pip install -e ".[dev]"`
- `.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase89-broader-candidate-source/run_result.json --output-dir output/debug-phase92-covered-proof-memory-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --warmup-rby1m-curobo --prior-proof-bundle-manifest output/debug-phase90-broader-selected-proof-execution/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --exclude-prior-covered --generate-fallback-requests --fallback-alias-limit 4`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase92-covered-proof-memory-dry-run/proof_bundle_run_manifest.json --max-selected-requests 0 --require-prior-covered-exclusion`
- `uv run ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
