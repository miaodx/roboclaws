# MolmoSpaces Semantic Underlay Architecture

**Status:** Completed under GSD Phase 115 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0050, ADR-0106
**Workflow:** `hybrid-phase-pipeline`, `improve-codebase-architecture`, `zoom-out`

## Problem

The repo already has a shared semantic cleanup loop and a shared Cleanup
Artifact Report underlay, but the semantic cleanup vocabulary was still copied
across the loop, reports, visual-core checks, and command-line checkers.

This is the architecture shape that allowed report drift: each caller knew too
much about the raw phase strings and report labels.

## Decision

Centralize semantic cleanup vocabulary in
`roboclaws.molmo_cleanup.semantic_timeline`.

The module now owns:

- raw phase constants;
- canonical surface and inside cleanup phase sequences;
- focused semantic action prefixes;
- report-facing display labels;
- current-contract and ADR-0003 loop variant strings;
- the report note for `nav, pick, nav, open?, place`.

Consumers import those values instead of maintaining local copies.

## Non-Goals

- Do not change cleanup behavior.
- Do not change report visual output.
- Do not generate or restore a grasp cache in this architecture slice.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/semantic_cleanup_loop.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/report_visual_core.py roboclaws/molmo_cleanup/realworld_contract.py scripts/check_molmospaces_cleanup_result.py scripts/check_molmo_agent_bridge_result.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/semantic_cleanup_loop.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/report_visual_core.py roboclaws/molmo_cleanup/realworld_contract.py scripts/check_molmospaces_cleanup_result.py scripts/check_molmo_agent_bridge_result.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_semantic_cleanup_loop.py tests/test_molmo_report_visual_core.py tests/test_molmo_cleanup_report.py tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_check_molmo_agent_bridge_result.py`
