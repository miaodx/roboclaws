# Phase 120 Summary: MolmoSpaces Report Artifact Scenario Fallback

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `120-01-report-artifact-scenario-fallback-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Close the remaining Cleanup Report Artifact Adapter gap so both scenario-backed
and scenario-less MolmoSpaces cleanup artifacts regenerate from `run_result.json`
through the same shared Cleanup Artifact Report underlay.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The adapter now keeps `run_result.json` as the single report regeneration
interface even when a cleanup artifact lacks `scenario.json`. Scenario-backed
artifacts still load the real scenario bundle. Scenario-less artifacts use a
minimal public shell and render from the existing run result, trace, snapshots,
and robot-view evidence.

## Evidence

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_report_visual_core.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/regenerate_molmo_cleanup_report.py output/molmo-realworld-report-underlay-visual/run_result.json`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --require-camera-model-policy --require-robot-views --accept-blocked-planner-cleanup-primitives output/molmo-realworld-report-underlay-visual/run_result.json`
- `.venv/bin/python scripts/check_molmo_agent_bridge_result.py output/molmo-agent-bridge-visual-codex/run_result.json --expect-backend molmospaces_subprocess --expect-robot rby1m --require-robot-views --require-semantic-acceptability`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
