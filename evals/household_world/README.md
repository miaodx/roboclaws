# Household World Eval Fixtures

This directory contains versioned eval-suite and eval-sample definitions for
the household-world capability. Run the deterministic smoke suite with:

```bash
just agent::eval suite=smoke_regression budget=smoke
```

Run the dedicated open-ended household goal suite with:

```bash
just agent::eval suite=open_ended_goals budget=smoke
```

The open-ended suite currently contains a negative drink-search sample, an
area-inspection sample, and a positive public-waypoint sample. Positive samples
grade against public runtime-map or trace evidence rather than private scorer
truth.

Run the map-build consumer suite with:

```bash
just agent::eval suite=map_build_consumer budget=smoke
```

Run repeated cleanup trials for `pass@k` and `pass^k` metrics with:

```bash
just agent::eval suite=cleanup_capability budget=smoke
```

Non-direct selections preserve live-agent identity and produce blocked
provider/runtime evidence unless live execution is explicitly requested:

```bash
just agent::eval suite=cleanup_capability budget=smoke agent_engine=codex-cli provider_profile=codex-env
```

Run an opt-in live provider route only when local provider/runtime requirements
are available:

```bash
just agent::eval suite=open_ended_goals budget=smoke \
  agent_engine=codex-cli provider_profile=codex-env \
  live_execution=run live_timeout_s=120
```

The smoke budget writes `output/evals/<suite>/<stamp>/eval_results.json`,
renders `eval_report.html`, and links each eval result back to the underlying
product run artifacts. Repeated suites keep every trial result visible in the
bundle and report `pass_at_k` plus `pass_caret_k`.

Promote a failed, blocked, or inconclusive result into a durable regression
sample with:

```bash
just agent::eval promote-regression \
  eval_results=output/evals/<suite>/<stamp>/eval_results.json \
  source_sample_id=<sample-id> \
  regression_sample_id=regression.<name>
```

Use `sample_output_path=...` and `suite_output_path=...` for review-local dry
runs. Promotion metadata keeps source artifacts and human review labels under
`private_goal_reference` with `private_truth_scope=grader_only`.
