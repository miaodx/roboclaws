# Phase 24 Verification

## Result

PASS for the Phase 24 diagnostics goal.

Strict planner-backed cleanup execution remains blocked and is intentionally not
claimed by this phase.

## Commands Run

```bash
uv --version && uv pip install -e ".[dev]"
.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"
set -a && source .env && set +a && .venv/bin/python -c "import os; assert os.environ.get('KIMI_API_KEY') or os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY'), 'No VLM API key set — did you source .env?'"
uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py
uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_manipulation_provenance.py
just verify::molmo-planner-manipulation-probe
.venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-manipulation-probe-execute --probe-mode execute --embodiment franka --steps 2 --timeout-s 120
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability output/molmo-planner-manipulation-probe-execute/run_result.json
.venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-manipulation-probe-rby1m --probe-mode config_import --embodiment rby1m --steps 2 --timeout-s 120
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability output/molmo-planner-manipulation-probe-rby1m/run_result.json
```

## Observed Outputs

- Focused pytest: `10 passed`.
- `just verify::molmo-planner-manipulation-probe`: default probe completed as
  accepted blocked-capability evidence and checker passed.
- Franka execute-mode probe: `status=blocked_capability`,
  `worker_returncode=-11`, blocker `process_signal`, message
  `worker terminated by SIGSEGV`.
- Franka stderr: faulthandler stack captured the crash at
  `glfw.create_window` inside MolmoSpaces OpenGL rendering during task sampling.
- RBY1M config-import probe: `status=blocked_capability`, blocker
  `ModuleNotFoundError`, message `No module named 'curobo'`, and
  `runtime_diagnostics.modules.curobo.available=false`.

## Artifact Checks

- `output/molmo-planner-manipulation-probe-harness/report.html` includes
  `Runtime Diagnostics`.
- `output/molmo-planner-manipulation-probe-execute/report.html` includes
  `Runtime Diagnostics` even though the worker segfaulted before final JSON.
- `output/molmo-planner-manipulation-probe-rby1m/report.html` includes
  `Runtime Diagnostics` and the CuRobo blocker.

## Notes

- The bare `python` executable is not on this shell's PATH. The repo venv
  interpreter `.venv/bin/python` was used for preflight and manual probes.
- No VLM calls were made during this phase; the `.env` key sanity check passed
  only to satisfy the repo's standard local preflight.
