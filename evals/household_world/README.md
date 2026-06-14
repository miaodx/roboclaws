# Household World Eval Fixtures

This directory contains versioned eval-suite and eval-sample definitions for
the household-world capability. Run the deterministic smoke suite with:

```bash
just agent::eval suite=smoke_regression budget=smoke
```

Run the map-build consumer and open-ended artifact-readiness suite with:

```bash
just agent::eval suite=map_build_consumer budget=smoke
```

Run repeated cleanup trials for `pass@k` and `pass^k` metrics with:

```bash
just agent::eval suite=cleanup_capability budget=smoke
```

Non-direct selections preserve live-agent identity and produce blocked
provider/runtime evidence until a supported live eval runtime is available:

```bash
just agent::eval suite=cleanup_capability budget=smoke agent_engine=codex-cli provider_profile=codex-env
```

The smoke budget writes `output/evals/<suite>/<stamp>/eval_results.json`,
renders `eval_report.html`, and links each eval result back to the underlying
product run artifacts. Repeated suites keep every trial result visible in the
bundle and report `pass_at_k` plus `pass_caret_k`.
