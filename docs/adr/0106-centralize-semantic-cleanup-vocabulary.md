# 0106. Centralize Semantic Cleanup Vocabulary

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0050 made Cleanup Artifact Reports show the semantic cleanup loop as
`nav`, `pick`, `nav`, optional `open`, then `place`. Later slices reused the
same loop across current-contract, ADR-0003, MCP smoke, and proof-bundle
handoff artifacts.

The raw phase names, display labels, loop variant strings, focused action
prefixes, and checker expectations were still repeated in multiple modules.
That made the shared underlay vulnerable to the same drift that created the
ADR-0003 report visual mismatch.

## Decision

Make `roboclaws.molmo_cleanup.semantic_timeline` the package-level source of
truth for semantic cleanup vocabulary:

- raw phases such as `navigate_to_object`, `pick`, `navigate_to_receptacle`,
  `open_receptacle`, `place`, `place_inside`, and `object_done`;
- canonical surface and inside cleanup phase sequences;
- report-facing subphase labels such as `nav/object`, `nav/target`, and
  `place/surface`;
- loop variant strings used by current-contract and ADR-0003 artifacts;
- focused robot-view action prefixes used by report/checker gates.

Reports, visual-core checks, semantic-loop execution, and artifact checkers
import those values instead of carrying local copies.

## Consequences

- Future semantic subphase changes have one module-level interface.
- Current-contract and ADR-0003 report gates now share the same vocabulary
  source.
- This does not change the cleanup behavior or visual output; it removes
  duplicated architecture around the existing `nav, pick, nav, open?, place`
  contract.

## Evidence

Implemented in Phase 115 on 2026-05-10.

Verification:

- `.venv/bin/ruff check ...`
- `.venv/bin/ruff format --check ...`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_semantic_cleanup_loop.py tests/test_molmo_report_visual_core.py tests/test_molmo_cleanup_report.py tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_check_molmo_agent_bridge_result.py`
