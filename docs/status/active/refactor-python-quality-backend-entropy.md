# Python Quality Backend Entropy Ratchet

Owner/session: Codex main session
Started: 2026-06-20
State: active

## Scope

Continue the accepted Python quality/backend entropy campaign one vertical
slice at a time. Source truth remains the active plan; completed slices belong
only in the completed ledger.

## Source Of Truth

- Plan: `docs/plans/refactor-python-quality-backend-entropy.md`
- Completed ledger: `docs/plans/refactor-python-quality-backend-entropy-completed.md`

## Latest Checkpoint

2026-06-20: Robot-camera visual parity summary loading now treats explicit
baseline/probe, RAW-FPV run result, calibration manifest, prepared USD summary,
paired comparison, visual sample, and nested RGB-gain source manifests as
JSON-object source truth before writing `visual_parity_summary.json` or
`report.html`. Focused visual-parity source tests, selected existing
visual-parity regression tests, touched-file Ruff/format, `git diff --check`,
changed-code review, and ratchet passed. Quality signal: 0 Ruff complexity
rows, 79 oversized modules.

## Next Action

Pick a fresh fail-aloud/source-truth seam from current ratchet evidence.

## Touched Areas

- `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py`
- `scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py`
- `scripts/maps/suggest_b1_map12_manual_anchor_semantics.py`
- `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- `tests/contract/maps/test_b1_map12_navigation_smoke_cli.py`
- `tests/contract/maps/test_b1_map12_navigation_report.py`
- `tests/contract/maps/test_b1_map12_manual_anchor_semantics_cli.py`
- `tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary_sources.py`
- `docs/plans/refactor-python-quality-backend-entropy.md`
- `docs/plans/refactor-python-quality-backend-entropy-completed.md`

## No-Touch Scope

- Do not touch unrelated `docs/status/active/2026-06-18-sdk-storage-targets.md`.
- Avoid adding to `tests/contract/maps/test_b1_map12_verified_alignment.py`
  unless also compacting local debt; it is at the 2000-line hard ceiling.
