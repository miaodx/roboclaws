# 21-01 Summary: Real-World Advisory Scoring

## Outcome

Phase 21 is complete for the advisory scoring/model-check slice. ADR-0003
MolmoSpaces cleanup artifacts can now carry a non-authoritative
`advisory_evaluation` payload, a persisted `advisory_evaluation.json` artifact,
and an `Advisory Review` section in the shared Cleanup Artifact Report.

The default advisory adapter is deterministic and CI-safe:
`deterministic_semantic_rubric_v1`. It uses the existing score rows and
semantic-acceptability labels to produce the same schema future live model
adapters must satisfy.

## Code Changes

- Added `roboclaws/molmo_cleanup/advisory_scoring.py`.
- Added advisory output to:
  - deterministic ADR-0003 runs in `examples/molmospaces_realworld_cleanup.py`;
  - MCP finalization in `roboclaws/molmo_cleanup/realworld_mcp_server.py`.
- Added `Advisory Review` rendering to `roboclaws/molmo_cleanup/report.py`.
- Added `--require-advisory-scoring` to
  `scripts/check_molmo_realworld_cleanup_result.py`.
- Updated ADR-0003 harness recipes so newly generated real-world, MCP,
  direct-agent, OpenClaw, and visual OpenClaw artifacts require advisory
  scoring.

## Evidence

- Focused tests passed:
  `tests/test_molmo_cleanup_advisory_scoring.py`,
  `tests/test_molmo_cleanup_report.py`,
  `tests/test_molmospaces_realworld_cleanup.py`,
  `tests/test_molmo_realworld_mcp_server.py`,
  `tests/test_check_molmo_realworld_cleanup_result.py`, and
  `tests/test_verify_just_recipes.py`.
- `just verify::molmo-realworld-agent-dogfood-kit` passed with
  `advisory_evaluation.authoritative=false`.
- `just verify::molmo-realworld-openclaw-dogfood-kit` passed with
  `--require-advisory-scoring`.

## Remaining Follow-Up

This phase does not call a paid or remote model. A future live Advisory LLM
Scorer can be added as another adapter only if it writes the same schema and
remains non-authoritative. Broader remaining MolmoSpaces work is now raw
FPV-only perception and planner-backed manipulation.
