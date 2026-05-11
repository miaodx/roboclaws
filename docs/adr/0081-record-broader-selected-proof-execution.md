# 0081. Record Broader Selected Proof Execution

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0080 let a broader ADR-0003 cleanup artifact contribute new exact-scene
proof requests without retrying known blocked internal planner object/target
pairs. The Phase89 dry-run selected eight candidates from the broader source
artifact and excluded the two known grasp-infeasible internal pairs.

Selection is not proof. The selected requests still needed local RBY1M/CuRobo
execution evidence to determine whether any candidate could produce a strict
planner-backed manipulation proof, promote cleanup primitive binding, and
record planner views.

## Decision

Execute the selected broader proof requests as a local-dev proof-bundle runner
artifact before attempting a cleanup rerun.

The execution uses the same shared proof-bundle runner path with:

- the Phase89 broader source artifact;
- carried prior blocker evidence from the Phase88 manifest;
- `--warmup-rby1m-curobo`;
- `--task-sampler-robot-placement-profile wide`;
- `--execute-probes`;
- checker validation with `--require-proof-outputs`.

The runner report remains the review surface for proof request selection, prior
proof evidence, warmup, exact probe commands, proof result summaries, and
planner-view images. Bundle-level proof result images now share the report
asset-path policy: manifest fields keep their trace paths, while HTML image
sources are rendered relative to the runner report directory so generated
reports remain portable when opened directly from `output/`.

## Consequences

- One broader candidate, `proof_008` (`observed_008` remote-control to stand),
  is now a strict `planner_backed` RBY1M/CuRobo proof.
- `proof_008` promoted cleanup primitive binding for
  `navigate_to_object`, `navigate_to_receptacle`, `pick`, and `place`.
- `proof_008` recorded initial and final planner head-camera views.
- The shared runner report now renders proof-result view `src` values as
  report-relative paths, closing a multi-implementation visual-report gap
  between standalone proof reports and bundle runner reports.
- The other seven selected candidates are classified as
  `grasp_feasibility` blocked with `17 grasp failures; 15 candidate-removal
  calls`.
- This still does not prove full planner-backed cleanup readiness. The next
  slice should rerun cleanup with the passing proof bundle and verify whether
  the final cleanup artifact can use the bound proof for the matching
  observed-handle/target subphases while leaving unmatched objects honest.

## Evidence

Phase 90 validates broader selected proof execution with:

- executed proof-bundle output at
  `output/debug-phase90-broader-selected-proof-execution/`;
- runner status `probes_executed`;
- 8 proof outputs and a checker pass with `--require-proof-outputs`;
- bundle summary of 1 `planner_backed` proof and 7 `blocked_capability`
  proofs;
- `proof_008` planner views at
  `proofs/007_observed_008_to_stand_6bc09b7e2670723819cfaf03855284c1_1_0_3/planner_views/`;
- `proof_008` cleanup binding promotion and sampled task match for
  `remotecontrol_488ea7924f7cb4d329c991926df62222_1_0_3` to
  `stand_6bc09b7e2670723819cfaf03855284c1_1_0_3`.
- runner report image sources such as
  `proofs/007_observed_008_to_stand_6bc09b7e2670723819cfaf03855284c1_1_0_3/planner_views/initial_head_camera.png`.

Verification on 2026-05-10:

- `uv --version && uv pip install -e ".[dev]" || python -m pip install -e ".[dev]"`
- `.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase89-broader-candidate-source/run_result.json --output-dir output/debug-phase90-broader-selected-proof-execution --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --task-sampler-robot-placement-profile wide --warmup-rby1m-curobo --execute-probes --prior-proof-bundle-manifest output/debug-phase88-nested-prior-carry-forward-dry-run/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 4`
- `uv run ruff check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase90-broader-selected-proof-execution/proof_bundle_run_manifest.json --require-proof-outputs`
