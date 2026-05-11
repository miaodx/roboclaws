# Phase 22 Verification

Verified: 2026-05-09

## Commands

```bash
.venv/bin/ruff check roboclaws/molmo_cleanup/realworld_contract.py roboclaws/molmo_cleanup/realworld_mcp_server.py roboclaws/molmo_cleanup/report.py examples/molmospaces_realworld_cleanup.py examples/molmo_realworld_cleanup_agent_server.py scripts/run_molmo_realworld_agent_mcp_smoke.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_contract.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmospaces_realworld_cleanup.py tests/test_verify_just_recipes.py
.venv/bin/ruff format --check roboclaws/molmo_cleanup/realworld_contract.py roboclaws/molmo_cleanup/realworld_mcp_server.py roboclaws/molmo_cleanup/report.py examples/molmospaces_realworld_cleanup.py examples/molmo_realworld_cleanup_agent_server.py scripts/run_molmo_realworld_agent_mcp_smoke.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_contract.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmospaces_realworld_cleanup.py tests/test_verify_just_recipes.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_contract.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmospaces_realworld_cleanup.py tests/test_verify_just_recipes.py
just verify::molmo-realworld-raw-fpv
```

## Results

- Ruff check passed.
- Ruff format check passed.
- Focused pytest slice passed: 39 tests.
- `just verify::molmo-realworld-raw-fpv` passed, including the real
  MolmoSpaces/RBY1M harness and checker.

## Artifact Assertions

`output/molmo-realworld-raw-fpv-harness/run_result.json` records:

- `perception_mode=raw_fpv_only`
- `cleanup_status=failed`
- `sweep_coverage_rate=1.0`
- `raw_fpv_observations=14`
- `robot_view_steps=16`
- first FPV artifact:
  `robot_views/0001_raw_fpv_001.fpv.png`

`output/molmo-realworld-raw-fpv-harness/report.html` contains:

- `Agent View`
- `Raw FPV Observations`
- `Robot View Timeline`
- `Advisory Review`
- `Private Evaluation`

## Residual Risk

Raw FPV mode is evidence-only. It does not yet let an agent register or select
objects from pixels, so it intentionally does not produce clean cleanup success.
