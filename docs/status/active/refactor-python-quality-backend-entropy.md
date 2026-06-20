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

2026-06-21: Report-performance JSONL reads now route through the shared JSONL
source helper instead of a local row parser, while preserving the
`ReportPerformanceSourceError` boundary for trace, OpenAI Agents span,
Codex/Claude event, and provider-request metrics consumers. Malformed and
non-object present rows now use canonical `path:row` source wording before
report-performance metrics or comparison rows can derive confidence from
partial JSONL evidence. Focused proof passed: report-performance
trace/span/provider JSONL source tests, provider-request happy-path test,
touched-file ruff, touched-file format check, diff check, changed-code cleanup
review, and ratchet summary. Current ratchet: 0 Ruff complexity violations,
80 oversized modules in the shared checkout.

Previous slice: Codex and Claude live cleanup timing trace readers now route
present `trace.jsonl` and Codex event JSONL rows through the shared JSONL
source helper instead of duplicate local row parsers. Missing trace sidecars
remain optional, while malformed or non-object present rows keep route-labelled
source errors before live timing can derive MCP timing confidence. Focused
proof passed: Codex/Claude live timing trace-source tests, Codex event-summary
source test, touched-file ruff, touched-file format check, diff check,
changed-code cleanup review, and ratchet summary. Current ratchet: 0 Ruff
complexity violations, 80 oversized modules in the shared checkout.

Previous slice: Isaac runtime checker no longer carries the unreachable
`_trace_events_from_path` helper. Current cleanup trace and Isaac
semantic-pose trace source validation live in their dedicated checker owners,
so the stale raw JSONL reader is removed instead of hardened. Focused proof
passed: exact no-reference search, cleanup-result checker contract test, fake
Isaac backend cleanup test, touched-file ruff, touched-file format check, diff
check, changed-code cleanup review, and ratchet summary. Current ratchet: 0
Ruff complexity violations, 80 oversized modules in the shared checkout.

Previous slice: Household cleanup and Agibot map-build MCP server self-trace
readers now route `trace.jsonl` through the shared JSONL source helper.
Malformed or non-object rows now surface as server-labelled source errors at
the `done` boundary before readiness, policy trace, raw-FPV observation, or
run-result evidence can derive confidence from a partial MCP trace. Focused
cleanup and Agibot MCP server contract tests, touched-file ruff, touched-file
format checks, diff check, changed-code cleanup review, and the ratchet summary
passed. Current ratchet: 0 Ruff complexity
violations, 80 oversized modules in the shared checkout.

Previous slice: Planner manipulation probe stdout parsing now fails malformed or
non-object JSON-looking worker rows aloud instead of silently skipping them
before timeout/runtime diagnostics are attached to manipulation evidence.
Ordinary non-JSON log lines remain tolerated. Focused planner manipulation
checker tests, touched-file ruff, touched-file format checks, diff check,
changed-code cleanup review, and the ratchet summary passed. Current ratchet:
0 Ruff complexity violations, 80 oversized modules in the shared checkout.

Previous slice: Cleanup artifact-report trace JSONL reads now route through
the shared JSONL source helper instead of a local parser. Malformed or
non-object trace rows now fail with row-labelled `cleanup report trace` source
errors before stale cleanup report re-rendering can derive semantic timeline
evidence from partial trace data. Focused artifact-report contract tests,
touched-file ruff, touched-file format checks, diff check, changed-code
cleanup review, and the ratchet summary passed. Current ratchet: 0 Ruff
complexity violations, 80 oversized modules in the shared checkout.

Previous slice: RAW-FPV private-label trace JSONL reads now route through the
shared JSONL source helper instead of a local parser. Malformed or non-object
trace rows now fail with row-labelled `RAW-FPV private-label trace` source
errors before private-label generation can derive first-sweep observations
from partial trace evidence. Focused RAW-FPV perception probe tests,
touched-file ruff, touched-file format checks, diff check, changed-code
cleanup review, and the ratchet summary passed. Current ratchet: 0 Ruff
complexity violations, 80 oversized modules in the shared checkout.

Previous slice: Isaac semantic-pose checker trace JSONL reads now route through
the shared JSONL source helper instead of a local parser. Malformed or
non-object trace rows now fail with row-labelled `Isaac semantic-pose trace`
source errors before semantic-pose pick/place provenance checks can derive
confidence from partial trace evidence. Focused semantic-pose and cleanup
trace-source checker tests, touched-file ruff, touched-file format checks,
diff check, changed-code cleanup review, and the ratchet summary passed.
Current ratchet: 0 Ruff complexity violations, 80 oversized modules in the
shared checkout.

Previous slice: Agibot map-build checker trace JSONL reads now route through the
shared JSONL source helper instead of a local parser. Malformed or non-object
trace rows now fail with row-labelled `Agibot map-build trace` source errors
before public-trace privacy checks or duplicate-navigation checks can derive
confidence from partial trace evidence. Focused Agibot and cleanup trace-source
checker tests, touched-file ruff, touched-file format checks, diff check,
changed-code cleanup review, and the ratchet summary passed. Current ratchet:
0 Ruff complexity violations, 80 oversized modules in the shared checkout.

Previous slice: Isaac Lab runtime smoke checker sidecar reads now reserve
stdout-last-JSON tolerance for `--init-result` only. Explicit `--state-path`
and `--robot-views-result` artifacts route through the shared JSON-object
source helper, so prefixed log text, malformed JSON, or non-object sidecars
fail with path-labelled source errors before the checker can assemble
valid-looking state/robot-view confidence. Focused runtime-smoke checker
tests, touched-file ruff, touched-file format checks, diff check,
changed-code cleanup review, and the ratchet summary passed. Current ratchet:
0 Ruff complexity violations, 80 oversized modules in the shared checkout.

Previous slice: MolmoSpaces grasp initial-contact diagnostics now validate
explicit candidate grasp JSON in the parent before launching the child probe.
Present malformed or non-object candidate grasp files fail with path-labelled
`candidate grasp JSON` source errors, while missing candidate files keep the
existing blocked-result path and valid candidates still reach the probe.
Focused initial-contact diagnostics tests, touched-file ruff, touched-file
format checks, diff check, and the ratchet summary passed. Current ratchet:
0 Ruff complexity violations, 80 oversized modules in the shared checkout.

Previous slice: Generated-mess placement seeding now reuses the canonical
generated-mess manifest relation/index validators in both MolmoSpaces and
Isaac scenario-state helpers. Persisted or hand-built worker state with bad
manifest `relation` or `placement_index` values now fails before placement
diagnostics can default to backend-derived `inside`/loop-index values, while
non-manifest seeding keeps its backend fallback behavior. Focused
generated-mess scenario-state, existing generated-mess manifest, MolmoSpaces
worker, and Isaac worker tests, touched-file ruff, touched-file format checks,
diff check, and the ratchet summary passed. Current ratchet: 0 Ruff complexity
violations, 80 oversized modules in the shared checkout.

Previous slice: Camera-control request normalization and backend camera-view spec
builders now reject malformed explicit render-pose vectors instead of
defaulting `target`/`lookat` to origin or deriving a plausible `eye` from bad
input. Canonical eye/target requests require finite 3-number `eye`,
`target`/`lookat`, and `up` vectors; anchor-orbit requests require an explicit
finite target unless they use the narrow focus-receptacle derived-camera path;
non-object view rows now fail instead of disappearing into an empty render
request. MolmoSpaces and Isaac direct camera-spec helpers reuse the same
strict vector parser while Isaac USD-bound target derivation remains covered.
Focused camera-control, MolmoSpaces camera-view, Isaac camera-view, and
scene-camera color-profile tests, touched-file ruff, touched-file format
checks, diff check, changed-code cleanup review, and the ratchet summary
passed. Current ratchet: 0 Ruff complexity violations, 80 oversized modules in
the shared checkout.

Previous slice: Operator-console runtime inventory now surfaces successful Docker
mount-inspect output with malformed or wrong-shaped JSON as a blocking
`source_error` task instead of omitting the running container as if no
repo-relevant mount existed. Normal repo-mounted Docker containers still appear
as running inventory tasks, while Docker absence and nonzero inspect results
remain optional host-probe paths. Focused runtime-inventory tests, touched-file
ruff, touched-file format checks, diff check, changed-code cleanup review, and
the ratchet summary passed. Current ratchet: 0 Ruff complexity violations, 80
oversized modules in the shared checkout.

Previous slice: Operator-console stop handling now treats successful Docker
mount-inspect output with malformed or wrong-shaped JSON as an operator stop
source error instead of silently deciding that no task container is mounted.
Docker absence and nonzero inspect results remain optional cleanup paths, but
corrupt present mount metadata now blocks state rewrite and lock release.
Focused operator-console launcher tests, touched-file ruff, touched-file
format checks, diff check, changed-code cleanup review, and the ratchet
summary passed. Current ratchet: 0 Ruff complexity violations, 80 oversized
modules in the shared checkout.

Previous slice before that: MolmoSpaces visual backend slot capacity config now fails invalid
`ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS` and explicit `max_slots` values aloud
instead of falling back to a plausible one-slot backend. Live household launch
reports invalid slot config separately from normal slot contention, and
operator-console runtime inventory surfaces the bad config as a blocking
`source_error` task. Focused visual-slot, live-driver, and runtime-inventory
tests, touched-file ruff, touched-file format checks, diff check,
changed-code cleanup review, and the ratchet summary passed. Current ratchet:
0 Ruff complexity violations, 80 oversized modules in the shared checkout.

Previous slice before that: RAW-FPV perception probe runtime-prior loading now fails explicit
`--runtime-map-prior` paths aloud when missing, including split and equals CLI
spellings, while preserving the default missing prior as intentional no-prior
context. Focused RAW-FPV perception probe tests, touched-file ruff,
touched-file format checks, diff check, changed-code cleanup review, and the
ratchet summary passed. Current ratchet: 0 Ruff complexity violations, 80
oversized modules in the shared checkout.

Previous slice before that: OpenAI Agents model-input compaction threshold parsing now fails
booleans and non-positive values aloud across the env-backed live runtime path,
direct `model_input_compaction.min_chars` metadata, and the perf-profile
`model_input_compaction_min_chars` producer path instead of clamping invalid
values to plausible `1`/`1200` thresholds. Focused OpenAI Agents runtime/config
tests, touched-file ruff, touched-file format checks, diff check, changed-code
cleanup review, and the ratchet summary passed. Current ratchet: 0 Ruff
complexity violations, 80 oversized modules in the shared checkout.

Previous slice before that: MolmoSpaces rigid grasp-cache generation preflight now blocks
malformed, non-object, or path-less successful runtime-probe stdout instead of
reporting `python_ready=True` with blank MolmoSpaces root/assets evidence.
Focused planner task feasibility tests, touched-file ruff, touched-file format
checks, diff check, changed-code cleanup review, and the ratchet summary
passed. Current ratchet: 0 Ruff complexity violations, 80 oversized modules in
the shared checkout.

Previous committed slice before that: Scene-camera comparison MolmoSpaces source provenance now reports
installed-package `direct_url.json` metadata problems as `metadata_unavailable`
or `metadata_unreadable` instead of false `not_installed` provenance. Focused
scene-camera source tests, a nearby manifest serialization contract test,
touched-file ruff, touched-file format checks, diff check, changed-code cleanup
review, and the ratchet summary passed. Current ratchet: 0 Ruff complexity
violations, 80 oversized modules in the shared checkout.

Previous committed slice before that: Environment setup private/report metadata env parsing now fails
present malformed or non-object `ROBOCLAWS_ENVIRONMENT_SETUP_JSON` values aloud
through the shared JSON-object text helper while preserving missing/blank env as
the no-metadata default. Focused core JSON-source and environment setup boundary
tests, touched-file ruff, touched-file format checks, diff check, changed-code
cleanup review, and the ratchet summary passed. Current ratchet: 0 Ruff
complexity violations, 80 oversized modules in the shared checkout.

## Next Action

Pick a fresh fail-aloud/source-truth seam from current ratchet evidence after
committing the report-performance JSONL source consolidation. Avoid reopening
closed visual-slot config, slot-file source readers, Docker mount stop/source
handling, Docker inventory mount source handling, camera-control vectors,
generated-mess relation/index placement fields, initial-contact candidate
grasp source validation, or Isaac runtime smoke sidecar-source validation
without fresh false-green evidence. Avoid reopening Agibot map-build,
Isaac semantic-pose, RAW-FPV private-label, cleanup artifact-report trace, or
planner manipulation probe stdout-source validation unless fresh
checker/generator/report/probe evidence shows false confidence again.
Avoid reopening household cleanup or Agibot map-build MCP self-trace parsing
unless fresh live-server evidence shows corrupt present `trace.jsonl` rows can
again feed readiness/done/run-result evidence.
Avoid reopening the deleted Isaac runtime checker trace helper unless a real
caller appears; current cleanup trace and semantic-pose trace readers are
owned elsewhere.
Avoid reopening Codex/Claude live trace timing JSONL readers unless fresh
live-timing or event-summary evidence shows corrupt present JSONL rows can
again feed route timing/status confidence.
Avoid reopening report-performance JSONL source handling unless fresh
report/comparison evidence shows corrupt present trace, span, event, or
provider-request rows can again feed metrics confidence.

## Touched Areas

- `scripts/molmo_cleanup/isaac_semantic_pose_checker.py`
- `tests/contract/checkers/test_isaac_semantic_pose_checker_trace_sources.py`
- `scripts/molmo_cleanup/generate_raw_fpv_private_labels.py`
- `tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
- `roboclaws/household/artifact_report.py`
- `tests/contract/reports/test_molmo_cleanup_artifact_report.py`
- `scripts/molmo_cleanup/planner_manipulation_probe_result.py`
- `tests/contract/checkers/test_check_molmo_planner_manipulation_probe.py`
- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/household/agibot_map_build_mcp_server.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- `tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`
- `scripts/molmo_cleanup/isaac_runtime_checker.py`
- `scripts/molmo_cleanup/realworld_agibot_map_build_checker.py`
- `tests/contract/checkers/test_agibot_map_build_checker_trace_sources.py`
- `scripts/isaac_lab_cleanup/check_isaac_lab_runtime_smoke_result.py`
- `tests/unit/molmo_cleanup/test_isaac_lab_runtime_smoke_checker.py`
- `scripts/molmo_cleanup/molmospaces_worker_protocol.py`
- `scripts/molmo_cleanup/molmospaces_subprocess_worker.py`
- `scripts/agibot/capture_map_context_views.py`
- `scripts/agibot/verify_waypoints_with_pnc.py`
- `scripts/agibot/generate_metric_map_from_context.py`
- `scripts/isaac_lab_cleanup/isaac_worker_protocol.py`
- `scripts/isaac_lab_cleanup/isaac_robot_import.py`
- `scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py`
- `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py`
- `scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py`
- `scripts/isaac_lab_cleanup/check_b1_map12_readiness.py`
- `scripts/isaac_lab_cleanup/check_b1_map12_asset_visual_comparison.py`
- `scripts/isaac_lab_cleanup/check_prepared_semantic_usd_summary.py`
- `scripts/isaac_lab_cleanup/compare_isaac_segmentation_aov.py`
- `scripts/isaac_lab_cleanup/summarize_isaac_aov_matrix.py`
- `scripts/isaac_lab_cleanup/isaac_scene_camera_geometry.py`
- `scripts/isaac_lab_cleanup/isaac_scenario_builders.py`
- `scripts/isaac_lab_cleanup/install_molmospaces_usd_references.py`
- `scripts/isaac_lab_cleanup/isaac_scene_index_metadata.py`
- `scripts/isaac_lab_cleanup/prepare_molmospaces_flattened_semantic_usd.py`
- `scripts/maps/render_b1_scene_gaussian_topdown.py`
- `scripts/maps/render_b1_map12_manual_alignment_overlay.py`
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
- `scripts/molmo_cleanup/run_live_codex_agibot_map_build.py`
- `tests/unit/molmo_cleanup/test_live_codex_agibot_map_build.py`
- `scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_smoke_artifacts.py`
- `scripts/visual_grounding/check_visual_grounding_benchmark_result.py`
- `scripts/visual_grounding/run_visual_grounding_benchmark.py`
- `scripts/molmo_cleanup/run_live_codex_cleanup.py`
- `scripts/molmo_cleanup/run_live_claude_cleanup.py`
- `tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `roboclaws/reports/live_performance.py`
- `tests/unit/reports/test_live_performance.py`
- `scripts/visual_grounding/build_visual_grounding_corpus_from_cleanup_run.py`
- `scripts/operator_console/scene_sampler_worklist_alignment.py`
- `scripts/operator_console/run_scene_sampler_source_prep.py`
- `scripts/operator_console/run_scene_sampler_scanner_plan.py`
- `roboclaws/launch/scene_sampler_prefilter.py`
- `roboclaws/launch/scene_sampler_scanner.py`
- `scripts/reports/write_pages_index.py`
- `scripts/reports/compare_live_report_metrics.py`
- `scripts/reports/serve_reports.py`
- `roboclaws/evals/live_artifacts.py`
- `scripts/molmo_cleanup/run_codex_cleanup_apple2apple_summary.py`
- `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py`
- `scripts/molmo_cleanup/run_molmo_planner_proof_bundle_from_requests.py`
- `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py`
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `scripts/molmo_cleanup/robot_camera_apple2apple_materials.py`
- `roboclaws/household/grasp_initial_contact_diagnostics.py`
- `roboclaws/household/scene_camera_source_artifacts.py`
- `roboclaws/household/agibot_contract_rehearsal.py`
- `roboclaws/household/planner_proof_requests.py`
- `roboclaws/household/planner_task_feasibility.py`
- `scripts/molmo_cleanup/check_molmo_planner_manipulation_probe.py`
- `scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py`
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
- `scripts/molmo_cleanup/run_live_claude_cleanup.py`
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
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
- `roboclaws/household/subprocess_backend.py`
- `roboclaws/household/isaac_lab_backend.py`
- `roboclaws/core/json_sources.py`
- `roboclaws/household/camera_control.py`
- `roboclaws/household/ci_live_reports.py`
- `roboclaws/household/artifact_report.py`
- `roboclaws/household/report_sections_isaac.py`
- `tests/unit/molmo_cleanup/test_report_sections_isaac_sources.py`
- `roboclaws/household/scene_camera_usda_contract.py`
- `tests/unit/molmo_cleanup/test_scene_camera_usda_contract_sources.py`
- `roboclaws/household/report_sections_timing.py`
- `roboclaws/household/grasp_cache_generation.py`
- `roboclaws/household/grasp_generation_setup.py`
- `roboclaws/household/grasp_pose_policy_cache.py`
- `roboclaws/household/skill_scratchpad.py`
- `roboclaws/launch/goals.py`
- `roboclaws/evals/models.py`
- `roboclaws/maps/room_semantics.py`
- `roboclaws/household/generated_mess.py`
- `scripts/molmo_cleanup/molmospaces_scenario_state.py`
- `scripts/isaac_lab_cleanup/isaac_scenario_state.py`
- `tests/contract/maps/test_b1_map12_navigation_smoke_cli.py`
- `tests/contract/maps/test_b1_map12_navigation_report.py`
- `tests/contract/maps/test_b1_map12_readiness_cli.py`
- `tests/contract/maps/test_b1_map12_asset_visual_comparison.py`
- `tests/unit/molmo_cleanup/test_check_prepared_semantic_usd_summary.py`
- `tests/unit/molmo_cleanup/test_isaac_segmentation_aov_compare.py`
- `tests/unit/molmo_cleanup/test_isaac_scenario_builder_sources.py`
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
- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
- `tests/unit/molmo_cleanup/test_backend_state_source_readers.py`
- `tests/unit/molmo_cleanup/test_prepare_molmospaces_flattened_semantic_usd_sources.py`
- `tests/unit/molmo_cleanup/test_isaac_robot_import_sources.py`
- `tests/unit/molmo_cleanup/test_molmospaces_worker_state.py`
- `tests/unit/molmo_cleanup/test_molmospaces_usd_reference_installer.py`
- `tests/unit/core/test_json_sources.py`
- `tests/unit/molmo_cleanup/test_camera_control.py`
- `tests/unit/molmo_cleanup/test_generated_mess_scenario_state.py`
- `tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `tests/contract/reports/test_molmo_cleanup_artifact_report.py`
- `tests/contract/reports/test_molmo_cleanup_report_timing_sources.py`
- `tests/unit/molmo_cleanup/test_grasp_cache_generation.py`
- `tests/unit/molmo_cleanup/test_grasp_generation_setup.py`
- `tests/unit/molmo_cleanup/test_grasp_pose_policy_cache.py`
- `tests/unit/molmo_cleanup/test_skill_scratchpad_sources.py`
- `tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`
- `tests/unit/molmo_cleanup/test_raw_fpv_perception_probe_sources.py`
- `tests/unit/molmo_cleanup/test_robot_camera_prior_probe_sources.py`
- `tests/unit/molmo_cleanup/test_molmo_grasp_initial_contact_diagnostics.py`
- `tests/unit/molmo_cleanup/test_scene_camera_source_artifacts.py`
- `tests/unit/molmo_cleanup/test_agibot_sdk_runner_sources.py`
- `tests/unit/molmo_cleanup/test_agibot_contract_rehearsal_sources.py`
- `tests/unit/evals/test_eval_models.py`
- `tests/unit/operator_console/test_scene_sampler_source_prep_runner.py`
- `tests/unit/operator_console/test_scene_sampler_scanner_runner.py`
- `tests/unit/launch/test_scene_sampler_scanner_sources.py`
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
- `roboclaws/agents/drivers/openai_agents_model_input.py`
- `scripts/molmo_cleanup/openai_agents_perf_profile.py`
- `tests/unit/agents/test_live_runtime.py`
- `tests/unit/agents/test_live_runtime_sources.py`
- `tests/unit/agents/test_openai_agents_model_input_config.py`
- `roboclaws/agents/provider_timing_proxy.py`
- `tests/unit/agents/test_provider_timing_proxy.py`
- `roboclaws/agents/drivers/household_live.py`
- `roboclaws/household/visual_backend_slots.py`
- `tests/unit/molmo_cleanup/test_visual_backend_slots.py`
- `roboclaws/operator_console/launch_support.py`
- `roboclaws/operator_console/runtime_inventory.py`
- `tests/unit/agents/test_household_live_driver.py`
- `tests/unit/operator_console/test_runtime_inventory.py`
- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/readiness.py`
- `roboclaws/operator_console/state.py`
- `roboclaws/operator_console/interactions.py`
- `tests/unit/operator_console/test_interactions.py`
- `roboclaws/operator_console/history.py`
- `docs/plans/refactor-python-quality-backend-entropy.md`
- `docs/plans/refactor-python-quality-backend-entropy-completed.md`

## No-Touch Scope

- Do not touch unrelated dirty `just` files: `just/agent.just` and
  `just/molmo.just`.
- Do not touch unrelated operator-console dirty files:
  `roboclaws/operator_console/launcher.py`,
  `roboclaws/operator_console/server.py`,
  `roboclaws/operator_console/static/app.js`, and
  `roboclaws/operator_console/static/index.html`.
- Do not touch unrelated dirty tests:
  `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`,
  `tests/contract/dev_tools/test_task_agent_just_recipes.py`,
  `tests/contract/maps/test_b1_map12_base_navigation_map.py`,
  `tests/contract/maps/test_b1_map12_runtime_bundle.py`,
  `tests/contract/maps/test_scene_room_semantic_overlay.py`,
  `tests/unit/launch/test_environment_setup_catalog.py`, and
  `tests/contract/maps/test_b1_map12_base_navigation_sidecar.py`.
- Do not touch unrelated dirty repo-status/plan/runtime files:
  `STATUS.md`, `docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md`,
  `roboclaws/launch/catalog.py`, and
  `scripts/maps/compile_b1_map12_runtime_bundle.py`.
- Do not touch unrelated `docs/status/active/2026-06-18-sdk-storage-targets.md`.
- Do not touch unrelated
  `docs/plans/2026-06-20-cross-environment-map-waypoint-source-of-truth.md`.
- Do not touch unrelated
  `scripts/maps/augment_b1_map12_base_navigation_map.py`.
- Avoid adding to `tests/contract/maps/test_b1_map12_verified_alignment.py`
  unless also compacting local debt; it is at the 2000-line hard ceiling.
