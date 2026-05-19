# 45-01 Report Visual Core Contract Plan

## Goal

Make current-contract and ADR-0003 MolmoSpaces cleanup demos enforce one
Cleanup Artifact Report visual core and one semantic robot-view mapping.

## Status

Completed 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add a shared report visual-core contract helper.
3. [x] Wire current-contract and ADR-0003 checkers to the shared visual-core
   contract.
4. [x] Reuse `semantic_timeline.robot_view_capture_for_tool` in the ADR-0003
   MCP server.
5. [x] Extend the shared robot-view capture helper to accept `fixture_id`
   target keys.
6. [x] Add focused tests for stale raw semantic reports and fixture-ID capture.
7. [x] Run focused verification gates.

## Acceptance

- Cleanup reports with semantic substeps must render the visual core in this
  order: Before/After, Object Moves, Semantic Substeps, optional Robot View
  Timeline, Score.
- Semantic Substeps must use report-facing labels such as `nav/object`,
  `pick/object`, `nav/target`, and `place/surface` or `place/inside`.
- Current-contract and ADR-0003 checkers fail stale raw-semantic report shapes.
- ADR-0003 MCP robot-view capture no longer maintains a second semantic phase
  mapping.
- Existing MCP and deterministic cleanup behavior stays unchanged.

## Verification

- Passed: `uv run ruff check roboclaws/molmo_cleanup/report_visual_core.py roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/check_molmo_agent_bridge_result.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `uv run ruff format --check roboclaws/molmo_cleanup/report_visual_core.py roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/check_molmo_agent_bridge_result.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_cleanup_mcp_server.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_demo.py`
- Passed: `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`

The tightened current-contract checker now rejects
`output/molmo-agent-bridge-visual-codex/run_result.json` because that ignored
artifact is stale and lacks the canonical `Before And After` visual-core
heading.

## Risks

- Tightening the checkers can invalidate old ignored `output/` artifacts. That
  is intentional for stale artifacts, but the checker should still accept
  minimum OpenClaw partial runs that do not claim completed semantic cleanup.
- Moving ADR-0003 MCP capture to the shared helper must preserve observed-handle
  to internal-object focus mapping.

## Completion Notes

`report_visual_core.py` now owns the shared Cleanup Artifact Report section
contract used by both Molmo current-contract and ADR-0003 checkers. The
checkers still allow partial minimum OpenClaw artifacts, but completed semantic
cleanup reports must render the canonical visual core and the compact semantic
subphase vocabulary.

`RealWorldMolmoCleanupMCPServer` now delegates robot-view capture metadata to
`semantic_timeline.robot_view_capture_for_tool`, with `fixture_id` supported as
the ADR-0003 target key. This removes the remaining hand-rolled semantic phase
mapping from the MCP server.
