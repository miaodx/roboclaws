---
phase: 06
plan: 02
slug: api-semantic-backend-and-mcp-contract
type: execute
wave: 2
depends_on: [06-01]
files_modified:
  - roboclaws/molmo_cleanup/backend.py
  - roboclaws/molmo_cleanup/mcp_contract.py
  - tests/test_molmo_cleanup_backend.py
  - tests/test_molmo_cleanup_mcp_contract.py
autonomous: true
requirements_addressed: [MOLMO-CLEANUP-03, MOLMO-CLEANUP-04]
---

<objective>
Create the direct coding-agent tool contract over the fake/MolmoSpaces-shaped
backend, with stable IDs, stale-reference errors, and explicit
`api_semantic` primitive provenance.
</objective>

<tasks>

<task type="tdd">
  <name>Task 1: Implement object-moving backend primitives</name>
  <action>
    Add a backend that supports `observe`, `scene_objects`, `goto`, `pick`,
    `place`, and `done`. `pick` and `place` mutate semantic object state and
    return `primitive_provenance=api_semantic`. Unknown object or receptacle IDs
    return a structured `stale_reference` error.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_backend.py</automated>
  </verify>
</task>

<task type="tdd">
  <name>Task 2: Add a direct MCP-style contract wrapper</name>
  <action>
    Add a small wrapper exposing the backend methods as direct-call tool
    functions. Do not bind a network server in this phase; tests must exercise
    the contract in process.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_mcp_contract.py</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- The backend mutates object locations only through labeled primitives.
- The tool wrapper preserves private-manifest privacy.
- Stale IDs are explicit errors, not crashes.
</success_criteria>
