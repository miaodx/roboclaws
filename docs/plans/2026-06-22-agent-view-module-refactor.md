---
plan_scope: agent-view-module-refactor
status: Proposed
created: 2026-06-22
last_reviewed: 2026-06-22
implementation_allowed: false
source:
  - user north-star clarification on open-ended robot agency and eval-driven evolution
  - plan-bakeoff candidate selection, 2026-06-22
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - CONTEXT.md
  - docs/human/domain.md
  - docs/human/mcp-skills-and-semantic-profiles.md
  - docs/human/molmospaces-settings.md
  - docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md
  - docs/adr/0138-use-detector-only-visual-grounding-sidecar.md
  - docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md
  - docs/adr/0141-use-eval-harness-as-maintainer-orchestration-facade.md
---

# Agent View Module Refactor

## Goal

Make **Agent View** the explicit module boundary for what a household-world
agent may see and act on.

The refactor should turn the current scattered rule into a concrete contract:

```text
Every agent-facing input is either:
  real-robot-obtainable public evidence,
  provenance-limited public evidence,
  or an explicitly blocked capability/status.

Private scorer truth, hidden setup state, simulator-only affordances, and
report-only views must not enter Agent View.
```

This is Candidate 1 from the architecture bakeoff. Candidate 4, active
perception, is included as an adapter inside this module. Candidate 2,
eval-to-evolution, is the immediate follow-up after this plan creates a stable
`agent_view_module` evolution target. Candidate 3, capability-slice eval
groups, stays parked as later eval-harness metadata.

## Why Now

The repo has intentionally broadened its surface:

- open-ended household prompts;
- coding-agent engines such as Codex CLI and Claude Code;
- OpenAI Agents SDK;
- direct deterministic runners;
- Base Navigation Map and Runtime Metric Map artifacts;
- `world-public-labels`, `camera-grounded-labels`, and `camera-raw-fpv`
  evidence lanes;
- Grounding DINO and other camera labelers;
- RAW-FPV candidate declaration and recovery;
- eval suites and eval-harness selection rows.

That breadth is not the problem. The current entropy is that the rule
"only expose what a real robot could obtain" is enforced by a mix of payload
builders, MCP profile metadata, RAW-FPV guidance, visual-candidate lifecycle
helpers, report code, and repeated `assert_no_forbidden_agent_view_keys` calls.

A clear Agent View Module gives the broad surface one ownership point. It also
lets evals later route failures to `agent_view_module` instead of vaguely
blaming provider routes, prompts, or broad harness rows.

## Current Evidence

Current source shape:

- `roboclaws/household/realworld_agent_view_contract.py` owns useful helper
  behavior such as forbidden-key checks, public acceptance config, policy-trace
  delegation, and real-robot readiness extraction.
- `roboclaws/household/realworld_contract_payloads.py` builds
  `agent_view_payload`, `runtime_metric_map_payload`, policy view, camera-model
  evidence, model-declared observations, and sanitized visible detections.
- `roboclaws/household/realworld_contract.py` still acts as a broad coordinator
  and forwards many private guard functions into helper modules.
- `roboclaws/household/agibot_cleanup_contract.py` has a separate
  `agent_view_payload` with the same top-level shape for the Agibot pilot path.
  This is a second owner for Agent View semantics and must be brought under the
  same guard/schema contract even if backend-specific payload construction
  stays local in the first implementation slice.
- RAW-FPV and active perception semantics are spread across
  `raw_fpv_guidance.py`, `realworld_visual_candidates.py`,
  `realworld_visual_candidate_declarations.py`,
  `realworld_visual_candidate_lifecycle.py`, `visual_grounding.py`, and
  `visual_grounding_contract.py`.
- `roboclaws/mcp/profiles.py` owns capability profile metadata that influences
  the agent-facing public tool/capability surface.
- `skills/eval-harness/scripts/select_eval_harness.py` and
  `skills/eval-harness/scripts/eval_harness_rows.py` still exist on this
  branch. The JSON row catalog and ADR-0145 discussed in an earlier branch are
  not present here, so this plan must not assume them.
- The current eval-harness selector already has signals for
  `realworld_contract`, `visual_grounding`, `raw_fpv`, and
  `runtime_metric_map`, but it does not explicitly know a future
  `roboclaws/household/agent_view.py` path yet.

Observed risk:

- Agent View is documented as the exact public information available to the
  cleanup agent, but current implementation does not expose one module-shaped
  interface that names all inputs, provenance, blocked capabilities, and
  private exclusions.
- `static_fixture_projection` still appears in current payload paths. This plan
  should not promote it as a new long-term Agent View concept. It may remain as
  a compatibility/report/map input where current behavior still needs it, but
  the explicit contract should center Base Navigation Map, Runtime Metric Map,
  public runtime evidence, active perception evidence, public MCP capabilities,
  and blocked/provenance-limited states.

## Architecture Decision To Record

Create a short ADR before implementation.

Decision:

- Agent View is a first-class household-world module boundary.
- Agent View owns agent-facing input assembly, provenance labeling,
  real-robot-obtainability labeling, blocked-capability labeling, and private
  exclusion enforcement.
- Active perception is an Agent View adapter, not a separate top-level product
  goal.
- Eval-to-evolution should later be allowed to target `agent_view_module` as a
  concrete evolution target.

The ADR should not approve a broad eval-harness redesign. It should only name
the boundary that this refactor creates.

## Target Module Shape

Prefer evolving the existing implementation instead of adding a parallel
concept.

Suggested package shape:

```text
roboclaws/household/agent_view.py
  AgentViewPayload
  AgentViewSection / provenance helper types if useful
  build_agent_view(...)
  build_runtime_metric_map_view(...)
  build_policy_view(...)
  assert_no_private_agent_view_keys(...)
  strip_private_agent_view_keys(...)
  label_real_robot_obtainability(...)

roboclaws/household/agent_view_adapters.py       # only if agent_view.py gets too large
  map adapter
  runtime evidence adapter
  active perception adapter
  mcp capability/profile adapter
```

If a rename is lower churn, `realworld_agent_view_contract.py` may become the
module owner directly. Avoid a second module that duplicates the same concept.

Expected Agent View sections:

| Section | Owns | Notes |
| --- | --- | --- |
| `task` | prompt, preset/intent, public acceptance config | No private scenario setup or scorer target count. |
| `capabilities` | public tool names, capability profile metadata, blocked capabilities | Pulls from MCP/capability profile source, not duplicated prose. |
| `base_navigation_map` | start-of-run public map context | Must not include static movable inventory or private relocation truth. |
| `runtime_metric_map` | public current-run map/evidence enrichment | Owns observed objects, anchors, candidates, map-update candidates. |
| `active_perception` | RAW-FPV observations, camera-grounded labels, visual-grounding provenance | Candidate 4 lives here. Include uncertainty and sidecar readiness. |
| `policy_view` | allowed/excluded policy inputs | Report-only views stay explicitly excluded. |
| `readiness` | real-robot readiness and blocked/provenance-limited states | Use explicit labels rather than silent fallbacks. |
| `privacy` | forbidden key policy and private-truth absence evidence | One canonical guard. |

Names may change during implementation, but these responsibilities should not
disappear.

## Implementation Slices

### Slice 1: ADR And Interface Inventory

- Add the ADR described above.
- Inventory current agent-facing payload builders and private guard call sites.
- Identify which current fields are public current contract, historical/report
  compatibility, or migration candidates.
- Record the intended owner for each field in the plan or ADR appendix.
- Include both MolmoSpaces/realworld and Agibot cleanup Agent View producers in
  the inventory. Do not let the new module become Molmo-only by accident.

Acceptance:

- The ADR names Agent View as the module boundary.
- The field inventory distinguishes Base Navigation Map, Runtime Metric Map,
  active perception, MCP capability metadata, blocked capabilities, and private
  exclusions.
- The inventory explicitly marks `static_fixture_projection` as not a new
  long-term public Agent View center.
- The inventory has a row for `agibot_cleanup_contract.agent_view_payload` and
  states whether it migrates in this plan or remains a backend-local adapter
  behind shared Agent View guards.

### Slice 2: Canonical Agent View Builder

- Move or wrap `agent_view_payload` construction behind one canonical builder.
- Centralize forbidden-private-key enforcement through the Agent View module.
- Add explicit real-robot-obtainability/provenance labels to top-level Agent
  View sections.
- Keep existing product launch commands and output artifact names stable.
- Preserve current `agent_view.json` top-level compatibility for this refactor
  unless the ADR explicitly approves a schema-version change. New structured
  sections may be additive first; migration/deletion of old top-level keys
  should be a later artifact-schema cleanup.
- Ensure MolmoSpaces and Agibot Agent View payloads use the same forbidden-key
  guard and section labeling vocabulary, even if their backend-specific map or
  movement evidence stays in separate adapters.

Acceptance:

- Existing `agent_view.json` output remains available.
- Callers use the canonical Agent View module rather than assembling payloads
  directly across unrelated helper modules.
- Forbidden private fields still fail loudly.
- No compatibility shim is added for obsolete public command names.
- The Agibot payload path is either migrated to the shared builder or explicitly
  wrapped by shared Agent View validation; leaving it as an unvalidated duplicate
  is not accepted.

### Slice 3: Active Perception Adapter

- Bring RAW-FPV guidance, camera-grounded-label evidence, detector provenance,
  visual-grounding sidecar status, uncertainty, and candidate lifecycle summary
  under the Agent View active-perception section.
- Preserve the current distinction between `camera-raw-fpv` and
  `camera-grounded-labels`.
- Do not make DINO or RAW-FPV separate top-level goals outside Agent View.

Acceptance:

- RAW-FPV observations and camera-grounded labels carry source/provenance.
- Sidecar unavailable, provider unavailable, and no-camera evidence states are
  visible as blocked/provenance-limited Agent View state rather than silent
  fallback.
- Existing RAW-FPV candidate recovery tests still pass or are updated to assert
  the new Agent View section.

### Slice 4: MCP Capability/Profile Adapter

- Ensure Agent View capability metadata is derived from current MCP capability
  profiles and public tool names.
- Represent blocked capabilities in Agent View using the same vocabulary as
  capability profiles/reports where possible.
- Keep server/runtime adapters thin; do not move cleanup strategy or prompt
  policy into server code.

Acceptance:

- Agent View describes available public tools and blocked capabilities without
  duplicating stale profile semantics.
- MCP server and launch routes keep the same public command grammar.

### Slice 5: Eval-Harness Hook, Not Redesign

- Teach eval-harness selection to notice Agent View module changes if current
  path-based rules do not already cover them.
- Add an Agent View focused deterministic gate if the existing focused tests are
  too scattered to catch private leakage/provenance drift.
- Do not reorganize the whole row taxonomy in this plan.

Acceptance:

- `just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused`
  selects deterministic Agent View / MCP / perception relevant rows.
- Changes to `roboclaws/household/agent_view.py`,
  `realworld_agent_view_contract.py`, `realworld_contract_payloads.py`, or
  `agibot_cleanup_contract.py` select the same Agent View contract gate.
- `execute budget=focused` either runs focused deterministic gates or records
  explicit blocked evidence for environment/provider-only rows.
- No new provider matrix is introduced by this refactor.

## Non-Goals

- Do not delete active evidence lanes.
- Do not remove DINO, RAW-FPV, OpenAI Agents SDK, Codex CLI, Claude Code, or
  provider profiles just because the surface is broad.
- Do not redesign eval-harness row taxonomy in this plan.
- Do not add the eval `evolution_target` field in this plan; park it as the
  immediate follow-up after Agent View exists as a target.
- Do not change public `just run::surface` grammar.
- Do not introduce a new robotics backend or simulator.
- Do not rely on private scorer truth, hidden relocation data, static movable
  object inventory, or report-only camera views as agent inputs.
- Do not add compatibility wrappers for obsolete task/profile names.

## Verification Plan

Start with eval-harness:

```bash
just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused
```

The recommendation pass is discovery evidence, not an instruction to run every
selected row for every slice. On 2026-06-22, this plan selected 19 focused rows
because the plan intentionally mentions eval harness, cleanup, open-ended,
MCP/checker, DINO, RAW-FPV, map-build, launch catalog, Codex, and Agent SDK.
That is expected for the whole refactor, but the first execution slice should
copy the relevant narrow subset into its preflight instead of claiming the full
matrix as required DoD.

Run full focused execution only after the slice owner has narrowed the row set
or explicitly accepts the cost/provider/runtime implications:

```bash
just agent::eval execute plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused
```

Focused deterministic checks expected to be relevant:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py \
  tests/unit/molmo_cleanup/test_visual_grounding.py \
  tests/unit/evals/test_eval_harness_selector.py
```

Static checks:

```bash
ruff check roboclaws/household roboclaws/mcp skills/eval-harness tests
ruff format --check roboclaws/household roboclaws/mcp skills/eval-harness tests
git diff --check
rg -n "hidden|relocation|private|scorer|static_fixture_projection" \
  roboclaws/household tests docs/plans/2026-06-22-agent-view-module-refactor.md
```

Optional local/live proof only after deterministic gates:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels

just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=map-build agent_engine=direct-runner \
  evidence_lane=camera-grounded-labels camera_labeler=grounding-dino
```

Live coding-agent or Agent SDK evals remain opt-in and provider/environment
dependent. They should be selected through eval-harness and recorded as run,
blocked, or skipped by budget; do not claim live proof from deterministic tests.

## Risks And Stop Gates

- **Scope creep into eval redesign:** stop if implementation starts reshaping
  eval-harness taxonomy beyond path selection or a focused Agent View gate.
- **Scope creep into server behavior:** stop if MCP server or runtime adapter
  code starts owning cleanup/search/map-build strategy.
- **Private truth leakage:** stop if a desired report field cannot be included
  without exposing private scorer/setup truth to Agent View.
- **Public command churn:** stop if a slice requires changing
  `just run::surface` grammar; that needs a separate plan/ADR.
- **Live provider dependency:** stop before requiring paid/live provider
  success for the deterministic refactor definition of done.
- **Eval-harness over-selection:** stop before treating all rows selected by
  the whole-plan `recommend` pass as mandatory for a small slice. Narrow the
  execution preflight to the changed files and accepted slice.
- **Mixed dirty worktree:** stop before staging or committing unrelated files.

## Follow-Up Sequence

1. **Eval-To-Evolution Feedback Module:** add `evolution_target` to eval result
   and harness summaries after `agent_view_module` exists as a stable target.
2. **Capability-Slice Eval Groups:** add lightweight capability-slice metadata
   to eval-harness rows only after the Agent View and evolution-target
   contracts exist.
3. **Surface stripping:** remove or retire surfaces only when eval evidence and
   architecture docs show they no longer serve open-ended robot agency or
   eval-driven evolution.

## Open Questions

1. Should the module file be named `agent_view.py`, or should
   `realworld_agent_view_contract.py` become the canonical owner to minimize
   churn? Proposed default: create `agent_view.py` as the canonical public
   module and move existing helper behavior there, leaving no new parallel
   concept.
2. Which current `agent_view_payload` fields are contractual versus historical
   report compatibility? Proposed default: decide in Slice 1 inventory before
   code movement.
3. Should the new top-level Agent View sections be additive in
   `agent_view.json`, or should existing top-level keys be migrated into
   sections in one breaking artifact-schema change? Proposed default: additive
   first, no artifact-breaking key deletion in this plan.
4. What is the minimum focused test set that proves Agent View without running
   the whole household suite? Proposed default: add one focused Agent View
   contract test module and keep the existing MCP/profile/perception focused
   tests as support.
5. Should Agibot use the same builder immediately or only the same validation
   and labels? Proposed default: share guard/schema helpers immediately; migrate
   full builder only if it does not pull Agibot-specific backend logic into the
   household realworld path.

## Reduce-Entropy Loop Notes

Selected mode: plan entropy mode.

Why: this is a new architecture refactor plan that needed missing decisions,
weak assumptions, and proof gaps found before preflight or execution.

Redirect: none.

Discovery intensity: saturation scan.

Demand sanity gate: passed. Candidate 1 deserves a new plan and ADR because the
current repo already has broad live-agent, Agent SDK, direct-runner,
perception, map, and eval surfaces; the surprise is not breadth, but the lack
of one explicit Agent View boundary for real-robot-obtainable inputs.

Round 1 findings resolved in this plan:

- Agibot has a separate `agent_view_payload`, so the plan now requires both
  MolmoSpaces/realworld and Agibot Agent View producers to share the same
  guard/schema vocabulary.
- The current branch has `select_eval_harness.py` and `eval_harness_rows.py`,
  not the JSON row catalog or ADR-0145 from another branch; the plan now treats
  those as absent.
- The future `roboclaws/household/agent_view.py` path is not an explicit
  eval-harness signal today; Slice 5 now requires a focused selector hook.

Round 2 findings resolved in this plan:

- New structured Agent View sections should be additive first. Deleting existing
  `agent_view.json` top-level keys would be an artifact-schema change and is
  out of scope unless the ADR explicitly approves it.
- `static_fixture_projection` may remain as compatibility/report/map input
  where current code still needs it, but it must not become the new public
  Agent View center.

Round 3 findings resolved in this plan:

- `just agent::eval recommend ... budget=focused` currently selects 19 rows for
  the whole plan. This is useful discovery evidence but too broad for a first
  implementation slice. The verification plan now requires slice-level
  narrowing before `execute`.

Parked observations:

- Eval `evolution_target` belongs to the Candidate 2 follow-up after this plan
  creates `agent_view_module` as a stable target.
- Capability-slice eval grouping belongs to later row metadata, not this
  refactor.
- Surface stripping should wait for eval and architecture evidence that a route
  no longer serves open-ended robot agency or eval-driven evolution.

Saturation status: saturated for plan entropy. No remaining P0/P1 plan gap was
found after Agibot ownership, eval-harness path selection, artifact-schema
compatibility, and whole-plan row over-selection were made explicit.

The next workflow should check:

- scope leaks between C1, C2, C3, and C4;
- implementation preflight for Slice 1;
- ADR naming and numbering;
- exact field-inventory format;
- narrow focused proof commands for the first slice.

## Current Recommendation

Proceed to `$intuitive-preflight` for Slice 1: ADR plus Agent View interface
inventory, including MolmoSpaces and Agibot producers, without starting the code
movement yet.
