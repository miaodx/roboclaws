# MolmoSpaces Report Artifact Scenario Fallback

**Status:** Completed under GSD Phase 120 on 2026-05-10
**Created:** 2026-05-10
**Source:** User visual review of `output/molmo-agent-bridge-visual-codex/report.html`, ADR-0009, ADR-0021, ADR-0050, ADR-0111, `CONTEXT.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

The Cleanup Report Artifact Adapter was the right seam for avoiding multiple
MolmoSpaces cleanup report implementations, but it still only worked for
artifacts with a colocated `scenario.json`.

That left a practical mismatch:

- `output/molmo-agent-bridge-visual-codex/run_result.json` could regenerate
  through the shared underlay and show the desired `nav, pick, nav, open?,
  place` visual rhythm.
- `output/molmo-realworld-report-underlay-visual/run_result.json` failed
  regeneration because the artifact has no `scenario.json`, even though the
  report has enough run-result, trace, snapshot, robot-view, Agent View, and
  Private Evaluation evidence.

## Decision

Keep `run_result.json` as the adapter interface and make the scenario artifact
optional for report regeneration.

If a real scenario artifact is present, the adapter loads it. If not, it builds
a minimal public scenario shell from the run result's scenario id, task prompt,
and seed, and delegates to the same `render_cleanup_report` underlay.

## Non-Goals

- Do not invent missing scenario objects, receptacles, Generated Mess Set rows,
  or private targets.
- Do not change cleanup scoring, primitive provenance, or planner-backed
  readiness.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- Scenario-backed and scenario-less cleanup artifacts both regenerate through
  `scripts/regenerate_molmo_cleanup_report.py`.
- Regenerated reports keep the shared visual core and plain semantic subphases.
- The realworld checker passes for the scenario-less ADR-0003 visual artifact.
- The referenced bridge checker still passes for the original visual Codex
  artifact.

## Result

Complete.

Implemented:

- `roboclaws/molmo_cleanup/artifact_report.py` now falls back to a minimal
  scenario shell when no scenario artifact exists.
- `tests/test_molmo_cleanup_artifact_report.py` covers scenario-less
  regeneration and asserts the report keeps plain `nav` subphase labels.
- `docs/adr/0111-regenerate-scenario-less-cleanup-artifacts.md` records the
  ADR gap closed by this slice.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_report_visual_core.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/regenerate_molmo_cleanup_report.py output/molmo-realworld-report-underlay-visual/run_result.json`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --require-camera-model-policy --require-robot-views --accept-blocked-planner-cleanup-primitives output/molmo-realworld-report-underlay-visual/run_result.json`
- `.venv/bin/python scripts/check_molmo_agent_bridge_result.py output/molmo-agent-bridge-visual-codex/run_result.json --expect-backend molmospaces_subprocess --expect-robot rby1m --require-robot-views --require-semantic-acceptability`
