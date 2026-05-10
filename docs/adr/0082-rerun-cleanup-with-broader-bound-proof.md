# 0082. Rerun Cleanup with Broader Bound Proof

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0081 recorded that the broader selected proof bundle produced one strict
RBY1M/CuRobo proof, `proof_008`, for `observed_008` remote-control cleanup to
the TV stand. The proof promoted cleanup primitive binding and recorded planner
views, but it had not yet been consumed by a final ADR-0003 cleanup rerun.

The cleanup bridge must be evaluated on the final cleanup artifact, not only on
the proof bundle. A single passing proof should make only its matching
object/target cleanup subphases planner-backed; unmatched objects must remain
`api_semantic`, and the global bridge must remain blocked until every cleaned
object has matching proof.

## Decision

Rerun cleanup directly with the existing Phase90 `proof_008` run result rather
than re-executing the proof bundle. The cleanup rerun uses the Phase89 broader
source parameters:

- seed `7`;
- `molmospaces_subprocess` backend;
- RBY1M robot inclusion;
- robot-view recording;
- generated mess count `10`;
- `--use-planner-proof-for-cleanup-primitives`;
- the Phase90 `proof_008` run result as the only attached proof.

Add a checker gate for this partial-bound state. The checker must be able to
require:

- a specific cleanup object/target pair to have all cleanup subphases strict
  `planner_backed`;
- mixed primitive evidence, meaning at least one unmatched object remains
  `api_semantic`;
- the global cleanup primitive gate and planner cleanup bridge remain blocked
  until every cleaned object has matching proof.

## Consequences

- `observed_008` to
  `stand_6bc09b7e2670723819cfaf03855284c1_1_0_3` now uses the
  probe-backed cleanup primitive executor for `nav`, `pick`, `nav`, and
  `place` in the final cleanup artifact.
- The final cleanup report renders the shared visual core, 44 robot timeline
  steps, attached planner proof initial/final views, cleanup primitive gate,
  and planner cleanup bridge.
- The cleanup primitive summary is mixed: 4 planner-backed subphases and 38
  `api_semantic` subphases.
- The final cleanup remains globally honest: `primitive_provenance` is still
  `api_semantic`, cleanup primitive gate status is `blocked_capability`, and
  planner cleanup bridge status is `blocked_capability`.
- Full planner-backed cleanup readiness now requires either matching proofs for
  the remaining cleanup objects or a new source candidate pool; the current
  broader seed should not be treated as solved by one bound proof.

## Evidence

Phase 91 validates the broader bound proof cleanup rerun with:

- cleanup rerun artifact at
  `output/debug-phase91-broader-bound-proof-cleanup-rerun/`;
- cleanup status `success`;
- generated mess count `10`;
- 44 robot timeline steps and 176 robot-view images;
- 2 attached planner proof images under `planner_proof/`;
- cleanup primitive summary `planner_backed=4`, `api_semantic=38`;
- `observed_008` strict planner-backed cleanup primitive evidence for
  `navigate_to_object`, `pick`, `navigate_to_receptacle`, and `place`;
- blocked global cleanup primitive gate and blocked planner cleanup bridge.

Verification on 2026-05-10:

- `uv --version && uv pip install -e ".[dev]" || python -m pip install -e ".[dev]"`
- `.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"`
- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/debug-phase91-broader-bound-proof-cleanup-rerun --seed 7 --backend molmospaces_subprocess --fixture-hint-mode room_only --perception-mode visible_object_detections --include-robot --robot-name rby1m --record-robot-views --generated-mess-count 10 --planner-proof-run-result output/debug-phase90-broader-selected-proof-execution/proofs/007_observed_008_to_stand_6bc09b7e2670723819cfaf03855284c1_1_0_3/run_result.json --use-planner-proof-for-cleanup-primitives`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase91-broader-bound-proof-cleanup-rerun/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --require-bound-planner-cleanup-object observed_008:stand_6bc09b7e2670723819cfaf03855284c1_1_0_3 --require-mixed-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge`
- `uv run ruff check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `uv run ruff format --check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_realworld_cleanup_result.py`
