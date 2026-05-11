# Phase 23 Verification

Date: 2026-05-09

## Commands

```bash
.venv/bin/ruff check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/report.py examples/molmospaces_cleanup_demo.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/mcp_server.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_manipulation_provenance.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_verify_just_recipes.py tests/test_molmo_cleanup_mcp_server.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py
.venv/bin/ruff format --check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/report.py examples/molmospaces_cleanup_demo.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/mcp_server.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_manipulation_provenance.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_verify_just_recipes.py tests/test_molmo_cleanup_mcp_server.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_cleanup_mcp_server.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_report.py tests/test_molmo_manipulation_provenance.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_verify_just_recipes.py
just verify::molmo-planner-manipulation-probe
```

## Result

All commands passed.

The verify recipe produced
`output/molmo-planner-manipulation-probe-harness/run_result.json` and
`output/molmo-planner-manipulation-probe-harness/report.html`. The artifact is
intentionally `blocked_capability`: planner class import exists, but strict
planner-backed execution proof is not claimed by the default gate.
