---
plan_scope: separate-digital-twin-isaac-from-molmospaces-mainline
refactor_scope: separate-digital-twin-isaac-from-molmospaces-mainline
status: DONE
accepted_severities:
  - P1
  - P2
created: 2026-06-15
last_reviewed: 2026-06-15
last_verified: 2026-06-15
implementation_allowed: true
source:
  - user request to reduce MolmoSpaces backend entropy around Isaac and Genesis
  - user clarification that digital twin still runs in Isaac and must remain supported
  - user clarification that the repo does not need backward compatibility for old demo surfaces
  - intuitive-reduce-entropy selection scan on Isaac/Genesis backend surfaces
  - intuitive-reduce-entropy plan saturation loop on 2026-06-15
related_context:
  - docs/adr/0142-scope-isaac-to-digital-twin-and-retire-molmospaces-isaac.md
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - docs/plans/refactor-reduce-entropy-b1-map12-digital-twin.md
  - docs/plans/isaac-lab-molmospaces-backend-support.md
  - docs/plans/mujoco-isaac-minimal-map-task-parity.md
  - docs/plans/genesis-scene-camera-backend-lane.md
  - docs/plans/refactor-reduce-entropy-loop.md
  - roboclaws/launch/backends.py
  - roboclaws/launch/worlds.py
  - roboclaws/operator_console/routes.py
---

# Separate Digital-Twin Isaac From MolmoSpaces Mainline

## Status

DONE

Reviewed by `intuitive-reduce-entropy` and `grill-with-docs-batch`; accepted
grill decisions are recorded below. Execution via `intuitive-refactor` finished
on 2026-06-15.

Supersession note: this plan's B1 route preservation predates the thin
B1 / Map 12 review/runtime contract. Current B1 product work should preserve
`world=b1-map12 backend=isaaclab`, but must not preserve
`map_bundle=b1-map12-room-semantics`; see
`docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md`.

## Goal

Reduce backend entropy without breaking the active digital-twin route:

```text
B1 / Map 12 digital twin
  -> keep Isaac Lab as the supported backend

MolmoSpaces household scenes
  -> use MuJoCo as the default and normal product/eval backend
  -> remove MolmoSpaces + Isaac support unless a file or recipe is directly
     needed by the current B1 / Map 12 digital-twin proof
```

The desired architecture is not "remove Isaac". It is "stop letting
MolmoSpaces Isaac survive as a compatibility path after the current product
direction has moved on."

## Why Now

Genesis has already been retired from active code paths and now mostly remains
as historical renderer evidence. Isaac is different:

- B1 / Map 12 digital twin still depends on Isaac and must stay healthy.
- MolmoSpaces public routes default to MuJoCo, but current metadata still
  exposes `isaaclab` beside `mujoco` for MolmoSpaces worlds.
- Operator-console route generation still creates MolmoSpaces Isaac cleanup and
  map-build routes.
- The core cleanup backend session still imports and instantiates the Isaac
  backend directly.

That creates a maintenance surprise: a maintainer can reasonably assume
MolmoSpaces Isaac is a normal product route with the same support level as
MuJoCo, while the current strategic direction treats it as optional local GPU
proof or renderer parity evidence.

## Architecture Layers

This plan touches these layers from `ARCHITECTURE.md`:

- Runnable Surface / World / Backend Runtime: public backend availability for
  MolmoSpaces and B1 worlds.
- Thin Runtime / Server Adapter: launch catalog and operator-console route
  projection.
- Backend Runtime / Environment Primitive: Isaac Lab subprocess support.
- Artifacts, reports, and eval suites: which routes are allowed to claim
  product or eval support.

It must not change the MCP capability contract, agent skill strategy, map
artifact schema, or provider profile model.

## Decisions

### D0: ADR Owns The Durable Policy

ADR-0142 records the durable command-surface/backend-support policy:

```text
Isaac Lab remains current for B1 / Map 12 digital twin.
MolmoSpaces household scenes use MuJoCo as the active backend.
MolmoSpaces Isaac support is retired rather than preserved for compatibility.
```

This plan owns execution order, files, tests, and cleanup gates.

### D1: Keep Isaac For Digital Twin

`world=b1-map12 backend=isaaclab` remains a supported experimental
digital-twin route. B1 navigation/readiness proof, local Isaac runtime
preflight, and `scripts/isaac_lab_cleanup/` stay in the repo.

Required invariant:

```text
b1-map12 available_backends == ("isaaclab",)
b1-map12 default_backend == "isaaclab"
```

### D2: MuJoCo Is The MolmoSpaces Mainline

MolmoSpaces operator-facing product and eval defaults use `backend=mujoco`.
MolmoSpaces route docs, README examples, eval-harness recommendations, and
operator-console default route matrix should not imply that Isaac is required
for normal MolmoSpaces household development.

Required invariant:

```text
MolmoSpaces world default_backend == "mujoco"
normal MolmoSpaces product/eval routes use backend=mujoco
```

### D3: MolmoSpaces + Isaac Is Removed

MolmoSpaces + Isaac is removed from active support. This repo has no
backward-compatibility requirement for obsolete demo surfaces, so do not keep a
compatibility shim, hidden route, generic override, or maintainer convenience
entrypoint just because it used to work.

Keep an Isaac file, test, or recipe only when it is needed by one of these
current paths:

- B1 / Map 12 digital-twin readiness, navigation smoke, report, or static
  proof;
- generic Isaac runtime isolation/preflight used by B1;
- historical docs that are explicitly labeled superseded, parked, retired, or
  evidence-only.

Delete or retire MolmoSpaces-specific Isaac entrypoints such as
`molmo-isaac-cleanup-smoke`, prepared MolmoSpaces semantic USD cleanup smoke,
MolmoSpaces Isaac operator-console routes, and generic
`backend=isaaclab_subprocess` MolmoSpaces overrides unless implementation
inspection proves they are required by B1. If B1 needs a shared helper, rename
or move that helper to a B1/generic Isaac boundary instead of preserving the
MolmoSpaces path.

### D4: Genesis Stays Retired

Do not restore Genesis as a backend, comparison lane, optional route, or
dependency surface. Historical Genesis plans and reports may remain as retired
evidence.

## Non-Goals

- Do not remove Isaac Lab support needed by B1 / Map 12.
- Do not redesign the backend plugin model.
- Do not add a new public surface for renderer parity.
- Do not make MolmoSpaces + Isaac pass by silently falling back to MuJoCo,
  placeholder images, or synthetic state.
- Do not update real Isaac GPU proof claims unless a local `.venv-isaaclab/`
  proof is actually run.
- Do not keep compatibility shims for old MolmoSpaces Isaac command shapes.
- Do not restore Genesis.

## Current Evidence To Preserve

Digital-twin support:

- `docs/plans/refactor-reduce-entropy-b1-map12-digital-twin.md` defines B1
  navigation readiness and keeps object/receptacle USD binding and
  manipulation blocked until proven.
- `just harness::b1-map12-navigation-smoke` and related tests are maintainer
  proof surfaces that should remain.

MolmoSpaces Isaac history:

- `docs/plans/isaac-lab-molmospaces-backend-support.md` records that Isaac was
  added as a backend variant but not as a replacement for MuJoCo defaults.
- `docs/plans/mujoco-isaac-minimal-map-task-parity.md` is now superseded by the
  new policy unless the user explicitly reopens MolmoSpaces backend parity.

Genesis history:

- `docs/plans/refactor-reduce-entropy-loop.md` records that the Genesis active
  lane was retired.
- `docs/plans/genesis-scene-camera-backend-lane.md` remains historical
  evidence only.

## Implementation Plan

### Phase 1: Contract And Docs

Update the human-facing contract so the repo says the same thing everywhere:

- README: MolmoSpaces uses MuJoCo by default; Isaac Lab is required for the B1
  digital-twin route and local maintainer proof, not normal MolmoSpaces demos.
- ARCHITECTURE: distinguish backend runtime support from world/backend product
  support. Use `backend=isaaclab` examples only for digital twin or explicitly
  labeled maintainer proof.
- AGENTS/CLAUDE guidance: keep `.venv-isaaclab/` isolation, but avoid wording
  that makes MolmoSpaces Isaac sound like a current public launch axis.
- docs/plans/README: mark old MuJoCo/Isaac parity plans as superseded or
  historical unless reopened.
- Existing MolmoSpaces Isaac parity plan files: add a short in-place
  supersession note so a reader who opens those files directly does not treat
  them as current execution contracts.
- docs/human/technical-design.md: update Backend Strategy so `isaaclab` is
  scoped to B1 / Map 12 digital twin and generic Isaac runtime proof, not
  MolmoSpaces mainline.
- Remove active examples for `molmo-isaac-*` proof commands unless the command
  remains as a B1/generic Isaac proof after implementation.

### Phase 2: Launch Catalog Boundary

Make launch metadata express the support boundary:

- Keep `BACKEND_SPECS["isaaclab"]`.
- Keep `WORLD_SPECS["b1-map12"].available_backends == ("isaaclab",)`.
- Change MolmoSpaces world specs so their normal `available_backends` include
  only `mujoco`.
- Do not add a hidden or experimental backend projection for MolmoSpaces Isaac.

### Phase 3: Operator Console Route Boundary

Make the console route matrix match the product contract:

- Keep B1 / Map 12 Isaac open-task route.
- Remove normal enabled MolmoSpaces Isaac cleanup and map-build route rows.
- Remove disabled MolmoSpaces Isaac rows as well; they no longer serve an
  operator decision after MolmoSpaces Isaac is retired.
- Keep Isaac field UI only if B1 still uses it.
- Preserve resource locks and gates needed by B1 Isaac.

### Phase 4: Command And Backend Selector Boundary

Tighten command-layer acceptance:

- Public `run::surface surface=household-world world=molmospaces/...` should
  reject `backend=isaaclab` once MolmoSpaces no longer lists it as available.
- Public `run::surface surface=household-world world=b1-map12 backend=isaaclab`
  should keep working. The implementation may still use the same
  `isaaclab_subprocess` backend primitive, but acceptance is world-scoped:
  B1 yes, MolmoSpaces no.
- Generic `agent::run household-world.cleanup` and
  `agent::run household-world.map-build` should reject
  `backend=isaaclab_subprocess` for MolmoSpaces worlds. This closes the
  public-route cleanup without leaving an equivalent maintainer shortcut that
  still looks like a normal backend choice.
- Generic `agent::run` routes that target `world=b1-map12` may still lower to
  `isaaclab_subprocess` if that is the current digital-twin implementation.
- Remove `molmo-isaac-*` harness recipes unless they are renamed/reworked into
  generic Isaac or B1 proof commands used by current digital-twin support.
- If the core cleanup backend selector still needs `isaaclab_subprocess` for
  B1, keep only the B1/generic branch and cover it with direct tests. Do not
  leave MolmoSpaces-specific selector acceptance behind.

### Phase 5: Tests And Search Gates

Update tests to encode the new contract:

- MolmoSpaces worlds expose only MuJoCo as normal available backend.
- B1 world exposes Isaac and defaults to Isaac.
- Operator console has no normal MolmoSpaces Isaac product routes.
- Public MolmoSpaces `backend=isaaclab` launch is rejected with an expected
  backend list that does not include Isaac.
- Public B1 `backend=isaaclab` launch resolves and preserves current B1
  digital-twin defaults. The old `map_bundle=b1-map12-room-semantics` default is
  superseded by the thin B1 / Map 12 review/runtime contract.
- Generic `agent::run household-world.cleanup ... backend=isaaclab_subprocess`
  and `agent::run household-world.map-build ... backend=isaaclab_subprocess`
  are rejected for MolmoSpaces worlds.
- Generic `agent::run` or console tests preserve the B1 route if that route is
  still implemented through `isaaclab_subprocess`.
- B1/generic Isaac proof recipes still exist; MolmoSpaces-specific Isaac
  harness recipes are removed or renamed if their implementation remains useful
  for B1.
- Genesis remains retired: no active Genesis backend/route/tests are restored.

## Verification

Focused deterministic checks:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/launch \
  tests/unit/operator_console \
  tests/contract/dev_tools/test_backend_catalog_just_recipes.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/dev_tools/test_isaac_runtime_preflight_just_recipe.py

ruff check \
  roboclaws/launch/backends.py \
  roboclaws/launch/worlds.py \
  roboclaws/operator_console/routes.py \
  tests/unit/launch \
  tests/unit/operator_console \
  tests/contract/dev_tools
```

Stale-surface search:

```bash
rg -n "molmospaces/.+::isaaclab|backend=isaaclab|isaaclab_subprocess|Genesis|genesis" \
  README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md \
  docs/human docs/plans just roboclaws/launch roboclaws/operator_console \
  tests/unit/launch tests/unit/operator_console tests/contract/dev_tools
```

The search does not need to return zero. Acceptable hits are:

- B1 / Map 12 Isaac support.
- Isolated `.venv-isaaclab/` setup guidance.
- Generic or B1 local GPU Isaac harness recipes.
- Historical Genesis or MolmoSpaces-Isaac plans labeled retired,
  superseded, parked, or evidence-only.

## Definition Of Done

- B1 / Map 12 digital-twin route remains available through Isaac.
- MolmoSpaces public/default route metadata no longer presents Isaac as a
  normal available backend.
- Operator console no longer surfaces enabled MolmoSpaces Isaac product rows by
  default.
- Public MolmoSpaces launches reject `backend=isaaclab` unless a deliberate
  new plan reopens MolmoSpaces Isaac support.
- Public B1 launches still accept `backend=isaaclab`.
- Generic `agent::run` MolmoSpaces routes do not accept
  `backend=isaaclab_subprocess` as a normal backend override.
- Generic `agent::run` or console B1 routes still lower to the current Isaac
  backend primitive when that is the digital-twin implementation.
- B1/generic Isaac proof commands remain available and clearly labeled.
- MolmoSpaces-specific Isaac harness recipes are removed, or renamed/reworked
  so their remaining code is no longer a MolmoSpaces backend path.
- Genesis remains retired.
- Tests encode the new boundary so future backend parity work cannot silently
  re-expand MolmoSpaces support.

## Reduce-Entropy Loop Result

Selected mode: plan entropy mode.
Discovery intensity: saturation scan.

The loop found and folded in two material plan gaps:

- P1: generic `agent::run ... backend=isaaclab_subprocess` would otherwise keep
  MolmoSpaces Isaac alive after public `run::surface` cleanup. The plan now
  requires generic MolmoSpaces overrides to reject Isaac and keeps only B1
  world-scoped Isaac lowering.
- P1: after the no-backward-compatibility clarification, hidden or
  maintainer-only MolmoSpaces Isaac routes are not worth preserving. The plan
  now requires deleting or renaming `molmo-isaac-*` recipes unless the remaining
  implementation is directly reworked into B1/generic Isaac proof.

Saturation result: no remaining P0/P1 plan gaps found in the selected scope.
Parked implementation detail: while executing, inspect shared helper use before
deleting Isaac files so B1 support is preserved by world scope rather than by
the old MolmoSpaces compatibility path.

## Grill-With-Docs Batch Result

Accepted on 2026-06-15:

- Keep B1 Isaac as a public launch/catalog and operator-console route, not only
  a harness proof.
- Rename reusable Isaac runtime/preflight pieces away from `molmo-isaac-*`;
  delete Molmo cleanup smoke recipes that are not needed by B1.
- Delete MolmoSpaces-specific Isaac code when tests prove B1 does not need it,
  instead of merely making it unreachable.
- Create a short ADR for the durable backend-support policy.
- Mark old MolmoSpaces Isaac parity plans as superseded in-place so direct
  readers do not treat them as active execution contracts.

## Preflight Contract

Preflight status: DRAFT

Task source: mixed.

Canonical source:
`docs/plans/2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md`.

Route: `$intuitive-refactor`.

Goal: Execute the reviewed Isaac scope cleanup: keep B1 / Map 12 Isaac support,
remove MolmoSpaces Isaac support paths, and preserve MuJoCo as MolmoSpaces
mainline.

Scope:

- Update launch catalog/world metadata so MolmoSpaces worlds expose only
  `mujoco`, while `b1-map12` keeps `isaaclab`.
- Remove operator-console MolmoSpaces Isaac enabled/disabled route rows.
- Reject MolmoSpaces `backend=isaaclab` and generic MolmoSpaces
  `backend=isaaclab_subprocess` overrides.
- Preserve B1 route lowering to the current Isaac backend primitive.
- Delete or rename `molmo-isaac-*` recipes/tests/docs into B1/generic Isaac
  only when directly needed.
- Keep docs/ADR wording consistent with ADR-0142.

Non-goals:

- No Genesis revival.
- No backend plugin framework.
- No compatibility shim or hidden MolmoSpaces Isaac route.
- No real GPU/Isaac proof claim unless actually run.

Entity budget:

- Reuse: `BACKEND_SPECS["isaaclab"]`, B1 world spec, and Isaac
  runtime/preflight helpers needed by B1.
- Remove/merge: MolmoSpaces Isaac launch, console, generic override, and
  harness surfaces.
- New: none expected.
- Expansion triggers: any new hidden route, backend abstraction, or restored
  MolmoSpaces Isaac support requires re-approval.

Context:

- Must read: `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `AGENTS.md`,
  `CLAUDE.md`, this plan, ADR-0142, `docs/human/technical-design.md`,
  `roboclaws/launch/backends.py`, `roboclaws/launch/worlds.py`,
  `roboclaws/operator_console/routes.py`, `just/agent.just`,
  `just/harness.just`, and `just/molmo.just`.
- Useful: old superseded MuJoCo/Isaac plans.
- Avoid unless needed: generated outputs and full historical retrospectives.

Acceptance:

- SUCCESS: MolmoSpaces public/default routes cannot select Isaac; B1
  public/console route still selects Isaac with B1 defaults;
  `molmo-isaac-*` active recipe names are gone or re-owned as B1/generic proof.
- BLOCKED_NEEDS_DECISION: none.
- BLOCKED_NEEDS_LOCAL_VALIDATION: real `.venv-isaaclab` B1 smoke is required
  before claiming live Isaac runtime health, but not required to complete
  deterministic route cleanup.
- INTERMEDIATE_ONLY: none.
- No regressions: MuJoCo MolmoSpaces cleanup/map-build/open-task routes remain
  available; B1 digital-twin route remains available; Agibot route is
  unaffected.

Verification:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/launch \
  tests/unit/operator_console \
  tests/contract/dev_tools/test_backend_catalog_just_recipes.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/dev_tools/test_isaac_runtime_preflight_just_recipe.py

ruff check \
  roboclaws/launch/backends.py \
  roboclaws/launch/worlds.py \
  roboclaws/operator_console/routes.py \
  tests/unit/launch \
  tests/unit/operator_console \
  tests/contract/dev_tools
```

Integration search gate:

```bash
rg -n "molmospaces/.+::isaaclab|molmo-isaac|backend=isaaclab_subprocess" \
  README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md \
  docs/human docs/plans just roboclaws/launch roboclaws/operator_console \
  tests/unit/launch tests/unit/operator_console tests/contract/dev_tools
```

Only B1/generic or historical superseded hits are accepted.

Product-run gate:

```bash
just run::surface \
  surface=household-world \
  world=molmospaces/val_0 \
  backend=mujoco \
  preset=map-build \
  agent_engine=direct-runner \
  evidence_lane=world-oracle-labels \
  seed=7 \
  scenario_setup=baseline \
  output_dir=/tmp/roboclaws-molmospaces-mujoco-check
```

Local-live/manual gate: run `just harness::b1-map12-navigation-smoke ...` on an
Isaac host before claiming B1 live runtime health. This gate is unavailable
unless a local GPU/Isaac runtime is ready.

Optional:

```bash
just agent::eval recommend \
  plan=docs/plans/2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md \
  budget=focused
```

Execution:

- Main: root supervisor; inspect diffs and protect unrelated worktree changes.
- Worker: none.
- Worker goal: none.

To execute:

```text
/goal execute docs/plans/2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md with intuitive-refactor
```

Optional tracking: none.

Approval: LGTM/approve/go ahead approves; edits request revision.

## Execution Log

### 2026-06-15 Intuitive-Refactor Slice

- Changed MolmoSpaces launch world metadata so available backends are only
  `("mujoco",)`.
- Kept `b1-map12` on `backend=isaaclab` and passed `world=b1-map12` through to
  private dispatch when lowering to `isaaclab_subprocess`.
- Removed enabled and disabled MolmoSpaces Isaac rows from the operator-console
  route matrix; B1 keeps Isaac field groups, locks, gates, and open-task route
  support.
- Rejected generic MolmoSpaces `agent::run ... backend=isaaclab_subprocess`
  and direct `molmo::household-world-impl ... backend=isaaclab_subprocess`
  shortcuts unless the resolved launch world is B1.
- Removed active `molmo-isaac-*` harness recipe names. Kept generic
  `isaac-runtime-preflight`, generic `isaac-runtime-smoke`, and
  `b1-map12-navigation-smoke`; removed the MolmoSpaces cleanup/prepared-cleanup
  and USD-reference harness shortcuts.
- Added/updated unit and contract tests for MolmoSpaces MuJoCo-only metadata,
  B1 Isaac lowering, console route absence, public MolmoSpaces Isaac rejection,
  private backend override rejection, and harness recipe cleanup.

Evidence so far:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/launch/test_environment_setup_catalog.py \
  tests/unit/operator_console/test_routes.py \
  tests/unit/operator_console/test_operator_console.py \
  tests/unit/operator_console/test_launcher.py \
  tests/contract/dev_tools/test_backend_catalog_just_recipes.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/dev_tools/test_isaac_runtime_preflight_just_recipe.py
```

Passed on 2026-06-15.

Final evidence:

```bash
ruff check \
  roboclaws/launch/backends.py \
  roboclaws/launch/worlds.py \
  roboclaws/operator_console/routes.py \
  tests/unit/launch \
  tests/unit/operator_console \
  tests/contract/dev_tools
```

Passed on 2026-06-15.

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/launch \
  tests/unit/operator_console \
  tests/contract/dev_tools/test_backend_catalog_just_recipes.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/dev_tools/test_isaac_runtime_preflight_just_recipe.py
```

Passed on 2026-06-15.

```bash
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=b1-map12 backend=isaaclab \
  agent_engine=codex-cli prompt='inspect the digital twin' \
  evidence_lane=world-oracle-labels
```

Passed as a trace gate on 2026-06-15: public B1 launch resolves to
`world=b1-map12`, `backend=isaaclab`, B1 map/scene defaults, and the private
`backend=isaaclab_subprocess` implementation.

```bash
ROBOCLAWS_JUST_TRACE=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=isaaclab \
  agent_engine=codex-cli preset=map-build evidence_lane=world-oracle-labels
```

Rejected on 2026-06-15 with `backend 'isaaclab' cannot run world
'molmospaces/val_0'; expected mujoco`.

```bash
ROBOCLAWS_JUST_TRACE=1 just agent::run \
  household-world.cleanup direct world-oracle-labels \
  backend=isaaclab_subprocess
```

Rejected on 2026-06-15 with `backend=isaaclab_subprocess is scoped to
world=b1-map12`.

```bash
rg -n "molmospaces/.+::isaaclab|backend=isaaclab|isaaclab_subprocess|Genesis|genesis" \
  README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md \
  docs/human docs/plans just roboclaws/launch roboclaws/operator_console \
  tests/unit/launch tests/unit/operator_console tests/contract/dev_tools
```

Passed on 2026-06-15 by inspection. Remaining hits are B1/generic Isaac support,
explicit MolmoSpaces rejection guards/tests, this completed gate, or historical
Genesis / MolmoSpaces-Isaac docs labeled retired, superseded, implemented, or
evidence-only.

```bash
just run::surface \
  surface=household-world \
  world=molmospaces/val_0 \
  backend=mujoco \
  preset=map-build \
  agent_engine=direct-runner \
  evidence_lane=world-oracle-labels \
  seed=7 \
  scenario_setup=baseline \
  output_dir=/tmp/roboclaws-molmospaces-mujoco-check
```

Passed on 2026-06-15. Report:
`/tmp/roboclaws-molmospaces-mujoco-check/0615_2131/seed-7/report.html`.

Skipped local-live/manual gate: `just harness::b1-map12-navigation-smoke ...`.
No real B1 Isaac GPU/runtime health is claimed by this deterministic refactor
slice.
