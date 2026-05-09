---
phase: 12
plan: 01
slug: current-contract-agent-bridge
type: execute
wave: 1
depends_on: [11]
files_modified:
  - roboclaws/molmo_cleanup/mcp_server.py
  - roboclaws/molmo_cleanup/mcp_contract.py
  - roboclaws/molmo_cleanup/report.py
  - examples/molmo_cleanup_agent_server.py
  - skills/molmo-cleanup/SKILL.md
  - scripts/run_molmo_agent_bridge_smoke.py
  - scripts/check_molmo_agent_bridge_result.py
  - just/harness.just
  - just/verify.just
  - tests/test_molmo_cleanup_mcp_server.py
  - tests/test_molmo_cleanup_agent_server.py
  - tests/test_check_molmo_agent_bridge_result.py
  - tests/test_verify_just_recipes.py
  - docs/plans/molmospaces-current-contract-agent-bridge.md
  - .planning/STATE.md
  - .planning/phases/12-molmospaces-current-contract-agent-bridge/12-VERIFICATION.md
  - .planning/phases/12-molmospaces-current-contract-agent-bridge/12-01-SUMMARY.md
autonomous: true
requirements_addressed: [MOLMO-AGENT-BRIDGE-01]
---

<objective>
Expose the existing MolmoSpaces current cleanup contract through a separate
FastMCP server so Codex, Claude Code, and OpenClaw can drive the semantic
cleanup tools directly, with artifacts comparable to the deterministic
rule-based cleanup run.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Molmo FastMCP server</name>
  <action>
    Add `MolmoCleanupMCPServer` and `make_molmo_cleanup_mcp(...)` that wrap
    `MolmoCleanupToolContract`, expose the current-contract cleanup tools, write
    request/response traces, and finalize `run_result.json` plus `report.html`
    when `done` is called.
  </action>
  <verify>
    <automated>Focused server tests cover tool registration, direct-call
    dispatch, trace output, done finalization, current-contract labels, and
    agent-driven metadata.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 2: Direct coding-agent entrypoint and skill</name>
  <action>
    Add a direct server script that prints Codex and Claude Code MCP setup
    commands, plus a compact `skills/molmo-cleanup/SKILL.md` describing the
    exact MCP tool sequence and current-contract boundaries.
  </action>
  <verify>
    <automated>Entrypoint tests assert the setup text names the Molmo skill,
    Codex command, Claude Code command, MCP URL, and artifact directory.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 3: Harness recipes and checker</name>
  <action>
    Add `just harness::molmo-agent-bridge` and
    `just verify::molmo-agent-bridge` so the local operator has a cheap
    non-agent contract smoke and focused tests. Add a checker that can validate
    clean direct-agent results and the lower OpenClaw viability gate.
  </action>
  <verify>
    <automated>Recipe tests detect the new harness and verify entries; checker
    tests cover clean agent cleanup, rule-based comparison, and minimum
    OpenClaw evidence.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 4: Local evidence and boundary docs</name>
  <action>
    Run focused tests and cheap local smoke runs, record evidence, and update
    the plan/state docs so this bridge is explicitly labeled
    `contract=current_contract` and not ADR-0003-complete.
  </action>
  <verify>
    <automated>Verification artifact maps every acceptance criterion to a
    command or generated artifact, including a comparison against the existing
    `public_heuristic` rule-based result.</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- The Molmo cleanup MCP server is separate from the AI2-THOR navigation MCP
  server and exposes `observe`, `scene_objects`, `navigate_to_object`,
  `navigate_to_receptacle`, `pick`, `open_receptacle`, `place`,
  `place_inside`, `object_done`, and `done`.
- Direct server startup text gives working Codex and Claude Code registration
  commands and points agents to `skills/molmo-cleanup/SKILL.md`.
- `run_result.json` and `report.html` distinguish `contract=current_contract`,
  `policy`, `agent_driven`, `policy_uses_private_truth=false`,
  `mcp_server=molmo_cleanup`, and current-contract shortcut notes.
- A cheap non-agent smoke proves the MCP wrapper can produce the same 5/5
  cleanup result as the current public rule-based cleanup loop.
- The checker can enforce the Clean Agent Cleanup Run criteria for Codex/Claude
  artifacts and the lower OpenClaw viability criteria for Gateway artifacts.
- Documentation states this bridge does not satisfy ADR-0003 and does not claim
  planner-backed robot manipulation.
</success_criteria>
