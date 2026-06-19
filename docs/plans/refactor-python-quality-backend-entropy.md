---
refactor_scope: python-quality-backend-entropy
status: CONTINUE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-19
completed_ledger: docs/plans/refactor-python-quality-backend-entropy-completed.md
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

CONTINUE. This file is the active continuation control doc. Completed slices
live only in
`docs/plans/refactor-python-quality-backend-entropy-completed.md`; do not copy
their full execution notes back here.

Latest quality snapshot from 2026-06-19:

- Ruff complexity rows: 0.
- Oversized modules: 78.
- Current emphasis: fresh Ruff complexity rows are clear again. The latest
  fail-aloud slices surfaced malformed operator-console runtime inventory
  JSON, eval runtime-map artifacts, eval trace JSONL artifacts, and live eval
  surface JSON artifacts as explicit source-error evidence. Eval-harness
  provider readiness now rejects unknown provider profiles through the provider
  registry instead of treating them like the Codex router when Codex env vars
  happen to exist, and attached eval-harness `eval_results.json` files now
  fail rows aloud when present but malformed or non-object. Explicit
  eval-harness `since=` source refs now fail aloud when `git diff` cannot read
  them instead of producing an empty recommendation set. Operator-console prompt
  previews now reject malformed or negative OpenAI Agents numeric prompt-env
  values instead of rendering default-looking kickoff prompts for bad live-route
  input, and the operator-state payload now reports malformed core
  `operator_state.json` / `live_status.json` / `run_result.json` sources as
  explicit failed source errors instead of erasing them into idle or missing
  state. OpenAI Agents SDK model selection now rejects unknown model overrides,
  and provider/profile route selection rejects catalog-known models that belong
  to the wrong route instead of treating family-compatible names as launchable.
  Continue fail-aloud/runtime-source audits from fresh evidence rather than
  reopening closed helper splits; route any future test-shape cleanup through
  `$intuitive-tests`.

The next implementation run should start with a fresh ratchet summary and a
targeted audit of one owner boundary before editing code.

## Resume Checklist

1. Read the repo first-read set required by `AGENTS.md`.
2. Read `$intuitive-flow` and `$intuitive-refactor` before code changes.
3. Check `git status --short`; do not mix unrelated dirty files into this
   stream.
4. Refresh:

   ```bash
   python scripts/dev/check_python_quality_ratchet.py --summary --top 80
   ```

5. Pick one bounded, non-overlapping slice from `Active Candidates`.
6. Add or update focused regression proof before or with the code change.
7. Run the selected focused tests, touched-file static checks, `git diff
   --check`, and ratchet.
8. Update this plan and the completed ledger, then commit explicit paths only.

## Operating Rules

- Two-document contract: this active plan plus the completed ledger. Do not
  create a third cleanup plan or scratch log.
- One verified vertical slice beats broad line shaving. Each slice names its
  owner layer from `ARCHITECTURE.md`, behavior-change class, touched files,
  proof, and non-goals.
- Fail-aloud rule: missing, ambiguous, or inconsistent runtime/source metadata,
  route support, provider profile, env input, map bundle input, visual artifact,
  readiness fact, or config precedence should become an explicit exception,
  blocked/unavailable status, or operator-visible validation error.
- Keep deliberate public defaults only when they are part of a documented
  launch contract and visible in artifacts, readiness payloads, or provider
  diagnostics.
- Compaction rule: every 3-5 accepted slices, move outcomes into the ledger and
  trim this file back to unresolved decisions, current candidates, proof gates,
  and stop conditions.
- Default Python module target: under 800 lines. 800-1200 lines may be
  acceptable for one cohesive owner. 1200-2000 lines remains tracked warning
  debt. Non-generated, non-vendor files above 2000 lines are P1 unless a narrow
  exception is recorded.
- Unit-test pruning must run through `$intuitive-tests` audit/propose before
  deleting tests.
- Documentation cleanup must run through `$intuitive-doc` and keep the human
  surface focused on `README.md`, `ARCHITECTURE.md`, `STATUS.md`, and
  `docs/human/**`.
- Do not reopen closed owner splits without fresh inline ownership drift or a
  hard-ceiling regression.

## Next Slice Selector

Default order after the latest checkpoint:

1. **S: Fail-Aloud Silent Fallback And Env-Var Cleanup** when a false-green
   family is found.
2. **D: OpenAI Agents timing/timeline split** only if fresh evidence makes it
   the best frontier. Do not reopen the closed performance-profile/default
   owner.
3. **B: Visual comparison ownership** only around fresh scene-camera or
   visual-parity summary/report drift.
4. **A: Contract/report ownership** only with fresh facade-private coupling,
   report-section ownership drift, or hard-ceiling regression.
5. **T: Unit-test pruning** through `$intuitive-tests`.
6. **U: Human documentation cleanup** through `$intuitive-doc`.

Choose by fresh call-site, test-value, doc-truth, and false-confidence
evidence, not file size alone.

## Active Candidates

### S: Fail-Aloud Silent Fallback And Env-Var Cleanup

Severity: P1 when a fallback can create false confidence, hide a missing source
asset, mask unsupported launch/profile input, fabricate room/map/visual
semantics, mask missing or conflicting environment-variable input, or make a
route look ready when required evidence is absent. Severity: P2 for local
developer convenience with clear test coverage and no user-facing claim.

Possible owner layers:

- Runnable Surfaces And Presets for launch/profile normalization.
- Agent Engines And Provider Profiles for provider route defaults and model
  selection.
- Thin Runtime / Server Adapters for readiness and live status packets.
- Backend Runtime / Environment Primitive for simulator/map/source asset
  loading.
- Artifacts, reports, and eval suites for preview/report/evidence generation.

Audit the selected owner for `fallback`, `default`, `legacy`, `unknown`,
`synthetic`, `missing`, broad `except`, `or {}`, `or []`, `os.environ`,
`getenv`, `ROBOCLAWS_`, `_API_KEY`, `_BASE_URL`, `_MODEL`,
`provider_profile`, and `alias`. Classify every hit as public default,
explicit blocked/unavailable status, test fixture convenience, or silent
fallback before changing behavior.

Good next families:

- Runtime artifact discovery: report/preview claims should not reuse stale or
  substitute assets when real camera/map/robot-view evidence is absent.
- Environment-variable route selection: collapse duplicate knobs, remove stale
  aliases, reject conflicting key/base-url/model/profile combinations, and
  surface precedence.
- Provider route and launch profile input: unsupported values should fail
  visibly instead of falling back to another route.
- Source map / preview inputs: missing B1/Molmo labels, semantic labels, or
  preview metadata should not be fabricated.
- Worker initialization: required source metadata should fail before state
  write, not create plausible placeholder room/object/receptacle state.

Allowed fallbacks:

- Documented public launch defaults.
- Provider secrets and local proxy/mirror env vars that fail readiness when
  missing or conflicting.
- Explicit operator-console unavailable/blocked readiness states.
- Test fixtures that intentionally omit optional fields and assert the
  resulting error/blocked behavior.
- Historical artifact readers that preserve old reports without relabeling
  them as current product proof.

### T: Unnecessary Unit-Test Pruning

Route through `$intuitive-tests` first. Start with one domain, classify tests as
keep, merge, delete, or reclassify, and preserve the last meaningful proof of
parser behavior, validation, fail-aloud errors, public CLI/report/MCP
contracts, artifact schemas, provider route semantics, and known regressions.

Good families:

- Provider/env tests that duplicate constants or route tables without
  exercising canonical resolution, readiness failure, or visible diagnostics.
- Operator-console tests that assert static DOM/route wiring without launch
  readiness, redaction, locks, status transitions, or artifact links.
- Eval-harness tests that duplicate manifest keys one field at a time instead
  of proving selected rows, blockers, promotion packets, or result contracts.
- Molmo cleanup worker/report tests that assert helper shape, static file
  names, or copied fixture metadata already covered by stronger tests.

### U: Human Documentation Surface Cleanup

Route through `$intuitive-doc`. Human-authoritative scope is `README.md`,
`ARCHITECTURE.md`, `STATUS.md`, and `docs/human/**`. Process/evidence scope is
`.planning/**`, `docs/plans/**`, `docs/status/active/**`,
`docs/retrospectives/**`, ADR detail, `output/**`, generated reports, and
screenshots unless a curated human doc deliberately promotes a specific item.

Good families:

- Current-looking docs that still show historical command grammar, profile
  names, or retired route names as copyable commands.
- `docs/human/**` pages that duplicate README/ARCHITECTURE/STATUS tables but
  lag behind current launch architecture.
- Agent-only local harness or skill-routing notes that belong in
  `docs/agents/**`.
- Old proof/evidence detail in human docs where a short current summary plus a
  process/evidence link is enough.

### A: Contract And Report Hard-Ceiling Split

Currently not the default next slice. Reopen only with a fresh hard-ceiling
regression or direct facade-private/report ownership drift.

Closed or cohesive owners:

- Public map/projection construction:
  `realworld_contract_projection.py`.
- Agent-view and policy evidence packets:
  `realworld_contract_payloads.py`.
- Done-readiness pending/held cleanup candidates:
  `realworld_done_readiness.py`.
- Public manipulation/tool response envelopes:
  `realworld_tool_responses.py`.
- Visual-candidate lifecycle:
  `realworld_visual_candidate_lifecycle.py`.
- Camera-label producer inputs:
  `realworld_visual_candidate_declarations.py`.
- Runtime Metric Map target/public-anchor construction:
  `realworld_runtime_map_targets.py`.
- Proof-bundle result rendering:
  `report_sections_proof_bundle.py`.

Candidate A is valid only for a new `RealWorldCleanupContract` boundary such as
agent-view wrapper cleanup, runtime-map/cleanup-worklist caller migration,
remaining report-section ownership, or another named facade-private coupling
point.

### B: Visual Comparison Pipeline Split

Candidate B remains valid only around fresh scene-camera / visual-parity
ownership drift. Do not reopen closed boundaries without evidence that the
runner or summarizer is rebuilding those packets inline again.

Closed or cohesive owners:

- Scene-camera report rendering: `scene_camera_report*.py`.
- Apple image metrics and residual diagnostics:
  `robot_camera_apple2apple_image_metrics.py`.
- Apple object parity: `robot_camera_apple2apple_object_parity.py`.
- Selected RGB/focus/nonblank/crop evidence:
  `robot_camera_apple2apple_rgb_evidence.py`.
- Visual-state contract evidence:
  `robot_camera_apple2apple_visual_state.py`.
- Object Gate / Render Gate diagnostics:
  `robot_camera_apple2apple_object_gate.py`.
- Report rendering: `robot_camera_apple2apple_report.py`.
- Camera-contract diagnostics:
  `robot_camera_apple2apple_camera_contract.py`.
- Native Isaac render diagnostics:
  `robot_camera_apple2apple_native_render.py`.

Preserve runner orchestration, top-level manifest/report attachment, capture
worker boundaries, and artifact schemas unless explicitly selected.

### C: Planner Manipulation Probe Runner Split

Cleared from P1 for now. Reopen only if
`scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py` crosses 2000
lines again or starts rebuilding either closed owner directly.

Closed owners:

- Runtime/module/CUDA/headless diagnostics:
  `planner_probe_runtime_diagnostics.py`.
- Task-sampler robot placement, cleanup binding, sampler failure diagnostics,
  and binding promotion:
  `planner_probe_task_sampler_diagnostics.py`.

### D: OpenAI Agents Live Runtime / Runner Split

Candidate D is valid only for fresh runner/driver evidence. Keep SDK driver
internals separate from runner lifecycle.

Closed owners:

- Model-input compaction, raw-FPV/camera-grounded history policy, and metrics:
  `openai_agents_model_input.py`.
- Runner-side Agent SDK performance profile/default/config resolution:
  `scripts/molmo_cleanup/openai_agents_perf_profile.py`.
- SDK span capture:
  `openai_agents_spans.py`.

Possible later slice: timing/latency/timeline ownership. If selected, move
runner timing breakdown, live timing timeline, timeline segment builders,
latency attribution, MCP trace/control-plane timing, unattributed model seconds,
and compact metric groups to a focused owner while preserving
`live_timing.json`.

Non-goals unless explicitly approved: provider route semantics, model thinking
policy, MCP session behavior, continuation policy, checker gates, event/span
schemas, model-input compaction schemas, live-status payloads, and timing
artifact schemas.

### E-H: P2 Rows And Small Cuts

Use these only when they remove stale surface, duplicate concept, or false
confidence without postponing a stronger P1 frontier.

- Live runtime / eval harness rows:
  `roboclaws/evals/live_runtime.py::wait_for_live_surface_completion` and
  `skills/eval-harness/scripts/run_eval_harness.py::_row_blockers`.
- B1 preview row:
  `scripts/operator_console/render_scene_previews.py::render_b1_map12_preview`.
- Behavior-test fixture-builder work in selected operator-console tests.
- Stale small cuts: empty camera-labeler maps, `_task_prefix_legacy`, legacy
  checker flag `--require-canonical-robot-view-camera-control`, duplicated lane
  prose, and old `hybrid-phase-pipeline` guidance wording.

Treat the legacy checker flag as a checker-contract migration, not an
opportunistic delete. Keep public `camera_labeler` /
`visual_grounding_pipeline_id` semantics unless a selected slice explicitly
migrates them.

## Cleared Or Parked

Reopen these only with fresh hard-ceiling regression, direct owner drift, or a
product slice that needs them:

- Backend worker hard-ceiling split.
- Scene-sampler hard-ceiling split.
- Agibot contract rehearsal below-ceiling cleanup.
- Report-performance skill wrapper consolidation.
- `PhysicalObservationProvider`.
- Scene-sampler public alias removal.
- Broad behavior-test pruning.
- Closed owner families listed in `Active Candidates`.

## Evidence Ladder

- Static: `ruff check <touched files>`, `ruff format --check <touched files>`,
  and `python scripts/dev/check_python_quality_ratchet.py --summary --top 80`.
- If a future slice creates a new untracked Python owner, run
  `git add -N <path>` before relying on ratchet line-count output.
- Focused tests: use `./scripts/dev/run_pytest_standalone.sh <tests> -q`.
- Contract/report changes: include the relevant contract or report tests.
- Fail-aloud cleanup changes: include at least one regression test where the
  old path silently fabricated/substituted data and the new path raises a clear
  error or returns explicit blocked/unavailable status.
- Unit-test pruning: run focused collection plus the selected domain's
  remaining behavior/contract tests; include keep/merge/delete/reclassify
  counts.
- Documentation cleanup: use `$intuitive-doc` audit/cleanup rules, verify stale
  claims and path consumers with `rg`, and run command/doc build checks only
  when changed runbook commands need validation.
- Changed-code review: after non-doc implementation, run `$intuitive-refactor`
  changed-code review on the changed scope before final verification.
- Agent-facing/eval/launch changes: prefer `just agent::eval recommend` or
  `just agent::eval execute` for gate selection.
- Simulator/live claims: claim them only after an explicit local run on a ready
  environment.
- Docs-only planning refresh: `git diff --check` is enough; do not run behavior
  tests when no code or contracts changed.

## Commit Notes Template

For each completed implementation slice, append one compact bullet to the
completed ledger with:

- durable behavior or ownership effect;
- owner layer;
- behavior-change class;
- metric delta when relevant;
- proof class;
- closed/reopen rule when the slice establishes an owner boundary.

Then update this file only when candidate ordering, stop conditions, or reopen
rules changed.

## Stop Condition

Stop this cleanup stream only after a fresh completion audit proves all of the
following:

- Non-generated, non-vendor files above 2000 lines are split below the ceiling
  or have a recorded narrow exception.
- Production/shared Ruff complexity rows are at or near zero.
- Remaining test complexity is fixture-builder debt with clear ownership, not
  one-off long test bodies.
- Low-signal unit tests in accepted domains have been deleted, merged, or
  reclassified, and remaining unit tests protect behavior/failure modes rather
  than static implementation shape.
- Backend id, runtime metadata, artifacts, and evidence attachments use common
  surfaces instead of repeated concrete-class or `backend == ...` branching.
- Silent fallback families that can create false confidence are removed,
  converted to explicit blocked/unavailable status, or documented as deliberate
  public defaults with tests.
- Env-var families no longer provide hidden route compatibility: canonical
  knobs are documented, duplicate aliases are removed or explicitly blocked,
  precedence is tested, and missing/conflicting provider keys, base URLs, or
  model/profile settings fail before launch readiness.
- The curated human documentation surface is small and current: README,
  ARCHITECTURE, STATUS, and `docs/human/**` describe active project truth;
  stale commands/routes/profile names are gone or historical outside the human
  surface; agent-only runbooks and execution evidence live in agent/process
  surfaces with current links.
- A fresh reduce-entropy round finds no P0/P1 or material P2 candidate in this
  code-size/backend-complexity class.
