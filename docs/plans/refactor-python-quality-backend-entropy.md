---
refactor_scope: python-quality-backend-entropy
status: CONTINUE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-17
completed_ledger: docs/plans/refactor-python-quality-backend-entropy-completed.md
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

CONTINUE. Continue one verified, non-overlapping slice at a time. This file is
the unfinished active plan only. Completed work lives in
`docs/plans/refactor-python-quality-backend-entropy-completed.md`.

Refreshed quality signal from `python scripts/dev/check_python_quality_ratchet.py
--summary --top 80` on 2026-06-17 after the OpenAI Agents SDK model-input
compaction owner split. Treat this as the planning snapshot for the next slice;
refresh before executing again.

- 11 Ruff complexity violations and 70 oversized modules remain. The oversized
  count increased by one because the new model-input compaction owner is now
  counted above the default 800-line target.
- Largest P1 production hard-ceiling files are
  `roboclaws/household/realworld_contract.py` at 2836,
  `roboclaws/household/scene_camera_comparison.py` at 2830,
  `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py` at 2808,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` at 2711,
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` at 2394,
  and `roboclaws/household/report.py` at 2108.
- `roboclaws/agents/drivers/openai_agents_live.py` is down to 1994 lines and is
  no longer a hard-ceiling P1. Keep it below 2000; reopen it only if SDK driver
  request/session/provider orchestration grows again or rebuilds model-input
  compaction inline.
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
  `scripts/molmo_cleanup/molmospaces_subprocess_worker.py` is 1841 lines.
- The apple object-parity owner files are now below the 800-line target:
  `robot_camera_apple2apple_object_parity.py` is 689 lines,
  `robot_camera_apple2apple_rgb_evidence.py` is 402 lines, and
  `robot_camera_apple2apple_visual_state.py` is 337 lines.
- `roboclaws/launch/scene_sampler.py` is 1965 lines and stays cleared from P1
  unless it crosses 2000 lines again or regains source-prep, candidate-profile,
  prefilter, or scanner-admission ownership drift.
- Current complexity rows are P2 unless paired with hard-ceiling work:
  operator-console tests, B1 preview rendering, a cleanup checker helper, live
  eval polling, MCP semantic tool registration, prompt preview, and eval-harness
  blockers. They should not hide while a file-size slice improves, but they are
  not the default next P1 unless the active product focus changes.

Execution refresh on 2026-06-17 moved visual-candidate declaration
orchestration into `realworld_visual_candidate_declarations.py` and the
registration/resolution lifecycle into `realworld_visual_candidate_lifecycle.py`.
`realworld_contract.py` dropped from 4656 to 3888 lines, while the new
declaration owner is 345 lines, the lifecycle owner is 737 lines, and
`realworld_visual_candidates.py` remains below the 800-line target at 627
lines. Candidate A is still active because `realworld_contract.py` remains
above the hard ceiling, but the visual-candidate payload/event/overlay,
declaration orchestration, and registration/resolution lifecycle boundaries
stay closed without fresh drift. Recent Candidate B slices moved
capture-quality probe construction into
`robot_camera_apple2apple_capture_quality.py`, deleted runner-private
material/probe wrapper delegates in favor of
`robot_camera_apple2apple_materials.py`, and moved native Isaac render
diagnostics into `robot_camera_apple2apple_native_render.py`; the latest slice
moved saved/metric image artifact preparation, image-diff payload construction,
residual diagnostics, and residual triage into
`robot_camera_apple2apple_image_metrics.py` while reusing
`scene_camera_image_metrics.py` for generic pixel visual metrics. The apple
runner dropped from 4573 to 3740 lines across those slices. Completed
init/runtime-prior, Runtime Metric Map payload, planner-probe report-panel,
scene-camera report, apple Object Gate / Render Gate, apple capture-quality,
material/probe primitive, native-render diagnostic, and apple image-metric
slices stay closed. Ponytail small cuts remain opportunistic inputs; they must
not postpone the P1 hard-ceiling checkpoint.

Ponytail audit recheck on 2026-06-17 did not find a dependency-level removal or
stdlib/native replacement that should jump ahead of the hard-ceiling work. The
useful ponytail inputs are small stale-surface or duplicate-wrapper cuts: the
checker legacy flag, camera-labeler identity maps, `_task_prefix_legacy`, and
duplicated lane/guidance wording. The apple material/probe delegate cut is
complete and should not be recreated. Treat remaining small cuts as P2
opportunistic scope inside a matching owner slice, not as a reason to defer the
next P1 split.

Intuitive-refactor implementation refresh on 2026-06-17 moved done-readiness
pending/held cleanup candidate derivation and destination-option derivation from
`realworld_contract.py` into `realworld_done_readiness.py`, then deleted the
contract-private `_pending_cleanup_candidates()`, `_held_cleanup_candidates()`,
and `_destination_options_for_policy()` wrappers after call-site scan confirmed
no in-repo production callers. Public done-readiness and MCP done-blocker
payloads were preserved by focused contract tests. The ratchet remains 11
complexity rows and 66 oversized modules; `realworld_contract.py` is down to
3774 lines, narrowly ahead of the 3740-line apple runner. Continue with a fresh
scan before the next slice. Default to Candidate A only if another real
facade-private coupling point is found; otherwise return to Candidate B's visual
comparison family. Do not reopen material/probe delegates, native render
diagnostics, Object Gate / Render Gate, capture-quality interpretation,
image-metric artifacts, scene-camera report rendering, visual-candidate
lifecycle, or done-readiness pending-candidate derivation without fresh drift.

Follow-up implementation refresh on 2026-06-17 moved public manipulation/tool
response envelope construction from `realworld_contract.py` into
`realworld_tool_responses.py`. The contract facade still owns tool sequencing
and state mutation, but no longer builds the public pick/place/open/close
success/error envelopes, fixture response ids, or semantic-order error payloads
inline. Focused contract and MCP server tests preserved direct and agent-facing
tool response shapes. The ratchet remains 11 complexity rows and 66 oversized
modules; `realworld_contract.py` is down to 3741 lines, one line above the
3740-line apple runner. Continue with a fresh scan before the next slice; the
default should now be whichever of Candidate A or Candidate B has the clearer
remaining owner boundary, not file size alone.

Planning-only intuitive-refactor / ponytail recheck on 2026-06-17 refreshed the
same ratchet and small-cut evidence after the tool-response slice. The ratchet
is still 11 complexity rows and 66 oversized modules. No `pyproject.toml`
dependency removal, stdlib replacement, or one-shot ponytail cut outranks the
P1 hard-ceiling frontier. The empty camera-labeler maps in
`roboclaws/household/profiles.py` are confirmed identity indirections, while
normalization, validation, public `camera_labeler`, and
`visual_grounding_pipeline_id` semantics stay active contracts. The
`_task_prefix_legacy` prompt shim still has no in-repo call sites. The
`--require-canonical-robot-view-camera-control` checker flag remains a
reachable CLI/docs alias for `--require-robot-head-camera-fpv` and needs a
checker-contract migration if selected. Duplicated lane and
`hybrid-phase-pipeline` wording is docs-only startup friction. Do not run a
standalone small-cut pass by default; fold these P2 cuts into a matching
profile, prompt, checker, or docs slice only when they simplify that selected
owner.

Implementation refresh on 2026-06-17 moved camera-label producer declaration
input construction from `realworld_contract.py` into
`realworld_visual_candidate_declarations.py`. That owner now builds simulated
camera-model candidate inputs, external visual-grounding requests, missing
client / contract-error / failed-pipeline envelopes, destination fixture
resolution for producer candidates, model-declared observation events, and
registration calls into the lifecycle owner. Direct cleanup and the MCP server
contract test now call the declaration owner directly instead of the
contract-private `_simulated_declaration_inputs_for_waypoint()` helper.
`realworld_contract.py` is down to 3554 lines, and the apple-to-apple runner is
again the largest production hard-ceiling file at 3740 lines. The ratchet
remains 11 complexity rows and 66 oversized modules. Reopen this boundary only
if the contract facade starts rebuilding camera-label producer request/failure
packets, simulated declaration input rows, model-declared observation events,
or registration wrapper aliases again.

Planning-only intuitive-refactor / ponytail audit recheck on 2026-06-17
refreshed the ratchet at the same 11 complexity rows and 66 oversized modules,
then inspected Candidate B's remaining apple runner seams. No new dependency,
stdlib/native replacement, or one-shot ponytail deletion outranks the P1
hard-ceiling frontier. The next default slice is Candidate B object parity audit
construction: move the `robot_camera_object_parity_audit_v1` artifact builder
out of `run_robot_camera_apple2apple_comparison.py` into a focused visual
comparison owner, while leaving Object Gate / Render Gate classification in
`robot_camera_apple2apple_object_gate.py` and leaving the runner as orchestration
and manifest attachment. Capture-lane initialization is not the default next
slice after inspection because the current code is still subprocess lifecycle,
canonical generated-mess setup, and block-manifest orchestration; split it only
if a fresh scan finds duplicated lane setup or an owner stronger than the runner
itself.

Implementation refresh on 2026-06-17 moved apple
`robot_camera_object_parity_audit_v1` construction, compact/skipped audit
summaries, semantic-pose index fallback, binding/index compaction, and category
summary construction from `run_robot_camera_apple2apple_comparison.py` into
`robot_camera_apple2apple_object_parity.py`; selected target RGB/focus evidence
moved into `robot_camera_apple2apple_rgb_evidence.py`; visual-state contract
evidence and visual-physics-sensitive target selection moved into
`robot_camera_apple2apple_visual_state.py`. The runner now reads lane state,
attaches the audit to the manifest, and invokes Object Gate / Render Gate
diagnostics without rebuilding audit items inline. Direct apple unit tests now
target the focused owners for audit, visual-state, and RGB evidence behavior.
The apple runner dropped from 3740 to 2394 lines; the new owners are 689, 402,
and 337 lines; the staged/add-N ratchet refresh still reports 11 complexity
rows and 66 oversized modules. Reopen this boundary only if the runner starts
rebuilding object/receptacle audit rows, compact/skipped audit packets,
visual-state contracts, selected RGB/focus evidence, semantic-pose index
fallback, or category summaries directly.

Planning-only intuitive-refactor / ponytail recheck on 2026-06-17 refreshed the
ratchet at 11 complexity rows and 66 oversized modules, then rechecked the
known ponytail small cuts and the A/B call-site frontier. No dependency removal,
stdlib/native replacement, or one-shot stale-surface deletion outranks the P1
hard-ceiling work. Candidate A now has the clearer next boundary:
`realworld_contract.py` still directly builds Runtime Metric Map target
candidates, public semantic anchors, public fixture-reference/anchor-id mapping,
target-search summaries, and minimal-map target-fixture resolution, while
`realworld_contract_payloads.py` and done-readiness still call back through
facade-private methods. The next default implementation slice is the Runtime
Metric Map target/public-anchor owner split. Candidate B remains active, but
the apple runner's remaining obvious chunks are camera-contract diagnostics,
render-domain interpretation, and capture-lane orchestration; those are fallback
work unless a fresh scan finds new duplication or drift. Revalidated ponytail P2
items: the camera-labeler maps are still zero-entry identity indirections,
`_task_prefix_legacy` still has no in-repo call sites, the checker legacy flag is
still a reachable CLI/docs alias, and duplicated lane / workflow wording remains
docs-only L0 friction.

Implementation refresh on 2026-06-17 finished Candidate A's Runtime Metric Map
target/public-anchor owner split in the local worktree. Target candidates,
public semantic anchors, fixture-reference/anchor-id mapping, target-search
summaries, minimal-map target-fixture resolution, waypoint anchor seeding, and
runtime-anchor target resolution now belong to
`realworld_runtime_map_targets.py`. Payload, done-readiness, visual-candidate,
tool-response, and init callers use that owner directly where they only need
target/public-anchor data; `RealWorldCleanupContract` keeps state mutation,
tool sequencing, and small action-flow wrappers. The old duplicate
contract-private target/anchor method bodies are gone, `resolve_target_query`
remains reachable from the public compatibility helper, and
`_preferred_waypoint_for_fixture()` is part of the runtime-map target protocol
instead of a `type: ignore` escape. Metric: `realworld_contract.py` 3554 ->
2836 lines; new owner 1009 lines; ratchet now reports 11 complexity rows and
67 oversized modules because the new owner is counted. Proof already run in
the local dirty checkpoint: ruff, format check, py_compile, focused
realworld-contract, actionable-snapshot, and MCP server tests, plus ratchet.
Before committing, rerun `git diff --check`; after commit, choose the next
slice from a fresh scan instead of reopening this boundary.

Implementation refresh on 2026-06-17 moved proof-bundle result rendering from
`report.py` into `report_sections_proof_bundle.py`. That owner now renders
proof result summaries, proof-quality summary rows, grasp-feasibility signature
tables, individual proof result cards, view figures, and local artifact hrefs.
`render_planner_proof_bundle_runner_report()` now composes the public
`proof_bundle_results_section()` instead of owning the proof-result helper
family inline. Metric: `report.py` 2525 -> 2108 lines;
`report_sections_proof_bundle.py` is 828 lines; ratchet reports 11 complexity
rows and 68 oversized modules because the proof-bundle owner is now counted
above 800. Proof already run in the local dirty checkpoint: ruff, format check,
py_compile, cleanup report contract tests, proof-bundle checker contract tests,
proof-bundle runner script unit tests, and ratchet. Reopen this boundary only
if `report.py` starts rebuilding proof-bundle result summaries, proof-quality
summary rows, grasp-feasibility signature tables, proof result cards, or
proof-result view figures directly.

Planning-only intuitive-refactor / ponytail recheck on 2026-06-17 refreshed the
ratchet after the proof-bundle dirty checkpoint and expanded the active P1 map
beyond A/B. The ratchet remains 11 complexity rows and 68 oversized modules. No
dependency removal, stdlib/native replacement, or one-shot ponytail deletion
outranks the hard-ceiling frontier. `run_molmo_planner_manipulation_probe.py`
and the OpenAI Agents SDK live runtime/runner are now explicit P1 candidate
clusters because they are production hard-ceiling files with real owner seams.
The default remains: close the current dirty proof-bundle checkpoint first, then
choose one owner-boundary slice from Candidates A-D by call-site evidence, not
by line count. Keep `_task_prefix_legacy`, empty camera-labeler maps, the legacy
checker flag, and duplicate wording as P2 opportunistic cuts only.

Implementation refresh on 2026-06-17 moved planner-probe runtime diagnostics
from `run_molmo_planner_manipulation_probe.py` into
`planner_probe_runtime_diagnostics.py`. Runtime module/version discovery, torch
and CUDA diagnostics, CUDA memory snapshots, CuRobo extension-cache packets,
Warp compatibility / minimal `warp.torch` adapter, renderer-device selection,
headless renderer environment setup, and renderer constructor patching now live
in the diagnostic owner. The runner still decides when to sample diagnostics and
emit worker events. Metric: planner probe runner 2948 -> 2510 lines; new owner
is 474 lines; ratchet remains 11 complexity rows and 68 oversized modules.
Proof: planner headless renderer unit tests, planner manipulation checker
contract tests, ruff, format check, py_compile, `git diff --check`, and ratchet.
Reopen this boundary only if the runner starts rebuilding runtime module
packets, CUDA snapshot math, CuRobo cache evidence, Warp adapter diagnostics, or
renderer adapter setup directly.

Planning-only intuitive-refactor / ponytail audit recheck on 2026-06-17
refreshed the ratchet at 11 complexity rows and 68 oversized modules, then
rechecked stale-surface and small-cut candidates against the active hard-ceiling
frontier. No `pyproject.toml` dependency removal, stdlib/native replacement, or
single small deletion outranks the current P1 owner-boundary work. The
camera-labeler pipeline maps remain zero-entry identity indirections but are
paired with active validation and public camera-labeler metadata;
`_task_prefix_legacy` still has no in-repo call sites; the canonical-robot-view
checker flag remains a reachable legacy alias that needs a focused checker
migration if selected.

Implementation refresh on 2026-06-17 completed Candidate C's task-sampler
diagnostics owner split. Task-sampler robot-placement profiles, exact cleanup
task config, exact sampler adapter, sampler failure diagnostics, placement
scene/grasp/candidate-removal diagnostics, diagnostic JSON coercion, sampled
task binding, requested cleanup primitive binding, and cleanup binding
promotion now live in
`scripts/molmo_cleanup/planner_probe_task_sampler_diagnostics.py`. The runner
now delegates those concepts directly and keeps probe orchestration, CuRobo
memory profile application, policy execution, worker exception context,
execute-mode image artifacts, CLI/worker dispatch, and result writes. Metric:
planner probe runner 2510 -> 1103 lines; new owner is 1412 lines; ratchet is
11 complexity rows and 69 oversized modules. Proof: focused planner headless
renderer unit tests, planner manipulation checker contract tests, ruff, format
check, py_compile, and ratchet. Reopen this boundary only if the runner starts
rebuilding task-sampler profiles, exact cleanup task config/binding, sampler
failure diagnostics, diagnostic JSON coercion, sampled task binding, requested
cleanup primitive binding, or cleanup binding promotion directly.

Planning-only intuitive-refactor / ponytail recheck on 2026-06-17 refreshed
the ratchet at 11 complexity rows and 69 oversized modules, then inspected the
A/B/D frontier without starting implementation. No dependency removal,
stdlib/native replacement, or small stale-surface deletion outranks the P1
hard-ceiling frontier. Candidate D now has the clearest default next owner
boundary: move OpenAI Agents SDK driver-side model-input compaction policy,
filtering, raw-FPV image-memory policy, camera-grounded history summarization,
tool-output summaries, model-input shape metrics, and model-input filter event
writing out of `roboclaws/agents/drivers/openai_agents_live.py` into a focused
driver owner. Keep runner-side perf-profile/default resolution in
`run_live_openai_agents_cleanup.py` unless a separate runner slice is selected;
do not combine SDK driver model-input filtering with live server lifecycle,
checker invocation, or timing attachment. Candidate B's clearest fallback
boundary is apple camera-contract diagnostics: move FPV/head-camera contract
summaries, per-location camera contract diagnostics, FPV pose/lens deltas,
compact camera metadata, robot-pose delta, Isaac robot import diagnostics,
head-articulation diagnostics, and chase-contract diagnostics out of
`run_robot_camera_apple2apple_comparison.py` into a focused apple camera
contract owner. Candidate A should not be chosen merely because
`realworld_contract.py` and `report.py` remain above the hard ceiling; select it
only with a fresh facade-private coupling point or a remaining report-section
owner such as Agibot rehearsal / SDK runner sections.

Planning-only intuitive-refactor / ponytail audit recheck on 2026-06-17
refreshed the same ratchet at 11 complexity rows and 69 oversized modules, then
checked Candidate D call sites and the remaining ponytail small cuts without
starting implementation. Candidate D remains the default next P1: the SDK
driver's model-input compaction block is still a cohesive owner boundary from
`_input_compaction_config()` through shape metrics and
`openai_agents_model_input_filter_v1` event writing, while
`_sdk_run_config_payload()` is only the RunConfig integration point. The
existing model-input tests import `_compact_model_input_items()` and
`_model_input_shape_summary()` from the driver-private module; a D
implementation should move those tests to the new owner directly instead of
leaving driver aliases. Keep runner-side profile/default construction in
`run_live_openai_agents_cleanup.py`: the runner builds perf-profile metadata,
the driver compacts the SDK model input from that metadata. Ponytail recheck
confirmed `_task_prefix_legacy` has no in-repo call sites and the camera-labeler
maps are empty identity mappings, but neither is large enough to outrank D; the
camera-labeler cut must keep public `camera_labeler` validation and
`visual_grounding_pipeline_id` round-tripping, and the checker legacy flag is
still a reachable CLI/docs alias that needs a focused migration if selected.
Docs-only duplicated lane wording includes a historical duplicate
`world-public-labels` entry in `docs/human/molmospaces-cleanup-mode-architecture.md`,
but keep that as L0 cleanup unless paired with a human-doc slice.

Implementation refresh on 2026-06-17 moved OpenAI Agents SDK model-input
compaction from `openai_agents_live.py` into
`openai_agents_model_input.py`. The new owner now owns model-input compaction
config extraction, RunConfig filter construction, raw-FPV image-memory
summaries, camera-grounded history summaries, tool-output unwrapping,
metric-map/public tool-output summaries, aggregate model-input shape metrics,
and `openai_agents_model_input_filter_v1` event writing. The SDK driver keeps
provider/model settings, retry, model racing, span recording, runtime config,
and MCP session lifecycle, and imports only the compaction config/filter
integration. Tests import `_compact_model_input_items()` and
`_model_input_shape_summary()` from the new owner directly instead of keeping
driver-private aliases. Metric: `openai_agents_live.py` 2889 -> 1994 lines;
new owner 972 lines; staged/add-N ratchet is 11 complexity rows and 70
oversized modules. Reopen this boundary only if the driver starts rebuilding
model-input compaction policy, raw-FPV/camera-grounded history summaries,
tool-output summaries, model-input shape metrics, or filter events inline.

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
- Line-count relief is evidence, not the goal. Prefer concept reduction:
  delete stale surfaces, merge duplicate concepts, move behavior to existing
  owners, or create a new owner only around a named ownership boundary. Preserve
  current public launch axes, artifact schemas, report claims, agent-facing
  contracts, and private/public eval boundaries unless a slice explicitly
  declares and verifies a migration.

## Current Target

Current checkpoint: Candidate D's SDK driver-side model-input compaction split
is verified and closed. Refresh the ratchet before implementation, then choose
the next P1 from the remaining hard-ceiling frontier by owner-boundary evidence.
Candidate A remains active because `realworld_contract.py` and `report.py` are
still above the hard ceiling, but the runtime-map target/public-anchor,
proof-bundle result-renderer, and related recent contract boundaries are
closed. Candidate B remains active through the visual comparison family:
`scene_camera_comparison.py`, `summarize_robot_camera_visual_parity.py`, and the
apple runner are still above the ceiling, but the apple object-parity audit,
selected RGB evidence, and visual-state contract boundaries are closed.
Candidate B's current best fallback is apple camera-contract diagnostics, not
capture-lane initialization. Candidate D remains active only through the
OpenAI Agents cleanup runner hard ceiling or a fresh SDK-driver owner seam such
as model-service retry/racing observability or span/event sanitization; do not
reopen SDK model-input compaction. Candidate C is no longer the default next P1
unless the planner probe runner crosses 2000 lines again or the task-sampler
owner reveals a second real owner with call-site evidence.

Recommended next slice claim:

- Slice: choose the next owner-boundary P1 from Candidate A, Candidate B, or the
  remaining Candidate D runner. Likely defaults are Candidate B apple
  camera-contract diagnostics or Candidate D runner-side performance-profile /
  timing-summary ownership; choose by fresh call-site evidence, not file size
  alone.
- Owner layer: MCP Capability Contract And Tools for Candidate A; Artifacts,
  reports, and eval suites for Candidates B/C; Agent Engines And Provider
  Profiles plus Thin Runtime / Server Adapters for Candidate D.
- Current friction: the hard-ceiling frontier is now
  `realworld_contract.py` at 2836, `scene_camera_comparison.py` is 2830,
  `summarize_robot_camera_visual_parity.py` is 2808,
  `run_live_openai_agents_cleanup.py` is 2711,
  the apple runner is 2394, and `report.py` is 2108. Candidate A's runtime-map
  target and proof-bundle result-renderer splits are closed. Candidate C's
  runtime diagnostics and task-sampler diagnostics owner splits are closed.
  Candidate B's apple Object Gate,
  capture-quality, material/probe primitives, native-render diagnostics,
  image-metric artifacts, object-parity audit assembly, selected RGB evidence,
  and visual-state contract evidence are closed. Candidate D's SDK driver-side
  model-input filtering boundary is closed; the live cleanup runner still keeps
  perf-profile/default resolution and timing/latency summary construction
  inline.
- Simplification: move one remaining real responsibility to an existing or
  focused owner and update callers to that owner directly. Delete obsolete
  private wrappers when call-site scan proves they are internal. Do not replace
  private coupling with a loose parameter bag, compatibility alias pile, or new
  wrapper facade. For any follow-up D runner slice, keep SDK driver internals
  separate from live server lifecycle and do not move profile/default
  construction into the SDK driver.
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
  audit/RGB/visual-state ownership, OpenAI Agents model-input compaction
  ownership, OpenAI Agents provider semantics, or lane initialization / manifest
  setup without fresh duplication.

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

Preflight status: REVIEWED. Route: `$intuitive-refactor` ratchet mode. Default
execution: refresh the ratchet, run a short ponytail recheck against current
hard-ceiling candidates, and select one remaining owner-boundary P1 from
Candidate A/B/D. Candidate B's apple camera-contract diagnostics and Candidate
D's runner-side performance-profile / timing-summary ownership are the clearest
known next seams; Candidate A needs fresh facade-private coupling evidence.
Non-goals: broad repo cleanup, line-count shaving across many files, preserving
obsolete internal wrappers, lane initialization unless fresh drift appears,
reopening SDK model-input compaction, mixing SDK driver internals with live
runner lifecycle, and live/provider/simulator proof unless the chosen slice
changes that route. Re-approve if a slice would change a public launch,
artifact schema, report shape, agent-facing payload, provider behavior,
event/span schema, model-input compaction schema, or private/public eval
contract.

## Active Candidates

### A: Contract And Report Hard-Ceiling Split

Severity: P1. `roboclaws/household/realworld_contract.py` is 2836 lines and
`roboclaws/household/report.py` is 2108 lines. Owning architecture layers: MCP
Capability Contract And Tools plus Artifacts, reports, and eval suites.
Done-readiness pending/held cleanup candidate derivation now belongs to
`realworld_done_readiness.py`; reopen it only if the contract facade starts
rebuilding pending candidates, held candidates, destination options, or private
wrapper aliases again. Public manipulation/tool response envelopes now belong
to `realworld_tool_responses.py`; reopen them only if the contract facade starts
rebuilding pick/place/open/close success/error payloads, fixture response ids,
or semantic-order error envelopes inline. Candidate A remains P1 only for a
fresh boundary that reduces facade-private coupling or report ownership, for
example agent-view wrapper cleanup, runtime-map/cleanup-worklist caller
migration, or a remaining report section owner. Do not reopen init
projection/runtime-prior, Runtime Metric Map payload, Runtime Metric Map
target/public-anchor ownership, visual-candidate payload/event/overlay,
visual-candidate declaration orchestration, visual-candidate
registration/resolution lifecycle, camera-label producer input construction, or
planner-probe report-panel slices.
Visual-candidate lifecycle now belongs to
`realworld_visual_candidate_lifecycle.py`; reopen it only if the contract facade
starts rebuilding normalization, match resolution, declaration payloads,
resolved/unresolved detection materialization, visual-evidence error payloads,
or handle actionability directly. Camera-label producer inputs now belong to
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

Severity: P1. `roboclaws/household/scene_camera_comparison.py`,
`scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`, and
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` remain
oversized. Owning architecture layer: Artifacts, reports, and eval suites,
with Backend Runtime / Environment Primitive details staying behind the
existing MuJoCo/Isaac capture workers. Scene-camera HTML report rendering now
belongs to `scene_camera_report*.py`, and the public
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

Other candidate-B slices are valid only around fresh real boundaries such as
apple camera-contract diagnostics, duplicated capture-lane initialization, new
render contract diagnostics drift, or visual-parity summary reporting. The
apple runner's remaining camera-contract diagnostics are the clearest B
fallback: move FPV/head-camera contract summaries, per-location camera contract
diagnostics, FPV pose/lens delta summaries, compact camera metadata,
robot-pose delta, Isaac robot import diagnostics, head-articulation
diagnostics, and chase-contract diagnostics to a focused owner while keeping
the runner responsible for lane initialization, state reads, manifest
attachment, target selection, and render-domain orchestration. Capture-lane
initialization remains parked as runner orchestration unless it grows duplicated
lane setup or a canonical generated-mess owner emerges. The
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
that owner directly. Remaining plausible D moves are model-service
retry/model-racing observability from the SDK driver, span recorder/event
sanitization from the SDK driver, or runner-side performance-profile/default
resolution and timing summary construction from the live cleanup runner. For a
runner slice, keep `_model_input_compaction_profile()`,
`_raw_fpv_image_memory_profile()`, and `_camera_grounded_history_profile()` out
of the SDK driver; move them only to a runner-owned profile/default module if
the slice selects that seam. Do not mix SDK driver internals with runner
lifecycle in one new owner, and do not change provider route semantics, model
thinking policy, MCP session behavior, continuation policy, checker gates,
event/span schemas, model-input compaction schemas, or live-status payloads
unless explicitly approved.

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
- Behavior tests: operator-console scene-preview/control/static-asset tests and
  cleanup-checker fixture lookup remain P2 fixture-builder work. Do not split
  large tests only for line count.
- MCP/prompt: `realworld_mcp_semantic_tools.py::register_semantic_cleanup_tools`
  and `prompt_preview.py::_goal_contract` are P2 unless they change an
  agent-facing contract.
- Stale small cuts: legacy checker flag
  `--require-canonical-robot-view-camera-control`, empty camera-labeler maps,
  `_task_prefix_legacy`, duplicated lane prose, and `hybrid-phase-pipeline`
  guidance wording. These do not justify deleting `camera_labeler`,
  visual-grounding artifact contracts, service plumbing, or public launch
  aliases. Current triage: the camera-labeler maps in
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
  unless paired with a human-doc cleanup slice.

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
  validation helper families.
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
- Backend id, runtime metadata, artifacts, and evidence attachments use common
  surfaces instead of repeated concrete-class or `backend == ...` branching.
- A fresh reduce-entropy round finds no P0/P1 or material P2 candidate in this
  code-size/backend-complexity class.
