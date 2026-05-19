# 26-01 Summary: Cleanup Planner Proof Attachment

Completed: 2026-05-09

## What Changed

- Added `roboclaws/molmo_cleanup/planner_proof_attachment.py` to validate a
  strict planner probe `run_result.json` and copy initial/final proof views into
  a cleanup artifact directory.
- Added optional `--planner-proof-run-result` support to the deterministic
  ADR-0003 cleanup harness and the real-world cleanup MCP server.
- Rendered an `Attached Planner-Backed Proof` panel in the shared Cleanup
  Artifact Report.
- Added `--require-planner-proof-attachment` to the ADR-0003 cleanup checker.
- Added focused tests for the attachment helper, report panel, and checker gate.

## Evidence

- Full local artifact:
  `output/molmo-realworld-cleanup-planner-proof/report.html`
- Attached proof images:
  `output/molmo-realworld-cleanup-planner-proof/planner_proof/`
- Strict planner source proof:
  `output/molmo-planner-manipulation-probe-headless/run_result.json`

## Boundary

This phase does not claim planner-backed cleanup execution. The cleanup loop's
object moves remain `api_semantic`; the Franka proof is attached as separate
strict planner-backed manipulation evidence.
