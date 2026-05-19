# 28-01 RBY1M CuRobo Runtime Gate Plan

## Goal

Create a first-class RBY1M/CuRobo readiness gate so later planner-backed
cleanup primitive replacement cannot accidentally depend on standalone Franka
proof or generic planner diagnostics.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [x] Add an RBY1M/CuRobo gate builder that derives readiness from planner probe
   artifacts.
3. [x] Render the gate in the shared planner probe report.
4. [x] Add checker modes:
   - accept explicit blocked-capability evidence for CuRobo/current
     RBY1M blockers;
   - require strict RBY1M/CuRobo readiness for future cleanup primitive
     replacement.
5. [x] Add focused tests and generate/validate a local RBY1M artifact.

## Outcome

Planner probe artifacts now include `rby1m_curobo_gate`, and the shared planner
probe report renders `RBY1M CuRobo Gate`. The checker can accept current
missing-CuRobo evidence explicitly or require strict RBY1M/CuRobo readiness.

The local RBY1M probe remains blocked. After installing the pinned CuRobo extra
and CUDA PyTorch into the isolated MolmoSpaces runtime, CuRobo is importable,
but the RBY1M config-import probe still times out during CuRobo CUDA-extension
JIT warmup before planner execution can be attempted. This is the expected
honest state: standalone Franka proof remains useful planner evidence, but it
does not satisfy target RBY1M/CuRobo readiness.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_rby1m_curobo_gate.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py`
- `CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=8.9 .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py --output-dir output/molmo-planner-rby1m-curobo-gate --embodiment rby1m --probe-mode config_import --steps 2 --timeout-s 60`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked output/molmo-planner-rby1m-curobo-gate/run_result.json`
- Strict gate should reject the same artifact with
  `--require-rby1m-curobo-ready` unless the local runtime genuinely has RBY1M
  CuRobo planner execution.

Evidence:

- Artifact: `output/molmo-planner-rby1m-curobo-gate/report.html`.
- Result: `output/molmo-planner-rby1m-curobo-gate/run_result.json`.
- Gate result after local CuRobo/CUDA PyTorch install:
  `status=blocked_capability`, `embodiment=rby1m`, `curobo_available=true`,
  `execution_attempted=false`.
- Strict rejection blockers include `timeout`,
  `rby1m_execution_not_attempted`, and `rby1m_planner_not_backed`.

## Risks

- This can be mistaken for installing CuRobo. It is only a gate and artifact
  boundary.
- If CuRobo becomes available locally, the strict path must still require
  execution and nonzero robot-state movement, not just import success.
