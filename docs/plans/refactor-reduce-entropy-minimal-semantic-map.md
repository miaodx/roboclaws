# Refactor: Minimal-First Semantic Map Pipeline

Status: DONE

## Target

Make the household semantic-map path obvious and true-to-hardware:

```text
minimal navigation map
  -> semantic-map-build
  -> runtime_metric_map.json
  -> household-cleanup runtime_map_prior=...
```

The cleanup stack should no longer present pre-authored rich fixture semantics as
the default path. Rich/pre-authored maps may remain temporarily as an explicit
legacy/debug shortcut while the minimal-first path is verified across backends.

## Accepted Checklist

- [x] Phase 1: Make minimal-first the canonical default in commands, docs, and examples.
- [x] Phase 2: Mark rich/pre-authored map mode as an explicit legacy/debug path.
- [x] Phase 3: Update live-agent prompts and gates so cleanup does not depend on
      `fixture_hints.rooms` containing target fixtures.
- [x] Phase 4: Remove rich implementation or narrow it to a non-public test/debug helper
      after focused verification proves minimal-first coverage.
- [x] Final: Run focused route, contract, checker, and smoke verification; update human docs.

## Phase Notes

- Public defaults now resolve to `map_mode=minimal` through `DEFAULT_MAP_MODE`,
  `just task::run`, `just molmo::cleanup`, the direct cleanup entrypoint, and the
  MCP server.
- `rich` is retained as an explicit legacy/debug projection because scene-index
  overlay tests and static fixture-map contract tests still need pre-authored
  public semantics as a comparison surface. It is no longer the default command
  or API mode.
- RAW-FPV cleanup no longer requires a prefilled `target_fixture_id` in minimal
  mode. Minimal mode resolves omitted targets through runtime semantic anchors
  and returns public `candidate_fixture_id` values for placement. When the
  resolved public anchor points to a fridge/bookshelf-style receptacle, the
  response keeps the public anchor id while deriving the correct recommended
  placement tool from the internal fixture binding.

## Verification

Completed on 2026-05-30:

- `python -m py_compile roboclaws/molmo_cleanup/realworld_contract.py examples/molmo_cleanup/molmospaces_realworld_cleanup.py examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -k 'minimal_map or runtime_metric_map or runtime_map_prior'`
- `ROBOCLAWS_JUST_TRACE=1 just task::run semantic-map-build direct smoke`
- `ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup direct smoke`
- `just task::run household-cleanup direct smoke seed=7 generated_mess_count=5 output_dir=output/checks/minimal-default-cleanup-smoke`
- `just task::run semantic-map-build direct smoke seed=7 generated_mess_count=5 output_dir=output/checks/minimal-default-map-build-smoke`
- `just task::run household-cleanup direct smoke seed=7 generated_mess_count=5 runtime_map_prior=output/checks/minimal-default-map-build-smoke/0530_2340/seed-7/runtime_metric_map.json output_dir=output/checks/minimal-prior-cleanup-smoke`
- `ruff check roboclaws/molmo_cleanup/realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py examples/molmo_cleanup/molmospaces_realworld_cleanup.py examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py`

Smoke artifacts:

- Cleanup default: `output/checks/minimal-default-cleanup-smoke/0530_2340/seed-7/report.html`
- Semantic map build: `output/checks/minimal-default-map-build-smoke/0530_2340/seed-7/report.html`
- Runtime-map-prior cleanup: `output/checks/minimal-prior-cleanup-smoke/0530_2340/seed-7/report.html`

Closeout audit:

- `$intuitive-doc`: updated `README.md`, `ARCHITECTURE.md`,
  `just/README.md`, `skills/molmo-realworld-cleanup/SKILL.md`, and
  `docs/human/mcp-skills-and-semantic-profiles.md`; checked `STATUS.md` and
  left it unchanged because repo-level current focus remains Isaac/backend
  work, not this bounded semantic-map default cleanup.
- Parked todos are classified below. None is in-scope-required for this pass.
- Initial commit audit: no commit was created at that point. The owned
  minimal-first changes overlapped in
  `just/molmo.just`, `just/agent.just`,
  `examples/molmo_cleanup/molmospaces_realworld_cleanup.py`, and
  `examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py` with
  pre-existing Isaac/backend/generated-mess edits in the same files. Selective
  staging would have risked committing unrelated work, so the flow recorded the
  blocker before a later clean closeout.
- Git closeout: this plan was committed after the minimal-first slice itself was
  already clean in the worktree. The remaining `uv.lock` diff only rewrites
  package URLs to a local mirror and is intentionally left uncommitted per the
  repo policy that mirror selection stays machine-local.

## Evidence Level

Required before DONE:

- `ROBOCLAWS_JUST_TRACE=1 just task::run semantic-map-build direct smoke`
- `ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup direct smoke`
- Focused route tests for `just task::run` cleanup/map-build routing.
- Focused contract/checker tests proving minimal map + runtime semantic anchors.
- At least one cheap smoke cleanup run with `map_mode=minimal`.

Local GPU, Isaac, Agibot hardware, and live-provider runs are not required to
mark this refactor slice done. If code paths remain that need those gates, record
them as parked validation with concrete commands.

## Affected Paths

- `README.md`
- `ARCHITECTURE.md`
- `just/README.md`
- `just/agent.just`
- `just/molmo.just`
- `examples/molmo_cleanup/molmospaces_realworld_cleanup.py`
- `examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py`
- `roboclaws/molmo_cleanup/realworld_contract.py`
- `roboclaws/molmo_cleanup/realworld_mcp_server.py`
- `skills/molmo-realworld-cleanup/SKILL.md`
- focused contract tests under `tests/contract/**`

## Parked Items

- `deferred-by-policy`: broaden minimal-first validation to real MolmoSpaces,
  Isaac prepared USD, and Agibot hardware after the cheap and contract-level
  path is clean. This pass explicitly did not require local GPU, live-provider,
  Isaac, or Agibot hardware gates.
- `needs-human-decision`: decide whether the name should remain `minimal` or
  become `sparse` in a later public API cleanup. This pass keeps `minimal`
  unless removal of `rich` makes the axis unnecessary.
