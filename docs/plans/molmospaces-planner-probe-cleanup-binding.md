# MolmoSpaces Planner Probe Cleanup Binding

**Status:** Implemented in GSD Phase 41 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0031, ADR-0032
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 40 added the adapter that can consume bound planner proof. The actual
planner probe does not yet emit that binding. Current RBY1M/CuRobo proof is
strict runtime evidence, but it remains generic sampled-task evidence.

Before real cleanup primitive replacement, the probe artifact must say which
pickup object and place receptacle it sampled, and whether those names match a
requested cleanup primitive.

## Decision

Add cleanup primitive binding diagnostics to
`scripts/run_molmo_planner_manipulation_probe.py`.

This phase should:

- add optional CLI fields for requested cleanup object, target, source, and
  tools;
- record sampled task binding from the upstream task config;
- promote `cleanup_primitive_binding` only when the requested binding exactly
  matches the sampled pickup/place task;
- record mismatch blockers otherwise;
- preserve generic probe behavior when no cleanup binding request is supplied.

## Non-Goals

- Do not force the upstream sampler to pick a specific object in this slice.
- Do not claim the existing Phase 35 proof is cleanup primitive proof.
- Do not run CuRobo in unit tests.

## Deliverables

- ADR-0032 and this source plan.
- `.planning/phases/41-molmospaces-planner-probe-cleanup-binding/41-01-planner-probe-cleanup-binding-PLAN.md`.
- Probe script binding fields and diagnostics.
- Focused tests for no request, matching request, and mismatch blockers.
- Current visual artifact checker remains accepted as blocked.

## Verification Plan

- Unit tests for requested binding parsing and sampled-task matching.
- Existing probe, attachment, primitive executor, and report tests.
- Ruff check/format on changed files.
- Current ADR-0003 real visual artifact checker in blocked mode.

## Completion Result - 2026-05-09

Phase 41 added requested cleanup binding inputs to
`scripts/run_molmo_planner_manipulation_probe.py`. Execute-mode worker payloads
now record the sampled upstream pickup/place task binding and promote
`planner_probe_cleanup_primitive_binding_v1` only when requested object,
target, and tool coverage match that sampled task. Generic probe runs remain
target runtime proof only, and mismatched requests emit explicit blockers.
Planner probe `report.html` artifacts now render this evidence in a dedicated
Planner Probe Cleanup Binding section.

This closes the probe-source binding gap from ADR-0032. It does not yet force
the upstream sampler to choose an ADR-0003 observed object handle, and it does
not replace cleanup-loop `api_semantic` primitives with real planner-backed
primitive execution.

## Verification Evidence - 2026-05-09

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_probe_primitive_executor.py tests/test_molmo_planner_proof_attachment.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`
