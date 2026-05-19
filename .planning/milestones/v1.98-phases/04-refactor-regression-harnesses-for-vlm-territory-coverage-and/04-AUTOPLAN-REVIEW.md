<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0423-autoplan-restore-20260423-205957.md -->
---
phase: 04
kind: autoplan-review
date: 2026-04-23
status: approved-with-auto-fixes
review_target: .planning/milestones/v1.98-phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and
---

# Phase 04 Autoplan Review

## Verdict

Approved with auto-fixes.

The phase is worth doing. The repo already has the right underlying pattern:
thin capture entrypoints, append-only experiment rows, replay artifacts, and a
separate analyzer on `view_experiment`. The main risk was not direction. It was
honesty and authority: the original draft blurred cloud-safe plumbing proof with
real behavioral proof, and it did not define how repeated baseline refreshes
stay auditable over time.

The review tightened those seams instead of expanding scope. The plans now say
truthfully which suites are local-only, freeze the shared row contract more
explicitly, recover `openclaw-demo` metrics from existing replay artifacts
instead of inventing new runner return shapes, require immutable capture-set
labels plus per-run metadata, and make the first local workflow proof honest
about same-commit baseline/candidate runs.

## Findings Fixed During Review

1. `04-02-direct-vlm-and-game-capture-suites-PLAN.md` implied direct-VLM
   behavioral capture was cloud-safe.
   The fix separates truthful cloud-safe synthetic coverage from real
   direct-VLM capture, which now stays explicitly local-only or otherwise fully
   provisioned.

2. The bundle did not define a durable authority model for repeated captures.
   The fix requires immutable capture-set labels such as
   `baseline-2026-04-23` and `candidate-dongxu-dev-0423`, plus per-run
   metadata fields including `run_id`, `captured_at`, `commit_sha`, and
   `schema_version`.

3. The shared row contract was under-specified.
   The fix adds a fixture-backed common row contract in Plan 01 and makes
   `artifact_dir` part of the required shape so repeated coordinates cannot
   silently clobber evidence.

4. `04-RESEARCH.md` and `04-03-openclaw-capture-suites-PLAN.md` assumed
   `examples/openclaw_demo.py` returned `visited_cells` directly.
   The fix corrects metric provenance: `visited_cells` comes from replay step
   state today, with optional additive summary work only if it lands cheaply.

5. The local workflow draft drifted from the repo's actual operator setup.
   The fix adds `.env` sourcing to the local preflight and aligns the workflow
   with the `.env` + AI2-THOR + Docker guidance in `AGENTS.md`.

6. The first proof recipe was ambiguous enough to invite misleading evidence.
   The fix explicitly allows a same-commit baseline/candidate pair for the
   first plumbing proof, but requires the write-up to label it as a
   workflow-proof pair rather than a real before/after refactor comparison.

## Auto-Decisions

- Keep the phase as one bundle. The problems are tightly coupled: contract
  freezing, capture, compare, and operator workflow all need one coherent row
  model.
- Skip Design review. This phase changes CLI scripts, docs, JSONL rows, and
  local operator workflow, but it does not introduce repo-owned frontend
  screens or component/UI design work.
- Prefer extracting missing metrics from existing replay artifacts over adding
  new return-shape obligations to shipped example runners.
- Use immutable capture-set labels instead of mutable `baseline/` and
  `candidate/` buckets as the authority model for baseline history.

## Review Scores

| Review | Score | Notes |
|--------|-------|-------|
| CEO | 8/10 | Right problem and right general seam choice. Needed tighter honesty around cloud/local proof and better baseline-history semantics. |
| Design | skipped | No meaningful frontend/UI scope in the repo sense. |
| Engineering | 8/10 | Strong leverage from existing runners and `view_experiment`; main issues were contract gaps, provenance mistakes, and repeatability semantics. |
| DX | 8/10 | Good maintainer intent. Needed clearer operator docs, truthful local-only boundaries, and a less ambiguous first-proof workflow. |

## CEO Review

### Premise Challenge

- Accepted: the repo needs a regression harness for refactors that touch direct
  VLM, territory/coverage game logic, and OpenClaw capture/analyze workflows.
- Accepted: the right starting point is the existing
  `examples/view_experiment.py` plus `scripts/analyze_view_experiment.py`
  split, not a new monolithic harness.
- Rejected: any wording that treats real direct-VLM behavioral capture as
  cloud-safe. That is not true on this repo's actual runtime model.
- Added: baseline authority must be explicit. Append-only history without
  immutable capture-set labels and per-run metadata is not enough once
  maintainers start refreshing baselines over time.

### Existing Code Leverage Map

| Sub-problem | Existing seam | Why it matters |
|-------------|---------------|----------------|
| Thin capture/analyze split | `examples/view_experiment.py`, `scripts/analyze_view_experiment.py` | The repo already has the pattern this phase should generalize. |
| Direct-VLM game entrypoints | `examples/single_agent_explore.py`, `examples/territory_game.py`, `examples/coverage_game.py` | The phase can reuse shipped runners instead of forking control loops. |
| Replay and contract surfaces | `roboclaws/core/replay.py`, `roboclaws/core/views.py`, `tests/fixtures/trace_schema_reference.json` | Hard contracts already exist and only need a smaller explicit layer where gaps remain. |
| Operator drill-down | `roboclaws.core.reporter.compare()` | HTML replay comparison already exists for human inspection; the phase adds machine gating, not a new visualizer. |
| OpenClaw autonomous summaries | `examples/openclaw_nav_autonomous.py`, `scripts/render_autonomous_replay.py` | The autonomous path already emits analyzable artifacts and should stay separate from push-model suites. |

### Dream State Mapping

```text
CURRENT
  shipped runners and replay artifacts exist
  -> contracts are partly implicit
  -> baseline refresh history is ad hoc
  -> cloud-safe vs local-only proof is easy to blur

THIS PHASE
  freeze the cross-cutting contracts
  -> capture append-only rows with stable pairing keys
  -> keep per-run artifact dirs and immutable capture-set labels
  -> compare baseline vs candidate with suite-specific thresholds
  -> document the real local workflow honestly

12-MONTH IDEAL
  maintainers refresh evidence-backed baselines deliberately
  -> capture rows are stable inputs to CI-adjacent analysis
  -> local-only proof is easy to reproduce
  -> future refactors answer "did behavior stay within tolerance?" quickly
```

### Implementation Alternatives

| Option | Effort | Pros | Cons | Verdict |
|--------|--------|------|------|---------|
| One giant end-to-end regression driver | medium | One command, one file | Blurs capture/analyze/contracts, hard to test, wrong blast radius | Reject |
| Shared suite helpers plus capture CLI and compare CLI | medium | Matches repo pattern, monkeypatchable, preserves local-only boundaries | Needs explicit row and threshold contracts | Approve |
| Exact replay equality for real-model behavior | low implementation, high pain | Simple assertion story | Not robust for real VLM/Gateway runs | Reject |
| Add new return values to every runner | medium | Fewer replay reads | Expands public runner contracts and duplicates data already on disk | Reject |

### NOT in Scope

- A new generic benchmark product or long-lived artifact storage system.
- Rewriting the example runners into harness-owned control loops.
- UI/design work beyond operator-facing docs and command examples.
- Claiming real behavioral validation from a cloud-only session.

### Error & Rescue Registry

| Risk | Rescue |
|------|--------|
| Real direct-VLM capture is run in an unprovisioned session | Emit actionable error rows or stop loudly; do not fake cloud-safe proof |
| Repeated coordinates overwrite prior evidence | Require unique per-run artifact dirs and record `artifact_dir` in the row |
| Baseline history becomes ambiguous across refreshes | Use immutable capture-set labels plus `run_id`, `captured_at`, and `commit_sha` |
| OpenClaw metrics are missing from direct runner returns | Read from replay summaries or replay step state where already available |
| First local proof is misrepresented as a real regression comparison | Require same-commit workflow proofs to be labeled explicitly in `04-LOCAL-PROBE-RESULTS.md` |

### CEO Outside Voices

| Voice | Status | Notes |
|-------|--------|-------|
| Claude subagent | unavailable | Session policy for this run did not permit delegation, so no Claude-side parallel review was used. |
| Codex CLI | partial but useful | Could not inspect the repo directly in its own sandbox, but a self-contained prompt produced valid strategic findings. |

The Codex review materially improved the plan in three places: it pushed for a
real run-identity model, called out the unsupported cloud-safe direct-VLM
claim, and surfaced the need for an explicit baseline authority model rather
than just append-only history.

### CEO Completion Summary

| Item | Result |
|------|--------|
| Premises valid? | yes, after tightening cloud/local truthfulness |
| Right problem to solve? | yes |
| Scope calibration | correct after auto-fixes; no split needed |
| Alternatives explored | yes |
| Dream state delta | written |
| NOT in scope | written |

## Engineering Review

### Architecture ASCII Diagram

```text
existing runners / artifact producers

direct VLM / game examples
  -> structured return dict
  -> replay.json

OpenClaw push-model
  -> runner return dict
  -> replay.json with per-step game_state

OpenClaw autonomous
  -> run_result.json
  -> trace.jsonl
  -> summary.json via render_autonomous_replay.py

Phase 04 harness

roboclaws/regression.py
  -> suite registry
  -> stable pairing-key helpers
  -> row normalization
  -> per-suite metric extractors

scripts/capture_refactor_regression.py
  -> iterate suite x scene x seed
  -> write append-only results.jsonl
  -> store artifacts under <label>/<suite>/<coord>/<run-id>/

scripts/analyze_refactor_regression.py
  -> pair rows on stable coordinates
  -> apply suite-specific threshold policy
  -> emit summary.md + summary.json
  -> non-zero exit on breach
```

### What Already Exists

- `roboclaws/core/views.py` already freezes the prompt image label/order
  contract that refactors must not silently break.
- `roboclaws/core/replay.py` already writes a stable replay envelope with
  machine-readable metadata and summary fields.
- `tests/fixtures/trace_schema_reference.json` already defines the exact vs
  additive schema posture for OpenClaw trace payloads.
- `scripts/generate_demo_report.py` already proves the repo has a cloud-safe
  mocked capture pattern for plumbing coverage.
- The example runners already expose most metrics Phase 04 needs without
  creating a parallel execution stack.

### Failure Modes Registry

| Failure mode | Severity | Plan fix |
|--------------|----------|----------|
| Shared row schema drifts per suite | high | Plan 01 freezes a common row contract fixture |
| Mutable labels make later baseline refreshes unauditable | high | Immutable capture-set labels plus run metadata |
| Direct-VLM capture path is described as cloud-safe when it is not | high | Plan 02 now states the local-only boundary explicitly |
| `openclaw-demo` metrics are sourced from the wrong place | high | Plan 03 now names replay step-state provenance |
| Analyzer thresholds apply one global policy to unlike suites | medium | Plan 04 uses explicit per-suite thresholds |
| First local proof overclaims what was validated | medium | Plan 04 requires exact commands, coordinates, labels, and workflow-proof labeling |

### Test Diagram

```text
Plan 01
  contract fixtures
  -> prompt image label/order test
  -> replay summary required-key test
  -> row contract normalization test

Plan 02
  direct VLM suites registered
  -> fake-suite / monkeypatch coverage
  -> append-only results.jsonl behavior
  -> error-row continuation behavior

Plan 03
  OpenClaw push-model + autonomous suites
  -> replay-summary / replay-step extraction tests
  -> local-only guard coverage

Plan 04
  analyzer
  -> stable-coordinate pairing tests
  -> threshold breach tests
  -> exact-check tests such as transcript source
  -> operator docs
  -> first local probe evidence
```

### Test Plan Artifact

`/home/mi/.gstack/projects/MiaoDX-roboclaws/mi-dongxu-dev-0423-eng-review-test-plan-20260423-214900.md`

### Engineering Completion Summary

| Item | Result |
|------|--------|
| Existing seams reused? | yes |
| Parallel stack avoided? | yes |
| Contracts explicit enough? | yes, after auto-fixes |
| Failure modes mapped? | yes |
| Test shape coherent? | yes |

## DX Review

### Primary User

Repo maintainer or refactor author on a real local workstation with AI2-THOR,
provider credentials, and sometimes OpenClaw Gateway available.

### Main DX Risks

- Running capture commands that look official but only prove mocked plumbing.
- Losing track of which baseline a candidate was compared against.
- Re-running the same coordinate and accidentally overwriting the prior
  evidence.
- Having the first local probe produce a pass/fail result that is impossible to
  interpret later.

### DX Fixes Accepted

- The docs/workflow now require immutable capture-set labels instead of vague
  reusable `baseline` / `candidate` buckets.
- The local preflight now starts with sourcing `.env`, which matches actual repo
  operator guidance.
- The first proof recipe now records whether it was same-commit plumbing proof
  or a true before/after comparison.
- The plans stay operator-facing and avoid inventing a second mental model apart
  from the existing runners.

### DX Completion Summary

| Item | Result |
|------|--------|
| Operator workflow truthful? | yes, after fixes |
| Cloud/local split explicit? | yes |
| Baseline history auditable? | yes |
| First-run ambiguity removed? | yes |

## Decision Audit Trail

- Accepted: reuse shipped example runners and existing replay artifacts.
- Accepted: suite-specific analyzer thresholds rather than one global threshold.
- Accepted: immutable capture-set labels and per-run metadata as the baseline
  authority model.
- Accepted: same-commit workflow-proof pair for the very first local evidence,
  but only with explicit write-up language.
- Rejected: new harness-owned execution loops.
- Rejected: treating cloud-safe synthetic tests as real behavioral proof.
- Rejected: Design review for a non-UI phase.

## Cross-Phase Themes

- The repo keeps paying for the same lesson: separate exact-contract surfaces
  from behavioral tolerances.
- Honest cloud/local boundaries are part of the architecture here, not merely
  documentation polish.
- Existing artifacts already carry more value than their current docs admit; the
  best refactors reuse them rather than widen public contracts casually.

## Approval Gate

No blockers remain after the auto-fixes.

If you want to override anything before execution, the only decisions worth
reopening are:

1. Whether immutable capture-set labels should be mandatory, or merely
   recommended.
2. Whether the first local proof may use a same-commit baseline/candidate pair,
   or whether you want to require a deliberately perturbed candidate instead.
3. Whether to keep this as one execution phase or split the local probe/write-up
   into a follow-on phase.

My recommendation is to keep the auto-decisions as written and hand this bundle
to GSD for execution when you want to start building.
