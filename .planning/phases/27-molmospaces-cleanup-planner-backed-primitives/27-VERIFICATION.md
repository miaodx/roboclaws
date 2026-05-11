# Phase 27 Verification: MolmoSpaces Cleanup Planner-Backed Primitive Gate

Date: 2026-05-09

## Commands

```bash
uv run ruff check roboclaws/molmo_cleanup/cleanup_primitive_evidence.py roboclaws/molmo_cleanup/semantic_timeline.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/realworld_mcp_server.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py
uv run ruff format --check roboclaws/molmo_cleanup/cleanup_primitive_evidence.py roboclaws/molmo_cleanup/semantic_timeline.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/realworld_mcp_server.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py
.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmo-realworld-cleanup-primitive-gate --backend molmospaces_subprocess --include-robot --record-robot-views --generated-mess-count 2 --planner-proof-run-result output/molmo-planner-manipulation-probe-headless/run_result.json
.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --require-robot-views --require-advisory-scoring --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives output/molmo-realworld-cleanup-primitive-gate/run_result.json
```

Strict rejection check:

```bash
.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --require-planner-backed-cleanup-primitives output/molmo-realworld-cleanup-primitive-gate/run_result.json
```

The strict command rejects the current artifact as expected because the cleanup
subphases are `api_semantic`, not planner-backed.

## Artifact Review

- `output/molmo-realworld-cleanup-primitive-gate/report.html` contains
  `Cleanup Primitive Gate`, `Attached Planner-Backed Proof`, `Semantic
  Substeps`, `Robot View Timeline`, `nav/object`, `pick/object`, `nav/target`,
  `api_semantic`, `blocked_capability`, and `mujoco_freejoint_qpos`.
- `output/molmo-realworld-cleanup-primitive-gate/run_result.json` contains
  `cleanup_primitive_evidence` with `status=blocked_capability`,
  `primitive_provenance=blocked_capability`, `object_count=2`, and
  `subphase_count=8`.

## Verdict

Phase 27 satisfies the evidence-gate requirement. It does not satisfy actual
planner-backed cleanup-loop execution; that remains a follow-up phase.
