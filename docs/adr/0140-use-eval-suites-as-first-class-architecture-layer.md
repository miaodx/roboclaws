# ADR-0140: Use Eval Suites As First-Class Architecture Layer

Status: Accepted

Date: 2026-06-15

## Context

Roboclaws already has reviewable product runs, private scorer boundaries,
reports, harness recipes, and an adaptive validation matrix. Those pieces prove
different things, but without a first-class evaluation layer future agents can
collapse them into one vague "harness" concept.

The repo now needs a durable way to ask whether household-world and planner
proof capabilities are improving over time across versioned samples, repeated
trials, graders, and failure classes.

## Decision

Use four separate architecture layers:

- Product run: `just run::surface ...` remains the operator-facing execution
  contract.
- Validation matrix: `just agent::harness agent-validation ...` selects and
  records which gates a plan, diff, or axis set must validate.
- Eval suite: versioned repo-owned capability benchmarks made of samples,
  trials, graders, aggregate metrics, and replayable failure evidence.
- Harness recipes: lower-level runners and specialist probes used by product,
  validation, and eval flows.

The first eval facade is a maintainer command under `just agent::eval ...`.
It is not a replacement for `just run::surface`, and it does not make evals a
normal operator product-run namespace.

Start with repo-native eval suite definitions and `roboclaws/evals/` support
code. Do not adopt Inspect AI or another third-party eval framework until the
first internal deterministic suite proves what framework support is actually
needed.

Eval results must record comparable identity, artifacts, grader outputs,
failure class, limitations, and budgets. Deterministic artifact, state,
trajectory, privacy, and efficiency graders are authoritative for safety and
private-boundary failures; model or human rubric graders are advisory until
calibrated.

Current public/private and MCP/tool contracts remain authoritative for eval
trajectory grading. In particular, ADR-0136's Base Navigation Map and Runtime
Metric Map direction applies to evals: cleanup should not revive a
fixture-hints-first MCP habit, while historical artifact fields may remain
readable for report and map compatibility.

## Rejected Alternatives

- Treat the validation matrix as the eval system. Rejected because it answers
  which gates should run for a change, not whether capability improves over a
  versioned sample set.
- Treat harness recipes as the conceptual source of truth. Rejected because
  recipes are execution mechanics, not product capability benchmarks.
- Put evals under the public `run::*` surface first. Rejected because evals are
  maintainer benchmarking workflows, not ordinary operator runs.
- Adopt a third-party eval framework before the first internal suite. Rejected
  because Roboclaws needs to discover its own sample, artifact, scorer, and
  privacy contracts first.
- Let LLM rubric graders override deterministic privacy, safety, or private
  scorer failures. Rejected because that would weaken the public/private
  boundary.

## Consequences

- The implementation plan is
  `docs/plans/2026-06-14-eval-driven-architecture.md`.
- Architecture and human docs should distinguish product runs, validation
  matrices, eval suites, and harness recipes.
- `just agent::eval ...` is the first expected eval command shape unless a
  later ADR changes the public contract.
- Eval implementation should begin with deterministic household suites and add
  live-agent repetition and `pass^k` only after deterministic semantics are
  stable.
- Existing `just run::surface`, `agent-validation-matrix`, and harness recipes
  remain valid in their own layers.
