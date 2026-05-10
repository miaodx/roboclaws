# 0115. Focus Cleanup Report Robot Timeline On Subphases

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0009 and ADR-0021 require current-contract and ADR-0003 cleanup artifacts to
share one Cleanup Artifact Report underlay and the same report-facing loop:
`nav -> pick -> nav -> open? -> place`.

The remaining visual gap was not a second renderer. The ADR-0003 camera-model
artifacts recorded raw FPV scan captures in `robot_view_steps`, so the primary
Robot View Timeline was dominated by perception scan cards before the semantic
cleanup actions appeared. The desired current-contract visual artifact
`output/molmo-agent-bridge-visual-codex/report.html` already showed the better
review shape: first-pass robot evidence should emphasize semantic cleanup
subphases, while raw scan evidence remains available as a separate evidence
panel.

## Decision

Keep raw FPV observation captures out of the primary Robot View Timeline when a
cleanup artifact also renders the Raw FPV Observations panel.

The raw FPV captures remain in `run_result.json`, `agent_view`, and the Raw FPV
Observations report section. The visual core Robot View Timeline keeps
before/after and semantic cleanup action views, so ADR-0003 and
current-contract reports share the same first-pass visual rhythm.

Also allow `scripts/regenerate_molmo_cleanup_report.py` to accept multiple
`run_result.json` paths. This keeps stale ignored cleanup artifacts repairable
through the same Cleanup Report Artifact Adapter instead of one-off report
rewrites.

## Consequences

- ADR-0003 reports stay visually close to the current-contract visual bridge:
  semantic cleanup actions are no longer buried under raw perception scans.
- Raw FPV evidence is not hidden; it is just rendered in its own post-score
  evidence section.
- Regeneration remains a single adapter seam starting at `run_result.json`.
- Planner/proof diagnostic reports are unaffected.

## Evidence

Implemented in Phase 124 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py roboclaws/molmo_cleanup/report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py roboclaws/molmo_cleanup/report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py tests/test_molmo_report_visual_core.py`
