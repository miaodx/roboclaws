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
--summary --top 80` on 2026-06-17. Treat this as a planning snapshot, not proof
of a clean checkpoint; refresh before the next execution slice.

- 11 Ruff complexity violations and 66 oversized modules remain.
- Largest P1 production hard-ceiling files are
  `roboclaws/household/realworld_contract.py` at 3888 lines,
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` at 3740,
  `scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py` at 2948,
  `roboclaws/agents/drivers/openai_agents_live.py` at 2889,
  `roboclaws/household/scene_camera_comparison.py` at 2830,
  `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py` at 2808,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` at 2711, and
  `roboclaws/household/report.py` at 2525.
- Backend workers remain below the hard ceiling:
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` is 1994 lines and
  `scripts/molmo_cleanup/molmospaces_subprocess_worker.py` is 1841 lines.
- `roboclaws/launch/scene_sampler.py` is 1965 lines and stays cleared from P1
  unless it crosses 2000 lines again or regains source-prep, candidate-profile,
  prefilter, or scanner-admission ownership drift.
- Current complexity rows are assigned to candidates C-H: operator-console
  tests, B1 preview rendering, a cleanup checker helper, live eval polling,
  MCP semantic tool registration, prompt preview, and eval-harness blockers.
  They should not hide while a file-size slice improves, but they are not the
  default next P1 unless the active product focus changes.

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

Ponytail audit recheck on 2026-06-17 did not find a dependency-level removal
that should jump ahead of the hard-ceiling work. The useful ponytail inputs are
small stale-surface or duplicate-wrapper cuts: the checker legacy flag,
camera-labeler identity maps, `_task_prefix_legacy`, and wording duplication.
The apple material/probe delegate cut is complete and should not be recreated.
Treat remaining small cuts as P2 opportunistic scope inside a matching owner
slice, not as a reason to defer the next P1 split.

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

## Operating Rules

- Two-document contract: this file is the only active plan, and
  `docs/plans/refactor-python-quality-backend-entropy-completed.md` is the only
  completed ledger. Do not create a third cleanup plan or scratch log.
- Refresh `python scripts/dev/check_python_quality_ratchet.py --summary --top
  40` before selecting or completing a slice. If new plan-external drift crosses
  2000 lines, adds production/shared complexity, or regresses totals, update the
  candidates before continuing.
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

Refresh the ratchet, then choose one new P1 owner-boundary slice.
`realworld_contract.py` remains the largest production hard-ceiling file at
3741 lines, while the visual comparison family still has three above-ceiling
files: `run_robot_camera_apple2apple_comparison.py`,
`scene_camera_comparison.py`, and `summarize_robot_camera_visual_parity.py`.
Default to Candidate A only if a fresh scan finds a real remaining
`RealWorldCleanupContract` facade-private coupling point. Otherwise select the
next concrete Candidate B visual-comparison boundary.

Recommended next slice claim:

- Slice: choose a fresh `RealWorldCleanupContract` facade-private coupling
  boundary or a visual-comparison owner boundary confirmed by call-site scan.
- Owner layer: MCP Capability Contract And Tools plus Artifacts, reports, and
  eval suites.
- Current friction: `realworld_contract.py` remains a 3741-line public/private
  contract facade, and the visual comparison family still has multiple
  above-ceiling report/probe scripts. The done-readiness pending-candidate and
  public manipulation-response boundaries are closed.
- Simplification: move one real responsibility to its existing owner or a
  focused owner module, and delete obsolete private wrappers when call-site scan
  proves they are internal. Do not replace private coupling with a loose
  parameter bag, compatibility alias pile, or new wrapper facade.
- Behavior-change class: internal owner cleanup unless the selected slice
  explicitly changes report or artifact contracts.
- Proof: focused contract/MCP/report/unit tests matching the selected boundary,
  ruff on touched files, format check, py_compile, and ratchet summary.
- Non-goals: reopening init projection/runtime-prior, Runtime Metric Map
  payloads, visual-candidate payload/declaration/lifecycle, planner-probe
  report panels, done-readiness pending-candidate derivation, or any closed
  apple visual-comparison owner without fresh drift.

Candidate A
remains valid only for a new `RealWorldCleanupContract` boundary such as
agent-view/readiness wrappers, runtime-map/cleanup-worklist caller migration,
or another named facade-private coupling point; do not reopen visual-candidate
payload, declaration, or lifecycle work without fresh drift. B1 label-tool
rows are cleared; candidate D is preview rendering only. Ponytail small cuts
are inputs when they remove stale surface, duplicate concept, or false
confidence, but they must not postpone the P1 hard-ceiling checkpoint.

## Execution Preflight

Preflight status: REVIEWED. Route: `$intuitive-refactor` ratchet mode. Default
execution: refresh the ratchet, then execute one P1 owner-boundary slice,
currently Candidate A only if a fresh facade-private coupling boundary remains,
otherwise Candidate B's next visual-comparison owner split. Non-goals: broad
repo cleanup, line-count shaving across many files, preserving obsolete
internal wrappers, and live/provider/simulator proof unless the chosen slice
changes that route. Re-approve if a slice would change a public launch,
artifact, report, agent-facing, or private/public eval contract.

## Active Candidates

### A: Contract And Report Hard-Ceiling Split

Severity: P1. `roboclaws/household/realworld_contract.py` is 3741 lines and
`roboclaws/household/report.py` is 2525 lines. Owning architecture layers: MCP
Capability Contract And Tools plus Artifacts, reports, and eval suites.
Done-readiness pending/held cleanup candidate derivation now belongs to
`realworld_done_readiness.py`; reopen it only if the contract facade starts
rebuilding pending candidates, held candidates, destination options, or private
wrapper aliases again. Public manipulation/tool response envelopes now belong
to `realworld_tool_responses.py`; reopen them only if the contract facade starts
rebuilding pick/place/open/close success/error payloads, fixture response ids,
or semantic-order error envelopes inline. Candidate A remains P1 only for a
fresh boundary that reduces facade-private coupling or report ownership, for
example runtime-map/cleanup-worklist caller migration or a remaining report
section owner. Do not reopen init projection/runtime-prior, Runtime Metric Map payload,
visual-candidate payload/event/overlay, visual-candidate declaration
orchestration, visual-candidate registration/resolution lifecycle, or
planner-probe report-panel slices. Visual-candidate lifecycle now belongs to
`realworld_visual_candidate_lifecycle.py`; reopen it only if the contract facade
starts rebuilding normalization, match resolution, declaration payloads,
resolved/unresolved detection materialization, visual-evidence error payloads,
or handle actionability directly. `RealWorldPayloadContract` and
`DoneReadinessContract` are ponytail inputs only when a slice removes
facade-private coupling; replacing an alias pile with a looser parameter bag,
all-purpose context object, or new wrapper facade is not a win.

### B: Visual Comparison Pipeline Split

Severity: P1. `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`,
`roboclaws/household/scene_camera_comparison.py`, and
`scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py` remain
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

Remaining candidate-B slices are valid only around real boundaries such as
capture-lane initialization, render contract diagnostics, object audit item
construction, or visual-parity summary reporting. The runner-private
material/probe delegate surface has been removed; do not recreate
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

### C-H: P2 Rows And Small Cuts

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
  normalization, validation, and public `camera_labeler` semantics. The
  `_task_prefix_legacy` shim has no in-repo call sites and can be deleted with
  prompt static proof plus focused prompt tests. The checker flag is still a
  reachable parser/test/docs alias for `--require-robot-head-camera-fpv`, so it
  needs a checker-contract migration rather than an opportunistic delete. The
  guidance wording is docs-only startup friction.

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
