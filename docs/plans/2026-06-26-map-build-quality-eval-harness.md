---
plan_scope: map-build-quality-eval-harness
status: DONE
created: 2026-06-26
last_reviewed: 2026-06-26
implementation_allowed: true
source:
  - user direction to make MapBuild scan richer semantic context for open-ended and cleanup tasks
  - current fixture-focused MapBuild implementation and post-fix prior-consumer evidence
related_context:
  - ARCHITECTURE.md
  - docs/human/evaluation.md
  - docs/plans/2026-06-24-map-build-panorama-consumer-experiments.md
  - docs/status/active/map-build-runtime-map-quality-contract.md
---

# MapBuild Quality Eval Harness

## Plan Ledger

- Plan status: DONE
- Session scope: map-build-quality-eval-harness
- Parent plan: docs/plans/2026-06-24-map-build-panorama-consumer-experiments.md
- Child plans: none
- Last updated: 2026-06-26
- Current slice: deterministic and focused live `map_build_consumer` proof is
  complete with fixture-observation backed anchors, grader-only simulator
  truth, checker-nonzero artifact recovery, actionability evidence from
  observed objects or target candidates, first-class live artifact regrade, and
  focused live SDK coverage for the four target profiles:
  `codex-router-responses`, `kimi-openai-chat`, `mimo-inside-openai-chat`, and
  `minimax-responses`.
- Next action: none for this MapBuild quality goal.
- Blocked on: none for deterministic quality gates or the proven focused live
  SDK cells.
- Do not touch from this session: public launch axes, Map12 field replication, live default provider routes, private fixture/scorer truth in agent inputs.

## Goal

Make `surface=household-world preset=map-build` prove two claims before it is
treated as product-complete:

1. The built Runtime Metric Map is richer and more useful than the start-of-run
   Base Metric Map while staying honest about RGB-only localization.
2. The built map measurably improves downstream open-ended and cleanup tasks.

The immediate work is the eval harness, not a new public MapBuild option.
Production and normal MapBuild still use the single agent/system default
fixture-focused strategy.

## Current State

Implemented and committed:

- one default `fixture-focused` MapBuild scan contract;
- direct-runner body-turn scan at each waypoint;
- prior-consumer fix that keeps Runtime Map Prior anchors bound to their
  snapshot waypoint;
- deterministic `map_build_consumer` proof showing richer direct-runner map
  artifacts and downstream open-ended efficiency improvement;
- grader-only simulator-truth gate for fixture category recall/precision and
  best-view waypoint correctness;
- Runtime Metric Map fixture anchors keep viewpoint/navigation pose semantics
  and bind to the fixture's best-view inspection waypoint instead of the final
  MapBuild sweep waypoint;
- thin live prior-consumer proof across four provider profiles.

Current evidence against the broader acceptance criteria:

- deterministic MapBuild quality and consumer utility pass 5/5;
- focused live OpenAI Agents SDK / `codex-router-responses` MapBuild plus
  open-ended and cleanup prior/no-prior matrix regrades 5/5 on completed live
  artifacts;
- focused live OpenAI Agents SDK / `kimi-openai-chat` MapBuild plus open-ended
  and cleanup prior/no-prior matrix passes 5/5 on completed live artifacts;
- focused live OpenAI Agents SDK / `mimo-inside-openai-chat` MapBuild plus
  open-ended and cleanup prior/no-prior matrix passes 5/5 on completed live
  artifacts;
- focused live OpenAI Agents SDK / `minimax-responses` MapBuild passes the same
  simulator-truth quality gates as the other live rows, and cleanup prior is
  `improved` against no-prior; its open-ended no-prior row failed because the
  provider returned invalid function-call argument JSON, so that cell is a
  provider/tool-call transport behavior gap rather than a MapBuild map-quality
  blocker;
- live MapBuild may produce fixture-backed target candidates without fresh
  movable `observed_objects`; this is accepted actionability evidence when
  target-candidate thresholds, simulator-truth gates, enrichment, privacy, and
  RGB-only pose-honesty gates all pass;
- completed live artifacts can be regraded through the standard eval CLI with
  `regrade_source=<existing-run-dir>`, without launching providers;
- no parked todo remains for the current MapBuild optimization goal.

## Acceptance Criteria

### A. Map Quality

The MapBuild eval must check, at minimum:

- Runtime Metric Map schema is valid and source map is not mutated.
- Private truth is absent from map artifacts exposed to agents.
- Public semantic anchor count meets a useful threshold.
- Stable fixture/surface/receptacle category coverage meets a useful threshold.
- Observed object count or target candidate count meets a useful threshold.
- No RGB-only current-run item claims `object_pose`.
- Duplicate fixture viewpoint groups are bounded by category, waypoint, and
  source observation.
- Pose semantics remain viewpoint/navigation pose unless trusted projection
  provenance exists.

Grader-only simulator-truth gate:

- use grader-only simulator truth to measure fixture category recall and
  precision;
- measure best-view waypoint correctness, not object map-frame pose, for
  RGB-only observations;
- keep private fixture/scorer truth out of MCP inputs, agent views, and public
  map artifacts.

### B. Downstream Utility

The eval harness must keep paired comparisons:

- open-ended no-prior vs fixture-focused prior;
- cleanup no-prior vs fixture-focused prior;
- same world, seed, backend, scenario setup, prompt, provider profile, and
  timeout class per pair where applicable.

Useful evidence includes:

- pass/fail outcome;
- first relevant evidence step/time;
- first actionable object discovery step/time for cleanup;
- `observe`, `adjust_camera`, `navigate_to_waypoint`, and
  `navigate_to_relative_pose` counts;
- prior-use verdict such as `stable_anchor_used`, `movable_hint_rechecked`,
  `prior_ignored`, `stale_prior_rejected`, or `unsafe_prior_use`.

## Execution Slices

1. Deterministic quality gate: DONE
   extend the existing `outcome` grader for `intent=map-build` with richer map
   quality checks and sample thresholds.
2. Baseline enrichment gate: DONE
   require Runtime Metric Map fixture/surface/receptacle enrichment over the
   Base Metric Map room/waypoint anchors.
3. Simulator-truth quality grader: DONE
   add grader-only truth matching for fixture category coverage and best-view
   waypoint correctness, without exposing object pose claims.
4. Downstream matrix: DONE for deterministic and focused
   `codex-router-responses`, `kimi-openai-chat`, `mimo-inside-openai-chat`,
   and `minimax-responses` live SDK coverage. Deterministic
   `map_build_consumer` passes 5/5. Codex, Kimi, and Mimo run or regrade 5/5
   on completed live artifacts. MiniMax passes MapBuild quality and cleanup
   utility rows, with one open-ended no-prior provider/tool-call transport
   failure.
5. Broader live coverage: DONE for the four target profile cells in this plan.
6. Live artifact reuse: DONE
   `just agent::eval ... regrade_source=<existing-run-dir>` reclassifies
   completed live artifacts through the standard eval runner without launching
   providers.

## Verification

Fast local proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_map_build_quality.py tests/unit/evals/test_eval_runner.py
just agent::eval suite=map_build_consumer budget=smoke
```

Plan-aware proof:

```bash
just agent::eval recommend plan=docs/plans/2026-06-26-map-build-quality-eval-harness.md budget=focused
just agent::eval execute plan=docs/plans/2026-06-26-map-build-quality-eval-harness.md budget=focused
```

Live proof remains opt-in and must use root repo provider/DINO env only when the
route is intentionally selected.

## Shipped Evidence

2026-06-26 deterministic quality slice:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_runner.py`
  passed.
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_map_build_quality.py tests/unit/evals/test_eval_runner.py`
  passed.
- `ruff check roboclaws/evals/runner.py roboclaws/evals/map_build_quality.py tests/unit/evals/test_eval_runner.py tests/unit/evals/test_map_build_quality.py tests/support/eval_runtime_map.py`
  passed.
- `ruff format --check roboclaws/evals/runner.py roboclaws/evals/map_build_quality.py tests/unit/evals/test_eval_runner.py tests/unit/evals/test_map_build_quality.py tests/support/eval_runtime_map.py`
  passed.
- `just agent::eval suite=map_build_consumer budget=smoke` passed 5/5 at
  `output/evals/household_world_map_build_consumer/20260626T083805/eval_results.json`.
- The MapBuild row passed with 24 public semantic anchors, 10 stable semantic
  anchor categories, 10 runtime-enrichment anchors over base room/waypoint
  anchors, 6 observed objects, 43 target candidates, 0 duplicate fixture
  viewpoint groups, and 0 RGB-only `object_pose` claims.

2026-06-26 simulator-truth and best-view waypoint slice:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_map_build_quality.py tests/unit/evals/test_eval_runner.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_map_build_fixture_anchors_keep_best_view_waypoint_binding`
  passed.
- `ruff check roboclaws/evals/runner.py roboclaws/evals/map_build_quality.py roboclaws/household/realworld_contract_projection.py roboclaws/household/realworld_runtime_map_targets.py roboclaws/household/realworld_visual_candidate_lifecycle.py tests/unit/evals/test_eval_runner.py tests/unit/evals/test_map_build_quality.py tests/support/eval_runtime_map.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
  passed.
- `ruff format --check roboclaws/evals/runner.py roboclaws/evals/map_build_quality.py roboclaws/household/realworld_contract_projection.py roboclaws/household/realworld_runtime_map_targets.py roboclaws/household/realworld_visual_candidate_lifecycle.py tests/unit/evals/test_eval_runner.py tests/unit/evals/test_map_build_quality.py tests/support/eval_runtime_map.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
  passed.
- `just agent::eval suite=map_build_consumer budget=smoke` passed 5/5 at
  `output/evals/household_world_map_build_consumer/20260626T092033/eval_results.json`.
- The MapBuild row passed with fixture category recall 1.0, precision 1.0,
  best-view waypoint accuracy 1.0, 24 public semantic anchors, 10 stable
  semantic anchor categories, 10 runtime-enrichment anchors, 6 observed
  objects, 43 target candidates, 0 duplicate fixture viewpoint groups, and 0
  RGB-only `object_pose` claims. Stable fixture anchors now distribute across
  best-view waypoints such as `room_2_inspection`, `room_3_inspection`,
  `room_4_inspection`, and `room_6_inspection` instead of all binding to the
  final sweep waypoint.
- The open-ended fridge consumer predicate now expects the fridge's corrected
  best-view waypoint, `room_2_inspection`; the fixture-focused prior row passes
  with `stable_anchor_used`.

2026-06-26 fixture-observation live grading and actionability slice:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_map_build_quality.py tests/unit/evals/test_eval_runner.py::test_map_build_consumer_suite_passes_runtime_map_prior_between_samples tests/unit/evals/test_eval_runner.py::test_map_build_eval_catches_unusable_runtime_metric_map tests/unit/evals/test_eval_runner.py::test_map_build_eval_uses_molmospaces_backend_fixture_truth_for_live_backend tests/unit/evals/test_eval_runner.py::test_map_build_eval_keeps_molmospaces_best_view_waypoint_gate tests/unit/evals/test_eval_runner.py::test_live_cleanup_eval_grades_artifacts_after_checker_nonzero_exit tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_runtime_metric_map_promotes_only_observed_fixture_viewpoints tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_map_build_fixture_anchors_keep_best_view_waypoint_binding tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_runtime_metric_map_clusters_same_view_fixture_anchors_and_keeps_view_pose_prior`
  passed.
- Focused `ruff check` and `ruff format --check` over changed eval/runtime/test
  files passed.
- `just agent::eval suite=map_build_consumer budget=smoke` passed 5/5 at
  `output/evals/household_world_map_build_consumer/20260626T132218-1487645-1782451338451468790/eval_results.json`.
- The focused live OpenAI Agents SDK / `codex-router-responses` matrix ran at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-codex-router-responses-20260626T1250/eval_results.json`
  and was regraded 5/5 through the standard eval CLI after the actionability
  gate fix at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-codex-router-responses-20260626T1250-regrade-cli/eval_results.json`.
- The live MapBuild row passed with 30 public semantic anchors, 16
  runtime-enrichment anchors, 37 target candidates, simulator fixture category
  recall 1.0, precision 1.0, best-view waypoint accuracy 1.0, and 0 RGB-only
  `object_pose` claims. The live cleanup prior row was `improved` against
  no-prior with lower search cost and `stable_anchor_used`.

2026-06-26 Kimi focused live SDK coverage:

- `just agent::eval suite=map_build_consumer budget=focused output_dir=output/eval-harness/map-build-quality-observed-fixtures/evals stamp=map-build-consumer-openai-agents-sdk-kimi-openai-chat-20260626T1345 agent_engine=openai-agents-sdk provider_profile=kimi-openai-chat live_execution=run`
  passed 5/5 at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-kimi-openai-chat-20260626T1345/eval_results.json`.
- The Kimi live MapBuild row passed with 30 public semantic anchors, 16
  runtime-enrichment anchors, 37 target candidates, simulator fixture category
  recall 1.0, precision 1.0, best-view waypoint accuracy 1.0, and 0 RGB-only
  `object_pose` claims. The row performed 7 waypoint visits, 28 observations,
  and 21 relative yaw moves, matching the fixture-focused sweep intent.
- The Kimi live cleanup prior row was `improved` against no-prior with
  `stable_anchor_used` and lower search cost: `observe` calls dropped from 21
  to 16, `adjust_camera` calls from 7 to 4, and
  `navigate_to_relative_pose` calls from 1 to 0. Both cleanup rows restored 4/5
  exact targets while semantically accepting 5/5 placements, so this cell's
  utility proof is efficiency/search-cost improvement rather than restoration
  rate improvement.

2026-06-26 Mimo and MiniMax focused live SDK coverage:

- `just agent::eval suite=map_build_consumer budget=focused output_dir=output/eval-harness/map-build-quality-observed-fixtures/evals stamp=map-build-consumer-openai-agents-sdk-mimo-inside-openai-chat-20260626T1430 agent_engine=openai-agents-sdk provider_profile=mimo-inside-openai-chat live_execution=run`
  passed 5/5 at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-mimo-inside-openai-chat-20260626T1430/eval_results.json`.
- The Mimo live MapBuild row passed with 30 public semantic anchors, 16
  runtime-enrichment anchors, 37 target candidates, simulator fixture category
  recall 1.0, precision 1.0, best-view waypoint accuracy 1.0, and 0 RGB-only
  `object_pose` claims. Mimo performed 7 waypoint visits, 28 observations, and
  21 relative yaw moves during MapBuild. Open-ended and cleanup prior rows were
  `improved` against no-prior by lower search cost and `stable_anchor_used`.
- `just agent::eval suite=map_build_consumer budget=focused output_dir=output/eval-harness/map-build-quality-observed-fixtures/evals stamp=map-build-consumer-openai-agents-sdk-minimax-responses-20260626T1500 agent_engine=openai-agents-sdk provider_profile=minimax-responses live_execution=run`
  produced a 4/5 live matrix at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-minimax-responses-20260626T1500/eval_results.json`;
  the completed artifacts were regraded at
  `output/eval-harness/map-build-quality-observed-fixtures/evals/household_world_map_build_consumer/map-build-consumer-openai-agents-sdk-minimax-responses-20260626T1500-regrade-cli/eval_results.json`.
- The MiniMax live MapBuild row passed with 30 public semantic anchors, 16
  runtime-enrichment anchors, 37 target candidates, simulator fixture category
  recall 1.0, precision 1.0, best-view waypoint accuracy 1.0, and 0 RGB-only
  `object_pose` claims. Cleanup prior was `improved` against no-prior by lower
  search cost and `stable_anchor_used`; the original open-ended no-prior row
  failed when MiniMax returned HTTP 400 for invalid function-call argument JSON.
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals/test_eval_runner.py::test_eval_runner_classifies_live_tool_argument_failures_as_agent_failures tests/unit/evals/test_eval_runner.py::test_eval_runner_classifies_live_provider_failures_as_blocked`
  passed.
- `ruff check roboclaws/evals/runner.py tests/unit/evals/test_eval_runner.py`
  passed.
- `ruff format --check roboclaws/evals/runner.py tests/unit/evals/test_eval_runner.py`
  passed.

## Remaining Work

- Parked todos for the current MapBuild optimization goal: none.
