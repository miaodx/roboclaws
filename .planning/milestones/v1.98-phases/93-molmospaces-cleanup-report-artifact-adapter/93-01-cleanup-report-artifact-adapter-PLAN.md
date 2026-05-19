# Phase 93-01: Cleanup Report Artifact Adapter

## Goal

Make stale MolmoSpaces cleanup artifacts regenerate through the shared Cleanup
Artifact Report underlay from only their `run_result.json`, eliminating the
remaining practical path for old report HTML to masquerade as a second
implementation.

## Tasks

- Add a small adapter that loads scenario, private manifest, trace, snapshots,
  and robot-view steps from a cleanup `run_result.json`.
- Delegate report writing to the existing shared `render_cleanup_report`
  underlay.
- Add a CLI for local artifact repair without rerunning MolmoSpaces.
- Add focused tests for artifact loading, colocated stale path fallback, and
  shared visual-core rendering.
- Re-render the referenced stale visual Codex report locally and run the
  existing bridge checker.

## Acceptance

- `scripts/regenerate_molmo_cleanup_report.py <run_result.json>` writes the
  report through `roboclaws/molmo_cleanup/report.py`.
- Semantic subphases render as `nav, pick, nav, open?, place`.
- The referenced `output/molmo-agent-bridge-visual-codex/run_result.json`
  passes the agent-bridge checker after regeneration.
- Lint, format, focused pytest, and report checker gates pass.

## Result

Complete on 2026-05-10.

Artifact repaired locally:
`output/molmo-agent-bridge-visual-codex/report.html`

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_report_visual_core.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/check_molmo_agent_bridge_result.py output/molmo-agent-bridge-visual-codex/run_result.json --expect-backend molmospaces_subprocess --expect-robot rby1m --require-robot-views --require-semantic-acceptability`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase93-rotated-source-candidate-selection-dry-run/proof_bundle_run_manifest.json --max-selected-requests 0 --require-prior-covered-exclusion`
