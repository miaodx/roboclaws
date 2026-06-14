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

Keep private scorer truth private. Generated mess sets, acceptable destinations,
hidden target lists, and private manifests may feed graders and reports, but
they must not appear in agent-facing MCP inputs or capability profile metadata.
Cleanup evals should classify a live `fixture_hints` MCP call as a trajectory
violation while allowing historical artifact fields with the same name to remain
readable for reports and map-bundle compatibility.
