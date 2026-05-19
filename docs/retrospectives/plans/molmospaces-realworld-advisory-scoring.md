# MolmoSpaces Real-World Advisory Scoring

**Status:** Completed 2026-05-09 under GSD Phase 21
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0009, ADR-0012, Phase 20 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

The broader `CONTEXT.md` plan calls for advisory scoring/model checks after the
deterministic ADR-0003 cleanup harness is stable. The current report already
shows exact private matches and semantic acceptability, but it does not expose
a distinct advisory review artifact that can explain disagreements without
affecting pass/fail.

## Decision

Implement ADR-0012 as a small post-run advisory scoring slice.

This phase should:

- add a reusable advisory scoring module with a stable schema;
- use a deterministic CI-safe adapter as the default "model-check shaped"
  reviewer;
- attach the advisory result to ADR-0003 deterministic and MCP run artifacts;
- write `advisory_evaluation.json`;
- render an `Advisory Review` section in the shared Cleanup Artifact Report;
- make checker support optional via a new requirement flag;
- verify that advisory output is non-authoritative and does not modify
  deterministic pass/fail fields.

## Non-Goals

- Do not call a paid or remote model in CI.
- Do not make advisory scoring authoritative.
- Do not expose advisory scoring to the Cleanup Agent during the run.
- Do not clone the report renderer.
- Do not start raw FPV-only perception or planner-backed manipulation work.

## Deliverables

- ADR-0012 and this source plan.
- `.planning/milestones/v1.98-phases/21-molmospaces-realworld-advisory-scoring/21-01-realworld-advisory-scoring-PLAN.md`.
- `roboclaws/molmo_cleanup/advisory_scoring.py` with a stable advisory schema.
- Report support for an `Advisory Review` panel.
- Run-result integration for deterministic real-world runs and
  `molmo_cleanup_realworld` MCP runs.
- Checker and tests for advisory presence, schema, non-authoritative status,
  and report rendering.

## Acceptance Criteria

- ADR-0003 run results may include `advisory_evaluation`.
- `artifacts.advisory_evaluation` points to a nonempty JSON file when advisory
  evaluation is present.
- The advisory payload explicitly states `authoritative=false`.
- Advisory output includes object-level rows and disagreement counts.
- The shared report includes `Advisory Review` when the payload is present.
- A focused checker flag can require advisory scoring without making it part of
  every historical artifact.
- Existing deterministic and OpenClaw clean gates continue to pass.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_advisory_scoring.py tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py`
- `ruff check` and `ruff format --check` on changed Python files.
- `just verify::molmo-realworld-agent-dogfood-kit`

## Completion Evidence

- Added `roboclaws/molmo_cleanup/advisory_scoring.py` with schema
  `advisory_cleanup_scoring_v1`.
- ADR-0003 deterministic and MCP finalization write
  `advisory_evaluation.json` and include `run_result["advisory_evaluation"]`.
- The shared report renders `Advisory Review` when advisory output is present.
- The checker supports `--require-advisory-scoring`, and ADR-0003 harness
  recipes require it for new artifacts.
- Focused tests, ruff, `just verify::molmo-realworld-agent-dogfood-kit`, and
  `just verify::molmo-realworld-openclaw-dogfood-kit` passed.
