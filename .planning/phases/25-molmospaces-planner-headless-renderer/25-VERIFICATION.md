# Phase 25 Verification

## Result

PASS for the Phase 25 headless Franka planner proof goal.

The strict standalone planner-backed manipulation gate now has a passing local
artifact. Full planner-backed cleanup execution remains a later integration
phase.

## Commands Run

```bash
uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_cleanup_report.py
uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_cleanup_report.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py
.venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-manipulation-probe-headless --probe-mode execute --embodiment franka --steps 2 --timeout-s 420
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --require-planner-backed output/molmo-planner-manipulation-probe-headless/run_result.json
just verify::molmo-planner-manipulation-probe
```

## Observed Outputs

- Focused pytest: `13 passed`.
- Default `just verify::molmo-planner-manipulation-probe`: passed with accepted
  `blocked_capability` evidence for the safe config-import gate.
- Strict headless Franka execute probe:
  - `status=planner_backed`
  - `primitive_provenance=planner_backed`
  - `strict_proof_eligible=true`
  - `execution_attempted=true`
  - `steps_executed=2`
  - `max_abs_qpos_delta=0.01846538091255523`
  - `image_artifacts.initial=planner_views/initial_wrist_camera.png`
  - `image_artifacts.final=planner_views/final_wrist_camera.png`
- Strict checker passed with `--require-planner-backed`.

## Artifact Checks

- `output/molmo-planner-manipulation-probe-headless/report.html` includes:
  `Manipulation Provenance`, `Planner Probe Views`, `Runtime Diagnostics`,
  `planner_backed`, `Strict proof: True`, `renderer_adapter=True`,
  `MUJOCO_GL=egl`, and `PYOPENGL_PLATFORM=egl`.
- `output/molmo-planner-manipulation-probe-headless/run_result.json` records
  the renderer adapter targets:
  `molmo_spaces.env.env.MjOpenGLRenderer` and
  `molmo_spaces.utils.scene_maps.MjOpenGLRenderer`.

## Remaining Gap

The standalone strict proof is now closed for Franka. The broader ADR-0003
cleanup path still needs a separate phase to use planner-backed manipulation
inside the cleanup contract/report loop. RBY1M remains blocked by missing
CuRobo.
