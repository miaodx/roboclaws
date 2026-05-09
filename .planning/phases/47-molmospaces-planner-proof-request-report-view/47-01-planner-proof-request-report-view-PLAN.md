# 47-01 Planner Proof Request Report View Plan

## Goal

Make planner proof request manifests visually reviewable in the shared
MolmoSpaces Cleanup Artifact Report without exposing private planner aliases to
Agent View.

## Status

Planned.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add shared report rendering for planner proof requests.
3. [ ] Add checker coverage that requires the report section when a manifest is
   present.
4. [ ] Add renderer/demo/MCP tests for proof request report visibility and
   privacy.
5. [ ] Run focused verification gates.

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

- Pending.

## Risks

- Planner aliases in the private report section could be mistaken for runtime
  Cleanup Agent inputs. Keep the section after the score/planner evidence area
  and explicitly validate that Agent View remains clean.
- The report can become too dense. Use a compact table and preserve the existing
  canonical visual core order.
