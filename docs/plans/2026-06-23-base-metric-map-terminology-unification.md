---
plan_scope: base-metric-map-terminology-unification
status: Draft
created: 2026-06-23
implementation_allowed: false
source:
  - discussion about aligning Base Navigation Map and Runtime Metric Map naming
related_context:
  - docs/plans/2026-06-17-sim-map-surface-simplification.md
  - docs/plans/2026-06-20-cross-environment-map-waypoint-source-of-truth.md
  - docs/plans/2026-06-23-map-visual-role-contract.md
  - docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md
---

# Base Metric Map Terminology Unification

## Goal

Rename the current start-of-run map term from **Base Navigation Map** to
**Base Metric Map** so the public model reads as one metric-map family:

```text
Base Metric Map
Runtime Metric Map
Runtime Map Prior Snapshot
```

The intended meaning stays the same: Base Metric Map is the start-of-run public
map context, while Runtime Metric Map is the same source-map frame plus
run-created semantic evidence. This plan does not add backward compatibility
aliases.

## Rename Table

Apply these replacements for the top-level map concept:

| Current | Target |
| --- | --- |
| `Base Navigation Map` | `Base Metric Map` |
| `base_navigation_map` | `base_metric_map` |
| `BASE_NAVIGATION_MAP` | `BASE_METRIC_MAP` |
| `base-navigation-map` | `base-metric-map` |
| `base_navigation_map_v1` | `base_metric_map_v1` |
| `base_navigation_map_contract` | `base_metric_map_contract` |
| `base_navigation_map_preview` | `base_metric_map_preview` |
| `base_navigation_map_bundle` | `base_metric_map_bundle` |

Do not mechanically rename these sub-concepts in the first pass:

- `navigation_area`
- `navigation_area_id`
- `base_navigation_area_inspection`
- `base_navigation_area_centroid_clearance_v1`

Those terms describe navigable areas or waypoint generation inside the map, not
the top-level map artifact name.

## Scope

Update the current product contract surfaces together:

- map bundle validation, preparation, preview, and copy helpers;
- Agent View section names and checker expectations;
- runtime/report/operator-console visual roles and labels;
- B1 and MolmoSpaces map build scripts, manifests, checked-in map assets, and
  static preview metadata;
- CLI flags, just recipes, launch catalog hints, eval gates, tests, and current
  human docs.

Historical plan prose may be updated for search clarity, but archived decisions
do not need new compatibility language.

## Non-Goals

- Do not rename Runtime Metric Map to Runtime Navigation Map.
- Do not change Runtime Metric Map payload semantics.
- Do not add compatibility readers for old `base_navigation_map*` field names,
  schema ids, visual roles, or file names.
- Do not broaden this into a map schema redesign.
- Do not rename `navigation_area` sub-fields unless a focused follow-up proves
  that they are also confusing.

## Implementation Slices

1. **Contract names**
   Rename constants, schema ids, validators, Agent View sections, checker
   flags, and public error messages from Base Navigation Map to Base Metric
   Map.

2. **Artifacts and assets**
   Migrate checked-in map bundle JSON, B1/MolmoSpaces generated asset metadata,
   preview role metadata, and expected artifact names.

3. **Callers and tests**
   Rename imports, helper functions, scripts, test files, test function names,
   just recipe references, eval gates, and report assertions.

4. **Docs and skills**
   Update current root docs, human docs, ADR references, AGENTS/CLAUDE guidance,
   and relevant skills so the active vocabulary is Base Metric Map plus Runtime
   Metric Map.

5. **Search cleanup**
   Run targeted search and leave only intentional historical references, if any.
   Prefer zero current-code hits for:

   ```text
   Base Navigation Map
   base_navigation_map
   BASE_NAVIGATION_MAP
   base-navigation-map
   ```

## Verification

Focused proof should include:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/maps \
  tests/unit/operator_console \
  tests/contract/reports/test_molmo_cleanup_report.py \
  tests/contract/checkers/test_realworld_base_navigation_map_checker.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Then run:

```bash
ruff check .
ruff format --check .
rg -n "Base Navigation Map|base_navigation_map|BASE_NAVIGATION_MAP|base-navigation-map" \
  roboclaws scripts tests just skills AGENTS.md CLAUDE.md README.md ARCHITECTURE.md STATUS.md docs/human docs/adr assets
```

## Stop Gates

Stop and re-scope if any of these happen:

- `navigation_area` sub-concepts require a broad semantic redesign.
- Renaming checked-in assets creates ambiguous map ids that cannot be migrated
  without regenerating runtime evidence.
- A live product route depends on old artifact names outside checked-in callers.
- Focused tests require adding compatibility aliases to pass.

## Expected Cost

This is a medium-sized repo-wide rename, not a simple text replacement. The
expected change touches roughly 120 to 160 files, mostly tests, docs, scripts,
checked-in map assets, and operator-console preview metadata.
