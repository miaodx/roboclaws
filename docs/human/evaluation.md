# Evaluation Suites

Roboclaws uses four related but separate proof layers:

| Layer | Command shape | Owns |
| --- | --- | --- |
| Product run | `just run::surface ...` | One operator-facing run with prompt, surface, world, backend, agent engine, evidence lane, artifacts, and report. |
| Validation matrix | `just agent::harness agent-validation ...` | Diff- or plan-aware selection of gates that must run for a change. |
| Eval suite | `just agent::eval ...` | Versioned capability benchmark across samples, trials, graders, aggregate metrics, and failure replay. |
| Harness recipe | `harness::*` or lower private recipes | Specialist execution mechanics used by product runs, validation gates, and eval suites. |

An eval suite answers whether a capability is improving over time, not whether a
single demo happened to complete. The expected flow is:

```text
eval_suite
  -> eval_sample
  -> environment reset
  -> agent trial
  -> trace and artifacts
  -> deterministic and optional advisory graders
  -> aggregate metrics
  -> failure replay or regression sample
```

Initial household graders should cover artifacts, final state/outcome,
trajectory, privacy, and efficiency. Deterministic privacy and safety failures
are authoritative; model or human rubric graders are advisory until calibrated.

Eval results must record enough identity to compare runs: suite/sample/trial,
surface, intent, preset, world, backend, evidence lane, camera labeler, scenario
setup, seed, prompt or goal hash, agent engine, provider/model, skill source,
MCP profile/tool surface, runtime limits, budgets, and artifact schema versions.
Missing relevant fields should be explicit `unavailable` or `not_applicable`.

The current repo-native schema package is `roboclaws.evals`. Versioned suite and
sample definitions live under `evals/<capability>/`, starting with
`evals/household_world/`.

The deterministic runner is available through:

```bash
just agent::eval suite=smoke_regression budget=smoke
just agent::eval suite=map_build_consumer budget=smoke
just agent::eval suite=cleanup_capability budget=smoke
```

These suites run direct-runner household samples without provider keys, write
`output/evals/<suite>/<stamp>/eval_results.json`, and render
`eval_report.html` with links to the underlying product run artifacts. Smoke
budget uses the synthetic cleanup backend for local determinism while eval
identity still records the sample's public surface, world, backend, evidence
lane, and missing live-provider fields explicitly.

`cleanup_capability` records repeated cleanup trials and reports `pass@k` plus
`pass^k` aggregate metrics. Live-agent eval identity can be requested with
`agent_engine=... provider_profile=...`; by default those trials are recorded
as blocked identity/preflight packets so provider-backed work is not launched
by accident. Use `live_execution=run` only when you intend to run the selected
live provider route. The live bridge calls the public `run::surface` product
route, pins an eval-owned `run_dir`, discovers timestamped product artifacts
when needed, and waits for detached Codex CLI cleanup artifacts before grading:

```bash
just agent::eval suite=cleanup_capability budget=smoke \
  agent_engine=openai-agents-sdk provider_profile=codex-env \
  live_execution=run live_timeout_s=120
```

For Codex CLI live evals, the eval runner passes a fixed product `run_dir`
through the public `run::surface` route and waits for detached live artifacts
before grading. The eval result still records blocked provider/runtime
conditions separately from agent behavior when the selected live route cannot
finish.

Blocked live-agent packets include either `roboclaws_live_eval_preflight_v1`
runner metadata, or a live product-route failure classified separately from
agent behavior failures. Provider 5xx/429/model-service failures are
`model_or_provider_unavailable`; missing simulator/runtime dependencies are
`environment_blocked`.

Failed, blocked, or inconclusive eval results can be promoted into a durable
regression sample with:

```bash
just agent::eval promote-regression \
  eval_results=output/evals/<suite>/<stamp>/eval_results.json \
  source_sample_id=<sample-id> \
  regression_sample_id=regression.<name>
```

By default this writes a sample under `evals/household_world/samples/regressions/`
and updates the source suite manifest. Use `sample_output_path=...` and
`suite_output_path=...` for dry runs or review-local promotion artifacts. Human
review labels are `eval-regression:accepted`,
`eval-regression:needs-human-review`, and `eval-regression:do-not-promote`; the
last label is a stop label and will not write a sample.

Keep private scorer truth private. Generated mess sets, acceptable destinations,
hidden target lists, and private manifests may feed graders and reports, but
they must not appear in agent-facing MCP inputs or capability profile metadata.
Cleanup evals should classify a live `fixture_hints` MCP call as a trajectory
violation while allowing historical artifact fields with the same name to remain
readable for reports and map-bundle compatibility. Regression promotion records
source result links and human labels inside `private_goal_reference` with
`private_truth_scope=grader_only`; that reference is grader input, not agent
input.
