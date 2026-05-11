# MolmoSpaces Generated Fallback Proof Execution

## Goal

Execute generated fallback proof requests locally against the RBY1M/CuRobo
planner path and summarize whether any alternate planner alias request produces
planner-backed proof that can promote cleanup primitive binding.

## Scope

- Use an ADR-0003 `molmospaces_subprocess` cleanup artifact with private proof
  request metadata.
- Use a prior proof-result summary that marks the exact source requests as
  task-feasibility blocked.
- Run the proof-bundle runner with task-feasibility exclusion and fallback
  request generation enabled.
- Execute the generated fallback probe commands locally.
- Validate the runner manifest/report with required proof outputs.
- Record the outcome as local-dev evidence without claiming cleanup primitive
  replacement unless strict proof and binding promotion actually pass.

## Acceptance

- The runner manifest contains generated fallback requests and executed proof
  outputs.
- The runner checker passes with `--require-proof-outputs`.
- The proof result summary reports per-fallback status, task feasibility,
  blockers, binding promotion, and any planner views.
- The phase result states whether generated fallback requests are enough for
  cleanup primitive promotion or what blocker remains.

## Out Of Scope

- Changing fallback generation logic unless execution exposes a concrete bug.
- Making generated fallbacks pass by relaxing strict validation.
- Treating a blocked proof output as planner-backed cleanup success.

## Result

Completed on 2026-05-10 as local-dev evidence.

Output artifact:
`output/debug-phase58-fallback-execute/proof_bundle_run_manifest.json`
with report `output/debug-phase58-fallback-execute/report.html`.

The runner generated and executed four fallback proof requests from two prior
task-feasibility-blocked source requests. The checker passed with required
proof outputs:

```bash
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py \
  --require-proof-outputs output/debug-phase58-fallback-execute
```

Result summary:

- `status=probes_executed`
- `command_count=4`
- generated fallback requests: 4
- planner-backed proofs: 0
- cleanup binding promotions: 0
- task-feasibility blocked proofs: 0
- planner view artifacts: 0

All four generated fallback probes reported `blocked_capability` with blocker
`timeout`. Their last worker stage was `rby1m_config_import`, so they did not
reach task sampling, sampled-task binding, cleanup primitive binding promotion,
or planner view capture. Generated fallback requests are therefore not enough
for cleanup primitive promotion yet. The next blocker is target-runtime
warmup/JIT progress for generated fallback execution, not missing fallback
request generation.
