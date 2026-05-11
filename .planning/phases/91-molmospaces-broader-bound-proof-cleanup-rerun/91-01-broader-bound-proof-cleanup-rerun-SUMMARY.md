# Phase 91 Summary: MolmoSpaces Broader Bound Proof Cleanup Rerun

Completed: 2026-05-11
Backfilled: 2026-05-11
Source plan: `91-01-broader-bound-proof-cleanup-rerun-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Rerun ADR-0003 cleanup with the Phase90 passing broader bound proof and verify
partial planner-backed cleanup primitive use in the final cleanup artifact.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

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

[Backfill note: source section truncated; see the phase PLAN for full embedded evidence.]

## Evidence

See the source phase plan and git history for embedded verification evidence.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
