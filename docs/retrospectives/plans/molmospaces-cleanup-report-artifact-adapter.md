# MolmoSpaces Cleanup Report Artifact Adapter

**Status:** Completed under GSD Phase 93 on 2026-05-10
**Created:** 2026-05-10
**Source:** `CONTEXT.md`, ADR-0003, ADR-0009, ADR-0021, ADR-0036, ADR-0050,
ADR-0084, user visual review of `output/molmo-agent-bridge-visual-codex/report.html`
**Workflow:** `hybrid-phase-pipeline`

## Problem

The shared report underlay is the right direction, but old ignored artifacts
can keep stale `report.html` files from earlier implementations. That made the
MolmoSpaces demos look like they still had multiple report implementations:
the old current-contract visual Codex report had the desired robot-view visual
evidence, while newer ADR-0003 reports had the shared visual core and plain
semantic subphases.

The missing module was an artifact adapter whose interface starts at
`run_result.json`, not at individual scenario/trace/snapshot files.

## Decision

Create a Cleanup Report Artifact Adapter that rehydrates a cleanup artifact from
its `run_result.json` and delegates to the shared report renderer.

This phase:

- adds `roboclaws/molmo_cleanup/artifact_report.py`;
- adds `scripts/regenerate_molmo_cleanup_report.py`;
- keeps semantic report labels as `nav, pick, nav, open?, place`;
- supports stale artifact paths by falling back to files colocated with the
  `run_result.json`;
- proves the referenced stale Codex visual artifact can be regenerated and pass
  the existing agent-bridge checker.

## Non-Goals

- Do not create another HTML renderer.
- Do not change cleanup scoring, private evaluation, or ADR-0003 separation.
- Do not claim new planner-backed cleanup coverage.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- A caller can regenerate a cleanup report by passing only `run_result.json`.
- The regenerated report uses the shared visual core:
  Before And After, Object Moves, Semantic Substeps, Robot View Timeline, Score.
- The semantic rail and robot timeline show primary subphases
  `nav, pick, nav, open?, place` with role detail as secondary evidence.
- `output/molmo-agent-bridge-visual-codex/run_result.json` passes
  `scripts/check_molmo_agent_bridge_result.py` after local regeneration.
- Focused lint, format, and pytest pass.

## Result

Complete on 2026-05-10.

Artifact repaired locally:
`output/molmo-agent-bridge-visual-codex/report.html` (ignored; not committed)

Key evidence:

- The stale Codex report now renders `Semantic Substeps` as phase rails with
  `nav`, `pick`, `nav`, `open`, `place`.
- The robot timeline badges now show `Subphase: nav/pick/open/place` with raw
  tool names only as secondary evidence.
- The agent-bridge checker passes for the regenerated artifact.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_report_visual_core.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/regenerate_molmo_cleanup_report.py output/molmo-agent-bridge-visual-codex/run_result.json`
- `.venv/bin/python scripts/check_molmo_agent_bridge_result.py output/molmo-agent-bridge-visual-codex/run_result.json --expect-backend molmospaces_subprocess --expect-robot rby1m --require-robot-views --require-semantic-acceptability`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase93-rotated-source-candidate-selection-dry-run/proof_bundle_run_manifest.json --max-selected-requests 0 --require-prior-covered-exclusion`
