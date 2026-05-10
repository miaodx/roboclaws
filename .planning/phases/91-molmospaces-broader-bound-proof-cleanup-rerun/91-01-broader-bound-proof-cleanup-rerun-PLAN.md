# Phase 91 Plan: MolmoSpaces Broader Bound Proof Cleanup Rerun

## Goal

Rerun ADR-0003 cleanup with the Phase90 passing broader bound proof and verify
partial planner-backed cleanup primitive use in the final cleanup artifact.

## Tasks

1. Add a checker gate for a required bound planner-backed cleanup object and
   for mixed planner/API-semantic primitive evidence.
2. Run environment preflight for editable dev dependencies and AI2-THOR import.
3. Execute `examples/molmospaces_realworld_cleanup.py` with the Phase90
   `proof_008` run result, `--use-planner-proof-for-cleanup-primitives`,
   MolmoSpaces subprocess backend, RBY1M robot inclusion, and robot views.
4. Validate the cleanup rerun with required robot views, planner proof
   attachment, bound object evidence, mixed primitive evidence, and blocked
   bridge honesty.
5. Inspect report visual coverage and result fields.
6. Record the result in ADR, plan, CONTEXT, ROADMAP, and STATE.

## Acceptance Checks

- Focused checker tests pass.
- Cleanup rerun artifact exists under
  `output/debug-phase91-broader-bound-proof-cleanup-rerun/`.
- `observed_008` to
  `stand_6bc09b7e2670723819cfaf03855284c1_1_0_3` is strict
  planner-backed in `cleanup_primitive_evidence`.
- At least one unmatched cleanup object remains `api_semantic`, leaving the
  global cleanup primitive gate and bridge blocked.
- The cleanup report renders shared visual core, robot views, planner proof
  views, cleanup primitive gate, and planner cleanup bridge sections.

## Result

Implemented.

The Phase91 cleanup rerun consumed the existing Phase90 `proof_008` run result
without re-executing the proof bundle. The final artifact lives at
`output/debug-phase91-broader-bound-proof-cleanup-rerun/`.

The rerun completed with `cleanup_status=success`, 10 generated mess objects,
44 robot timeline steps, 176 robot-view images, and attached planner proof
initial/final images under `planner_proof/`.

`observed_008` to
`stand_6bc09b7e2670723819cfaf03855284c1_1_0_3` is strict planner-backed for
the cleanup subphases `nav`, `pick`, `nav`, and `place`. The rest of the run
remains honest: primitive summary is `planner_backed=4` and
`api_semantic=38`, so the global cleanup primitive gate and planner cleanup
bridge both remain `blocked_capability`.

Focused validation passed:

- `uv --version && uv pip install -e ".[dev]" || python -m pip install -e ".[dev]"`
- `.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"`
- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/debug-phase91-broader-bound-proof-cleanup-rerun --seed 7 --backend molmospaces_subprocess --fixture-hint-mode room_only --perception-mode visible_object_detections --include-robot --robot-name rby1m --record-robot-views --generated-mess-count 10 --planner-proof-run-result output/debug-phase90-broader-selected-proof-execution/proofs/007_observed_008_to_stand_6bc09b7e2670723819cfaf03855284c1_1_0_3/run_result.json --use-planner-proof-for-cleanup-primitives`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase91-broader-bound-proof-cleanup-rerun/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --require-bound-planner-cleanup-object observed_008:stand_6bc09b7e2670723819cfaf03855284c1_1_0_3 --require-mixed-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge`
- `uv run ruff check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `uv run ruff format --check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_matching_probe_backed_executor`

## Status

Complete.
