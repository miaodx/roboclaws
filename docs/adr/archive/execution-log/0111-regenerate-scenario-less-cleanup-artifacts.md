# 0111. Regenerate Scenario-Less Cleanup Artifacts

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0009 and ADR-0021 require current-contract and ADR-0003 MolmoSpaces cleanup
artifacts to share one Cleanup Artifact Report underlay. Phase 93 added the
Cleanup Report Artifact Adapter so stale ignored `report.html` files can be
regenerated from `run_result.json`.

The adapter still assumed every cleanup artifact had a colocated `scenario.json`.
That held for `output/molmo-agent-bridge-visual-codex/`, but not for
`output/molmo-realworld-report-underlay-visual/`, whose `run_result.json`
contains the score, trace path, snapshots, robot timeline, Agent View, and
Private Evaluation but no scenario artifact. This made the newer ADR-0003
artifact look like it required a different report implementation.

## Decision

The Cleanup Report Artifact Adapter treats `run_result.json` as the report
regeneration interface even when `scenario.json` is absent.

If a scenario artifact exists, the adapter rehydrates it as before. If it is
missing, the adapter builds a minimal public scenario shell from
`run_result.json` using only scenario id, task prompt, and seed, with no
objects, receptacles, or private targets fabricated. The report remains driven
by the existing run result, trace, snapshots, and robot timeline.

## Consequences

- Scenario-less ADR-0003 cleanup artifacts regenerate through the same shared
  underlay as current-contract bridge artifacts.
- The canonical visual sequence and semantic subphase display stay centralized:
  Before/After, Object Moves, Semantic Substeps, Robot View Timeline, Score,
  then contract-specific evidence.
- The fallback is deliberately shallow: it preserves report presentation but
  does not invent missing scenario objects or private scoring truth.
- Future cleanup demos should keep adding data to `run_result.json` and the
  shared adapter instead of creating per-demo HTML renderers.

## Evidence

Implemented in Phase 120 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_report_visual_core.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/regenerate_molmo_cleanup_report.py output/molmo-realworld-report-underlay-visual/run_result.json`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --require-camera-model-policy --require-robot-views --accept-blocked-planner-cleanup-primitives output/molmo-realworld-report-underlay-visual/run_result.json`
- `.venv/bin/python scripts/check_molmo_agent_bridge_result.py output/molmo-agent-bridge-visual-codex/run_result.json --expect-backend molmospaces_subprocess --expect-robot rby1m --require-robot-views --require-semantic-acceptability`
