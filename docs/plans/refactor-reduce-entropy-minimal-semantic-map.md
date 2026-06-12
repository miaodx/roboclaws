---
refactor_scope: semantic-map-map-mode-collapse
status: CONTINUE
accepted_severities:
  - P1
  - P2
last_verified: null
---

# Refactor: Minimal-First Semantic Map Pipeline

Status: CONTINUE

## Current Reopened Scope

Reopened on 2026-06-11 after live cleanup/open-ended task review.

The previous minimal-first slice made `map_mode=minimal` the default and left
`rich` as a legacy/debug projection. The current decision removes the
backward-compatibility requirement: the repo should no longer maintain a public
`rich`/`minimal` map-mode abstraction.

New target shape:

```text
Base Navigation Map
  -> optional public room-category hints
  -> semantic-map-build / online observation
  -> Runtime Metric Map
  -> cleanup or open-ended task consumption
```

The key product insight is that open-ended goals such as "我渴了，帮我找水果/水"
need room-level search priors. A sparse map that hides every room category makes
the agent sweep blindly; a rich map that exposes all static fixtures gives away
too much simulator-authored structure. The intended middle ground is:

- expose room categories as public search/navigation hints;
- keep static fixture lists out of the default agent-facing surface;
- let `semantic-map-build` and online observations create fixture/object
  semantics as Runtime Metric Map evidence.

## Status

CONTINUE

## Accepted Severities

- P1: remove live source drift and stale public `map_mode` surface.
- P2: clean tests, docs, prompts, and compatibility-shaped naming inside this
  map-contract seam.

## Accepted Cleanup Checklist

- [ ] Remove `rich` as a public map mode from CLI, `just`, MCP server
      construction, direct runner APIs, docs, and command examples.
- [ ] Collapse current default `minimal` behavior into the single Base
      Navigation Map projection. Keep artifact fields only when they remain
      useful for report/checker clarity; do not preserve them as a selectable
      mode.
- [ ] Add public room-category hints to the Base Navigation Map path. These
      hints may identify areas such as kitchen, dining room, living room,
      bedroom, and bathroom for search prioritization, but must not expose a
      full static fixture inventory.
- [ ] Teach target resolution to use room-category hints as search priors for
      open-ended queries such as water, fruit, food, dishes, books, linen, or
      electronics.
- [ ] Keep fixture/receptacle actionability in the Runtime Metric Map layer:
      public semantic anchors, target candidates, observed objects, and loaded
      runtime-map priors.
- [ ] Recast or delete tests that import `RICH_MAP_MODE` or assert rich static
      fixture hints as product behavior. Keep tests that prove source map
      parsing only if they do not imply an agent-facing rich map mode.
- [ ] Update `skills/molmo-realworld-cleanup/SKILL.md` and live-agent prompts
      so the first-call pattern and recovery instructions refer to Base
      Navigation Map + Runtime Metric Map, not `minimal` vs `rich`.
- [ ] Update human docs and current command docs to describe the two surviving
      concepts: Base Navigation Map and Runtime Metric Map.

## Explicit Non-Goals

- Do not preserve backward compatibility for `map_mode=rich`.
- Do not add a new public mode name such as `sparse` unless implementation
  evidence shows that callers still need an explicit axis.
- Do not expose static fixture hints as default task input. A room hint may say
  "kitchen"; it should not say "fridge_01 exists at exact fixture pose" before
  public observation or map-build evidence.
- Do not mutate source map artifacts during cleanup or map-build. Runtime map
  output remains a separate artifact.
- Do not run paid/live-provider, OpenClaw Gateway, or local GPU gates as part of
  this planning pass.

## Proposed Contract Shape

### Base Navigation Map

The Base Navigation Map is the agent-facing static map projection available at
run start. It should contain:

- occupancy/free-space geometry and frame metadata;
- generated exploration candidates or safe inspection waypoints;
- current robot pose;
- public room-category hints when available;
- no private relocation/scoring truth;
- no static movable-object inventory;
- no full fixture/receptacle table by default.

Room-category hint shape should be close to Public Semantic Anchor shape so the
agent has one mental model:

```json
{
  "anchor_type": "room_area",
  "category": "kitchen",
  "label": "Kitchen",
  "room_id": "room_area_001",
  "waypoint_id": "generated_exploration_003",
  "affordances": ["navigate", "observe"],
  "classification_status": "map_prior",
  "confidence": 0.8
}
```

### Runtime Metric Map

The Runtime Metric Map remains the current-run semantic evidence layer. It
should contain:

- public semantic anchors for observed or loaded-prior places;
- target candidates and target actionability status;
- observed objects and observed-object priors;
- generated target inspection candidates;
- producer and provenance summaries;
- no private cleanup target truth.

Semantic-map-build is the canonical way to turn Base Navigation Map context
into reusable Runtime Metric Map evidence before cleanup or open-ended tasks.

## Open Design Questions

- Should room-category hints live only inside `public_semantic_anchors`, or also
  in a top-level `room_category_hints` convenience field for report/UI clarity?
  Current preference: store them as anchors and optionally summarize them.
- Should `fixture_hints()` remain as an MCP tool returning an empty/deprecated
  explanatory payload for one slice, or should it be removed from the tool list
  in the same refactor? Current preference: remove if known in-repo prompts and
  tests can migrate cleanly.
- Should old `map_mode` fields remain in historical report rendering only, or
  be removed from new run results entirely? Current preference: preserve
  historical report interpretation, remove from new launch/config surfaces.

## Evidence Ladder

Required before this reopened scope can return to DONE:

- Static search: no production route, prompt, or current docs expose
  `map_mode=rich`.
- Focused tests:
  - Base Navigation Map starts without static fixture inventory.
  - Base Navigation Map can expose room-category hints.
  - `resolve_target_query("fruit")` or equivalent query ranks kitchen/dining
    room hints before unrelated room areas when no observed object exists.
  - Runtime Metric Map still exposes fixture/receptacle anchors after
    observation or semantic-map-build.
  - Cleanup with runtime-map prior consumes anchors without static fixture
    hints.
- Route tests for `just run::surface ... intent=map-build` and
  `intent=cleanup` without a `map_mode` parameter.
- Checker/report tests updated so minimal-map requirements become Base
  Navigation Map / Runtime Metric Map requirements.
- Fast deterministic smoke:
  - direct semantic-map-build;
  - direct cleanup;
  - cleanup with prior from semantic-map-build.

Local GPU, Isaac segmentation, Agibot hardware, live VLM/provider, and OpenClaw
Gateway gates are parked validation unless a code change directly touches those
backend adapters.

## Stop Condition

Stop when the public household-world map contract has exactly two concepts in
current code and docs:

```text
Base Navigation Map
Runtime Metric Map
```

No current public command, MCP task setup, live-agent prompt, or product-facing
doc should require choosing between `minimal` and `rich`. Static fixture
semantics may survive only as internal source-map parsing or historical report
support, not as a task-time public mode.

## Execution Log

- 2026-06-11: Reopened after review of open-ended household goals. Decision:
  no backward compatibility for public `rich` mode; plan first, no direct
  implementation in this turn.

---

## Previous Completed Scope

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
