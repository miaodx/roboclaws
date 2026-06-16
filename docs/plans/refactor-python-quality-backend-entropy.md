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
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` at 4573,
  `roboclaws/household/realworld_contract.py` at 3888 lines,
  `scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py` at 2948,
  `roboclaws/agents/drivers/openai_agents_live.py` at 2889,
  `roboclaws/household/scene_camera_comparison.py` at 2830,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` at 2711, and
  `roboclaws/household/report.py` at 2525.
- Backend workers remain below the hard ceiling:
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` is 1994 lines and
  `scripts/molmo_cleanup/molmospaces_subprocess_worker.py` is 1841 lines.
- `roboclaws/launch/scene_sampler.py` is 1965 lines and stays cleared from P1
  unless it crosses 2000 lines again or regains source-prep, candidate-profile,
  prefilter, or scanner-admission ownership drift.
- Current complexity rows are assigned to candidates C-F/E: operator-console
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
stay closed without fresh drift. Completed init/runtime-prior, Runtime Metric
Map payload, planner-probe report-panel, scene-camera report, and apple Object
Gate / Render Gate slices also stay closed. Ponytail small cuts remain
opportunistic inputs; they must not postpone the P1 hard-ceiling checkpoint.

Current checkout note: if the worktree still contains the uncommitted
visual-candidate lifecycle split (`realworld_visual_candidate_lifecycle.py`
plus the `realworld_contract.py` delegates), close that in-flight candidate-A
slice first with changed-code review, focused proof, and an explicit commit or
owner decision before starting the next slice. Do not keep adding lifecycle
work to `realworld_visual_candidate_lifecycle.py` once it would cross the
800-line target; the next contract slice needs a different named boundary.

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

Immediate next action in a dirty checkout: close the in-flight
visual-candidate lifecycle slice before opening new work. Once the checkout is
clean or the owner explicitly parks that slice, refresh the ratchet and choose
the next P1 owner boundary from the remaining hard-ceiling files. Candidate A
remains valid only for a new `RealWorldCleanupContract` boundary such as
agent-view/readiness wrappers, runtime-map/cleanup-worklist caller migration,
or another named facade-private coupling point; do not reopen visual-candidate
payload, declaration, or lifecycle work without fresh drift. Candidate B's
apple runner is now the largest P1 file and is a valid alternate when the next
boundary is concrete. B1 label-tool rows are cleared; candidate D is preview
rendering only. Ponytail small cuts are inputs when they remove stale surface,
duplicate concept, or false confidence, but they must not postpone the P1
hard-ceiling checkpoint.

## Execution Preflight

Preflight status: REVIEWED. Route: `$intuitive-refactor` ratchet mode. Default
execution: refresh the ratchet, then execute one P1 owner-boundary slice,
currently candidate A unless a fresh context scan selects a more concrete P1
boundary. Non-goals: broad repo cleanup, line-count shaving across many files,
preserving obsolete internal wrappers, and live/provider/simulator proof unless
the chosen slice changes that route. Re-approve if a slice would change a
public launch, artifact, report, agent-facing, or private/public eval contract.

## Active Candidates

### A: Contract And Report Hard-Ceiling Split

Severity: P1. `roboclaws/household/realworld_contract.py` is 3888 lines and
`roboclaws/household/report.py` is 2525 lines. Owning architecture layers: MCP
Capability Contract And Tools plus Artifacts, reports, and eval suites.
Alternate P1 only when a fresh boundary reduces facade-private coupling or
report ownership, for example agent-view/readiness wrappers,
runtime-map/cleanup-worklist caller migration, or a remaining report section
owner. Do not reopen init projection/runtime-prior, Runtime Metric Map payload,
visual-candidate payload/event/overlay, visual-candidate declaration
orchestration, visual-candidate registration/resolution lifecycle, or
planner-probe report-panel slices. Visual-candidate lifecycle now belongs to
`realworld_visual_candidate_lifecycle.py`; reopen it only if the contract
facade starts rebuilding normalization, match resolution, declaration payloads,
resolved/unresolved detection materialization, visual-evidence error payloads,
or handle actionability directly. `RealWorldPayloadContract` and
`DoneReadinessContract` are ponytail inputs only when a slice removes
facade-private coupling; replacing an alias pile with a looser parameter bag,
all-purpose context object, or new wrapper facade is not a win.

### B: Visual Comparison Pipeline Split

Severity: P1. `roboclaws/household/scene_camera_comparison.py` and
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` remain
oversized. Scene-camera HTML report rendering now belongs to
`scene_camera_report*.py`, and the public
`render_scene_camera_comparison_report` entry point is preserved in
`scene_camera_comparison.py`. Do not reopen report rendering unless the
comparison facade starts rebuilding report sections directly again.

Other candidate-B slices remain valid only around real boundaries such as
capture-lane initialization, render contract diagnostics, native render
diagnostics, object audit item construction, or image metric artifact
preparation. Real renderer claims still require separate local proof. The
Object Gate / Render Gate diagnostic packet owner is now
`robot_camera_apple2apple_object_gate.py`, and report-renderer tests call
`robot_camera_apple2apple_report.py` directly; do not reopen those runner
facade aliases without fresh drift. Continue the apple runner only when the
selected boundary is not already owned by
`robot_camera_apple2apple_object_gate.py` or
`robot_camera_apple2apple_report.py`.

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
  `roboclaws/household/profiles.py` are identity-map shrink targets only; the
  prompt helper alias has no in-repo call sites but still needs a scoped prompt
  test/static proof before deletion; the checker flag has parser/test surface
  and needs a checker-contract migration; the guidance wording is docs-only
  startup friction.

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
  `robot_camera_apple2apple_object_gate.py`; scene-camera USD render-contract,
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
