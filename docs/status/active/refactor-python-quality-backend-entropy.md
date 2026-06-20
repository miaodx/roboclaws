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

2026-06-20: Agibot metric-map generation now routes the required
`context_json` source through the shared JSON-object helper before map-context
validation. Missing, malformed, and non-object authoring context sources fail
with path-labelled source errors instead of raw parser/type failures. Focused
Agibot context source-error and happy-path tests, touched-file Ruff/format,
`git diff --check`, and ratchet passed.
Current shared-checkout ratchet summary still reports 1 unrelated Ruff
complexity row in
`scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules; the
801-line `tests/contract/maps/test_b1_map12_label_tool.py` entry rolled out of
the top-80 list after the touched Agibot contract test grew, but remains
unrelated no-touch debt.

## Next Action

Pick a fresh fail-aloud/source-truth seam from current ratchet evidence after
committing the Agibot metric-map context source-reader slice.

## Touched Areas

- `scripts/agibot/generate_metric_map_from_context.py`
- `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py`
- `scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py`
- `scripts/isaac_lab_cleanup/check_b1_map12_readiness.py`
- `scripts/isaac_lab_cleanup/check_b1_map12_asset_visual_comparison.py`
- `scripts/isaac_lab_cleanup/check_prepared_semantic_usd_summary.py`
- `scripts/isaac_lab_cleanup/compare_isaac_segmentation_aov.py`
- `scripts/isaac_lab_cleanup/summarize_isaac_aov_matrix.py`
- `scripts/maps/render_b1_scene_gaussian_topdown.py`
- `scripts/maps/render_b1_scene_topdown_diagnostic.py`
- `scripts/maps/suggest_b1_map12_manual_anchor_semantics.py`
- `scripts/maps/build_b1_map12_semantic_anchor_review_packet.py`
- `scripts/maps/build_b1_map12_semantic_projection.py`
- `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- `scripts/maps/render_b1_map12_correspondence_review.py`
- `scripts/maps/fit_b1_map12_scene_alignment.py`
- `scripts/maps/render_b1_map12_manual_alignment_overlay.py`
- `scripts/maps/normalize_semantic_map_spatial_contract.py`
- `scripts/maps/compile_b1_map12_runtime_bundle.py`
- `scripts/maps/check_robot_map12_consistency.py`
- `scripts/maps/export_bundle.py`
- `scripts/maps/promote_b1_map12_manual_draft_for_verification.py`
- `scripts/maps/promote_b1_map12_semantic_review_packet.py`
- `scripts/molmo_cleanup/run_molmo_apple2apple_test_grid.py`
- `scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py`
- `scripts/visual_grounding/check_visual_grounding_benchmark_result.py`
- `scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `scripts/visual_grounding/build_visual_grounding_corpus_from_cleanup_run.py`
- `scripts/operator_console/scene_sampler_worklist_alignment.py`
- `scripts/operator_console/run_scene_sampler_source_prep.py`
- `scripts/operator_console/run_scene_sampler_scanner_plan.py`
- `scripts/reports/write_pages_index.py`
- `scripts/reports/compare_live_report_metrics.py`
- `scripts/reports/serve_reports.py`
- `roboclaws/evals/live_artifacts.py`
- `scripts/molmo_cleanup/run_codex_cleanup_apple2apple_summary.py`
- `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py`
- `scripts/molmo_cleanup/run_molmo_planner_proof_bundle_from_requests.py`
- `scripts/molmo_cleanup/check_molmo_planner_manipulation_probe.py`
- `scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py`
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
- `scripts/molmo_cleanup/make_robot_camera_rgb_gain_profile.py`
- `scripts/molmo_cleanup/summarize_live_run.py`
- `roboclaws/maps/runtime_prior_snapshot.py`
- `roboclaws/maps/bundle.py`
- `roboclaws/maps/bundle_validation.py`
- `roboclaws/maps/project.py`
- `roboclaws/household/agibot_map_bundle.py`
- `roboclaws/household/planner_proof_attachment.py`
- `roboclaws/cli/household_agent_server.py`
- `roboclaws/household/realworld_cleanup.py`
- `roboclaws/core/json_sources.py`
- `roboclaws/household/camera_control.py`
- `roboclaws/household/ci_live_reports.py`
- `roboclaws/household/artifact_report.py`
- `roboclaws/household/report_sections_timing.py`
- `roboclaws/household/grasp_cache_generation.py`
- `roboclaws/household/grasp_generation_setup.py`
- `roboclaws/household/grasp_pose_policy_cache.py`
- `roboclaws/household/skill_scratchpad.py`
- `roboclaws/launch/goals.py`
- `roboclaws/evals/models.py`
- `roboclaws/maps/room_semantics.py`
- `tests/contract/maps/test_b1_map12_navigation_smoke_cli.py`
- `tests/contract/maps/test_b1_map12_navigation_report.py`
- `tests/contract/maps/test_b1_map12_readiness_cli.py`
- `tests/contract/maps/test_b1_map12_asset_visual_comparison.py`
- `tests/unit/molmo_cleanup/test_check_prepared_semantic_usd_summary.py`
- `tests/unit/molmo_cleanup/test_isaac_segmentation_aov_compare.py`
- `tests/contract/maps/test_b1_scene_gaussian_topdown.py`
- `tests/contract/maps/test_b1_map12_manual_anchor_semantics_cli.py`
- `tests/contract/maps/test_b1_map12_verified_alignment.py`
- `tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary_sources.py`
- `tests/contract/maps/test_b1_map12_correspondence_review_cli.py`
- `tests/contract/maps/test_b1_map12_alignment_fit_cli.py`
- `tests/contract/maps/test_b1_map12_manual_alignment_overlay_cli.py`
- `tests/contract/maps/test_cross_environment_semantic_map_parity.py`
- `tests/contract/maps/test_b1_map12_runtime_bundle.py`
- `tests/contract/maps/test_robot_map12_consistency.py`
- `tests/contract/maps/test_agibot_map_bundle_export.py`
- `tests/contract/maps/test_nav2_map_bundle_contract.py`
- `tests/unit/molmo_cleanup/test_apple2apple_test_grid.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark_checker_sources.py`
- `tests/contract/visual_grounding/test_visual_grounding_benchmark_runner_sources.py`
- `tests/contract/visual_grounding/test_visual_grounding_corpus_builder.py`
- `tests/unit/molmo_cleanup/test_codex_cleanup_apple2apple_summary.py`
- `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `tests/unit/molmo_cleanup/test_robot_camera_rgb_gain_profile.py`
- `tests/unit/molmo_cleanup/test_summarize_live_run.py`
- `tests/unit/molmo_cleanup/test_molmo_planner_proof_attachment.py`
- `tests/unit/scripts/test_run_molmo_planner_proof_bundle_from_requests.py`
- `tests/unit/scripts/test_run_molmo_planner_proof_bundle_prior_sources.py`
- `tests/contract/checkers/test_cleanup_checker_planner_proof_request_sources.py`
- `tests/contract/checkers/test_cleanup_checker_b1_manifest_sources.py`
- `tests/contract/checkers/test_cleanup_checker_run_result_sources.py`
- `tests/contract/checkers/test_cleanup_checker_scene_index_sources.py`
- `tests/contract/checkers/test_cleanup_checker_trace_sources.py`
- `tests/contract/checkers/test_planner_checker_source_readers.py`
- `tests/contract/maps/test_runtime_map_prior_snapshot.py`
- `tests/contract/maps/test_runtime_map_prior_source_loading.py`
- `tests/contract/maps/test_scene_room_semantic_overlay.py`
- `tests/contract/agibot/test_agibot_map_context_scripts.py`
- `tests/unit/core/test_json_sources.py`
- `tests/unit/molmo_cleanup/test_camera_control.py`
- `tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `tests/contract/reports/test_molmo_cleanup_artifact_report.py`
- `tests/contract/reports/test_molmo_cleanup_report_timing_sources.py`
- `tests/unit/molmo_cleanup/test_grasp_cache_generation.py`
- `tests/unit/molmo_cleanup/test_grasp_generation_setup.py`
- `tests/unit/molmo_cleanup/test_grasp_pose_policy_cache.py`
- `tests/unit/molmo_cleanup/test_skill_scratchpad_sources.py`
- `tests/unit/evals/test_eval_models.py`
- `tests/unit/operator_console/test_scene_sampler_source_prep_runner.py`
- `tests/unit/operator_console/test_scene_sampler_scanner_runner.py`
- `tests/unit/launch/test_goal_contract_sources.py`
- `tests/unit/reports/test_write_pages_index_sources.py`
- `tests/unit/reports/test_compare_live_report_metrics_sources.py`
- `tests/unit/reports/test_serve_reports_sources.py`
- `tests/unit/evals/test_live_artifacts_sources.py`
- `roboclaws/evals/regression.py`
- `tests/unit/evals/test_regression_promotion_sources.py`
- `roboclaws/evals/runner.py`
- `tests/unit/evals/test_eval_runner_sources.py`
- `roboclaws/reports/live_performance.py`
- `roboclaws/agents/live_runtime.py`
- `tests/unit/agents/test_live_runtime_sources.py`
- `roboclaws/agents/provider_timing_proxy.py`
- `tests/unit/agents/test_provider_timing_proxy.py`
- `roboclaws/operator_console/readiness.py`
- `roboclaws/operator_console/state.py`
- `roboclaws/operator_console/interactions.py`
- `roboclaws/operator_console/history.py`
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
- Do not touch unrelated B1 label/source-of-truth dirty files:
  `tests/contract/maps/test_b1_map12_label_tool.py` and
  `scripts/maps/render_b1_map12_base_label_review.py`.
- Do not touch unrelated `docs/status/active/2026-06-18-sdk-storage-targets.md`.
- Do not touch unrelated
  `docs/plans/2026-06-20-cross-environment-map-waypoint-source-of-truth.md`.
- Avoid adding to `tests/contract/maps/test_b1_map12_verified_alignment.py`
  unless also compacting local debt; it is at the 2000-line hard ceiling.
