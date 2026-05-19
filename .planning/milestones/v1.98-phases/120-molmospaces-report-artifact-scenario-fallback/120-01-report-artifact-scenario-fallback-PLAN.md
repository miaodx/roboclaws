# Phase 120 Plan: MolmoSpaces Report Artifact Scenario Fallback

## Goal

Close the remaining Cleanup Report Artifact Adapter gap so both scenario-backed
and scenario-less MolmoSpaces cleanup artifacts regenerate from `run_result.json`
through the same shared Cleanup Artifact Report underlay.

## Context

The user compared newer generated reports against
`output/molmo-agent-bridge-visual-codex/report.html` and called out that the
new implementation still looked different. Earlier report slices already
centralized the visual core and semantic subphase labels, but a concrete adapter
gap remained: `output/molmo-realworld-report-underlay-visual/run_result.json`
has no colocated `scenario.json`, so regeneration failed before the shared
underlay could rewrite stale report HTML.

## Scope

- Add a scenario-less fallback to `roboclaws/molmo_cleanup/artifact_report.py`.
- Keep the fallback minimal and public: scenario id, task prompt, seed, no
  fabricated objects, receptacles, or private targets.
- Add regression coverage for scenario-less cleanup report regeneration.
- Record the decision in ADR-0111 and the source plan.
- Regenerate local ignored reports only as verification artifacts.

## Acceptance Criteria

- `scripts/regenerate_molmo_cleanup_report.py` works for
  `output/molmo-realworld-report-underlay-visual/run_result.json`.
- The regenerated realworld visual report uses plain semantic labels in the
  robot timeline and Cleanup Primitive Gate.
- The realworld checker passes with camera-model policy, robot views, and
  blocked planner-cleanup primitives accepted.
- The reference visual Codex bridge checker still passes.
- Focused lint, format, and pytest pass.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_report_visual_core.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/regenerate_molmo_cleanup_report.py output/molmo-realworld-report-underlay-visual/run_result.json`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --require-camera-model-policy --require-robot-views --accept-blocked-planner-cleanup-primitives output/molmo-realworld-report-underlay-visual/run_result.json`
- `.venv/bin/python scripts/check_molmo_agent_bridge_result.py output/molmo-agent-bridge-visual-codex/run_result.json --expect-backend molmospaces_subprocess --expect-robot rby1m --require-robot-views --require-semantic-acceptability`

## Result

Complete on 2026-05-10.

The adapter now keeps `run_result.json` as the single report regeneration
interface even when a cleanup artifact lacks `scenario.json`. Scenario-backed
artifacts still load the real scenario bundle. Scenario-less artifacts use a
minimal public shell and render from the existing run result, trace, snapshots,
and robot-view evidence.
