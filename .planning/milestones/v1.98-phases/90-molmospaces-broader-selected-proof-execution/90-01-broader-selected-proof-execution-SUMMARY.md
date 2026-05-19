# Phase 90 Summary: MolmoSpaces Broader Selected Proof Execution

Completed: 2026-05-11
Backfilled: 2026-05-11
Source plan: `90-01-broader-selected-proof-execution-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Execute the broader exact-scene proof candidates selected by Phase89 and record
whether any candidate is strict planner-backed cleanup primitive evidence.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

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

## Evidence

See the source phase plan and git history for embedded verification evidence.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
