# Phase 08 Context - MolmoSpaces Real Subprocess Cleanup

## Source

- `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
- Phase 6 scaffold: `.planning/milestones/v1.98-phases/06-molmospaces-api-semantic-cleanup/`
- Phase 7 prompt proof: `.planning/milestones/v1.98-phases/07-molmospaces-prompt-driven-cleanup-demo/`

## Why This Phase Exists

Phase 7 proved that the prompt `帮我整理这个房间` can drive a public-only cleanup
policy through the cleanup tool loop, but it still used an in-process synthetic
backend. The user definition of done requires a real upstream MolmoSpaces/MuJoCo
scene, isolated Python 3.11 runtime, real inventory/state readback, and
`backend=molmospaces_subprocess` or equivalent.

## Non-Negotiables

- Do not use `scripted_reference`, fake, shim, or synthetic backend for the
  final proof.
- The planner must not read `private_manifest`; it is scorer-only.
- `api_semantic` is acceptable only if the primitive mutates real MuJoCo state.
- Do not label primitives `real` until RBY1M/Franka planner-backed pick/place is
  proven.
- Required artifacts: `before.png`, `after.png`, `trace.jsonl`,
  `run_result.json`, `report.html`.

## Acceptance Target

`just verify::molmo-real-cleanup` passes locally and the generated
`output/molmo-real-cleanup-harness/run_result.json` records:

- `backend=molmospaces_subprocess`
- `task_prompt=帮我整理这个房间`
- `planner=public_heuristic`
- `planner_uses_private_manifest=false`
- `primitive_provenance=api_semantic`
- real MolmoSpaces runtime and scene metadata
- successful cleanup above the 3-of-5 threshold
