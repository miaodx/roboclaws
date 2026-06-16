---
refactor_scope: python-quality-backend-entropy
status: ACTIVE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-17
completed_ledger: docs/plans/refactor-python-quality-backend-entropy-completed.md
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

ACTIVE. Continue one verified, non-overlapping slice at a time. This file is
the unfinished active plan only. Completed work lives in
`docs/plans/refactor-python-quality-backend-entropy-completed.md`.

Refreshed quality signal from `python scripts/dev/check_python_quality_ratchet.py
--summary --top 40` on 2026-06-17. Treat this as a planning snapshot, not proof
of a clean checkpoint; refresh before the next execution slice.

- 15 Ruff complexity violations and 65 oversized modules in the current dirty
  checkout. The additional row/module versus the earlier 2026-06-17 snapshot
  comes from plan-external `scripts/operator_console/render_scene_previews.py`
  edits; keep it with the B1 Map 12/preview owner unless it survives as
  unowned drift.
- The prior dirty-worktree scene-sampler drift is now real source drift:
  `roboclaws/launch/scene_sampler.py` was 3070 lines before the scene-only
  prefilter split and is 2607 lines afterward. It remains the next P1
  checkpoint unless another active plan explicitly owns the repair.
- P1 hard-ceiling production files still include
  `roboclaws/household/realworld_contract.py` at 5036 lines,
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` at 4900,
  `roboclaws/household/scene_camera_comparison.py` at 4693,
  `roboclaws/household/report.py` at 3806,
  `scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py` at 2948,
  `roboclaws/agents/drivers/openai_agents_live.py` at 2889, and
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` at 2711.
- Backend workers remain below the hard ceiling:
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` is 1994 lines and
  `scripts/molmo_cleanup/molmospaces_subprocess_worker.py` is 1841 lines.
- Complexity rows are no longer only test fixture debt. Current rows span
  operator-console tests, the B1 Map 12 label tool, a cleanup checker helper,
  scene-preview rendering, live eval polling, MCP semantic tool registration,
  prompt preview, and eval-harness row blockers.

Do not treat these counts as current during execution. Refresh the repo-wide
summary before selecting or completing a slice.

## Two-Document Contract

- Active unfinished plan: this file.
- Completed concise ledger:
  `docs/plans/refactor-python-quality-backend-entropy-completed.md`.
- Do not create a third related plan, scratch log, or per-slice history file
  for this cleanup stream.
- Do not paste full command logs into either file. Keep only decision-relevant
  metrics, ownership, and proof class.

## Fixed Maintenance Action

Run this compaction step every 3-5 accepted slices, before pausing/committing a
checkpoint, or whenever this active plan grows beyond about 250 lines:

1. Refresh the ratchet summary.
2. Move completed active items into the completed ledger as compact bullets.
3. Trim this file back to unresolved decisions, current candidates, proof
   gates, and stop conditions.
4. Keep completed entries short: one slice or bundle, one effect, one proof
   level, and the metric delta if it matters.
5. If the completed ledger grows too large, compress older rows in place
   instead of creating another document.

Entry size rule: active candidates should usually fit in 6-8 lines; completed
ledger entries should usually fit in 2-4 lines.

## Out-of-Plan Drift Guard

Before each implementation slice, and again before marking the slice complete:

1. Run `python scripts/dev/check_python_quality_ratchet.py --summary --top 40`.
2. Compare the summary against this active plan, not only against touched
   files.
3. If new files outside the active candidates cross 2000 lines, gain new Ruff
   complexity rows, or cause the repo totals to regress, pause execution and
   update `## Active Candidates` before continuing.
4. Promote new drift to P1 when it crosses the hard file-size ceiling, adds
   production/shared complexity, or hides a false-green gate. Promote to P2
   when it is test-only or local workflow friction with clear ownership.
5. If the drift belongs to another active plan, reference that plan in one line
   here instead of duplicating detail.
6. If no new material drift appears, record only the refreshed totals in the
   completed ledger during the next compaction.

This guard is intentionally repo-wide. A slice that improves one planned file
should not finish while newly changed, plan-external files quietly become the
largest quality debt.

## Quality Standard

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
- Line-count relief is evidence, not the goal. Prefer fewer concepts, clearer
  owners, and less branching over extraction that only moves code around.

## Refactor Strategy

Use `$intuitive-refactor` ratchet mode for this stream. A slice may simplify
architecture and delete or change old internal behavior when that removes stale
surfaces or duplicate concepts. Preserve only current public launch axes,
artifact schemas, report claims, agent-facing contracts, and private/public
evaluation boundaries unless the slice explicitly declares and verifies a
migration.

Good patterns for this repo include backend facade/protocol boundaries, typed
evidence envelopes, strategy tables, command catalogs, pipeline/stage objects,
report section renderers, artifact builders, fixture builders, and scenario
factories. Bad patterns are compatibility shims for retired names, wrappers
that only preserve old call shapes, and splits that leave the same branching in
a different file.

## Current Target

Continue the Python code-size and complexity cleanup with stronger file-size
pressure than the earlier ratchet-only loop. Complexity has fallen quickly;
the next useful work should prioritize hard-ceiling files, test fixture debt,
and backend/report/evidence boundaries that prevent branching from returning.

Next execution should start by resolving the current drift classification:
either execute the scene-sampler hard-ceiling slice, or record which active
scene-sampler/eval plan owns it. After that, choose one P1 hard-ceiling
architecture slice. Do not continue by shaving isolated lines from many files.
Ponytail audit items are inputs to this queue only when they remove a stale
surface, duplicate concept, or false-confidence source; they should not
postpone the P1 hard-ceiling checkpoint.

## Parallel Acceleration Policy

Use parallel execution when it reduces wall-clock time without multiplying
concepts or creating merge risk. The main session remains the coordinator,
scope judge, and final verifier; worker sessions may execute independent
vertical slices only after the coordinator names the slice, owning layer,
likely touched files, focused tests, and merge order.

Parallelize only when all of these are true:

- Slices touch disjoint production modules, tests, docs, generated artifacts,
  and launch/eval/catalog surfaces.
- Each slice has a clear architecture owner from `ARCHITECTURE.md` and can be
  proven with its own focused gate before integration.
- No slice changes a public launch contract, artifact schema, report claim,
  agent-facing MCP/tool contract, or private/public evaluation boundary unless
  it is the only slice in flight.
- The dirty worktree is either clean enough for ownership to be obvious, or the
  coordinator explicitly records which existing dirty files are off limits.
- The batch size is small: prefer two concurrent slices; use three only for
  obviously disjoint test-fixture or docs/static cleanup.

Do not parallelize:

- Competing edits to the same hard-ceiling module, its immediate callers, or
  its primary behavior tests.
- `scene_sampler.py` / eval-sample drift while another active branch is already
  changing launch catalog, eval harness, generated samples, or operator-console
  readiness flows.
- Report, checker, and artifact-schema changes that need one coherent rendered
  claim.
- Any slice whose first step is deciding whether public behavior may change.

Merge protocol:

1. Refresh `python scripts/dev/check_python_quality_ratchet.py --summary --top
   40` once before selecting the batch.
2. Assign non-overlapping slice claims. Each worker returns a concise changed
   file list, simplification claim, and proof commands/results.
3. Integrate one slice at a time in the main session, rerunning that slice's
   focused gates and checking `git diff` before taking the next patch.
4. Rerun the ratchet summary after each integrated slice when it touches Python
   source, or after the whole batch only for docs-only/static batches.
5. If overlap, unexpected public-contract impact, or ratchet regression appears,
   stop the batch and serialize the remaining work.

This policy does not loosen the two-document contract: completed durable
outcomes still go into the completed ledger, and this active plan remains the
only unfinished source of truth for the cleanup stream.

## Execution Preflight

Preflight status: DRAFT.
Task source: plan path.
Canonical source: `docs/plans/refactor-python-quality-backend-entropy.md`.
Route: `$intuitive-refactor` ratchet mode.
Goal: Continue this cleanup with one architecture-simplifying slice, starting
by resolving or explicitly assigning current scene-sampler/eval ratchet drift
and classifying the new complexity rows.

Scope:

- Refresh ratchet signal before edits.
- Treat `scene_sampler.py` at 2607 lines as the first P1 checkpoint.
- If another active plan owns that drift, link that plan here before taking an
  unrelated hard-ceiling slice.
- Classify new complexity rows before execution; do not let plan-external
  complexity become invisible while one file-size slice improves.
- Then choose one P1 hard-ceiling architecture slice from this plan and execute
  it vertically: code, callers, tests, stale internal paths, proof.

Non-goals: broad repo cleanup, line-count shaving across many files,
preserving obsolete internal wrappers, live/provider/simulator proof unless the
chosen slice changes that route.

Entity budget: reuse this plan, existing owners, tests, and helpers;
remove/merge obsolete internal compatibility paths when callers move; add a new
module or helper only around a named architecture boundary; re-approve if a
slice would change a public launch, artifact, report, or agent contract.

Context: must-read root orientation docs, this active plan, the completed
ledger, current ratchet summary, touched module tests, and call sites. Avoid
old retrospectives, parked `TODOS.md` / `THOUGHTS.md`, and full historical
phase logs unless needed.

Acceptance:

- Success: one accepted slice reduces architecture friction, updates callers
  and tests, removes or parks stale surfaces, and leaves ratchet totals
  non-regressed.
- Blocked needs decision: public behavior, schema, report contract, or
  agent-facing contract would change beyond this plan.
- Blocked needs local validation: only if the chosen slice affects simulator,
  live provider, or hardware behavior that cannot be proven locally.
- Intermediate only: none unless explicitly approved before execution.
- No regressions: current public launch axes, artifact schemas, report claims,
  agent-facing contracts, and private/public eval boundaries remain intact
  unless explicitly migrated.

Verification: deterministic gates are `ruff check <touched files>`,
`ruff format --check <touched files>`,
`python scripts/dev/check_python_quality_ratchet.py --summary --top 40`, and
focused pytest via `./scripts/dev/run_pytest_standalone.sh <tests> -q`.
If eval, launch, or agent-facing files change, use
`just agent::eval recommend plan=docs/plans/refactor-python-quality-backend-entropy.md budget=focused`
or `just agent::eval execute ...` for gate selection. Product-run and
local-live-manual gates are required only when the selected slice changes a
public route or real simulator/provider claim.

Execution: main session supervises, integrates, and verifies. Prefer one
vertical slice when ownership overlaps; otherwise use the Parallel Acceleration
Policy above to run a small batch of independent slices and merge them one at a
time.
To execute:
`/goal execute docs/plans/refactor-python-quality-backend-entropy.md with intuitive-flow`.
Approval: LGTM/approve/go ahead approves; edits request revision.

## Active Candidates

### A: Scene Sampler Hard-Ceiling Drift

Severity: P1. `roboclaws/launch/scene_sampler.py` is now 2607 lines after the
scene-only prefilter owner split, so it improved but remains above the hard
ceiling. Owning architecture layers: Runnable Surfaces And Presets plus Eval
Suites, because sampler changes feed product/eval scene selection and
generated eval rows. Next slice should split another real sampler ownership
boundary, likely candidate profile, source prep, scanner execution planning,
or selection-gap assembly; alternatively link the separate active plan that
owns this drift. Proof: full scene-sampler focused tests, launch/eval tests if
touched, ruff, format check, and ratchet.

### B: Contract And Report Hard-Ceiling Split

Severity: P1. `roboclaws/household/realworld_contract.py` is 5036 lines and
`roboclaws/household/report.py` is 3806 lines. Owning architecture layers: MCP
Capability Contract And Tools for the contract facade, and Artifacts, reports,
and eval suites for report rendering. Continue only around real ownership
boundaries: payload builders, policy/event families, section renderers, or
artifact envelopes. Preserve public schemas and report claims.

### C: Visual Comparison Pipeline Split

Severity: P1. `roboclaws/household/scene_camera_comparison.py` and
`scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` remain
oversized. Prefer capture-lane stages, diagnostics builders, manifest/artifact
setup helpers, and report-specific modules. Owning architecture layers:
Backend Runtimes / Environment Primitives plus Artifacts, reports, and eval
suites. Real renderer claims still require separate local proof.

### D: Live Runtime And Eval Harness Entropy

Severity: P1 for hard-ceiling files, otherwise P2. Watch
`roboclaws/agents/drivers/openai_agents_live.py`,
`scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
`roboclaws/evals/live_runtime.py`, and
`skills/eval-harness/scripts/run_eval_harness.py`. Owning architecture layers:
Agent Engines And Provider Profiles, Thin Runtime / Server Adapters, and Eval
Suites. Normalize status/evidence envelopes only where it removes repeated
branching without changing public launch, report, or grader contracts.

### E: B1 Map 12 Label And Preview Tooling Complexity

Severity: P2, promoted to P1 if it blocks B1 map alignment proof or hides a
false-green review gate. Current rows include
`scripts/maps/render_b1_map12_label_tool.py::semantic_map_layers_from_semantics`,
`validate_label_draft_manifest`, and
`scripts/operator_console/render_scene_previews.py::render_b1_map12_preview`.
Owning architecture layers: Worlds / Scenes, Backend Runtimes / Environment
Primitives, and Artifacts, reports, and eval suites. The current dirty checkout
has two render-preview rows in this bucket; keep them with the same owner.

### F: Behavior-Test Fixture Builders

Severity: P2, promoted to P1 when a test file crosses the 2000-line hard
ceiling or hides a false-green gate. Current rows include operator-console
scene-preview/control/static-asset tests and a cleanup-checker fixture lookup
helper. Oversized behavior tests remain a large part of the top-40 list. Use
fixture builders and focused assertion helpers only when they make behavior
ownership easier to scan. Owning architecture layers follow the behavior under
test: operator console, reports/artifacts, eval suites, or launch surfaces.

### G: MCP Semantic Tool And Prompt Preview Complexity

Severity: P2, promoted to P1 only if tool registration or prompt preview drift
changes an agent-facing contract. Current rows include
`roboclaws/household/realworld_mcp_semantic_tools.py::register_semantic_cleanup_tools`
and `roboclaws/operator_console/prompt_preview.py::_goal_contract`. Owning
architecture layers: MCP Capability Contract And Tools plus Agent Skills.

### H: Agent Guidance Skill-Router Drift

Severity: P2. `AGENTS.md` and `CLAUDE.md` still mention
`hybrid-phase-pipeline`, while this environment exposes `intuitive-flow`.
Fix only if startup rediscovery continues to cost time. Keep it separate from
code-size slices. Owning layer: agent operating guidance, not product runtime.

### I: Stale Internal Surface Small-Cut Bundle

Severity: P2. Execute only as a scoped stale-surface deletion bundle or when a
nearby accepted slice already touches the same owner files. Current ponytail
inputs: legacy checker flag `--require-canonical-robot-view-camera-control`,
empty visual-grounding labeler maps, and duplicated current-doc lane prose.
Owning layers depend on the touched surface: Artifacts, reports, and eval
suites for checker/report claims; MCP Capability Contract And Tools or Agent
Skills for labeler/profile guidance. Behavior-change class is internal/stale
docs unless a public command, report claim, or artifact contract changes; stop
for a slice decision if that happens. Proof: affected checker or visual-
grounding tests when code changes, otherwise static grep/docs proof plus
ratchet.

### Cleared Or Parked

- Backend worker hard-ceiling split is cleared as of 2026-06-17; reopen only if
  `isaac_lab_backend_worker.py` or `molmospaces_subprocess_worker.py` crosses
  2000 lines again.
- `agibot_contract_rehearsal.py` remains below the hard ceiling; reopen only
  for fresh file-size, wrapper/import, or evidence-branching drift.
- Report-performance skill calibration drift is cleared as of 2026-06-17; the
  skill-local calibration script now delegates to the canonical
  `scripts/reports/calibrate_model_latency.py`. Reopen only for new
  skill/root script divergence.

## Ponytail Audit Triage

The 2026-06-17 repo-wide ponytail audit produced simplification candidates.
Use these as ratchet inputs, not as approval to change public contracts without
a slice gate.

- Accepted P1/P2 cleanup inputs:
  - Scene-sampler facade and legacy MolmoSpaces alias drift: already candidate
    A. Deleting public `molmospaces/val_*` aliases is a public launch-contract
    change and needs its own slice decision.
  - Report-performance skill scripts: calibration drift is cleared. The
    remaining thin metric wrappers are P2 only if a future skill packaging slice
    can point `SKILL.md` / `skill.json` at root scripts directly.
  - Contract extraction Protocols in `realworld_contract_payloads.py` and
    `realworld_done_readiness.py`: valid P2 concept-reduction targets inside
    candidate B, but only if the slice reduces facade/private-member coupling
    instead of just moving lines.
  - Legacy checker flag
    `--require-canonical-robot-view-camera-control`, empty visual-grounding
    labeler maps, and duplicated current-doc lane prose are candidate I, not
    ad hoc edits to unrelated owners.
- Parked unless a nearby accepted slice touches them:
  - `PhysicalObservationProvider` is low-value Protocol cleanup and belongs to
    a physical Nav2 pilot slice, not the main hard-ceiling pass.
  - General large behavior-test files remain candidate F, but ponytail did not
    justify deleting test coverage wholesale.

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
