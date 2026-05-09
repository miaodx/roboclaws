---
phase: 13
plan: 01
slug: agent-bridge-visual-results
type: execute
wave: 1
depends_on: [12]
files_modified:
  - roboclaws/molmo_cleanup/mcp_server.py
  - examples/molmo_cleanup_agent_server.py
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
  - .planning/phases/13-molmospaces-agent-bridge-visual-results/13-VERIFICATION.md
  - .planning/phases/13-molmospaces-agent-bridge-visual-results/13-01-SUMMARY.md
autonomous: true
requirements_addressed: [MOLMO-AGENT-BRIDGE-VISUAL-01]
---

<objective>
Make the Codex, Claude Code, and OpenClaw Molmo cleanup bridge artifacts
visually comparable to `output/molmo-robot-visual-harness/report.html`: same
RBY1M FPV/chase/map/verification timeline, same semantic mid-phase rows, and
same public-rule baseline comparison.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Visual capture in the MCP bridge</name>
  <action>
    Extend `MolmoCleanupMCPServer` with an opt-in robot-view recording mode that
    calls the existing MolmoSpaces subprocess backend `write_robot_views(...)`
    after observe, scene_objects, and each semantic manipulation phase. Pass the
    resulting `robot_view_steps` into `render_cleanup_report`.
  </action>
  <verify>
    <automated>Server tests prove visual steps are written, relative image paths
    resolve, and `report.html` contains the robot timeline.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 2: CLI and smoke support</name>
  <action>
    Add backend, robot, and recording flags to the direct server and bridge smoke
    entrypoints so local operators can run the same current-contract agent path
    against `backend=molmospaces_subprocess`.
  </action>
  <verify>
    <automated>Entrypoint tests cover visual setup text and smoke arguments
    while preserving the cheap synthetic default.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 3: Visual checker and just recipes</name>
  <action>
    Teach the bridge checker to require robot-view evidence and add visual
    bridge recipes that compare the agent bridge to the public-rule visual
    harness result.
  </action>
  <verify>
    <automated>Checker tests reject missing visual steps and recipe tests assert
    the new visual bridge gates are registered.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 4: Local visual dogfood</name>
  <action>
    Run the visual rule baseline plus Codex, Claude Code, and OpenClaw bridge
    runs locally. Record generated artifact paths, scores, stale-reference
    counts, and robot-view counts.
  </action>
  <verify>
    <automated>Verification artifact maps every generated result to the checker
    command used to validate it.</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- The bridge can produce `robot_view_steps`, `view_variant`, `robot`,
  `robot_name`, and `artifacts.robot_views` in `run_result.json`.
- The bridge report includes `Robot View Timeline` rows for semantic mid phases.
- `just harness::molmo-agent-bridge-visual` generates both public-rule visual
  and current-contract bridge visual artifacts.
- Codex, Claude Code, and OpenClaw visual bridge runs are checker-validated,
  visually comparable to the public-rule baseline, and explicitly report any
  score gaps caused by public semantic choices versus private scorer truth.
- The ADR-0003 boundary remains explicit: this is still current-contract
  semantic API manipulation with public global `scene_objects`.
</success_criteria>
