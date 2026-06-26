# MapBuild Quality Eval Harness

Capsule status: DONE

Source plan: `docs/plans/2026-06-26-map-build-quality-eval-harness.md`

Latest user intent: create a concise TODO document for the remaining MapBuild
quality work, then continue optimizing and testing MapBuild until the map-build
optimization goal is met.

Current slice: fixture-observation backed Runtime Metric Map anchors, live
MolmoSpaces simulator-truth grading, checker-nonzero artifact recovery, the
MapBuild actionability gate, first-class live artifact regrade, and focused
four-profile SDK live evidence are implemented in the existing
`map_build_consumer` suite.

Last proven evidence:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_map_build_quality.py tests/unit/evals/test_eval_runner.py::test_map_build_consumer_suite_passes_runtime_map_prior_between_samples tests/unit/evals/test_eval_runner.py::test_map_build_eval_catches_unusable_runtime_metric_map tests/unit/evals/test_eval_runner.py::test_map_build_eval_uses_molmospaces_backend_fixture_truth_for_live_backend tests/unit/evals/test_eval_runner.py::test_map_build_eval_keeps_molmospaces_best_view_waypoint_gate tests/unit/evals/test_eval_runner.py::test_live_cleanup_eval_grades_artifacts_after_checker_nonzero_exit tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_runtime_metric_map_promotes_only_observed_fixture_viewpoints tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_map_build_fixture_anchors_keep_best_view_waypoint_binding tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_runtime_metric_map_clusters_same_view_fixture_anchors_and_keeps_view_pose_prior`
  passed.
- Focused `ruff check` and `ruff format --check` over changed eval/runtime/test
  files passed.
- `just agent::eval suite=map_build_consumer budget=smoke` passed 5/5 at
  `output/evals/household_world_map_build_consumer/20260626T132218-1487645-1782451338451468790/eval_results.json`.
  The deterministic MapBuild row passed with 24 public semantic anchors, 10
  stable semantic anchor categories, 10 runtime-enrichment anchors, 6 observed
  objects, 43 target candidates, simulator fixture category recall 1.0,
  precision 1.0, best-view waypoint accuracy 1.0, 0 duplicate fixture
  viewpoint groups, and 0 RGB-only `object_pose` claims.
- The focused live OpenAI Agents SDK / `codex-router-responses` matrix ran
  against root repo env artifacts and was locally regraded 5/5 at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-codex-router-responses-20260626T1250-regrade-cli/eval_results.json`
  through the standard `just agent::eval ... regrade_source=<run-dir>` route.
  The live MapBuild row passed with 30 public semantic anchors, 16
  runtime-enrichment anchors, 37 target candidates, simulator fixture category
  recall 1.0, precision 1.0, best-view waypoint accuracy 1.0, and 0 RGB-only
  `object_pose` claims. Live cleanup prior was `improved` against no-prior by
  lower search cost and `stable_anchor_used`.
- The focused live OpenAI Agents SDK / `kimi-openai-chat` matrix passed 5/5 at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-kimi-openai-chat-20260626T1345/eval_results.json`.
  The live MapBuild row passed with 30 public semantic anchors, 16
  runtime-enrichment anchors, 37 target candidates, simulator fixture category
  recall 1.0, precision 1.0, best-view waypoint accuracy 1.0, and 0 RGB-only
  `object_pose` claims. Kimi performed 7 waypoint visits, 28 observations, and
  21 relative yaw moves during MapBuild. Live cleanup prior was `improved`
  against no-prior by lower search cost and `stable_anchor_used`; it reduced
  cleanup `observe` calls from 21 to 16, `adjust_camera` calls from 7 to 4,
  and `navigate_to_relative_pose` calls from 1 to 0.
- The focused live OpenAI Agents SDK / `mimo-inside-openai-chat` matrix passed
  5/5 at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-mimo-inside-openai-chat-20260626T1430/eval_results.json`.
  The live MapBuild row passed with 30 public semantic anchors, 16
  runtime-enrichment anchors, 37 target candidates, simulator fixture category
  recall 1.0, precision 1.0, best-view waypoint accuracy 1.0, and 0 RGB-only
  `object_pose` claims. Mimo cleanup prior was `improved` against no-prior by
  lower search cost and `stable_anchor_used`; open-ended prior also improved
  search cost.
- The focused live OpenAI Agents SDK / `minimax-responses` matrix produced
  usable partial provider-profile evidence. The live MapBuild row passed with
  the same quality metrics as the other live rows: 30 public semantic anchors,
  16 runtime-enrichment anchors, 37 target candidates, simulator fixture
  category recall 1.0, precision 1.0, best-view waypoint accuracy 1.0, and 0
  RGB-only `object_pose` claims. Cleanup prior was `improved` against no-prior
  by lower search cost and `stable_anchor_used` after regrade at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-minimax-responses-20260626T1500-regrade-cli/eval_results.json`.
  The one failed row is open-ended no-prior; the original live status shows
  MiniMax returned HTTP 400 for invalid function-call argument JSON, so this is
  recorded as a provider/tool-call transport behavior gap, not a MapBuild map
  quality failure.
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_runner.py::test_eval_runner_classifies_live_tool_argument_failures_as_agent_failures tests/unit/evals/test_eval_runner.py::test_eval_runner_classifies_live_provider_failures_as_blocked`
  passed after tightening future live failure classification for provider
  tool-call argument JSON errors.
- `ruff check roboclaws/evals/runner.py tests/unit/evals/test_eval_runner.py`
  and
  `ruff format --check roboclaws/evals/runner.py tests/unit/evals/test_eval_runner.py`
  passed.
- The cross-profile MapBuild review report now renders the direct, Codex,
  Kimi, Mimo, and MiniMax result files at
  `output/eval-harness/map-build-quality-observed-fixtures/map-build-matrix-review/map_build_matrix_report.html`
  with machine-readable summary
  `output/eval-harness/map-build-quality-observed-fixtures/map-build-matrix-review/map_build_matrix_summary.json`.
  The summary has 5 profiles, 5 MapBuild rows, 10 downstream comparisons, 5/5
  richer-than-base MapBuild rows, 6 improved downstream pairs, 3 no-regression
  pairs, 0 regressed pairs, and keeps the MiniMax open-ended no-prior provider
  artifact failure as inconclusive.

Next proof command:

```bash
just agent::eval recommend plan=docs/plans/2026-06-26-map-build-quality-eval-harness.md budget=focused
```

Stop condition: stop before adding public scan-profile choices, exposing
private fixture/scorer truth to agents, copying Map12 fields wholesale, or
claiming RGB-only object map-frame pose.

Active next work, not parked:

- none for the current MapBuild optimization goal.

Parked work: none for the current MapBuild optimization goal. Root `TODOS.md`
remains the repo-level parking lot for unrelated queued tasks.
