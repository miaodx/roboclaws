# 27-01 Cleanup Planner-Backed Primitive Gate Plan

## Goal

Create the per-subphase evidence gate that future planner-backed cleanup
primitive execution must satisfy, while keeping current ADR-0003 cleanup
artifacts honest about `api_semantic` execution.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [x] Add a cleanup primitive evidence builder that summarizes object-level
   `nav, pick, nav, open?, place` subphases and their primitive provenance.
3. [x] Render the primitive gate in the shared Cleanup Artifact Report.
4. [x] Add checker modes:
   - accept explicit blocked-capability evidence for current semantic cleanup;
   - require planner-backed manipulation subphases for strict future proof.
5. [x] Add focused tests and generate/validate a local visual artifact.

## Outcome

The cleanup artifact now contains `cleanup_primitive_evidence` derived from the
semantic substep trace. The report renders a `Cleanup Primitive Gate` section
with object-level `nav/object`, `pick/object`, `nav/target`, `open/target`,
and `place/surface` rows, plus primitive provenance and state mutation details.

Current MolmoSpaces cleanup artifacts are accepted only as explicit
`blocked_capability` evidence because their subphases remain `api_semantic`.
The strict checker path rejects those same artifacts until cleanup-loop
primitives are actually planner-backed.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmo-realworld-cleanup-primitive-gate --backend molmospaces_subprocess --include-robot --record-robot-views --generated-mess-count 2 --planner-proof-run-result output/molmo-planner-manipulation-probe-headless/run_result.json`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --require-robot-views --require-advisory-scoring --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives output/molmo-realworld-cleanup-primitive-gate/run_result.json`
- Strict gate should reject the same artifact with
  `--require-planner-backed-cleanup-primitives`.

Evidence:

- Artifact: `output/molmo-realworld-cleanup-primitive-gate/report.html`.
- Result: `output/molmo-realworld-cleanup-primitive-gate/run_result.json`.
- Gate result: `status=blocked_capability`, `primitive_provenance=blocked_capability`,
  `object_count=2`, `subphase_count=8`, and `api_semantic` subphase provenance.
- Visual payload: 40 robot-view PNGs plus 2 attached planner-proof PNGs.

## Risks

- The gate can be mistaken for actual planner execution unless blocked evidence
  and report copy remain explicit.
- Strict RBY1M planner-backed cleanup likely remains blocked by CuRobo until a
  later dependency/runtime phase.
