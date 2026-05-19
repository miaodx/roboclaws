# Phase 45 Verification: Report Visual Core Contract

Date: 2026-05-11
Source plan: `45-01-report-visual-core-contract-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
45. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- Cleanup reports with semantic substeps must render the visual core in this
  order: Before/After, Object Moves, Semantic Substeps, optional Robot View
  Timeline, Score.
- Semantic Substeps must use report-facing labels such as `nav/object`,
  `pick/object`, `nav/target`, and `place/surface` or `place/inside`.
- Current-contract and ADR-0003 checkers fail stale raw-semantic report shapes.
- ADR-0003 MCP robot-view capture no longer maintains a second semantic phase
  mapping.
- Existing MCP and deterministic cleanup behavior stays unchanged.

## Recorded Verification Evidence

- Passed: `uv run ruff check roboclaws/molmo_cleanup/report_visual_core.py roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/check_molmo_agent_bridge_result.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `uv run ruff format --check roboclaws/molmo_cleanup/report_visual_core.py roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/check_molmo_agent_bridge_result.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmo_report_visual_core.py tests/test_check_molmo_agent_bridge_result.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_realworld_mcp_server.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_cleanup_mcp_server.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_demo.py`
- Passed: `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`

The tightened current-contract checker now rejects
`output/molmo-agent-bridge-visual-codex/run_result.json` because that ignored
artifact is stale and lacks the canonical `Before And After` visual-core
heading.

## Artifact Integrity Checks

- Source plan exists: `45-01-report-visual-core-contract-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-10`.
- Backfilled summary exists: `45-01-report-visual-core-contract-SUMMARY.md`.
- Backfilled verification exists: `45-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 45 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.
