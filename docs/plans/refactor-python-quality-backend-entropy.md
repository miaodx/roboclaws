---
refactor_scope: python-quality-backend-entropy
status: CONTINUE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-18
completed_ledger: docs/plans/refactor-python-quality-backend-entropy-completed.md
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

CONTINUE. Continue one verified, non-overlapping slice at a time. This file is
the unfinished active plan only. Completed work lives in
`docs/plans/refactor-python-quality-backend-entropy-completed.md`.

Planning update on 2026-06-17: the next cleanup group should prioritize
fail-aloud-and-early behavior over more silent compatibility cleanup. Silent
fallbacks that fabricate labels, choose alternate assets, hide missing source
metadata, normalize invalid launch/profile input without surfacing it, or turn
real setup failures into plausible defaults are now first-class cleanup targets.
Environment-variable cleanup belongs in the same pass: collapse duplicate env
knobs, remove stale compatibility aliases, make precedence explicit, and reject
ambiguous provider/model/key/base-url combinations instead of silently selecting
another route or developer fallback. Execute these as dedicated slices before
returning to hard-ceiling owner splits.

Planning update on 2026-06-17: unnecessary unit-test cleanup is also in scope,
but it must run through `$intuitive-tests` audit/propose before deleting tests.
The suite already has `unit` / `contract` / `integration` layers and strict
markers, so the next test cleanup should be pruning-first rather than
layout-first: remove, merge, or reclassify low-signal unit tests that assert
implementation shape, copied constants, private-call choreography, file/path
trivia, or registration metadata without caller-visible behavior.

Planning update on 2026-06-17: documentation cleanup is in scope as a bounded
parallel stream, but it must run through `$intuitive-doc` and keep the repo's
human surface small. Human-facing truth is `README.md`, `ARCHITECTURE.md`,
`STATUS.md`, and `docs/human/**`; planning logs, generated evidence,
retrospectives, active status scratchpads, and ADR detail stay as process or
evidence surfaces unless a human doc deliberately promotes them. Doc cleanup
should remove or relocate stale current-looking guidance, duplicate command
tables, historical launch/profile narratives, and implementation/proof detail
that makes humans or future agents rediscover old routes.

Implementation refresh on 2026-06-18 completed the MolmoSpaces robot-map
renderer split. `render_robot_map()` now delegates projection, frame, room
outline, focus marker, object marker, trajectory, heading, and legend drawing to
focused helpers inside `molmospaces_room_map.py`. Behavior-change class:
internal cleanup; map dimensions, colors, labels, bounds, artifact names, and
callers are unchanged. The ratchet reports 9 complexity rows and 77 oversized
modules; `scripts/molmo_cleanup/molmospaces_room_map.py` is 414 lines and no
longer appears in the complexity list.

Latest refreshed quality signal from `python
scripts/dev/check_python_quality_ratchet.py --summary --top 60` on 2026-06-18.
Treat this as the planning snapshot for the next slice; refresh before executing
again.

- Follow-up implementation refresh on 2026-06-18 aligned OpenAI Agents SDK
  performance-profile integer parsing with the fail-aloud runtime config
  contract. Malformed integer env/direct settings such as
  `ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_CANDIDATE_BUDGET`, and non-positive
  positive-only settings such as `max_turns`, now produce actionable
  `OpenAI Agents SDK setting ...` errors instead of raw conversion failures or
  terse constraint messages. Behavior-change class: fail-aloud
  runner/provider-profile configuration; valid integer defaults, matching
  CLI/env values, existing conflicts, and profile output schemas are unchanged.
  The ratchet remains 0 complexity rows and 79 oversized modules;
  `openai_agents_perf_profile.py` is 800 lines and stays below the oversized
  threshold.
- Follow-up implementation refresh on 2026-06-18 closed one metric-map
  rasterization false-green. `occupancy_grid_from_metric_map()` now requires
  declared `metric_map.width` and `metric_map.height` values to be present,
  integer, and within the existing 16..4096 projection bounds instead of
  silently fabricating the default 240x180 grid for malformed map evidence.
  Behavior-change class: fail-aloud source-map/costmap projection; valid
  metric-map projection, public launch axes, Nav2 bundle artifact schemas, and
  computed geometry expansion clamping are unchanged. The ratchet remains 0
  complexity rows and 79 oversized modules; `rasterize.py` is 268 lines.
- Follow-up implementation refresh on 2026-06-18 closed one Runtime Map Prior
  artifact false-green. `runtime_metric_map_from_prior_artifact()` now accepts
  only raw `runtime_metric_map_v1` payloads or `runtime_map_prior_snapshot_v1`
  wrappers whose nested runtime map is also `runtime_metric_map_v1`; unknown or
  malformed non-empty prior artifacts fail with a clear schema error instead of
  being treated as usable runtime-map evidence. Behavior-change class:
  fail-aloud runtime artifact/source truth; omitted prior paths, valid raw
  runtime maps, valid snapshot wrappers, public launch axes, and downstream
  Runtime Map Prior Snapshot contracts are unchanged. The ratchet remains 0
  complexity rows and 79 oversized modules; `runtime_prior_snapshot.py` is 844
  lines and remains a justified warning-band owner.
- Follow-up implementation refresh on 2026-06-18 moved OpenAI Agents SDK
  runner-side MCP client-session timeout default/env validation into
  `openai_agents_perf_profile.py`. Malformed
  `ROBOCLAWS_OPENAI_AGENTS_MCP_CLIENT_SESSION_TIMEOUT_S`, negative direct
  timeout values, and CLI/env timeout conflicts now fail through the same
  performance-profile resolver as the other SDK runtime settings instead of
  being parsed early by argparse or silently clamped to zero. Behavior-change
  class: fail-aloud runner/provider-profile configuration; default 30s timeout,
  matching CLI/env values, valid positive values, and explicit zero-as-disable
  profile output are unchanged. The ratchet remains 0 complexity rows and 79
  oversized modules; `run_live_openai_agents_cleanup.py` is down to 1972 lines.
- Follow-up implementation refresh on 2026-06-18 closed an OpenAI Agents SDK
  direct `max_turns` metadata false-green. Invalid or non-positive direct
  `max_turns` metadata now fails as a normalized `provider_config_failure`
  live-status packet instead of silently reusing the default SDK turn budget or
  clamping to one. Behavior-change class: fail-aloud SDK runtime
  configuration; omitted metadata, validated `LiveAgentRequest.max_turns`, and
  positive profile-owned `max_turns` values are unchanged. The ratchet remains
  0 complexity rows and 79 oversized modules.
- Follow-up implementation refresh on 2026-06-18 closed an OpenAI Agents SDK
  MCP client-session timeout config false-green. Invalid
  `ROBOCLAWS_OPENAI_AGENTS_MCP_CLIENT_SESSION_TIMEOUT_S` values and negative
  direct `mcp_client_session_timeout_s` metadata now fail as normalized
  `provider_config_failure` live-status packets instead of being treated as
  absent or disabled timeout configuration. Behavior-change class: fail-aloud
  SDK runtime configuration; omitted values, valid positive timeout values,
  and explicit zero-as-disable behavior are unchanged. The ratchet remains 0
  complexity rows and 79 oversized modules.
- Follow-up implementation refresh on 2026-06-18 closed an OpenAI Agents SDK
  retry config false-green. Invalid
  `ROBOCLAWS_OPENAI_AGENTS_MODEL_SERVICE_RETRY_ATTEMPTS` values and invalid
  direct `model_service_retry_sleep_s` metadata now fail as normalized
  `provider_config_failure` live-status packets instead of silently reusing
  defaults. Behavior-change class: fail-aloud SDK runtime configuration;
  omitted values, valid non-negative retry attempts/sleep values,
  profile-owned retry packets, public launch axes, event schemas, and retry
  observability are unchanged. The ratchet remains 0 complexity rows and 79
  oversized modules.
- Follow-up implementation refresh on 2026-06-18 closed an OpenAI Agents SDK
  model-input compaction config false-green. Invalid
  `ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS` values and invalid direct
  `raw_fpv_image_memory` / `camera_grounded_history` retained-count metadata now
  fail as normalized `provider_config_failure` live-status packets instead of
  silently reusing defaults or carrying malformed policy values into the model
  input filter. Behavior-change class: fail-aloud SDK runtime configuration;
  omitted values, valid defaults, profile-owned compaction packets, public
  launch axes, event schemas, and valid compaction output are unchanged. The
  ratchet remains 0 complexity rows and 79 oversized modules.
- Follow-up implementation refresh on 2026-06-18 split provider-registry CLI
  dispatch out of `_main()` into focused parser, JSON payload/write, route-text,
  and supports-engine helpers. Behavior-change class: internal cleanup; provider
  route semantics, env precedence, public profile names, command names, and model
  metadata are unchanged. The ratchet reports 8 complexity rows and 77 oversized
  modules; `provider_registry.py::_main` is cleared from the complexity list.
- Follow-up implementation refresh on 2026-06-18 split live-eval detached-route
  polling out of `wait_for_live_surface_completion()` into focused helpers for
  early completion, timeout normalization/deadline calculation, poll completion,
  and post-deadline recovery. Behavior-change class: internal cleanup; live
  surface commands, artifact discovery, timeout/grace behavior, and
  `live_status.json` semantics are unchanged. The ratchet reports 7 complexity
  rows and 77 oversized modules; `live_runtime.py::wait_for_live_surface_completion`
  is cleared from the complexity list.
- Follow-up implementation refresh on 2026-06-18 split eval-harness row blocker
  routing out of `_row_blockers()` into a requirement-priority table and a
  per-requirement blocker helper. Behavior-change class: internal cleanup;
  selected-row schema, blocker details, DINO sidecar autostart behavior,
  runtime-map-prior gating, and execution order are unchanged. The ratchet
  reports 6 complexity rows and 77 oversized modules;
  `run_eval_harness.py::_row_blockers` is cleared from the complexity list.
- Follow-up implementation refresh on 2026-06-18 split operator-console prompt
  preview goal-contract launch argument building out of `_goal_contract()` into
  focused helpers for launch axes, missing default overrides, and explicit
  overrides. Behavior-change class: internal cleanup; prompt text, launch args,
  override precedence, and `LaunchError` recovery are unchanged. The ratchet
  reports 5 complexity rows and 77 oversized modules;
  `prompt_preview.py::_goal_contract` is cleared from the complexity list.
- Follow-up implementation refresh on 2026-06-18 split semantic cleanup MCP
  registration out of `register_semantic_cleanup_tools()` into map/navigation,
  observation, visual-grounding, and target-resolution registration helpers.
  Behavior-change class: internal cleanup; public tool names, FastMCP schemas,
  dispatch handlers, and response shapes are unchanged. The ratchet reports 4
  complexity rows and 77 oversized modules;
  `realworld_mcp_semantic_tools.py::register_semantic_cleanup_tools` is cleared
  from the complexity list.
- Follow-up implementation refresh on 2026-06-18 split cleanup-checker
  fixture-id lookup out of `_candidate_fixture_id_for_object()` into local
  helpers for semantic substeps, cleanup primitive evidence, agent-view
  worklist rows, and destination options. Behavior-change class: test-only
  cleanup; checker semantics and fixture artifacts are unchanged. The ratchet
  reports 3 complexity rows and 77 oversized modules;
  `test_check_molmo_realworld_cleanup_result.py::_candidate_fixture_id_for_object`
  is cleared from the complexity list.
- Follow-up implementation refresh on 2026-06-18 split scene-sampler next-flow
  readiness assertions out of `_assert_next_flow()` into summary, artifact-path,
  source-status, and scanner-plan helper families. Behavior-change class:
  test-only cleanup; generated readiness artifact contracts are unchanged. The
  ratchet reports 2 complexity rows and 77 oversized modules;
  `test_scene_sampler_readiness_export.py::_assert_next_flow` is cleared from
  the complexity list.
- Follow-up implementation refresh on 2026-06-18 split operator-console scene
  preview asset endpoint assertions into registered-asset, PNG-response,
  JSON-response, and invalid-path helper families. Behavior-change class:
  test-only cleanup; preview asset route behavior and registered preview names
  are unchanged. The ratchet reports 1 complexity row and 77 oversized modules;
  `test_operator_console.py::test_operator_console_serves_scene_preview_assets`
  is cleared from the complexity list.
- Follow-up implementation refresh on 2026-06-18 split operator-console control
  endpoint setup, transport cases, response assertions, and persistence checks
  out of
  `test_operator_console_control_endpoint_is_allowlisted_and_records_operator_rows()`
  into focused local helpers. Behavior-change class: test-only cleanup; control
  route allowlisting, movement bounds, MCP call payload, and operator artifact
  persistence are unchanged. The ratchet reports 0 complexity rows and 77
  oversized modules; the remaining
  `test_operator_console.py::test_operator_console_control_endpoint_is_allowlisted_and_records_operator_rows`
  PLR0915 row is cleared from the complexity list.
- Follow-up implementation refresh on 2026-06-18 split scene-camera canonical
  camera geometry contracts out of `scene_camera_comparison.py` into
  `scene_camera_geometry_contract.py`. Behavior-change class: internal artifact
  construction cleanup; camera pose/intrinsics, room-scale,
  scene-frame-transform, and projection diagnostic payload schemas are
  unchanged. Dead facade aliases for already-owned USD/render/lighting helpers
  were removed instead of preserved as compatibility shims. The ratchet reports
  0 complexity rows and 77 oversized modules; `scene_camera_comparison.py` is
  down to 1999 lines and no longer a hard-ceiling P1, while the new geometry
  owner is 744 lines.
- Follow-up implementation refresh on 2026-06-18 split real-world contract
  public map/projection builders, agent-view/policy evidence packets, raw-FPV
  observation packets, visible/camera candidate materialization, generated
  inspection waypoint creation, and `navigate_to_visual_candidate()` response
  assembly into existing projection, payload, and visual-candidate lifecycle
  owners. Behavior-change class: internal owner split; public tool names,
  agent-view/runtime-map schemas, visual-candidate navigation responses, and
  private-truth guards are unchanged. Dead facade aliases for already-owned
  helpers were removed instead of preserved as compatibility shims. The ratchet
  reports 0 complexity rows and 79 oversized modules; `realworld_contract.py`
  is down to 1989 lines and no longer a hard-ceiling P1. The projection and
  visual-candidate lifecycle owners are warning-band modules at 1074 and 1188
  lines; keep them as cohesive owners unless a second real owner emerges.

- 0 Ruff complexity violations and 79 oversized modules remain.
- No active production/shared hard-ceiling P1 is known in the refreshed top-60
  ratchet snapshot. Continue only with bounded P1/P2 slices from the broader
  stop condition: fail-aloud/env cleanup, test pruning through `$intuitive-tests`,
  documentation cleanup through `$intuitive-doc`, or a fresh hard-ceiling
  regression if another production/shared file crosses 2000 lines.
- `roboclaws/household/realworld_contract.py` is down to 1989 lines and is no
  longer a hard-ceiling P1. Keep it below 2000; reopen it only if the contract
  facade starts rebuilding public map/projection packets, agent-view/policy
  evidence, observation packets, visible/camera candidate materialization,
  generated inspection waypoints, visual-candidate navigation response
  assembly, done-readiness, public manipulation/tool responses, runtime-map
  target/public-anchor packets, or visual-candidate declarations/lifecycle
  directly again.
- `roboclaws/household/scene_camera_comparison.py` is down to 1999 lines and
  is no longer a hard-ceiling P1. Keep it below 2000; reopen it only if the
  facade starts rebuilding canonical camera geometry contracts, report
  hydration/report sections, image metrics, lighting diagnostics, render-domain
  contracts, or USD contract parsing inline again.
- `roboclaws/household/report.py` is down to 1995 lines and is no longer a
  hard-ceiling P1. Keep it below 2000; reopen it only if report sections start
  rebuilding Agibot, proof-bundle, probe, map, timing, agent, or robot section
  rendering inline again.
- `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py` is down to
  1976 lines and is no longer a hard-ceiling P1. Keep it below 2000; reopen it
  only if the summarizer starts rebuilding HTML report rendering,
  object/capture-quality payload compaction, or manifest-ranking summaries
  inline again.
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` is down to 1972
  lines and is no longer a hard-ceiling P1. Keep it below 2000; reopen it only
  if runner-side profile/default/config ownership grows again.
- `roboclaws/agents/drivers/openai_agents_live.py` is 1883 lines and is
  no longer a hard-ceiling P1. Keep it below 2000; reopen it only if SDK driver
  request/session/provider orchestration grows again or rebuilds model-input or
  span compaction inline.
- `roboclaws/agents/drivers/openai_agents_model_input.py` is 972 lines and owns
  OpenAI Agents SDK model-input compaction. Keep it as a justified cohesive
  800-1200-line owner unless a second real owner emerges inside it.
- `roboclaws/household/realworld_runtime_map_targets.py` is 1009 lines. Keep
  it as a justified cohesive 800-1200-line owner only while it owns the single
  target/public-anchor concept; do not split it again just to chase line count.
- `roboclaws/household/report_sections_proof_bundle.py` is 828 lines after
  taking proof-bundle result rendering. Keep it as a justified cohesive
  800-1200-line owner for proof-bundle runner report sections; split it only if
  a second real owner emerges, not because it crossed 800 by 28 lines.
- `scripts/molmo_cleanup/planner_probe_runtime_diagnostics.py` is 474 lines and
  owns planner-probe runtime diagnostics, CUDA memory snapshots, CuRobo extension
  cache evidence, Warp compatibility, and headless renderer adapter setup.
- `scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py` is down to
  1103 lines and no longer a hard-ceiling P1. Keep it as the planner-probe
  orchestration owner for CLI/worker dispatch, subprocess command construction,
  CuRobo memory profile application, policy execution, diagnostic image capture,
  and artifact write orchestration.
- `scripts/molmo_cleanup/planner_probe_task_sampler_diagnostics.py` is 1412
  lines. This is warning-band debt, not the next default P1: keep it as the
  cohesive owner for task-sampler profile/config/binding/failure diagnostics
  unless a later scan finds a second real owner inside it.
- Backend workers remain below the hard ceiling:
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` is 1994 lines and
  `scripts/molmo_cleanup/molmospaces_subprocess_worker.py` is 1846 lines.
- The apple object-parity owner files are now below the 800-line target:
  `robot_camera_apple2apple_object_parity.py` is 689 lines,
  `robot_camera_apple2apple_rgb_evidence.py` is 402 lines, and
  `robot_camera_apple2apple_visual_state.py` is 337 lines.
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` is down to
  1803 lines after the camera-contract diagnostic owner split and is no longer
  a hard-ceiling P1. `robot_camera_apple2apple_camera_contract.py` is 626 lines
  and owns FPV/head-camera summaries, per-location camera contract diagnostics,
  FPV pose/lens deltas, compact camera metadata, robot-pose delta, Isaac robot
  import diagnostics, head-articulation diagnostics, and chase-contract
  diagnostics.
- `roboclaws/launch/scene_sampler.py` is 1941 lines and stays cleared from P1
  unless it crosses 2000 lines again or regains source-prep, candidate-profile,
  prefilter, or scanner-admission ownership drift.
- Current complexity rows are P2 unless paired with hard-ceiling work:
  the operator-console control endpoint test. It should not hide while a
  file-size slice improves, but it is not the default next P1 unless the active
  product focus changes.

Current closure snapshot:

- Completed implementation details have been compacted into
  `docs/plans/refactor-python-quality-backend-entropy-completed.md`; do not use
  old execution refreshes in this active plan as a second ledger.
- Candidate A closed boundaries: contract init/runtime-prior, Runtime Metric Map
  payloads, target/public-anchor ownership, done-readiness pending/held
  candidates, public manipulation/tool response envelopes, visual-candidate
  payload/declaration/lifecycle, camera-label producer declaration inputs,
  proof-bundle result rendering, and Agibot report section rendering. Reopen
  only with fresh facade-private or report-section drift.
- Candidate B closed boundaries: scene-camera report rendering; visual-parity
  HTML report rendering; visual-parity object/capture-quality payload summaries;
  apple Object
  Gate / Render Gate; capture-quality; material/probe primitives; native-render
  diagnostics; image-metric artifacts; object-parity audit assembly; selected
  RGB/focus evidence; visual-state contract evidence; and apple camera-contract
  diagnostics. Reopen only if the runner starts rebuilding these packets
  directly.
- Candidate C is cleared from P1 for now. The planner probe runner is below the
  hard ceiling after runtime diagnostics and task-sampler diagnostics moved to
  focused owners.
- Candidate D closed boundaries: SDK driver-side model-input compaction,
  runner-side Agent SDK performance-profile/default resolution, and sanitized
  SDK span capture. `run_live_openai_agents_cleanup.py` and
  `openai_agents_live.py` are below the hard ceiling; reopen only if the runner
  rebuilds profile/default/config packets inline again, or if the SDK driver
  request/session/provider orchestration grows again or rebuilds model-input or
  span compaction inline.

Implementation refresh on 2026-06-17 moved apple camera-contract diagnostics
from `run_robot_camera_apple2apple_comparison.py` into
`robot_camera_apple2apple_camera_contract.py`. The runner now asks the focused
owner for top-level camera contract metadata, per-location diagnostics, and
summary diagnostics, while keeping lane initialization, state reads, manifest
attachment, target selection, and render-domain orchestration. The ratchet
remains 11 complexity rows and 70 oversized modules; the apple runner is down
from 2394 to 1803 lines and no longer a hard-ceiling P1, while the new owner is
626 lines. Planning-only recheck on 2026-06-17 refreshed the same ratchet and
ponytail inputs after this dirty checkpoint. No dependency, stdlib/native, or
single stale-surface deletion outranks the hard-ceiling frontier. Next
implementation should choose the remaining P1 by fresh call-site evidence. This
older checkpoint is superseded for Candidate D by later owner splits: runner-side
Agent SDK performance-profile/default resolution and SDK sanitized span capture
are both closed. Timing/timeline summary ownership remains a separate D
follow-up only if fresh call-site evidence makes it the best frontier. Candidate
B remains active only when a current hard-ceiling facade starts rebuilding owned
scene-camera or visual-parity packets inline. Candidate A needs a new
facade-private/report ownership seam; Candidate C stays parked unless it crosses
the hard ceiling again. The remaining ponytail small cuts are P2 inputs only:
empty camera-labeler identity maps, `_task_prefix_legacy`, the reachable legacy
checker flag, and duplicated lane/workflow wording.

Implementation refresh on 2026-06-17 completed the first fail-aloud runtime
configuration slice for OpenAI Agents SDK performance-profile selection.
`--agent-sdk-perf-profile` and `ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE` now
reject conflicting values instead of silently letting CLI input override the
environment. Matching duplicate values remain valid and are surfaced as
`source=cli+environment`. Proof passed with focused OpenAI Agents perf-profile
tests, ruff, format check, py_compile, and a ratchet refresh. The refreshed
ratchet reports 14 complexity rows and 74 oversized modules; the larger totals
reflect current repository drift and this slice's regression tests, not a
closed hard-ceiling owner split. This checkpoint's recommendation to return to
Candidate D profile-owner extraction is superseded by the later completed
profile owner split below.

Implementation refresh on 2026-06-17 extended that fail-aloud rule to the
shared OpenAI Agents SDK profile setting helpers. String, integer,
positive-integer, float, and boolean SDK profile knobs now reject CLI/env
conflicts while preserving the current `just` recipe pattern where environment
values are passed through to CLI arguments with the same resolved value. This
closes the broadest known ambiguity in the Agent SDK perf-profile helper family.
The next fail-aloud cleanup should pick a new bounded fallback family by fresh
audit evidence; do not return to Candidate D runner-side profile-owner
extraction unless the runner starts rebuilding profile/default/config packets
inline again.

Implementation refresh on 2026-06-17 closed a RAW-FPV visual-labeler provider
fallback: `codex-router-responses` now requires explicit `CODEX_BASE_URL` plus
`CODEX_API_KEY` instead of silently using `https://api.openai.com/v1` when the
base URL is missing. This aligns the probe/eval route with the current Codex
router contract and keeps missing provider setup visible as a `missing_env`
status. Proof passed with focused RAW-FPV visual-labeler provider tests, ruff,
format check, py_compile, and ratchet. Continue only with new fail-aloud
families that have similarly clear false-confidence risk; otherwise select the
next P1/P2 frontier from the current closure snapshot instead of reopening the
closed Candidate D profile-owner split.

Implementation refresh on 2026-06-17 completed the Candidate D runner-side
OpenAI Agents SDK performance-profile owner split. Profile id/default
selection, environment/CLI precedence checks, SDK model settings, SDK run
config, model-input compaction profile knobs, model-racing observability,
camera-grounded composite-tool gating, robot-view capture policy, retry
settings, and context-limit validation now live in
`scripts/molmo_cleanup/openai_agents_perf_profile.py`. The live runner keeps
runner-owned skill-context loading, stable-prefix hashing, prompt rendering,
server lifecycle, continuation, timing, checker, and artifact orchestration.
Metric: `run_live_openai_agents_cleanup.py` is down to 1981 lines and no
longer a hard-ceiling P1; the new owner is 786 lines. The ratchet remains 14
complexity rows and 74 oversized modules; `openai_agents_live.py` is now 2020
lines and should be treated as fresh Candidate D driver-side P1 evidence only
after confirming request/session/provider orchestration or compaction ownership
drift. Proof passed with focused OpenAI Agents perf-profile tests, ruff,
format check, py_compile, and ratchet. Do not reopen runner-side perf-profile
ownership unless the runner starts rebuilding profile/default/config packets
inline again.

Implementation refresh on 2026-06-17 completed the next Candidate D SDK
driver owner split. Sanitized OpenAI Agents SDK span recording, span limitation
packets, span export parsing, span-name safety, MCP/tool-name extraction,
usage/model extraction, sanitized error projection, ISO duration parsing, and
span JSONL writing now live in `roboclaws/agents/drivers/openai_agents_spans.py`.
`openai_agents_live.py` keeps live run assembly, model settings, retry/racing,
provider settings, and runtime failure classification. Metric:
`openai_agents_live.py` is down to 1825 lines and no longer a hard-ceiling P1;
the new span owner is 240 lines. The ratchet remains 14 complexity rows and 74
oversized modules, now led by other production hard-ceiling files rather than
the OpenAI Agents SDK driver. Proof passed with focused OpenAI Agents
span/retry/runtime tests, ruff, format check, py_compile, and ratchet. Do not
reopen SDK span ownership unless the driver starts rebuilding sanitized span
packets or span capture limitations inline again.

Implementation refresh on 2026-06-17 completed the Candidate B visual-parity
summary owner split. HTML report rendering now lives in
`robot_camera_visual_parity_report.py`; object visual-parity audit compaction,
best-audit selection, category status summaries, native Isaac render
diagnostic compaction, capture-quality probe/settings summaries, metric scene
signatures, capture-quality probe classification, and status-count helpers now
live in `robot_camera_visual_parity_payloads.py`. The visual-parity summarizer
keeps CLI orchestration, manifest reads, gate/check assembly, probe matrix
ranking, visual-sample collection, and artifact writes. Metric:
`summarize_robot_camera_visual_parity.py` is down to 1976 lines and no longer a
hard-ceiling P1; the new report owner is 517 lines and the new payload owner is
349 lines. The ratchet remains 14 complexity rows and 74 oversized modules,
now led by `realworld_contract.py`, `scene_camera_comparison.py`, and
`report.py` among production hard-ceiling files. Proof passed with focused
visual-parity unit tests, ruff, format check, py_compile, and ratchet. Do not
reopen visual-parity summary ownership unless the summarizer starts rebuilding
report rendering or payload compaction inline again.

Implementation refresh on 2026-06-17 completed the cleanup report Agibot
section owner split. MolmoSpaces Agibot contract rehearsal rendering, Agibot SDK
runner rendering, backend-stage/public-tool mapping, and subphase status labels
now live in `report_sections_agibot.py`; `report.py` keeps the cleanup report
section sequence, shared report helpers, generic tables, state snapshots, and
HTML shell. Two stale private table/format helpers left behind by prior section
splits were removed. Metric: `report.py` is down to 1995 lines and no longer a
hard-ceiling P1; the new Agibot report-section owner is 193 lines. The ratchet
remains 14 complexity rows and 74 oversized modules, now led by
`realworld_contract.py` and `scene_camera_comparison.py` among production
hard-ceiling files. Proof passed with focused cleanup-report and MolmoSpaces
Agibot contract report tests, ruff, format check on touched files, py_compile,
and ratchet. Do not reopen cleanup-report Agibot section ownership unless
`report.py` starts rebuilding those sections inline again.

## Operating Rules

- Two-document contract: this file is the only active plan, and
  `docs/plans/refactor-python-quality-backend-entropy-completed.md` is the only
  completed ledger. Do not create a third cleanup plan or scratch log.
- Refresh `python scripts/dev/check_python_quality_ratchet.py --summary --top
  40` before selecting or completing a slice. If new plan-external drift crosses
  2000 lines, adds production/shared complexity, or regresses totals, update the
  candidates before continuing.
- Planning-only refreshes should update this active plan when they change
  selection guidance. Add ledger entries only for completed implementation
  slices or durable triage compaction, not for every re-read.
- Every slice names its `ARCHITECTURE.md` owner layer, behavior-change class,
  touched files, proof, and non-goals. One verified vertical slice beats broad
  line shaving.
- Fail-aloud rule: when required runtime/source metadata, route support,
  provider profile, environment variable, map bundle inputs, room labels,
  visual artifacts, readiness facts, or configuration precedence are missing,
  ambiguous, or inconsistent, prefer an explicit exception,
  blocked/unavailable status, or operator-visible validation error over a
  guessed default. Keep only deliberate, documented defaults that are part of a
  public contract, and make them visible in artifacts, readiness payloads, or
  provider-route diagnostics.
- Compaction rule: every 3-5 accepted slices, move completed outcomes into the
  ledger and trim this file back to unresolved decisions, current candidates,
  proof gates, and stop conditions.

- Default target: Python modules stay under 800 lines.
- Justified larger modules: 800-1200 lines may be acceptable with one cohesive
  owner and a documented reason.
- Warning band: 1200-2000 lines requires an explicit split rationale and stays
  tracked as active debt.
- Hard ceiling: non-generated, non-vendor Python files over 2000 lines are P1
  entropy candidates unless a maintainer records a narrow exception. Do not
  normalize application or test files above 2000 lines as a stable end state.
- Complexity target: production/shared code trends toward zero ratcheted Ruff
  complexity rows. Test complexity is reduced through fixture builders, data
  factories, behavior-focused split tests, and shared assertions.
- Unit-test cleanup rule: existing unit tests are not grandfathered in. Keep
  tests that prove project logic, caller-visible behavior, meaningful failure
  modes, public contracts, or known regressions; delete, merge, or reclassify
  tests that only assert static shape, duplicated constants, file names, import
  paths, private helper calls, or implementation layout.
- Line-count relief is evidence, not the goal. Prefer concept reduction:
  delete stale surfaces, merge duplicate concepts, move behavior to existing
  owners, or create a new owner only around a named ownership boundary. Preserve
  current public launch axes, artifact schemas, report claims, agent-facing
  contracts, and private/public eval boundaries unless a slice explicitly
  declares and verifies a migration.

## Current Target

Current checkpoint: pause implementation and treat the next execution as a
dedicated fail-aloud cleanup pass. Refresh the ratchet and run a targeted
silent-fallback and env-var audit before selecting code changes. The first
implementation should remove one bounded family of silent fallbacks or
ambiguous environment-variable routes and prove the new explicit
failure/blocked path with tests before returning to line-count owner splits.

Dedicated implementation prompt for the next cleanup run:

```text
Update Roboclaws to fail aloud and early instead of silently falling back. Audit
the touched area first, then choose one bounded fallback family. Remove fallback
branches that fabricate missing source truth, silently substitute legacy assets,
normalize unsupported user input without surfacing the canonical value or error,
continue after required runtime evidence is absent, or let missing/ambiguous
environment variables silently choose a provider route, model, key, base URL, or
developer-only override. Treat env-var cleanup as part of this pass: collapse
duplicate knobs, remove stale compatibility aliases, make CLI/config/env
precedence visible, and reject conflicting combinations instead of selecting a
plausible default. Preserve explicit public defaults only when they are
documented launch contracts and surfaced in diagnostics. For every removed
fallback, add or update focused tests proving the missing/invalid input now
raises a clear exception or produces an explicit blocked/unavailable
readiness/status packet. Do not combine this with hard-ceiling file splitting
unless the fallback owner is the actual reason for the split.
```

Candidate D remains a valid follow-up only with fresh evidence. The runner-side
Agent SDK performance-profile/default slice is closed; do not reopen
`_resolve_agent_sdk_perf_profile()`, profile id/default selection, profile
sub-builders, SDK model/run config payloads, provider route normalization, or
setting coercion helpers unless `run_live_openai_agents_cleanup.py` starts
rebuilding those packets inline again. Timing/latency/timeline/MCP control-plane
summaries are a separate D follow-up only if D becomes the best frontier again.
Do not move runner profile construction into the SDK driver and do not combine
profile defaults with live server lifecycle.

Candidate B remains active through `scene_camera_comparison.py` and
`summarize_robot_camera_visual_parity.py`, but the apple runner is now below the
hard ceiling. Candidate A remains active because `realworld_contract.py` and
`report.py` are still above the hard ceiling, but it needs fresh facade-private
coupling or a remaining report-section owner before selection. Candidate C is no
longer the default next P1 unless the planner probe runner crosses 2000 lines
again or the task-sampler owner reveals a second real owner with call-site
evidence.

Dedicated `$intuitive-tests` prompt for the next UT cleanup run:

```text
Audit Roboclaws unit tests for unnecessary coverage before deleting anything.
Selected mode: Audit / propose first, then Prune / consolidate after the slice
is accepted. The suite already has unit/contract/integration layers, strict
pytest markers, and auto-marking from tests/conftest.py; do not start with a
layout or marker migration. Inventory the selected domain's unit tests, map each
candidate to the behavior/contract/regression it protects, and classify it as
keep, merge, delete, or reclassify. Delete or merge tests that only assert
dataclass mechanics, copied constants, static registry/config metadata,
file/path/name trivia, import locations, private helper call choreography, or
stale implementation layout. Preserve the last meaningful proof of parser
behavior, validation, safety defaults, fail-aloud errors, public CLI/report/MCP
contracts, artifact schemas, provider route semantics, and known regressions.
Run only focused collection/tests for the accepted domain plus git diff check;
do not broaden into production refactors or unrelated test layout churn.
```

Dedicated `$intuitive-doc` prompt for the next documentation cleanup run:

```text
Audit Roboclaws documentation for stale or misplaced human-facing truth before
rewriting anything. Selected mode: Cleanup, with an audit pass first. Treat
`README.md`, `ARCHITECTURE.md`, `STATUS.md`, and `docs/human/**` as the curated
human surface. Treat `.planning/**`, `docs/plans/**`, `docs/status/active/**`,
`docs/retrospectives/**`, ADR detail, output artifacts, and generated reports as
process/evidence surfaces unless a curated human doc intentionally points there
as current truth. Find stale current-looking command examples, launch-axis or
profile names, duplicated run matrices, old OpenClaw/AI2-THOR/direct-VLM
guidance, over-detailed local harness notes, and doc-only compatibility
narratives that conflict with the active launch architecture. Classify each
candidate as keep/rewrite, move to `docs/agents/**`, move to process/history,
or remove. For any rewrite/removal, update path consumers and prove with `rg`
that old paths or stale claims are gone from the human surface. Do not edit
AGENTS.md or CLAUDE.md unless the cleanup would otherwise leave stale pointers;
route broad agent-guidance refresh through `$intuitive-init`.
```

Recommended next slice claim:

- Slice: choose one owner-boundary P1/P2 from fresh evidence. Default order after
  the latest refresh is: fail-aloud silent fallback and env-var cleanup when a
  false-green family is found; Candidate D timing/timeline summary only as a
  separate follow-up if D becomes the best frontier again; Candidate B or
  Candidate A only with new facade-private/report evidence; Candidate T unit-test
  pruning through `$intuitive-tests`; and Candidate U documentation cleanup
  through `$intuitive-doc`. Do not reopen the closed Candidate D runner-side
  Agent SDK performance-profile/default owner split without new inline ownership
  drift. Choose by fresh call-site, test-value, and doc-truth evidence, not file
  size alone.
- Owner layer: MCP Capability Contract And Tools for Candidate A; Artifacts,
  reports, and eval suites for Candidates B/C; Agent Engines And Provider
  Profiles plus Thin Runtime / Server Adapters for Candidate D and provider/env
  cleanup; Runnable Surfaces And Presets when env vars or docs are acting as
  hidden launch-axis overrides; human documentation surface for Candidate U.
- Current friction: the refreshed snapshot reports no active production/shared
  hard-ceiling P1. Candidate A's runtime-map target, public map/projection,
  policy/observation evidence, visual-candidate lifecycle, proof-bundle
  result-renderer, and Agibot report-section splits are closed. Candidate C's
  runtime diagnostics and task-sampler diagnostics owner splits are closed.
  Candidate B's apple Object Gate, capture-quality, material/probe primitives,
  native-render diagnostics, image-metric artifacts, object-parity audit
  assembly, selected RGB evidence, visual-state contract evidence,
  camera-contract diagnostics, scene-camera report/geometry, visual-parity
  report, and visual-parity payload owners are closed. Candidate D's SDK
  driver-side model-input filtering, runner-side Agent SDK
  performance-profile/default resolution, and SDK span-capture boundaries are
  closed; timing/latency/timeline helpers form a different possible owner seam
  only if fresh evidence makes them the next frontier.
- Simplification: move one remaining real responsibility to an existing or
  focused owner and update callers to that owner directly. Delete obsolete
  private wrappers when call-site scan proves they are internal. Do not replace
  private coupling with a loose parameter bag, compatibility alias pile, or new
  wrapper facade. For any future D slice, keep SDK driver internals separate from
  live server lifecycle and keep timing/timeline summaries separate from profile
  defaults.
- Behavior-change class: internal owner cleanup. Preserve SDK request behavior,
  provider route semantics, model thinking policy, MCP session behavior,
  continuation policy, event/span schemas, model-input compaction output
  schemas, live-status payloads, and public launch/profile contracts.
- Proof: focused tests matching the selected boundary, ruff on touched files,
  format check, py_compile, `git diff --check`, and ratchet summary. If a future
  slice creates or keeps a new untracked owner during planning, use `git add -N`
  before relying on the ratchet line-count output.
- Non-goals: changing artifact schema, launch axes, `camera_labeler`,
  visual-grounding contracts, map-prior semantics, target-query behavior,
  done-readiness policy, visual-candidate declaration/lifecycle ownership,
  Runtime Metric Map target/public-anchor ownership, proof-bundle result
  rendering, planner-probe runtime diagnostics ownership, planner-probe
  report-panel ownership, apple Object Gate / Render Gate classification,
  capture-quality, native-render diagnostics,
  material/probe delegates, image-metric artifacts, apple object-parity
  audit/RGB/visual-state ownership, apple camera-contract diagnostics ownership,
  OpenAI Agents model-input compaction ownership, OpenAI Agents provider
  semantics, timing/timeline summary ownership unless explicitly selected, or
  lane initialization / manifest setup without fresh duplication.

Candidate A remains valid only for a new `RealWorldCleanupContract` boundary
such as agent-view wrapper cleanup that reduces private method coupling,
runtime-map/cleanup-worklist caller migration, report-section ownership, or
another named facade-private coupling point; do not reopen visual-candidate
payload, declaration, lifecycle, camera-label producer input, tool-response,
Runtime Metric Map target/public-anchor work, or proof-bundle result rendering
without fresh drift. B1 label-tool rows are cleared; B1 preview rendering is P2
only. Ponytail small cuts are inputs when they remove stale surface, duplicate
concept, or false confidence, but they must not postpone the P1 hard-ceiling
checkpoint.

## Execution Preflight

Preflight status: REVIEWED, planning-only rechecked on 2026-06-17. Route:
`$intuitive-refactor` ratchet mode. Default execution: refresh the ratchet, run
a targeted silent-fallback/env-var audit, and select one bounded fail-aloud
cleanup family before returning to hard-ceiling owner-boundary P1s. The default
candidate order is Silent Fallback And Env-Var Cleanup, D runner-side Agent SDK
performance-profile/default resolution, D timing/timeline summary only as a
separate follow-up if D remains best, B scene-camera / visual-parity summary
ownership, then A only with fresh facade-private/report evidence.
Non-goals: broad repo cleanup, line-count shaving across many files, preserving
obsolete internal wrappers, lane initialization unless fresh drift appears,
reopening SDK model-input compaction, mixing SDK driver internals with live
runner lifecycle, mixing timing/timeline helpers into the profile/default slice,
and live/provider/simulator proof unless the chosen slice changes that route.
Re-approve if a slice would change a public launch, artifact schema, report
shape, agent-facing payload, provider behavior, event/span schema, model-input
compaction schema, private/public eval contract, or a documented public default;
do not re-approve merely to delete undocumented env aliases or hidden fallback
routes that the selected slice proves are stale.

## Active Candidates

### S: Fail-Aloud Silent Fallback And Env-Var Cleanup

Severity: P1 when a fallback can create false confidence, hide a missing source
asset, mask unsupported launch/profile input, fabricate room/map/visual
semantics, mask missing or conflicting environment-variable input, or let an
operator believe a route is ready when required evidence is absent. Severity: P2
when the fallback is local developer convenience with clear test coverage and no
user-facing claim.

Owning architecture layers depend on the selected family:
Runnable Surfaces And Presets for launch/profile normalization; Agent Engines
And Provider Profiles for provider route defaults; Thin Runtime / Server
Adapters for readiness and status packets; Backend Runtime / Environment
Primitive for simulator/map/source-asset loading; Artifacts, reports, and eval
suites for preview/report/evidence generation. Env-var cleanup usually belongs
to Agent Engines And Provider Profiles, Thin Runtime / Server Adapters, or the
public launch catalog; avoid burying route choice in ad hoc `os.environ` reads.

Audit prompts for the implementation slice:

- Search for `or {}`, `or []`, `or ""`, broad `except Exception`, broad
  `except (KeyError, TypeError, ValueError)`, `fallback`, `default`, `unknown`,
  `synthetic`, `legacy`, `missing`, `skip_existing`, `os.environ`, `getenv`,
  `ROBOCLAWS_`, `_API_KEY`, `_BASE_URL`, `_MODEL`, `provider_profile`, and
  `alias` in the target owner.
- Classify each hit as explicit public default, explicit blocked/unavailable
  status, test-only fixture convenience, or silent fallback.
- For env-var hits, classify each knob as canonical public config,
  provider-secret input, local machine convenience, or stale compatibility
  alias. Record precedence between CLI args, launch catalog defaults,
  repo-local `.env`, process env, and hardcoded defaults before changing code.
- Remove or replace only silent fallback rows in the selected family. Do not
  mechanically delete every default.
- Make failure actionable: include the missing key/path/route/capability and
  the operator or developer command that should supply it when the local pattern
  already has such vocabulary.

Good first families:

- Source map / preview inputs: do not fabricate B1 or Molmo room labels,
  semantic-map labels, or preview metadata when source manifests are missing.
- Provider route and launch profile input: accept documented aliases only when
  the resolved canonical value is surfaced; reject unsupported values instead of
  silently falling back to `codex-router-responses` or another route.
- Environment-variable route selection: collapse duplicate provider/profile
  knobs, remove stale route aliases, reject conflicting key/base-url/model
  combinations, and make missing required provider keys fail readiness before a
  live run starts.
- Runtime artifact discovery: when a report/preview claims real camera, map, or
  robot-view evidence, missing files should produce explicit unavailable status
  rather than reusing stale or semantic-map substitutes.
- Worker initialization: missing required source metadata should fail before
  state write, not create plausible placeholder room/object/receptacle state.

Allowed fallbacks:

- Public launch defaults documented in README/ARCHITECTURE/just docs, such as
  default `surface=household-world` axes.
- Canonical provider secrets and machine-local mirror/proxy env vars that are
  documented as external setup inputs, as long as missing or conflicting values
  produce explicit readiness errors instead of route substitution.
- Explicit operator-console unavailable/blocked readiness states.
- Test fixtures that intentionally omit optional fields and assert the resulting
  blocked/error behavior.
- Historical artifact readers that preserve old reports without relabeling them
  as current product proof.

Proof should include focused tests for the selected owner plus `ruff` on touched
files, `git diff --check`, and the ratchet summary. If a selected fallback is
user-facing launch, env-var, or status behavior, include a contract test proving
the message/status is visible and the old implicit route no longer starts.

Implementation refresh on 2026-06-18 closed one operator-console provider-env
false-green. `launch_support.py` now owns provider env override selection,
application, and public filtering. Readiness and `start_console_run()` resolve a
single canonical provider profile from the route/override first, force the
child environment to that same value, reject conflicting
`ROBOCLAWS_PROVIDER_PROFILE` input, and prevent ambient process or repo `.env`
provider settings from silently retargeting a selected route. Focused tests
cover conflicting canonical/env provider input, ambient provider-profile drift,
and launch-state/child-env consistency. Proof passed with focused
operator-console provider-profile tests, ruff, format check, py_compile,
`git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 closed an operator-console
provider/evidence-lane compatibility false-green. Readiness no longer swallows
`KeyError` / `ValueError` raised while enriching provider status with
evidence-lane compatibility; lookup drift now marks the provider packet
`ok=false` and blocks start through the existing `needs_provider` gate with the
agent engine, provider profile, evidence lane, and lookup error in the message.
Behavior-change class: fail-aloud readiness only; provider route semantics,
launch args, model defaults, and supported evidence-lane policy are unchanged.
Proof passed with focused operator-console provider/readiness tests, ruff,
format check, py_compile, `git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 closed an explicit model-override
false-green in provider readiness. `provider_readiness()` now rejects unknown
model ids instead of reporting `model_family=unknown` with `ok=true` when
required provider env vars are present. Omitted model input still uses the
route's documented default model. Behavior-change class: fail-aloud provider
readiness only; provider profiles, route defaults, model aliases, launch args,
and base-url/key precedence are unchanged. Proof passed with focused provider
catalog and operator-console provider/readiness tests, ruff, format check,
py_compile, `git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 extended explicit model-override
validation to the coding-agent shell helper path. `provider_registry.py` now
exposes a `model-id` lookup command, and `scripts/dev/coding_agent_env.sh`
resolves `ROBOCLAWS_CODEX_MODEL` / `ROBOCLAWS_CODE_AGENT_MODEL` through that
catalog for non-system provider routes before building Codex launcher args.
Unknown model env overrides now fail before launch config generation instead
of being passed through as plausible provider settings; known aliases such as
`minimax-highspeed` continue to normalize to their catalog model id. Behavior
change class: fail-aloud env cleanup; provider profiles, route defaults,
system Claude behavior, key/base-url precedence, and public launch axes are
unchanged. Proof passed with focused provider catalog and dev-tool shell
helper tests, ruff, format check, `bash -n`, py_compile, `git diff --check`,
and ratchet.

Implementation refresh on 2026-06-18 closed a MiMo inside readiness false-green.
`mimo-inside-openai-chat` now declares both `MIMO_BASE_URL` and `MIMO_API_KEY`
as required env keys, matching its no-default-base-url provider contract.
Provider readiness and operator-console readiness now block when only
`MIMO_API_KEY` is present instead of reporting the on-demand route startable
with an empty base URL. Behavior-change class: fail-aloud provider readiness;
provider profile ids, route default model, public launch axes, and documented
operator setup remain unchanged. Proof passed with focused provider catalog and
operator-console provider/readiness tests, ruff, format check, py_compile,
`git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 closed one Nav2 map-bundle projection
false-green. `metric_map_from_bundle()` and
`static_fixture_projection_from_bundle()` now validate the selected Nav2 bundle
before projecting map evidence, so missing `map.yaml` image metadata, missing
inspection waypoints, missing source-frame metadata, or other bundle-validation
errors no longer produce `ok=true` projected artifacts through direct callers.
Behavior-change class: fail-aloud source-map artifact projection; valid bundle
projection, public launch axes, artifact schemas, map report shape, and
product callers that already validate selected bundles are unchanged. Proof
passed with focused Nav2 map-bundle contract tests, touched-file ruff and
format check, py_compile, `git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 closed one operator-console
runtime-artifact discovery false-green. `_latest_view_assets()` now treats only
`visual_grounding/overlays/**` images as current grounding overlays; report-only
`*.bbox*`, `*.detection*`, or loose `*grounding*` images elsewhere in the run
directory no longer replace the FPV slot or appear as live grounding evidence.
Behavior-change class: fail-aloud runtime artifact/status honesty; real
visual-grounding overlays still surface as both `grounding` and FPV display
source, while report-rendered bbox evidence remains available through report
artifacts. Proof passed with focused operator-console state tests, touched-file
ruff and format check, py_compile, `git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 closed the parked operator-console
route-fixture drift that followed the provider-env slice. The operator-console
route registry now tracks the current source-aware MolmoSpaces catalog:
cleanup defaults no longer pretend legacy `molmospaces/val_0` cleanup rows are
available, disabled Claude map-build rows are generated from the console-visible
world IDs, and tests use source-aware `procthor-objaverse-val` map-build/open
task route IDs. The scene-sampler stress fixtures were regenerated from the
current readiness export: `procthor-objaverse-val` is the complete UI/eval-ready
source, `procthor-10k-val` is partial with five eval-ready rows, and the suite
now contains 15 generated samples. Proof passed with focused operator-console
tests, focused eval/model/scene-sampler tests, ruff, format check, py_compile,
`git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 closed one B1 static-preview false-green.
Static B1 / Map 12 preview generation without `--b1-camera-artifact` now always
removes stale `b1-map12-fpv.png` / `b1-map12-chase.png` files and rewrites
map/topdown-only metadata instead of carrying forward a previous Isaac runtime
camera artifact. Fresh Isaac camera preview promotion remains explicit through
`--b1-camera-artifact`. Proof passed with focused operator-console preview
tests, ruff, format check, py_compile, `git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 closed the adjacent B1 camera-artifact
skip-cache false-green. `--skip-existing --b1-camera-artifact <path>` now
skips only when existing metadata records real Isaac camera previews from that
same artifact path; stale previews from another artifact are regenerated from
the requested artifact instead of being treated as current. Proof passed with
focused operator-console preview tests, ruff, format check, py_compile,
`git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 split B1 preview cache/stale policy out of
`render_b1_map12_preview()`. The renderer now delegates stale camera-preview
deletion and `--skip-existing` eligibility to focused helpers, while keeping
runtime bundle compilation, static map/topdown rendering, and camera promotion
in the main renderer. Behavior is unchanged; the C901 row for
`render_b1_map12_preview()` is cleared. Proof passed with focused
operator-console preview/static tests, ruff, format check, py_compile,
`git diff --check`, and ratchet.

Implementation refresh on 2026-06-18 split B1 camera preview candidate
evaluation out of `_promote_b1_camera_previews()`. Candidate discovery,
provenance rejection, missing-view diagnostics, quality rejection, accepted
score calculation, and evaluated-candidate payloads now live in focused helpers;
the promotion function keeps artifact readability, highest-score selection,
image writes, and promoted metadata assembly. Behavior is unchanged and the B1
preview PLR0915 row is cleared. Proof passed with focused operator-console
preview/static tests, ruff, format check, py_compile, `git diff --check`, and
ratchet.

### T: Unnecessary Unit-Test Pruning

Severity: P2 by default; P1 only when tests create false confidence for a public
route, block safe refactors through private implementation coupling, or preserve
obsolete behavior that conflicts with the current launch/profile/MCP contract.
Route through `$intuitive-tests`, selected mode Audit / propose before any
deletion. Current inventory: `tests/` already uses layer-first folders, strict
pytest markers, and auto-marking; the next slice should be pruning-first or
fixture/factory-first, not marker-first or layout-first.

Owning architecture layer depends on the selected test domain. Unit tests should
prove behavior in the code owner they exercise. Contract tests should remain
only for public schemas, CLI/recipe shapes, MCP tools, reports, replay/artifact
compatibility, provider route contracts, and documented compatibility promises.

Audit prompts for the implementation slice:

- Pick one domain first, for example provider/env route tests, operator-console
  tests, eval-harness tests, Molmo cleanup worker tests, or report tests. Do not
  prune the whole suite in one pass.
- For each candidate unit test, answer: would a real project bug fail it; would
  a harmless refactor fail it; is it already covered by a stronger behavior,
  contract, or regression test; and does it protect a public API/artifact or only
  implementation shape?
- Classify each candidate as keep, merge, delete, or reclassify. Do not delete
  the last proof of parsing, validation, state transition, fail-aloud behavior,
  safety default, artifact schema, public command, provider route semantics, or
  known regression.
- Delete tests that only assert dataclass field storage, copied constants,
  import paths, module locations, file existence, directory listings,
  registration-table membership, decorator/marker presence, mocked private calls
  without user-visible effect, or stale private helper layout.
- Merge one-field-at-a-time tests into behavior tests when that improves
  diagnosis and keeps the public behavior obvious.
- Reclassify file/artifact/CLI/recipe checks as contract tests only when the
  runtime, packaging, public docs, or artifact compatibility actually depends on
  them.

Good first families:

- Provider/env tests that duplicate constants or assert route tables without
  exercising canonical resolution, readiness failure, or visible diagnostics.
- Operator-console tests that assert static DOM/route wiring without exercising
  launch readiness, redaction, locks, status transitions, or artifact links.
- Eval-harness selector/model tests that duplicate manifest keys one field at a
  time instead of proving selected rows, blockers, promotion packets, or result
  contracts.
- Molmo cleanup worker/report tests that assert helper shape, static file names,
  or copied fixture metadata already covered by contract/report tests.

Proof should include `git diff --check`, focused collection for the selected
test domain, and the smallest behavior/contract test command that proves the
remaining coverage. Use `./scripts/dev/run_pytest_standalone.sh <tests> -q`.
Report kept/merged/deleted/reclassified counts in the slice summary. Do not
claim product behavior proof from pruning tests alone.

### U: Human Documentation Surface Cleanup

Severity: P2 by default; P1 only when human-facing docs create false confidence
for a public route, advertise retired launch/profile/provider paths as current,
hide current blockers, or make agent/human startup follow stale setup commands.
Route through `$intuitive-doc`, selected mode Cleanup with an audit pass first.
This is documentation cleanup, not a third cleanup plan: record the accepted
slice and completed result in this plan/ledger pair only.

Human-authoritative scope:

- `README.md` for project orientation and what can be run now.
- `ARCHITECTURE.md` for current layers, contracts, extension points, and proof
  boundaries.
- `STATUS.md` for current focus, next action, blockers, and current source
  links.
- `docs/human/**` for human runbooks and detail that would bloat root docs.

Evidence/process scope:

- `.planning/**`, `docs/plans/**`, `docs/status/active/**`,
  `docs/retrospectives/**`, ADR detail, `output/**`, generated reports, and
  screenshots are evidence or process unless intentionally linked as current
  truth from the human surface.
- `AGENTS.md` and `CLAUDE.md` are agent-operational pointers. Update them only
  when a doc cleanup would otherwise leave stale links or conflicts; route broad
  agent guidance cleanup through `$intuitive-init`.

Audit prompts for the implementation slice:

- Inventory the curated human surface and classify linked docs as
  human-authoritative, agent-operational, process/evidence, or historical.
- Search for stale current-looking commands and names: `task::run`,
  one-axis cleanup `profile=...`, old `molmo::cleanup` public surfaces,
  retired AI2-THOR/direct-VLM/Genesis/OpenClaw-as-public wording, old
  `minimal`/`rich` map-mode guidance, and duplicated run matrices.
- Search for process leakage in human docs: phase logs, proof-output tables,
  raw implementation checklists, generated reports, old local run transcripts,
  and long harness notes that belong in `docs/agents/**`, `docs/plans/**`,
  `docs/retrospectives/**`, or `docs/status/active/**`.
- Classify each candidate as keep/rewrite, move to `docs/agents/**`, move to
  process/history/evidence, or remove.
- Preserve current public launch axes, provider/runtime guardrails, artifact
  contracts, privacy boundaries, and active blockers. Prefer deleting stale
  compatibility narratives over relabeling them as current.

Good first families:

- Human docs that still show historical command grammar, profile names, or
  retired route names as copyable current commands.
- `docs/human/**` pages that duplicate README/ARCHITECTURE/STATUS tables but
  lag behind the active launch architecture.
- Agent-only local harness or skill routing notes that have leaked into
  human-facing docs and should move to `docs/agents/**`.
- Old proof/evidence detail in human docs where a short current-truth summary
  plus a link to process/evidence is enough.

Proof should include `git diff --check`, `rg` searches for removed stale claims
or paths across the curated human surface and known consumers, plus any focused
command/test validation for runbook commands changed by the slice. For docs-only
cleanup, do not run product tests unless a runbook command or generated-doc
contract changed. Report kept/rewritten/moved/removed counts and list any
human docs intentionally left unchanged.

### A: Contract And Report Hard-Ceiling Split

Status: cleared from hard-ceiling P1 for now. `realworld_contract.py` is 1989
lines and `report.py` is 1995 lines. Owning architecture layers: MCP Capability
Contract And Tools plus Artifacts, reports, and eval suites.
Public map/projection construction now belongs to
`realworld_contract_projection.py`; reopen it only if the contract facade
starts rebuilding Base Navigation Map, bundle metric-map, static fixture
projection, minimal static projection, fallback map template, generated
exploration candidate visited-state, or scene-index projection overlay payloads
inline again. Agent-view and policy evidence packets now belong to
`realworld_contract_payloads.py`; reopen them only if the contract facade starts
rebuilding top-level agent-view payloads, visible detection sanitization,
camera-model policy summaries, model-declared observation evidence, raw-FPV
observation packets, or inspection observation summaries inline again.
Done-readiness pending/held cleanup candidate derivation now belongs to
`realworld_done_readiness.py`; reopen it only if the contract facade starts
rebuilding pending candidates, held candidates, destination options, or private
wrapper aliases again. Public manipulation/tool response envelopes now belong
to `realworld_tool_responses.py`; reopen them only if the contract facade starts
rebuilding pick/place/open/close success/error payloads, fixture response ids,
or semantic-order error envelopes inline. Candidate A remains P1 only for a
fresh hard-ceiling regression or direct facade-private/report ownership drift.
Do not reopen init projection/runtime-prior, public map/projection, top-level
agent-view/policy evidence, Runtime Metric Map payload, Runtime Metric Map
target/public-anchor ownership, visual-candidate payload/event/overlay,
visual-candidate declaration orchestration, visual-candidate registration,
resolution, visible/camera candidate materialization, generated inspection
waypoint creation, visual-candidate navigation response assembly, camera-label
producer input construction, or planner-probe report-panel slices without fresh
drift.
Visual-candidate lifecycle now belongs to
`realworld_visual_candidate_lifecycle.py`; reopen it only if the contract facade
starts rebuilding normalization, match resolution, declaration payloads,
resolved/unresolved detection materialization, visible/camera candidate
materialization, generated inspection waypoint creation, visual-candidate
navigation response assembly, visual-evidence error payloads, or handle
actionability directly. Camera-label producer inputs now belong to
`realworld_visual_candidate_declarations.py`; reopen them only if the contract
facade starts rebuilding simulated declaration input rows, visual-grounding
requests, producer failure envelopes, model-declared observation events, or
registration wrapper aliases directly. `RealWorldPayloadContract` and
`DoneReadinessContract` are ponytail inputs only when a slice removes
facade-private coupling; replacing an alias pile with a looser parameter bag,
all-purpose context object, or new wrapper facade is not a win.

Runtime Metric Map target/public-anchor construction now belongs to
`realworld_runtime_map_targets.py`. Reopen it only if the contract facade starts
rebuilding target candidates, public semantic anchors, fixture-reference or
anchor-id mapping, target-search summaries, minimal-map target-fixture
resolution, waypoint anchor seeding, or runtime-anchor target resolution
directly. The new owner is 1009 lines; keep it as a cohesive justified module
unless a later scan finds a second real owner inside it. Same-boundary ponytail
closeout cut the unused `_recommended_place_tool` alias in that owner and the
now-unused `TARGET_SEARCH_SUMMARY_SCHEMA` constant in `realworld_contract.py`.

Proof-bundle result rendering now belongs to `report_sections_proof_bundle.py`.
Reopen it only if `report.py` starts rebuilding proof-bundle result summaries,
proof-quality summary rows, grasp-feasibility signature tables, proof result
cards, or proof-result view figures directly. The owner is 828 lines, a
justified cohesive proof-bundle runner report module below the 1200-line
warning ceiling.

### B: Visual Comparison Pipeline Split

Severity: P1 for `roboclaws/household/scene_camera_comparison.py` and
`scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`; warning-band
debt for `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
after the camera-contract split. Owning architecture layer: Artifacts, reports,
and eval suites, with Backend Runtime / Environment Primitive details staying
behind the existing MuJoCo/Isaac capture workers. Scene-camera HTML report
rendering now belongs to `scene_camera_report*.py`, and the public
`render_scene_camera_comparison_report` entry point is preserved in
`scene_camera_comparison.py`. Do not reopen report rendering unless the
comparison facade starts rebuilding report sections directly again.

Apple image-metric artifact preparation and residual diagnostics now belong to
`robot_camera_apple2apple_image_metrics.py`, with generic pixel visual metrics
reused from `scene_camera_image_metrics.py`. Do not recreate runner-private
helpers for saved-report image derivation, metric-image path/downsample
construction, image diff payload assembly, residual diagnostic math, or
residual triage summaries. `_location_result` should remain runner
orchestration that delegates image-artifact/diff subpayloads only.

Apple object parity audit construction now belongs to
`robot_camera_apple2apple_object_parity.py`, selected-target RGB/focus and
nonblank/crop evidence belongs to `robot_camera_apple2apple_rgb_evidence.py`,
and visual-state contract evidence plus visual/physics-sensitive target ids
belong to `robot_camera_apple2apple_visual_state.py`. Keep Object Gate / Render
Gate classification in `robot_camera_apple2apple_object_gate.py`, keep report
rendering in `robot_camera_apple2apple_report.py`, and keep the runner
responsible for orchestration, reading state artifacts, attaching
top-level/summary manifest fields, and invoking gate diagnostics. Reopen this
boundary only if the runner starts rebuilding those audit packets, RGB evidence
packets, visual-state contracts, or helper aliases directly.

Apple camera-contract diagnostics now belong to
`robot_camera_apple2apple_camera_contract.py`; reopen only if the runner starts
rebuilding top-level camera contract metadata, per-location camera contract
diagnostics, FPV pose/lens delta summaries, compact camera metadata,
robot-pose delta, Isaac robot import diagnostics, head-articulation diagnostics,
or chase-contract diagnostics directly. Other candidate-B slices are valid only
around fresh real boundaries such as duplicated capture-lane initialization, new
render contract diagnostics drift, scene-camera comparison ownership, or
visual-parity summary reporting. Capture-lane initialization remains parked as
runner orchestration unless it grows duplicated lane setup or a canonical
generated-mess owner emerges. The
runner-private material/probe delegate surface has been removed; do not recreate
`_probe_manifest_summary`,
`_comparison_probe_comparable`, `_comparison_probe_delta`,
`_material_response_probe_history`, `_tone_color_probe_history`,
`_texture_colorspace_material_response_check`,
`_texture_material_target_summary`, `_path_basenames`,
`_usd_preview_surface_material_model_check`, or
`_preview_surface_target_summary` as compatibility aliases. Keep
`_tone_color_response_check` in the runner for now because it still combines
residual triage, native color settings, and report-domain interpretation.
Light/shadow probe history remains runner/render-domain-owned while sharing
material-owner probe primitives directly. Native Isaac render diagnostics now
belong to `robot_camera_apple2apple_native_render.py`; do not reopen it unless
the runner starts rebuilding native diagnostics candidate selection, native
setting-group compaction, native-status interpretation, or native summary
payloads directly. Real renderer claims still require separate local proof. The
Object Gate / Render Gate diagnostic packet owner is now
`robot_camera_apple2apple_object_gate.py`, and report-renderer tests call
`robot_camera_apple2apple_report.py` directly; do not reopen those runner
facade aliases without fresh drift. Continue the apple runner only when the
selected boundary is not already owned by
`robot_camera_apple2apple_object_gate.py` or
`robot_camera_apple2apple_report.py`. For
`summarize_robot_camera_visual_parity.py`, prefer a report/gate summary owner
over splitting by helper count; do not duplicate Object Gate, Render Gate, or
capture-quality interpretation that already has focused owners.

### C: Planner Manipulation Probe Runner Split

Status: cleared from P1 for now. `scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py`
is 1103 lines after the runtime and task-sampler owner splits. Owning
architecture layer: Artifacts, reports, and eval suites, with Backend Runtime /
Environment Primitive details behind the MolmoSpaces worker and planner runtime
imports. Runtime module/version discovery, torch/CUDA diagnostics, CUDA memory
snapshots, CuRobo extension-cache packets, Warp compatibility, and headless
renderer adapter setup belong to `planner_probe_runtime_diagnostics.py`.
Task-sampler robot-placement profiles, exact cleanup task config/binding,
sampler failure diagnostics, placement scene/grasp/candidate diagnostics,
diagnostic JSON coercion, sampled task binding, requested cleanup primitive
binding, and cleanup binding promotion belong to
`planner_probe_task_sampler_diagnostics.py`. Reopen Candidate C as P1 only if
the runner crosses 2000 lines again or starts rebuilding either owner directly.
The new task-sampler owner is 1412 lines; split it only if a second real owner
emerges, not for line count alone.

Behavior-change class is internal artifact-construction cleanup unless the slice
changes probe CLI flags, result schema, report claims, or checker semantics.
Proof should include the focused planner probe checker/unit tests that cover the
selected owner, plus ruff, format check, py_compile, and ratchet.

### D: OpenAI Agents Live Runtime / Runner Split

Severity: P1 for the runner only after the model-input slice.
`roboclaws/agents/drivers/openai_agents_live.py` is 1994 lines and
`scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` is 2711 lines.
Owning architecture layers: Agent Engines And Provider Profiles for SDK request,
model settings, retry, input compaction, camera-grounded history, model racing,
and span/event artifacts; Thin Runtime / Server Adapters for live server
ownership, lease/status/timing, continuation attempts, checker invocation, and
live-run metrics attachment.

Default D slice candidates should preserve the runtime/runner boundary instead
of creating another catch-all module. Model-input compaction plus
raw-FPV/camera-grounded history policy and metrics now belongs to
`openai_agents_model_input.py`; reopen only if the SDK driver starts rebuilding
that owner directly.

The runner-owned Agent SDK performance profile/default owner is closed.
`resolve_agent_sdk_perf_profile()`, profile id/default selection, profile
sub-builders, SDK settings/run-config helpers, and setting coercion helpers now
live in `scripts/molmo_cleanup/openai_agents_perf_profile.py`; tests import the
resolver from that owner directly instead of keeping runner-private aliases.
Preserve the profile payload schema, default values, env/CLI override behavior,
provider route normalization, wire API selection, and model thinking policy.
Reopen only if the runner starts rebuilding profile/default/config packets
inline again.

Timing/latency/timeline ownership is a separate D follow-up, not part of the
profile slice. If selected later, it should move `_runner_timing_breakdown()`,
`_live_timing_timeline()`, timeline segment builders, latency attribution, MCP
trace/control-plane timing, unattributed-model seconds, and compact metric
groups to a timing owner while preserving the `live_timing.json` shape.
Possible later SDK-driver D moves remain model-service retry/model-racing
observability or span recorder/event sanitization from the SDK driver. Do not
mix SDK driver internals with runner lifecycle in one new owner, and do not
change provider route semantics, model thinking policy, MCP session behavior,
continuation policy, checker gates, event/span schemas, model-input compaction
schemas, live-status payloads, or timing artifact schemas unless explicitly
approved.

Behavior-change class is internal owner cleanup unless the selected slice
changes provider behavior, event/span schemas, status artifacts, prompt/profile
contracts, or live-run retry semantics. Proof should include focused OpenAI
Agents driver/runner tests for the chosen owner, static checks, py_compile, and
ratchet. Live provider proof is not required for an internal split and must not
be claimed without an explicit local run.

### E-H: P2 Rows And Small Cuts

- Live runtime / eval harness: P1 only for hard-ceiling runner work. Current P2
  rows are `roboclaws/evals/live_runtime.py::wait_for_live_surface_completion`
  and `skills/eval-harness/scripts/run_eval_harness.py::_row_blockers`.
- B1 preview: current row is
  `scripts/operator_console/render_scene_previews.py::render_b1_map12_preview`.
  Keep this to preview rendering; runtime-bundle and label-tool validation rows
  are cleared.
- Behavior tests: the operator-console control endpoint test remains P2
  fixture-builder work. Cleanup-checker fixture lookup, scene-sampler next-flow
  assertions, and scene-preview endpoint assertions are cleared. Do not split
  large tests only for line count.
- MCP/prompt: `realworld_mcp_semantic_tools.py::register_semantic_cleanup_tools`
  and `prompt_preview.py::_goal_contract` are cleared. Reopen only if MCP
  semantic registration or prompt-preview goal-contract helpers regain direct
  capability groups or launch-argument assembly complexity.
- Stale small cuts: legacy checker flag
  `--require-canonical-robot-view-camera-control`, empty camera-labeler maps,
  `_task_prefix_legacy`, duplicated lane prose, and `hybrid-phase-pipeline`
  guidance wording. These are P2 or L0 inputs, not standalone default work while
  P1 hard-ceiling seams remain. They also do not justify deleting
  `camera_labeler`, visual-grounding artifact contracts, service plumbing, or
  public launch aliases. Current triage: the camera-labeler maps in
  `roboclaws/household/profiles.py` are confirmed zero-entry identity maps; a
  future cut should remove only the maps/get-indirection while keeping
  normalization, validation, and public `camera_labeler` /
  `visual_grounding_pipeline_id` semantics plus contract profile tests. The
  `_task_prefix_legacy` shim has no in-repo call sites and can be deleted with
  prompt static proof plus focused prompt tests. The checker flag is still a
  reachable parser/docs alias for `--require-robot-head-camera-fpv`, so it needs
  a checker-contract migration rather than an opportunistic delete. The
  guidance wording is docs-only startup friction; known evidence includes a
  duplicated `world-public-labels` entry in
  `docs/human/molmospaces-cleanup-mode-architecture.md`, but keep that L0
  unless paired with a human-doc cleanup slice. Latest ponytail recheck on
  2026-06-17 found no `pyproject.toml` dependency removal or stdlib/native
  replacement that outranks the current P1 frontier; the core dependency set is
  small and heavy runtime packages are route-scoped extras.

### Cleared Or Parked

- Backend worker hard-ceiling split is cleared as of 2026-06-17; reopen only if
  `isaac_lab_backend_worker.py` or `molmospaces_subprocess_worker.py` crosses
  2000 lines again.
- Scene-sampler hard-ceiling drift is cleared as of 2026-06-17. Reopen as P1
  only if `scene_sampler.py` crosses 2000 lines again or if its facade starts
  re-owning source-prep, candidate-profile, prefilter, or scanner-admission
  internals instead of delegating to named owner modules.
- The following completed owner splits stay closed unless they regain direct
  owner drift: Runtime Metric Map payloads in `realworld_runtime_map_contract.py`;
  init projection/runtime-prior owner calls; visual-candidate payload/event/
  overlay assembly in `realworld_visual_candidates.py`; visual-candidate
  declaration orchestration in `realworld_visual_candidate_declarations.py`;
  visual-candidate registration/resolution lifecycle in
  `realworld_visual_candidate_lifecycle.py`; planner-probe report panels in
  `report_sections_probe_runtime.py`, `report_sections_probe.py`, and
  `report_sections_probe_failures.py`; apple Object Gate / Render Gate
  diagnostics in
  `robot_camera_apple2apple_object_gate.py`; apple capture-quality probe
  configuration in `robot_camera_apple2apple_capture_quality.py`;
  apple image-metric artifact preparation and residual diagnostics in
  `robot_camera_apple2apple_image_metrics.py`;
  scene-camera USD render-contract,
  image metric, lighting/tone/shadow, render-domain, and render-source
  diagnostics in focused scene-camera modules; B1 runtime-bundle and label-tool
  validation helper families; MolmoSpaces robot-map projection, room, focus,
  object, trajectory, heading, and legend drawing helpers in
  `molmospaces_room_map.py`; provider-registry CLI parser, JSON output,
  route-text, and supports-engine dispatch helpers in `provider_registry.py`;
  live-eval detached-route early-completion, timeout, poll-completion, and
  post-deadline recovery helpers in `live_runtime.py`; eval-harness requirement
  priority and per-requirement blocker helpers in `run_eval_harness.py`;
  operator-console prompt-preview goal-contract launch-argument helpers in
  `prompt_preview.py`; semantic cleanup MCP map/navigation, observation,
  visual-grounding, and target-resolution registration helpers in
  `realworld_mcp_semantic_tools.py`.
- Parked unless a matching product slice needs them: `agibot_contract_rehearsal.py`
  below-ceiling cleanup, report-performance skill wrapper consolidation,
  `PhysicalObservationProvider`, scene-sampler public alias removal, and broad
  behavior-test pruning.

## Evidence Ladder

- Static: `ruff check <touched files>`, `ruff format --check <touched files>`,
  and `python scripts/dev/check_python_quality_ratchet.py`.
- If a future slice creates a new untracked Python owner, include it in the
  ratchet input with `git add -N <path>` before using the ratchet summary as
  size proof; otherwise untracked owners are invisible to `git ls-files`.
- Docs-only planning refresh: `git diff --check` plus the ratchet summary used
  for selection is enough; do not run behavior tests when no code or contracts
  changed.
- Focused tests: use `./scripts/dev/run_pytest_standalone.sh <tests> -q`.
- Contract/report changes: include the relevant contract or report tests.
- Fail-aloud cleanup changes: include at least one regression test where the
  old path would silently fabricate or substitute data, and the new path raises
  a clear error or returns an explicit blocked/unavailable packet.
- Unit-test pruning changes: run focused collection and the selected domain's
  remaining behavior/contract tests; include a short keep/merge/delete/
  reclassify report. Deleting tests is not proof that behavior still works.
- Documentation cleanup changes: use `$intuitive-doc` audit/cleanup rules,
  verify stale claims and path consumers with `rg`, and run command/doc build
  checks only when the changed human runbook makes testable command claims.
  Report kept/rewritten/moved/removed counts. Do not claim code behavior proof
  from docs-only cleanup.
- Changed-code review: after implementation, run `$intuitive-refactor`
  changed-code review on the changed scope before final verification when the
  slice is not docs-only.
- Agent-facing/eval/launch changes: prefer `just agent::eval recommend` or
  `just agent::eval execute` for gate selection instead of hand-writing a fixed
  eval list.
- Simulator/live claims: only claim them after an explicit local run on a ready
  environment.

## Stop Condition

Stop this cleanup stream when:

- Non-generated, non-vendor files above 2000 lines are either split below the
  ceiling or have a recorded narrow exception.
- Production/shared Ruff complexity rows are at or near zero.
- Remaining test complexity is fixture-builder debt with clear ownership, not
  one-off long test bodies.
- Low-signal unit tests in the accepted domains have been deleted, merged, or
  reclassified, and the remaining unit tests protect behavior/failure modes
  rather than static implementation shape.
- Backend id, runtime metadata, artifacts, and evidence attachments use common
  surfaces instead of repeated concrete-class or `backend == ...` branching.
- Silent fallback families that can create false confidence are either removed,
  converted to explicit blocked/unavailable status, or documented as deliberate
  public defaults with tests.
- Env-var families no longer provide hidden route compatibility: canonical
  knobs are documented, duplicate aliases are removed or explicitly blocked,
  precedence is tested, and missing/conflicting provider keys, base URLs, or
  model/profile settings fail before launch readiness.
- The curated human documentation surface is small and current: README,
  ARCHITECTURE, STATUS, and `docs/human/**` describe only active project truth;
  stale commands/routes/profile names are gone or historical outside the human
  surface; agent-only runbooks and execution evidence live in agent/process
  surfaces with current links.
- A fresh reduce-entropy round finds no P0/P1 or material P2 candidate in this
  code-size/backend-complexity class.
