# 0117. Consume Phase 125 Proof In Cleanup Primitive Path

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0116 produced a strict RBY1M/CuRobo planner-backed exact proof for the
`observed_001` to refrigerator cleanup pair. That proof is not enough by itself
to claim full ADR-0003 cleanup replacement: it proves one target-runtime
execution step and carries cleanup primitive binding for one observed handle.

The next architecture question is whether that proof can be consumed by the
ADR-0003 cleanup primitive path without weakening the global bridge. The target
is an inside placement, so the bound cleanup object uses
`nav -> pick -> nav -> open -> place_inside`, not the surface-only
`nav -> pick -> nav -> place` pattern that the previous bound-object checker
assumed.

## Decision

Rerun the ADR-0003 real-world cleanup harness with the Phase 125 proof attached
and `--use-planner-proof-for-cleanup-primitives`.

The checker now treats bound cleanup objects as either:

- surface targets requiring `navigate_to_object`, `pick`,
  `navigate_to_receptacle`, and `place`; or
- inside targets requiring `navigate_to_object`, `pick`,
  `navigate_to_receptacle`, `open_receptacle`, and `place_inside`.

The global cleanup artifact remains `api_semantic` unless every cleaned object
has matching strict planner-backed primitive evidence. A single bound proof may
make only its matching object subphases planner-backed.

## Consequences

- The Phase 125 exact proof now drives the ADR-0003 cleanup primitive executor
  for `observed_001` to the refrigerator.
- The final cleanup report renders the shared visual core, Robot View Timeline,
  attached planner proof views, Cleanup Primitive Gate, and Planner Cleanup
  Bridge in one artifact.
- The artifact is intentionally mixed: `observed_001` is strict
  planner-backed for 5 subphases, while unmatched objects remain
  `api_semantic`.
- The bridge stays honest: global primitive provenance remains `api_semantic`,
  cleanup primitive gate status is `blocked_capability`, and planner cleanup
  bridge status is `blocked_capability`.
- Full planner-backed cleanup now requires proof coverage for the remaining
  objects, or a stricter future decision about whether multi-step pick/place
  progress or full containment is required.

## Evidence

Implemented in Phase 126 on 2026-05-10.

The cleanup rerun artifact is:

- `output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json`;
- `output/debug-phase126-phase125-bound-proof-cleanup-rerun/report.html`.

Observed result:

- `cleanup_status=success`;
- `generated_mess_count=10`;
- `robot_view_steps=44`;
- `primitive_provenance=api_semantic`;
- `cleanup_primitive_evidence.primitive_provenance_summary` is
  `planner_backed=5`, `api_semantic=37`;
- `observed_001` to
  `refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2` is strict
  planner-backed for `navigate_to_object`, `pick`, `navigate_to_receptacle`,
  `open_receptacle`, and `place_inside`;
- `planner_cleanup_bridge_evidence.status=blocked_capability`.

Verification:

- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/debug-phase126-phase125-bound-proof-cleanup-rerun --seed 7 --backend molmospaces_subprocess --fixture-hint-mode room_only --perception-mode visible_object_detections --include-robot --robot-name rby1m --record-robot-views --generated-mess-count 10 --planner-proof-run-result output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --use-planner-proof-for-cleanup-primitives`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --require-bound-planner-cleanup-object observed_001:refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2 --require-mixed-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge`
- `.venv/bin/ruff check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/ruff format --check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_proof_bundle_for_full_gate_readiness tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_matching_probe_backed_executor`
