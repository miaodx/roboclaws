# Phase 136: Generic MCP Entrypoint And Semantic Capability Profiles - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Source:** PRD Express Path (`docs/retrospectives/plans/generic-mcp-entrypoint-semantic-capabilities.md`)

<domain>
## Phase Boundary

Deliver the smallest metadata-first generic MCP entrypoint/router prototype that
can load one selected backend/domain contract profile and expose only that
profile's declared public semantic capability tools. The phase represents the
existing AI2-THOR navigation and MolmoSpaces cleanup contracts as profiles,
classifies simulator shortcuts as accelerators, preserves ADR-0003 public/private
cleanup boundaries, and leaves current demo commands intact.

</domain>

<decisions>
## Implementation Decisions

### Scope
- D-01: A user instruction such as "clean the room" is a Task Prompt, not one
  MCP tool.
- D-02: MCP should expose Semantic Capabilities and selected bounded Semantic
  Services, not raw Environment Primitives.
- D-03: Open-ended task planning belongs to the agent. Services may solve only
  bounded subproblems such as localization, route planning, semantic map query,
  object association, grasp feasibility, and memory retrieval.
- D-04: Build one generic MCP entrypoint/router that loads one selected
  Contract Profile. Do not build a premature universal robot tool set.
- D-05: Contract profiles combine backend and domain when both matter:
  `ai2thor_navigation_v1`, `molmospaces_cleanup_v1`, and later
  `real_robot_cleanup_v1`.
- D-06: Keep this as one coherent GSD phase. ROS/Nav2 or real-robot validation
  is out of scope.

### Capability And Provenance Model
- D-07: Profiles declare capability families: perception, localization,
  mapping, navigation, manipulation, and memory.
- D-08: Agent-facing tools live at the semantic capability or selected semantic
  service layer.
- D-09: Every public profile/tool response metadata path must support honest
  provenance values such as `api_semantic`, `sim_planner`, `nav2_action`,
  `planner_backed`, and `blocked_capability`.
- D-10: Convenience operations must be classified as `canonical`, `composed`, or
  `accelerator`.

### Existing Contract Classification
- D-11: AI2-THOR `observe` is canonical. `move` is profile-specific canonical
  for low-level navigation. `done` is canonical episode lifecycle.
- D-12: AI2-THOR `scene_objects` and current teleport-like `goto` are
  accelerators unless redesigned as decomposed semantic services with traceable
  substeps.
- D-13: MolmoSpaces cleanup profile must preserve ADR-0003 public inputs and
  must not expose Generated Mess Set, acceptable destination sets, target count,
  private manifest, `is_misplaced`, hidden target receptacles, or private
  scoring truth.
- D-14: Deterministic cleanup policies and proof-bundle selection are
  accelerators/baselines/evidence helpers, not the open-ended agent capability.

### Execution Shape
- D-15: Start with a bounded research/design spike that produces
  implementation-ready schema, naming, provenance, and shortcut-classification
  guidance.
- D-16: Implement a small typed profile declaration before rewriting server
  classes.
- D-17: Add adapters/metadata for existing AI2-THOR and MolmoSpaces contracts
  without removing current server implementations.
- D-18: Add a generic router prototype that can load a selected profile and
  register only declared public tools.
- D-19: Add fail-closed tests for unknown profiles, malformed metadata,
  accelerator leakage, stale tool registration, and Molmo private-field leakage.
- D-20: Update agent-facing vocabulary so Task Prompt, Semantic Capability,
  Semantic Service, Demo Recipe, and Accelerator are used consistently.

### the agent's Discretion
- Choose the concrete Python module names, dataclass shape, and test file split
  if they preserve the decisions above.
- The generic router may be test-first and additive. It does not need to replace
  existing production MCP launchers in this phase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source Plan
- `docs/retrospectives/plans/generic-mcp-entrypoint-semantic-capabilities.md` — reviewed PRD,
  accepted autoplan decisions, acceptance criteria, and GSD handoff.

### Existing MCP Contracts
- `ARCHITECTURE.md` — current AI2-THOR and MolmoSpaces MCP contract map.
- `roboclaws/mcp/server.py` — AI2-THOR FastMCP server and current tool surface.
- `roboclaws/molmo_cleanup/realworld_mcp_server.py` — ADR-0003 cleanup FastMCP
  server and fail-closed `scene_objects` rejection.
- `roboclaws/molmo_cleanup/realworld_contract.py` — public/private cleanup
  contract, observed handles, provenance, and forbidden private data.
- `roboclaws/molmo_cleanup/profiles.py` — existing small metadata-registry
  pattern for cleanup profiles.
- `roboclaws/molmo_cleanup/semantic_timeline.py` — centralized semantic cleanup
  vocabulary.

### Durable Decisions
- `docs/adr/0003-separate-cleanup-agent-view-from-private-evaluation.md` —
  ADR-0003 public/private cleanup boundary.
- `docs/adr/0004-use-separate-mcp-servers-for-ai2thor-and-molmo-cleanup.md` —
  current separate-server decision; this phase must extend, not silently
  erase, that history.
- `docs/adr/0006-expose-adr-0003-cleanup-contract-through-mcp.md` — ADR-0003
  MCP public tool surface and private-field exclusions.
- `docs/adr/0106-centralize-semantic-cleanup-vocabulary.md` — vocabulary source
  for cleanup semantic substeps.

### Existing Tests
- `tests/contract/mcp/test_mcp_server.py` — AI2-THOR MCP contract patterns.
- `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py` —
  real-world cleanup MCP privacy/tool behavior.
- `tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py` — existing
  profile metadata validation style.

</canonical_refs>

<specifics>
## Specific Ideas

- Use `profile_id`, `version`, `backend`, `domain`, `capability_families`,
  `public_tools`, `accelerators`, `privacy_exclusions`, and provenance
  expectations as the initial profile declaration fields.
- Keep semantic names visible in metadata even if the FastMCP registration name
  remains the current short tool name.
- Make canonical profile serialization the privacy boundary checked by tests.
- Make accelerator inclusion opt-in and explicit; canonical profile metadata
  should not list accelerator tools as public tools.

</specifics>

<deferred>
## Deferred Ideas

- Real ROS/Nav2 integration.
- Live OpenClaw Gateway validation.
- GPU, Docker, live VLM, paid API, or private-credential validation.
- Removing or replacing the existing AI2-THOR and MolmoSpaces MCP server
  classes.
- Whole-task tools such as `cleanup_room()`.
- ADR update. The source plan says to create an ADR only after the prototype
  answers whether this extends or supersedes ADR-0004.

</deferred>

---

*Phase: 136-generic-mcp-entrypoint-and-semantic-capability-profiles*
*Context gathered: 2026-05-14 via PRD Express Path*
