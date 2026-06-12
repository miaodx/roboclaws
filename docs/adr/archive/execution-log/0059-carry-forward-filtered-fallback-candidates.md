# 0059. Carry Forward Filtered Fallback Candidates

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0057 introduced failed-candidate memory, and ADR-0058 executed the remaining
filtered fallback commands. The latest execution proved the last untried book
runtime sibling is also a non-root body.

The next runner pass must not lose the filters that were already rendered in
the previous `fallback_generation` section. Otherwise, using the latest
manifest as prior evidence could regenerate candidates that were filtered in an
earlier pass.

## Decision

Carry prior `fallback_generation.filtered_aliases` and
`fallback_generation.filtered_pairs` forward alongside discovered aliases.

The selection layer now treats carried filtered candidates as active filters
before generating commands:

- carried `prior_non_root_body_alias` rows block future object-side commands
  for the same alias;
- carried `not_exact_scene_runtime_alias` rows remain visible and filtered;
- carried `prior_task_feasibility_blocked_pair` rows block exact object/target
  pair retries.

## Consequences

- Using the Phase 67 manifest as prior evidence now produces zero generated
  commands instead of rediscovering already-filtered aliases or pairs.
- The runner report still shows the carried discovered aliases, filtered
  aliases, and filtered pairs, making the exhausted fallback state reviewable.
- The next implementation work must derive or validate pickup root-body aliases
  from a better source before object-side fallback generation can continue.

## Evidence

The Phase 68 dry-run wrote
`output/debug-phase68-filter-carry-forward-dry-run/report.html` and
`proof_bundle_run_manifest.json`.

Using the Phase 67 executed bundle as prior input, the runner reported:

- `command_count=0`
- `generated_request_count=0`
- `discovered_alias_count=5`
- `filtered_alias_count=7`
- `filtered_pair_count=2`
- `unavailable_source_request_count=2`
- `fallback_required=true`

Validation passed with:

```bash
uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase68-filter-carry-forward-dry-run
```
