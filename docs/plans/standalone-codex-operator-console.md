# Standalone Codex Operator Console

**Status note, 2026-06-15:** current console route policy is world-scoped.
MolmoSpaces console routes use MuJoCo. Isaac Lab remains current for the
B1 / Map 12 digital-twin route and generic Isaac runtime proof; old
MolmoSpaces Isaac cleanup/map-build rows in this plan are historical target
rows, not current route guidance. See
[`2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md`](2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md)
and ADR-0142.

## Goal

Build a standalone HTML operator console for Roboclaws live Codex robot runs.
The console should launch supported existing task routes, accept custom task
prompts only where the route can carry them safely, show live robot state and
agent decision evidence, provide operator controls, and hand off completed runs
to the existing `report.html` artifacts.

The target runtime was originally Codex controlling MolmoSpaces/MuJoCo,
MolmoSpaces Isaac, and Agibot G2 routes. Current console support keeps
MolmoSpaces/MuJoCo, B1 / Map 12 Isaac, and Agibot G2 routes. Direct, OpenClaw,
appliance, AI2-THOR game, and generic shell execution are out of scope for this
console.

## Idea Shaping Mode

`grill-with-docs-batch` discussion against repo docs and command contracts.

## Source Evidence

- `README.md` - public task grammar and report-oriented project posture.
- `ARCHITECTURE.md` - task, skill, capability profile, backend variant, and
  artifact boundaries.
- `CONTEXT.md` - durable vocabulary for Runnable Task, Backend Variant,
  Runtime Metric Map, Agent View, Private Evaluation, and real-robot gates.
- `docs/human/domain.md` - cleanup report, Agent View, Private Evaluation, and
  blocked manipulation vocabulary.
- `docs/human/technical-design.md` - reviewability, VLM decision evidence, and
  cleanup proof separation.
- `just/README.md` - public command surface, household lanes, Codex live launch
  behavior, and artifact locations.
- `roboclaws/launch/catalog.py` and `roboclaws/household/tasks.py` - catalog
  metadata and current task/driver/profile support.
- `scripts/molmo_cleanup/run_live_codex_cleanup.py` - existing Codex cleanup
  live-run ownership of MCP server, Codex exec, checker, status files, and
  artifacts.
- `scripts/molmo_cleanup/run_live_codex_agibot_map_build.py` and
  `roboclaws/household/agibot_map_build_mcp_server.py` - existing Codex
  semantic-map-build route over Agibot MCP tools.
- `docs/plans/isaac-lab-molmospaces-backend-support.md` - Isaac backend
  variant, local GPU proof gates, and honest `isaac_semantic_pose`
  provenance.
- `docs/plans/agibot-g2-cleanup-support-pilot.md` - Agibot G2 backend variant,
  operator gates, Human Takeover Stop, and blocked manipulation policy.
- `docs/human/railway/appliance-plan.md` - existing appliance shape; used as a
  non-goal for this standalone console.

## Decisions Already Made

- The console is standalone first. Appliance integration is deferred until much
  later.
- The console is Codex-only for v1. It should not expose direct, OpenClaw,
  Claude, VLM game, or arbitrary shell routes.
- Use existing public task routes and Just/Catalog resolution. The browser must
  not submit arbitrary shell commands.
- Custom prompts are supported only on route metadata that can safely pass a
  prompt. Routes without prompt support must disable the prompt input.
- Historical target routes for v1 before ADR-0142:
  - `household-cleanup codex world-labels backend=molmospaces_subprocess`
  - `semantic-map-build codex camera-labels backend=agibot_gdk`
  - `semantic-map-build codex world-labels backend=molmospaces_subprocess`
- Current target route replacement for Isaac:
  - `surface=household-world world=b1-map12 backend=isaaclab agent_engine=codex-cli prompt=...`
- Unsupported desired routes should be visible as disabled cards with concrete
  blocker text. Example: `household-cleanup + agibot_gdk` is disabled because
  physical cleanup manipulation remains blocked.
- Pause and E-stop are separate controls. Pause is cooperative and
  route-specific; E-stop/hard stop is backend-specific and mandatory for real
  robot operation.
- The decision/thinking panel may show public decision evidence, model-provided
  reasoning fields, prompt-state summaries, Codex event summaries, tool traces,
  and provider status. It must not promise hidden/private model chain-of-thought.
- Raw Codex logs are not shown by default. They may be available behind an
  expandable details view with secret redaction.
- The first implementation slice included route code/adapters for MuJoCo,
  Isaac, and Agibot G2. Current support scopes Isaac to B1 / Map 12.
- Proof order is MuJoCo first, B1 Isaac next on the local GPU machine, then
  Agibot G2.
- The console should add a normalized live operator state layer derived from
  existing artifacts instead of forcing every backend to rewrite its output
  format.
- Resource locks are required per backend: `molmospaces_mujoco`, `isaac_gpu`,
  and `agibot_g2`.
- Agibot G2 Start is disabled until the console has the required context and
  operator gate evidence: `context_json`, localization gate, run enablement,
  and visible E-stop/manual stop readiness.
- B1 Isaac Start requires a preflight/runtime-smoke pass or a recent accepted
  preflight artifact before enabling the Codex route.
- Human Takeover Stop ends the run in v1. Continuing requires a new run after
  the operator resolves the condition.
- Runs are marked green only after their route-specific checker passes.

## Idea Shaping Decisions

| # | Question | Classification | Decision | Rationale | Revisit if |
|---|----------|----------------|----------|-----------|------------|
| 1 | Standalone or appliance-first? | Product boundary | Standalone first. | The operator console should not be constrained by the Railway/OpenClaw appliance process layout. | Appliance integration becomes the near-term deployment target. |
| 2 | Arbitrary Just/shell or catalog-backed routes? | Security and command surface | Catalog-backed routes only. | Browser-driven shell execution is too broad for a robot operator surface. | A separate admin-only tool with stronger auth is requested. |
| 3 | Custom prompt support? | Public route contract | Metadata-gated by route. | Some routes can carry a `task`/kickoff prompt safely, others cannot. | All supported runners gain one normalized prompt argument. |
| 4 | Pause semantics? | Safety and runtime control | Cooperative pause plus separate hard stop/E-stop. | A soft agent-loop pause is not equivalent to robot motion stop. | Backends expose one uniform tested pause/stop protocol. |
| 5 | Thinking panel content? | Agent evidence boundary | Show public decision evidence and explicitly surfaced model reasoning; do not promise hidden chain-of-thought. | Keeps the UI reviewable without misrepresenting model internals. | Provider contracts expose a safe richer reasoning artifact. |
| 6 | Target routes? | Scope boundary | Codex over MolmoSpaces/MuJoCo, B1 Isaac, and Agibot G2 only. | These are the target runtimes; direct/OpenClaw are not product targets. | The operator workflow expands to non-Codex drivers. |
| 7 | Disabled unsupported routes? | UX and safety | Show disabled cards with blocker text. | Operators need to see why a desired route is unavailable. | The route matrix becomes too large and needs filtering. |
| 8 | First proof scope? | Acceptance gate | Include MuJoCo, B1 Isaac, and G2 route code in the first implementation, prove in order MuJoCo -> B1 Isaac -> G2. | Local GPU is available and G2 follows simulator proof. | G2 hardware access is delayed or unavailable. |
| 9 | Resource locks? | Runtime safety | Lock per backend resource. | Live simulators, GPU Isaac, and real G2 cannot be treated as unlimited background jobs. | Multi-instance backends become supported and tested. |
| 10 | Green run criteria? | Verification gate | Route-specific checker must pass. | A UI launch is not success without existing report/checker evidence. | Checkers are replaced by a stronger unified operator verifier. |

## Non-Goals

- Do not build an appliance or Railway deployment path in this slice.
- Do not expose OpenClaw Control UI, direct drivers, Claude drivers, VLM game
  routes, or AI2-THOR territory/coverage/navigation routes.
- Do not allow arbitrary browser-submitted shell commands.
- Do not claim physical Agibot cleanup manipulation. Agibot G2 v1 is
  `semantic-map-build` / navigation + perception; cleanup manipulation remains
  `blocked_capability`.
- Do not make Isaac the default cleanup backend.
- Do not leak Private Evaluation, hidden generated mess truth, credentials, or
  raw private scoring data into Agent View or the live decision panel.
- Do not promise private model chain-of-thought visibility.
- Do not continue a run after Human Takeover Stop in v1.

## Smallest Demo

A standalone local console starts a Codex `household-cleanup` run against
MolmoSpaces/MuJoCo, streams live operator state, shows FPV/robot-view evidence
when available, shows latest decision evidence and tool progress, supports
cooperative pause and stop, and links to the generated `report.html` after the
route-specific checker passes.

The smallest demo should still include visible but gated route cards and adapter
code for B1 Isaac and Agibot G2 so the console shape does not need to be
redesigned after the MuJoCo proof.

## Fuller Demo

The console supports the full v1 route matrix:

- MuJoCo cleanup through Codex.
- MuJoCo semantic-map-build through Codex.
- B1 Isaac open-ended task through Codex after local GPU preflight/runtime-smoke
  evidence.
- Agibot G2 semantic-map-build through Codex after context, localization, run
  enablement, and E-stop readiness gates.

The operator can pick an evidence lane, edit supported run parameters, supply a
custom prompt only when enabled, inspect live FPV/chase/map or robot camera
evidence, inspect public decision evidence and expandable raw logs, pause or
stop the run, and open the final report/checker result.

## Acceptance Criteria

- The console has a standalone local entrypoint, for example
  `just console::run`, and does not require the appliance stack.
- Route selection is generated from explicit console route metadata and existing
  task/catalog constraints, not from arbitrary user shell input.
- The v1 UI exposes only Codex target routes, with unsupported combinations
  disabled and explained.
- Prompt input is enabled only on routes whose metadata declares prompt support.
- Each run has a normalized operator state stream or pollable state artifact
  derived from existing run artifacts.
- Live state includes route, run id, backend lock, phase/status, latest action,
  latest public decision evidence, artifact paths, latest view assets, checker
  status, and terminal reason.
- MuJoCo, Isaac, and Agibot G2 resources have separate locks that prevent
  conflicting starts and show the active run owner.
- Pause, Stop, and real-robot E-stop/readiness controls are represented
  separately in the UI and backend contract.
- Agibot G2 Start remains disabled until required operator gate evidence is
  present.
- Isaac Start remains disabled until a preflight/runtime-smoke pass or accepted
  recent preflight artifact is present.
- Finished runs link to `report.html`, `run_result.json`, trace artifacts, and
  checker output.
- A run is marked green only when the route-specific checker passes.
- The UI redacts secrets from raw logs and does not expose Private Evaluation
  data as Agent View or decision input.

## Verification

Initial implementation should provide CI-safe tests for route metadata,
prompt-gating, command construction, lock behavior, operator-state derivation,
and redaction.

Local proof gates:

```bash
just task::run household-cleanup codex world-labels \
  backend=molmospaces_subprocess seed=7 generated_mess_count=5
```

Expected checker shape: Codex agent-driven cleanup, robot views when enabled,
waypoint honesty, real-robot alignment, semantic acceptance floor, and sweep
coverage.

```bash
just task::run semantic-map-build codex world-labels \
  backend=molmospaces_subprocess seed=7 generated_mess_count=5
```

Expected checker shape: Codex agent-driven map build, runtime metric map,
minimal map evidence, waypoint honesty, real-robot alignment, no cleanup
success gate, and report exists.

```bash
just agent::harness isaac-runtime-preflight
just agent::harness isaac-runtime-smoke
just run::surface surface=household-world world=b1-map12 backend=isaaclab \
  agent_engine=codex-cli provider_profile=codex-env \
  prompt="inspect the digital twin" evidence_lane=world-oracle-labels
```

Expected checker shape: B1 / Map 12 Isaac route starts only after local runtime
proof, preserves the B1 map bundle and USD path defaults, and records
robot-view provenance. Real Isaac runtime health still requires local GPU
verification.

```bash
just task::run semantic-map-build codex camera-labels \
  backend=agibot_gdk \
  context_json=<completed-agibot-map-context.json> \
  visual_grounding=grounding-dino
```

Expected checker shape: backend `agibot_gdk`, MCP server
`agibot_semantic_map_build`, agent-driven run, camera evidence or visible
visual-grounding failure, runtime metric map, semantic sweep, no Human Takeover
Stop, and physical manipulation still blocked.

## Vertical Slices

1. **Console route registry**
   Define the v1 route matrix, disabled-route blocker messages, prompt support,
   required parameters, resource locks, preflight gates, and checker commands.

2. **Standalone web shell**
   Add a local server and static HTML/CSS/JS console. It should list route
   cards, show parameters, enforce prompt gating, and start only supported
   Codex routes.

3. **Run launcher and locks**
   Wrap existing `just task::run` / live Codex runners through a safe launcher
   that owns run ids, lock files, process/session metadata, and terminal status.

4. **Normalized operator state**
   Build an adapter that reads existing artifacts such as status files,
   `trace.jsonl`, `codex-events.jsonl`, `run_result.json`, images, and checker
   output into one live operator state contract.

5. **Live robot views and decision evidence**
   Render FPV/chase/map or robot camera timelines, visual-grounding overlays
   when available, latest action, public reasoning/decision evidence, provider
   status, and expandable raw logs with redaction.

6. **Controls**
   Implement cooperative pause where supported, stop/terminate for every route,
   snapshot links, and explicit Agibot E-stop/readiness display. Human Takeover
   Stop is terminal in v1.

7. **MuJoCo proof**
   Run and verify the MolmoSpaces/MuJoCo Codex cleanup route through the
   console.

8. **Isaac proof**
   Wire Isaac preflight gating and run a GPU-backed Isaac Codex cleanup route
   through the console.

9. **Agibot G2 proof**
   Wire Agibot context/operator gates and run G2 semantic-map-build through the
   console once simulator confidence is sufficient and hardware is ready.

## Risks And Assumptions

- Some current Codex routes are detached/tmux-oriented. The console must adapt
  to those artifacts instead of assuming a foreground process model.
- Pause may initially be best-effort because existing runners do not expose one
  uniform pause protocol.
- Isaac availability depends on the local GPU runtime, `.venv-isaaclab/`, and
  local scene assets.
- Agibot G2 verification depends on hardware access, completed context JSON,
  operator localization, run enablement, and E-stop readiness.
- Raw Codex logs may contain credentials, endpoint details, or irrelevant
  provider internals. Redaction is part of the acceptance criteria, not polish.
- A browser UI can make risky runs feel easy. Disabled states, blocker text,
  gates, and proof status must stay prominent.

## GSD Handoff Trigger

Use this plan as the canonical pre-GSD source once implementation starts.

```text
missing planning or phase: manifest + gsd-ingest-docs, then gsd-plan-phase --prd docs/plans/standalone-codex-operator-console.md
```

## GSTACK REVIEW REPORT

Scope note: the user requested `$devex-review`, `$gsd-ui-phase`, and
`$design-review` before implementation. There is no rendered console yet, and
the repo-local GSD workflow entrypoint expected by `$gsd-ui-phase`
(`get-shit-done/bin/gsd-tools.cjs` or `gsd-sdk`) is not available in this
checkout. This report therefore records the pre-GSD, artifact-based review of
this plan and its UI-SPEC. It does not replace live browser DX/design QA after
the console exists.

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| GSD UI Phase | `$gsd-ui-phase` | UI design contract | 1 | CLEAR (artifact) | UI-SPEC passes the 6 checker dimensions: copywriting, visuals, color, typography, spacing, and registry safety. Historical follow-up implementation added public `semantic-map-build codex` Just routes for MolmoSpaces and old Isaac subprocess targets; ADR-0142 now scopes Isaac console support to B1 / Map 12. Console Start should gate on route metadata, locks, and preflights rather than an Agibot-only restriction. |
| DX Review | `$devex-review` | Operator/developer workflow | 1 | PARTIAL (artifact) | Live TTHW cannot be measured yet. Implementation must provide one local entrypoint, metadata-driven route addition, command preview, actionable disabled-state errors, redaction, lock visibility, and final report links. |
| Design Review | `$design-review` | UI/UX gaps | 1 | PARTIAL (artifact) | Classified as app UI. The contract avoids landing-page/AI-SaaS patterns, keeps the robot view as the visual anchor, separates Pause/Stop/E-stop, and constrains type/color/spacing. Live screenshot review remains required after implementation. |
| Eng Review | `/plan-eng-review` | Architecture & tests (required before ship) | 0 for this plan | REQUIRED LATER | Before implementation or ship, review route registry boundaries, launcher safety, locks, redaction, operator-state adapters, and CI-safe tests. |

- **UNRESOLVED:** Live DX score, live design score, and TTHW remain unmeasured until a runnable console exists.
- **VERDICT:** UI design is cleared for implementation planning. Shipping still requires implementation tests plus live browser DX/design review against the running console.
