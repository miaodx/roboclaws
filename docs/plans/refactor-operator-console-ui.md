---
refactor_scope: operator-console-ui
status: DONE
accepted_severities:
  - P1
  - P2
last_verified: 2026-06-03
---

# Refactor Scope: Operator Console UI

> **Supersession note (2026-06-10):** The route-card UI produced by this
> completed refactor was the predecessor to
> `docs/plans/operator-console-orthogonal-launch-refactor.md`. Current console
> launch identity is the orthogonal selection of world/scene, backend, intent,
> agent engine, provider profile, evidence lane, and scenario setup. Treat this
> file as historical evidence for the prior four-column shell and view-mode
> cleanup, not as current launch taxonomy.

## Status

DONE

## Target

`roboclaws/operator_console/`, limited to the standalone operator console route
metadata, static UI, and focused unit/static tests.

## Accepted Severities

- P1: misleading view tabs that do not change the visible workspace layout.
- P1: workspace grid cannot show the default FPV, Map, and Grounding views cleanly.
- P1: route-specific controls are inferred indirectly and can surface irrelevant backend controls.
- P2: route and parameter setup are separated by one long rail instead of adjacent operator steps.
- P2: UI language should remain agent-provider neutral and avoid Codex-only labels where routes include Claude Code.

## Accepted Cleanup Checklist

- Route payload exposes explicit `field_groups` and `view_modes` metadata for the UI.
- Routes and selected-route setup are adjacent panels instead of one long left rail.
- Default workspace mode is `Overview`.
- Overview uses two columns: left column `FPV` plus optional `Grounding`, right column `Map`.
- Routes without `Grounding` render `FPV` and `Map` as equal-height columns, with no empty grounding panel.
- Focus controls (`FPV`, `Map`, `Grounding`, `Chase`, `Outputs`) actually switch the workspace layout.
- `Artifacts` UI copy is renamed to `Outputs`.
- Isaac-only and Agibot-only controls are hidden unless the selected route metadata declares those field groups.
- Provider/key copy remains agent-neutral and supports Codex and Claude Code routes.

## Parked Cross-Seam / Future Ideas

- Do not add unsupported Claude `semantic-map-build` catalog routes in this UI refactor.
- Do not redesign the real run launcher, Gateway, coding-agent Docker runtime, or task protocol.
- Do not add arbitrary browser-submitted shell commands.
- Do not make mobile a primary robot-operation layout; only keep it readable.

## Evidence Ladder

- L0: `node --check roboclaws/operator_console/static/app.js`
- L1: `ruff check roboclaws/operator_console tests/unit/operator_console`
- L1: `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
- L2: route/static contract tests for field groups, view modes, and DOM ids.
- Browser smoke: local console screenshot and DOM assertions for route-specific fields and view mode switching.

## Stop Condition

Stop when the accepted checklist is implemented, focused tests pass, `app.js`
passes syntax check, and a local browser smoke proves default overview and focus
mode behavior without launching a real agent run.

## Execution Log

- 2026-06-03: Created gate after user approved the full refactor plan.
- 2026-06-03: Implemented route UI metadata, adjacent route/setup layout,
  default Overview workspace, Outputs copy, route-specific field hiding, focused
  tests, and headless Chrome smoke verification.
