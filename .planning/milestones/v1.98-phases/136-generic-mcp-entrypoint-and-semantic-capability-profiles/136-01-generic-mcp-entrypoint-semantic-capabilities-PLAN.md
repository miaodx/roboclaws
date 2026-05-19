---
phase: 136
plan: 136-01
wave: 1
depends_on: []
autonomous: true
requirements:
  - A-09
files_modified:
  - roboclaws/mcp/profiles.py
  - roboclaws/mcp/entrypoint.py
  - tests/contract/mcp/test_semantic_profiles.py
  - docs/human/coding-agent-nav-server.md
  - docs/human/molmospaces-settings.md
  - skills/ai2thor-navigator/SKILL.md
---

# Phase 136 Plan: Generic MCP Entrypoint And Semantic Capability Profiles

## Source

- PRD: `docs/retrospectives/plans/generic-mcp-entrypoint-semantic-capabilities.md`
- Context: `.planning/milestones/v1.98-phases/136-generic-mcp-entrypoint-and-semantic-capability-profiles/136-CONTEXT.md`
- Research: `.planning/milestones/v1.98-phases/136-generic-mcp-entrypoint-and-semantic-capability-profiles/136-RESEARCH.md`

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

<task id="T1" type="auto">
  <title>Add semantic profile schema and validation</title>
  <read_first>
    <file>roboclaws/molmo_cleanup/profiles.py</file>
    <file>roboclaws/mcp/server.py</file>
    <file>roboclaws/molmo_cleanup/realworld_mcp_server.py</file>
  </read_first>
  <action>
    Create `roboclaws/mcp/profiles.py` with typed profile/tool declarations,
    capability-family constants, tool classification constants, provenance
    vocabulary, public serialization, profile lookup, and validation helpers.
  </action>
  <acceptance_criteria>
    <criterion>`roboclaws/mcp/profiles.py` defines `ContractProfile` and `ToolDescriptor`.</criterion>
    <criterion>Validation rejects accelerator descriptors in canonical `public_tools`.</criterion>
    <criterion>Validation rejects serialized public profile metadata containing configured forbidden private keys.</criterion>
  </acceptance_criteria>
</task>

<task id="T2" type="auto">
  <title>Add built-in AI2-THOR and MolmoSpaces profile metadata</title>
  <read_first>
    <file>docs/adr/0003-separate-cleanup-agent-view-from-private-evaluation.md</file>
    <file>docs/adr/0006-expose-adr-0003-cleanup-contract-through-mcp.md</file>
    <file>roboclaws/molmo_cleanup/realworld_contract.py</file>
  </read_first>
  <action>
    Add `ai2thor_navigation_v1` and `molmospaces_cleanup_v1` built-in profiles.
    AI2-THOR public tools are `observe`, `observe_archived`, `move`, and `done`;
    AI2-THOR accelerators are `scene_objects` and `goto`. Molmo public tools
    mirror the ADR-0003 real-world MCP surface and exclude private evaluator
    fields.
  </action>
  <acceptance_criteria>
    <criterion>`ai2thor_navigation_v1` lists `scene_objects` and `goto` only under accelerators.</criterion>
    <criterion>`molmospaces_cleanup_v1` public metadata contains no `Generated Mess Set`, `acceptable_destination`, `private_manifest`, `is_misplaced`, or hidden target fields.</criterion>
  </acceptance_criteria>
</task>

<task id="T3" type="auto">
  <title>Add generic MCP entrypoint/router prototype</title>
  <read_first>
    <file>roboclaws/mcp/server.py</file>
    <file>roboclaws/molmo_cleanup/realworld_mcp_server.py</file>
  </read_first>
  <action>
    Create `roboclaws/mcp/entrypoint.py` with a generic profile loader and a
    registration helper that registers exactly the selected profile's public
    tools against supplied handler callables.
  </action>
  <acceptance_criteria>
    <criterion>Unknown profile ids raise `ValueError` that includes the unknown id and allowed profile ids.</criterion>
    <criterion>A router registration test can prove only selected-profile public tools are registered.</criterion>
  </acceptance_criteria>
</task>

<task id="T4" type="auto">
  <title>Add profile and router contract tests</title>
  <read_first>
    <file>tests/contract/mcp/test_mcp_server.py</file>
    <file>tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py</file>
    <file>tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py</file>
  </read_first>
  <action>
    Add `tests/contract/mcp/test_semantic_profiles.py` covering profile lookup,
    validation, built-in metadata, accelerator exclusion, Molmo privacy
    exclusions, and router registration.
  </action>
  <acceptance_criteria>
    <criterion>`tests/contract/mcp/test_semantic_profiles.py` passes through the repo pytest wrapper.</criterion>
  </acceptance_criteria>
</task>

<task id="T5" type="auto">
  <title>Update agent-facing vocabulary</title>
  <read_first>
    <file>docs/human/agent-task-command-taxonomy.md</file>
    <file>docs/human/coding-agent-nav-server.md</file>
    <file>docs/human/molmospaces-settings.md</file>
    <file>skills/ai2thor-navigator/SKILL.md</file>
  </read_first>
  <action>
    Make the smallest docs/skill updates needed to distinguish Task Prompt,
    Semantic Capability, Semantic Service, Demo Recipe, and Accelerator.
  </action>
  <acceptance_criteria>
    <criterion>Docs do not describe `scene_objects` or teleport-like `goto` as canonical real-robot capabilities.</criterion>
  </acceptance_criteria>
</task>

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

## Result

Complete on 2026-05-14.

Phase 136 added an additive semantic MCP profile/router layer without changing
existing demo server behavior:

- `roboclaws/mcp/profiles.py` defines `ContractProfile`, `ToolDescriptor`,
  capability-family constants, tool classification constants, provenance
  vocabulary, built-in `ai2thor_navigation_v1` and `molmospaces_cleanup_v1`
  metadata, profile lookup, and fail-closed validation.
- `roboclaws/mcp/entrypoint.py` provides a small router/helper that loads one
  selected profile and registers only that profile's public tools against
  supplied handlers.
- `tests/contract/mcp/test_semantic_profiles.py` locks the profile registry,
  AI2-THOR accelerator exclusions, Molmo private-metadata exclusions, router
  registration behavior, unknown-profile errors, and extra-handler rejection.
- `docs/human/coding-agent-nav-server.md`,
  `docs/human/molmospaces-settings.md`, and
  `skills/ai2thor-navigator/SKILL.md` now describe the semantic profile
  boundary and label `scene_objects` / teleport-like `goto` as AI2-THOR
  accelerators rather than real-robot canonical capabilities.

Verification evidence is recorded in `136-VERIFICATION.md`. The implementation
commit is `b620a44`.
