# Phase 10 Verification - MolmoSpaces Semantic Substeps

Verified on 2026-05-08 in the local workstation session.

## Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Dependency preflight | PASS | `uv --version` -> `uv 0.9.27`; `uv pip install -e ".[dev]"` rebuilt `roboclaws==0.1.0`; `.venv/bin/python -c "import ai2thor; ..."` -> `ai2thor 5.0.0 ok`. |
| Focused formatting | PASS | `.venv/bin/ruff format --check examples/molmospaces_cleanup_demo.py roboclaws/molmo_cleanup/backend.py roboclaws/molmo_cleanup/mcp_contract.py roboclaws/molmo_cleanup/subprocess_backend.py roboclaws/molmo_cleanup/report.py scripts/molmospaces_subprocess_worker.py scripts/check_molmospaces_cleanup_result.py tests/test_molmo_cleanup_demo.py tests/test_molmo_cleanup_report.py` -> `9 files already formatted`. |
| Focused lint | PASS | Same focused file set with `.venv/bin/ruff check ...` -> `All checks passed!`. |
| Focused unit/report/recipe tests | PASS | `just verify::molmo-robot-visual` first ran `tests/test_molmo_cleanup_policy.py`, `tests/test_molmo_cleanup_demo.py`, `tests/test_molmo_cleanup_report.py`, `tests/test_molmo_cleanup_subprocess_backend.py`, and `tests/test_verify_just_recipes.py` -> `15 passed`. |
| Real non-robot MolmoSpaces cleanup | PASS | `just harness::molmo-real-cleanup` -> checker success for `output/molmo-real-cleanup-harness/run_result.json`. |
| Real RBY1M visual cleanup | PASS | `just verify::molmo-robot-visual` -> checker success for `output/molmo-robot-visual-harness/run_result.json`. |

## Real Runtime Evidence

Latest non-robot real run:

- Output: `output/molmo-real-cleanup-harness/`
- Backend: `molmospaces_subprocess`
- Runtime: Python `3.11.14`, MuJoCo `3.4.0`
- Scene: upstream `procthor-10k-val` scene index `0`
- Scene stats: 140 metadata objects, 415 MuJoCo bodies, 3492 geoms, 129 joints
- Planner: `public_heuristic`
- `planner_uses_private_manifest`: `false`
- Primitive provenance: `api_semantic`
- Cleanup status: `success`
- Restored: `5/5`
- Required artifacts present: `before.png`, `after.png`, `trace.jsonl`, `run_result.json`, `report.html`

Latest RBY1M visual run:

- Output: `output/molmo-robot-visual-harness/`
- Backend: `molmospaces_subprocess`
- Runtime: Python `3.11.14`, MuJoCo `3.4.0`
- Scene stats with RBY1M included: 140 metadata objects, 453 MuJoCo bodies, 4513 geoms, 158 joints
- Robot: `rby1m`, with `robot_0/head_camera` and follower camera available
- Robot control provenance: `semantic_robot_base_and_head_qpos`
- View variant: `molmospaces-rby1m-fpv-map-chase-verify`
- Robot view steps: 25
- Cleanup status: `success`
- Restored: `5/5`

## Semantic Loop Evidence

Both real runs record:

- `semantic_loop_variant`: `navigate-pick-navigate-open-place-object_done`
- Tool counts:
  - `navigate_to_object:request`: 5
  - `pick:request`: 5
  - `navigate_to_receptacle:request`: 5
  - `open_receptacle:request`: 1
  - `place_inside:request`: 1
  - `place:request`: 4
  - `object_done:request`: 5

Apple/fridge evidence:

- Object: `apple_9f56af06d43fe8692531302b5e0dc1df_1_0_2`
- Target: `refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2`
- Sequence: `navigate_to_object`, `pick`, `navigate_to_receptacle`, `open_receptacle`, `place_inside`, `object_done`
- Final containment: `contained_in=refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2`
- Final relation: `location_relation=inside`

## Privacy And Provenance

- The planner remains public-only: `planner=public_heuristic` and `planner_uses_private_manifest=false`.
- The private manifest remains scorer-only.
- `primitive_provenance=api_semantic`, not `real`.
- This is acceptable because the worker mutates real MolmoSpaces/MuJoCo scene state through qpos/joint updates. It is still not planner-backed RBY1M/Franka pick/place.

## Visual Follow-up Evidence

- Non-focused `before`, `observe`, `scene_objects`, and `after` robot timeline rows keep FPV/chase/map context but the report suppresses the misleading Verification panel and zero-pixel visibility badges when `focus.has_focus=false`.
- Focused semantic rows carry `semantic_phase`, public focus provenance, same-room pose evidence, and FPV/verification visibility checks.
- A first visual gate run failed because the selected `RemoteControl` target was seeded into an occluded desk spot. The final implementation raises `RemoteControl` seed/place height on real receptacles so the object is visible in the robot source-navigation frame; the rerun passed.
