# ADR-0141: Use Eval Harness As Maintainer Orchestration Facade

Status: Accepted

Date: 2026-06-15

Supersedes: ADR-0140 maintainer-facade wording for the separate
`agent-validation-matrix` entrypoint.

## Context

ADR-0140 made eval suites a first-class architecture layer and separated product
runs, validation matrices, eval suites, and harness recipes. That was useful
while the eval layer was being introduced, but it left maintainers with two
competing user-facing proof entrypoints:

- `agent-validation-matrix` for "what should this plan or diff validate?"
- `just agent::eval ...` for "did this capability improve or regress?"

That split creates repeated explanation burden and false-confidence risk. A
user asking for agent capability evaluation can accidentally receive only a
deterministic validation recommendation unless the live-agent eval path is
selected and reported explicitly.

## Decision

Use `eval-harness` as the single maintained validation/eval orchestration
facade.

Canonical entrypoints:

```bash
just agent::eval recommend plan=docs/plans/example.md budget=focused
just agent::eval execute since=origin/main budget=focused
just agent::eval suite=cleanup_capability budget=smoke
just agent::eval promote-regression eval_results=output/evals/<suite>/<stamp>/eval_results.json ...
```

The separate `agent-validation-matrix` skill and active
`just agent::harness agent-validation ...` route are removed without a
compatibility shim.

The conceptual layers remain distinct:

- Product run: `just run::surface ...` remains the operator-facing run contract.
- Eval harness: selects and executes relevant deterministic gates, product
  rows, eval-suite rows, live-agent eval rows, manual review rows, and
  regression-promotion guidance for a plan, diff, or explicit request.
- Eval suite: versioned benchmark artifacts made of samples, trials, graders,
  aggregate metrics, and replayable failure evidence.
- Harness recipes: private low-level execution mechanics used by product and
  eval flows.

Focused and full eval-harness execution must not silently turn selected
live-agent evals into deterministic-only success. Selected live rows either run
after non-secret preflight or record explicit blocked evidence such as
`model_or_provider_unavailable` or `environment_blocked`.

Eval-harness manifests may link maintainer-only private artifacts, but they must
not inline private scorer truth, hidden targets, acceptable destinations,
generated mess sets, private manifests, or raw provider logs.

## Rejected Alternatives

- Keep `agent-validation-matrix` as a compatibility alias. Rejected because the
  user-facing split is the problem being removed.
- Add `just agent::eval-harness ...` beside `just agent::eval ...`. Rejected
  because it would create another prominent eval entrypoint.
- Make deterministic direct-runner suites stand in for selected live-agent
  evals. Rejected because that hides provider/runtime/agent-route risk.
- Add an LLM selector first. Rejected because deterministic rule-table parity is
  easier to audit and preserves the useful prior selector behavior.

## Consequences

- Maintained docs should point users to `@eval-harness` and
  `just agent::eval recommend|execute|suite|promote-regression`.
- `skills/eval-harness/` owns the maintainer orchestration skill and manifest
  schema `roboclaws_eval_harness_manifest_v1`.
- Historical plans and retrospectives may retain old
  `agent-validation-matrix` evidence links, but active first-read docs,
  command examples, and tests should not recommend the old route.
- Eval suites remain first-class benchmark artifacts under the facade; they are
  not collapsed into ad hoc command rows.
