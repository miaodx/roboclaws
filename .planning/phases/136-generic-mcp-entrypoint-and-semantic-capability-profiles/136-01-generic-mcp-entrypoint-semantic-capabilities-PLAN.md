# Phase 136 Plan: Generic MCP Entrypoint And Semantic Capability Profiles

## Source

- PRD: `docs/plans/generic-mcp-entrypoint-semantic-capabilities.md`
- Context: `.planning/phases/136-generic-mcp-entrypoint-and-semantic-capability-profiles/136-CONTEXT.md`
- Research: `.planning/phases/136-generic-mcp-entrypoint-and-semantic-capability-profiles/136-RESEARCH.md`

## Goal

Add an additive profile/router layer for MCP semantic capabilities so existing
AI2-THOR and MolmoSpaces contracts can be represented as backend/domain-specific
profiles, with simulator accelerators and Molmo private evaluator truth excluded
from canonical public profiles.

## Scope

- Profile declaration schema and validation under `roboclaws/mcp/`.
- Built-in `ai2thor_navigation_v1` and `molmospaces_cleanup_v1` metadata.
- Generic router prototype that loads exactly one profile and registers only
  selected public tools.
- Contract tests for profile validation, accelerator exclusion, router
  registration, unknown-profile errors, and Molmo privacy exclusions.
- Focused docs/skill vocabulary updates for Task Prompt, Semantic Capability,
  Semantic Service, Demo Recipe, and Accelerator.

## Non-Goals

- No ROS/Nav2 live integration.
- No Docker Gateway, GPU, paid VLM, private credential, or real-robot
  validation.
- No replacement or removal of existing MCP server classes.
- No whole-task MCP tools such as `cleanup_room()`.
- No ADR update until the prototype proves whether ADR-0004 is extended or
  superseded.

## Tasks

1. Add semantic profile schema and validation.
   - Read first: `roboclaws/molmo_cleanup/profiles.py`,
     `roboclaws/mcp/server.py`, `roboclaws/molmo_cleanup/realworld_mcp_server.py`.
   - Modify: `roboclaws/mcp/profiles.py`.
   - Acceptance: profile validation rejects unknown families, accelerator tools
     in canonical public tools, missing descriptors, and forbidden private keys.

2. Add built-in AI2-THOR and MolmoSpaces profile metadata.
   - Read first: `docs/adr/0003-separate-cleanup-agent-view-from-private-evaluation.md`,
     `docs/adr/0006-expose-adr-0003-cleanup-contract-through-mcp.md`,
     `roboclaws/molmo_cleanup/realworld_contract.py`.
   - Modify: `roboclaws/mcp/profiles.py`.
   - Acceptance: `ai2thor_navigation_v1` lists `scene_objects` and `goto` only
     as accelerators; `molmospaces_cleanup_v1` serialized metadata contains no
     ADR-0003 private evaluator fields.

3. Add generic MCP entrypoint/router prototype.
   - Read first: `roboclaws/mcp/server.py`,
     `roboclaws/molmo_cleanup/realworld_mcp_server.py`.
   - Modify: `roboclaws/mcp/entrypoint.py`.
   - Acceptance: loading an unknown profile raises an actionable error, and a
     mock FastMCP registration test sees only tools from the selected profile's
     `public_tools`.

4. Add contract/unit tests.
   - Modify: `tests/contract/mcp/test_semantic_profiles.py`.
   - Acceptance: tests cover profile parsing/validation, built-in metadata,
     accelerator exclusion, Molmo privacy exclusions, and router registration.

5. Update agent-facing vocabulary.
   - Read first: `docs/human/agent-task-command-taxonomy.md`,
     `docs/human/coding-agent-nav-server.md`,
     `docs/human/molmospaces-settings.md`,
     `skills/ai2thor-navigator/SKILL.md`.
   - Modify the smallest docs/skill surfaces needed to make Task Prompt,
     Semantic Capability, Semantic Service, Demo Recipe, and Accelerator
     language consistent.
   - Acceptance: docs do not describe `scene_objects` or teleport-like `goto`
     as canonical real-robot capabilities.

## Acceptance Checks

- The repo has a documented semantic capability model aligned with
  `CONTEXT.md` and the reviewed PRD.
- Existing AI2-THOR and MolmoSpaces contracts can be represented as profiles.
- A generic router can load one profile and register only its public tools in a
  fast test.
- Canonical profile metadata excludes AI2-THOR accelerators by default.
- Molmo cleanup profile preserves ADR-0003 public/private boundaries.
- Existing demo recipes are not changed or removed.

## Verification Plan

- `.venv/bin/ruff check roboclaws/mcp/profiles.py roboclaws/mcp/entrypoint.py tests/contract/mcp/test_semantic_profiles.py`
- `.venv/bin/ruff format --check roboclaws/mcp/profiles.py roboclaws/mcp/entrypoint.py tests/contract/mcp/test_semantic_profiles.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/mcp/test_semantic_profiles.py tests/contract/mcp/test_mcp_server.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py`

## Must-Haves

- A-09 is covered by this plan.
- Profile metadata is additive and does not alter existing server behavior.
- Accelerator and privacy exclusions fail closed in tests.
- No local-dev hardware, Docker, paid API, or private-credential gate is crossed.
