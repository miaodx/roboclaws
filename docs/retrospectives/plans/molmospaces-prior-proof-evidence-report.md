# MolmoSpaces Prior Proof Evidence Report

**Status:** Completed for Phase 86 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/0077-render-prior-proof-evidence-in-runner-reports.md`

## Goal

Make prior proof evidence visibly reviewable in proof-bundle runner reports
after standalone or prior-bundle evidence is normalized for selection.

## Problem

Phase 85 lets standalone prior probes drive selection memory, but the runner
report only showed the resulting exclusion and report path. The normalized prior
proof result itself was not rendered as a full report section, so reviewers had
to jump between artifacts to inspect blocker details or planner-view images.

## Scope

- Store the merged prior proof result summary in runner manifests.
- Render a `Prior Proof Evidence` section before new proof commands/results.
- Reuse the existing proof result card renderer for prior status, diagnostics,
  worker-stage evidence, report paths, and view images.
- Extend checker and focused tests to require visible prior evidence when the
  manifest carries it.

## Non-Goals

- Do not expose prior proof evidence to the Cleanup Agent.
- Do not change proof selection behavior.
- Do not execute new RBY1M/CuRobo proofs.
- Do not treat prior visual evidence as readiness.

## Acceptance Criteria

- A runner manifest with prior proof evidence contains
  `prior_proof_result_summary`.
- Runner `report.html` renders `Prior Proof Evidence`.
- Prior proof report/run-result paths and prior view image paths render when
  present.
- The runner checker validates the prior evidence section.
- Focused lint, format, pytest, and manual checker validation pass.

## Result

Implemented.

The runner report now shows prior proof evidence as a peer to current proof
results. A manual Phase 86 dry-run using the Phase 81 standalone probe rendered
the prior grasp-feasibility blocker details, proof paths, worker-stage
diagnostics, and no-view status before the newly selected proof command.

Verification:

- Focused ruff and format checks passed for changed implementation, checker,
  and tests.
- Focused pytest passed for report rendering, standalone prior ingest, and
  checker coverage.
- Manual runner dry-run rendered `Prior Proof Evidence` and passed
  `scripts/check_molmo_planner_proof_bundle_runner_result.py`.
