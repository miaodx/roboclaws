# 47-01 Planner Proof Request Report View Plan

## Goal

Make planner proof request manifests visually reviewable in the shared
MolmoSpaces Cleanup Artifact Report without exposing private planner aliases to
Agent View.

## Status

Completed 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add shared report rendering for planner proof requests.
3. [x] Add checker coverage that requires the report section when a manifest is
   present.
4. [x] Add renderer/demo/MCP tests for proof request report visibility and
   privacy.
5. [x] Run focused verification gates.

## Acceptance

- Reports with `planner_cleanup_proof_requests_v1` include a
  `Planner Proof Requests` section.
- The section shows ready/blocked counts, cleanup object/source/target IDs,
  semantic tools, private planner aliases, and blockers.
- The section appears with planner/private evidence after the visual core and
  before Agent View.
- Agent View and public traces still do not expose planner aliases.
- Older reports without proof request manifests remain checker-compatible.
- Tests cover the shared renderer plus deterministic and MCP ADR-0003 paths.

## Verification

- `uv run ruff check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/report_visual_core.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/report_visual_core.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`

## Completion Notes

- Cleanup reports now render `Planner Proof Requests` when
  `planner_cleanup_proof_requests_v1` is present.
- The section appears after planner cleanup bridge evidence and before Agent
  View, preserving the visual core and public/private boundary.
- The checker requires the section only for artifacts that include proof
  requests, so older pre-Phase-47 artifacts remain valid.

## Risks

- Planner aliases in the private report section could be mistaken for runtime
  Cleanup Agent inputs. Keep the section after the score/planner evidence area
  and explicitly validate that Agent View remains clean.
- The report can become too dense. Use a compact table and preserve the existing
  canonical visual core order.
