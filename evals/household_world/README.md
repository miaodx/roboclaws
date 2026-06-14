# Household World Eval Fixtures

This directory contains versioned eval-suite and eval-sample definitions for
the household-world capability. Run the first deterministic suite with:

```bash
just agent::eval suite=smoke_regression budget=smoke
```

The smoke budget writes `output/evals/<suite>/<stamp>/eval_results.json`,
renders `eval_report.html`, and links each eval result back to the underlying
product run artifacts.
