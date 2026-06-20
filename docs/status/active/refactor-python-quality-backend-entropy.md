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

2026-06-20: B1 asset visual comparison validation now treats explicit baseline
and candidate navigation artifacts as JSON-object source truth before writing
comparison outputs. Focused asset-comparison CLI source tests, touched-file
Ruff/format, `git diff --check`, and ratchet passed. Quality signal: 0 Ruff
complexity rows, 79 oversized modules.

## Next Action

Pick a fresh fail-aloud/source-truth seam from current ratchet evidence.

## Touched Areas

- `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py`
- `scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py`
- `scripts/isaac_lab_cleanup/check_b1_map12_readiness.py`
- `scripts/isaac_lab_cleanup/check_b1_map12_asset_visual_comparison.py`
- `scripts/isaac_lab_cleanup/check_prepared_semantic_usd_summary.py`
- `scripts/isaac_lab_cleanup/compare_isaac_segmentation_aov.py`
- `scripts/isaac_lab_cleanup/summarize_isaac_aov_matrix.py`
- `scripts/maps/suggest_b1_map12_manual_anchor_semantics.py`
- `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- `scripts/maps/render_b1_map12_correspondence_review.py`
- `scripts/maps/fit_b1_map12_scene_alignment.py`
- `scripts/maps/render_b1_map12_manual_alignment_overlay.py`
- `tests/contract/maps/test_b1_map12_navigation_smoke_cli.py`
- `tests/contract/maps/test_b1_map12_navigation_report.py`
- `tests/contract/maps/test_b1_map12_readiness_cli.py`
- `tests/contract/maps/test_b1_map12_asset_visual_comparison.py`
- `tests/unit/molmo_cleanup/test_check_prepared_semantic_usd_summary.py`
- `tests/unit/molmo_cleanup/test_isaac_segmentation_aov_compare.py`
- `tests/contract/maps/test_b1_map12_manual_anchor_semantics_cli.py`
- `tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary_sources.py`
- `tests/contract/maps/test_b1_map12_correspondence_review_cli.py`
- `tests/contract/maps/test_b1_map12_alignment_fit_cli.py`
- `tests/contract/maps/test_b1_map12_manual_alignment_overlay_cli.py`
- `docs/plans/refactor-python-quality-backend-entropy.md`
- `docs/plans/refactor-python-quality-backend-entropy-completed.md`

## No-Touch Scope

- Do not touch unrelated CloudML/eval dirty files:
  `docs/plans/2026-06-18-cloudml-juicefs-eval.md`,
  `docs/status/active/2026-06-18-cloudml-juicefs-eval.md`,
  `roboclaws/evals/live_runtime.py`,
  `scripts/dev/cloudml_eval_dry_run.sh`,
  `scripts/dev/stage_cloudml_cleanup_assets.sh`, and
  `tests/unit/evals/test_eval_runner.py`.
- Do not touch unrelated `docs/status/active/2026-06-18-sdk-storage-targets.md`.
- Avoid adding to `tests/contract/maps/test_b1_map12_verified_alignment.py`
  unless also compacting local debt; it is at the 2000-line hard ceiling.
