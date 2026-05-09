# 21-01 Real-World Advisory Scoring Plan

## Goal

Add a non-authoritative advisory scoring/model-check artifact to ADR-0003
MolmoSpaces cleanup runs and render it in the shared Cleanup Artifact Report,
while keeping deterministic scoring as the only pass/fail source.

## Status

Active 2026-05-09.

## Tasks

1. Add ADR/source-plan documentation and update roadmap/state/context references
   for Phase 21.
2. Implement `roboclaws/molmo_cleanup/advisory_scoring.py` with a deterministic
   CI-safe adapter and stable schema for future model adapters.
3. Attach advisory output to deterministic real-world cleanup runs and
   `molmo_cleanup_realworld` MCP finalization, including
   `advisory_evaluation.json` artifacts.
4. Render `Advisory Review` in the shared report and add optional checker
   enforcement.
5. Add tests, run focused verification, write summary/verification docs, and
   mark Phase 21 complete.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_advisory_scoring.py tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py`
- `ruff check` / `ruff format --check` on changed Python files.
- `just verify::molmo-realworld-agent-dogfood-kit`

## Risks

- Advisory review must not look like a second authoritative score. The schema
  and report copy must say `authoritative=false`.
- The report addition must be conditional so historical artifacts remain valid.
- Future live model adapters must use the same schema rather than adding a
  second report path.
