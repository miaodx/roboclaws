# Phase 90 Plan: MolmoSpaces Broader Selected Proof Execution

## Goal

Execute the broader exact-scene proof candidates selected by Phase89 and record
whether any candidate is strict planner-backed cleanup primitive evidence.

## Tasks

1. Run environment preflight for editable dev dependencies and AI2-THOR import.
2. Execute the Phase89 selected proof bundle with Phase88 prior evidence,
   RBY1M/CuRobo warmup, the wide task-sampler robot-placement profile, and
   `--execute-probes`.
3. Validate the executed runner manifest with `--require-proof-outputs`.
4. Inspect the proof result summary for planner-backed status, cleanup binding
   promotion, task-feasibility blockers, and planner views.
5. Reuse the shared report path policy for proof-result view images so runner
   report `src` values resolve from the report directory.
6. Record the result in ADR, plan, CONTEXT, ROADMAP, and STATE.

## Acceptance Checks

- Executed proof-bundle runner artifact exists under
  `output/debug-phase90-broader-selected-proof-execution/`.
- Runner status is `probes_executed`.
- The runner checker passes with `--require-proof-outputs`.
- Proof result summary classifies all eight selected requests.
- Any passing proof has cleanup binding promotion and planner views.
- Runner report proof-result image `src` values are report-relative and checked
  by focused report/checker tests.

## Result

Implemented.

The runner executed all eight selected broader candidates. Seven are
`blocked_capability` with `task_feasibility_blocker_kind=grasp_feasibility`.

`proof_008` is the first broader selected source request to pass as strict
`planner_backed` RBY1M/CuRobo evidence. It promoted cleanup binding for
`observed_008` to
`stand_6bc09b7e2670723819cfaf03855284c1_1_0_3`, matched the sampled upstream
remote-control-to-stand task, executed one policy step, changed robot state,
and recorded initial/final planner head-camera views.

The shared runner report now renders proof-result views as report-relative
`proofs/.../planner_views/...` image sources instead of embedding output-dir
paths that break when the report is opened directly.

Focused validation passed:

- `uv --version && uv pip install -e ".[dev]" || python -m pip install -e ".[dev]"`
- `.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"`
- `uv run ruff check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase90-broader-selected-proof-execution/proof_bundle_run_manifest.json --require-proof-outputs`

## Status

Complete.
