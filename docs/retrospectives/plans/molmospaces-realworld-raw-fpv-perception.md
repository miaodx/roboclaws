# MolmoSpaces Real-World Raw FPV Perception

**Status:** Completed 2026-05-09 under GSD Phase 22
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0009, ADR-0013, Phase 21 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

The broader `CONTEXT.md` plan defers raw FPV-only perception until the
ADR-0003 cleanup contract, report underlay, clean-policy gate, and advisory
artifacts are stable. Those prerequisites are now complete.

The current public contract still gives the Cleanup Agent structured visible
object detections with categories, names, bounding boxes, and support estimates.
That is robot-local and private-truth safe, but it is not the harder camera-only
mode described in the original discussion.

## Decision

Implement ADR-0013 as an evidence-mode raw FPV slice.

This phase should:

- add a `raw_fpv_only` perception mode while preserving the current default;
- make `observe` return no structured movable-object detections in that mode;
- record public raw FPV observation rows in the Agent View;
- attach FPV image artifacts from the existing robot-view capture underlay when
  robot views are enabled;
- render a `Raw FPV Observations` report section through the shared report
  renderer;
- add checker support for raw-FPV evidence without requiring cleanup success;
- keep planner-backed manipulation and camera-only object registration out of
  scope.

## Non-Goals

- Do not make raw FPV mode clean successfully yet.
- Do not expose private generated mess, target count, support estimates, object
  categories, or target receptacles to the agent in raw mode.
- Do not clone the report renderer.
- Do not introduce a paid model or VLM call in CI.
- Do not start planner-backed RBY1M/Franka manipulation.

## Deliverables

- ADR-0013 and this source plan.
- `.planning/milestones/v1.98-phases/22-molmospaces-realworld-raw-fpv-perception/22-01-realworld-raw-fpv-perception-PLAN.md`.
- A `perception_mode` knob in the ADR-0003 deterministic and MCP paths.
- Raw FPV observation serialization in `agent_view.json` and `run_result.json`.
- Report support for a `Raw FPV Observations` panel.
- Checker and tests for raw-FPV mode, no structured detections, artifact
  linkage, and report rendering.
- Optional harness/verify recipes for the local MolmoSpaces/RBY1M raw-FPV
  evidence run.

## Acceptance Criteria

- Default `visible_object_detections` behavior and existing clean gates continue
  to pass.
- Raw mode run results record `perception_mode=raw_fpv_only`.
- Raw mode `observe` responses and `agent_view` do not expose structured
  visible object detections, categories, support estimates, target labels, or
  private scoring truth.
- Raw mode records at least one `raw_fpv_observations` row.
- When robot views are recorded, every raw FPV observation row links to a
  nonempty FPV image artifact.
- The shared report renders `Raw FPV Observations`.
- The checker can require raw-FPV evidence without requiring cleanup success.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_contract.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py`
- `ruff check` and `ruff format --check` on changed Python files.
- `just verify::molmo-realworld-raw-fpv`

## Completion Evidence

- Added `perception_mode=raw_fpv_only` to the ADR-0003 deterministic and MCP
  paths while preserving `visible_object_detections` as the default.
- Raw mode `observe` responses and `agent_view` rows contain no structured
  movable-object detections, categories, support estimates, target labels, or
  private scoring truth.
- The shared report renders `Raw FPV Observations` and still includes the Robot
  View Timeline, Agent View, Advisory Review, and Private Evaluation sections.
- The checker supports `--require-raw-fpv-observations`.
- `just verify::molmo-realworld-raw-fpv` passed against the real
  MolmoSpaces/RBY1M backend with 14 raw FPV observations and 16 robot-view
  steps.
