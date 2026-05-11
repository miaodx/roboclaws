# Phase 45 Summary: Report Visual Core Contract

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `45-01-report-visual-core-contract-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Make current-contract and ADR-0003 MolmoSpaces cleanup demos enforce one
Cleanup Artifact Report visual core and one semantic robot-view mapping.

## Completed Tasks

- Add ADR/source-plan documentation and update roadmap/state/context.
- Add a shared report visual-core contract helper.
- Wire current-contract and ADR-0003 checkers to the shared visual-core contract.
- Reuse `semantic_timeline.robot_view_capture_for_tool` in the ADR-0003 MCP server.
- Extend the shared robot-view capture helper to accept `fixture_id` target keys.
- Add focused tests for stale raw semantic reports and fixture-ID capture.
- Run focused verification gates.

## Recorded Status

Completed 2026-05-10.

## Evidence

- Passed: `uv run ruff check roboclaws/molmo_cleanup/report_visual_core.py roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/check_molmo_agent_bridge_result.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `uv run ruff format --check roboclaws/molmo_cleanup/report_visual_core.py roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/check_molmo_agent_bridge_result.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_cleanup_mcp_server.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_demo.py`
- Passed: `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`

The tightened current-contract checker now rejects
`output/molmo-agent-bridge-visual-codex/run_result.json` because that ignored
artifact is stale and lacks the canonical `Before And After` visual-core
heading.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
