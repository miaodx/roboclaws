# Phase 08 Verification - MolmoSpaces Real Subprocess Cleanup

**Date:** 2026-05-07
**Status:** PASS

## Verification Gates

| Gate | Result |
| --- | --- |
| `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_policy.py tests/test_molmo_cleanup_demo.py tests/test_molmo_cleanup_subprocess_backend.py tests/test_verify_just_recipes.py` | PASS - 13 focused tests passed. |
| `just harness::molmo-real-cleanup` | PASS - wrote real-runtime cleanup artifacts under `output/molmo-real-cleanup-harness/`. |
| `just verify::molmo-real-cleanup` | PASS - 11 focused tests passed, then the real MolmoSpaces harness passed. |

## Real Harness Artifact

`output/molmo-real-cleanup-harness/run_result.json` recorded:

- `backend=molmospaces_subprocess`
- `task_prompt=帮我整理这个房间`
- `scenario_id=molmospaces-procthor-val-0-7`
- `planner=public_heuristic`
- `planner_uses_private_manifest=false`
- `cleanup_status=success`
- `primitive_provenance=api_semantic`
- `primitive_provenance_summary.api_semantic=15`
- `restored_count=5`
- `total_targets=5`
- `success_threshold=3`
- runtime Python `3.11.14`
- MuJoCo `3.4.0`
- upstream scene `procthor-10k-val`, scene index `0`
- scene stats: 140 metadata objects, 415 MuJoCo bodies, 3492 geoms, 129 joints
- report: `output/molmo-real-cleanup-harness/report.html`
- trace: `output/molmo-real-cleanup-harness/trace.jsonl`
- images: `output/molmo-real-cleanup-harness/before.png` and `after.png`

## Acceptance Coverage

| Acceptance criterion | Status |
| --- | --- |
| Real upstream MolmoSpaces/MuJoCo scene loaded | PASS - worker installed/loaded `procthor-10k-val` scene index 0 through the Python 3.11 runtime. |
| Real object inventory/state readback | PASS - `observe` / `scene_objects` report `inventory_source=molmospaces_metadata+mujoco_state` and `metadata_object_count=140`. |
| Prompt is `帮我整理这个房间` | PASS - asserted by `scripts/check_molmospaces_cleanup_result.py --expect-task`. |
| Planner does not read private manifest | PASS - `planner_uses_private_manifest=false`; private manifest is written only as scorer artifact. |
| Backend is not fake/shim/scripted_reference | PASS - run result records `backend=molmospaces_subprocess` and `planner=public_heuristic`. |
| Required artifacts exist | PASS - checker verified `report.html`; manual gate confirmed `before.png`, `after.png`, `trace.jsonl`, and `run_result.json`. |
| Provenance boundary is explicit | PASS - primitives record `api_semantic`; `place` responses record `state_mutation=mujoco_freejoint_qpos` and `qpos_changed=true`. |

## Residual Risks

- This is semantic MuJoCo state mutation, not planner-backed RBY1M/Franka
  manipulation. `primitive_provenance=real` remains deferred.
- The policy is deterministic and public-state-only, not a real VLM/OpenClaw
  agent.
- The subprocess worker reloads the MuJoCo scene per tool call. It is acceptable
  for this proof but should become persistent before broader demos.
