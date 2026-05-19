# Phase 11 Verification - MolmoSpaces Held-Object Carry Visuals

Verified on 2026-05-08 in the local workstation session.

## Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Focused formatting | PASS | `.venv/bin/ruff format --check scripts/molmospaces_subprocess_worker.py scripts/check_molmospaces_cleanup_result.py tests/test_molmo_cleanup_subprocess_backend.py` -> `3 files already formatted`. |
| Focused lint | PASS | `.venv/bin/ruff check scripts/molmospaces_subprocess_worker.py scripts/check_molmospaces_cleanup_result.py tests/test_molmo_cleanup_subprocess_backend.py` -> `All checks passed!`. |
| Focused tests | PASS | `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_subprocess_backend.py tests/test_molmo_cleanup_demo.py tests/test_molmo_cleanup_report.py tests/test_verify_just_recipes.py` -> `11 passed, 1 skipped`; the skipped test requires local `mujoco` in the repo venv and is exercised by the isolated MolmoSpaces runtime gate below. |
| Real RBY1M visual cleanup | PASS | `just verify::molmo-robot-visual` -> focused recipe tests passed, then checker success for `output/molmo-robot-visual-harness/run_result.json`. |
| Explicit checker replay | PASS | `.venv/bin/python scripts/check_molmospaces_cleanup_result.py --require-public-planner --expect-task "帮我整理这个房间" --expect-backend molmospaces_subprocess --expect-robot rby1m --require-robot-views --require-semantic-substeps output/molmo-robot-visual-harness/run_result.json` -> `molmo-cleanup ok`. |
| Diff hygiene | PASS | `git diff --check` exited 0. |

## Real Runtime Evidence

Latest RBY1M visual run:

- Output: `output/molmo-robot-visual-harness/`
- Backend: `molmospaces_subprocess`
- Runtime: Python `3.11.14`, MuJoCo `3.4.0`
- Scene: upstream `procthor-10k-val` scene index `0`
- Robot: `rby1m`
- Planner: `public_heuristic`
- `planner_uses_private_manifest`: `false`
- Primitive provenance: `api_semantic`
- Cleanup status: `success`
- Restored: `5/5`
- Robot view steps: `25`
- Required artifacts present: `before.png`, `after.png`, `trace.jsonl`,
  `run_result.json`, `report.html`

## Held-Object Evidence

`navigate_to_receptacle` rows now record the object as `held`, with the object
position equal to the robot-relative held pose:

| Row | Object | FPV object pixels | FPV receptacle pixels | Robot-relative error |
| --- | --- | ---: | ---: | ---: |
| `0005_navigate_receptacle_1` | Apple | `1917` | `95259` | `0.0` |
| `0010_navigate_receptacle_2` | Book | `22602` | `38095` | `0.0` |
| `0014_navigate_receptacle_3` | Bowl | `18569` | `48256` | `0.000001` |
| `0018_navigate_receptacle_4` | Pillow | `38946` | `86784` | `0.0` |
| `0022_navigate_receptacle_5` | RemoteControl | `3798` | `83778` | `0.0` |

Trace responses record the new real-state mutation:

- `navigate_to_receptacle`: `robot_base_qpos+held_object_freejoint_qpos`
- `open_receptacle` for the fridge:
  `mujoco_receptacle_joint_qpos+robot_base_qpos+held_object_freejoint_qpos`

## Privacy And Provenance

- The planner remains public-only: `planner=public_heuristic` and
  `planner_uses_private_manifest=false`.
- The private manifest remains scorer-only.
- `primitive_provenance=api_semantic`, not `real`.
- This is acceptable because the worker mutates real MolmoSpaces/MuJoCo scene
  state through qpos/joint updates. It is still not planner-backed RBY1M/Franka
  pick/place.
