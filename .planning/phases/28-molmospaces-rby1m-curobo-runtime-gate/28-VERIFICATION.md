# Phase 28 Verification: RBY1M CuRobo Runtime Gate

Date: 2026-05-09

## Commands

```bash
uv run ruff check roboclaws/molmo_cleanup/rby1m_curobo_gate.py scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_rby1m_curobo_gate.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py
uv run ruff format --check roboclaws/molmo_cleanup/rby1m_curobo_gate.py scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_rby1m_curobo_gate.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_rby1m_curobo_gate.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py
.venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-curobo-gate --embodiment rby1m --probe-mode config_import --steps 2 --timeout-s 120
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked output/molmo-planner-rby1m-curobo-gate/run_result.json
```

Strict rejection check:

```bash
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --require-rby1m-curobo-ready output/molmo-planner-rby1m-curobo-gate/run_result.json
```

The strict command rejects the current artifact as expected because CuRobo is
not available and RBY1M planner execution was not attempted.

## Artifact Review

- `output/molmo-planner-rby1m-curobo-gate/report.html` contains
  `Planner-Backed Manipulation Probe`, `Runtime Diagnostics`,
  `RBY1M CuRobo Gate`, `Capability Blockers`, `curobo`, and
  `blocked_capability`.
- `output/molmo-planner-rby1m-curobo-gate/run_result.json` contains
  `rby1m_curobo_gate` with `status=blocked_capability`,
  `embodiment=rby1m`, `curobo_available=false`, and blockers for missing
  CuRobo / unattempted execution.

## Verdict

Phase 28 satisfies the target-runtime gate requirement. It does not satisfy
actual RBY1M planner execution; that requires CuRobo/runtime enablement first.
